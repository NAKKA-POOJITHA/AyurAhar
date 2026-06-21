-- PostgreSQL DDL Script for AyurAhar (Ayurvedic Diet Management System)
-- Optimized for Fast Spatiotemporal and Bio-characteristic Filtering

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector; -- Support for pgvector similarity search

-- 2. Create Custom Domains/Enum Types (Optional, standard tables are safer for extension compatibility)
-- We will use VARCHAR/TEXT with CHECK constraints or standard lookups to maximize performance and flexibility.

-- 3. Create FoodItems Table (Dynamic Database of 8,000+ items across dual-matrix)
CREATE TABLE IF NOT EXISTS food_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL, -- e.g., grain, legume, vegetable, fruit, spice, dairy
    
    -- Dual-Matrix 1: Modern Nutrition Profile
    calories NUMERIC(8, 2) NOT NULL CHECK (calories >= 0),
    protein_g NUMERIC(6, 2) NOT NULL CHECK (protein_g >= 0),
    carbs_g NUMERIC(6, 2) NOT NULL CHECK (carbs_g >= 0),
    fats_g NUMERIC(6, 2) NOT NULL CHECK (fats_g >= 0),
    micronutrients JSONB NOT NULL DEFAULT '{}'::jsonb, -- e.g., {"iron_mg": 2.7, "calcium_mg": 120, "vitamin_c_mg": 90}
    
    -- Dual-Matrix 2: Ayurvedic Bio-Characteristics
    rasa VARCHAR(50)[] NOT NULL, -- Tastes: Sweet (Madhura), Sour (Amla), Salty (Lavana), Pungent (Katu), Bitter (Tikta), Astringent (Kashaya)
    virya VARCHAR(50) NOT NULL CHECK (virya IN ('Ushna', 'Shita')), -- Ushna (Heating) or Shita (Cooling)
    guna VARCHAR(50)[] NOT NULL, -- Digestibility properties: e.g., Guru (Heavy), Laghu (Light), Snigdha (Oily), Ruksha (Dry), Tikshna (Sharp), Manda (Dull)
    vipaka VARCHAR(50) NOT NULL CHECK (vipaka IN ('Madhura', 'Amla', 'Katu')), -- Post-digestive taste: Madhura (Sweet), Amla (Sour), Katu (Pungent)
    dosha_effects JSONB NOT NULL DEFAULT '{}'::jsonb, -- Modifications map: {"vata": -1, "pitta": 1, "kapha": 0} (Aggravates: 1, Pacifies: -1, Neutral: 0)
    
    -- Spatiotemporal & Seasonal Attributes
    seasons VARCHAR(50)[] NOT NULL, -- Seasonal suitability: e.g., {"Grishma", "Varsha", "Sharad", "Hemanta", "Shishira", "Vasanta"}
    origin_coordinates GEOGRAPHY(Point, 4326), -- Spatial location (longitude, latitude) of primary availability/origin
    
    -- NLP/ML Semantic Fingerprint Vector
    embedding VECTOR(384), -- 384-dimension vector embedding of textual + bio-characteristic fingerprint
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create PatientProfiles Table
CREATE TABLE IF NOT EXISTS patient_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0 AND age < 150),
    gender VARCHAR(50) NOT NULL,
    dietary_habits VARCHAR(100) NOT NULL, -- e.g., Vegetarian, Vegan, Pescatarian, Non-Vegetarian
    meal_frequency INTEGER NOT NULL DEFAULT 3 CHECK (meal_frequency > 0),
    bowel_movements VARCHAR(100) NOT NULL, -- e.g., Krura (Hard/Constipated), Mridu (Soft/Loose), Madhyama (Regular), Vishama (Variable)
    water_intake_liters NUMERIC(4, 2) NOT NULL CHECK (water_intake_liters >= 0),
    appetite_level VARCHAR(100) NOT NULL, -- Agni level: Mandagni (Low), Tikshnagni (High), Vishamagni (Variable), Samagni (Balanced)
    current_dosha_imbalance JSONB NOT NULL DEFAULT '{}'::jsonb, -- e.g., {"vata": 0.6, "pitta": 0.8, "kapha": 0.2}
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Indexes Optimization for Fast Filtering on Spatiotemporal and Bio-characteristic Queries

-- Index A: Array-based GIN indexing for Ayurvedic tastes (Rasa) and properties (Guna)
-- Crucial for fast query execution: `rasa @> ARRAY['Bitter']`
CREATE INDEX idx_food_items_rasa ON food_items USING GIN (rasa);
CREATE INDEX idx_food_items_guna ON food_items USING GIN (guna);

-- Index B: JSONB GIN indexing for dosha effects modification maps
-- Enables sub-millisecond lookups on specific dosha modifiers, e.g., `dosha_effects->>'pitta' = '1'`
CREATE INDEX idx_food_items_dosha_effects ON food_items USING GIN (dosha_effects);

-- Index C: Spatiotemporal Spatial Index (GiST) on origin coordinates
-- Supports extremely fast distance checks and geospatial boundaries using PostGIS ST_DWithin or ST_Contains
CREATE INDEX idx_food_items_origin_spatial ON food_items USING GIST (origin_coordinates);

-- Index D: Temporal/Seasonal suitability Index (GIN)
-- Optimizes retrieval of foods recommended for specific seasons, e.g., `seasons @> ARRAY['Grishma']`
CREATE INDEX idx_food_items_seasons ON food_items USING GIN (seasons);

-- Index E: B-Tree Index on Virya and Vipaka (Scalar bio-characteristics)
-- Speeds up queries filters like `virya = 'Shita' AND vipaka = 'Madhura'`
CREATE INDEX idx_food_items_virya ON food_items (virya);
CREATE INDEX idx_food_items_vipaka ON food_items (vipaka);

-- Index F: pgvector HNSW Index for Semantic Cosine Similarity
-- Optimized index for vector similarity searches: `SELECT * FROM food_items ORDER BY embedding <=> :input_vector LIMIT 5;`
-- Note: M=16, ef_construction=64 are common balanced parameters.
CREATE INDEX idx_food_items_embedding_hnsw ON food_items USING HNSW (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Index G: B-Tree Index on Modern Nutrition Macros
-- Accelerates queries containing numeric constraints like: `protein_g >= 10 AND calories <= 500`
CREATE INDEX idx_food_items_macros ON food_items (calories, protein_g, carbs_g, fats_g);

-- Index H: Patient Profiles Search Index
-- Optimizes profiles tracking and retrieval
CREATE INDEX idx_patient_profiles_lookup ON patient_profiles (age, gender);
CREATE INDEX idx_patient_profiles_dosha_gin ON patient_profiles USING GIN (current_dosha_imbalance);
