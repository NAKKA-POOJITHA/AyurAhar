import React, { useState } from "react";

export default function Dashboard({ mealPlan, onSubstitute, substituteResults, activeSubstituteItem, loadingSubstitute, setMealPlan }) {
  const [cuisinePref, setCuisinePref] = useState("");
  const [showSubModal, setShowSubModal] = useState(false);
  const [selectedSubItem, setSelectedSubItem] = useState(null);

  if (!mealPlan) {
    return (
      <div className="glass p-12 text-center text-gray-400 max-w-[750px] mx-auto animate-fade-in">
        <svg className="mx-auto h-16 w-16 text-emerald-600/40 mb-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
        <h3 className="text-xl font-bold text-gray-200 mb-2">No Meal Plan Generated</h3>
        <p className="text-sm max-w-md mx-auto">
          Please complete the patient intake diagnostic wizard on the left and click "Generate Meal Plan" to compile the AI optimal diet blueprint.
        </p>
      </div>
    );
  }

  const { status, nutritional_summary, ingredients, exclusions_count } = mealPlan;

  // Ayurvedic Incompatible Food Combinations ("Viruddha Ahar" / Red Alerts)
  // Let's implement an client-side checker that scans the ingredients list for toxic pairings:
  // 1. Milk + Fish (creates heavy skin conditions)
  // 2. Milk + Citrus Fruits (curdling, acidic fire disruption)
  // 3. Honey + Ghee in equal parts (toxic weight pairing)
  // 4. Yogurt + Hot Beverages (destroys active cultures, congests Agni)
  const checkRedAlerts = () => {
    const alerts = [];
    const names = ingredients.map((i) => i.name.toLowerCase());
    
    const hasMilk = names.some((n) => n.includes("milk"));
    const hasFish = names.some((n) => n.includes("fish"));
    const hasCitrus = names.some((n) => n.includes("lemon") || n.includes("orange") || n.includes("sour") || n.includes("citrus"));
    const hasHoney = names.some((n) => n.includes("honey"));
    const hasGhee = names.some((n) => n.includes("ghee"));
    const hasYogurt = names.some((n) => n.includes("yogurt"));
    const hasGinger = names.some((n) => n.includes("ginger"));
    
    if (hasMilk && hasFish) {
      alerts.push({
        id: "alert_milk_fish",
        title: "Toxic Pairing: Milk & Fish (Viruddha)",
        description: "Combining milk and fish creates biological obstruction in channels (Srotas), aggravating skin and circulatory systems."
      });
    }
    if (hasMilk && hasCitrus) {
      alerts.push({
        id: "alert_milk_citrus",
        title: "Toxic Pairing: Milk & Sour Fruit (Viruddha)",
        description: "Sour elements curdle milk in the stomach, producing Ama (undigested toxins) that slows down metabolism."
      });
    }
    if (hasHoney && hasGhee) {
      // If weights are very close (within 5g), flag as equal ratio warning
      const honeyItem = ingredients.find((i) => i.name.toLowerCase().includes("honey"));
      const gheeItem = ingredients.find((i) => i.name.toLowerCase().includes("ghee"));
      if (honeyItem && gheeItem && Math.abs(honeyItem.quantity_g - gheeItem.quantity_g) < 5) {
        alerts.push({
          id: "alert_honey_ghee",
          title: "Incompatible Ratio: Equal Honey & Ghee",
          description: "Ayurveda states that honey and ghee in exact 1:1 weight proportions act as a heavy toxic compound (Ama-producing)."
        });
      }
    }
    if (hasYogurt && hasGinger) {
      const gingerItem = ingredients.find((i) => i.name.toLowerCase().includes("ginger"));
      const yogurtItem = ingredients.find((i) => i.name.toLowerCase().includes("yogurt"));
      if (gingerItem && yogurtItem && gingerItem.quantity_g > 0 && yogurtItem.quantity_g > 0) {
         // Hot + sour yogurt warning
         if (gingerItem.ayurvedic.virya === "Ushna") {
            alerts.push({
              id: "alert_yogurt_hot",
              title: "Digestive Warning: Fermented Yogurt with High Heating Spice",
              description: "Yogurt combined with highly heating elements blocks sweat ducts and channels. Serve separately or with cooling herbs."
            });
         }
      }
    }

    return alerts;
  };

  const redAlerts = checkRedAlerts();

  const handleOpenSubstitute = (item) => {
    setSelectedSubItem(item);
    setShowSubModal(true);
    onSubstitute(item.id, cuisinePref);
  };

  const handleApplySubstitution = (sub) => {
    // Perform inline swap of ingredients in local client state
    const updatedIngredients = ingredients.map((ing) => {
      if (ing.id === selectedSubItem.id) {
        // Compute new macro ratios based on selected quantity proportion
        // To make it simple, we replace the ingredient info directly and keep similar quantity
        const quantity_g = ing.quantity_g;
        const multiplier = quantity_g / 100.0;
        
        return {
          id: sub.id,
          name: sub.name,
          category: sub.category,
          quantity_g: quantity_g,
          contribution: {
            calories: roundVal(sub.calories * multiplier),
            protein_g: roundVal(sub.protein_g * multiplier),
            carbs_g: roundVal(sub.carbs_g * multiplier),
            fats_g: roundVal(sub.fats_g * multiplier)
          },
          ayurvedic: {
            rasa: sub.ayurvedic.rasa,
            virya: sub.ayurvedic.virya,
            guna: sub.ayurvedic.guna,
            vipaka: sub.ayurvedic.vipaka
          }
        };
      }
      return ing;
    });

    // Recompute total nutritional summary
    const total_opt_calories = updatedIngredients.reduce((sum, i) => sum + i.contribution.calories, 0);
    const total_opt_protein = updatedIngredients.reduce((sum, i) => sum + i.contribution.protein_g, 0);
    const total_opt_carbs = updatedIngredients.reduce((sum, i) => sum + i.contribution.carbs_g, 0);
    const total_opt_fats = updatedIngredients.reduce((sum, i) => sum + i.contribution.fats_g, 0);

    setMealPlan((prev) => ({
      ...prev,
      nutritional_summary: {
        ...prev.nutritional_summary,
        solved: {
          calories: roundVal(total_opt_calories),
          protein_g: roundVal(total_opt_protein),
          carbs_g: roundVal(total_opt_carbs),
          fats_g: roundVal(total_opt_fats)
        }
      },
      ingredients: updatedIngredients
    }));

    setShowSubModal(false);
    setSelectedSubItem(null);
  };

  const roundVal = (v) => Math.round(v * 10) / 10;

  const triggerPrint = () => {
    window.print();
  };

  // Custom SVG donut chart parameters
  const solved = nutritional_summary.solved;
  const target = nutritional_summary.target;
  
  // Percentages calculated
  const getPercent = (s, t) => Math.min(100, Math.round((s / t) * 100));
  const calPct = getPercent(solved.calories, target.calories);
  const protPct = getPercent(solved.protein_g, target.protein_g);
  const carbPct = getPercent(solved.carbs_g, target.carbs_g);
  const fatPct = getPercent(solved.fats_g, target.fats_g);

  return (
    <div className="glass p-8 flex flex-col gap-6 animate-fade-in relative" style={{ width: "100%" }}>
      {/* Header Panel */}
      <div className="flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-emerald-400">🥗 Optimized Meal Plan Blueprint</h2>
          <p className="text-xs text-gray-400">AyurAhar Dual-Matrix Constraint Solver Output</p>
        </div>
        <button
          onClick={triggerPrint}
          className="no-print px-4 py-1.5 text-xs font-semibold rounded bg-slate-800 text-gray-300 hover:bg-slate-700 border border-gray-700 flex items-center gap-1.5"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Print Prescription PDF
        </button>
      </div>

      {/* Red Alerts Panel */}
      {redAlerts.length > 0 && (
        <div className="bg-red-950/30 border border-red-900 rounded-lg p-4 animate-pulse">
          <div className="flex items-center gap-2 text-red-400 font-bold text-sm mb-2">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>🚨 RED ALERT: Ayurvedic Incompatibilities (Viruddha Ahar)</span>
          </div>
          <div className="space-y-2">
            {redAlerts.map((alert) => (
              <div key={alert.id} className="text-xs">
                <div className="font-semibold text-red-300">{alert.title}</div>
                <div className="text-gray-400">{alert.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Exclusions Metric */}
      {exclusions_count > 0 && (
        <div className="text-xs bg-slate-900/60 p-3 rounded border border-gray-800/80 text-gray-400">
          🛡️ <strong>Ayurvedic Safety Net:</strong> solver successfully excluded <strong>{exclusions_count}</strong> contraindicated items from database queries based on patient's high doshas / low Agni.
        </div>
      )}

      {/* Nutrient Comparison Charts */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 bg-slate-900/40 p-4 rounded-xl border border-gray-800">
        {[
          { name: "Calories", unit: "kcal", solved: solved.calories, target: target.calories, pct: calPct, color: "#10b981" },
          { name: "Protein", unit: "g", solved: solved.protein_g, target: target.protein_g, pct: protPct, color: "#3b82f6" },
          { name: "Carbs", unit: "g", solved: solved.carbs_g, target: target.carbs_g, pct: carbPct, color: "#f59e0b" },
          { name: "Fats", unit: "g", solved: solved.fats_g, target: target.fats_g, pct: fatPct, color: "#a855f7" }
        ].map((macro) => (
          <div key={macro.name} className="flex flex-col items-center p-3 text-center">
            {/* SVG Ring Gauge */}
            <div className="relative h-20 w-20 mb-2">
              <svg className="h-20 w-20 transform -rotate-90">
                <circle cx="40" cy="40" r="34" stroke="#1f2937" strokeWidth="6" fill="transparent" />
                <circle 
                  cx="40" 
                  cy="40" 
                  r="34" 
                  stroke={macro.color} 
                  strokeWidth="6" 
                  fill="transparent" 
                  strokeDasharray={2 * Math.PI * 34}
                  strokeDashoffset={2 * Math.PI * 34 * (1 - macro.pct / 100)}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-xs font-bold">
                {macro.pct}%
              </div>
            </div>
            <div className="text-xs font-bold text-gray-200">{macro.name}</div>
            <div className="text-[10px] text-gray-400">
              {macro.solved} / {macro.target} {macro.unit}
            </div>
          </div>
        ))}
      </div>

      {/* Ingredients List */}
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">📋 Recommended Food Matrix Ingredients</h3>
        <div className="space-y-3">
          {ingredients.map((ing) => (
            <div key={ing.id} className="flex justify-between items-start bg-slate-900/60 p-4 rounded-lg border border-gray-800/80 hover:border-gray-700/80 transition-all">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-gray-100">{ing.name}</span>
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-gray-400 font-bold">
                    {ing.category}
                  </span>
                </div>
                {/* Ayurvedic Metadata Row */}
                <div className="flex flex-wrap gap-2 text-[10px] text-gray-400 mt-1">
                  <span><strong>Rasa:</strong> {ing.ayurvedic.rasa.join(", ")}</span>
                  <span>•</span>
                  <span><strong>Virya:</strong> <span className={ing.ayurvedic.virya === "Ushna" ? "text-amber-400" : "text-sky-400"}>{ing.ayurvedic.virya}</span></span>
                  <span>•</span>
                  <span><strong>Vipaka:</strong> {ing.ayurvedic.vipaka}</span>
                  <span>•</span>
                  <span><strong>Guna:</strong> {ing.ayurvedic.guna.join(", ")}</span>
                </div>
                {/* Nutrition Row */}
                <div className="text-[10px] text-gray-500 mt-1">
                  Macros: {ing.contribution.calories} kcal | P: {ing.contribution.protein_g}g | C: {ing.contribution.carbs_g}g | F: {ing.contribution.fats_g}g
                </div>
              </div>
              
              <div className="text-right flex flex-col items-end gap-2">
                <span className="font-bold text-sm text-emerald-400">{ing.quantity_g}g</span>
                <button
                  onClick={() => handleOpenSubstitute(ing)}
                  className="no-print px-2.5 py-1 text-[10px] font-semibold text-emerald-400 bg-emerald-950/20 border border-emerald-800/30 rounded hover:bg-emerald-900/20"
                >
                  🔄 Substitute
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Semantic Smart Substitution Modal */}
      {showSubModal && selectedSubItem && (
        <div className="no-print fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass p-6 w-full max-w-lg animate-fade-in flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-gray-800 pb-3">
              <div>
                <h3 className="font-bold text-base text-emerald-400">🔄 Smart Substitution</h3>
                <p className="text-xs text-gray-400">Substituting: {selectedSubItem.name}</p>
              </div>
              <button 
                onClick={() => setShowSubModal(false)}
                className="text-gray-400 hover:text-gray-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {/* Global Cuisine Preference selector */}
            <div className="flex gap-2 items-center">
              <label className="text-xs font-semibold text-gray-300 shrink-0">Cuisine Target:</label>
              <select 
                value={cuisinePref} 
                onChange={(e) => {
                  setCuisinePref(e.target.value);
                  onSubstitute(selectedSubItem.id, e.target.value);
                }}
                className="py-1 px-2 text-xs"
              >
                <option value="">Global (Closest Match)</option>
                <option value="Mediterranean">Mediterranean</option>
                <option value="Western">Western / Macrobiotic</option>
                <option value="East Asian">East Asian / Herb</option>
                <option value="North Indian">North Indian</option>
                <option value="South Indian">South Indian</option>
              </select>
            </div>

            <div className="space-y-3 overflow-y-auto max-h-[300px] pr-1">
              {loadingSubstitute ? (
                <div className="py-8 text-center text-sm text-emerald-400">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-400 mx-auto mb-2"></div>
                  Calculating Cosine Similarity embeddings...
                </div>
              ) : substituteResults && substituteResults.length > 0 ? (
                substituteResults.map((sub) => (
                  <div 
                    key={sub.id} 
                    onClick={() => handleApplySubstitution(sub)}
                    className="flex justify-between items-center p-3 rounded-lg border border-gray-800 bg-slate-900/60 hover:bg-slate-800 hover:border-emerald-500/40 cursor-pointer transition-all"
                  >
                    <div>
                      <div className="font-semibold text-xs text-gray-100">{sub.name}</div>
                      <div className="text-[9px] text-gray-400 mt-0.5">
                        Virya: {sub.ayurvedic.virya} | Vipaka: {sub.ayurvedic.vipaka} | {sub.calories} kcal / 100g
                      </div>
                      <div className="text-[9px] text-emerald-500 font-bold mt-1">
                        Ayurvedic similarity score: {sub.match_confidence}
                      </div>
                    </div>
                    <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/20 px-2 py-0.5 rounded border border-emerald-800/30">
                      Choose
                    </span>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-gray-500">
                  No biochemically matching substitutes found in the database matrix.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
