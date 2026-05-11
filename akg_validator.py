"""
Modul Validasi AKG (Angka Kecukupan Gizi)
Berdasarkan Permenkes RI No. 28 Tahun 2019

Batasan Proposal:
- Usia target: 13-59 tahun
- Kategori: Laki-laki dan Perempuan saja
- TIDAK termasuk: Bayi, Anak, Hamil, Menyusui
"""

import pandas as pd
import os

class AKGValidator:
    # Batasan usia sesuai proposal skripsi
    MIN_AGE = 13
    MAX_AGE = 59
    
    # Kategori yang diizinkan (sesuai batasan proposal)
    ALLOWED_CATEGORIES = ['laki-laki', 'perempuan']
    
    def __init__(self, akg_csv_path: str):
        """
        Inisialisasi validator dengan path ke file AKG CSV.
        
        Args:
            akg_csv_path: Path absolut ke file akg_clean.csv
        """
        if not os.path.exists(akg_csv_path):
            raise FileNotFoundError(f"File AKG tidak ditemukan: {akg_csv_path}")
        
        # Load dan preprocess data AKG
        self.akg_df = self._load_and_preprocess(akg_csv_path)
        
    def _load_and_preprocess(self, path: str) -> pd.DataFrame:
        """Load CSV dan ekstrak range usia"""
        df = pd.read_csv(path)
        
        # Normalisasi nama kolom
        df.columns = (df.columns.str.strip().str.lower()
                      .str.replace(' ', '_')
                      .str.replace('(', '').str.replace(')', ''))
        
        # Normalisasi kategori
        df['kelompok'] = df['kelompok'].astype(str).str.lower().str.strip()
        df['umur_raw'] = df['umur'].astype(str).str.lower().str.strip()
        
        # Filter hanya kategori yang diizinkan
        df = df[df['kelompok'].isin(self.ALLOWED_CATEGORIES)].copy()
        
        # Ekstrak min/max usia
        df['umur_min'] = df['umur_raw'].str.extract(r'(\d+)')[0].astype(float)
        df['umur_max'] = df['umur_raw'].str.extract(r'(\d+)\s*-\s*(\d+)').iloc[:, -1]
        
        # Handle format "80+" (tidak relevan untuk range 13-59)
        plus_mask = df['umur_raw'].str.contains(r'\d+\+', regex=True, na=False)
        df.loc[plus_mask, 'umur_max'] = 200.0
        
        # Fillna untuk single value (misal "19 tahun")
        df['umur_max'] = df['umur_max'].fillna(df['umur_min']).astype(float)
        
        # Filter berdasarkan batasan usia proposal (13-59 tahun)
        # Ambil yang range nya overlap dengan 13-59
        df = df[
            (df['umur_min'] <= self.MAX_AGE) & 
            (df['umur_max'] >= self.MIN_AGE)
        ].copy()
        
        return df
    
    def get_akg_for_user(self, gender: str, age: int) -> dict:
        """
        Mendapatkan standar AKG berdasarkan gender dan usia.
        
        Args:
            gender: 'Laki-laki' atau 'Perempuan'
            age: Usia dalam tahun (13-59)
            
        Returns:
            Dict berisi standar AKG, atau pesan error jika tidak ditemukan
        """
        # Validasi input
        if age < self.MIN_AGE or age > self.MAX_AGE:
            return {
                "error": True,
                "message": f"Usia {age} tahun di luar batasan sistem (13-59 tahun)."
            }
        
        # Normalisasi gender
        gender_norm = gender.lower().strip()
        if gender_norm in ['pria', 'male', 'laki-laki', 'l']:
            gender_norm = 'laki-laki'
        elif gender_norm in ['wanita', 'female', 'perempuan', 'p']:
            gender_norm = 'perempuan'
        else:
            return {
                "error": True,
                "message": f"Gender '{gender}' tidak dikenali."
            }
        
        # Cari di dataframe
        mask = (
            (self.akg_df['kelompok'] == gender_norm) &
            (self.akg_df['umur_min'] <= age) &
            (self.akg_df['umur_max'] >= age)
        )
        
        result = self.akg_df[mask]
        
        if result.empty:
            return {
                "error": True,
                "message": f"Data AKG untuk {gender} usia {age} tidak ditemukan."
            }
        
        # Ambil baris pertama dan convert ke dict
        row = result.iloc[0].to_dict()
        row['error'] = False
        row['source'] = 'Permenkes RI No. 28 Tahun 2019'
        
        return row
    
    def validate_calculation(self, gender: str, age: int, calculated_energy: float) -> dict:
        """
        Membandingkan hasil kalkulasi TDEE dengan standar AKG.
        
        Args:
            gender: Gender user
            age: Usia user
            calculated_energy: Hasil kalkulasi TDEE (kkal)
            
        Returns:
            Dict berisi validasi dan catatan
        """
        akg = self.get_akg_for_user(gender, age)
        
        if akg.get('error'):
            return akg
        
        akg_energy = akg.get('energi_total_kkal', 0)
        
        # Hitung persentase deviasi
        if akg_energy > 0:
            deviation_pct = ((calculated_energy - akg_energy) / akg_energy) * 100
        else:
            deviation_pct = 0
        
        # Tentukan status
        if abs(deviation_pct) <= 10:
            status = "SESUAI"
            note = "Kebutuhan kalori Anda sesuai dengan standar AKG."
        elif deviation_pct > 10:
            status = "DI ATAS AKG"
            note = f"TDEE Anda {deviation_pct:.1f}% lebih tinggi dari standar AKG. Ini wajar jika aktivitas Anda tinggi."
        else:
            status = "DI BAWAH AKG"
            note = f"TDEE Anda {abs(deviation_pct):.1f}% lebih rendah dari standar AKG. Pastikan asupan nutrisi tetap tercukupi."
        
        return {
            "error": False,
            "status": status,
            "calculated_tdee": round(calculated_energy),
            "akg_standard": akg_energy,
            "deviation_percent": round(deviation_pct, 1),
            "note": note,
            "akg_details": {
                "protein_g": akg.get('protein_g', 0),
                "lemak_total_g": akg.get('lemak_total_g', 0),
                "karbohidrat_g": akg.get('karbohidrat_g', 0),
                "serat_g": akg.get('serat_g', 0)
            },
            "source": akg.get('source', 'Permenkes 2019')
        }


