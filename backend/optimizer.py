import numpy as np
from scipy.optimize import linprog
from typing import List, Dict, Any, Tuple

def solve_meal_plan(
    food_items: List[Dict[str, Any]],
    patient_profile: Dict[str, Any],
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fats: float
) -> Dict[str, Any]:
    """
    Executes a Linear Programming Optimization Solver (via scipy.optimize.linprog)
    to find the perfect mix of ingredients that satisfies modern macronutrient targets
    while treating Ayurvedic bio-characteristic incompatibilities as hard constraints.
    
    Ayurvedic Rules implemented as Hard Filters:
    - High Pitta (imbalance > 0.5) -> Exclude all 'Ushna' (heating) foods.
    - Low Digestive Agni ('Mandagni') -> Exclude all 'Guru' (heavy) foods to prevent indigestion.
    - High Vata (imbalance > 0.5) -> Exclude all 'Ruksha' (dry) foods.
    - High Kapha (imbalance > 0.5) -> Exclude all 'Guru' (heavy) and 'Snigdha' (oily) foods.
    """
    # 1. Extract Patient Characteristics
    dosha_imbalance = patient_profile.get("current_dosha_imbalance", {})
    pitta_level = dosha_imbalance.get("pitta", 0.0)
    vata_level = dosha_imbalance.get("vata", 0.0)
    kapha_level = dosha_imbalance.get("kapha", 0.0)
    agni = patient_profile.get("appetite_level", "Samagni")
    
    # 2. Hard Ayurvedic Constraints Filtering
    filtered_items = []
    exclusions = []
    
    for item in food_items:
        exclude_item = False
        reasons = []
        
        # Rule A: High Pitta -> Drop Ushna (heating) items
        if pitta_level > 0.5 and item.get("virya") == "Ushna":
            exclude_item = True
            reasons.append("High Pitta contraindication: Ushna (heating) potency")
            
        # Rule B: Low Agni (Mandagni) -> Drop Guru (heavy) items
        if agni == "Mandagni" and "Guru" in item.get("guna", []):
            exclude_item = True
            reasons.append("Low Agni contraindication: Guru (heavy) quality")
            
        # Rule C: High Vata -> Drop Ruksha (dry) items
        if vata_level > 0.5 and "Ruksha" in item.get("guna", []):
            exclude_item = True
            reasons.append("High Vata contraindication: Ruksha (dry) quality")
            
        # Rule D: High Kapha -> Drop Guru (heavy) or Snigdha (oily) items
        if kapha_level > 0.5 and ("Guru" in item.get("guna", []) or "Snigdha" in item.get("guna", [])):
            exclude_item = True
            reasons.append("High Kapha contraindication: Guru/Snigdha (heavy/oily) qualities")
            
        if exclude_item:
            exclusions.append({"name": item["name"], "reasons": reasons})
        else:
            filtered_items.append(item)
            
    num_foods = len(filtered_items)
    if num_foods == 0:
        return {
            "status": "Infeasible",
            "message": "All food items were filtered out due to severe Ayurvedic contraindications.",
            "exclusions": exclusions,
            "meals": []
        }
        
    # 3. Formulate the Linear Programming Problem with Slack Variables
    # We want to minimize a combined objective:
    # Obj = Sum_{i=0..N-1} (c_i * x_i) + M * Sum(slacks)
    # where c_i is the cost of food item i, designed to penalize foods that aggravate
    # patient's dosha imbalances, and reward foods that pacify them.
    # We define 8 slack variables to ensure the LP is always feasible (Goal Programming):
    # s0: cal_positive, s1: cal_negative
    # s2: prot_positive, s3: prot_negative
    # s4: carb_positive, s5: carb_negative
    # s6: fat_positive, s7: fat_negative
    
    num_slacks = 8
    M = 10000.0  # Large penalty for nutritional deviations
    
    c = []
    for item in filtered_items:
        # Base coefficient is small positive to discourage excessively large food quantities
        cost = 0.1 
        
        # Modify cost based on dosha effects
        # If food aggravates a dosha which is imbalanced, penalize it
        dosha_effects = item.get("dosha_effects", {})
        for dosha, level in [("vata", vata_level), ("pitta", pitta_level), ("kapha", kapha_level)]:
            effect = dosha_effects.get(dosha, 0)
            if level > 0.3:
                if effect > 0: # Aggravating
                    cost += effect * level * 2.0
                elif effect < 0: # Pacifying (negative effect)
                    cost -= abs(effect) * level * 1.5
                    
        # Ensure cost stays positive (linprog works better with bounded positive objectives here)
        c.append(max(0.01, cost))
        
    # Append high penalties for slack variables
    c.extend([M] * num_slacks)
    
    # Coefficients matrices
    # A_eq * w = b_eq
    # where w = [x_0, ..., x_{N-1}, s0, s1, s2, s3, s4, s5, s6, s7]
    A_eq = []
    b_eq = []
    
    # Constraints rows mapping:
    # 0: Calories, 1: Protein, 2: Carbs, 3: Fats
    macros = [
        ("calories", target_calories),
        ("protein_g", target_protein),
        ("carbs_g", target_carbs),
        ("fats_g", target_fats)
    ]
    
    for row_idx, (macro_name, target_val) in enumerate(macros):
        row = [0.0] * (num_foods + num_slacks)
        # Populate food coefficients (values per 100g portion)
        for i, item in enumerate(filtered_items):
            row[i] = float(item[macro_name])
            
        # Slack coefficients: s_{2*row_idx} (positive deviation), s_{2*row_idx + 1} (negative deviation)
        # Sum_{i} (x_i * macro_i) - s_pos + s_neg = Target
        row[num_foods + 2 * row_idx] = -1.0
        row[num_foods + 2 * row_idx + 1] = 1.0
        
        A_eq.append(row)
        b_eq.append(target_val)
        
    # Bound limits
    # Food portions bounds: Limit to max 2.5 units (250g) of a single food item to avoid meal monotony
    # Min portion is 0.0
    bounds = []
    for item in filtered_items:
        # Spices have smaller portion size limit (max 15g = 0.15) to make it realistic
        if item["category"].lower() == "spice":
            bounds.append((0.0, 0.2))
        elif item["category"].lower() == "fat":
            bounds.append((0.0, 0.4)) # limit oils/ghee to 40g
        else:
            bounds.append((0.0, 2.5))
            
    # Slack bounds: [0, None]
    for _ in range(num_slacks):
        bounds.append((0.0, None))
        
    # 4. Run Optimization Solver
    res = linprog(
        c=c,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs" # Modern fast interior-point/simplex solver in SciPy
    )
    
    # 5. Compile Results
    if not res.success:
        return {
            "status": "Failed",
            "message": f"Optimization solver failed: {res.message}",
            "exclusions": exclusions,
            "meals": []
        }
        
    # Extract decision variables
    x_sol = res.x[:num_foods]
    slack_sol = res.x[num_foods:]
    
    selected_ingredients = []
    total_opt_calories = 0.0
    total_opt_protein = 0.0
    total_opt_carbs = 0.0
    total_opt_fats = 0.0
    
    for i, quantity in enumerate(x_sol):
        if quantity > 0.01: # Threshold to filter out trace ingredients
            item = filtered_items[i]
            qty_g = round(quantity * 100, 1) # Convert to grams
            
            item_calories = item["calories"] * quantity
            item_protein = item["protein_g"] * quantity
            item_carbs = item["carbs_g"] * quantity
            item_fats = item["fats_g"] * quantity
            
            total_opt_calories += item_calories
            total_opt_protein += item_protein
            total_opt_carbs += item_carbs
            total_opt_fats += item_fats
            
            selected_ingredients.append({
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "quantity_g": qty_g,
                "contribution": {
                    "calories": round(item_calories, 1),
                    "protein_g": round(item_protein, 1),
                    "carbs_g": round(item_carbs, 1),
                    "fats_g": round(item_fats, 1)
                },
                "ayurvedic": {
                    "rasa": item["rasa"],
                    "virya": item["virya"],
                    "guna": item["guna"],
                    "vipaka": item["vipaka"]
                }
            })
            
    # Calculate nutritional deviations from targets
    deviations = {
        "calories": round(slack_sol[0] - slack_sol[1], 1),
        "protein_g": round(slack_sol[2] - slack_sol[3], 1),
        "carbs_g": round(slack_sol[4] - slack_sol[5], 1),
        "fats_g": round(slack_sol[6] - slack_sol[7], 1)
    }
    
    return {
        "status": "Success",
        "nutritional_summary": {
            "target": {
                "calories": target_calories,
                "protein_g": target_protein,
                "carbs_g": target_carbs,
                "fats_g": target_fats
            },
            "solved": {
                "calories": round(total_opt_calories, 1),
                "protein_g": round(total_opt_protein, 1),
                "carbs_g": round(total_opt_carbs, 1),
                "fats_g": round(total_opt_fats, 1)
            },
            "deviations": deviations
        },
        "ingredients": selected_ingredients,
        "exclusions_count": len(exclusions),
        "exclusions_sample": exclusions[:10] # Return a subset of exclusions for review
    }
