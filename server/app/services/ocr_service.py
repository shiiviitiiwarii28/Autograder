# app/services/ocr_service.py

import pytesseract
from PIL import Image
import cv2
import numpy as np
from typing import Dict, Any
import fitz  # PyMuPDF
import io
import os
import re
import easyocr
from paddleocr import PaddleOCR


class OCRService:
    def __init__(self):
        # Confidence threshold for switching OCR engines
        self.confidence_threshold = 0.5

        # Initialize EasyOCR (for handwriting)
        self.easyocr_reader = easyocr.Reader(['en'], gpu=False)

        # Initialize PaddleOCR (robust fallback)
        self.paddle_ocr = PaddleOCR(lang='en', use_angle_cls=True)

    # -------------------------------------------------------------------------
    # IMAGE OCR (PaddleOCR + Tesseract + EasyOCR Fallback)
    # -------------------------------------------------------------------------
    async def extract_text_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """Extract text from handwritten image using PaddleOCR first, then Tesseract/EasyOCR fallback."""
        try:
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            image_np = np.array(image)

            # 🧹 Step 0: Clean the image (remove blue lines & normalize background)
            image_np = self._remove_blue_lines(image_np)
            image_np = self._normalize_background(image_np)

            # 🧠 Step 1: Try PaddleOCR first (best for handwriting)
            print("🧠 Trying PaddleOCR first (optimized for handwriting)...")
            try:
                paddle_results = self.paddle_ocr.ocr(image_np, cls=True)
                if paddle_results and isinstance(paddle_results, list):
                    lines, confidences = [], []
                    for block in paddle_results:
                        for line in block:
                            if len(line) >= 2:
                                lines.append(line[1][0])
                                confidences.append(line[1][1])
                    if lines:
                        text = " ".join(lines)
                        avg_conf = round(sum(confidences) / len(confidences), 3)
                        print(f"✅ PaddleOCR succeeded, confidence={avg_conf}")
                        return {
                            "text": text.strip(),
                            "confidence": avg_conf,
                            "status": "success",
                            "method": "paddleocr"
                        }
            except Exception as e:
                print(f"⚠️ PaddleOCR failed initially: {e}")

            # 🔁 Step 2: Try preprocessing variants + Tesseract/EasyOCR fallback
            print("🔁 Falling back to Tesseract/EasyOCR hybrid...")
            variants = {
                "A_contrast_clahe": self._preprocess_variant_A,
                "B_adaptive_inv_morph": self._preprocess_variant_B,
                "C_gray_sharpen_upscale": self._preprocess_variant_C,
                "D_ink_boost": self._preprocess_variant_D
            }

            best = {"text": "", "confidence": 0.0, "method": "none"}
            for name, func in variants.items():
                processed = func(image_np.copy())
                debug_name = f"debug_preprocessed_{name}.jpg"
                cv2.imwrite(debug_name, processed)
                print(f"🖼️ Saved preprocessed image to {debug_name}")

                # 🧩 Tesseract OCR
                try:
                    proc_gray = processed if processed.ndim == 2 else cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                    tess_config = "--oem 1 --psm 6"
                    text_tess = pytesseract.image_to_string(proc_gray, config=tess_config).strip()
                    data = pytesseract.image_to_data(proc_gray, output_type=pytesseract.Output.DICT)
                    confs = [
                        float(c) / 100.0
                        for c in data.get("conf", [])
                        if str(c).isdigit() and float(c) > 0
                    ]
                    avg_conf_tess = sum(confs) / len(confs) if confs else 0.0
                except Exception as e:
                    print(f"⚠️ Tesseract error on {name}: {e}")
                    text_tess, avg_conf_tess = "", 0.0

                # 🧩 EasyOCR fallback
                try:
                    rgb_for_easy = (
                        cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
                        if processed.ndim == 3
                        else cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                    )
                    easy_results = self.easyocr_reader.readtext(rgb_for_easy, detail=1, paragraph=True)
                    if easy_results:
                        texts = [r[1] for r in easy_results if len(r) >= 2]
                        text_easy = " ".join(texts).strip()
                        confs_easy = [r[2] for r in easy_results if isinstance(r[2], (float, int))]
                        avg_conf_easy = sum(confs_easy) / len(confs_easy) if confs_easy else 0.0
                    else:
                        text_easy, avg_conf_easy = "", 0.0
                except Exception as e:
                    print(f"⚠️ EasyOCR error on {name}: {e}")
                    text_easy, avg_conf_easy = "", 0.0

                # 🧮 Choose better result
                winner_text = (
                    text_easy if (avg_conf_easy > avg_conf_tess or len(text_easy) > len(text_tess)) else text_tess
                )
                winner_conf = max(avg_conf_easy, avg_conf_tess)
                method_used = "easyocr" if winner_text == text_easy else "tesseract"

                if winner_conf > best["confidence"]:
                    best.update({
                        "text": winner_text,
                        "confidence": winner_conf,
                        "method": method_used,
                        "variant": name,
                    })

            if not best["text"]:
                return {"text": "", "confidence": 0.0, "status": "error", "error": "no text extracted"}

            print(f"✅ OCR completed using {best['method'].upper()} ({best['variant']}), confidence={best['confidence']}")
            return {
                "text": best["text"],
                "confidence": best["confidence"],
                "status": "success",
                "method": best["method"],
            }

        except Exception as e:
            return {"text": "", "confidence": 0.0, "status": "error", "error": str(e)}

    # -------------------------------------------------------------------------
    # PDF OCR
    # -------------------------------------------------------------------------
    async def extract_text_from_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """Extract text from PDF bytes (handles both text & image-based PDFs)."""
        try:
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            extracted_pages = []
            total_conf = 0

            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text = page.get_text()

                if text.strip():
                    extracted_pages.append({
                        "page": page_num + 1,
                        "text": text.strip(),
                        "confidence": 0.95,
                        "method": "direct",
                    })
                    total_conf += 0.95
                else:
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    ocr_result = await self.extract_text_from_image(img_data)
                    extracted_pages.append({
                        "page": page_num + 1,
                        "text": ocr_result["text"],
                        "confidence": ocr_result["confidence"],
                        "method": ocr_result.get("method", "ocr"),
                    })
                    total_conf += ocr_result["confidence"]

            pdf_document.close()
            combined_text = "\n\n".join([p["text"] for p in extracted_pages])
            avg_conf = total_conf / len(extracted_pages) if extracted_pages else 0

            return {
                "text": combined_text,
                "confidence": round(avg_conf, 2),
                "pages": extracted_pages,
                "status": "success",
            }

        except Exception as e:
            return {"text": "", "confidence": 0.0, "status": "error", "error": str(e)}

    # -------------------------------------------------------------------------
    # TXT OCR
    # -------------------------------------------------------------------------
    async def extract_text_from_txt(self, file_path: str) -> Dict[str, Any]:
        """Extract text from TXT file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return {"text": text.strip(), "confidence": 1.0, "status": "success"}
        except Exception as e:
            return {"text": "", "confidence": 0.0, "status": "error", "error": str(e)}

    # -------------------------------------------------------------------------
    # AUTO-DETECT FILE TYPE
    # -------------------------------------------------------------------------
    async def extract_answers(self, file_path: str) -> Dict[str, str]:
        """Extract answers from TXT, PDF, or image file."""
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".txt":
            result = await self.extract_text_from_txt(file_path)
        elif file_extension == ".pdf":
            with open(file_path, "rb") as f:
                pdf_data = f.read()
            result = await self.extract_text_from_pdf(pdf_data)
        else:
            with open(file_path, "rb") as f:
                image_data = f.read()
            result = await self.extract_text_from_image(image_data)

        if result["status"] == "success" and result["text"]:
            return self._parse_answers_botanical(result["text"])
        else:
            return {}

    # -------------------------------------------------------------------------
    # IMAGE CLEANING HELPERS
    # -------------------------------------------------------------------------
    def _remove_blue_lines(self, image):
        """Remove blue ruled lines (common in notebook paper)."""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        image[mask > 0] = [255, 255, 255]
        return image

    def _normalize_background(self, image):
        """Normalize uneven lighting and shadows."""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        bg = cv2.medianBlur(gray, 31)
        norm = cv2.divide(gray, bg, scale=255)
        return cv2.cvtColor(norm, cv2.COLOR_GRAY2RGB)

    # -------------------------------------------------------------------------
    # IMAGE PREPROCESSING VARIANTS
    # -------------------------------------------------------------------------
    def _preprocess_variant_A(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        gray = cv2.convertScaleAbs(gray, alpha=1.6, beta=12)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.fastNlMeansDenoising(gray, None, 20, 7, 21)
        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 10)
        kernel = np.ones((2, 2), np.uint8)
        proc = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=1)
        return cv2.resize(proc, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

    def _preprocess_variant_B(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 18)
        kernel = np.ones((3, 3), np.uint8)
        proc = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=2)
        proc = cv2.resize(proc, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)
        return 255 - proc

    def _preprocess_variant_C(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        kernel_sharp = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharp = cv2.filter2D(gray, -1, kernel_sharp)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        sharp = clahe.apply(sharp)
        _, thr = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        proc = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel, iterations=1)
        return cv2.resize(proc, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

    def _preprocess_variant_D(self, image):
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        L, A, B = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        L = clahe.apply(L)
        merged = cv2.merge((L, A, B))
        gray = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)
        gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15
        )
        kernel = np.ones((3, 3), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        final = 255 - morph
        final = cv2.resize(final, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite("debug_preprocessed_D_ink_boost.jpg", final)
        print("🖼️ Saved preprocessed image to debug_preprocessed_D_ink_boost.jpg")
        return final

    # -------------------------------------------------------------------------
    # ANSWER PARSER
    # -------------------------------------------------------------------------
    def _parse_answers_botanical(self, text: str) -> Dict[str, str]:
        """
        Improved OCR text parser for AutoGrader.
        Handles answers in continuous lines, missing colons, and inconsistent spacing.
        Example text handled:
        'Answer 1 JDK used for developing Java programs. JRE is runtime,JVM executes program Answer 2: ...'
        """
        import re

        # --- Clean up OCR text ---
        text = text.replace("EXAMINATI ON", "EXAMINATION")  # Fix OCR spacing error
        text = re.sub(r"Answer(\d)", r"Answer \1", text)    # Ensure space after 'Answer'
        text = re.sub(r"\s+", " ", text).strip()             # Normalize spaces

        # --- Regex to match all answers in one go ---
        # Matches patterns like:
        #   Answer 1, Answer1., Answer:1, Answer 1:
        pattern = r"(?:Answer\s*[\.:]?\s*(\d+)[\.:]?\s*)(.*?)(?=Answer\s*\d+[\.:]?|$)"
        matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)

        answers = {}
        for num, ans in matches:
            cleaned_answer = ans.strip()
            if cleaned_answer:
                answers[f"question_{num}"] = cleaned_answer

        # --- Debug logs (visible in backend terminal) ---
        print("🧾 CLEANED OCR TEXT PREVIEW:", text[:400])
        print("✅ PARSED ANSWERS:", answers)

        return answers
