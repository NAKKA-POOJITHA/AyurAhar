# Verification Script for AyurAhar Python Backend Components
import sys
import os

# Add parent directory of backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimizer import solve_meal_plan
from ocr import parse_clinical_keywords, process_prescription_ocr
from nlp import find_smart_substitutes

# Sample dataset matching database structure
MOCK_FOODS = [
    {
        "id": "f_1",
        "name": "Standard Boiled Basmati Rice",
        "category": "Grain",
        "calories": 130.0,
        "protein_g": 2.7,
        "carbs_g": 28.0,
        "fats_g": 0.3,
        "rasa": ["Sweet"],
        "virya": "Shita",
        "guna": ["Laghu", "Snigdha"],
        "vipaka": "Madhura",
        "dosha_effects": {"vata": -1, "pitta": -1, "kapha": 1},
        "embedding": [0.1] * 384
    },
    {
        "id": "f_2",
        "name": "Standard Cooked with Spices Brown Rice",
        "category": "Grain",
        "calories": 111.0,
        "protein_g": 2.6,
        "carbs_g": 23.0,
        "fats_g": 0.9,
        "rasa": ["Sweet", "Pungent"],
        "virya": "Ushna",
        "guna": ["Guru", "Ruksha"],
        "vipaka": "Madhura",
        "dosha_effects": {"vata": 0, "pitta": 1, "kapha": -1},
        "embedding": [0.05] * 384
    },
    {
        "id": "f_3",
        "name": "Satvic Ghee",
        "category": "Fat",
        "calories": 884.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fats_g": 100.0,
        "rasa": ["Sweet"],
        "virya": "Shita",
        "guna": ["Guru", "Snigdha"],
        "vipaka": "Madhura",
        "dosha_effects": {"vata": -1, "pitta": -1, "kapha": 1},
        "embedding": [0.2] * 384
    },
    {
        "id": "f_4",
        "name": "Standard Cooked Spiced Moong Dal",
        "category": "Legume",
        "calories": 105.0,
        "protein_g": 7.0,
        "carbs_g": 19.0,
        "fats_g": 0.4,
        "rasa": ["Sweet", "Astringent", "Pungent"],
        "virya": "Shita",
        "guna": ["Laghu", "Ruksha"],
        "vipaka": "Madhura",
        "dosha_effects": {"vata": 1, "pitta": -1, "kapha": -1},
        "embedding": [0.12] * 384
    }
]

