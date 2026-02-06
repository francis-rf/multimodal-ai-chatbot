"""
Image Service - Handles vision and image generation tasks
"""
import asyncio
import base64
from pathlib import Path
from typing import Optional, List, Dict
from openai import OpenAI
import fireworks.client as fw
from fireworks.client.image import ImageInference, Answer
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Set Fireworks API key globally
fw.api_key = settings.fireworks_api_key


class VisionService:
    """Service for analyzing images using Gemini"""

    def __init__(self):
        """Initialize vision service with Gemini"""
        self.client = OpenAI(api_key=settings.gemini_api_key, base_url=settings.gemini_base_url)
        self.model = settings.gemini_model
        logger.info(f"VisionService initialized with {self.model}")

    @staticmethod
    def encode_image(image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def analyze_image(
        self,
        image_path: str,
        prompt: str = "What is in this image?",
    ) -> str:
        """
        Analyze an image with a text prompt

        Args:
            image_path: Path to the image file
            prompt: Question or instruction about the image
            max_tokens: Maximum tokens in response

        Returns:
            str: Analysis result
        """
        try:
            image_base64 = self.encode_image(image_path)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],

            )

            result = response.choices[0].message.content
            logger.info(f"Image analyzed successfully using {self.model}")
            return result

        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise


class ImageGenerationService:
    """Service for generating images using Fireworks AI"""

    def __init__(self):
        """Initialize image generation service"""
        self.client = ImageInference(model=settings.fireworks_model)
        logger.info("Initialized ImageGenerationService with Fireworks AI")

    def generate_image(
        self,
        prompt: str,
        output_path: str = "generated_image.jpg",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate an image from a text prompt

        Args:
            prompt: Text description of the image to generate
            output_path: Path to save the generated image
            width: Image width in pixels
            height: Image height in pixels
            steps: Number of generation steps (higher = better quality, slower)
            cfg_scale: Classifier-free guidance scale (how closely to follow prompt)
            seed: Random seed for reproducibility (None for random)

        Returns:
            Optional[str]: Path to generated image, or None if failed
        """
        try:
            answer: Answer = self.client.text_to_image(
                prompt=prompt,
                cfg_scale=cfg_scale,
                height=height,
                width=width,
                steps=steps,
                seed=seed if seed is not None else 42,
                output_image_format="JPG"
            )

            if answer.image is None:
                logger.warning("Image generation returned None")
                return None

            answer.image.save(output_path)
            logger.info(f"Image generated successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise

    async def generate_image_async(
        self,
        prompt: str,
        output_path: str = "generated_image.jpg",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate an image from a text prompt (async version for FastAPI)

        Args:
            prompt: Text description of the image to generate
            output_path: Path to save the generated image
            width: Image width in pixels
            height: Image height in pixels
            steps: Number of generation steps (higher = better quality, slower)
            cfg_scale: Classifier-free guidance scale (how closely to follow prompt)
            seed: Random seed for reproducibility (None for random)

        Returns:
            Optional[str]: Path to generated image, or None if failed
        """
        try:
            answer: Answer = await self.client.text_to_image_async(
                prompt=prompt,
                cfg_scale=cfg_scale,
                height=height,
                width=width,
                steps=steps,
                seed=seed if seed is not None else 42,
                output_image_format="JPG"
            )

            if answer.image is None:
                logger.warning("Image generation returned None")
                return None

            answer.image.save(output_path)
            logger.info(f"Image generated successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise


