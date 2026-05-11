"""
Modul Calculator Nutrisi (BMR, TDEE, Makro)
Versi: Evidence-Based (ISSN, WHO, ACSM)
"""

class NutritionCalculator:

    # =========================
    # 1. BMR (Mifflin-St Jeor)
    # =========================
    @staticmethod
    def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
        """
        Hitung BMR menggunakan rumus Mifflin-St Jeor
        """
        gender = gender.lower()
        
        if gender in ['laki-laki', 'pria', 'male']:
            return (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            return (10 * weight) + (6.25 * height) - (5 * age) - 161

    # =========================
    # 2. TDEE
    # =========================
    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str) -> float:
        """
        Hitung TDEE berdasarkan aktivitas
        """
        factors = {
            'sangat ringan': 1.2,
            'ringan': 1.375,
            'sedang': 1.55,
            'berat': 1.725,
            'sangat berat': 1.9
        }

        factor = factors.get(activity_level.lower(), 1.2)
        return bmr * factor

    # =========================
    # 3. MACRO (HYBRID MODEL)
    # =========================
    @staticmethod
    def calculate_macro_distribution(
        tdee: float, 
        weight: float, 
        goal: str = 'maintain'
    ) -> dict:
        """
        Hitung makronutrien berbasis evidence:
        - Protein: g/kg BB (ISSN)
        - Lemak: % kalori (WHO)
        - Karbo: sisa kalori (ACSM)
        """

        goal = goal.lower()

        # === 1. Tentukan kalori & protein ===
        if goal == 'cutting':
            calories = tdee - 500
            protein = weight * 2.2   # tinggi untuk jaga massa otot
            fat_ratio = 0.25

        elif goal == 'bulking':
            calories = tdee + 300
            protein = weight * 1.8   # optimal hypertrophy
            fat_ratio = 0.25

        else:  # maintain
            calories = tdee
            protein = weight * 1.6
            fat_ratio = 0.30

        # === 2. Hitung lemak ===
        fat = (calories * fat_ratio) / 9

        # === 3. Hitung karbo (sisa kalori) ===
        remaining_calories = calories - (protein * 4 + fat * 9)
        carbs = max(0, remaining_calories / 4)  # guard biar tidak negatif

        # === 4. Safety clamp tambahan ===
        protein = max(0, protein)
        fat = max(0, fat)

        return {
            'calories': round(calories),
            'protein': round(protein),
            'fat': round(fat),
            'carbs': round(carbs)
        }

    # =========================
    # 4. DISTRIBUSI MAKAN
    # =========================
    @staticmethod
    def distribute_daily_meals(calories: float) -> dict:
        """
        Distribusi kalori harian berdasarkan TOTAL KALORI (bukan TDEE)
        """
        return {
            'sarapan': round(calories * 0.25),
            'makan_siang': round(calories * 0.35),
            'makan_malam': round(calories * 0.30),
            'snack': round(calories * 0.10)
        }

    # =========================
    # 5. OPSIONAL: VALIDASI LOGIC
    # =========================
    @staticmethod
    def validate_macros(macros: dict) -> dict:
        """
        Validasi sederhana untuk memastikan tidak ada anomali
        """
        total_calculated = (
            macros['protein'] * 4 +
            macros['fat'] * 9 +
            macros['carbs'] * 4
        )

        return {
            "calculated_calories": total_calculated,
            "difference": total_calculated - macros['calories'],
            "is_valid": abs(total_calculated - macros['calories']) < 50
        }