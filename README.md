# 🍽️ Sistem Rekomendasi Gizi Berbasis RAG — TKPI 2019

Aplikasi rekomendasi bahan pangan harian berbasis **Retrieval-Augmented Generation (RAG)** yang dikembangkan sebagai proyek skripsi. Sistem ini membantu pengguna menyusun rekomendasi bahan pangan sesuai kebutuhan gizi personal (BMR/TDEE), tujuan diet, dan validasi terhadap standar AKG Permenkes RI No. 28 Tahun 2019.

---

## 🧩 Arsitektur Sistem

```
tkpi-2019.xlsx ──► tkpi_preprocessing.ipynb ──► ChromaDB (tkpi_full)
                                                        │
akg_clean.csv ──────────────────────────────► akg_validator.py
                                                        │
User Input (usia, BB, TB, aktivitas, tujuan) ──► calculator.py
                                                        │
                                               ingredient_recommender.py
                                               (RAG: query ChromaDB)
                                                        │
                                               Qwen2.5-7B-Instruct (4-bit)
                                               (Generate narasi gizi)
                                                        │
                                               app_rag.py (Streamlit UI)
```

---

## 📁 Struktur File

```
├── app_rag.py                   # Aplikasi utama Streamlit
├── ingredient_recommender.py    # Modul RAG retrieval dari ChromaDB
├── calculator.py                # Kalkulasi BMR, TDEE, dan makronutrien
├── akg_validator.py             # Validasi TDEE vs standar AKG
├── config.py                    # Konfigurasi path (baca dari Colab Secrets)
├── tkpi_preprocessing.ipynb     # Preprocessing data + embedding + ingest ChromaDB
├── menu_preprocessing.ipynb     # Preprocessing data menu (eksplorasi)
├── requirements.txt             
├── .env.example                 # Template konfigurasi path
└── .gitignore
```

---

## ⚙️ Setup & Cara Menjalankan

### 1. Clone Repository
```bash
git clone https://github.com/username/neuro-symbolic-nutrition-assistant.git
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Path (Google Colab)

Proyek ini dirancang untuk berjalan di **Google Colab** dengan data di **Google Drive**.

**Cara setup Colab Secrets:**
1. Buka notebook di Colab
2. Klik ikon 🔑 **Secrets** di sidebar kiri
3. Tambahkan key-value berikut dan aktifkan toggle *"Notebook access"*:

| Key | Contoh Value |
|-----|-------------|
| `DRIVE_BASE_PATH` | `/content/drive/MyDrive/skripsian` |
| `CHROMA_PATH` | `/content/drive/MyDrive/skripsian/chroma_db/chroma_tkpi_full` |
| `AKG_CSV_PATH` | `/content/drive/MyDrive/skripsian/data/akg_clean.csv` |
| `NOTEBOOK_BASE_PATH` | `/content/drive/MyDrive/skripsian/Notebook` |

> Atau salin `.env.example` menjadi `.env` untuk pengembangan lokal.

### 4. Siapkan Data (jalankan sekali)

Buka dan jalankan `tkpi_preprocessing.ipynb` di Colab. Notebook ini akan:
- Membersihkan data `tkpi-2019.xlsx`
- Membuat narasi dan metadata per bahan pangan
- Menghasilkan embedding dengan `intfloat/multilingual-e5-large`
- Menyimpan ke ChromaDB collection `tkpi_full`

### 5. Jalankan Aplikasi
```bash
streamlit run app_rag.py
```

---

## 🔬 Penjelasan Modul

### `ingredient_recommender.py`
Melakukan semantic search ke ChromaDB dengan filtering:
- Blacklist bahan tidak umum (jeroan langka, bahan eksotis)
- Boost popularitas untuk bahan sehari-hari (nasi, ayam, tempe, dll.)
- Filter nutrisi per kategori (karbo, protein, serat) dan tujuan diet

### `calculator.py`
Kalkulasi berbasis evidence:
- **BMR**: Rumus Mifflin-St Jeor
- **TDEE**: BMR × faktor aktivitas (WHO)
- **Makro**: Protein per kg BB (ISSN), lemak % kalori (WHO), karbo dari sisa

### `akg_validator.py`
Membandingkan TDEE pengguna dengan standar AKG berdasarkan gender dan kelompok usia (rentang 13–59 tahun, Permenkes 2019).

### `app_rag.py`
Antarmuka Streamlit yang mengorkestrasikan semua modul dan menggunakan **Qwen2.5-7B-Instruct** (quantized 4-bit) untuk menghasilkan narasi edukasi gizi.

---

## 📊 Dataset

| Dataset | Sumber |
|---------|--------|
| TKPI 2019 | Tabel Komposisi Pangan Indonesia, Kemenkes RI |
| AKG 2019 | Permenkes RI No. 28 Tahun 2019 |

> ⚠️ File data (`tkpi-2019.xlsx`, `akg_clean.csv`) tidak disertakan di repositori karena hak cipta. Silakan unduh dari sumber resmi Kemenkes RI.

---

## 🤖 Model

| Komponen | Model |
|----------|-------|
| Text Embedding | `intfloat/multilingual-e5-large` |
| LLM Generasi | `Qwen/Qwen2.5-7B-Instruct` (4-bit quantization) |
| Vector Store | ChromaDB (persistent) |

---

## 📝 Catatan

- Sistem ini **bukan pengganti konsultasi ahli gizi profesional**
- Rentang usia yang didukung: **13–59 tahun**
- Rekomendasi berdasarkan kandungan gizi per **100 gram** bahan pangan
