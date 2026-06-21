import re
import io
import os
import logging
from PIL import Image, ImageEnhance, ImageFilter
from typing import Dict, Any, Tuple, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AyurAharOCR")

# Try to import pytesseract
try:
    import pytesseract
    # Try to search for standard Windows installation paths if Tesseract isn't in environment path
    TESSERACT_WINDOWS_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for path in TESSERACT_WINDOWS_PATHS:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Configured Tesseract path to: {path}")
            break
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False
    logger.warning("Pytesseract not installed in this environment.")

# Try to import easyocr
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False
    logger.warning("EasyOCR not installed in this environment.")

def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Applies image enhancement techniques to improve OCR accuracy on handwritten text.
    - Convers to grayscale
    - Increases contrast
    - Applies subtle sharpening and thresholding to denoise
    """
    img = Image.open(io.BytesIO(image_bytes))
    
    # 1. Convert to Grayscale
    img = img.convert('L')
    
    # 2. Enhance Contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # 3. Apply subtle denoising / smoothing
    img = img.filter(ImageFilter.SMOOTH_MORE)
    
    return img

def extract_text_pytesseract(img: Image.Image) -> Tuple[str, float]:
    """
    Extracts text using PyTesseract.
    Returns: (text, confidence)
    """
    if not HAS_PYTESSERACT:
        raise RuntimeError("PyTesseract is not available.")
        
    try:
        # Check if tesseract binary actually runs
        version = pytesseract.get_tesseract_version()
        logger.info(f"Running Tesseract version {version}")
    except Exception as e:
        raise RuntimeError(f"Tesseract binary is not installed or not in PATH: {str(e)}")
        
    # Get detailed OCR data including confidence scores
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    # Extract text content and calculate average confidence
    text_blocks = []
    confidences = []
    
    for i in range(len(data['text'])):
        word = data['text'][i].strip()
        conf = float(data['conf'][i])
        
        if word:
            text_blocks.append(word)
            # Filter out -1 confidence which represents layout blocks, not text
            if conf >= 0:
                confidences.append(conf)
                
    text = " ".join(text_blocks)
    avg_conf = (sum(confidences) / len(confidences)) / 100.0 if confidences else 0.0
    return text, avg_conf

def extract_text_easyocr(image_bytes: bytes) -> Tuple[str, float]:
    """
    Extracts text using EasyOCR (which runs natively in Python without requiring system binaries).
    Returns: (text, confidence)
    """
    if not HAS_EASYOCR:
        raise RuntimeError("EasyOCR is not available.")
        
    # EasyOCR reader initialization (uses English by default)
    # Note: GPU=False is safer for local sandbox instances without CUDA configured
    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_bytes)
    
    text_blocks = []
    confidences = []
    
    for bbox, text, conf in results:
        text_blocks.append(text)
        confidences.append(conf)
        
    text = " ".join(text_blocks)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return text, avg_conf

def parse_clinical_keywords(text: str) -> Dict[str, Any]:
    """
    Uses Regular Expressions and Semantic Rules to parse clinical keywords out of the OCR text.
    Maps findings to database schema fields.
    """
    text_lower = text.lower()
    profile = {
        "name": "Extracted Patient",
        "age": 30, # Default values
        "gender": "Unknown",
        "dietary_habits": "Vegetarian", # Default
        "meal_frequency": 3,
        "bowel_movements": "Regular",
        "water_intake_liters": 2.0,
        "appetite_level": "Samagni",
        "current_dosha_imbalance": {"vata": 0.33, "pitta": 0.33, "kapha": 0.33},
        "extracted_raw_text": text
    }
    
    # 1. Parse Age
    age_match = re.search(r'\b(?:age|yr|yrs|years?|old)[:\s-]*(\d{1,2})\b', text_lower)
    if age_match:
        profile["age"] = int(age_match.group(1))
    else:
        # Fallback regex for standalone numbers that could be age (e.g., "M / 42" or "F 42")
        age_match_fallback = re.search(r'\b[mf]/[:\s-]*(\d{1,2})\b', text_lower)
        if age_match_fallback:
            profile["age"] = int(age_match_fallback.group(1))

    # 2. Parse Gender
    if re.search(r'\b(?:male|man|m)\b', text_lower):
        profile["gender"] = "Male"
    elif re.search(r'\b(?:female|woman|f)\b', text_lower):
        profile["gender"] = "Female"

    # 3. Parse Bowel Movements
    if any(kw in text_lower for kw in ["constipation", "constipated", "hard stool", "krura", "dry stool", "hard bowel"]):
        profile["bowel_movements"] = "Krura (Hard/Constipated)"
    elif any(kw in text_lower for kw in ["loose", "diarrhea", "watery stool", "mridu", "soft stool"]):
        profile["bowel_movements"] = "Mridu (Soft/Loose)"
    elif any(kw in text_lower for kw in ["variable", "irregular", "vishama", "gas"]):
        profile["bowel_movements"] = "Vishamagni (Variable)"
    elif any(kw in text_lower for kw in ["regular", "normal", "madhyama", "daily stool"]):
        profile["bowel_movements"] = "Madhyama (Regular)"

    # 4. Parse Appetite / Agni
    if any(kw in text_lower for kw in ["low agni", "mandagni", "poor appetite", "sluggish digestion", "indigestion"]):
        profile["appetite_level"] = "Mandagni (Low)"
    elif any(kw in text_lower for kw in ["high agni", "tikshnagni", "sharp appetite", "acidity", "heartburn", "hyperactive"]):
        profile["appetite_level"] = "Tikshnagni (High)"
    elif any(kw in text_lower for kw in ["variable agni", "vishamagni", "irregular hunger", "gas", "bloating"]):
        profile["appetite_level"] = "Vishamagni (Variable)"
    elif any(kw in text_lower for kw in ["balanced agni", "samagni", "good appetite", "normal digestion"]):
        profile["appetite_level"] = "Samagni (Balanced)"

    # 5. Parse Dietary Habits
    if any(kw in text_lower for kw in ["vegan"]):
        profile["dietary_habits"] = "Vegan"
    elif any(kw in text_lower for kw in ["non-veg", "meat", "chicken", "fish"]):
        profile["dietary_habits"] = "Non-Vegetarian"
    elif any(kw in text_lower for kw in ["veg", "vegetarian", "sattvic", "satvic"]):
        profile["dietary_habits"] = "Vegetarian"

    # 6. Parse Dosha imbalances
    # We look for keywords and score them.
    vata_score = 0.33
    pitta_score = 0.33
    kapha_score = 0.33
    
    # Vata signs: dry skin, bloating, anxiety, insomnia, joints, pain
    vata_kws = ["vata", "dryness", "bloating", "constipation", "anxiety", "insomnia", "joints pain", "cold hands", "thin build"]
    # Pitta signs: pitta, burning, acidity, hot, rash, anger, red eyes, inflammation
    pitta_kws = ["pitta", "burning", "acidity", "heat", "inflammation", "rash", "anger", "sweating", "acne", "ushna"]
    # Kapha signs: kapha, heavy, mucus, congestion, sleepiness, weight gain, lazy, lethargy
    kapha_kws = ["kapha", "heaviness", "mucus", "congestion", "lethargy", "sluggish", "water retention", "excess sleep"]
    
    for kw in vata_kws:
        if kw in text_lower:
            vata_score += 0.2
    for kw in pitta_kws:
        if kw in text_lower:
            pitta_score += 0.2
    for kw in kapha_kws:
        if kw in text_lower:
            kapha_score += 0.2
            
    # Normalize scores so they sum to 1.0 (imbalance percentages)
    total_score = vata_score + pitta_score + kapha_score
    profile["current_dosha_imbalance"] = {
        "vata": round(vata_score / total_score, 2),
        "pitta": round(pitta_score / total_score, 2),
        "kapha": round(kapha_score / total_score, 2)
    }
    
    # 7. Extract Specific Ayurvedic Base Meals (added to patient record tags or notes)
    meals_found = []
    base_meals = ["khichdi", "kitchari", "moong dal", "ghee", "basmati", "buttermilk", "takra", "ginger tea"]
    for meal in base_meals:
        if meal in text_lower:
            meals_found.append(meal.title())
    profile["extracted_meals"] = meals_found
    
    return profile

def process_prescription_ocr(image_bytes: bytes) -> Dict[str, Any]:
    """
    Main OCR pipeline coordinator:
    1. Preprocesses the image bytes to increase contrast and denoise.
    2. Tries PyTesseract first for fast extraction.
    3. Falls back to EasyOCR if Tesseract is not configured or throws an error.
    4. Evaluates extracted text confidence to detect blurred/unreadable documents.
    5. Parses keywords using regex rules.
    """
    text = ""
    confidence = 0.0
    ocr_method = "None"
    
    # Check if empty image
    if not image_bytes:
        return {
            "status": "Error",
            "message": "Empty file uploaded.",
            "data": None
        }
        
    # Attempt OCR Method 1: PyTesseract
    if HAS_PYTESSERACT:
        try:
            logger.info("Attempting PyTesseract OCR...")
            preprocessed_img = preprocess_image(image_bytes)
            text, confidence = extract_text_pytesseract(preprocessed_img)
            ocr_method = "PyTesseract"
            logger.info(f"PyTesseract OCR succeeded. Confidence: {confidence:.2f}")
        except Exception as e:
            logger.warning(f"PyTesseract OCR failed: {str(e)}. Falling back to EasyOCR...")
            
    # Attempt OCR Method 2: EasyOCR (if PyTesseract failed or was unavailable)
    if not text and HAS_EASYOCR:
        try:
            logger.info("Attempting EasyOCR...")
            text, confidence = extract_text_easyocr(image_bytes)
            ocr_method = "EasyOCR"
            logger.info(f"EasyOCR succeeded. Confidence: {confidence:.2f}")
        except Exception as e:
            logger.error(f"EasyOCR also failed: {str(e)}")
            
    # If no OCR tool was successful or text is completely empty
    if not text.strip():
        # Let's check if the image has content by reading it
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # If we open it, return a specialized error
            return {
                "status": "Unreadable",
                "message": "Image text is unreadable or blurry. Please upload a clearer high-contrast prescription.",
                "confidence": 0.0,
                "data": None
            }
        except Exception:
            return {
                "status": "Error",
                "message": "Invalid image file format. Please upload a valid JPEG, PNG, or WebP image.",
                "data": None
            }
            
    # 3. Error Handling for Blurry / Low Confidence results
    # If confidence is extremely low (e.g. less than 35% on PyTesseract, or less than 20% on EasyOCR)
    # we classify it as potentially blurry or unreadable, but we still parse what we can and return a warning.
    threshold = 0.35 if ocr_method == "PyTesseract" else 0.20
    is_blurry = confidence < threshold
    
    # 4. Parse clinical findings
    parsed_data = parse_clinical_keywords(text)
    
    if is_blurry:
        return {
            "status": "Warning",
            "message": "Text extraction confidence is low. Image may be blurred or contains handwriting that is difficult to decipher. Please verify the parsed fields manually.",
            "confidence": round(confidence, 2),
            "ocr_method": ocr_method,
            "data": parsed_data
        }
        
    return {
        "status": "Success",
        "message": "Text successfully extracted and parsed.",
        "confidence": round(confidence, 2),
        "ocr_method": ocr_method,
        "data": parsed_data
    }
