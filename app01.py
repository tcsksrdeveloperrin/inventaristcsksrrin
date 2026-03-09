import streamlit as st
import pandas as pd
from datetime import date, datetime

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inventaris Kafe",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SUPABASE INIT ───────────────────────────────────────────────────────────────
@st.cache_resource
def init_supabase():
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stRadio > div { gap: 4px; }
    [data-testid="stSidebar"] .stRadio label {
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
        padding: 8px 12px !important;
        transition: background 0.2s;
    }
    [data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.14); }
    div[data-testid="metric-container"] {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        background: #f8fafc;
        border-radius: 16px;
        border: 2px dashed #cbd5e1;
        color: #64748b;
        margin: 1rem 0;
    }
    .empty-state .icon { font-size: 3rem; margin-bottom: 0.5rem; }
    .empty-state h3 { color: #475569; margin: 0.5rem 0 0.3rem; }
    .empty-state p  { margin: 0; font-size: 0.9rem; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    .form-section-title {
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #667eea;
        margin-bottom: 0.6rem;
        margin-top: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── KONSTANTA ───────────────────────────────────────────────────────────────────
KATEGORI_OPTIONS = ["Bahan Baku Minuman", "Bahan Baku Makanan", "Packaging"]

SUB_KATEGORI_MAP = {
    "Bahan Baku Minuman": [
        "Coffee Beans", "Dairy & Creamer", "Powder & Syrup",
        "Fresh & Produce", "Air & Es Batu", "Lainnya",
    ],
    "Bahan Baku Makanan": [
        "Adonan & Tepung", "Protein", "Fresh & Produce",
        "Dairy & Topping", "Bumbu & Pelengkap", "Lainnya",
    ],
    "Packaging": [
        "Gelas & Tutup", "Sedotan", "Kantong Plastik", "Box Makanan",
        "Kertas & Tisu", "Alat Makan Sekali Pakai", "Label & Branding", "Lainnya",
    ],
}

NAMA_BARANG_MAP = {
    ("Bahan Baku Minuman", "Coffee Beans"): [
        "Beans Natural", "Espresso Shot", "Lainnya",
    ],
    ("Bahan Baku Minuman", "Dairy & Creamer"): [
        "Susu Full Cream", "Susu UHT Full Cream", "SKM (Susu Kental Manis)",
        "Creamer Cair / Krim Masak", "Lainnya",
    ],
    ("Bahan Baku Minuman", "Powder & Syrup"): [
        "Powder Hazelnut", "Powder Greentea / Matcha", "Powder Red Velvet",
        "Powder Chocolate / Coklat Bubuk", "Gula Aren / Aren Liquid",
        "Simple Syrup (Gula Cair)", "Syrup Hazelnut", "Syrup Leci",
        "Syrup Melon", "Syrup Strawberry", "Lainnya",
    ],
    ("Bahan Baku Minuman", "Fresh & Produce"): [
        "Lemon Segar", "Teh Celup / Teh Bubuk", "Yakult", "Lainnya",
    ],
    ("Bahan Baku Minuman", "Air & Es Batu"): [
        "Air Mineral / Air Galon", "Es Batu Kristal / Batangan", "Lainnya",
    ],
    ("Bahan Baku Makanan", "Adonan & Tepung"): [
        "Adonan Surabi (Tepung Beras + Santan)", "Beras Ketan", "Tepung Terigu", "Lainnya",
    ],
    ("Bahan Baku Makanan", "Protein"): [
        "Ayam Fillet / Ayam Potong", "Telur Ayam", "Abon Sapi / Abon Ayam",
        "Sosis Ayam / Sosis Sapi", "Seafood Mix (Cumi, Udang, dll)",
        "Daging Kambing", "Ikan Jambal Roti", "Pempek Original",
        "Pempek Kapal Selam", "Risoles", "Tahu Putih / Tahu Goreng",
        "Tempe", "Oncom", "Bakso", "Lainnya",
    ],
    ("Bahan Baku Makanan", "Fresh & Produce"): [
        "Beras (Nasi Putih)", "Kwetiau / Mie Kwetiau", "Kol / Kubis",
        "Pisang Kepok / Cavendish", "Kentang",
        "Sayuran Capcay (Wortel, Sawi, Jagung muda, dll)", "Lainnya",
    ],
    ("Bahan Baku Makanan", "Dairy & Topping"): [
        "Keju Cheddar", "Keju Mozarella", "SKM (Susu Kental Manis)",
        "Meses / Cokelat Serut", "Pasta Cokelat / Dark Chocolate", "Lainnya",
    ],
    ("Bahan Baku Makanan", "Bumbu & Pelengkap"): [
        "Bawang Merah & Bawang Putih", "Bawang Goreng Crispy", "Sambal",
        "Saus Tomat", "Saus Hot / Saus Pedas", "Cuko Pempek",
        "Serundeng Kelapa", "Minyak Goreng",
        "Garam, Gula Pasir, Kecap Manis, Merica", "Lainnya",
    ],
    ("Packaging", "Gelas & Tutup"): [
        "Cup Paper 8oz Hot", "Cup Paper 12oz Hot", "Cold Cup Plastik 16oz",
        "Cold Cup Plastik 22oz", "Tutup Flat Hot Cup", "Tutup Dome Cold Cup",
        "Gelas Plastik Shot / Yakult Cup", "Lainnya",
    ],
    ("Packaging", "Sedotan"): [
        "Sedotan Bening Standar", "Sedotan Boba / Jumbo",
        "Sedotan Kertas / Bambu", "Lainnya",
    ],
    ("Packaging", "Kantong Plastik"): [
        "Kantong Kresek HD Putih / Bening", "Kantong Plastik Besar 30x40cm",
        "Plastik Klip / Zip Lock", "Lainnya",
    ],
    ("Packaging", "Box Makanan"): [
        "Nasi Box / Rice Box Kertas", "Box Snack Kertas Kecil",
        "Tray Plastik PP (untuk Pempek)", "Cup Plastik + Tutup (untuk Cuko)", "Lainnya",
    ],
    ("Packaging", "Kertas & Tisu"): [
        "Tisu Makan / Tissue Napkin", "Tisu Dapur / Kitchen Towel Roll",
        "Kertas Roti / Parchment Paper", "Kertas Nasi / Wax Paper", "Lainnya",
    ],
    ("Packaging", "Alat Makan Sekali Pakai"): [
        "Sendok Plastik Takeaway", "Garpu Plastik Takeaway",
        "Tusuk Sate / Lidi Surabi", "Tusuk Gigi", "Lainnya",
    ],
    ("Packaging", "Label & Branding"): [
        "Stiker Seal / Security Cup", "Kertas Struk Thermal 80mm", "Lainnya",
    ],
}

MERK_MAP = {
    "Susu Full Cream":                       ["Rich Milk", "Lainnya"],
    "Susu UHT Full Cream":                   ["Diamond", "Lainnya"],
    "Yakult":                                ["Yakult", "Lainnya"],
    "Adonan Surabi (Tepung Beras + Santan)": ["Homemade", "Lainnya"],
    "Simple Syrup (Gula Cair)":              ["Homemade", "Lainnya"],
    "Risoles":                               ["Homemade", "Lainnya"],
    "Sambal":                                ["Homemade", "Lainnya"],
    "Cuko Pempek":                           ["Homemade", "Lainnya"],
    "Serundeng Kelapa":                      ["Homemade", "Lainnya"],
    "Stiker Seal / Security Cup":            ["Custom Print", "Lainnya"],
}

DIGUNAKAN_DI_MENU = {
    "Beans Natural":                                    "Kopi Tubruk, Vietnam Drip, Japanese, V60",
    "Espresso Shot":                                    "Kopi Susu Gula Aren, Kopi Susu Klasik, Hazelnut, Coffee Latte, Americano",
    "Susu Full Cream":                                  "Kopi Susu series, Coffee Latte",
    "Susu UHT Full Cream":                              "Hazelnut Latte, Greentea Latte, Red Velvet, Chocolate Latte",
    "SKM (Susu Kental Manis)":                          "Vietnam Drip, Greentea Latte / Surabi Susu, Pisang Keju, Pisang Coklat",
    "Creamer Cair / Krim Masak":                        "Kopi Susu series, Coffee Latte",
    "Powder Hazelnut":                                  "Hazelnut Latte",
    "Powder Greentea / Matcha":                         "Greentea Latte",
    "Powder Red Velvet":                                "Red Velvet Latte",
    "Powder Chocolate / Coklat Bubuk":                  "Chocolate Latte",
    "Gula Aren / Aren Liquid":                          "Kopi Susu Gula Aren",
    "Simple Syrup (Gula Cair)":                         "Coffee Latte, Lemonade, Lemon Tea, Es Teh Manis, Greentea Latte",
    "Syrup Hazelnut":                                   "Kopi Susu Hazelnut",
    "Syrup Leci":                                       "Yakult Leci",
    "Syrup Melon":                                      "Yakult Melon",
    "Syrup Strawberry":                                 "Yakult Strawberry",
    "Lemon Segar":                                      "Lemonade, Lemon Tea",
    "Teh Celup / Teh Bubuk":                            "Lemon Tea, Es Teh Manis",
    "Yakult":                                           "Yakult Leci, Yakult Melon, Yakult Strawberry",
    "Air Mineral / Air Galon":                          "Semua menu kopi & non-kopi",
    "Es Batu Kristal / Batangan":                       "Semua menu minuman dingin",
    "Adonan Surabi (Tepung Beras + Santan)":            "Semua varian Surabi",
    "Beras Ketan":                                      "Ketan Mozarella",
    "Tepung Terigu":                                    "Risoles",
    "Ayam Fillet / Ayam Potong":                        "Ayam Rempah Komplit, Ayam Penyet, Ayam Serundeng, Capcay, Surabi Abon",
    "Telur Ayam":                                       "Surabi Telor, Nasi Goreng series",
    "Abon Sapi / Abon Ayam":                            "Surabi Abon",
    "Sosis Ayam / Sosis Sapi":                          "Surabi Sosis, Sosis goreng",
    "Seafood Mix (Cumi, Udang, dll)":                   "Nasi Goreng Sea Food",
    "Daging Kambing":                                   "Nasi Goreng Kambing",
    "Ikan Jambal Roti":                                 "Nasi Goreng Jambal",
    "Pempek Original":                                  "Pempek Original",
    "Pempek Kapal Selam":                               "Pempek Kapal Selam",
    "Risoles":                                          "Risoles",
    "Tahu Putih / Tahu Goreng":                         "Ayam Rempah Komplit, Ayam Penyet, Ayam Serundeng",
    "Tempe":                                            "Ayam Rempah Komplit, Ayam Penyet, Ayam Serundeng",
    "Oncom":                                            "Surabi Oncom",
    "Bakso":                                            "Capcay",
    "Beras (Nasi Putih)":                               "Ayam series, Nasi Goreng series",
    "Kwetiau / Mie Kwetiau":                            "Kwetiau",
    "Kol / Kubis":                                      "Ayam series, Capcay",
    "Pisang Kepok / Cavendish":                         "Pisang Keju, Pisang Coklat",
    "Kentang":                                          "Kentang goreng",
    "Sayuran Capcay (Wortel, Sawi, Jagung muda, dll)":  "Capcay, Kwetiau",
    "Keju Cheddar":                                     "Surabi Keju, Pisang Keju",
    "Keju Mozarella":                                   "Ketan Mozarella",
    "Meses / Cokelat Serut":                            "Surabi Coklat, Pisang Coklat",
    "Pasta Cokelat / Dark Chocolate":                   "Pisang Coklat",
    "Bawang Merah & Bawang Putih":                      "Semua menu makanan berat",
    "Bawang Goreng Crispy":                             "Ayam series, Nasi Goreng series",
    "Sambal":                                           "Ayam series, Kentang",
    "Saus Tomat":                                       "Kentang, Sosis",
    "Saus Hot / Saus Pedas":                            "Kentang, Sosis",
    "Cuko Pempek":                                      "Pempek Original, Pempek Kapal Selam",
    "Serundeng Kelapa":                                 "Ayam Serundeng",
    "Minyak Goreng":                                    "Semua menu goreng",
    "Garam, Gula Pasir, Kecap Manis, Merica":           "Bumbu semua masakan",
    "Cup Paper 8oz Hot":                                "Kopi Tubruk, Americano Hot, dan semua minuman panas",
    "Cup Paper 12oz Hot":                               "Minuman panas ukuran besar",
    "Cold Cup Plastik 16oz":                            "Semua minuman es: Kopi Susu, Latte series, Yakult, Lemonade, dll",
    "Cold Cup Plastik 22oz":                            "Minuman es ukuran besar",
    "Tutup Flat Hot Cup":                               "Pasangan Cup Paper Hot",
    "Tutup Dome Cold Cup":                              "Pasangan Cold Cup plastik",
    "Gelas Plastik Shot / Yakult Cup":                  "Yakult series, espresso shot",
    "Sedotan Bening Standar":                           "Semua minuman dingin",
    "Sedotan Boba / Jumbo":                             "Menu dengan topping boba/jelly (jika ada)",
    "Sedotan Kertas / Bambu":                           "Alternatif eco-friendly",
    "Kantong Kresek HD Putih / Bening":                 "Bungkus takeaway semua menu",
    "Kantong Plastik Besar 30x40cm":                    "Takeaway makanan berat, paket banyak",
    "Plastik Klip / Zip Lock":                          "Penyimpanan bahan, kemasan kecil",
    "Nasi Box / Rice Box Kertas":                       "Nasi Goreng series, Ayam series — takeaway",
    "Box Snack Kertas Kecil":                           "Pisang Keju/Coklat, Kentang, Sosis, Surabi takeaway",
    "Tray Plastik PP (untuk Pempek)":                   "Pempek Original & Kapal Selam takeaway",
    "Cup Plastik + Tutup (untuk Cuko)":                 "Wadah saus cuko pempek",
    "Tisu Makan / Tissue Napkin":                       "Meja pelanggan, semua menu",
    "Tisu Dapur / Kitchen Towel Roll":                  "Area dapur untuk kebersihan",
    "Kertas Roti / Parchment Paper":                    "Alas sajian surabi, cemilan",
    "Kertas Nasi / Wax Paper":                          "Membungkus surabi, makanan takeaway",
    "Sendok Plastik Takeaway":                          "Semua menu makanan takeaway",
    "Garpu Plastik Takeaway":                           "Pempek, Cemilan, Makanan berat takeaway",
    "Tusuk Sate / Lidi Surabi":                         "Penyajian Surabi",
    "Tusuk Gigi":                                       "Meja pelanggan",
    "Stiker Seal / Security Cup":                       "Segel tutup cup takeaway",
    "Kertas Struk Thermal 80mm":                        "Printer kasir / nota transaksi",
}

UOM_OPTIONS    = ["kg", "gram", "liter", "ml", "pcs", "pack", "dus", "botol", "karton", "lusin"]
GRIND_OPTIONS  = ["-", "Whole Bean", "V60 (5-6)", "Vietnam Drip (3-4)", "Espresso (2-3)", "French Press (7-8)"]
STATUS_OPTIONS = ["Lunas", "Tempo (Hutang)", "DP/Uang Muka"]

# ─── SHELF LIFE MAP ──────────────────────────────────────────────────────────────
# Produk yang TIDAK memiliki expired date di kemasan → estimasi otomatis per metode simpan.
# Format: { nama_barang: { metode_simpan: (hari_min, hari_max, label) } }
METODE_SIMPAN_OPTIONS = ["Pilih metode penyimpanan...", "Suhu Ruang", "Kulkas / Pendingin", "Freezer", "Wadah Kering / Kedap Udara"]

SHELF_LIFE_MAP = {
    # ── BAHAN BAKU MAKANAN ──
    "Telur Ayam": {
        "Suhu Ruang":                (7,  21,  "1–3 minggu (suhu ruang)"),
        "Kulkas / Pendingin":        (21, 35,  "3–5 minggu (kulkas)"),
        "Freezer":                   (90, 365, "3–12 bulan (freezer, sudah dikocok)"),
    },
    "Ayam Fillet / Ayam Potong": {
        "Suhu Ruang":                (0,  1,   "Maks 2 jam (suhu ruang — segera masak)"),
        "Kulkas / Pendingin":        (1,  2,   "1–2 hari (kulkas)"),
        "Freezer":                   (90, 270, "3–9 bulan (freezer)"),
    },
    "Daging Kambing": {
        "Kulkas / Pendingin":        (3,  5,   "3–5 hari (kulkas)"),
        "Freezer":                   (90, 180, "3–6 bulan (freezer)"),
    },
    "Ikan Jambal Roti": {
        "Suhu Ruang":                (14, 30,  "2–4 minggu (suhu ruang, sudah dikeringkan)"),
        "Kulkas / Pendingin":        (30, 60,  "1–2 bulan (kulkas)"),
        "Freezer":                   (90, 180, "3–6 bulan (freezer)"),
    },
    "Tahu Putih / Tahu Goreng": {
        "Suhu Ruang":                (1,  1,   "Maks 1 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (3,  5,   "3–5 hari (kulkas, rendam air ganti tiap hari)"),
    },
    "Tempe": {
        "Suhu Ruang":                (1,  2,   "1–2 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (5,  7,   "5–7 hari (kulkas)"),
        "Freezer":                   (90, 180, "3–6 bulan (freezer)"),
    },
    "Oncom": {
        "Suhu Ruang":                (1,  2,   "1–2 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (3,  5,   "3–5 hari (kulkas)"),
    },
    "Bakso": {
        "Kulkas / Pendingin":        (3,  5,   "3–5 hari (kulkas)"),
        "Freezer":                   (30, 90,  "1–3 bulan (freezer)"),
    },
    "Seafood Mix (Cumi, Udang, dll)": {
        "Kulkas / Pendingin":        (1,  2,   "1–2 hari (kulkas)"),
        "Freezer":                   (90, 180, "3–6 bulan (freezer)"),
    },
    "Pisang Kepok / Cavendish": {
        "Suhu Ruang":                (3,  7,   "3–7 hari (suhu ruang, tergantung kematangan)"),
        "Kulkas / Pendingin":        (7,  14,  "1–2 minggu (kulkas, kulit menghitam normal)"),
    },
    "Kol / Kubis": {
        "Suhu Ruang":                (3,  5,   "3–5 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (14, 21,  "2–3 minggu (kulkas)"),
    },
    "Sayuran Capcay (Wortel, Sawi, Jagung muda, dll)": {
        "Suhu Ruang":                (1,  2,   "1–2 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (5,  7,   "5–7 hari (kulkas)"),
    },
    "Lemon Segar": {
        "Suhu Ruang":                (7,  14,  "1–2 minggu (suhu ruang)"),
        "Kulkas / Pendingin":        (21, 42,  "3–6 minggu (kulkas)"),
    },
    # ── BAHAN BAKU MINUMAN ──
    "Beans Natural": {
        "Suhu Ruang":                (14, 30,  "2–4 minggu setelah roasting (suhu ruang, kedap udara)"),
        "Wadah Kering / Kedap Udara":(30, 60,  "1–2 bulan (wadah kedap udara)"),
    },
    "Adonan Surabi (Tepung Beras + Santan)": {
        "Kulkas / Pendingin":        (1,  2,   "1–2 hari (kulkas)"),
        "Freezer":                   (7,  14,  "1–2 minggu (freezer)"),
    },
    "Sambal": {
        "Suhu Ruang":                (1,  1,   "Maks 1 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (5,  7,   "5–7 hari (kulkas)"),
        "Freezer":                   (30, 60,  "1–2 bulan (freezer)"),
    },
    "Cuko Pempek": {
        "Suhu Ruang":                (1,  2,   "1–2 hari (suhu ruang)"),
        "Kulkas / Pendingin":        (7,  14,  "1–2 minggu (kulkas)"),
    },
    "Serundeng Kelapa": {
        "Suhu Ruang":                (7,  14,  "1–2 minggu (suhu ruang, wadah tertutup)"),
        "Wadah Kering / Kedap Udara":(14, 30,  "2–4 minggu (wadah kedap udara)"),
    },
    "Risoles": {
        "Kulkas / Pendingin":        (2,  3,   "2–3 hari (kulkas, belum digoreng)"),
        "Freezer":                   (30, 60,  "1–2 bulan (freezer, belum digoreng)"),
    },
    "Simple Syrup (Gula Cair)": {
        "Suhu Ruang":                (14, 30,  "2–4 minggu (suhu ruang, botol steril tertutup)"),
        "Kulkas / Pendingin":        (30, 60,  "1–2 bulan (kulkas)"),
    },
    "Pempek Original": {
        "Kulkas / Pendingin":        (3,  5,   "3–5 hari (kulkas)"),
        "Freezer":                   (30, 90,  "1–3 bulan (freezer)"),
    },
    "Pempek Kapal Selam": {
        "Kulkas / Pendingin":        (3,  5,   "3–5 hari (kulkas)"),
        "Freezer":                   (30, 90,  "1–3 bulan (freezer)"),
    },
}

KOLOM_DB = [
    "id", "cabang", "tanggal", "no_nota", "supplier",
    "kategori", "sub_kategori", "nama_barang", "merk", "grind_size",
    "qty", "uom", "harga_satuan", "total_harga",
    "tgl_kadaluarsa", "status_pembayaran", "catatan", "created_at",
]

# ─── SESSION STATE ───────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "logged_in":  False,
        "role":       None,
        "cabang":     None,
        "username":   None,
        "local_data": [],
        "next_id":    1,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ─── HELPERS UI ──────────────────────────────────────────────────────────────────
def empty_state(icon: str, title: str, subtitle: str):
    st.markdown(f"""
    <div class="empty-state">
        <div class="icon">{icon}</div>
        <h3>{title}</h3>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ─── DB HELPERS ──────────────────────────────────────────────────────────────────
def get_data(cabang: str) -> pd.DataFrame:
    if supabase:
        try:
            res = supabase.table("transaksi").select("*").eq("cabang", cabang).order("tanggal", desc=True).execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=KOLOM_DB)
        except Exception as e:
            st.warning(f"Gagal memuat data dari Supabase: {e}")
    rows = [r for r in st.session_state.local_data if r.get("cabang") == cabang]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=KOLOM_DB)

def insert_row(data: dict) -> bool:
    if supabase:
        try:
            # Hapus kolom generated (total_harga dihitung otomatis oleh Supabase)
            payload = {k: v for k, v in data.items() if k != "total_harga"}
            supabase.table("transaksi").insert(payload).execute()
            return True
        except Exception as e:
            st.error(f"Gagal menyimpan ke database: {e}")
            return False
    data["id"]         = st.session_state.next_id
    data["created_at"] = datetime.now().isoformat()
    st.session_state.local_data.append(data.copy())
    st.session_state.next_id += 1
    return True

def update_row(row_id, data: dict) -> bool:
    if supabase:
        try:
            # Hapus kolom generated (total_harga dihitung otomatis oleh Supabase)
            payload = {k: v for k, v in data.items() if k != "total_harga"}
            supabase.table("transaksi").update(payload).eq("id", row_id).execute()
            return True
        except Exception as e:
            st.error(f"Gagal memperbarui: {e}")
            return False
    for i, r in enumerate(st.session_state.local_data):
        if r.get("id") == row_id:
            st.session_state.local_data[i].update(data)
            return True
    return False

def delete_row(row_id) -> bool:
    if supabase:
        try:
            supabase.table("transaksi").delete().eq("id", row_id).execute()
            return True
        except Exception as e:
            st.error(f"Gagal menghapus: {e}")
            return False
    st.session_state.local_data = [r for r in st.session_state.local_data if r.get("id") != row_id]
    return True

def login_check(username: str, password: str):
    if supabase:
        try:
            res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
            if res.data:
                u = res.data[0]
                return u["role"], u["cabang"]
        except Exception as e:
            st.warning(f"Supabase belum terhubung: {e}")
    return None, None

# ─── LOGIN ───────────────────────────────────────────────────────────────────────
def show_login():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;padding:2.2rem;
                    background:linear-gradient(135deg,#1a1a2e,#0f3460);
                    border-radius:20px;color:white;margin-bottom:2rem;'>
            <div style='font-size:3.5rem;'>☕</div>
            <h2 style='margin:0.4rem 0 0.2rem;font-size:1.6rem;'>Inventaris Kafe</h2>
            <p style='opacity:0.65;margin:0;font-size:0.9rem;'>
                Sistem Pencatatan Bahan Baku & Packaging
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_login"):
            username  = st.text_input("Username", placeholder="Masukkan username")
            password  = st.text_input("Password", type="password", placeholder="Masukkan password")
            login_btn = st.form_submit_button("Masuk", use_container_width=True, type="primary")

        if login_btn:
            if not username or not password:
                st.warning("Isi username dan password terlebih dahulu.")
            else:
                role, cabang = login_check(username, password)
                if role:
                    st.session_state.logged_in = True
                    st.session_state.role      = role
                    st.session_state.cabang    = cabang
                    st.session_state.username  = username
                    st.rerun()
                else:
                    st.error("Username atau password salah.")

        if not supabase:
            st.markdown("""
            <div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;
                        padding:0.8rem 1rem;margin-top:1rem;font-size:0.82rem;color:#9a3412;'>
            Supabase belum terhubung. Tambahkan <code>SUPABASE_URL</code> dan <code>SUPABASE_KEY</code>
            di file <code>.streamlit/secrets.toml</code>.
            </div>
            """, unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────────
def show_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style='text-align:center;padding:1rem 0 0.8rem;
                    border-bottom:1px solid rgba(255,255,255,0.15);margin-bottom:1rem;'>
            <div style='font-size:2.2rem;'>☕</div>
            <div style='font-size:1rem;font-weight:700;margin-top:4px;'>Inventaris Kafe</div>
            <div style='font-size:0.75rem;opacity:0.6;margin-top:2px;'>
                Cabang {st.session_state.cabang}
            </div>
        </div>
        """, unsafe_allow_html=True)

        icon = "👑" if st.session_state.role == "manager" else "🧑‍💼"
        st.markdown(f"""
        <div style='background:rgba(255,255,255,0.09);border-radius:10px;
                    padding:0.6rem 0.8rem;margin-bottom:1.2rem;font-size:0.85rem;'>
            {icon} <b>{st.session_state.username}</b><br>
            <span style='opacity:0.6;font-size:0.75rem;'>
                {st.session_state.role.title()} · Cabang {st.session_state.cabang}
            </span>
        </div>
        """, unsafe_allow_html=True)

        pages = [
            "📊 Dashboard",
            "📋 Administrasi",
            "🏷️ Identitas Barang",
            "📦 Detail Stok",
            "🔍 Kontrol & Audit",
        ]
        page = st.radio("Menu", pages, label_visibility="collapsed")

        st.markdown("<div style='margin-top:2rem;border-top:1px solid rgba(255,255,255,0.1);padding-top:1rem;'></div>",
                    unsafe_allow_html=True)
        if st.button("Keluar", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    return page

# ─── HELPER: RESOLVE NILAI SEKSI 2 DARI SESSION STATE ────────────────────────────
# FIX: Semua widget Seksi 2 ada di LUAR st.form() sehingga drill-down reaktif.
# Nilai dibaca dari st.session_state saat submit form Seksi 3-4.

def _get_s2_nama() -> str:
    """Kembalikan nama barang final (custom jika Lainnya)."""
    sel = st.session_state.get("s2_nama_sel", "Lainnya")
    if sel == "Lainnya":
        return st.session_state.get("s2_nama_custom", "").strip()
    return sel

def _get_s2_merk() -> str:
    """Kembalikan merk/brand final (custom jika Lainnya)."""
    sel = st.session_state.get("s2_nama_sel", "Lainnya")
    presets = MERK_MAP.get(sel)
    if presets:
        merk_sel = st.session_state.get("s2_merk_sel", presets[0])
        if merk_sel == "Lainnya":
            return st.session_state.get("s2_merk_custom", "").strip() or "-"
        return merk_sel
    return st.session_state.get("s2_merk_free", "").strip() or "-"

def _get_s2_grind() -> str:
    """Kembalikan grind size (hanya aktif untuk Coffee Beans)."""
    kat = st.session_state.get("s2_kategori", "")
    sub = st.session_state.get("s2_sub", "")
    if kat == "Bahan Baku Minuman" and sub == "Coffee Beans":
        return st.session_state.get("s2_grind", "-")
    return "-"

# ─── HELPER: FOTO INVOICE ────────────────────────────────────────────────────────
def render_foto_invoice():
    """
    Tampilkan kamera real-time untuk foto invoice.
    Nama file otomatis: {no_nota}_{cabang}_{tanggal_foto}.jpg
    Simpan ke Supabase Storage bucket 'invoice-foto' jika tersedia,
    atau kembalikan bytes untuk disimpan lokal / ditampilkan.
    Mengembalikan (bytes_foto | None, nama_file | None).
    """
    import io
    foto_bytes = st.camera_input(
        "📷 Foto Invoice (kamera langsung)",
        help="Arahkan kamera ke invoice/nota, lalu tekan tombol untuk mengambil foto",
        key="s1_kamera",
    )
    if foto_bytes is not None:
        nota    = st.session_state.get("s1_nota", "NONOTA").strip() or "NONOTA"
        cabang  = st.session_state.get("cabang",  "CBG").strip()
        tgl_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Bersihkan karakter yang tidak aman untuk nama file
        nota_clean   = "".join(c for c in nota   if c.isalnum() or c in "-_")
        cabang_clean = "".join(c for c in cabang if c.isalnum() or c in "-_")
        nama_file = f"{nota_clean}_{cabang_clean}_{tgl_str}.jpg"

        # Upload ke Supabase Storage jika tersedia
        if supabase:
            try:
                supabase.storage.from_("invoice-foto").upload(
                    path=nama_file,
                    file=foto_bytes.getvalue(),
                    file_options={"content-type": "image/jpeg"},
                )
                st.success(f"Foto tersimpan: **{nama_file}**")
            except Exception as e:
                st.warning(f"Upload ke Storage gagal ({e}). Foto tetap ditampilkan di sini.")
        else:
            st.info(f"Nama file foto: **{nama_file}** (Supabase Storage belum terhubung)")

        return foto_bytes.getvalue(), nama_file
    return None, None

# ─── HELPER: HITUNG KADALUARSA OTOMATIS ─────────────────────────────────────────
def hitung_kadaluarsa_otomatis(nama_barang: str, metode: str, tgl_beli: date):
    """
    Hitung estimasi tanggal kadaluarsa otomatis berdasarkan SHELF_LIFE_MAP.
    Mengembalikan (tgl_min: date, tgl_max: date, label: str) atau (None, None, "").
    """
    from datetime import timedelta
    produk_map = SHELF_LIFE_MAP.get(nama_barang)
    if not produk_map or metode not in produk_map:
        return None, None, ""
    hari_min, hari_max, label = produk_map[metode]
    return (
        tgl_beli + timedelta(days=hari_min),
        tgl_beli + timedelta(days=hari_max),
        label,
    )

# ─── PAGE: DASHBOARD ─────────────────────────────────────────────────────────────
def page_dashboard(df: pd.DataFrame):
    st.title("📊 Dashboard")
    st.caption(f"Cabang **{st.session_state.cabang}** · {datetime.now().strftime('%A, %d %B %Y')}")

    if df.empty:
        empty_state("📊", "Belum Ada Data",
                    "Mulai catat transaksi pertama di halaman Administrasi.")
        return

    df["total_harga"]  = pd.to_numeric(df["total_harga"],  errors="coerce").fillna(0)
    df["harga_satuan"] = pd.to_numeric(df["harga_satuan"], errors="coerce").fillna(0)
    df["qty"]          = pd.to_numeric(df["qty"],          errors="coerce").fillna(0)

    total_keluar = df["total_harga"].sum()
    total_trx    = len(df)
    n_lunas      = len(df[df["status_pembayaran"] == "Lunas"])
    total_hutang = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)]["total_harga"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💸 Total Pengeluaran",    f"Rp {total_keluar:,.0f}")
    c2.metric("📝 Jumlah Transaksi",      total_trx)
    c3.metric("✅ Lunas",               f"{n_lunas} dari {total_trx}")
    c4.metric("⏳ Total Hutang Supplier", f"Rp {total_hutang:,.0f}")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📂 Pengeluaran per Kategori")
        kat = df.groupby("kategori")["total_harga"].sum().reset_index()
        kat.columns = ["Kategori", "Total (Rp)"]
        st.dataframe(kat.sort_values("Total (Rp)", ascending=False),
                     use_container_width=True, hide_index=True)
    with col_b:
        st.subheader("🏪 Top Supplier")
        sup = df.groupby("supplier")["total_harga"].sum().reset_index()
        sup.columns = ["Supplier", "Total (Rp)"]
        st.dataframe(sup.sort_values("Total (Rp)", ascending=False).head(8),
                     use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⚠️ Peringatan Kadaluarsa 30 Hari ke Depan")
    if "tgl_kadaluarsa" in df.columns:
        df_exp = df[
            df["tgl_kadaluarsa"].notna() &
            (df["tgl_kadaluarsa"].astype(str).str.strip().isin(["", "None"]) == False)
        ].copy()
        if not df_exp.empty:
            df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
            today = pd.Timestamp.today().normalize()
            soon  = df_exp[df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30)]
            if not soon.empty:
                cols = [c for c in ["nama_barang","merk","qty","uom","tgl_kadaluarsa"] if c in soon.columns]
                st.dataframe(soon[cols].sort_values("tgl_kadaluarsa"),
                             use_container_width=True, hide_index=True)
            else:
                st.success("Tidak ada barang yang akan kadaluarsa dalam 30 hari ke depan.")
        else:
            st.info("Belum ada data kadaluarsa yang dicatat.")

# ─── PAGE: ADMINISTRASI ───────────────────────────────────────────────────────────
def page_administrasi(df: pd.DataFrame):
    st.title("📋 Administrasi Jejak Rekam Transaksi")

    tab_catat, tab_riwayat, tab_kelola = st.tabs([
        "✏️ Catat Transaksi Baru",
        "📃 Riwayat Transaksi",
        "⚙️ Kelola Data",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1: CATAT TRANSAKSI BARU
    # ARSITEKTUR: Seksi 1+2 di LUAR form (reaktif), Seksi 3+4 di DALAM form.
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_catat:
        st.caption("Kolom bertanda * wajib diisi.")

        # ── SEKSI 1: ADMINISTRASI ─────────────────────────────────────────────
        st.markdown('<p class="form-section-title">📋 Seksi 1 — Administrasi</p>',
                    unsafe_allow_html=True)
        c1a, c1b, c1c = st.columns(3)
        with c1a:
            st.date_input("Tanggal Transaksi *", value=date.today(), key="s1_tgl")
        with c1b:
            st.text_input("Nomor Nota / Invoice", placeholder="Contoh: INV-001", key="s1_nota")
        with c1c:
            st.text_input("Nama Supplier *",
                          placeholder="Contoh: Roastery A, Makmur Plastik", key="s1_sup")

        # Foto invoice — kamera real-time, di luar form agar tidak reload form
        with st.expander("📷 Ambil Foto Invoice (opsional)", expanded=False):
            st.caption("Foto diambil langsung via kamera. Nama file otomatis: `{nota}_{cabang}_{waktu}.jpg`")
            _foto_bytes, _nama_foto = render_foto_invoice()

        st.divider()

        # ── SEKSI 2: IDENTITAS BARANG — DI LUAR FORM ─────────────────────────
        # Karena di luar form, setiap perubahan langsung re-render (reaktif).
        st.markdown('<p class="form-section-title">🏷️ Seksi 2 — Identitas Barang</p>',
                    unsafe_allow_html=True)

        # Baris A: Kategori → Sub Kategori
        ca, cb = st.columns(2)
        with ca:
            st.selectbox("Kategori *", KATEGORI_OPTIONS, key="s2_kategori")
        with cb:
            sub_opts = SUB_KATEGORI_MAP.get(st.session_state.s2_kategori, ["Lainnya"])
            # Reset s2_sub jika tidak valid untuk kategori baru
            if st.session_state.get("s2_sub") not in sub_opts:
                st.session_state["s2_sub"] = sub_opts[0]
            st.selectbox("Sub Kategori *", sub_opts, key="s2_sub")

        # Baris B: Nama Barang → Merk → Grind Size
        cc, cd, ce = st.columns(3)
        with cc:
            nama_opts = NAMA_BARANG_MAP.get(
                (st.session_state.s2_kategori, st.session_state.s2_sub), ["Lainnya"]
            )
            # Reset s2_nama_sel jika tidak valid untuk sub kategori baru
            if st.session_state.get("s2_nama_sel") not in nama_opts:
                st.session_state["s2_nama_sel"] = nama_opts[0]
            st.selectbox(
                "Nama Barang *", nama_opts, key="s2_nama_sel",
                help="Pilih dari daftar, atau pilih 'Lainnya' untuk ketik manual"
            )
            if st.session_state.s2_nama_sel == "Lainnya":
                st.text_input("Ketik Nama Barang Baru *",
                              placeholder="Nama barang yang belum ada di daftar",
                              key="s2_nama_custom")

        with cd:
            presets = MERK_MAP.get(st.session_state.s2_nama_sel)
            if presets:
                st.selectbox("Merk / Brand", presets, key="s2_merk_sel",
                             help="Pilih merk atau 'Lainnya' untuk ketik manual")
                if st.session_state.get("s2_merk_sel") == "Lainnya":
                    st.text_input("Ketik Merk / Brand Baru",
                                  placeholder="Masukkan merk baru", key="s2_merk_custom")
            else:
                st.text_input("Merk / Brand",
                              placeholder="Contoh: Diamond, Fiesta, Homemade",
                              key="s2_merk_free")

        with ce:
            is_kopi = (st.session_state.s2_kategori == "Bahan Baku Minuman"
                       and st.session_state.s2_sub == "Coffee Beans")
            if is_kopi:
                st.selectbox("Grind Size (Khusus Kopi) *", GRIND_OPTIONS, key="s2_grind")
            else:
                st.selectbox("Grind Size", ["-"], key="s2_grind_dis",
                             disabled=True, help="Hanya aktif untuk Coffee Beans")

        # Info Digunakan di Menu — reaktif karena di luar form
        nama_sel_now = st.session_state.get("s2_nama_sel", "")
        digunakan_now = DIGUNAKAN_DI_MENU.get(nama_sel_now, "")
        if digunakan_now:
            st.info(f"🍽️ **Digunakan di Menu:** {digunakan_now}")
        elif nama_sel_now == "Lainnya":
            st.caption("Info menu tidak tersedia untuk barang baru. Bisa dicatat di kolom Catatan.")
        else:
            st.caption("Pilih nama barang untuk melihat info penggunaan di menu.")

        st.divider()

        # ── SEKSI 3 & 4: DALAM FORM ───────────────────────────────────────────
        st.markdown('<p class="form-section-title">📦 Seksi 3 — Detail Stok & Harga</p>',
                    unsafe_allow_html=True)

        with st.form("form_catat", clear_on_submit=True):
            cf, cg, ch = st.columns(3)
            with cf:
                f_qty   = st.number_input("Kuantitas (Qty) *", min_value=0.0,
                                          step=0.5, format="%.2f")
            with cg:
                f_uom   = st.selectbox("Satuan (UoM) *", UOM_OPTIONS)
            with ch:
                f_harga = st.number_input("Harga Satuan (Rp) *", min_value=0, step=500)

            f_total = f_qty * f_harga
            st.info(f"💰 **Total Harga:** Rp {f_total:,.0f}  ·  {f_qty} {f_uom} × Rp {f_harga:,.0f}")

            st.divider()
            st.markdown('<p class="form-section-title">🔍 Seksi 4 — Kontrol & Audit</p>',
                        unsafe_allow_html=True)

            # Cek apakah barang yang dipilih ada di SHELF_LIFE_MAP (tidak ada expired di kemasan)
            nama_untuk_shelf = st.session_state.get("s2_nama_sel", "")
            if nama_untuk_shelf == "Lainnya":
                nama_untuk_shelf = st.session_state.get("s2_nama_custom", "").strip()
            ada_di_shelf_map = nama_untuk_shelf in SHELF_LIFE_MAP

            ci, cj = st.columns(2)
            with ci:
                if ada_di_shelf_map:
                    # Produk tanpa expired date di kemasan → pilih metode simpan
                    metode_opts = METODE_SIMPAN_OPTIONS.copy()
                    metode_tersedia = list(SHELF_LIFE_MAP[nama_untuk_shelf].keys())
                    # Filter hanya metode yang relevan untuk produk ini
                    metode_opts = ["Pilih metode penyimpanan..."] + metode_tersedia
                    f_metode = st.selectbox(
                        f"🌡️ Metode Penyimpanan *",
                        metode_opts,
                        key="s4_metode",
                        help=f"Pilih cara penyimpanan untuk estimasi kadaluarsa otomatis"
                    )
                    # Hitung estimasi kadaluarsa
                    tgl_beli = st.session_state.get("s1_tgl", date.today())
                    if f_metode != "Pilih metode penyimpanan...":
                        tgl_min, tgl_max, shelf_label = hitung_kadaluarsa_otomatis(
                            nama_untuk_shelf, f_metode, tgl_beli
                        )
                        if tgl_min:
                            st.success(
                                f"📅 **Estimasi Kadaluarsa:** {tgl_min.strftime('%d %b %Y')} "
                                f"s/d {tgl_max.strftime('%d %b %Y')}\n\n"
                                f"_{shelf_label}_"
                            )
                            # Gunakan titik tengah sebagai tanggal kadaluarsa yang disimpan
                            from datetime import timedelta
                            f_exp = tgl_min + (tgl_max - tgl_min) // 2
                        else:
                            f_exp = None
                    else:
                        f_exp = None
                        st.caption("⬆️ Pilih metode penyimpanan untuk estimasi kadaluarsa otomatis.")
                else:
                    # Produk dengan kemasan ber-expired date → pilih manual
                    f_exp = st.date_input(
                        "Tanggal Kadaluarsa",
                        value=None,
                        help="Isi sesuai tanggal expired yang tertera di kemasan. Kosongkan jika tidak relevan (Packaging, dll)."
                    )

            with cj:
                f_status = st.selectbox("Status Pembayaran *", STATUS_OPTIONS)

            f_catatan = st.text_area(
                "Catatan Tambahan",
                placeholder="Contoh: Tutup botol retak sudah diretur · Dapat diskon 5%",
                height=80,
            )

            submit = st.form_submit_button("💾 Simpan Transaksi",
                                           type="primary", use_container_width=True)

        # ── PROSES SUBMIT ─────────────────────────────────────────────────────
        if submit:
            # Baca semua nilai Seksi 1 & 2 dari session_state
            sup_val   = st.session_state.get("s1_sup",  "").strip()
            nota_val  = st.session_state.get("s1_nota", "").strip()
            tgl_val   = st.session_state.get("s1_tgl",  date.today())
            kat_val   = st.session_state.get("s2_kategori", KATEGORI_OPTIONS[0])
            sub_val   = st.session_state.get("s2_sub",  "")
            nama_val  = _get_s2_nama()
            merk_val  = _get_s2_merk()
            grind_val = _get_s2_grind()

            errors = []
            if not sup_val:      errors.append("Nama Supplier")
            if not nama_val:     errors.append("Nama Barang (isi kolom 'Ketik Nama Barang Baru')")
            if f_qty  <= 0:      errors.append("Kuantitas harus lebih dari 0")
            if f_harga <= 0:     errors.append("Harga Satuan harus lebih dari 0")

            if errors:
                st.error("Harap lengkapi: " + " · ".join(errors))
            else:
                ok = insert_row({
                    "cabang":            st.session_state.cabang,
                    "tanggal":           tgl_val.isoformat(),
                    "no_nota":           nota_val or None,
                    "supplier":          sup_val,
                    "kategori":          kat_val,
                    "sub_kategori":      sub_val,
                    "nama_barang":       nama_val,
                    "merk":              merk_val,
                    "grind_size":        grind_val,
                    "qty":               float(f_qty),
                    "uom":               f_uom,
                    "harga_satuan":      int(f_harga),
                    "total_harga":       int(f_total),
                    "tgl_kadaluarsa":    f_exp.isoformat() if f_exp else None,
                    "status_pembayaran": f_status,
                    "catatan":           f_catatan.strip() or None,
                })
                if ok:
                    st.success(f"Transaksi **{nama_val}** dari **{sup_val}** berhasil dicatat!")
                    st.balloons()

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: RIWAYAT TRANSAKSI
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_riwayat:
        if df.empty:
            empty_state("📃", "Belum Ada Riwayat",
                        "Catat transaksi pertama di tab 'Catat Transaksi Baru'.")
        else:
            rf1, rf2, rf3, rf4 = st.columns(4)
            with rf1:
                cari    = st.text_input("Cari nama barang / supplier", key="r_cari")
            with rf2:
                fil_kat = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="r_kat")
            with rf3:
                fil_st  = st.selectbox("Status", ["Semua"] + STATUS_OPTIONS, key="r_st")
            with rf4:
                fil_bln = st.text_input("Bulan (YYYY-MM)", placeholder="2025-07", key="r_bln")

            hasil = df.copy()
            if cari:
                mask = (
                    hasil["nama_barang"].str.contains(cari, case=False, na=False) |
                    hasil["supplier"].str.contains(cari, case=False, na=False)
                )
                hasil = hasil[mask]
            if fil_kat != "Semua":
                hasil = hasil[hasil["kategori"] == fil_kat]
            if fil_st != "Semua":
                hasil = hasil[hasil["status_pembayaran"] == fil_st]
            if fil_bln:
                hasil = hasil[hasil["tanggal"].astype(str).str.startswith(fil_bln)]

            cols_show = [c for c in ["tanggal","no_nota","supplier","nama_barang","merk",
                                     "kategori","qty","uom","harga_satuan","total_harga",
                                     "status_pembayaran"] if c in hasil.columns]
            urut = hasil.sort_values("tanggal", ascending=False) if "tanggal" in hasil.columns else hasil
            st.dataframe(urut[cols_show], use_container_width=True, hide_index=True)
            total_f = pd.to_numeric(hasil["total_harga"], errors="coerce").sum()
            st.caption(f"**{len(hasil)}** transaksi · Total: **Rp {total_f:,.0f}**")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3: KELOLA DATA (Manager only)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_kelola:
        if st.session_state.role != "manager":
            st.info("Fitur edit dan hapus hanya tersedia untuk Manager.")
            return

        if df.empty:
            empty_state("⚙️", "Belum Ada Data", "Belum ada transaksi yang bisa dikelola.")
            return

        if "id" not in df.columns:
            st.warning("Kolom ID tidak tersedia dari database.")
            return

        col_sel, _ = st.columns([1, 2])
        with col_sel:
            id_pilih = st.selectbox(
                "Pilih ID Transaksi",
                df["id"].tolist(),
                format_func=lambda x: (
                    f"ID {x} — "
                    + str(df.loc[df["id"] == x, "nama_barang"].values[0])
                    if not df[df["id"] == x].empty else f"ID {x}"
                ),
                key="kelola_id",
            )

        baris = df[df["id"] == id_pilih]
        if baris.empty:
            return

        row = baris.iloc[0]
        st.markdown(f"**Terpilih:** {row.get('nama_barang','-')} · "
                    f"{row.get('supplier','-')} · {row.get('tanggal','-')}")

        # ── EDIT ──────────────────────────────────────────────────────────────
        with st.expander("✏️ Edit Transaksi Ini", expanded=False):
            with st.form(f"form_edit_{id_pilih}"):
                ea, eb, ec = st.columns(3)
                with ea:
                    e_tgl  = st.date_input("Tanggal",
                        value=pd.to_datetime(row.get("tanggal", date.today())).date())
                    e_nota = st.text_input("No. Nota", value=str(row.get("no_nota") or ""))
                with eb:
                    e_sup  = st.text_input("Supplier", value=str(row.get("supplier") or ""))
                    kat_n  = row.get("kategori", KATEGORI_OPTIONS[0])
                    e_kat  = st.selectbox("Kategori", KATEGORI_OPTIONS,
                        index=KATEGORI_OPTIONS.index(kat_n) if kat_n in KATEGORI_OPTIONS else 0)
                with ec:
                    sub_l = SUB_KATEGORI_MAP.get(e_kat, ["Lainnya"])
                    sub_n = row.get("sub_kategori", sub_l[0])
                    e_sub = st.selectbox("Sub Kategori", sub_l,
                        index=sub_l.index(sub_n) if sub_n in sub_l else 0)

                ed, ee, ef = st.columns(3)
                with ed:
                    nama_opts = NAMA_BARANG_MAP.get((e_kat, e_sub), ["Lainnya"])
                    cur_nama  = row.get("nama_barang", "")
                    nama_idx  = nama_opts.index(cur_nama) if cur_nama in nama_opts else len(nama_opts) - 1
                    e_nama_sel = st.selectbox("Nama Barang", nama_opts, index=nama_idx,
                                              key=f"e_nama_{id_pilih}")
                    if e_nama_sel == "Lainnya":
                        e_nama = st.text_input("Ketik Nama Barang Baru",
                            value=cur_nama if cur_nama not in nama_opts else "",
                            key=f"e_nama_c_{id_pilih}")
                    else:
                        e_nama = e_nama_sel

                with ee:
                    cur_merk = str(row.get("merk") or "")
                    merk_pre = MERK_MAP.get(e_nama_sel)
                    if merk_pre:
                        mk_idx = merk_pre.index(cur_merk) if cur_merk in merk_pre else len(merk_pre) - 1
                        e_merk_sel = st.selectbox("Merk / Brand", merk_pre, index=mk_idx,
                                                  key=f"e_merk_{id_pilih}")
                        if e_merk_sel == "Lainnya":
                            e_merk = st.text_input("Ketik Merk Baru",
                                value=cur_merk if cur_merk not in merk_pre else "",
                                key=f"e_merk_c_{id_pilih}")
                        else:
                            e_merk = e_merk_sel
                    else:
                        e_merk = st.text_input("Merk / Brand", value=cur_merk,
                                               key=f"e_merk_f_{id_pilih}")

                with ef:
                    e_qty  = st.number_input("Qty", value=float(row.get("qty", 0)),
                                             min_value=0.0, step=0.5)
                    uom_n  = row.get("uom", UOM_OPTIONS[0])
                    e_uom  = st.selectbox("UoM", UOM_OPTIONS,
                        index=UOM_OPTIONS.index(uom_n) if uom_n in UOM_OPTIONS else 0)

                eg, eh = st.columns(2)
                with eg:
                    e_hrg = st.number_input("Harga Satuan (Rp)",
                        value=int(row.get("harga_satuan", 0)), min_value=0, step=500)
                with eh:
                    st_n  = row.get("status_pembayaran", STATUS_OPTIONS[0])
                    e_st  = st.selectbox("Status Pembayaran", STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(st_n) if st_n in STATUS_OPTIONS else 0)

                exp_raw = row.get("tgl_kadaluarsa")
                exp_v   = pd.to_datetime(exp_raw).date() \
                          if exp_raw and str(exp_raw) not in ("None", "") else None
                e_exp   = st.date_input("Tanggal Kadaluarsa", value=exp_v)
                e_cat   = st.text_area("Catatan", value=str(row.get("catatan") or ""), height=70)

                e_total = e_qty * e_hrg
                st.info(f"Total Harga: **Rp {e_total:,.0f}**")

                if st.form_submit_button("Simpan Perubahan", type="primary"):
                    ok = update_row(id_pilih, {
                        "tanggal":           e_tgl.isoformat(),
                        "no_nota":           e_nota or None,
                        "supplier":          e_sup,
                        "kategori":          e_kat,
                        "sub_kategori":      e_sub,
                        "nama_barang":       e_nama,
                        "merk":              e_merk or "-",
                        "qty":               float(e_qty),
                        "uom":               e_uom,
                        "harga_satuan":      int(e_hrg),
                        "total_harga":       int(e_total),
                        "tgl_kadaluarsa":    e_exp.isoformat() if e_exp else None,
                        "status_pembayaran": e_st,
                        "catatan":           e_cat or None,
                    })
                    if ok:
                        st.success("Data berhasil diperbarui!")
                        st.rerun()

        # ── HAPUS ─────────────────────────────────────────────────────────────
        with st.expander("🗑️ Hapus Transaksi Ini", expanded=False):
            st.warning(
                f"Kamu akan menghapus: **{row.get('nama_barang','-')}** "
                f"dari **{row.get('supplier','-')}**. Tindakan ini tidak bisa dibatalkan."
            )
            konfirm = st.text_input('Ketik HAPUS untuk konfirmasi', key="konfirm_hapus")
            if st.button("Hapus Sekarang", type="primary", key="btn_hapus"):
                if konfirm.strip().upper() == "HAPUS":
                    ok = delete_row(id_pilih)
                    if ok:
                        st.success("Transaksi berhasil dihapus.")
                        st.rerun()
                else:
                    st.error('Ketik kata HAPUS (huruf kapital semua) untuk konfirmasi.')

# ─── PAGE: IDENTITAS BARANG ───────────────────────────────────────────────────────
def page_identitas(df: pd.DataFrame):
    st.title("🏷️ Identitas Barang")

    if df.empty:
        empty_state("🏷️", "Belum Ada Barang Tercatat",
                    "Catat transaksi terlebih dahulu untuk melihat katalog barang.")
        return

    cf1, cf2 = st.columns(2)
    with cf1:
        fil_kat = st.selectbox("Filter Kategori", ["Semua"] + KATEGORI_OPTIONS, key="id_kat")
    with cf2:
        cari = st.text_input("Cari Nama Barang / Merk", key="id_cari")

    tampil = df.copy()
    if fil_kat != "Semua":
        tampil = tampil[tampil["kategori"] == fil_kat]
    if cari:
        tampil = tampil[
            tampil["nama_barang"].str.contains(cari, case=False, na=False) |
            tampil["merk"].str.contains(cari, case=False, na=False)
        ]

    st.markdown("---")
    st.subheader("📦 Katalog Barang Unik")
    katalog_cols = [c for c in ["kategori","sub_kategori","nama_barang","merk","grind_size","uom"]
                    if c in tampil.columns]
    if not tampil.empty:
        unik = tampil[katalog_cols].drop_duplicates().sort_values("nama_barang")
        st.dataframe(unik, use_container_width=True, hide_index=True)
        st.caption(f"{len(unik)} jenis barang unik")
    else:
        st.info("Tidak ada barang sesuai filter.")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📊 Transaksi per Sub Kategori")
        if "sub_kategori" in tampil.columns and not tampil.empty:
            sub = tampil.groupby(["kategori","sub_kategori"]).size().reset_index(name="Jml Transaksi")
            st.dataframe(sub.sort_values("Jml Transaksi", ascending=False),
                         use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("🔍 Riwayat per Barang")
        if "nama_barang" in tampil.columns and not tampil.empty:
            barang_list = sorted(tampil["nama_barang"].dropna().unique().tolist())
            pilih = st.selectbox("Pilih Barang", barang_list, key="id_barang")
            detail = tampil[tampil["nama_barang"] == pilih]
            st.write(f"**{len(detail)} transaksi** untuk *{pilih}*")
            dc = [c for c in ["tanggal","supplier","merk","qty","uom",
                               "harga_satuan","total_harga","status_pembayaran"]
                  if c in detail.columns]
            st.dataframe(detail[dc], use_container_width=True, hide_index=True)

# ─── PAGE: DETAIL STOK ───────────────────────────────────────────────────────────
def page_detail_stok(df: pd.DataFrame):
    st.title("📦 Detail Stok")

    if df.empty:
        empty_state("📦", "Belum Ada Data Stok",
                    "Data stok muncul otomatis setelah transaksi dicatat.")
        return

    df["qty"]          = pd.to_numeric(df["qty"],          errors="coerce").fillna(0)
    df["harga_satuan"] = pd.to_numeric(df["harga_satuan"], errors="coerce").fillna(0)
    df["total_harga"]  = pd.to_numeric(df["total_harga"],  errors="coerce").fillna(0)

    st.subheader("💰 Ringkasan Finansial")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Pengeluaran",       f"Rp {df['total_harga'].sum():,.0f}")
    c2.metric("Rata-rata per Transaksi", f"Rp {df['total_harga'].mean():,.0f}")
    c3.metric("Transaksi Terbesar",      f"Rp {df['total_harga'].max():,.0f}")
    c4.metric("Jenis Barang Unik",       df["nama_barang"].nunique() if "nama_barang" in df.columns else 0)

    st.markdown("---")
    col_kiri, col_kanan = st.columns(2)
    with col_kiri:
        st.subheader("📊 Akumulasi Stok per Barang")
        if "nama_barang" in df.columns:
            grp = df.groupby(["nama_barang","uom"]).agg(
                Total_Qty     =("qty",          "sum"),
                Total_Spend   =("total_harga",  "sum"),
                Rata_Harga    =("harga_satuan", "mean"),
                Jml_Transaksi =("total_harga",  "count"),
            ).reset_index()
            grp.columns = ["Nama Barang","UoM","Total Qty",
                           "Total Spend (Rp)","Rata-rata Harga (Rp)","Jml Transaksi"]
            st.dataframe(grp.sort_values("Total Spend (Rp)", ascending=False),
                         use_container_width=True, hide_index=True)

    with col_kanan:
        st.subheader("📈 Tren Harga Satuan")
        if "nama_barang" in df.columns and not df.empty:
            pilih = st.selectbox("Pilih barang", sorted(df["nama_barang"].dropna().unique()),
                                 key="tren_pilih")
            tren = df[df["nama_barang"] == pilih][["tanggal","harga_satuan"]].copy()
            tren["tanggal"] = pd.to_datetime(tren["tanggal"], errors="coerce")
            tren = tren.dropna().sort_values("tanggal")
            if len(tren) >= 2:
                st.line_chart(tren.rename(columns={"tanggal":"Tanggal",
                                                   "harga_satuan":"Harga Satuan (Rp)"})
                                  .set_index("Tanggal"))
            elif len(tren) == 1:
                st.info("Baru 1 catatan harga. Butuh minimal 2 untuk tampilkan tren.")
            else:
                st.info("Tidak ada data harga.")

    st.markdown("---")
    st.subheader("🗓️ Pengeluaran per Bulan")
    if "tanggal" in df.columns:
        df["bulan"] = pd.to_datetime(df["tanggal"], errors="coerce").dt.to_period("M").astype(str)
        monthly = df.groupby("bulan")["total_harga"].sum().reset_index()
        monthly.columns = ["Bulan", "Total (Rp)"]
        if not monthly.empty:
            st.bar_chart(monthly.sort_values("Bulan").set_index("Bulan"))

# ─── PAGE: KONTROL & AUDIT ────────────────────────────────────────────────────────
def page_kontrol_audit(df: pd.DataFrame):
    st.title("🔍 Kontrol & Audit")

    if df.empty:
        empty_state("🔍", "Belum Ada Data untuk Diaudit",
                    "Data audit muncul setelah transaksi dicatat.")
        return

    df["total_harga"] = pd.to_numeric(df["total_harga"], errors="coerce").fillna(0)

    tab_exp, tab_kas, tab_log = st.tabs([
        "⏰ Monitor Kadaluarsa",
        "💳 Arus Kas & Hutang",
        "📋 Audit Log",
    ])

    # ── KADALUARSA ───────────────────────────────────────────────────────────────
    with tab_exp:
        st.subheader("📅 Status Kadaluarsa Barang")
        if "tgl_kadaluarsa" not in df.columns:
            st.info("Kolom kadaluarsa tidak tersedia.")
        else:
            df_exp = df[
                df["tgl_kadaluarsa"].notna() &
                (df["tgl_kadaluarsa"].astype(str).str.strip().isin(["", "None"]) == False)
            ].copy()

            if df_exp.empty:
                empty_state("📅", "Belum Ada Data Kadaluarsa",
                            "Isi kolom Tanggal Kadaluarsa saat mencatat transaksi bahan baku.")
            else:
                df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
                today    = pd.Timestamp.today().normalize()
                kritis   = df_exp[df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=7)]
                mendekat = df_exp[
                    (df_exp["tgl_kadaluarsa"] >  today + pd.Timedelta(days=7)) &
                    (df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30))
                ]
                aman = df_exp[df_exp["tgl_kadaluarsa"] > today + pd.Timedelta(days=30)]

                c1, c2, c3 = st.columns(3)
                c1.metric("🔴 Kritis (≤7 hari)",    len(kritis))
                c2.metric("🟡 Mendekat (8–30 hari)", len(mendekat))
                c3.metric("🟢 Aman (>30 hari)",      len(aman))

                exp_cols = [c for c in ["nama_barang","merk","qty","uom","tgl_kadaluarsa","catatan"]
                            if c in df_exp.columns]
                if not kritis.empty:
                    st.error("🚨 Barang Kritis — Segera Pakai atau Retur ke Supplier!")
                    st.dataframe(kritis[exp_cols].sort_values("tgl_kadaluarsa"),
                                 use_container_width=True, hide_index=True)
                if not mendekat.empty:
                    st.warning("⚠️ Akan Kadaluarsa dalam 30 Hari")
                    st.dataframe(mendekat[exp_cols].sort_values("tgl_kadaluarsa"),
                                 use_container_width=True, hide_index=True)
                if not aman.empty:
                    with st.expander(f"✅ Barang Aman ({len(aman)} item)"):
                        st.dataframe(aman[exp_cols].sort_values("tgl_kadaluarsa"),
                                     use_container_width=True, hide_index=True)

    # ── ARUS KAS ─────────────────────────────────────────────────────────────────
    with tab_kas:
        st.subheader("💸 Ringkasan Arus Kas Keluar")
        total_all    = df["total_harga"].sum()
        total_lunas  = df[df["status_pembayaran"] == "Lunas"]["total_harga"].sum()
        total_hutang = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)]["total_harga"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Keluar",             f"Rp {total_all:,.0f}")
        c2.metric("✅ Sudah Lunas",            f"Rp {total_lunas:,.0f}")
        c3.metric("⏳ Belum Lunas / Hutang",  f"Rp {total_hutang:,.0f}")

        st.markdown("---")
        st.subheader("📋 Transaksi Belum Lunas")
        belum = df[df["status_pembayaran"] != "Lunas"]
        if not belum.empty:
            bl_cols = [c for c in ["tanggal","no_nota","supplier","nama_barang",
                                   "total_harga","status_pembayaran","catatan"]
                       if c in belum.columns]
            bl_sorted = belum[bl_cols].sort_values("tanggal") if "tanggal" in belum.columns else belum[bl_cols]
            st.dataframe(bl_sorted, use_container_width=True, hide_index=True)
            st.caption(f"Total hutang: **Rp {total_hutang:,.0f}**")
        else:
            st.success("Semua transaksi sudah berstatus Lunas!")

        if st.session_state.role == "manager":
            st.markdown("---")
            st.subheader("📊 Pengeluaran per Supplier")
            sup_grp = df.groupby(["supplier","status_pembayaran"])["total_harga"].sum().reset_index()
            sup_grp.columns = ["Supplier","Status","Total (Rp)"]
            st.dataframe(sup_grp.sort_values("Total (Rp)", ascending=False),
                         use_container_width=True, hide_index=True)

    # ── AUDIT LOG ────────────────────────────────────────────────────────────────
    with tab_log:
        st.subheader("📋 Log Seluruh Transaksi")

        lf1, lf2, lf3 = st.columns(3)
        with lf1:
            kat_f  = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="log_kat")
        with lf2:
            sort_f = st.selectbox("Urutkan", ["tanggal","total_harga","supplier","nama_barang"],
                                  key="log_sort")
        with lf3:
            asc_f  = st.selectbox("Urutan", ["Terbaru dulu","Terlama dulu"], key="log_asc")

        log_df = df.copy()
        if kat_f != "Semua":
            log_df = log_df[log_df["kategori"] == kat_f]
        if sort_f in log_df.columns:
            log_df = log_df.sort_values(sort_f, ascending=(asc_f == "Terlama dulu"))

        st.dataframe(log_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(log_df)} catatan ditampilkan")

        if st.session_state.role == "manager":
            st.markdown("---")
            csv = log_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Export CSV",
                data=csv,
                file_name=f"inventaris_{st.session_state.cabang}_{date.today()}.csv",
                mime="text/csv",
            )

# ─── MAIN ────────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        show_login()
        return

    page = show_sidebar()
    df   = get_data(st.session_state.cabang)

    if   page == "📊 Dashboard":        page_dashboard(df)
    elif page == "📋 Administrasi":     page_administrasi(df)
    elif page == "🏷️ Identitas Barang": page_identitas(df)
    elif page == "📦 Detail Stok":      page_detail_stok(df)
    elif page == "🔍 Kontrol & Audit":  page_kontrol_audit(df)

if __name__ == "__main__":
    main()
