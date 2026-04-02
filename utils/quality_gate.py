"""
CropSentinel AI  -  utils/quality_gate.py
Image quality gate: blur detection and minimum-size enforcement.
"""

import io
import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("QualityGate")


class ImageQualityGate:
    """
    Validates that an uploaded image meets minimum quality standards
    before passing it to the model predictor.
    """

    BLUR_THRESHOLD = 100.0  # Laplacian variance below this -> too blurry
    MIN_DIMENSION  = 50     # px  -  minimum width OR height

    def check(self, image_bytes: bytes) -> dict:
        """
        Check whether the image is acceptable for inference.

        Returns a dict:
          passed          : bool
          blur_score      : float  (Laplacian variance)
          quality_score   : float  (0-100, higher is better)
          rejection_reason: str or None
          width           : int
          height          : int
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            width, height = image.size

            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            quality_score = min(100.0, round((blur_score / 500.0) * 100.0, 2))

            if width < self.MIN_DIMENSION or height < self.MIN_DIMENSION:
                return {
                    "passed": False,
                    "blur_score": round(blur_score, 2),
                    "quality_score": quality_score,
                    "rejection_reason": (
                        f"Image too small ({width}x{height}px). "
                        f"Minimum {self.MIN_DIMENSION}x{self.MIN_DIMENSION}px required."
                    ),
                    "width": width,
                    "height": height,
                }

            if blur_score < self.BLUR_THRESHOLD:
                return {
                    "passed": False,
                    "blur_score": round(blur_score, 2),
                    "quality_score": quality_score,
                    "rejection_reason": (
                        "Image is too blurry. "
                        "Please retake photo in good lighting and hold camera steady."
                    ),
                    "width": width,
                    "height": height,
                }

            return {
                "passed": True,
                "blur_score": round(blur_score, 2),
                "quality_score": quality_score,
                "rejection_reason": None,
                "width": width,
                "height": height,
            }

        except Exception as e:
            logger.error(f"Quality gate error: {e}")
            return {
                "passed": False,
                "blur_score": 0.0,
                "quality_score": 0.0,
                "rejection_reason": f"Could not process image: {str(e)}",
                "width": 0,
                "height": 0,
            }
