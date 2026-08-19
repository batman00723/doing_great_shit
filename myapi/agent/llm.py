from backend.config import settings
from langchain_groq import ChatGroq
from langchain_cerebras import ChatCerebras
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI
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


class ReportLLMService:
    def __init__(self):
        self.primary_model= ChatOpenAI(    
                base_url="https://openrouter.ai/api/v1",                                                                                                                                
                api_key=settings.openrouter_api_key.get_secret_value(),                                                                                                              
                model="meta-llama/llama-3.3-70b-instruct",                                                                                                                                         
                temperature=0.2,                    
                timeout= 360,                                                                                                                           
                model_kwargs={"max_retries": 3}                                                                                                                                                
            )

        self.fallback_model = ChatGoogleGenerativeAI(
            api_key= settings.google_api_key.get_secret_value(),
            model= "gemini-3.1-pro-preview",
            temperature= 0.2,
            max_tokens= 3000,
            model_kwargs={"max_retries": 1}
        )
        
        self.robust_model = self.primary_model.with_fallbacks([self.fallback_model])

    def invoke(self, messages):                                                                                                                                                                                               
        return self.robust_model.invoke(messages)                                                                                                                          
                                                                                                                                                                               
    def get_structured(self, schema, messages):                                                                                                                                                                                                                                  
        structured_model = self.robust_model.with_structured_output(schema)                                                                                                
        return structured_model.invoke(messages)