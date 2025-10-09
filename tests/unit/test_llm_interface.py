"""Unit tests for LLM interface."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from meta_agent.llm_interface import (
    BaseLLM, MockLLM, GeminiLLM, make_llm,
    LLMConfigError, LLMAPIError
)


class TestMockLLM:
    """Test MockLLM implementation."""
    
    def test_frontend_generation(self):
        llm = MockLLM()
        result = llm.generate_code("create a frontend component")
        assert "Frontend" in result or "frontend" in result.lower()
        assert len(result) > 0
    
    def test_backend_generation(self):
        llm = MockLLM()
        result = llm.generate_code("create a backend API")
        assert "Backend" in result or "backend" in result.lower()
        assert len(result) > 0
    
    def test_test_generation(self):
        llm = MockLLM()
        result = llm.generate_code("create tests")
        assert "test" in result.lower()
        assert len(result) > 0
    
    def test_streaming(self):
        llm = MockLLM()
        chunks = list(llm.generate_streaming("create frontend"))
        assert len(chunks) == 1
        assert len(chunks[0]) > 0


class TestGeminiLLM:
    """Test GeminiLLM implementation."""
    
    def test_initialization_without_key(self):
        """Test that GeminiLLM initializes but client is None without API key."""
        with patch.dict('os.environ', {}, clear=True):
            llm = GeminiLLM()
            assert llm._client is None
    
    def test_api_key_validation(self):
        """Test API key validation."""
        llm = GeminiLLM()
        
        # Empty key should return None
        assert llm._load_api_key("") is None
        assert llm._load_api_key("   ") is None
        
        # Valid format
        key = llm._load_api_key("AIzaSyTest123")
        assert key == "AIzaSyTest123"
    
    def test_backoff_calculation(self):
        """Test exponential backoff calculation."""
        llm = GeminiLLM(base_backoff=2.0, max_backoff=60.0)
        
        # Attempt 0: ~2 seconds
        backoff_0 = llm._calculate_backoff(0)
        assert 2.0 <= backoff_0 <= 2.5
        
        # Attempt 1: ~4 seconds
        backoff_1 = llm._calculate_backoff(1)
        assert 4.0 <= backoff_1 <= 4.5
        
        # Attempt 10: should hit max
        backoff_10 = llm._calculate_backoff(10)
        assert backoff_10 <= 66.0  # max_backoff + jitter
    
    @patch('meta_agent.llm_interface.genai')
    def test_successful_generation(self, mock_genai):
        """Test successful code generation."""
        # Mock response
        mock_response = Mock()
        mock_response.text = "Generated code here"
        
        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)
        
        mock_genai.configure = Mock()
        mock_genai.GenerativeModel = Mock(return_value=mock_model)
        
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'AIzaSyTest123'}):
            with patch('meta_agent.llm_interface.genai', mock_genai):
                llm = GeminiLLM()
                result = llm.generate_code("test prompt")
                
                assert result == "Generated code here"
                mock_model.generate_content.assert_called_once()
    
    def test_fallback_on_no_client(self):
        """Test that MockLLM fallback works when client is not initialized."""
        with patch.dict('os.environ', {}, clear=True):
            llm = GeminiLLM()
            result = llm.generate_code("create frontend")
            
            # Should get MockLLM response
            assert len(result) > 0
            assert "Mock" in result or "frontend" in result.lower()


class TestMakeLLM:
    """Test LLM factory function."""
    
    def test_make_llm_prefers_gemini(self):
        """Test that make_llm returns GeminiLLM by default."""
        llm = make_llm(prefer_gemini=True)
        assert isinstance(llm, GeminiLLM)
    
    def test_make_llm_mock(self):
        """Test that make_llm can return MockLLM."""
        llm = make_llm(prefer_gemini=False)
        assert isinstance(llm, MockLLM)
