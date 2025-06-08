import unittest
from unittest.mock import patch, MagicMock
from devops_gpt.llm_providers import OllamaProvider
from devops_gpt.config import parse_config

class TestOllamaProvider(unittest.TestCase):
    def setUp(self):
        self.config = {
            'llm': {
                'provider': 'ollama',
                'base_url': 'http://localhost:11434',
                'model': 'llama2',
                'max_tokens': 500,
                'fallback_provider': True,
                'openai_api_key': 'dummy-key',
                'openai_model': 'gpt-4',
            }
        }
        
    @patch('devops_gpt.llm_providers.requests')
    def test_generate_response(self, mock_requests):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test response'}
        mock_requests.post.return_value = mock_response

        # Initialize provider
        provider = OllamaProvider(
            base_url=self.config['llm']['base_url'],
            model=self.config['llm']['model'],
            max_tokens=self.config['llm']['max_tokens']
        )

        # Test generate_response
        response = provider.generate_response('Test prompt')
        self.assertEqual(response, 'Test response')
        
        # Verify API call
        mock_requests.post.assert_called_with(
            f"{self.config['llm']['base_url']}/api/generate",
            json={
                'model': self.config['llm']['model'],
                'prompt': 'Test prompt',
                'max_tokens': self.config['llm']['max_tokens']
            }
        )

    @patch('devops_gpt.llm_providers.requests')
    def test_handle_request_error(self, mock_requests):
        # Setup mock error response 
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'error': 'Internal server error'}
        mock_requests.post.return_value = mock_response

        provider = OllamaProvider(
            base_url=self.config['llm']['base_url'],
            model=self.config['llm']['model'],
            max_tokens=self.config['llm']['max_tokens']
        )

        # Verify error handling
        with self.assertRaises(Exception):
            provider.generate_response('Test prompt')

    @patch('devops_gpt.llm_providers.requests')
    def test_fallback_behavior(self, mock_requests):
        # Setup mock error for Ollama
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.post.side_effect = [mock_response, MagicMock(status_code=200, json=lambda: {'response': 'Fallback response'})]

        config = parse_config('config.yaml')
        provider = OllamaProvider(
            base_url=self.config['llm']['base_url'],
            model=self.config['llm']['model'],
            max_tokens=self.config['llm']['max_tokens'],
            fallback_provider=True,
            openai_api_key=self.config['llm']['openai_api_key'],
            openai_model=self.config['llm']['openai_model']
        )

        response = provider.generate_response('Test prompt')
        self.assertEqual(response, 'Fallback response')

if __name__ == '__main__':
    unittest.main()
