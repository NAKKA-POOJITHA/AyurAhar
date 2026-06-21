import os
import random
import json
import numpy as np
from sqlalchemy import create_engine, Column, String, Integer, Float, JSON, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Database Connection Configuration
# We support PostgreSQL via environment variable, otherwise fall back to a local SQLite database for easy local testing.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ayurahar.db")

# SQLite connection adjustments for thread compatibility
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Database Models
class FoodItem(Base):
    __tablename__ = "food_items"
    
    # We use String for ID to support both UUID strings (Postgres) and standard text IDs (SQLite)
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    
    # Modern Nutrition
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fats_g = Column(Float, nullable=False)
    micronutrients = Column(JSON, nullable=False, default=dict) # JSONB in Postgres, JSON in SQLite
    
    # Ayurvedic Bio-Characteristics
    # SQLite doesn't natively support arrays, so we store arrays as JSON in SQLite, and ARRAY in Postgres.
    # To maintain database portability, we use JSON column for rasa/guna/seasons, or a string-serialized list.
    # Storing as JSON in SQLite is extremely clean and transparent.
    rasa = Column(JSON, nullable=False) # List of tastes: Sweet, Sour, Salty, Pungent, Bitter, Astringent
    virya = Column(String, nullable=False) # Ushna (Heating) or Shita (Cooling)
    guna = Column(JSON, nullable=False) # List of qualities: Guru, Laghu, Snigdha, Ruksha, etc.
    vipaka = Column(String, nullable=False) # Madhura (Sweet), Amla (Sour), Katu (Pungent)
    dosha_effects = Column(JSON, nullable=False, default=dict) # {"vata": -1, "pitta": 1, "kapha": 0}
    
    # Spatiotemporal suitability
    seasons = Column(JSON, nullable=False) # e.g., ["Summer", "Winter"]
    origin_latitude = Column(Float, nullable=True) # Fallback float coordinates for SQLite compatibility
    origin_longitude = Column(Float, nullable=True)
    
    # NLP Vector Embedding
    # Vector embedding serialized as JSON float list for portability across SQLite and Postgres.
    # When querying Postgres, we can map this to pgvector. Locally, we compute cosine similarity using numpy.
    embedding = Column(JSON, nullable=True) 

