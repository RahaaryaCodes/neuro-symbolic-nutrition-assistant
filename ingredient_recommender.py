"""
Ingredient Recommender v2.0
- Query lebih spesifik untuk bahan umum Indonesia
- Blacklist bahan tidak umum (buah eksotis, jeroan langka)
- Boost untuk bahan populer
"""

import chromadb

class IngredientRecommender:
    
    # Daftar bahan yang TIDAK UMUM dikonsumsi sehari-hari
    BLACKLIST_KEYWORDS = [
        # Buah eksotis/langka
        'rotan', 'kom', 'kelenting', 'mengkudu', 'kedondong hutan',
        # Jeroan langka
        'paru', 'usus', 'limpa', 'otak', 'mata', 'lidah', 'ekor',
        # Bahan mentah tidak lazim
        'bubuk mentah', 'tepung mentah',
        # Makanan spesifik daerah yang sangat niche
        'rasi', 'papeda', 'saksang',
        # Label yang aneh
        'darah', 'dideh'
    ]
    
    # Bahan POPULER yang harus diprioritaskan (boost score)
    POPULAR_FOODS = {
        'karbo': ['nasi', 'beras', 'kentang', 'ubi', 'singkong', 'jagung', 
                  'mie', 'roti', 'oatmeal', 'havermut'],
        'protein': ['ayam', 'telur', 'ikan', 'daging sapi', 'tempe', 'tahu', 
                    'udang', 'cumi', 'bandeng', 'lele', 'tongkol', 'tuna'],
        'serat': ['bayam', 'kangkung', 'brokoli', 'wortel', 'sawi', 'kol',
                  'terong', 'labu', 'timun', 'tomat', 'selada', 'buncis']
    }
    
    def __init__(self, chroma_path, embedding_model):
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        try:
            self.collection = self.chroma_client.get_collection(name="tkpi_full")
        except Exception as e:
            raise ValueError(f"Database error: {e}")
        self.model = embedding_model

    def _is_blacklisted(self, nama: str) -> bool:
        """Cek apakah bahan termasuk blacklist."""
        nama_lower = nama.lower()
        return any(bl in nama_lower for bl in self.BLACKLIST_KEYWORDS)
    
    def _get_popularity_score(self, nama: str, category: str) -> int:
        """
        Hitung skor popularitas berdasarkan kecocokan dengan bahan umum.
        Return: 0-100 (lebih tinggi = lebih populer)
        """
        nama_lower = nama.lower()
        popular_list = self.POPULAR_FOODS.get(category, [])
        
        for popular in popular_list:
            if popular in nama_lower:
                return 50  # Boost signifikan untuk bahan populer
        return 0
    
    # Threshold minimum untuk setiap kategori (per 100g)
    MIN_NUTRIENT_THRESHOLD = {
        'karbo': {'karbo': 20},      # Minimal 20g karbo untuk masuk kategori karbo
        'protein': {'protein': 10},   # Minimal 10g protein
        'serat': {}                   # Tidak ada minimum untuk serat
    }
    
    def retrieve_candidates(self, query_text, n_results=10, sort_key=None, category=None, where_filter=None):
        """
        Mencari kandidat bahan pangan dari TKPI dengan filtering.
        
        Args:
            query_text: Query untuk semantic search
            n_results: Jumlah hasil
            sort_key: 'protein', 'karbo', atau 'lemak'
            category: 'karbo', 'protein', atau 'serat' (untuk popularity boost)
        """
        # Tambahkan prefix untuk embedding model
        query_vec = self.model.encode(f"query: {query_text}", normalize_embeddings=True).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=n_results * 4,
            where=where_filter  
        )
        
        candidates = []
        if results['metadatas']:
            for i, meta in enumerate(results['metadatas'][0]):
                nama = meta.get('NAMA BAHAN', meta.get('nama', 'Unknown'))
                
                # Skip bahan yang di-blacklist
                if self._is_blacklisted(nama):
                    continue
                
                # Ambil nilai nutrisi
                kalori = float(meta.get('kalori') or meta.get('ENERGI (Kal)') or 0)
                protein = float(meta.get('protein') or meta.get('PROTEIN (g)') or 0)
                lemak = float(meta.get('lemak') or meta.get('LEMAK (g)') or 0)
                karbo = float(meta.get('karbohidrat') or meta.get('KH (g)') or 0)
                serat = float(meta.get('serat') or meta.get('SERAT (g)') or 0)
                nama = meta.get('nama') or meta.get('NAMA BAHAN') or "Unknown"
                
                # Skip jika nutrisi kosong/invalid
                if kalori == 0 and protein == 0 and karbo == 0:
                    continue
                
                # Filter berdasarkan threshold minimum kategori
                if category and category in self.MIN_NUTRIENT_THRESHOLD:
                    thresholds = self.MIN_NUTRIENT_THRESHOLD[category]
                    skip_item = False
                    for nutrient, min_val in thresholds.items():
                        if nutrient == 'karbo' and karbo < min_val:
                            skip_item = True
                        elif nutrient == 'protein' and protein < min_val:
                            skip_item = True
                    if skip_item:
                        continue
                
                # Hitung skor gabungan
                base_score = n_results * 4 - i  # Skor dari semantic similarity
                popularity_score = self._get_popularity_score(nama, category or '')
                
                candidates.append({
                    "nama": nama,
                    "kalori": kalori,
                    "protein": protein,
                    "lemak": lemak,
                    "karbo": karbo,
                    "serat": serat,
                    "desc": results['documents'][0][i] if results['documents'] else '',
                    "_score": base_score + popularity_score
                })
        
        # Sorting berdasarkan kombinasi: score + nutrisi
        if sort_key == 'protein':
            # Prioritas: popularitas dulu, baru protein tinggi
            candidates.sort(key=lambda x: (x['_score'], x['protein']), reverse=True)
        elif sort_key == 'karbo':
            candidates.sort(key=lambda x: (x['_score'], x['karbo']), reverse=True)
        elif sort_key == 'lemak':
            # Untuk lemak, kita cari yang RENDAH
            candidates.sort(key=lambda x: (x['_score'], -x['lemak']), reverse=True)
        else:
            candidates.sort(key=lambda x: x['_score'], reverse=True)
        
        # Hapus field internal sebelum return
        for c in candidates:
            c.pop('_score', None)
        
        return candidates[:n_results]

    def get_balanced_basket(self, goal):
        basket = {}
        
        if goal == 'cutting':
            # FILTER: Lemak maksimal 10g, Kalori maksimal 250 per 100g
            cutting_filter = {
                "$and": [
                    {"lemak": {"$lte": 10}},
                    {"kalori": {"$lte": 250}}
                ]
            }
            basket['karbo'] = self.retrieve_candidates("nasi merah ubi rebus", 5, 'karbo', 'karbo', cutting_filter)
            basket['protein'] = self.retrieve_candidates("ikan pepes dada ayam panggang", 5, 'protein', 'protein', cutting_filter)
            basket['serat'] = self.retrieve_candidates("sayur bening kangkung", 5, None, 'serat', cutting_filter)
            
        elif goal == 'bulking':
            # FILTER: Kalori minimal 150 agar tidak mengambil makanan terlalu ringan
            bulking_filter = {"kalori": {"$gte": 100}}
            basket['karbo'] = self.retrieve_candidates("nasi putih mie roti", 5, 'karbo', 'karbo', bulking_filter)
            basket['protein'] = self.retrieve_candidates("ayam goreng telur daging", 5, 'protein', 'protein', bulking_filter)
            basket['serat'] = self.retrieve_candidates("tumis sayur lodeh", 5, None, 'serat')
            
        else: # Maintain
            maintain_filter = {"lemak": {"$lte": 20}}
            basket['karbo'] = self.retrieve_candidates("nasi jagung kentang", 5, None, 'karbo', maintain_filter)
            basket['protein'] = self.retrieve_candidates("ayam bakar ikan telur", 5, 'protein', 'protein', maintain_filter)
            basket['serat'] = self.retrieve_candidates("cah kangkung sayur sop", 5, None, 'serat', maintain_filter)
            
        return basket