import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import PyPDF2
import pdfplumber
from typing import List, Dict, Optional
import os
from pathlib import Path
import hashlib
from loguru import logger
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

class VectorStore:
    def __init__(self, persist_directory: str, embedding_model: str = "all-MiniLM-L6-v2"):
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        self._embedding_model = None
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection for FAQ documents
        self.collection = self.client.get_or_create_collection(
            name="halodoc_faq",
            metadata={"description": "Halodoc homecare services FAQ and documentation"}
        )
        
        logger.info(f"Vector store initialized with {self.collection.count()} documents")
    
    @property
    def embedding_model(self):
        """Lazy initialization of the embedding model"""
        if self._embedding_model is None:
            def init_model():
                return SentenceTransformer(self.embedding_model_name)
            
            # Initialize in a thread to avoid event loop conflicts
            with ThreadPoolExecutor() as executor:
                future = executor.submit(init_model)
                self._embedding_model = future.result()
        return self._embedding_model
    
    def process_pdf(self, pdf_path: str) -> List[Dict[str, str]]:
        """Extract text from PDF and chunk it for embedding"""
        chunks = []
        
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        # Clean and chunk the text
                        cleaned_text = self._clean_text(text)
                        page_chunks = self._chunk_text(cleaned_text, page_num, pdf_path)
                        chunks.extend(page_chunks)
            
            if not chunks:
                # Fallback to PyPDF2 if pdfplumber fails
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            cleaned_text = self._clean_text(text)
                            page_chunks = self._chunk_text(cleaned_text, page_num + 1, pdf_path)
                            chunks.extend(page_chunks)
            
            logger.info(f"Extracted {len(chunks)} chunks from {pdf_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\/\₹]', '', text)
        return text.strip()
    
    def _chunk_text(self, text: str, page_num: int, source: str, chunk_size: int = 500) -> List[Dict[str, str]]:
        """Split text into overlapping chunks"""
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "page": page_num,
                        "source": os.path.basename(source),
                        "chunk_id": hashlib.md5(current_chunk.encode()).hexdigest()
                    })
                current_chunk = sentence + ". "
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "page": page_num,
                "source": os.path.basename(source),
                "chunk_id": hashlib.md5(current_chunk.encode()).hexdigest()
            })
        
        return chunks
    
    def load_pdf_directory(self, directory: str):
        """Load all PDFs from a directory into the vector store"""
        pdf_files = list(Path(directory).glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        all_chunks = []
        for pdf_file in pdf_files:
            chunks = self.process_pdf(str(pdf_file))
            all_chunks.extend(chunks)
        
        if all_chunks:
            self._add_documents(all_chunks)
            logger.info(f"Successfully loaded {len(all_chunks)} chunks from {len(pdf_files)} PDFs")
    
    def _add_documents(self, chunks: List[Dict[str, str]]):
        """Add document chunks to the vector store"""
        # Prepare data for ChromaDB
        documents = [chunk["content"] for chunk in chunks]
        metadatas = [{
            "page": chunk["page"],
            "source": chunk["source"],
            "chunk_id": chunk["chunk_id"]
        } for chunk in chunks]
        ids = [chunk["chunk_id"] for chunk in chunks]
        
        # Generate embeddings in a thread to avoid event loop conflicts
        def generate_embeddings():
            return self.embedding_model.encode(documents).tolist()
        
        # Run in a separate thread
        with ThreadPoolExecutor() as executor:
            future = executor.submit(generate_embeddings)
            embeddings = future.result()
        
        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(documents)} documents to vector store")
    
    async def search(self, query: str, k: int = 5) -> List[Dict[str, any]]:
        """Search for relevant documents"""
        try:
            # Generate query embedding in a thread to avoid event loop conflicts
            def generate_query_embedding():
                return self.embedding_model.encode([query]).tolist()
            
            # Run embedding generation in a thread
            query_embedding = await asyncio.to_thread(generate_query_embedding)
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "score": 1 - results['distances'][0][i] if results['distances'] else 0,
                        "source": results['metadatas'][0][i].get('source', 'Unknown') if results['metadatas'] else 'Unknown',
                        "page": results['metadatas'][0][i].get('page', 0) if results['metadatas'] else 0
                    })
            
            logger.info(f"Found {len(formatted_results)} relevant documents for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def clear_collection(self):
        """Clear all documents from the collection"""
        try:
            self.client.delete_collection("halodoc_faq")
            self.collection = self.client.create_collection(
                name="halodoc_faq",
                metadata={"description": "Halodoc homecare services FAQ and documentation"}
            )
            logger.info("Collection cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")