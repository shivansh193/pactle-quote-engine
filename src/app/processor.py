# src/processor.py (FINAL, SIMPLIFIED, AND RELIABLE VERSION)

import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
from typing import Dict, Any

class RfqOCRProcessor:
    def __init__(self):
        self.confidence_threshold = 60
        print("✓ OCR Processor Initialized (using Tesseract).")

    def enhance_image(self, image: Image.Image) -> Image.Image:
        cv_img = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 5)
        return Image.fromarray(thresh)

    def extract_text_with_confidence(self, image: Image.Image) -> tuple[str, float]:
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, lang='eng')
        except Exception as e:
            return f"Pytesseract error: {e}", 0.0

        text_parts, confidences = [], []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0 and data['text'][i].strip():
                text_parts.append(data['text'][i])
                confidences.append(int(data['conf'][i]))
        return ' '.join(text_parts), np.mean(confidences) if confidences else 0.0

    def _basic_text_clean(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def process_pil_image(self, pil_image: Image.Image) -> Dict[str, Any]:
        try:
            # Step 1: Extract text from the original image
            extracted_text, initial_confidence = self.extract_text_with_confidence(pil_image)
            current_text, enhancement_used, final_confidence = extracted_text, False, initial_confidence

            # Step 2: If confidence is low, try enhancing the image
            if initial_confidence < self.confidence_threshold:
                enhancement_used = True
                enhanced_img = self.enhance_image(pil_image)
                enhanced_text, enhanced_confidence = self.extract_text_with_confidence(enhanced_img)
                if enhanced_confidence > initial_confidence:
                    current_text = enhanced_text
                    final_confidence = enhanced_confidence
            
            # Step 3: Perform basic cleaning and return. NO AI MODEL.
            final_text = self._basic_text_clean(current_text)
            return {
                "final_cleaned_text": final_text,
                "summary": f"Final Confidence: {final_confidence:.1f}%. Enhanced: {enhancement_used}."
            }
        except Exception as e:
            return {"error": str(e)}