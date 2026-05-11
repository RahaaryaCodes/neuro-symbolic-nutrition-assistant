import streamlit as st
import sys
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
from peft import PeftModel

# --- KONFIGURASI PATH ---
CHROMA_PATH = "/content/drive/MyDrive/skripsian/chroma_db/chroma_tkpi_full"
BASE_PATH = "/content/drive/MyDrive/skripsian/Notebook" 
if BASE_PATH not in sys.path: sys.path.append(BASE_PATH)

try:
    from ingredient_recommender import IngredientRecommender
    from calculator import NutritionCalculator
    from akg_validator import AKGValidator
except ImportError as e:
    st.error(f"Gagal import modul: {e}"); st.stop()

# Path ke data AKG
AKG_PATH = "/content/drive/MyDrive/skripsian/data/akg_clean.csv"

st.set_page_config(page_title="Asisten Gizi TKPI", layout="wide")

# --- LOAD MODELS ---
@st.cache_resource
def load_models_v4():
    embed_model = SentenceTransformer('intfloat/multilingual-e5-large')
    
    # === [KODE LAMA] QWEN 1.5B FINE-TUNED (DI-COMMENT) ===
    # base_model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    # adapter_path = "/content/drive/MyDrive/skripsian/adapters/gizi_assistant_lora_1.5b"
    # tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    # bnb_config = BitsAndBytesConfig(load_in_4bit=True)
    # base_model = AutoModelForCausalLM.from_pretrained(
    #     base_model_id, 
    #     torch_dtype=torch.float16, 
    #     device_map="auto", 
    #     quantization_config=bnb_config
    # )
    # model = PeftModel.from_pretrained(base_model, adapter_path)
    # model.eval() 
    
    # === [KODE BARU] QWEN 7B INSTRUCT (TANPA LORA) ===
    # Model 7B ini jauh lebih pintar berargumentasi dan muat di Colab (4-bit)
    base_model_id = "Qwen/Qwen2.5-7B-Instruct"
    
    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    bnb_config = BitsAndBytesConfig(load_in_4bit=True)

    model = AutoModelForCausalLM.from_pretrained(
        base_model_id, 
        torch_dtype=torch.float16, 
        device_map="auto", 
        quantization_config=bnb_config
    )
    model.eval()
    # =================================================

    text_generator = pipeline(
        "text-generation", 
        model=model, 
        tokenizer=tokenizer, 
        max_new_tokens=512
    )
    
    recommender = IngredientRecommender(CHROMA_PATH, embed_model)
    return recommender, text_generator, tokenizer

try:
    recommender, llm, tokenizer = load_models_v4()
except Exception as e:
    st.error(f"Gagal memuat model. Pesan error: {e}") 
    st.stop()

# --- STATE MANAGEMENT ---
if 'generated_plan' not in st.session_state:
    st.session_state['generated_plan'] = None
if 'analysis_text' not in st.session_state:
    st.session_state['analysis_text'] = ""
