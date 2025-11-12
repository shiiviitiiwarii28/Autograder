# test_ocr_debug.py
import asyncio
from app.services.ocr_service import OCRService

async def run_test():
    ocr = OCRService()

    img_path = r"C:\Users\HP\Desktop\Autograder\server\uploads\7113807a-a3e7-4acb-ba36-a7d860b63f3c\STU004\handwritten_test.jpg"

    print(f"🖼️ Testing OCR on: {img_path}")

    with open(img_path, "rb") as f:
        data = f.read()

    result = await ocr.extract_text_from_image(data)

    print("\n✅ OCR Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(run_test())
