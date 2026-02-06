"""
FastAPI Multi-Modal Chatbot Application
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import os
import time
import traceback
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import our services
from services.image_service import VisionService, ImageGenerationService
from services.speech_service import TextToSpeechService
from models.chat_models import GroqChat, GeminiChat
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(title="OmniChat - Multi-Modal AI")

# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=3)

# Mount static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
vision_service_gemini = VisionService()
image_gen_service = ImageGenerationService()
text_to_speech_service = TextToSpeechService()

# Initialize chat models
openai_chat = None
groq_chat = None
qwen_chat = None
llama_chat = None
gemini_chat = None



try:
    openai_chat= GroqChat(model_name="openai")
    logger.info("openai chat model initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Groq: {e}")

try:
    groq_chat = GroqChat(model_name="groq")
    logger.info("Groq chat model initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Groq: {e}")

try:
    qwen_chat = GroqChat(model_name="qwen")
    logger.info("Qwen chat model initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Qwen: {e}")

try:
    llama_chat = GroqChat(model_name="llama")
    logger.info("Llama chat model initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Llama: {e}")

try:
    gemini_chat = GeminiChat()
    logger.info("Gemini chat model initialized")
except Exception as e:
    logger.warning(f"Failed to initialize Gemini: {e}")

# Simple in-memory conversation storage (session_id -> history)
conversation_histories = {}

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    model: str = "openai"
    use_tools: bool = True  # Enable tool calling by default
    session_id: str = "default"  # Session ID for conversation memory

class ChatResponse(BaseModel):
    response: str

class ImageGenerateRequest(BaseModel):
    prompt: str
    steps: int = 70

class ImageGenerateResponse(BaseModel):
    image_path: str
    message: str

# Routes

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main HTML page"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Handle text chat messages with streaming
    """
    try:
        # Select the appropriate chat model
        chat_instance = None
        model_name = request.model.lower()

        if model_name == "openai":
            chat_instance = openai_chat  
        elif model_name == "groq":
            chat_instance = groq_chat
        elif model_name == "qwen":
            chat_instance = qwen_chat
        elif model_name == "llama":
            chat_instance = llama_chat
        elif model_name == "gemini":
            chat_instance = gemini_chat
        else:
            # Default to groq if available
            chat_instance = groq_chat

        if chat_instance is None:
            raise HTTPException(
                status_code=503,
                detail=f"The {model_name} model is not available. Please check your API keys."
            )

        # Get or create conversation history
        if request.session_id not in conversation_histories:
            conversation_histories[request.session_id] = []

        conversation_history = conversation_histories[request.session_id]

        # Define streaming generator
        async def generate():
            try:
                loop = asyncio.get_event_loop()

                # Disable tools for models that don't support them well
                use_tools_for_model = request.use_tools
                if model_name in ["openai", "groq"]:
                    use_tools_for_model = False
                    if request.use_tools:
                        logger.info(f"Tools disabled for {model_name} model (not supported)")

                # If tools are enabled, use non-streaming completion
                if use_tools_for_model:
                    logger.info("Using non-streaming mode with tools enabled")
                    # Enhanced system prompt for tool usage
                    tool_system_prompt = (
                        "You are a helpful assistant with access to web search. "
                        "When asked for current information, news, facts, or to list specific items, "
                        "use the tavily_search tool to find accurate information. "
                        "Always search when unsure or when details are requested."
                    )
                    response = await loop.run_in_executor(
                        None,
                        chat_instance.chat_completion,
                        request.message,
                        conversation_history,  # Pass conversation history
                        tool_system_prompt,  # Enhanced system_prompt for better tool usage
                        True  # use_tools
                    )
                    # Add to history
                    conversation_history.append({"role": "user", "content": request.message})
                    conversation_history.append({"role": "assistant", "content": response})
                    # Keep last 10 exchanges (20 messages)
                    if len(conversation_history) > 20:
                        conversation_history[:] = conversation_history[-20:]

                    # Stream response word by word to match streaming behavior
                    words = response.split()
                    for word in words:
                        yield f"data: {word} \n\n"
                # Use streaming method if available and tools not required
                elif hasattr(chat_instance, 'chat_completion_stream'):
                    logger.info("Using streaming mode")
                    full_response = ""
                    # Run the synchronous generator in thread pool
                    with ThreadPoolExecutor() as executor:
                        for chunk in chat_instance.chat_completion_stream(request.message, conversation_history):
                            full_response += chunk
                            yield f"data: {chunk}\n\n"
                            await asyncio.sleep(0)  # Allow other tasks to run

                    # Add to history after streaming completes
                    conversation_history.append({"role": "user", "content": request.message})
                    conversation_history.append({"role": "assistant", "content": full_response})
                    if len(conversation_history) > 20:
                        conversation_history[:] = conversation_history[-20:]
                else:
                    # Fallback to non-streaming without tools
                    response = await loop.run_in_executor(
                        None,
                        chat_instance.chat_completion,
                        request.message,
                        conversation_history,
                        "You are a helpful assistant",
                        False
                    )
                    # Add to history
                    conversation_history.append({"role": "user", "content": request.message})
                    conversation_history.append({"role": "assistant", "content": response})
                    if len(conversation_history) > 20:
                        conversation_history[:] = conversation_history[-20:]

                    yield f"data: {response}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                yield f"data: Error: {str(e)}\n\n"

        logger.info(f"Chat request processed with {model_name}: {request.message[:50]}...")
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/clear")
async def clear_conversation(request: dict):
    """Clear conversation history for a session"""
    try:
        session_id = request.get("session_id", "default")
        if session_id in conversation_histories:
            conversation_histories[session_id] = []
            logger.info(f"Cleared conversation history for session: {session_id}")
        return {"status": "success", "message": "Conversation cleared"}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form("Describe this image in detail"),
):
    """
    Analyze an uploaded image using vision models
    """
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        service = vision_service_gemini

        # Analyze the image
        result = service.analyze_image(temp_path, prompt)

        # Clean up temp file
        os.remove(temp_path)

        logger.info(f"Image analyzed successfully with gemini")
        return {"result": result}

    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/image/generate", response_model=ImageGenerateResponse)
