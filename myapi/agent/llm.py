from backend.config import settings
from langchain_groq import ChatGroq
from langchain_cerebras import ChatCerebras
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.model= ChatGoogleGenerativeAI(
            api_key= settings.google_api_key.get_secret_value(),
            model= "gemini-3.7-flash",
            temperature= 0.2,
            max_tokens= 3000
        )
    def invoke(self, messages):
        response= self.model.invoke(messages)
        return response
    
    def get_structured(self, schema, messages):
        structured_model = self.model.with_structured_output(schema)
        return structured_model.invoke(messages)
    

class AlternativeLLMService:
    def __init__(self):
        self.model= ChatGroq(
            api_key= settings.groq_api_key.get_secret_value(),
            model= "groq/compound",
            temperature= 0.2,
            max_tokens= 3000
        )

    def invoke(self, messages):
        response= self.model.invoke(messages)
        return response

    def get_structured(self, schema, messages):
        structured_model= self.model.with_structured_output(schema)
        return structured_model.invoke(messages)
    

    
class ChatLLMService:
    def __init__(self):
        self.model= ChatGroq(
            api_key= settings.groq_api_key.get_secret_value(),
            model= "openai/gpt-oss-120b",
            temperature= 0.5,
            max_tokens= 500
        )
    def invoke(self, messages):
        response= self.model.invoke(messages)
        return response
    
    def get_structured(self, schema, messages):
        structured_model = self.model.with_structured_output(schema)
        return structured_model.invoke(messages)
