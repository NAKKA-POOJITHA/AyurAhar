import numpy as np
from typing import List, Dict, Any, Optional

def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes the cosine similarity between two vectors.
    Since our embeddings are L2 normalized during generation, this simplifies
    to a simple dot product, which is extremely fast.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(np.dot(a, b) / (norm_a * norm_b))

def find_smart_substitutes(
    target_item: Dict[str, Any],
    all_items: List[Dict[str, Any]],
    top_n: int = 5,
    cuisine_pref: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Looks up the multi-dimensional fingerprint of a food item (its Rasa, Guna, Virya, Vipaka, and macro targets)
    and performs a cosine-similarity mathematical search across all database items to recommend alternative
    regional or international options that hold an identical biochemical and Ayurvedic property profile.
    
    Parameters:
    - target_item: Dict representing the food item to substitute.
    - all_items: List of all food items in the database.
    - top_n: Number of recommendations to return.
    - cuisine_pref: Filter to target a specific global cuisine style (e.g. "Mediterranean", "Western", "East Asian").
    """
    target_emb = target_item.get("embedding")
    if not target_emb:
        return []
        
    target_vector = np.array(target_emb)
    target_id = target_item.get("id")
    target_category = target_item.get("category")
    
    scored_items = []
    
    for item in all_items:
        # Exclude the item itself
        if item["id"] == target_id:
            continue
            
        item_emb = item.get("embedding")
        if not item_emb:
            continue
            
        item_vector = np.array(item_emb)
        
        # Calculate Cosine Similarity
        similarity = compute_cosine_similarity(target_emb, item_emb)
        
        # Apply weighting heuristics to enhance contextual relevance
        final_score = similarity
        
        # Heuristic 1: Prioritize same category (e.g. substitute grains for grains, fats for fats)
        if item["category"] == target_category:
            final_score += 0.05
            
        # Heuristic 2: Match client's global cuisine preference if specified
        # Standard names contain tags like "North Indian Style", "Mediterranean Fusion", "Western Macrobiotic", "East Asian"
        if cuisine_pref:
            pref_lower = cuisine_pref.lower()
            name_lower = item["name"].lower()
            
            # Boost score if item matches desired target cuisine
            if pref_lower in name_lower:
                final_score += 0.15
            # Penalize if it belongs to the target's original cuisine (e.g. trying to swap Indian for Global)
            elif "indian" in name_lower and pref_lower != "indian":
                final_score -= 0.05
                
        scored_items.append({
            "item": item,
            "score": final_score,
            "raw_similarity": similarity
        })
        
    # Sort items by similarity score in descending order
    scored_items.sort(key=lambda x: x["score"], reverse=True)
    
    # Format and return the top recommendations
    recommendations = []
    for entry in scored_items[:top_n]:
        item = entry["item"]
        recommendations.append({
            "id": item["id"],
            "name": item["name"],
            "category": item["category"],
            "calories": item["calories"],
            "protein_g": item["protein_g"],
            "carbs_g": item["carbs_g"],
            "fats_g": item["fats_g"],
            "ayurvedic": {
                "rasa": item["rasa"],
                "virya": item["virya"],
                "guna": item["guna"],
                "vipaka": item["vipaka"],
                "dosha_effects": item["dosha_effects"]
            },
            "similarity_score": round(entry["raw_similarity"], 4),
            "match_confidence": f"{round(entry['raw_similarity'] * 100, 1)}%"
        })
        
    return recommendations
