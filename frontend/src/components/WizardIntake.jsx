import React, { useState } from "react";

export default function WizardIntake({ formData, setFormData, onSubmit, onOcrUpload, ocrLoading, ocrResult }) {
  const [step, setStep] = useState(1);
  const [dragActive, setDragActive] = useState(false);

  const nextStep = () => setStep((s) => Math.min(s + 1, 3));
  const prevStep = () => setStep((s) => Math.max(s - 1, 1));

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleDoshaChange = (dosha, value) => {
    setFormData((prev) => {
      const newDosha = { ...prev.current_dosha_imbalance, [dosha]: parseFloat(value) };
      // Normalize so they sum to approximately 1.0 if they sum to something else,
      // but for sliders, simple raw ratio is fine. We will normalize in API or here.
      return {
        ...prev,
        current_dosha_imbalance: newDosha,
      };
    });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onOcrUpload(e.target.files[0]);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onOcrUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="glass p-8 animate-fade-in" style={{ width: "100%", maxWidth: "750px" }}>
      {/* OCR Drag-and-Drop Prescription Uploader */}
      {step === 1 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-3 text-emerald-400">💡 OCR Smart Pre-populate</h3>
          <p className="text-sm text-gray-400 mb-4">
            Upload or drag handwritten clinical diet notes to extract details (Age, Bowel habits, Agni level, Dosha signs) automatically.
          </p>
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-6 text-center transition-all ${
              dragActive ? "border-emerald-400 bg-emerald-950/20" : "border-gray-700 bg-slate-900/40"
            }`}
          >
            {ocrLoading ? (
              <div className="py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400 mx-auto mb-2"></div>
                <p className="text-sm text-emerald-400">Extracting clinical keywords via OCR engine...</p>
              </div>
            ) : (
              <div>
                <svg className="mx-auto h-12 w-12 text-gray-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <label className="cursor-pointer text-sm font-semibold text-emerald-400 hover:text-emerald-300">
                  <span>Upload clinical notes</span>
                  <input type="file" className="hidden" accept="image/*" onChange={handleFileChange} />
                </label>
                <p className="text-xs text-gray-500 mt-1">PNG, JPG, or WebP up to 10MB</p>
              </div>
            )}
          </div>
          
          {ocrResult && (
            <div className={`mt-4 p-4 rounded-md text-sm border ${
              ocrResult.status === "Success" 
                ? "bg-emerald-950/20 border-emerald-800 text-emerald-300"
                : ocrResult.status === "Warning"
                ? "bg-amber-950/20 border-amber-800 text-amber-300"
                : "bg-red-950/20 border-red-900 text-red-300"
            }`}>
              <div className="font-semibold mb-1">
                {ocrResult.status === "Success" ? "✓ OCR Parsing Success" : `⚠ OCR Status: ${ocrResult.status}`}
              </div>
              <p className="text-xs mb-2">{ocrResult.message}</p>
              {ocrResult.data && (
                <div className="text-xs grid grid-cols-2 gap-x-4 gap-y-1 mt-2 bg-black/30 p-2 rounded">
                  <div><strong>Age:</strong> {ocrResult.data.age}</div>
                  <div><strong>Gender:</strong> {ocrResult.data.gender}</div>
                  <div><strong>Bowel Movements:</strong> {ocrResult.data.bowel_movements}</div>
                  <div><strong>Appetite:</strong> {ocrResult.data.appetite_level}</div>
                  <div><strong>Vata/Pitta/Kapha:</strong> {Object.entries(ocrResult.data.current_dosha_imbalance).map(([k, v]) => `${k.toUpperCase()}:${v}`).join(", ")}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Steps Indicators */}
      <div className="flex items-center justify-between mb-8 border-b border-gray-800 pb-4">
        {[
          { num: 1, name: "Vitals & Demographics" },
          { num: 2, name: "Ayurvedic Diagnostics" },
          { num: 3, name: "Lifestyle & Nutrition" }
        ].map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <span className={`h-8 w-8 rounded-full flex items-center justify-center font-bold text-sm ${
              step === s.num 
                ? "bg-emerald-500 text-black shadow-md shadow-emerald-500/20" 
                : step > s.num 
                ? "bg-emerald-800/40 text-emerald-400 border border-emerald-500/30" 
                : "bg-slate-800/50 text-gray-500 border border-transparent"
            }`}>
              {s.num}
            </span>
            <span className={`text-xs font-semibold hidden md:inline ${step === s.num ? "text-emerald-400" : "text-gray-500"}`}>
              {s.name}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Vitals & Demographics */}
      {step === 1 && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">PATIENT FULL NAME</label>
              <input 
                type="text" 
                placeholder="Enter patient name" 
                value={formData.name} 
                onChange={(e) => handleInputChange("name", e.target.value)} 
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">GENDER</label>
              <select value={formData.gender} onChange={(e) => handleInputChange("gender", e.target.value)}>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">AGE</label>
              <input 
                type="number" 
                placeholder="Age" 
                value={formData.age} 
                onChange={(e) => handleInputChange("age", parseInt(e.target.value) || "")} 
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">DIETARY PREFERENCE</label>
              <select value={formData.dietary_habits} onChange={(e) => handleInputChange("dietary_habits", e.target.value)}>
                <option value="Vegetarian">Vegetarian (Sattvic)</option>
                <option value="Vegan">Vegan</option>
                <option value="Non-Vegetarian">Non-Vegetarian</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Ayurvedic Diagnostics */}
      {step === 2 && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">DIGESTIVE FIRE (AGNI)</label>
              <select value={formData.appetite_level} onChange={(e) => handleInputChange("appetite_level", e.target.value)}>
                <option value="Samagni">Samagni (Balanced Digestion)</option>
                <option value="Mandagni">Mandagni (Low / Slow Agni)</option>
                <option value="Tikshnagni">Tikshnagni (High / Sharp Agni)</option>
                <option value="Vishamagni">Vishamagni (Variable / Unstable Agni)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">BOWEL HABITS (KOSTHA)</label>
              <select value={formData.bowel_movements} onChange={(e) => handleInputChange("bowel_movements", e.target.value)}>
                <option value="Madhyama">Madhyama (Regular / Balanced)</option>
                <option value="Krura">Krura (Hard / Constipated / Dry)</option>
                <option value="Mridu">Mridu (Soft / Loose / Frequent)</option>
                <option value="Vishama">Vishama (Variable / Gas-prone)</option>
              </select>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <h4 className="text-sm font-semibold text-emerald-400 mb-4">🌀 Current Dosha Imbalance Profiles</h4>
            <div className="space-y-4">
              {[
                { name: "Vata (Air & Ether)", val: formData.current_dosha_imbalance.vata, key: "vata", desc: "Dryness, coldness, gas, anxiety, variable bowel", color: "var(--accent-vata)" },
                { name: "Pitta (Fire & Water)", val: formData.current_dosha_imbalance.pitta, key: "pitta", desc: "Heat, acidity, inflammation, hunger, loose bowel", color: "var(--accent-pitta)" },
                { name: "Kapha (Water & Earth)", val: formData.current_dosha_imbalance.kapha, key: "kapha", desc: "Heaviness, lethargy, slow digestion, congestion", color: "var(--accent-kapha)" }
              ].map((dosha) => (
                <div key={dosha.key} className="bg-slate-900/50 p-4 rounded-lg border border-gray-800">
                  <div className="flex justify-between text-xs font-bold mb-1">
                    <span style={{ color: dosha.color }}>{dosha.name}</span>
                    <span style={{ color: dosha.color }}>{Math.round(dosha.val * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    value={dosha.val}
                    onChange={(e) => handleDoshaChange(dosha.key, e.target.value)}
                    style={{ accentColor: dosha.color, cursor: "pointer" }}
                  />
                  <p className="text-[10px] text-gray-500 mt-1">{dosha.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Lifestyle & Nutrition */}
      {step === 3 && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">DAILY WATER INTAKE (LITERS)</label>
              <input 
                type="number" 
                step="0.1" 
                placeholder="e.g. 2.5" 
                value={formData.water_intake_liters} 
                onChange={(e) => handleInputChange("water_intake_liters", parseFloat(e.target.value) || 0.0)} 
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">MEAL FREQUENCY (PER DAY)</label>
              <input 
                type="number" 
                placeholder="e.g. 3" 
                value={formData.meal_frequency} 
                onChange={(e) => handleInputChange("meal_frequency", parseInt(e.target.value) || 0)} 
              />
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <h4 className="text-sm font-semibold text-emerald-400 mb-4">🎯 Target Modern Nutrients Macros</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-gray-400 mb-1">CALORIES (KCAL)</label>
                <input 
                  type="number" 
                  value={formData.target_calories} 
                  onChange={(e) => handleInputChange("target_calories", parseFloat(e.target.value) || 0)} 
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-gray-400 mb-1">PROTEIN (G)</label>
                <input 
                  type="number" 
                  value={formData.target_protein} 
                  onChange={(e) => handleInputChange("target_protein", parseFloat(e.target.value) || 0)} 
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-gray-400 mb-1">CARBS (G)</label>
                <input 
                  type="number" 
                  value={formData.target_carbs} 
                  onChange={(e) => handleInputChange("target_carbs", parseFloat(e.target.value) || 0)} 
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-gray-400 mb-1">FATS (G)</label>
                <input 
                  type="number" 
                  value={formData.target_fats} 
                  onChange={(e) => handleInputChange("target_fats", parseFloat(e.target.value) || 0)} 
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex justify-between items-center mt-8 border-t border-gray-800 pt-4">
        <button
          onClick={prevStep}
          disabled={step === 1}
          className={`px-4 py-2 text-sm font-semibold rounded-md border ${
            step === 1 
              ? "border-gray-800 text-gray-600 bg-slate-900/20 cursor-not-allowed" 
              : "border-gray-700 text-gray-300 hover:bg-slate-800 bg-slate-900/60"
          }`}
        >
          Previous
        </button>

        {step < 3 ? (
          <button
            onClick={nextStep}
            className="px-5 py-2 text-sm font-semibold rounded-md bg-emerald-500 text-black hover:bg-emerald-400"
          >
            Next Step
          </button>
        ) : (
          <button
            onClick={onSubmit}
            className="px-6 py-2 text-sm font-bold rounded-md bg-gradient-to-r from-emerald-500 to-teal-500 text-black hover:opacity-90 shadow-md shadow-emerald-500/25"
          >
            ⚡ Generate Meal Plan
          </button>
        )}
      </div>
    </div>
  );
}
