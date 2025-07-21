import pytest
import asyncio
from unittest.mock import Mock, patch
from src.core.conversation_manager import ConversationManager
from src.core.base_agent import AgentType

@pytest.fixture
def mock_config():
    return {
        "google_api_key": "test_key",
        "model_name": "gemini-1.5-pro",
        "chroma_persist_directory": "./test_data/chroma_db",
        "embedding_model": "all-MiniLM-L6-v2"
    }

@pytest.fixture
def conversation_manager(mock_config):
    with patch('src.core.conversation_manager.VectorStore'):
        with patch('google.generativeai.configure'):
            manager = ConversationManager(mock_config)
            return manager

@pytest.mark.asyncio
async def test_session_creation(conversation_manager):
    """Test basic session creation"""
    session_id = conversation_manager.create_session()
    assert session_id is not None
    assert len(session_id) > 0
    
    session = conversation_manager.get_session(session_id)
    assert session is not None
    assert session.session_id == session_id

@pytest.mark.asyncio
async def test_orchestrator_routing(conversation_manager):
    """Test orchestrator routing logic"""
    session_id = conversation_manager.create_session()
    
    # Mock the orchestrator response
    mock_response = Mock()
    mock_response.content = "Routing to discovery agent"
    mock_response.requires_handoff = True
    mock_response.handoff_to = AgentType.DISCOVERY
    mock_response.metadata = {}
    
    with patch.object(conversation_manager.orchestrator, 'process', return_value=mock_response):
        with patch.object(conversation_manager.discovery_agent, 'process', return_value=mock_response):
            response = await conversation_manager.process_message(
                session_id, 
                "What services do you offer?"
            )
            
            assert response is not None
            assert "discovery" in response.lower() or "service" in response.lower()

@pytest.mark.asyncio
async def test_booking_flow_initiation(conversation_manager):
    """Test booking flow initiation"""
    session_id = conversation_manager.create_session()
    
    mock_response = Mock()
    mock_response.content = "I'll help you book a service"
    mock_response.requires_handoff = False
    mock_response.metadata = {"booking_state": {"current_step": "service_selection"}}
    
    with patch.object(conversation_manager.booking_agent, 'process', return_value=mock_response):
        response = await conversation_manager.process_message(
            session_id, 
            "I want to book a nurse visit"
        )
        
        assert response is not None
        session = conversation_manager.get_session(session_id)
        # Note: In actual implementation, booking_state would be updated

def test_agent_initialization(conversation_manager):
    """Test that all agents are properly initialized"""
    assert conversation_manager.orchestrator is not None
    assert conversation_manager.discovery_agent is not None
    assert conversation_manager.medical_advisor is not None
    assert conversation_manager.booking_agent is not None
    assert conversation_manager.care_navigator is not None
    
    assert len(conversation_manager.agents) == 5