class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    dietary_habits = Column(String, nullable=False) # e.g., Vegetarian, Vegan, Non-Vegetarian
    meal_frequency = Column(Integer, nullable=False, default=3)
    bowel_movements = Column(String, nullable=False) # e.g., Hard, Soft, Regular
    water_intake_liters = Column(Float, nullable=False)
    appetite_level = Column(String, nullable=False) # e.g. Mandagni, Tikshnagni, Vishamagni, Samagni
    current_dosha_imbalance = Column(JSON, nullable=False, default=dict) # {"vata": 0.5, "pitta": 0.8, "kapha": 0.3}

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Dynamic Mock Database Generator (Generates 8,000+ items)
def init_db():
    Base.metadata.create_base_all = Base.metadata.create_all(engine)
    db = SessionLocal()
    
    # Check if we already have items to avoid double generation
    if db.query(FoodItem).count() > 0:
        db.close()
        return
        
    print("Initializing database and generating 8,000+ Ayurvedic food items...")
    
    # Define foundational Ayurvedic food materials
    base_foods = [
        # Grains
        {"name": "Basmati Rice", "category": "Grain", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Laghu", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": -1, "kapha": 1}, "cal": 130, "prot": 2.7, "carb": 28.0, "fat": 0.3, "micro": {"iron_mg": 0.2, "calcium_mg": 10.0, "zinc_mg": 0.4}},
        {"name": "Brown Rice", "category": "Grain", "rasa": ["Sweet"], "virya": "Ushna", "guna": ["Guru", "Ruksha"], "vipaka": "Madhura", "dosha": {"vata": 0, "pitta": 1, "kapha": -1}, "cal": 111, "prot": 2.6, "carb": 23.0, "fat": 0.9, "micro": {"iron_mg": 0.4, "calcium_mg": 10.0, "magnesium_mg": 43.0}},
        {"name": "Barley", "category": "Grain", "rasa": ["Sweet", "Astringent"], "virya": "Shita", "guna": ["Laghu", "Ruksha"], "vipaka": "Madhura", "dosha": {"vata": 1, "pitta": -1, "kapha": -1}, "cal": 354, "prot": 12.5, "carb": 73.5, "fat": 2.3, "micro": {"iron_mg": 3.6, "calcium_mg": 33.0, "potassium_mg": 452.0}},
        {"name": "Quinoa", "category": "Grain", "rasa": ["Sweet", "Bitter"], "virya": "Ushna", "guna": ["Laghu", "Ruksha"], "vipaka": "Katu", "dosha": {"vata": 0, "pitta": 1, "kapha": -1}, "cal": 120, "prot": 4.4, "carb": 21.3, "fat": 1.9, "micro": {"iron_mg": 1.5, "calcium_mg": 17.0, "folate_mcg": 42.0}},
        {"name": "Oats", "category": "Grain", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": 0, "kapha": 1}, "cal": 389, "prot": 16.9, "carb": 66.3, "fat": 6.9, "micro": {"iron_mg": 4.7, "calcium_mg": 54.0, "zinc_mg": 4.0}},
        
        # Legumes
        {"name": "Moong Dal", "category": "Legume", "rasa": ["Sweet", "Astringent"], "virya": "Shita", "guna": ["Laghu", "Ruksha"], "vipaka": "Madhura", "dosha": {"vata": 1, "pitta": -1, "kapha": -1}, "cal": 105, "prot": 7.0, "carb": 19.0, "fat": 0.4, "micro": {"iron_mg": 1.4, "calcium_mg": 27.0, "folate_mcg": 159.0}},
        {"name": "Red Lentils", "category": "Legume", "rasa": ["Sweet", "Astringent"], "virya": "Shita", "guna": ["Laghu", "Ruksha"], "vipaka": "Madhura", "dosha": {"vata": 1, "pitta": -1, "kapha": 0}, "cal": 116, "prot": 9.0, "carb": 20.0, "fat": 0.4, "micro": {"iron_mg": 3.3, "calcium_mg": 19.0, "potassium_mg": 369.0}},
        {"name": "Chickpeas", "category": "Legume", "rasa": ["Sweet", "Astringent"], "virya": "Shita", "guna": ["Guru", "Ruksha"], "vipaka": "Katu", "dosha": {"vata": 1, "pitta": 0, "kapha": -1}, "cal": 164, "prot": 8.9, "carb": 27.4, "fat": 2.6, "micro": {"iron_mg": 2.9, "calcium_mg": 49.0, "folate_mcg": 172.0}},
        {"name": "Urad Dal", "category": "Legume", "rasa": ["Sweet"], "virya": "Ushna", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": 1, "kapha": 1}, "cal": 341, "prot": 25.2, "carb": 58.9, "fat": 1.6, "micro": {"iron_mg": 7.5, "calcium_mg": 154.0, "magnesium_mg": 350.0}},
        
        # Dairy & Fats
        {"name": "Ghee", "category": "Fat", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": -1, "kapha": 1}, "cal": 884, "prot": 0.0, "carb": 0.0, "fat": 100.0, "micro": {"vitamin_a_mcg": 840.0, "vitamin_e_mg": 2.8}},
        {"name": "Cow Milk", "category": "Dairy", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": -1, "kapha": 1}, "cal": 61, "prot": 3.2, "carb": 4.8, "fat": 3.3, "micro": {"calcium_mg": 120.0, "vitamin_d_mcg": 1.2, "potassium_mg": 150.0}},
        {"name": "Yogurt", "category": "Dairy", "rasa": ["Sour"], "virya": "Ushna", "guna": ["Guru", "Snigdha"], "vipaka": "Amla", "dosha": {"vata": -1, "pitta": 1, "kapha": 1}, "cal": 63, "prot": 3.5, "carb": 4.7, "fat": 3.3, "micro": {"calcium_mg": 110.0, "potassium_mg": 141.0, "vitamin_b12_mcg": 0.4}},
        {"name": "Sesame Oil", "category": "Fat", "rasa": ["Sweet", "Bitter", "Astringent"], "virya": "Ushna", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": 1, "kapha": 0}, "cal": 884, "prot": 0.0, "carb": 0.0, "fat": 100.0, "micro": {"vitamin_e_mg": 1.4, "vitamin_k_mcg": 13.6}},
        {"name": "Coconut Oil", "category": "Fat", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": 1, "pitta": -1, "kapha": 1}, "cal": 862, "prot": 0.0, "carb": 0.0, "fat": 100.0, "micro": {"vitamin_e_mg": 0.1}},
        
        # Vegetables
        {"name": "Spinach", "category": "Vegetable", "rasa": ["Sweet", "Astringent"], "virya": "Shita", "guna": ["Laghu", "Ruksha"], "vipaka": "Katu", "dosha": {"vata": 1, "pitta": -1, "kapha": -1}, "cal": 23, "prot": 2.9, "carb": 3.6, "fat": 0.4, "micro": {"iron_mg": 2.7, "calcium_mg": 99.0, "vitamin_c_mg": 28.1, "vitamin_a_mcg": 469.0}},
        {"name": "Zucchini", "category": "Vegetable", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Laghu", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": 0, "pitta": -1, "kapha": 0}, "cal": 17, "prot": 1.2, "carb": 3.1, "fat": 0.3, "micro": {"iron_mg": 0.4, "calcium_mg": 16.0, "vitamin_c_mg": 17.9}},
        {"name": "Ginger", "category": "Spice", "rasa": ["Pungent"], "virya": "Ushna", "guna": ["Laghu", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": 0, "kapha": -1}, "cal": 80, "prot": 1.8, "carb": 17.8, "fat": 0.8, "micro": {"iron_mg": 0.6, "calcium_mg": 16.0, "potassium_mg": 415.0}},
        {"name": "Turmeric", "category": "Spice", "rasa": ["Pungent", "Bitter", "Astringent"], "virya": "Ushna", "guna": ["Laghu", "Ruksha"], "vipaka": "Katu", "dosha": {"vata": 0, "pitta": 1, "kapha": -1}, "cal": 312, "prot": 9.7, "carb": 67.1, "fat": 3.2, "micro": {"iron_mg": 55.0, "calcium_mg": 168.0, "magnesium_mg": 208.0}},
        {"name": "Bitter Gourd", "category": "Vegetable", "rasa": ["Bitter"], "virya": "Shita", "guna": ["Laghu", "Ruksha"], "vipaka": "Katu", "dosha": {"vata": 1, "pitta": -1, "kapha": -1}, "cal": 17, "prot": 1.0, "carb": 3.7, "fat": 0.2, "micro": {"iron_mg": 0.4, "calcium_mg": 19.0, "vitamin_c_mg": 84.0}},
        {"name": "Sweet Potato", "category": "Vegetable", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": -1, "kapha": 1}, "cal": 86, "prot": 1.6, "carb": 20.1, "fat": 0.1, "micro": {"iron_mg": 0.6, "calcium_mg": 30.0, "vitamin_a_mcg": 709.0, "vitamin_c_mg": 2.4}},
        
        # Fruits
        {"name": "Pomegranate", "category": "Fruit", "rasa": ["Sweet", "Sour", "Astringent"], "virya": "Shita", "guna": ["Laghu", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": -1, "kapha": 0}, "cal": 83, "prot": 1.7, "carb": 18.7, "fat": 1.2, "micro": {"iron_mg": 0.3, "calcium_mg": 10.0, "vitamin_c_mg": 10.2}},
        {"name": "Apple", "category": "Fruit", "rasa": ["Sweet", "Sour", "Astringent"], "virya": "Shita", "guna": ["Laghu", "Ruksha"], "vipaka": "Madhura", "dosha": {"vata": 1, "pitta": -1, "kapha": -1}, "cal": 52, "prot": 0.3, "carb": 13.8, "fat": 0.2, "micro": {"iron_mg": 0.1, "calcium_mg": 6.0, "vitamin_c_mg": 4.6}},
        {"name": "Date", "category": "Fruit", "rasa": ["Sweet"], "virya": "Shita", "guna": ["Guru", "Snigdha"], "vipaka": "Madhura", "dosha": {"vata": -1, "pitta": -1, "kapha": 1}, "cal": 282, "prot": 2.5, "carb": 75.0, "fat": 0.4, "micro": {"iron_mg": 1.0, "calcium_mg": 39.0, "potassium_mg": 656.0}}
    ]
    
    # Expansion parameters to generate 8,000+ items
    # 25 base items x 10 preparation styles x 16 regional/spice additions x 2 grades = 8000 items!
    prep_styles = [
        {"style": "Raw", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.0, "guna_add": ["Laghu", "Ruksha"]},
        {"style": "Boiled", "cal_mod": 0.9, "prot_mod": 0.9, "carb_mod": 0.9, "fat_mod": 0.8, "guna_add": ["Laghu", "Snigdha"]},
        {"style": "Steamed", "cal_mod": 0.95, "prot_mod": 0.95, "carb_mod": 0.95, "fat_mod": 0.9, "guna_add": ["Laghu"]},
        {"style": "Roasted", "cal_mod": 1.1, "prot_mod": 1.0, "carb_mod": 1.1, "fat_mod": 1.0, "guna_add": ["Laghu", "Ruksha"]},
        {"style": "Sautéed in Ghee", "cal_mod": 1.5, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 4.5, "guna_add": ["Guru", "Snigdha"], "dosha_mod": {"vata": -1, "pitta": -1, "kapha": 1}},
        {"style": "Cooked with Spices", "cal_mod": 1.05, "prot_mod": 1.0, "carb_mod": 1.05, "fat_mod": 1.1, "guna_add": ["Laghu", "Tikshna"], "virya_force": "Ushna"},
        {"style": "Baked", "cal_mod": 1.05, "prot_mod": 1.0, "carb_mod": 1.05, "fat_mod": 1.0, "guna_add": ["Guru", "Ruksha"]},
        {"style": "Deep Fried", "cal_mod": 2.5, "prot_mod": 0.8, "carb_mod": 1.2, "fat_mod": 15.0, "guna_add": ["Guru", "Snigdha"], "virya_force": "Ushna", "dosha_mod": {"vata": -1, "pitta": 1, "kapha": 1}},
        {"style": "Sprouted", "cal_mod": 0.85, "prot_mod": 1.2, "carb_mod": 0.8, "fat_mod": 0.9, "guna_add": ["Laghu"], "dosha_mod": {"vata": 1, "pitta": -1, "kapha": -1}},
        {"style": "Fermented", "cal_mod": 1.1, "prot_mod": 1.1, "carb_mod": 0.95, "fat_mod": 1.0, "guna_add": ["Laghu", "Tikshna"], "virya_force": "Ushna", "vipaka_force": "Amla", "dosha_mod": {"vata": -1, "pitta": 1, "kapha": 1}}
    ]
    
    variations = [
        {"name": "Standard", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.0, "season": "Sadharana"},
        {"name": "North Indian Style", "cal_mod": 1.2, "prot_mod": 1.0, "carb_mod": 1.1, "fat_mod": 1.5, "season": "Hemanta"},
        {"name": "South Indian Style", "cal_mod": 1.1, "prot_mod": 1.0, "carb_mod": 1.1, "fat_mod": 1.3, "season": "Grishma"},
        {"name": "Ayurvedic Detox Blend", "cal_mod": 0.9, "prot_mod": 1.0, "carb_mod": 0.9, "fat_mod": 0.8, "season": "Varsha"},
        {"name": "Pitta-Pacifying Blend", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.0, "season": "Grishma", "virya_force": "Shita"},
        {"name": "Vata-Pacifying Blend", "cal_mod": 1.1, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.4, "season": "Hemanta", "virya_force": "Ushna"},
        {"name": "Kapha-Pacifying Blend", "cal_mod": 0.85, "prot_mod": 1.0, "carb_mod": 0.9, "fat_mod": 0.6, "season": "Vasanta", "virya_force": "Ushna"},
        {"name": "Organic Wild Harvest", "cal_mod": 1.0, "prot_mod": 1.1, "carb_mod": 0.95, "fat_mod": 1.0, "season": "Sadharana"},
        {"name": "Himalayan Herbs Edition", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.0, "season": "Shishira"},
        {"name": "Kerala Coconut Blend", "cal_mod": 1.3, "prot_mod": 1.0, "carb_mod": 1.05, "fat_mod": 2.2, "season": "Sharad"},
        {"name": "Mediterranean Fusion", "cal_mod": 1.1, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.4, "season": "Grishma"},
        {"name": "East Asian Herbal Mix", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 0.95, "fat_mod": 0.9, "season": "Sharad"},
        {"name": "Western Macrobiotic", "cal_mod": 0.95, "prot_mod": 1.05, "carb_mod": 0.95, "fat_mod": 0.95, "season": "Sadharana"},
        {"name": "Satvic Kitchen Formula", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.1, "season": "Sadharana", "virya_force": "Shita"},
        {"name": "High Protein Version", "cal_mod": 1.05, "prot_mod": 1.6, "carb_mod": 0.9, "fat_mod": 1.0, "season": "Sadharana"},
        {"name": "Low Carb Version", "cal_mod": 0.8, "prot_mod": 1.2, "carb_mod": 0.5, "fat_mod": 1.3, "season": "Sadharana"}
    ]

    seasons_map = {
        "Grishma": ["Summer", "Late Spring"],
        "Varsha": ["Monsoon", "Rainy"],
        "Sharad": ["Autumn", "Fall"],
        "Hemanta": ["Early Winter"],
        "Shishira": ["Late Winter"],
        "Vasanta": ["Spring"],
        "Sadharana": ["Summer", "Monsoon", "Autumn", "Winter", "Spring"]
    }
    
    tastes_list = ["Sweet", "Sour", "Salty", "Pungent", "Bitter", "Astringent"]
    gunas_list = ["Guru", "Laghu", "Snigdha", "Ruksha", "Tikshna", "Manda"]
    
    # Generate 8,000+ items
    count = 0
    all_db_items = []
    
    # To hit 8,000+, we do: 23 base items * 10 preps * 16 vars * 2 portion-sizes = 7360.
    # Let's add a minor variation layer (size-grade: Standard / Large) to multiply by 2, yielding 14,720 items.
    portion_sizes = [
        {"label": "", "cal_mod": 1.0, "prot_mod": 1.0, "carb_mod": 1.0, "fat_mod": 1.0},
        {"label": " (Double Portion)", "cal_mod": 2.0, "prot_mod": 2.0, "carb_mod": 2.0, "fat_mod": 2.0}
    ]
    
    for base in base_foods:
        for prep in prep_styles:
            for var in variations:
                for portion in portion_sizes:
                    count += 1
                    
                    # Generate unique name
                    item_name = f"{var['name']} {prep['style']} {base['name']}{portion['label']}"
                    
                    # Modern nutrition modifications
                    cal = base["cal"] * prep["cal_mod"] * var["cal_mod"] * portion["cal_mod"]
                    prot = base["prot"] * prep["prot_mod"] * var["prot_mod"] * portion["prot_mod"]
                    carb = base["carb"] * prep["carb_mod"] * var["carb_mod"] * portion["carb_mod"]
                    fat = base["fat"] * prep["fat_mod"] * var["fat_mod"] * portion["fat_mod"]
                    
                    # Prevent zero calorie for grains/legumes/fats
                    if cal <= 0 and base["cal"] > 0:
                        cal = base["cal"]
                        
                    # Synthesis of micronutrients
                    micro = base["micro"].copy()
                    for k in micro:
                        micro[k] = round(micro[k] * prep["cal_mod"] * portion["cal_mod"], 2)
                        
                    # Ayurvedic bio-characteristics
                    virya = var.get("virya_force", prep.get("virya_force", base["virya"]))
                    vipaka = prep.get("vipaka_force", base["vipaka"])
                    
                    # Rasa (Tastes) union
                    rasa = base["rasa"].copy()
                    if prep["style"] == "Fermented" and "Sour" not in rasa:
                        rasa.append("Sour")
                    if prep["style"] == "Cooked with Spices" and "Pungent" not in rasa:
                        rasa.append("Pungent")
                        
                    # Guna (Qualities) union
                    guna = list(set(base["guna"] + prep["guna_add"]))
                    
                    # Dosha effects merge
                    dosha = base["dosha"].copy()
                    if "dosha_mod" in prep:
                        for d in dosha:
                            dosha[d] += prep["dosha_mod"].get(d, 0)
                    if "dosha_mod" in var:
                        for d in dosha:
                            dosha[d] += var["dosha_mod"].get(d, 0)
                    # Clip dosha effects to reasonable range [-2, 2]
                    for d in dosha:
                        dosha[d] = max(-2, min(2, dosha[d]))
                        
                    # Seasons mapping
                    season_group = var["season"]
                    seasons = seasons_map.get(season_group, ["Summer", "Autumn", "Winter", "Spring"])
                    
                    # Spatial Coordinates: centered in India (Lat 8.4 to 37.6, Lon 68.7 to 97.2)
                    lat = random.uniform(8.4, 37.6)
                    lon = random.uniform(68.7, 97.2)
                    
                    # Create 384-dimensional dense embedding based on properties
                    # We create a deterministic vector based on name + properties, and add minor noise
                    # Dimensions:
                    # 0-5: Rasa hot-encoding
                    # 6: Virya (-1 for cooling, +1 for heating)
                    # 7-12: Guna hot-encoding
                    # 13-15: Vipaka hot-encoding
                    # 16-18: Dosha effects (Vata, Pitta, Kapha)
                    # 19-22: Normalized nutrition (cal, prot, carb, fat)
                    # 23-383: Deterministic projection based on hash of name
                    emb = np.zeros(384)
                    
                    # Rasa indices
                    for t in rasa:
                        if t in tastes_list:
                            emb[tastes_list.index(t)] = 1.0
                    # Virya
                    emb[6] = 1.0 if virya == "Ushna" else -1.0
                    # Gunas
                    for g in guna:
                        if g in gunas_list:
                            emb[7 + gunas_list.index(g)] = 1.0
                    # Vipaka
                    vipaka_list = ["Madhura", "Amla", "Katu"]
                    if vipaka in vipaka_list:
                        emb[13 + vipaka_list.index(vipaka)] = 1.0
                    # Dosha
                    emb[16] = dosha.get("vata", 0.0)
                    emb[17] = dosha.get("pitta", 0.0)
                    emb[18] = dosha.get("kapha", 0.0)
                    # Nutrition normalized roughly
                    emb[19] = cal / 1000.0
                    emb[20] = prot / 100.0
                    emb[21] = carb / 100.0
                    emb[22] = fat / 100.0
                    
                    # Name projection for vocabulary diversity (hash based seeds)
                    random.seed(hash(item_name) % 1234567)
                    for idx in range(23, 384):
                        emb[idx] = random.uniform(-0.1, 0.1)
                        
                    # L2 Normalize the embedding to make cosine similarity simple dot-product
                    norm = np.linalg.norm(emb)
                    if norm > 0:
                        emb = emb / norm
                        
                    embedding_list = emb.tolist()
                    
                    food_item = FoodItem(
                        id=f"fi_{count}",
                        name=item_name,
                        category=base["category"],
                        calories=round(cal, 2),
                        protein_g=round(prot, 2),
                        carbs_g=round(carb, 2),
                        fats_g=round(fat, 2),
                        micronutrients=micro,
                        rasa=rasa,
                        virya=virya,
                        guna=guna,
                        vipaka=vipaka,
                        dosha_effects=dosha,
                        seasons=seasons,
                        origin_latitude=round(lat, 4),
                        origin_longitude=round(lon, 4),
                        embedding=embedding_list
                    )
                    all_db_items.append(food_item)
                    
                    if count >= 8200: # Ensure we cross 8,000+ items
                        break
                if count >= 8200:
                    break
            if count >= 8200:
                break
        if count >= 8200:
            break
            
    # Bulk save to DB
    print(f"Generated {len(all_db_items)} items. Inserting to database...")
    db.bulk_save_objects(all_db_items)
    db.commit()
    print("Database initialization complete!")
    db.close()

if __name__ == "__main__":
    init_db()
