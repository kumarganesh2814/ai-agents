from typing import Dict, Any
import openai

class ResponseGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.model = model
        openai.api_key = api_key
    
    async def generate_response(self, context: Dict[str, Any], error: str = None) -> str:
        """Generate human-friendly response based on execution context"""
        prompt = self._build_prompt(context, error)
        
        response = await openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful DevOps assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        return response.choices[0].message.content
    
    def _build_prompt(self, context: Dict[str, Any], error: str = None) -> str:
        base_prompt = f"Command: {context.get('command')}\n"
        base_prompt += f"Result: {context.get('result')}\n"
        
        if error:
            base_prompt += f"Error: {error}\n"
            base_prompt += "Please explain what went wrong and suggest how to fix it."
        else:
            base_prompt += "Please provide a clear summary of what was done."
            
        return base_prompt