if 'akg_validation' not in st.session_state:
    st.session_state['akg_validation'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("📝 Data Pengguna")
    usia = st.number_input("Usia", 13, 59, 25) 
    gender = st.selectbox("Gender", ["Laki-laki", "Perempuan"])
    bb = st.number_input("Berat Badan (kg)", 30, 150, 60)
    tb = st.number_input("Tinggi Badan (cm)", 100, 220, 170)
    activity_options = {
        "Sangat Ringan (Kerja kantoran/rebahan, jarang/tidak olahraga)": "sangat ringan",
        "Ringan (Olahraga santai 1-3 hari/minggu, banyak duduk)": "ringan",
        "Sedang (Olahraga rutin/gym 3-5 hari/minggu, cukup aktif berjalan)": "sedang",
        "Berat (Olahraga keras 6-7 hari/minggu atau Pekerja Lapangan)": "berat",
        "Sangat Berat (Atlet profesional, kuli bangunan, latihan 2x sehari)": "sangat berat"
    }
    
    aktivitas_label = st.selectbox(
        "Aktivitas Fisik", 
        list(activity_options.keys()),
        index=1, # Default ke 'Ringan'
        help="Pilih aktivitas yang paling mewakili keseharian Anda"
    )
    
    # Ekstrak value rahasianya untuk dikirim ke calculator
    aktivitas_value = activity_options[aktivitas_label]
    tujuan = st.selectbox("Tujuan", ["Maintain", "Cutting", "Bulking"])
    
    if st.button("🚀 GENERATE REKOMENDASI", type="primary"):
        with st.spinner("Mengambil data TKPI..."):
            # 1. Hitung (Menambahkan variabel berat badan 'bb' untuk logic baru)
            bmr = NutritionCalculator.calculate_bmr(bb, tb, usia, gender)
            tdee = NutritionCalculator.calculate_tdee(bmr, aktivitas_value)
            macros = NutritionCalculator.calculate_macro_distribution(tdee, bb, tujuan.lower())
            meals_dist = NutritionCalculator.distribute_daily_meals(macros['calories'])
            # 2. Validasi terhadap AKG Permenkes
            try:
                akg_validator = AKGValidator(AKG_PATH)
                akg_result = akg_validator.validate_calculation(gender, usia, tdee)
                st.session_state['akg_validation'] = akg_result
            except Exception as e:
                st.session_state['akg_validation'] = {"error": True, "message": str(e)}
            
            # 3. Ambil Data
            basket = recommender.get_balanced_basket(tujuan.lower())
            
            # 4. AI Analysis
            karbo_str = ", ".join([i['nama'] for i in basket['karbo']])
            protein_str = ", ".join([i['nama'] for i in basket['protein']])
            sayur_str = ", ".join([i['nama'] for i in basket['serat']])
            
            # PROMPT SYSTEM YANG DIKUNCI KETAT
            prompt_sys = f"""Anda adalah Ahli Gizi profesional bernama Ahsyadya.
TARGET KALORI: {macros['calories']} kkal
FASE: {tujuan}

BAHAN TERPILIH:
- Karbohidrat: {karbo_str}
- Lauk (Protein): {protein_str}
- Sayur/Serat: {sayur_str}

TUGAS: Tuliskan narasi edukasi gizi dalam bentuk 3 PARAGRAF UTUH.

ATURAN MUTLAK:
1. DILARANG membuat format daftar (bullet points) atau persentase. Tulis dalam format paragraf yang mengalir.
2. DILARANG mengulang-ulang kalimat yang sama.
3. HANYA bahas makanan yang ada di daftar BAHAN TERPILIH.

STRUKTUR PARAGRAF YANG WAJIB DIIKUTI:
Paragraf 1: Sapa pengguna dengan ramah, sebutkan target {macros['calories']} kkal. Jelaskan mengapa Karbohidrat dan Lauk di atas sangat cocok sebagai sumber energi dan pembangun otot.
Paragraf 2: Jelaskan secara spesifik manfaat serat dan vitamin dari Sayur di atas untuk kesehatan pencernaan.
Paragraf 3: Berikan penutup yang memotivasi dan ingatkan untuk mematuhi satu porsi dari setiap jenis bahan agar target kalori tercapai."""
            
            messages = [
                {"role": "system", "content": prompt_sys},
                {"role": "user", "content": "Berikan analisis gizi."}
            ]
            
            prompt_text = tokenizer.apply_chat_template(
                messages,
                tokenize=False, 
                add_generation_prompt=True
            )
            
            # === [KODE LAMA] PARAMETER GENERASI (DI-COMMENT) ===
            # outputs = llm(
            #     prompt_text, 
            #     max_new_tokens=512, 
            #     temperature=0.1,
            #     repetition_penalty=1.05,
            #     return_full_text=False
            # )

            # === [KODE BARU] PARAMETER GENERASI YANG DIPERBAIKI ===
            outputs = llm(
                prompt_text, 
                max_new_tokens=512, 
                temperature=0.3,         # Dinaikkan sedikit agar bahasanya lebih mengalir/kreatif
                repetition_penalty=1.15, # Dinaikkan untuk menghukum model jika mengulang kata/kalimat
                return_full_text=False
            )
            
            final_analysis = outputs[0]["generated_text"]
            
            st.session_state['user_macros'] = macros
            st.session_state['generated_plan'] = basket
            st.session_state['analysis_text'] = final_analysis
            st.session_state['meals_dist'] = meals_dist


# ===================== [MAIN INTERFACE] =====================
st.title("🍽️ Rekomendasi Gizi TKPI (Bahan & Masakan)")

def get_tags(item, category):
    """Membuat label otomatis agar informatif"""
    tags = []
    try:
        cal = float(item.get('kalori', 0))
        prot = float(item.get('protein', 0))
        fib = float(item.get('serat', 0))
        
        if cal < 100: tags.append("📉 Rendah Kalori")
        elif cal > 350: tags.append("⚡ Padat Energi")
        
        if category == 'protein':
            if prot > 20: tags.append("💪 Super Protein")
            elif prot > 15: tags.append("✅ Tinggi Protein")
            
        if category in ['karbo', 'serat'] and fib > 2:
            tags.append("🌾 Kaya Serat")
            
    except:
        pass
        
    return " • ".join(tags)

if st.session_state['generated_plan']:
    macros = st.session_state['user_macros']
    basket = st.session_state['generated_plan']
    
    with st.container(border=True):
        st.subheader("🎯 Target Harian Anda")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Energi", f"{macros['calories']} kkal")
        c2.metric("Protein", f"{macros['protein']} g", help="Penting untuk otot")
        c3.metric("Karbo", f"{macros['carbs']} g", help="Sumber tenaga")
        c4.metric("Lemak", f"{macros['fat']} g")
        
        akg_val = st.session_state.get('akg_validation')
        if akg_val and not akg_val.get('error'):
            st.divider()
            st.caption("📋 **Validasi terhadap AKG Permenkes 2019**")
            
            col_akg1, col_akg2, col_akg3 = st.columns(3)
            with col_akg1:
                st.metric(
                    "TDEE Anda", 
                    f"{akg_val['calculated_tdee']} kkal",
                    delta=f"{akg_val['deviation_percent']:+.1f}% vs AKG"
                )
            with col_akg2:
                st.metric("Standar AKG", f"{akg_val['akg_standard']} kkal")
            with col_akg3:
                status_emoji = "✅" if akg_val['status'] == "SESUAI" else "⚠️"
                st.metric("Status", f"{status_emoji} {akg_val['status']}")
            
            if akg_val.get('note'):
                st.info(f"💡 {akg_val['note']}")
                
            with st.expander("📊 Lihat Detail Standar AKG"):
                akg_details = akg_val.get('akg_details', {})
                st.write(f"**Protein:** {akg_details.get('protein_g', 0)} g/hari")
                st.write(f"**Lemak:** {akg_details.get('lemak_total_g', 0)} g/hari")
                st.write(f"**Karbohidrat:** {akg_details.get('karbohidrat_g', 0)} g/hari")
                st.write(f"**Serat:** {akg_details.get('serat_g', 0)} g/hari")
                st.caption(f"Sumber: {akg_val.get('source', 'Permenkes 2019')}")
                st.info("""
            💡 **Kenapa TDEE Anda bisa berbeda dari Standar AKG?** Angka Kecukupan Gizi (AKG) adalah nilai rata-rata acuan untuk populasi nasional berdasarkan kelompok umur. Sementara itu, **TDEE Anda dihitung secara personal** menggunakan formula *Mifflin-St Jeor* yang sangat akurat dengan menyesuaikan Berat Badan, Tinggi Badan, serta Tingkat Aktivitas Fisik Anda yang sebenarnya.
            """)
        elif akg_val and akg_val.get('error'):
            st.warning(f"⚠️ Validasi AKG: {akg_val.get('message', 'Error tidak diketahui')}")

    meals = st.session_state['meals_dist']
    st.subheader("🕒 Distribusi Kalori per Waktu Makan")
    st.caption("Panduan pembagian kalori agar tubuh Anda mendapat energi yang stabil sepanjang hari (Berdasarkan Target Kalori).")
    
    with st.container(border=True):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("🌅 Sarapan (25%)", f"{meals['sarapan']} kkal")
        col_m2.metric("☀️ Makan Siang (35%)", f"{meals['makan_siang']} kkal")
        col_m3.metric("🌙 Makan Malam (30%)", f"{meals['makan_malam']} kkal")
        col_m4.metric("🍎 Snack (10%)", f"{meals['snack']} kkal")

    st.write("")

    st.subheader("🛒 Pilihan Bahan Pangan")
    st.caption("Silakan **pilih 1 item** dari setiap kategori di bawah ini untuk menyusun menu makan Anda.")
    
    tab_karbo, tab_lauk, tab_sayur = st.tabs(["🍚 Karbohidrat", "🍗 Lauk (Protein)", "🥦 Sayur & Serat"])

    with tab_karbo:
        for item in basket['karbo']:
            with st.container(border=True):
                col_icon, col_info = st.columns([1, 5])
                with col_icon:
                    st.markdown("<h1>🍚</h1>", unsafe_allow_html=True)
                with col_info:
                    st.markdown(f"**{item['nama']}**")
                    tag_str = get_tags(item, 'karbo')
                    if tag_str: st.caption(f"🏷️ {tag_str}")
                    
                    c_val = float(item.get('karbo', 0))
                    st.progress(min(c_val/100, 1.0), text=f"Karbohidrat: {c_val}g")
                    st.markdown(f"<small>🔥 Energi: {item['kalori']} kkal | 💪 Protein: {item['protein']}g</small>", unsafe_allow_html=True)

    with tab_lauk:
        for item in basket['protein']:
            with st.container(border=True):
                col_icon, col_info = st.columns([1, 5])
                with col_icon:
                    st.markdown("<h1>🍗</h1>", unsafe_allow_html=True)
                with col_info:
                    st.markdown(f"**{item['nama']}**")
                    tag_str = get_tags(item, 'protein')
                    if tag_str: st.caption(f"🏷️ {tag_str}")
                    
                    p_val = float(item.get('protein', 0))
                    st.progress(min(p_val/40, 1.0), text=f"Protein: {p_val}g")
                    st.markdown(f"<small>🔥 Energi: {item['kalori']} kkal | 💧 Lemak: {item.get('lemak', 0)}g</small>", unsafe_allow_html=True)

    with tab_sayur:
        for item in basket['serat']:
            with st.container(border=True):
                col_icon, col_info = st.columns([1, 5])
                with col_icon:
                    st.markdown("<h1>🥦</h1>", unsafe_allow_html=True)
                with col_info:
                    st.markdown(f"**{item['nama']}**")
                    
                    # Cek tag serat jika tersedia
                    tag_str = get_tags(item, 'serat')
                    if tag_str: st.caption(f"🏷️ {tag_str}")
                    
                    # Ekstrak nilai serat dengan fallback ke 0
                    s_val = float(item.get('serat', 0))
                    
                    # Gunakan progress bar seperti pada karbo/protein (misal max target 10g per porsi)
                    st.progress(min(s_val/10, 1.0), text=f"Serat: {s_val}g")
                    
                    # Tampilkan kalori dan protein ringan (sayur kadang mengandung protein nabati)
                    p_val_sayur = float(item.get('protein', 0))
                    st.markdown(f"<small>🔥 Energi: {item['kalori']} kkal | 💪 Protein: {p_val_sayur}g</small>", unsafe_allow_html=True)
            
    st.divider()
    
    st.subheader("💡 Analisis Ahli Gizi (AI)")
    with st.chat_message("assistant"):
        st.markdown(st.session_state['analysis_text'])
    
else:
    st.info("👈 Silakan isi data diri di Sidebar kiri, lalu klik **ROCKET (GENERATE)**.")