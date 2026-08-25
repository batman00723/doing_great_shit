from backend.config import settings
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)
    
class ChatLLMService:
    def __init__(self):
        self.model= ChatGroq(
            api_key= settings.groq_api_key.get_secret_value(),
            model= "openai/gpt-oss-120b",
            temperature= 0.5,
            max_tokens= 500
        )
    async def invoke(self, messages):
        response= await self.model.ainvoke(messages)
        return response
    
    async def get_structured(self, schema, messages):
        structured_model = self.model.with_structured_output(schema)
        return await structured_model.ainvoke(messages)



class ReportLLMService:
    def __init__(self):
        self.primary_model= ChatOpenAI(    
                base_url="https://openrouter.ai/api/v1",                                                                                                                              
                api_key=settings.openrouter_api_key.get_secret_value(),                                                                                                              
                model="meta-llama/llama-3.3-70b-instruct",                                                                                                                                         
                temperature=0.2,                    
                timeout= 10,                                                                                                                           
                max_retries=3                                                                                                                                                
            )

        self.fallback_model = ChatGoogleGenerativeAI(
            api_key= settings.google_api_key.get_secret_value(),
            model= "gemini-3.1-pro-preview",
            temperature= 0.2,
            max_tokens= 3000,
            max_retries=1
        )
        
    async def invoke(self, messages):
        chain = self.primary_model.with_fallbacks([self.fallback_model])
        return await chain.ainvoke(messages)                                                                                                                          
                                                                                                                                                                                
    async def get_structured(self, schema, messages):                                                                                                                                                                                                                                  
        primary_structured = self.primary_model.with_structured_output(schema)
        fallback_structured = self.fallback_model.with_structured_output(schema)
        robust_structured = primary_structured.with_fallbacks([fallback_structured])
        return await robust_structured.ainvoke(messages)