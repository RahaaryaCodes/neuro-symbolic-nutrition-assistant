"""
config.py — Konfigurasi Path Terpusat
======================================
Membaca path dari Colab Secrets (userdata) jika tersedia,
atau fallback ke environment variable / nilai default.

Cara setup di Google Colab:
  1. Klik ikon 🔑 (Secrets) di sidebar kiri Colab
  2. Tambahkan key-value sesuai nama variabel di bawah
  3. Aktifkan toggle "Notebook access" untuk setiap secret

Cara setup lokal (untuk development):
  1. Salin .env.example menjadi .env
  2. Isi nilai path sesuai mesin kamu
  3. Install python-dotenv: pip install python-dotenv
"""

import os

def _get_secret(key: str, default: str = "") -> str:
    """
    Baca nilai dari Colab Secrets terlebih dahulu,
    lalu fallback ke environment variable, lalu default.
    """
    # 1. Coba Colab Secrets (userdata)
    try:
        from google.colab import userdata
        value = userdata.get(key)
        if value:
            return value
    except Exception:
        pass  # Bukan environment Colab, lanjut

    # 2. Coba environment variable (untuk .env lokal)
    value = os.environ.get(key, "")
    if value:
        return value

    # 3. Gunakan default
    return default


# =============================================
# PATH UTAMA — Sesuaikan via Colab Secrets
# =============================================

# Base folder Google Drive kamu
DRIVE_BASE_PATH = _get_secret(
    "DRIVE_BASE_PATH",
    "/content/drive/MyDrive/skripsian"  # default fallback
)

# Path ke folder data
DATA_PATH = _get_secret("DATA_PATH", f"{DRIVE_BASE_PATH}/data")

# File-file sumber data
TKPI_EXCEL_PATH = _get_secret("TKPI_EXCEL_PATH", f"{DATA_PATH}/tkpi-2019.xlsx")
AKG_CSV_PATH    = _get_secret("AKG_CSV_PATH",    f"{DATA_PATH}/akg_clean.csv")
PROCESSED_PATH  = _get_secret("PROCESSED_DATA_PATH", f"{DATA_PATH}/processed")

# Path ChromaDB vector store
CHROMA_PATH = _get_secret(
    "CHROMA_PATH",
    f"{DRIVE_BASE_PATH}/chroma_db/chroma_tkpi_full"
)

# Path folder notebook/modul Python (agar bisa import ingredient_recommender, dll)
NOTEBOOK_BASE_PATH = _get_secret(
    "NOTEBOOK_BASE_PATH",
    f"{DRIVE_BASE_PATH}/Notebook"
)

# (Opsional) Path LoRA adapter — hanya relevan jika pakai model fine-tuned
LORA_ADAPTER_PATH = _get_secret(
    "LORA_ADAPTER_PATH",
    f"{DRIVE_BASE_PATH}/adapters/gizi_assistant_lora_1.5b"
)


# =============================================
# MODEL SETTINGS (tidak sensitif, aman di repo)
# =============================================
EMBEDDING_MODEL_ID = "intfloat/multilingual-e5-large"
LLM_MODEL_ID       = "Qwen/Qwen2.5-7B-Instruct"
CHROMA_COLLECTION  = "tkpi_full"


if __name__ == "__main__":
    # Jalankan file ini untuk verifikasi path sudah terbaca
    print("=== Konfigurasi Path ===")
    print(f"DRIVE_BASE_PATH    : {DRIVE_BASE_PATH}")
    print(f"TKPI_EXCEL_PATH    : {TKPI_EXCEL_PATH}")
    print(f"AKG_CSV_PATH       : {AKG_CSV_PATH}")
    print(f"CHROMA_PATH        : {CHROMA_PATH}")
    print(f"NOTEBOOK_BASE_PATH : {NOTEBOOK_BASE_PATH}")
    print(f"LLM_MODEL_ID       : {LLM_MODEL_ID}")
