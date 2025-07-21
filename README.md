# 🏥 Halodoc Homecare AI Assistant

A sophisticated multi-agent AI system built with Google's Generative AI SDK for Halodoc's homecare services. This project demonstrates advanced AI agent orchestration, RAG-powered information retrieval, and seamless booking workflows.

## 🌟 Features

### Multi-Agent Architecture
- **Orchestrator Agent**: Intelligent query routing and intent recognition
- **Discovery Agent**: RAG-powered service information and FAQ handling
- **Medical Advisor Agent**: Symptom analysis and service recommendations
- **Booking Agent**: Complete booking flow with payment integration
- **Care Navigator Agent**: Post-booking support and order management

### Key Capabilities
- 📚 PDF-based FAQ processing with vector search
- 🤖 Context-aware conversation management
- 💳 Mock payment and order services for demo
- 🎨 Rich console interface with real-time updates
- 📊 Session tracking and analytics

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google AI API Key (Gemini)
- PyCharm or any Python IDE

### Installation

1. **Clone the repository**
```bash
cd halodoc_homecare_assistant
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env .env
# Edit .env and add your Google API key
```

5. **Add FAQ documents**
```bash
mkdir -p data/faq_documents
# Place your PDF files in data/faq_documents/
```

6. **Run the assistant**
```bash
python main.py
```

## 📁 Project Structure

```
halodoc_homecare_assistant/
├── src/
│   ├── core/
│   │   ├── base_agent.py      # Base agent framework
│   │   ├── config.py          # Configuration management
│   │   └── conversation_manager.py
│   ├── agents/
│   │   ├── orchestrator.py    # Query routing
│   │   ├── discovery_agent.py # FAQ & services
│   │   ├── medical_advisor.py # Health recommendations
│   │   ├── booking_agent.py   # Booking flow
│   │   └── care_navigator.py  # Post-booking support
│   ├── services/
│   │   ├── vector_store.py    # ChromaDB integration
│   │   └── mock_services.py   # Payment & order mocks
│   └── utils/
├── data/
│   └── faq_documents/         # Place PDF files here
├── main.py                    # Entry point
├── requirements.txt
└── .env.example
```

## 🎮 Usage Examples

### Basic Service Discovery
```
You: What homecare services do you offer?
Assistant: [Provides detailed service information from FAQ documents]
```

### Medical Consultation
```
You: I have severe back pain and difficulty walking
Assistant: [Medical advisor analyzes symptoms and recommends physiotherapy]
```

### Complete Booking Flow
```
You: I want to book a physiotherapy session
Assistant: [Guides through service selection → date/time → address → payment]
```

### Order Support
```
You: What should I prepare for my nurse visit tomorrow?
Assistant: [Provides preparation checklist and important reminders]
```

## 🛠️ Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google AI API key
- `MODEL_NAME`: Gemini model (default: gemini-1.5-pro)
- `TEMPERATURE`: Model temperature (0.0-1.0)
- `CHROMA_PERSIST_DIRECTORY`: Vector DB storage location

### Adding FAQ Documents
1. Place PDF files in `data/faq_documents/`
2. The system automatically processes them on startup
3. Supports complex PDF layouts and multi-page documents

## 🏆 Hackathon Highlights

### Technical Innovation
- **Pure Google AI SDK**: No LangChain dependencies, showcasing Google's capabilities
- **Async Architecture**: High-performance concurrent agent processing
- **Smart Handoffs**: Seamless transitions between specialized agents
- **Context Preservation**: Maintains conversation state across agents

### Demo Features
- Live agent switching visualization
- Real-time booking progress tracking
- Mock payment flow for complete E2E demo
- Rich console UI with color-coded responses

### Scalability Considerations
- Modular agent design for easy extension
- Service-oriented architecture
- Configurable vector store for large document sets
- Session management for multiple users

## 🔧 Development

### Adding New Agents
1. Extend `BaseAgent` class
2. Implement `_get_system_prompt()` and `_process_specific()`
3. Register in `ConversationManager`
4. Update orchestrator routing logic

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 📈 Future Enhancements
- Voice input/output integration
- Multi-language support
- Real payment gateway integration
- WhatsApp/Telegram bot deployment
- Analytics dashboard
- ML-based intent prediction

## 🤝 Contributing
Feel free to submit issues and enhancement requests!

## 📄 License
This project is created for the Halodoc Hackathon demonstration purposes.

---

**Built with ❤️ using Google Generative AI SDK**