async def generate_image(request: ImageGenerateRequest):
    """
    Generate an image from text prompt
    """
    try:
        # Create outputs directory if it doesn't exist
        os.makedirs("static/generated", exist_ok=True)

        # Generate unique filename
        filename = f"generated_{int(time.time())}.jpg"
        output_path = f"static/generated/{filename}"

        # Generate image using the async version
        result_path = await image_gen_service.generate_image_async(
            prompt=request.prompt,
            output_path=output_path,
            steps=request.steps
        )

        if result_path:
            # Return path relative to static folder
            relative_path = f"/static/generated/{filename}"
            logger.info(f"Image generated successfully: {filename}")
            return ImageGenerateResponse(
                image_path=relative_path,
                message="Image generated successfully!"
            )
        else:
            raise HTTPException(status_code=500, detail="Image generation failed")

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/speech/synthesize")
async def synthesize_speech(request: dict):
    """
    Convert text to speech and return audio as base64
    """
    try:
        text = request.get("text", "")
        voice = request.get("voice", "autumn")  # Default to autumn voice
        response_format = request.get("format", "wav")  # Default to wav

        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        logger.info(f"Synthesizing speech for text: {text[:50]}... with voice: {voice}")

        # Generate speech
        audio_base64 = text_to_speech_service.text_to_speech_base64(
            text,
            voice=voice,
            response_format=response_format
        )

        logger.info(f"Speech synthesized successfully, base64 length: {len(audio_base64)}")
        return {
            "audio": audio_base64,
            "format": response_format
        }

    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "OminiChat is running!"}

if __name__ == "__main__":
    import uvicorn
    print("Starting OmniChat AI Chatbot...")
    print("Open your browser at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
