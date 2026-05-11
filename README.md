# Neuro-Symbolic Nutrition Assistant (NutriVision AI)

Asisten virtual cerdas yang dirancang untuk memberikan rekomendasi gizi personal yang akurat secara medis. Proyek ini mengimplementasikan arsitektur **Neuro-Symbolic** untuk mengatasi kelemahan umum pada LLM standar, yaitu risiko halusinasi pada data angka dan medis.

### ⚡ Fitur Utama & Arsitektur:
* **Neuro-Symbolic Integration:** Menggabungkan logika simbolik (kalkulasi matematis BMI/TDEE berbasis Python) dengan kemampuan generatif LLM.
* **Custom RAG (Retrieval-Augmented Generation):** Alur kerja pencarian data gizi yang diorkestrasi secara manual menggunakan Python murni (tanpa framework pihak ketiga) untuk kontrol penuh atas presisi data.
* **Vector Database:** Menggunakan **ChromaDB** untuk penyimpanan dan pemanggilan kembali (retrieval) dataset gizi terstandarisasi secara efisien.
* **Fact-Grounded Response:** Memastikan setiap saran gizi berlandaskan pada data gizi resmi, bukan sekadar prediksi bahasa.

### 🛠️ Tech Stack:
* **Language:** Python
* **Model:** Hugging Face Transformers (LLM)
* **Database:** ChromaDB (Vector DB)
* **Interface:** Streamlit
