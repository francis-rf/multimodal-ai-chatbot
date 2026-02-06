"""
OpenAI, Groq, and Gemini Chat Model Integration
Supports basic chat, tool calling with Tavily search, and streaming
"""

from openai import OpenAI
from typing import List, Dict, Optional
from utils.config import settings
from utils.logger import get_logger
from models.tools import tool_manager

logger = get_logger(__name__)

class GroqChat:
    """Groq, Qwen, and Llama models with tool calling"""

    def __init__(self, model_name: str):
        """Initialize Groq client for specified model"""
        try:
            self.model_name = model_name
            self.api_key = settings.groq_api_key
            self.model = getattr(settings, f"{model_name}_model")
            self.base_url = settings.groq_base_url
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.tool_manager = tool_manager
            logger.info(f"Groq client initialized for {model_name}: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
            raise Exception(f"Initialization failed: {str(e)}")

    def chat_completion(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = "You are a helpful assistant",
        use_tools: bool = False
    ) -> str:
        """Get response from Openai/Groq/Qwen/Llama model"""
        try:
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            logger.debug(f"Sending request to {self.model_name}, tools={use_tools}")

            params = {
                "model": self.model,
                "messages": messages
            }

            if use_tools:
                params["tools"] = self.tool_manager.get_tool_definitions()
                params["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**params)
            assistant_message = response.choices[0].message

            # Handle tool calls
            if assistant_message.tool_calls:
                logger.info(f"Processing tool calls for {self.model_name}")

                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in assistant_message.tool_calls
                    ]
                })

                tool_results = self.tool_manager.process_tool_calls(assistant_message.tool_calls)
                messages.extend(tool_results)

                params["messages"] = messages
                final_response = self.client.chat.completions.create(**params)
                result = final_response.choices[0].message.content

                logger.info("Got response after tool execution")
                return result

            logger.info(f"Response from {self.model_name} received")
            return assistant_message.content or "I received your message but have no response."

        except Exception as e:
            logger.error(f"Error with {self.model_name}: {str(e)}")
            return f"Sorry, an error occurred: {str(e)}"

    def chat_completion_stream(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = "You are a helpful assistant"
    ):
        """Stream response from openai/Groq/Qwen/Llama"""
        try:
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            logger.debug(f"Streaming from {self.model_name}")

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info(f"Streaming from {self.model_name} completed")

        except Exception as e:
            logger.error(f"Streaming error for {self.model_name}: {str(e)}")
            yield f"Error: {str(e)}"


class GeminiChat:
    """Google Gemini model with tool calling"""

    def __init__(self):
        """Initialize Gemini client"""
        try:
            self.api_key = settings.gemini_api_key
            self.model = settings.gemini_model
            self.base_url = settings.gemini_base_url
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.tool_manager = tool_manager
            logger.info(f"Gemini client initialized: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise Exception(f"Initialization failed: {str(e)}")

    def chat_completion(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = "You are a helpful assistant",
        use_tools: bool = False
    ) -> str:
        """Get response from Gemini model"""
        try:
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            logger.debug(f"Sending request to Gemini, tools={use_tools}")

            params = {
                "model": self.model,
                "messages": messages
            }

            if use_tools:
                params["tools"] = self.tool_manager.get_tool_definitions()
                params["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**params)
            assistant_message = response.choices[0].message

            # Handle tool calls
            if assistant_message.tool_calls:
                logger.info("Processing tool calls for Gemini")

                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in assistant_message.tool_calls
                    ]
                })

                tool_results = self.tool_manager.process_tool_calls(assistant_message.tool_calls)
                messages.extend(tool_results)

                params["messages"] = messages
                final_response = self.client.chat.completions.create(**params)
                result = final_response.choices[0].message.content

                logger.info("Got response after tool execution")
                return result

            logger.info("Gemini response received")
            return assistant_message.content

        except Exception as e:
            logger.error(f"Error with Gemini: {str(e)}")
            return f"Sorry, an error occurred: {str(e)}"

    def chat_completion_stream(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = "You are a helpful assistant"
    ):
        """Stream response from Gemini"""
        try:
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            logger.debug("Streaming from Gemini")

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info("Gemini streaming completed")

        except Exception as e:
            logger.error(f"Gemini streaming error: {str(e)}")
            yield f"Error: {str(e)}"

