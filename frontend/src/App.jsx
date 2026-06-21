import React, { useState } from "react";
import WizardIntake from "./components/WizardIntake";
import Dashboard from "./components/Dashboard";

// Base URL targeting our FastAPI backend
const API_BASE_URL = "http://127.0.0.1:8000";

export default function App() {
  const [formData, setFormData] = useState({
    name: "",
    age: 35,
    gender: "Male",
    dietary_habits: "Vegetarian",
    meal_frequency: 3,
    bowel_movements: "Madhyama",
    water_intake_liters: 2.5,
    appetite_level: "Samagni",
    current_dosha_imbalance: {
      vata: 0.33,
      pitta: 0.33,
      kapha: 0.34,
    },
    target_calories: 2000,
    target_protein: 70,
    target_carbs: 250,
    target_fats: 60,
  });

  const [mealPlan, setMealPlan] = useState(null);
  const [substituteResults, setSubstituteResults] = useState([]);
  const [loadingMeal, setLoadingMeal] = useState(false);
  const [loadingSubstitute, setLoadingSubstitute] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Submit to AI LP Solver
  const handleGenerateMealPlan = async () => {
    setLoadingMeal(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/optimize-meal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_profile: {
            name: formData.name || "Default Patient",
            age: formData.age || 30,
            gender: formData.gender,
            dietary_habits: formData.dietary_habits,
            meal_frequency: formData.meal_frequency,
            bowel_movements: formData.bowel_movements,
            water_intake_liters: formData.water_intake_liters,
            appetite_level: formData.appetite_level,
            current_dosha_imbalance: formData.current_dosha_imbalance,
          },
          target_calories: formData.target_calories,
          target_protein: formData.target_protein,
          target_carbs: formData.target_carbs,
          target_fats: formData.target_fats,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail?.message || "Failed to solve diet plan under current Ayurvedic constraints.");
      }
      setMealPlan(data);
    } catch (err) {
      setErrorMessage(err.message);
      setMealPlan(null);
    } finally {
      setLoadingMeal(false);
    }
  };

  // Upload prescription image for OCR extraction
  const handleOcrUpload = async (file) => {
    setOcrLoading(true);
    setOcrResult(null);
    setErrorMessage(null);
    try {
      const bodyData = new FormData();
      bodyData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/api/v1/ocr/upload-prescription`, {
        method: "POST",
        body: bodyData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to process prescription OCR.");
      }

      setOcrResult(data);
      
      // Pre-populate Form Data fields if OCR extraction yields valid records
      if (data.data) {
        const parsed = data.data;
        setFormData((prev) => {
          // Normalize values where appropriate
          let bowelVal = "Madhyama";
          if (parsed.bowel_movements.includes("Hard")) bowelVal = "Krura";
          else if (parsed.bowel_movements.includes("Soft")) bowelVal = "Mridu";
          else if (parsed.bowel_movements.includes("Variable")) bowelVal = "Vishama";

          let agniVal = "Samagni";
          if (parsed.appetite_level.includes("Low")) agniVal = "Mandagni";
          else if (parsed.appetite_level.includes("High")) agniVal = "Tikshnagni";
          else if (parsed.appetite_level.includes("Variable")) agniVal = "Vishamagni";

          return {
            ...prev,
            age: parsed.age || prev.age,
            gender: parsed.gender !== "Unknown" ? parsed.gender : prev.gender,
            dietary_habits: parsed.dietary_habits,
            bowel_movements: bowelVal,
            appetite_level: agniVal,
            current_dosha_imbalance: parsed.current_dosha_imbalance,
          };
        });
      }
    } catch (err) {
      setOcrResult({
        status: "Error",
        message: err.message,
        data: null
      });
    } finally {
      setOcrLoading(false);
    }
  };

  // Fetch NLP Smart Substitutes
  const handleFetchSubstitutes = async (foodId, cuisinePreference = "") => {
    setLoadingSubstitute(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/substitute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          food_id: foodId,
          cuisine_preference: cuisinePreference || null,
          top_n: 5,
        }),
      });

      const data = await response.json();
      if (response.ok) {
        setSubstituteResults(data.substitutes);
      } else {
        setSubstituteResults([]);
      }
    } catch (err) {
      console.error(err);
      setSubstituteResults([]);
    } finally {
      setLoadingSubstitute(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Premium Top Navigation Bar */}
      <header className="no-print bg-slate-950/80 border-b border-gray-900 px-6 py-4 sticky top-0 z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="h-9 w-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-black font-extrabold text-lg shadow-md shadow-emerald-500/20">
              आ
            </span>
            <div>
              <h1 className="text-lg font-extrabold text-white tracking-wide flex items-center gap-1.5">
                AyurAhar <span className="text-[10px] bg-emerald-950 border border-emerald-800 text-emerald-400 font-bold px-1.5 py-0.5 rounded">ENTERPRISE</span>
              </h1>
              <p className="text-[10px] text-gray-400 tracking-wider uppercase font-semibold">Ayurvedic Diet Management System</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs font-semibold text-gray-300">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
              Core engine online
            </span>
          </div>
        </div>
      </header>

      {/* Main Body Layout */}
      <main className="container flex-1 py-8 flex flex-col gap-6">
        {errorMessage && (
          <div className="no-print bg-red-950/20 border border-red-900 p-4 rounded-lg text-sm text-red-400 flex items-start gap-2.5 max-w-4xl mx-auto w-full animate-bounce">
            <svg className="h-5 w-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <div className="font-bold">Optimization Solver Failed</div>
              <p className="text-xs text-gray-400 mt-1">{errorMessage}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start max-w-7xl mx-auto w-full">
          {/* Left Column: Diagnostics Intake */}
          <div className="no-print xl:col-span-5 flex justify-center w-full">
            <WizardIntake
              formData={formData}
              setFormData={setFormData}
              onSubmit={handleGenerateMealPlan}
              onOcrUpload={handleOcrUpload}
              ocrLoading={ocrLoading}
              ocrResult={ocrResult}
            />
          </div>

          {/* Right Column: Optimizer & Dashboard Visualizer */}
          <div className="xl:col-span-7 flex justify-center w-full">
            {loadingMeal ? (
              <div className="glass p-20 text-center w-full max-w-[700px] flex flex-col items-center justify-center gap-3">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400"></div>
                <h3 className="font-bold text-gray-200 mt-2">Compiling Ayurvedic Matrix...</h3>
                <p className="text-xs text-gray-400 max-w-xs">
                  Running Interior-Point Simplex constraints optimization on the 8,000+ item database.
                </p>
              </div>
            ) : (
              <Dashboard
                mealPlan={mealPlan}
                onSubstitute={handleFetchSubstitutes}
                substituteResults={substituteResults}
                loadingSubstitute={loadingSubstitute}
                setMealPlan={setMealPlan}
              />
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="no-print bg-slate-950/40 border-t border-gray-900 py-6 text-center text-xs text-gray-500">
        <p>© 2026 AyurAhar System. Empowering practitioners with precision Ayurvedic-Biochemical diet planning.</p>
      </footer>
    </div>
  );
}