def run_tests():
    print("==================================================")
    print("[TEST] RUNNING AYURAHAR BACKEND VERIFICATION TESTS")
    print("==================================================")
    
    # --------------------------------------------------
    # TEST 1: LP Solver Ayurvedic Contraindications
    # --------------------------------------------------
    print("\n[Test 1] Verifying LP Solver Hard Constraints...")
    
    # Scenario A: Patient with High Pitta (imbalance = 0.8)
    # The solver MUST exclude "Brown Rice" because its Virya is "Ushna" (heating)
    high_pitta_profile = {
        "name": "Test Pitta",
        "age": 30,
        "gender": "Female",
        "dietary_habits": "Vegetarian",
        "appetite_level": "Samagni",
        "current_dosha_imbalance": {"vata": 0.1, "pitta": 0.8, "kapha": 0.1}
    }
    
    result_pitta = solve_meal_plan(
        food_items=MOCK_FOODS,
        patient_profile=high_pitta_profile,
        target_calories=500,
        target_protein=15,
        target_carbs=80,
        target_fats=10
    )
    
    # Assert exclusions list contains Brown Rice due to heating potency
    excluded_names = [e["name"] for e in result_pitta.get("exclusions_sample", [])]
    print(f"-> High Pitta Exclusions: {excluded_names}")
    assert "Standard Cooked with Spices Brown Rice" in excluded_names, "Brown Rice (Ushna) must be excluded for high Pitta!"
    print("[OK] Ushna (heating) exclusion constraint passed.")
    
    # Scenario B: Patient with Low digestive Agni (Mandagni)
    # The solver MUST exclude "Ghee" because its Guna has "Guru" (heavy digestibility)
    low_agni_profile = {
        "name": "Test Agni",
        "age": 45,
        "gender": "Male",
        "dietary_habits": "Vegetarian",
        "appetite_level": "Mandagni",
        "current_dosha_imbalance": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}
    }
    
    result_agni = solve_meal_plan(
        food_items=MOCK_FOODS,
        patient_profile=low_agni_profile,
        target_calories=500,
        target_protein=15,
        target_carbs=80,
        target_fats=10
    )
    
    excluded_agni_names = [e["name"] for e in result_agni.get("exclusions_sample", [])]
    print(f"-> Low Agni Exclusions: {excluded_agni_names}")
    assert "Satvic Ghee" in excluded_agni_names or "Standard Cooked with Spices Brown Rice" in excluded_agni_names, "Guru (heavy) foods must be excluded for low Agni!"
    print("[OK] Guru (heavy) exclusion constraint passed.")
    
    # --------------------------------------------------
    # TEST 2: OCR Prescription Keyword Parsing
    # --------------------------------------------------
    print("\n[Test 2] Verifying OCR Clinical Keyword Parser...")
    
    # Simulate a handwritten note with specific keywords
    handwritten_note = (
        "Patient: John Doe, Age: 42, Male. Patient reports severe chronic constipation (hard stool) "
        "and sluggish poor digestion. Sluggish appetite (low agni) noticed. "
        "Aggravated Pitta symptoms (burning sensation in chest) but Vata is also very high. "
        "Recommend daily Khichdi and a warm cup of herbal tea."
    )
    
    parsed = parse_clinical_keywords(handwritten_note)
    
    print(f"-> Parsed Age: {parsed['age']}")
    print(f"-> Parsed Gender: {parsed['gender']}")
    print(f"-> Parsed Bowel Movements: {parsed['bowel_movements']}")
    print(f"-> Parsed Appetite: {parsed['appetite_level']}")
    print(f"-> Parsed Dosha Imbalances: {parsed['current_dosha_imbalance']}")
    print(f"-> Extracted Meals: {parsed['extracted_meals']}")
    
    assert parsed["age"] == 42, "Failed to parse Age 42."
    assert parsed["gender"] == "Male", "Failed to parse Gender Male."
    assert "Krura" in parsed["bowel_movements"] or "Hard" in parsed["bowel_movements"], "Failed to extract constipation bowel habit."
    assert "Low" in parsed["appetite_level"] or "Mandagni" in parsed["appetite_level"], "Failed to extract sluggish low agni."
    assert "Khichdi" in parsed["extracted_meals"], "Failed to extract standard meal block 'Khichdi'."
    
    print("[OK] OCR clinical keyword extraction logic passed.")
    
    # --------------------------------------------------
    # TEST 3: NLP Cosine Similarity Substitution
    # --------------------------------------------------
    print("\n[Test 3] Verifying NLP Cosine Similarity Substitution Search...")
    
    # Let's target Moong Dal (f_4) and find substitutes
    # The L2 normalized dot product is tested in finding replacements
    target = MOCK_FOODS[3] # Moong Dal
    candidates = MOCK_FOODS
    
    # We substitute f_4. Basmati Rice (f_1) should be closest because both have Shita virya, Laghu guna, Madhura vipaka.
    results = find_smart_substitutes(
        target_item=target,
        all_items=candidates,
        top_n=2
    )
    
    print(f"-> Best Substitute for {target['name']}:")
    for r in results:
        print(f"   Name: {r['name']} | Category: {r['category']} | Score: {r['similarity_score']}")
        
    assert len(results) > 0, "NLP substitution engine returned empty lists."
    assert results[0]["id"] == "f_1", "Basmati Rice should be the closest Ayurvedic match to Moong Dal in mock profile."
    print("[OK] Cosine-similarity recommendation algorithm passed.")
    
    print("\n==================================================")
    print("[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