# === UTILITY FUNCTION ===
def validate_against_akg(gender: str, age: int, calculated_energy: float, 
                         akg_path: str = None) -> dict:
    """
    Fungsi wrapper untuk validasi cepat.
    
    Args:
        gender: Gender user
        age: Usia user  
        calculated_energy: Hasil kalkulasi TDEE
        akg_path: Path ke file akg_clean.csv (opsional)
    
    Returns:
        Dict hasil validasi
    """
    if akg_path is None:
        # Default path (sesuaikan dengan struktur proyek)
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        akg_path = os.path.join(base_dir, "data", "akg_clean.csv")
    
    try:
        validator = AKGValidator(akg_path)
        return validator.validate_calculation(gender, age, calculated_energy)
    except Exception as e:
        return {
            "error": True,
            "message": f"Error validasi AKG: {str(e)}"
        }


# === TEST ===
if __name__ == "__main__":
    # Test lokal
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    akg_path = os.path.join(script_dir, "..", "data", "akg_clean.csv")
    
    validator = AKGValidator(akg_path)
    
    # Test case: Pria 25 tahun, TDEE 2500 kkal
    result = validator.validate_calculation("Laki-laki", 25, 2500)
    print("=== Test Validasi AKG ===")
    print(f"Status: {result.get('status')}")
    print(f"TDEE Hitung: {result.get('calculated_tdee')} kkal")
    print(f"AKG Standar: {result.get('akg_standard')} kkal")
    print(f"Deviasi: {result.get('deviation_percent')}%")
    print(f"Catatan: {result.get('note')}")
