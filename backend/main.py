import os
import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Local imports
from db import get_db, init_db, FoodItem, PatientProfile
from optimizer import solve_meal_plan
from ocr import process_prescription_ocr
from nlp import find_smart_substitutes

# Initialize FastAPI app
app = FastAPI(
    title="AyurAhar API",
    description="Enterprise Ayurvedic Diet Management System Core Engine",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Automatic DB initialisation on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Pydantic Schemas
class DoshaMap(BaseModel):
    vata: float = Field(..., ge=0.0, le=1.0)
    pitta: float = Field(..., ge=0.0, le=1.0)
    kapha: float = Field(..., ge=0.0, le=1.0)

class PatientProfileCreate(BaseModel):
    name: str
    age: int
    gender: str
    dietary_habits: str
    meal_frequency: int = 3
    bowel_movements: str
    water_intake_liters: float
    appetite_level: str
    current_dosha_imbalance: DoshaMap

class OptimizeMealRequest(BaseModel):
    patient_profile: PatientProfileCreate
    target_calories: float = Field(2000.0, gt=0)
    target_protein: float = Field(70.0, gt=0)
    target_carbs: float = Field(250.0, gt=0)
    target_fats: float = Field(60.0, gt=0)

class SubstituteRequest(BaseModel):
    food_id: str
    cuisine_preference: Optional[str] = None
    top_n: Optional[int] = 5

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the AyurAhar Core Engine API", "status": "Online"}

@app.get("/api/v1/food-items")
def list_food_items(
    category: Optional[str] = None,
    virya: Optional[str] = None,
    vipaka: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Lists food items with pagination and filters (category, virya, vipaka, search keyword).
    """
    query = db.query(FoodItem)
    if category:
        query = query.filter(FoodItem.category == category)
    if virya:
        query = query.filter(FoodItem.virya == virya)
    if vipaka:
        query = query.filter(FoodItem.vipaka == vipaka)
    if search:
        query = query.filter(FoodItem.name.like(f"%{search}%"))
        
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": i.id,
                "name": i.name,
                "category": i.category,
                "calories": i.calories,
                "protein_g": i.protein_g,
                "carbs_g": i.carbs_g,
                "fats_g": i.fats_g,
                "rasa": i.rasa,
                "virya": i.virya,
                "guna": i.guna,
                "vipaka": i.vipaka,
                "dosha_effects": i.dosha_effects,
                "seasons": i.seasons
            } for i in items
        ]
    }

@app.post("/api/v1/patients")
def create_patient_profile(profile: PatientProfileCreate, db: Session = Depends(get_db)):
    """
    Creates a new patient profile records.
    """
    patient_id = f"pat_{uuid.uuid4().hex[:8]}"
    db_profile = PatientProfile(
        id=patient_id,
        name=profile.name,
        age=profile.age,
        gender=profile.gender,
        dietary_habits=profile.dietary_habits,
        meal_frequency=profile.meal_frequency,
        bowel_movements=profile.bowel_movements,
        water_intake_liters=profile.water_intake_liters,
        appetite_level=profile.appetite_level,
        current_dosha_imbalance=profile.current_dosha_imbalance.model_dump()
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return {"status": "Success", "patient_id": db_profile.id, "profile": profile}

@app.post("/api/v1/optimize-meal")
def optimize_meal_endpoint(req: OptimizeMealRequest, db: Session = Depends(get_db)):
    """
    Core AI Meal Optimizer. Retrieves the food items list, runs linear programming constraints solver,
    and returns a balanced Ayurvedic diet profile matching macro targets.
    """
    # Fetch all foods in database (8,000+ items)
    foods = db.query(FoodItem).all()
    food_list = []
    for f in foods:
        food_list.append({
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "calories": f.calories,
            "protein_g": f.protein_g,
            "carbs_g": f.carbs_g,
            "fats_g": f.fats_g,
            "rasa": f.rasa,
            "virya": f.virya,
            "guna": f.guna,
            "vipaka": f.vipaka,
            "dosha_effects": f.dosha_effects
        })
        
    result = solve_meal_plan(
        food_items=food_list,
        patient_profile=req.patient_profile.model_dump(),
        target_calories=req.target_calories,
        target_protein=req.target_protein,
        target_carbs=req.target_carbs,
        target_fats=req.target_fats
    )
    
    if result["status"] == "Failed" or result["status"] == "Infeasible":
        raise HTTPException(status_code=400, detail=result)
        
    return result

@app.post("/api/v1/ocr/upload-prescription")
async def upload_prescription_endpoint(file: UploadFile = File(...)):
    """
    Accepts image files of handwritten diet notes, runs the computer vision extraction,
    and returns structured profile attributes for pre-populating patient forms.
    """
    contents = await file.read()
    
    # Run OCR Pipeline
    ocr_result = process_prescription_ocr(contents)
    
    if ocr_result["status"] == "Error":
        raise HTTPException(status_code=400, detail=ocr_result["message"])
        
    return ocr_result

@app.post("/api/v1/substitute")
def smart_substitution_endpoint(req: SubstituteRequest, db: Session = Depends(get_db)):
    """
    NLP Smart Substitution Engine. Computes cosine similarity of multi-dimensional food embeddings
    to recommend alternate dishes holding matching biochemical and Ayurvedic profiles.
    """
    # Fetch target food item
    target = db.query(FoodItem).filter(FoodItem.id == req.food_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target food item not found.")
        
    target_dict = {
        "id": target.id,
        "name": target.name,
        "category": target.category,
        "embedding": target.embedding
    }
    
    # Fetch candidate items
    candidates = db.query(FoodItem).all()
    candidate_list = []
    for c in candidates:
        candidate_list.append({
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "calories": c.calories,
            "protein_g": c.protein_g,
            "carbs_g": c.carbs_g,
            "fats_g": c.fats_g,
            "rasa": c.rasa,
            "virya": c.virya,
            "guna": c.guna,
            "vipaka": c.vipaka,
            "dosha_effects": c.dosha_effects,
            "embedding": c.embedding
        })
        
    substitutes = find_smart_substitutes(
        target_item=target_dict,
        all_items=candidate_list,
        top_n=req.top_n,
        cuisine_pref=req.cuisine_preference
    )
    
    return {
        "target_item": {
            "id": target.id,
            "name": target.name,
            "category": target.category,
            "calories": target.calories,
            "protein_g": target.protein_g,
            "carbs_g": target.carbs_g,
            "fats_g": target.fats_g,
            "ayurvedic": {
                "rasa": target.rasa,
                "virya": target.virya,
                "guna": target.guna,
                "vipaka": target.vipaka
            }
        },
        "substitutes": substitutes
    }
