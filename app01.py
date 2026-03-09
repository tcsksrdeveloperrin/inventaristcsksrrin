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

# Satuan Kuantitas Unit yang Dibeli — berapa kemasan/unit diterima dari supplier
UOM_QTY_OPTIONS = [
    "pcs", "pack", "dus / karton", "kantong", "botol",
    "lusin", "ikat", "buah", "ekor", "bungkus",
    "tray", "galon", "roll", "sachet",
    "lembar", "bal", "porsi",
]

# Satuan Berat / Volume per Satu Unit yang Dibeli
VOL_OPTIONS = ["ml", "liter", "gram (g)", "kg", "mg", "ons"]

# Faktor konversi ke unit dasar (gram/ml) untuk kalkulasi netto total
VOL_FAKTOR = {
    "ml": 1, "liter": 1000,
    "gram (g)": 1, "kg": 1000, "mg": 0.001, "ons": 100,
}

# Faktor pengali untuk satuan qty yang punya jumlah pcs baku
QTY_MULTIPLIER = {
    "lusin": 12,
    # Semua lainnya = 1 (tidak bisa diasumsi, tergantung produk)
}

GRIND_OPTIONS  = ["-", "Whole Bean", "V60 (5-6)", "Vietnam Drip (3-4)", "Espresso (2-3)", "French Press (7-8)"]
STATUS_OPTIONS = ["Lunas", "Tempo (Hutang)", "DP/Uang Muka"]

# ─── SHELF LIFE MAP ──────────────────────────────────────────────────────────────
# Produk yang TIDAK atau MUNGKIN TIDAK memiliki expired date di kemasan.
# Program menghitung estimasi otomatis berdasarkan metode penyimpanan.
# Format: { nama_barang: { metode_simpan: (hari_min, hari_max, keterangan) } }

METODE_SIMPAN_OPTIONS = [
    "Pilih metode penyimpanan...",
    "Suhu Ruang",
    "Kulkas (1–4 °C)",
    "Pendingin / Chiller (4–10 °C)",
    "Freezer (≤ −18 °C)",
    "Wadah Kering / Kedap Udara",
]

SHELF_LIFE_MAP = {

    # ══════════════════════════════════════════════════════════════════════════
    # BAHAN BAKU MAKANAN — Protein
    # ══════════════════════════════════════════════════════════════════════════
    "Telur Ayam": {
        "Suhu Ruang":               (7,  21,  "1–3 minggu · suhu ruang"),
        "Kulkas (1–4 °C)":          (28, 42,  "4–6 minggu · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (21, 35, "3–5 minggu · chiller"),
        "Freezer (≤ −18 °C)":       (90, 365, "3–12 bulan · freezer (sudah dikocok/dipisah)"),
    },
    "Ayam Fillet / Ayam Potong": {
        "Suhu Ruang":               (0,  0,   "Maks 2 jam · suhu ruang — segera masak!"),
        "Kulkas (1–4 °C)":          (1,  2,   "1–2 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (1,  1, "Maks 1 hari · chiller"),
        "Freezer (≤ −18 °C)":       (90, 270, "3–9 bulan · freezer"),
    },
    "Daging Kambing": {
        "Kulkas (1–4 °C)":          (3,  5,   "3–5 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (2, 3,  "2–3 hari · chiller"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer"),
    },
    "Ikan Jambal Roti": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (sudah dikeringkan/diasin)"),
        "Kulkas (1–4 °C)":          (30, 60,  "1–2 bulan · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (20, 45, "3–6 minggu · chiller"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer"),
        "Wadah Kering / Kedap Udara": (30, 60, "1–2 bulan · suhu ruang wadah kedap udara"),
    },
    "Tahu Putih / Tahu Goreng": {
        "Suhu Ruang":               (0,  1,   "Maks 1 hari · suhu ruang"),
        "Kulkas (1–4 °C)":          (3,  5,   "3–5 hari · kulkas (rendam air, ganti tiap hari)"),
        "Pendingin / Chiller (4–10 °C)": (2, 3,  "2–3 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 60,  "1–2 bulan · freezer (tekstur berubah, cocok untuk dimasak)"),
    },
    "Tempe": {
        "Suhu Ruang":               (1,  2,   "1–2 hari · suhu ruang"),
        "Kulkas (1–4 °C)":          (5,  7,   "5–7 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (3, 5,  "3–5 hari · chiller"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer"),
    },
    "Oncom": {
        "Suhu Ruang":               (1,  2,   "1–2 hari · suhu ruang"),
        "Kulkas (1–4 °C)":          (4,  6,   "4–6 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (2, 4,  "2–4 hari · chiller"),
        "Freezer (≤ −18 °C)":       (60, 90,  "2–3 bulan · freezer"),
    },
    "Bakso": {
        "Kulkas (1–4 °C)":          (3,  5,   "3–5 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (2, 3,  "2–3 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 90,  "1–3 bulan · freezer"),
    },
    "Seafood Mix (Cumi, Udang, dll)": {
        "Kulkas (1–4 °C)":          (1,  2,   "1–2 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (0, 1,  "Maks 1 hari · chiller"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer"),
    },
    "Abon Sapi / Abon Ayam": {
        "Suhu Ruang":               (30, 60,  "1–2 bulan · suhu ruang (kemasan belum dibuka)"),
        "Kulkas (1–4 °C)":          (60, 90,  "2–3 bulan · kulkas (kemasan terbuka)"),
        "Wadah Kering / Kedap Udara": (30, 60, "1–2 bulan · wadah kedap udara"),
    },
    "Sosis Ayam / Sosis Sapi": {
        "Kulkas (1–4 °C)":          (3,  7,   "3–7 hari · kulkas (kemasan dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (2, 5,  "2–5 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 60,  "1–2 bulan · freezer"),
    },
    "Pempek Original": {
        "Suhu Ruang":               (0,  1,   "Maks 1 hari · suhu ruang (sudah dimasak)"),
        "Kulkas (1–4 °C)":          (3,  5,   "3–5 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (2, 3,  "2–3 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 90,  "1–3 bulan · freezer (mentah/setengah matang)"),
    },
    "Pempek Kapal Selam": {
        "Suhu Ruang":               (0,  1,   "Maks 1 hari · suhu ruang (sudah dimasak)"),
        "Kulkas (1–4 °C)":          (3,  5,   "3–5 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (2, 3,  "2–3 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 90,  "1–3 bulan · freezer (mentah/setengah matang)"),
    },
    "Risoles": {
        "Kulkas (1–4 °C)":          (2,  3,   "2–3 hari · kulkas (mentah, belum digoreng)"),
        "Pendingin / Chiller (4–10 °C)": (1, 2,  "1–2 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 60,  "1–2 bulan · freezer (mentah, belum digoreng)"),
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BAHAN BAKU MAKANAN — Fresh & Produce
    # ══════════════════════════════════════════════════════════════════════════
    "Beras (Nasi Putih)": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (beras mentah, wadah tertutup)"),
        "Wadah Kering / Kedap Udara": (365, 730, "1–2 tahun · wadah kedap udara"),
    },
    "Kwetiau / Mie Kwetiau": {
        "Suhu Ruang":               (1,  2,   "1–2 hari · suhu ruang (kwetiau basah segar)"),
        "Kulkas (1–4 °C)":          (3,  5,   "3–5 hari · kulkas (kwetiau basah)"),
        "Pendingin / Chiller (4–10 °C)": (2, 3,  "2–3 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 90,  "1–3 bulan · freezer"),
    },
    "Kol / Kubis": {
        "Suhu Ruang":               (3,  5,   "3–5 hari · suhu ruang"),
        "Kulkas (1–4 °C)":          (14, 21,  "2–3 minggu · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (10, 18, "10–18 hari · chiller"),
    },
    "Pisang Kepok / Cavendish": {
        "Suhu Ruang":               (3,  7,   "3–7 hari · suhu ruang (tergantung kematangan)"),
        "Kulkas (1–4 °C)":          (7,  14,  "1–2 minggu · kulkas (kulit menghitam, daging tetap baik)"),
        "Pendingin / Chiller (4–10 °C)": (5, 10, "5–10 hari · chiller"),
    },
    "Kentang": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (tempat gelap & kering)"),
        "Kulkas (1–4 °C)":          (30, 60,  "1–2 bulan · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (21, 45, "3–6 minggu · chiller"),
        "Wadah Kering / Kedap Udara": (30, 60, "1–2 bulan · tempat gelap kering"),
    },
    "Sayuran Capcay (Wortel, Sawi, Jagung muda, dll)": {
        "Suhu Ruang":               (1,  2,   "1–2 hari · suhu ruang"),
        "Kulkas (1–4 °C)":          (5,  7,   "5–7 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (3, 5,  "3–5 hari · chiller"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer (sudah di-blanching)"),
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BAHAN BAKU MAKANAN — Adonan & Tepung
    # ══════════════════════════════════════════════════════════════════════════
    "Adonan Surabi (Tepung Beras + Santan)": {
        "Kulkas (1–4 °C)":          (1,  2,   "1–2 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (0, 1,  "Maks 1 hari · chiller"),
        "Freezer (≤ −18 °C)":       (7,  14,  "1–2 minggu · freezer"),
    },
    "Beras Ketan": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (mentah, kering)"),
        "Wadah Kering / Kedap Udara": (365, 730, "1–2 tahun · wadah kedap udara"),
    },
    "Tepung Terigu": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (kemasan tertutup)"),
        "Wadah Kering / Kedap Udara": (365, 548, "1–1,5 tahun · wadah kedap udara"),
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BAHAN BAKU MAKANAN — Dairy & Topping
    # ══════════════════════════════════════════════════════════════════════════
    "Keju Cheddar": {
        "Kulkas (1–4 °C)":          (14, 30,  "2–4 minggu · kulkas (kemasan dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (7, 14, "1–2 minggu · chiller"),
        "Freezer (≤ −18 °C)":       (60, 180, "2–6 bulan · freezer (tekstur sedikit berubah)"),
    },
    "Keju Mozarella": {
        "Kulkas (1–4 °C)":          (7,  21,  "1–3 minggu · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (5, 14, "5–14 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 90,  "1–3 bulan · freezer"),
    },
    "Meses / Cokelat Serut": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (kemasan tertutup, tempat sejuk)"),
        "Wadah Kering / Kedap Udara": (180, 365, "6–12 bulan · wadah kedap udara"),
    },
    "Pasta Cokelat / Dark Chocolate": {
        "Suhu Ruang":               (90, 180,  "3–6 bulan · suhu ruang (sejuk, tidak kena sinar langsung)"),
        "Kulkas (1–4 °C)":          (180, 365, "6–12 bulan · kulkas"),
        "Wadah Kering / Kedap Udara": (120, 240, "4–8 bulan · wadah kedap udara"),
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BAHAN BAKU MAKANAN — Bumbu & Pelengkap
    # ══════════════════════════════════════════════════════════════════════════
    "Bawang Merah & Bawang Putih": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (tempat kering & sirkulasi udara baik)"),
        "Kulkas (1–4 °C)":          (30, 60,  "1–2 bulan · kulkas (sudah dikupas, wadah tertutup)"),
        "Pendingin / Chiller (4–10 °C)": (21, 45, "3–6 minggu · chiller"),
        "Wadah Kering / Kedap Udara": (30, 60, "1–2 bulan · kering & gelap"),
    },
    "Bawang Goreng Crispy": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (wadah tertutup rapat)"),
        "Wadah Kering / Kedap Udara": (30, 60, "1–2 bulan · wadah kedap udara"),
    },
    "Sambal": {
        "Suhu Ruang":               (0,  1,   "Maks 1 hari · suhu ruang (sambal segar/homemade)"),
        "Kulkas (1–4 °C)":          (5,  7,   "5–7 hari · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (3, 5,  "3–5 hari · chiller"),
        "Freezer (≤ −18 °C)":       (30, 60,  "1–2 bulan · freezer"),
    },
    "Saus Tomat": {
        "Suhu Ruang":               (7,  14,  "1–2 minggu · suhu ruang (botol dibuka)"),
        "Kulkas (1–4 °C)":          (30, 45,  "1–1,5 bulan · kulkas (botol dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (21, 35, "3–5 minggu · chiller"),
    },
    "Saus Hot / Saus Pedas": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (botol dibuka)"),
        "Kulkas (1–4 °C)":          (60, 90,  "2–3 bulan · kulkas (botol dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (30, 60, "1–2 bulan · chiller"),
    },
    "Cuko Pempek": {
        "Suhu Ruang":               (1,  2,   "1–2 hari · suhu ruang (homemade)"),
        "Kulkas (1–4 °C)":          (7,  14,  "1–2 minggu · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (5, 10, "5–10 hari · chiller"),
        "Freezer (≤ −18 °C)":       (60, 90,  "2–3 bulan · freezer"),
    },
    "Serundeng Kelapa": {
        "Suhu Ruang":               (7,  14,  "1–2 minggu · suhu ruang (wadah tertutup)"),
        "Kulkas (1–4 °C)":          (21, 30,  "3–4 minggu · kulkas"),
        "Wadah Kering / Kedap Udara": (14, 30, "2–4 minggu · wadah kedap udara"),
    },
    "Minyak Goreng": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (botol belum dibuka)"),
        "Wadah Kering / Kedap Udara": (90, 180, "3–6 bulan · setelah dibuka (jauhkan dari panas & cahaya)"),
    },
    "Garam, Gula Pasir, Kecap Manis, Merica": {
        "Suhu Ruang":               (365, 730, "1–2 tahun · suhu ruang (tempat kering)"),
        "Wadah Kering / Kedap Udara": (730, 1095, "2–3 tahun · wadah kedap udara"),
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BAHAN BAKU MINUMAN
    # ══════════════════════════════════════════════════════════════════════════
    "Beans Natural": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu setelah roasting · suhu ruang (kedap udara)"),
        "Kulkas (1–4 °C)":          (30, 60,  "1–2 bulan · kulkas (wadah kedap udara, hindari kelembapan)"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer (wadah kedap udara, 1x beku jangan dicairkan ulang)"),
        "Wadah Kering / Kedap Udara": (21, 60, "3–8 minggu · wadah kedap udara suhu ruang"),
    },
    "Espresso Shot": {
        "Suhu Ruang":               (0, 0,    "Konsumsi segera · espresso shot hanya tahan 20–30 detik"),
    },
    "Susu Full Cream": {
        "Kulkas (1–4 °C)":          (5,  7,   "5–7 hari · kulkas (susu segar setelah dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (3, 5,  "3–5 hari · chiller"),
    },
    "Susu UHT Full Cream": {
        "Suhu Ruang":               (180, 270, "6–9 bulan · suhu ruang (belum dibuka, cek kemasan)"),
        "Kulkas (1–4 °C)":          (5,  7,   "5–7 hari · kulkas (setelah dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (3, 5, "3–5 hari · chiller (setelah dibuka)"),
    },
    "SKM (Susu Kental Manis)": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (kaleng/sachet dibuka, pindah ke wadah tertutup)"),
        "Kulkas (1–4 °C)":          (14, 21,  "2–3 minggu · kulkas (sudah dibuka)"),
    },
    "Creamer Cair / Krim Masak": {
        "Kulkas (1–4 °C)":          (7,  14,  "1–2 minggu · kulkas (setelah dibuka)"),
        "Pendingin / Chiller (4–10 °C)": (5, 10, "5–10 hari · chiller"),
        "Freezer (≤ −18 °C)":       (90, 180, "3–6 bulan · freezer"),
    },
    "Powder Hazelnut": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (kemasan tertutup, kering)"),
        "Wadah Kering / Kedap Udara": (180, 365, "6–12 bulan · wadah kedap udara"),
    },
    "Powder Greentea / Matcha": {
        "Suhu Ruang":               (90, 180, "3–6 bulan · suhu ruang (kemasan tertutup)"),
        "Kulkas (1–4 °C)":          (180, 365, "6–12 bulan · kulkas (wadah kedap udara)"),
        "Wadah Kering / Kedap Udara": (90, 180, "3–6 bulan · wadah kedap udara"),
    },
    "Powder Red Velvet": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (kemasan tertutup)"),
        "Wadah Kering / Kedap Udara": (180, 365, "6–12 bulan · wadah kedap udara"),
    },
    "Powder Chocolate / Coklat Bubuk": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (kering)"),
        "Wadah Kering / Kedap Udara": (365, 730, "1–2 tahun · wadah kedap udara"),
    },
    "Gula Aren / Aren Liquid": {
        "Suhu Ruang":               (30, 60,  "1–2 bulan · suhu ruang (cair, botol tertutup)"),
        "Kulkas (1–4 °C)":          (90, 180, "3–6 bulan · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (60, 120, "2–4 bulan · chiller"),
    },
    "Simple Syrup (Gula Cair)": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (botol steril, tertutup rapat)"),
        "Kulkas (1–4 °C)":          (30, 60,  "1–2 bulan · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (21, 45, "3–6 minggu · chiller"),
    },
    "Syrup Hazelnut": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (belum dibuka)"),
        "Kulkas (1–4 °C)":          (30, 90,  "1–3 bulan · kulkas (setelah dibuka)"),
    },
    "Syrup Leci": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (belum dibuka)"),
        "Kulkas (1–4 °C)":          (30, 90,  "1–3 bulan · kulkas (setelah dibuka)"),
    },
    "Syrup Melon": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (belum dibuka)"),
        "Kulkas (1–4 °C)":          (30, 90,  "1–3 bulan · kulkas (setelah dibuka)"),
    },
    "Syrup Strawberry": {
        "Suhu Ruang":               (180, 365, "6–12 bulan · suhu ruang (belum dibuka)"),
        "Kulkas (1–4 °C)":          (30, 90,  "1–3 bulan · kulkas (setelah dibuka)"),
    },
    "Lemon Segar": {
        "Suhu Ruang":               (7,  14,  "1–2 minggu · suhu ruang"),
        "Kulkas (1–4 °C)":          (21, 42,  "3–6 minggu · kulkas"),
        "Pendingin / Chiller (4–10 °C)": (14, 30, "2–4 minggu · chiller"),
    },
    "Teh Celup / Teh Bubuk": {
        "Suhu Ruang":               (365, 730, "1–2 tahun · suhu ruang (teh kering, kemasan tertutup)"),
        "Wadah Kering / Kedap Udara": (365, 730, "1–2 tahun · wadah kedap udara"),
    },
    "Yakult": {
        "Kulkas (1–4 °C)":          (14, 30,  "2–4 minggu · kulkas (cek tanggal di botol)"),
        "Pendingin / Chiller (4–10 °C)": (10, 21, "10–21 hari · chiller"),
    },
    "Air Mineral / Air Galon": {
        "Suhu Ruang":               (14, 30,  "2–4 minggu · suhu ruang (galon terpasang di dispenser, jauh dari sinar matahari)"),
        "Wadah Kering / Kedap Udara": (30, 60, "1–2 bulan · galon tersegel belum dibuka"),
    },
    "Es Batu Kristal / Batangan": {
        "Freezer (≤ −18 °C)":       (30, 90,  "1–3 bulan · freezer (tersegel, jauh dari bahan berbau)"),
    },
}

KOLOM_DB = [
    "id", "cabang", "tanggal", "jam_transaksi", "no_nota", "supplier", "nama_pencatat",
    "kategori", "sub_kategori", "nama_barang", "merk", "grind_size",
    "qty", "uom_qty", "vol_per_unit", "uom_vol", "netto_total",
    "harga_total",
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
            # Hapus kolom yang dihitung di sisi DB (generated / computed)
            excluded = {"total_harga", "harga_satuan", "uom"}
            payload = {k: v for k, v in data.items() if k not in excluded}
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
    Nama file: {no_nota}_{cabang}_{YYYYMMDD}_{HHMMSS}.jpg
    Mengembalikan (bytes_foto | None, nama_file | None, timestamp_str | None).
    """
    foto_bytes = st.camera_input(
        "📷 Arahkan kamera ke nota/invoice, lalu tekan tombol capture",
        help="Nama file otomatis: {nota}_{cabang}_{tanggal}_{jam}.jpg",
        key="s1_kamera",
    )
    if foto_bytes is not None:
        now       = datetime.now()
        tgl_str   = now.strftime("%Y%m%d")
        jam_str   = now.strftime("%H%M%S")
        nota      = st.session_state.get("s1_nota", "NONOTA").strip() or "NONOTA"
        cabang    = st.session_state.get("cabang",  "CBG").strip()
        nota_cl   = "".join(c for c in nota   if c.isalnum() or c in "-_")
        cabang_cl = "".join(c for c in cabang if c.isalnum() or c in "-_")
        nama_file = f"{nota_cl}_{cabang_cl}_{tgl_str}_{jam_str}.jpg"
        ts_label  = now.strftime("%d %b %Y · %H:%M:%S")

        if supabase:
            try:
                supabase.storage.from_("invoice-foto").upload(
                    path=nama_file,
                    file=foto_bytes.getvalue(),
                    file_options={"content-type": "image/jpeg"},
                )
                st.success(f"✅ Foto tersimpan: **{nama_file}**")
            except Exception as e:
                st.warning(f"Upload ke Storage gagal ({e}). Foto tetap terekam.")
        else:
            st.info(f"📄 Nama file foto: **{nama_file}** · {ts_label}")

        return foto_bytes.getvalue(), nama_file, now.strftime("%H:%M:%S")
    return None, None, None

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
    import numpy as np

    now_str = datetime.now().strftime("%A, %d %B %Y · %H:%M")
    st.title("📊 Dashboard")
    st.caption(f"Cabang **{st.session_state.cabang}** · {now_str}")

    if df.empty:
        empty_state("📊", "Belum Ada Data",
                    "Mulai catat transaksi pertama di halaman Administrasi.")
        return

    # ── Normalisasi kolom numerik ─────────────────────────────────────────────
    col_harga = "harga_total" if "harga_total" in df.columns else "total_harga"
    df[col_harga] = pd.to_numeric(df[col_harga], errors="coerce").fillna(0)
    df["qty"]     = pd.to_numeric(df.get("qty", 0), errors="coerce").fillna(0)
    if "tanggal" in df.columns:
        df["tanggal_dt"] = pd.to_datetime(df["tanggal"], errors="coerce")
        df["bulan"]      = df["tanggal_dt"].dt.to_period("M").astype(str)
        df["minggu"]     = df["tanggal_dt"].dt.to_period("W").astype(str)

    today        = pd.Timestamp.today().normalize()
    bulan_ini    = today.to_period("M").strftime("%Y-%m")
    bulan_lalu   = (today - pd.DateOffset(months=1)).to_period("M").strftime("%Y-%m")

    total_keluar    = df[col_harga].sum()
    total_bln_ini   = df[df["bulan"] == bulan_ini][col_harga].sum() if "bulan" in df else 0
    total_bln_lalu  = df[df["bulan"] == bulan_lalu][col_harga].sum() if "bulan" in df else 0
    delta_bln       = total_bln_ini - total_bln_lalu
    total_trx       = len(df)
    n_lunas         = len(df[df["status_pembayaran"] == "Lunas"]) if "status_pembayaran" in df.columns else 0
    total_hutang    = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)][col_harga].sum() if "status_pembayaran" in df.columns else 0
    jenis_barang    = df["nama_barang"].nunique() if "nama_barang" in df.columns else 0

    # ── Kadaluarsa alert ─────────────────────────────────────────────────────
    n_kritis = n_mendekat = 0
    if "tgl_kadaluarsa" in df.columns:
        df_exp = df[df["tgl_kadaluarsa"].notna() &
                    (df["tgl_kadaluarsa"].astype(str).str.strip() != "") &
                    (df["tgl_kadaluarsa"].astype(str).str.strip() != "None")].copy()
        if not df_exp.empty:
            df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
            n_kritis   = len(df_exp[df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=7)])
            n_mendekat = len(df_exp[
                (df_exp["tgl_kadaluarsa"] > today + pd.Timedelta(days=7)) &
                (df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30))
            ])

    # ═══════════════════════════════════════════════════════════════════════════
    # BARIS 1: FLASHCARD UTAMA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 💡 Ringkasan Hari Ini")
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
    fc1.metric("💸 Total Pengeluaran", f"Rp {total_keluar:,.0f}")
    fc2.metric("📅 Bulan Ini",
               f"Rp {total_bln_ini:,.0f}",
               delta=f"Rp {delta_bln:+,.0f} vs bulan lalu",
               delta_color="inverse")
    fc3.metric("📝 Total Transaksi", total_trx)
    fc4.metric("⏳ Hutang Supplier",  f"Rp {total_hutang:,.0f}",
               delta_color="inverse")
    fc5.metric("🚨 Kadaluarsa Kritis", f"{n_kritis} item",
               delta=f"{n_mendekat} mendekati" if n_mendekat else None,
               delta_color="inverse")
    fc6.metric("📦 Jenis Barang", jenis_barang)

    if n_kritis > 0:
        st.error(f"🚨 **{n_kritis} item** sudah kadaluarsa atau ≤7 hari! Cek halaman Kontrol & Audit.")
    elif n_mendekat > 0:
        st.warning(f"⚠️ **{n_mendekat} item** akan kadaluarsa dalam 30 hari.")

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # BARIS 2: PENGELUARAN BULANAN + KOMPOSISI KATEGORI
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📈 Analisis Pengeluaran")
    col_grafik1, col_grafik2 = st.columns([3, 2])

    with col_grafik1:
        st.markdown("**📊 Pengeluaran Bulanan (Time Series)**")
        if "bulan" in df.columns:
            monthly = (df.groupby("bulan")[col_harga].sum()
                       .reset_index()
                       .rename(columns={col_harga: "Total (Rp)", "bulan": "Bulan"})
                       .sort_values("Bulan"))
            if len(monthly) >= 2:
                # Regresi linear sederhana untuk trend line
                x = np.arange(len(monthly))
                y = monthly["Total (Rp)"].values
                m, b = np.polyfit(x, y, 1)
                monthly["Trend (Rp)"] = m * x + b
                st.line_chart(monthly.set_index("Bulan")[["Total (Rp)", "Trend (Rp)"]],
                              use_container_width=True)
                arah = "📈 naik" if m > 0 else "📉 turun"
                st.caption(f"Tren: pengeluaran rata-rata {arah} **Rp {abs(m):,.0f}** per bulan "
                           f"(regresi linear · {len(monthly)} bulan data)")
            elif len(monthly) == 1:
                st.bar_chart(monthly.set_index("Bulan")["Total (Rp)"], use_container_width=True)
            else:
                st.info("Belum cukup data untuk grafik.")

    with col_grafik2:
        st.markdown("**🗂️ Komposisi per Kategori**")
        if "kategori" in df.columns:
            kat_grp = (df.groupby("kategori")[col_harga].sum()
                       .reset_index()
                       .rename(columns={col_harga: "Total (Rp)"})
                       .sort_values("Total (Rp)", ascending=False))
            total_all = kat_grp["Total (Rp)"].sum()
            for _, r in kat_grp.iterrows():
                pct = r["Total (Rp)"] / total_all * 100 if total_all > 0 else 0
                st.markdown(f"**{r['kategori']}**")
                st.progress(int(pct), text=f"Rp {r['Total (Rp)']:,.0f} · {pct:.1f}%")

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # BARIS 3: ANALISIS HARGA (VOLATILITAS & MOVING AVERAGE)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🔬 Analisis Harga per Produk")
    col_trend, col_stat = st.columns([3, 2])

    with col_trend:
        st.markdown("**📉 Tren Harga Produk + Moving Average**")
        if "nama_barang" in df.columns and "tanggal_dt" in df.columns:
            barang_opts = sorted(df["nama_barang"].dropna().unique())
            pilih_barang = st.selectbox("Pilih produk", barang_opts, key="db_tren_barang")
            tren_df = df[df["nama_barang"] == pilih_barang][["tanggal_dt", col_harga, "qty"]].copy()
            tren_df = tren_df.dropna(subset=["tanggal_dt"]).sort_values("tanggal_dt")
            # Harga per unit estimasi
            tren_df["qty_safe"] = tren_df["qty"].replace(0, np.nan)
            tren_df["harga_per_unit"] = tren_df[col_harga] / tren_df["qty_safe"]
            tren_df = tren_df.dropna(subset=["harga_per_unit"])
            tren_df = tren_df.set_index("tanggal_dt")

            if len(tren_df) >= 3:
                tren_df["MA3"] = tren_df["harga_per_unit"].rolling(3, min_periods=1).mean()
                st.line_chart(tren_df[["harga_per_unit", "MA3"]], use_container_width=True)

                # Statistik deskriptif
                mu  = tren_df["harga_per_unit"].mean()
                std = tren_df["harga_per_unit"].std()
                cv  = std / mu * 100 if mu > 0 else 0
                st.caption(
                    f"Rata-rata: **Rp {mu:,.0f}** · "
                    f"Std dev: **Rp {std:,.0f}** · "
                    f"Koefisien variasi: **{cv:.1f}%**"
                    + (" — harga cukup stabil ✅" if cv < 10 else " — harga fluktuatif ⚠️")
                )
            elif len(tren_df) >= 1:
                st.bar_chart(tren_df[["harga_per_unit"]], use_container_width=True)
                st.caption("Butuh ≥3 transaksi untuk moving average.")
            else:
                st.info("Belum ada data harga untuk produk ini.")

    with col_stat:
        st.markdown("**📊 Top 5 Pengeluaran per Produk**")
        if "nama_barang" in df.columns:
            top5 = (df.groupby("nama_barang")[col_harga].sum()
                    .sort_values(ascending=False).head(5)
                    .reset_index()
                    .rename(columns={"nama_barang": "Produk", col_harga: "Total (Rp)"}))
            for i, r in top5.iterrows():
                pct = r["Total (Rp)"] / total_keluar * 100 if total_keluar > 0 else 0
                medal = ["🥇","🥈","🥉","4️⃣","5️⃣"][i]
                st.markdown(f"{medal} **{r['Produk']}**  \n"
                            f"Rp {r['Total (Rp)']:,.0f} · {pct:.1f}%")

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # BARIS 4: SUPPLIER + FREKUENSI PEMBELIAN
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🏪 Analisis Supplier & Frekuensi")
    col_sup, col_freq = st.columns(2)

    with col_sup:
        st.markdown("**🏆 Top Supplier (by nilai pembelian)**")
        if "supplier" in df.columns:
            sup_df = (df.groupby("supplier")
                      .agg(total=(col_harga, "sum"), frekuensi=("tanggal", "count"))
                      .reset_index()
                      .sort_values("total", ascending=False)
                      .head(8))
            sup_df.columns = ["Supplier", "Total (Rp)", "Frekuensi"]
            sup_df["Total (Rp)"] = sup_df["Total (Rp)"].apply(lambda x: f"Rp {x:,.0f}")
            st.dataframe(sup_df, use_container_width=True, hide_index=True)

    with col_freq:
        st.markdown("**📆 Frekuensi Pembelian per Minggu**")
        if "minggu" in df.columns:
            weekly = (df.groupby("minggu").size()
                      .reset_index(name="Jumlah Item")
                      .sort_values("minggu")
                      .tail(12))  # 12 minggu terakhir
            if len(weekly) >= 2:
                st.bar_chart(weekly.set_index("minggu")["Jumlah Item"],
                             use_container_width=True)
                avg_w = weekly["Jumlah Item"].mean()
                st.caption(f"Rata-rata **{avg_w:.1f} item** dibeli per minggu "
                           f"(12 minggu terakhir)")
            else:
                st.info("Butuh minimal 2 minggu data.")

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # BARIS 5: STATUS PEMBAYARAN + KADALUARSA SEGERA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### ⚠️ Perlu Perhatian")
    col_bayar, col_exp = st.columns(2)

    with col_bayar:
        st.markdown("**💳 Status Pembayaran**")
        if "status_pembayaran" in df.columns:
            st_df = (df.groupby("status_pembayaran")[col_harga].sum()
                     .reset_index()
                     .rename(columns={"status_pembayaran": "Status", col_harga: "Total (Rp)"}))
            for _, r in st_df.iterrows():
                icon = "✅" if r["Status"] == "Lunas" else "⏳"
                st.markdown(f"{icon} **{r['Status']}:** Rp {r['Total (Rp)']:,.0f}")

            hutang_items = df[df["status_pembayaran"] != "Lunas"]
            if not hutang_items.empty:
                st.markdown("---")
                st.caption("Supplier dengan tagihan belum lunas:")
                ht = (hutang_items.groupby("supplier")[col_harga].sum()
                      .sort_values(ascending=False).head(5))
                for sup, val in ht.items():
                    st.markdown(f"• **{sup}**: Rp {val:,.0f}")

    with col_exp:
        st.markdown("**🗓️ Kadaluarsa Terdekat**")
        if "tgl_kadaluarsa" in df.columns and not df_exp.empty if "df_exp" in dir() else False:
            pass
        # re-compute untuk tampilan ini
        if "tgl_kadaluarsa" in df.columns:
            _exp = df[df["tgl_kadaluarsa"].notna() &
                      (df["tgl_kadaluarsa"].astype(str).str.strip() != "") &
                      (df["tgl_kadaluarsa"].astype(str).str.strip() != "None")].copy()
            if not _exp.empty:
                _exp["tgl_kadaluarsa"] = pd.to_datetime(_exp["tgl_kadaluarsa"], errors="coerce")
                _soon = _exp[_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30)].sort_values("tgl_kadaluarsa")
                if not _soon.empty:
                    for _, r in _soon.head(6).iterrows():
                        sisa = (r["tgl_kadaluarsa"] - today).days
                        icon = "🔴" if sisa <= 7 else "🟡"
                        nama = r.get("nama_barang", "-")
                        st.markdown(f"{icon} **{nama}** — sisa **{sisa} hari** "
                                    f"({r['tgl_kadaluarsa'].strftime('%d %b %Y')})")
                else:
                    st.success("✅ Tidak ada barang yang kadaluarsa dalam 30 hari ke depan.")
            else:
                st.info("Belum ada data kadaluarsa dicatat.")

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
    # Satu sesi nota bisa menampung banyak item (multi-item per transaksi).
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_catat:
        st.caption("Kolom bertanda \\* wajib diisi.")

        # ── SEKSI 1: ADMINISTRASI ─────────────────────────────────────────────
        st.markdown('<p class="form-section-title">📋 Seksi 1 — Administrasi</p>',
                    unsafe_allow_html=True)

        c1a, c1b, c1c = st.columns(3)
        with c1a:
            st.date_input("Tanggal Transaksi *", value=date.today(), key="s1_tgl")
            st.time_input("Jam Transaksi *", value=datetime.now().time(), key="s1_jam",
                          help="Jam saat transaksi terjadi — dicatat di database dan nama foto")
        with c1b:
            st.text_input("Nomor Nota / Invoice", placeholder="Contoh: INV-001", key="s1_nota")
            st.text_input("Nama Supplier *",
                          placeholder="Contoh: Roastery A, Makmur Plastik", key="s1_sup")
        with c1c:
            st.text_input("Nama Pencatat *",
                          placeholder="Nama staf yang melakukan pembelian",
                          key="s1_pencatat",
                          help="Nama orang yang mencatat / melakukan transaksi ini")

        # Foto invoice — WAJIB
        st.markdown('<p class="form-section-title">📷 Foto Invoice — Wajib *</p>',
                    unsafe_allow_html=True)
        st.caption("Satu foto untuk satu nota. Foto berlaku untuk semua item dalam nota yang sama.")
        _foto_bytes, _nama_foto, _jam_foto = render_foto_invoice()
        if _foto_bytes is None:
            st.warning("📷 Foto invoice belum diambil. Ambil foto nota sebelum menyimpan.")

        st.divider()

        # ── INFO MULTI-ITEM ───────────────────────────────────────────────────
        # Inisialisasi keranjang item dalam session_state
        if "item_keranjang" not in st.session_state:
            st.session_state["item_keranjang"] = []

        keranjang = st.session_state["item_keranjang"]

        # Tampilkan keranjang jika sudah ada item
        if keranjang:
            st.markdown('<p class="form-section-title">🛒 Item dalam Nota Ini</p>',
                        unsafe_allow_html=True)
            df_keranjang = pd.DataFrame(keranjang)
            cols_show_k = [c for c in ["nama_barang","merk","qty","uom_qty",
                                        "vol_per_unit","uom_vol","harga_total",
                                        "tgl_kadaluarsa"] if c in df_keranjang.columns]
            st.dataframe(df_keranjang[cols_show_k], use_container_width=True, hide_index=True)
            total_keranjang = sum(item.get("harga_total", 0) for item in keranjang)
            st.info(f"🧾 **{len(keranjang)} item** dalam nota ini · "
                    f"Total sementara: **Rp {total_keranjang:,.0f}**")

            col_simpan_all, col_batal = st.columns(2)
            with col_simpan_all:
                if st.button("💾 Simpan Semua Item ke Database",
                             type="primary", use_container_width=True,
                             key="btn_simpan_semua"):
                    sup_val      = st.session_state.get("s1_sup", "").strip()
                    pencatat_val = st.session_state.get("s1_pencatat", "").strip()
                    nota_val     = st.session_state.get("s1_nota", "").strip()

                    errs_global = []
                    if not sup_val:       errs_global.append("Nama Supplier")
                    if not pencatat_val:  errs_global.append("Nama Pencatat")
                    if _foto_bytes is None: errs_global.append("Foto Invoice belum diambil")

                    if errs_global:
                        st.error("Harap lengkapi: " + " · ".join(errs_global))
                    else:
                        berhasil = 0
                        for item in keranjang:
                            ok = insert_row(item)
                            if ok:
                                berhasil += 1
                        if berhasil == len(keranjang):
                            st.success(f"✅ **{berhasil} item** dari nota **{nota_val or '-'}** "
                                       f"berhasil disimpan!")
                            st.session_state["item_keranjang"] = []
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"Hanya {berhasil}/{len(keranjang)} item berhasil disimpan.")

            with col_batal:
                if st.button("🗑️ Batalkan Semua Item",
                             use_container_width=True, key="btn_batal_semua"):
                    st.session_state["item_keranjang"] = []
                    st.rerun()

            st.divider()

        # ── SEKSI 2: IDENTITAS BARANG — DI LUAR FORM ─────────────────────────
        st.markdown('<p class="form-section-title">🏷️ Seksi 2 — Identitas Barang</p>',
                    unsafe_allow_html=True)

        ca, cb = st.columns(2)
        with ca:
            st.selectbox("Kategori *", KATEGORI_OPTIONS, key="s2_kategori")
        with cb:
            sub_opts = SUB_KATEGORI_MAP.get(st.session_state.s2_kategori, ["Lainnya"])
            if st.session_state.get("s2_sub") not in sub_opts:
                st.session_state["s2_sub"] = sub_opts[0]
            st.selectbox("Sub Kategori *", sub_opts, key="s2_sub")

        cc, cd, ce = st.columns(3)
        with cc:
            nama_opts = NAMA_BARANG_MAP.get(
                (st.session_state.s2_kategori, st.session_state.s2_sub), ["Lainnya"]
            )
            if st.session_state.get("s2_nama_sel") not in nama_opts:
                st.session_state["s2_nama_sel"] = nama_opts[0]
            st.selectbox("Nama Barang *", nama_opts, key="s2_nama_sel",
                         help="Pilih dari daftar, atau pilih 'Lainnya' untuk ketik manual")
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

        nama_sel_now  = st.session_state.get("s2_nama_sel", "")
        digunakan_now = DIGUNAKAN_DI_MENU.get(nama_sel_now, "")
        if digunakan_now:
            st.info(f"🍽️ **Digunakan di Menu:** {digunakan_now}")
        elif nama_sel_now == "Lainnya":
            st.caption("Info menu tidak tersedia untuk barang baru.")
        else:
            st.caption("Pilih nama barang untuk melihat info penggunaan di menu.")

        st.divider()

        # ── SEKSI 3 & 4: DALAM FORM ───────────────────────────────────────────
        st.markdown('<p class="form-section-title">📦 Seksi 3 — Detail Stok & Harga</p>',
                    unsafe_allow_html=True)

        is_packaging = st.session_state.get("s2_kategori", "") == "Packaging"

        with st.form("form_catat", clear_on_submit=True):

            # ── Baris 1: Qty · Satuan Qty · Vol per unit · Satuan Vol ─────────
            cA, cB, cC, cD = st.columns(4)
            with cA:
                f_qty = st.number_input(
                    "Kuantitas yang Dibeli (Qty) *",
                    min_value=0.0, step=1.0, format="%.2f",
                    help="Jumlah unit/kemasan yang kamu terima dari supplier"
                )
            with cB:
                f_uom_qty = st.selectbox(
                    "Satuan Kuantitas (UoM Qty) *",
                    UOM_QTY_OPTIONS,
                    help="Satuan kemasan/unit pembelian: pcs, pack, dus, kantong, dll"
                )
            with cC:
                f_vol = st.number_input(
                    "Berat/Volume per Unit (Vol/Netto)",
                    min_value=0.0, step=0.1, format="%.3f",
                    help="Berat atau volume SATU unit. Contoh: 1 botol = 750 ml → isi 750"
                )
            with cD:
                f_uom_vol = st.selectbox(
                    "Satuan Berat/Volume (UoM Vol)",
                    VOL_OPTIONS,
                    help="Satuan berat/volume: ml, liter, gram, kg, ons, mg"
                )

            # ── Kalkulasi netto total otomatis ────────────────────────────────
            multiplier  = QTY_MULTIPLIER.get(f_uom_qty, 1)
            faktor_vol  = VOL_FAKTOR.get(f_uom_vol, 1)
            # Netto total dalam satuan dasar (gram atau ml)
            netto_total = f_qty * multiplier * f_vol * faktor_vol

            if f_qty > 0 and f_vol > 0:
                satuan_dasar = "ml" if f_uom_vol in ("ml", "liter") else "gram"
                st.caption(
                    f"📊 **Netto Total:** {f_qty:.2f} {f_uom_qty}"
                    + (f" × {multiplier} pcs" if multiplier > 1 else "")
                    + f" × {f_vol:.3f} {f_uom_vol}"
                    + f" = **{netto_total:,.1f} {satuan_dasar}**"
                )

            st.divider()

            # ── Baris 2: Harga Total ──────────────────────────────────────────
            st.markdown("**💰 Harga**")
            cE, cF = st.columns([1, 2])
            with cE:
                f_harga_total = st.number_input(
                    "Harga Total Pembelian (Rp) *",
                    min_value=0, step=500,
                    help="Isi total harga yang tertera di nota untuk item ini"
                )
            with cF:
                if f_qty > 0 and f_harga_total > 0:
                    harga_per_unit = f_harga_total / f_qty
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.caption(
                        f"≈ Rp {harga_per_unit:,.0f} per {f_uom_qty}"
                        + (f" · Rp {f_harga_total / (f_qty * multiplier):,.0f} per pcs"
                           if multiplier > 1 else "")
                    )

            st.divider()
            st.markdown('<p class="form-section-title">🔍 Seksi 4 — Kontrol & Audit</p>',
                        unsafe_allow_html=True)

            ci, cj = st.columns(2)
            with ci:
                # Tanggal kadaluarsa manual untuk semua produk KECUALI Packaging
                if is_packaging:
                    f_exp = None
                    st.caption("ℹ️ Produk Packaging tidak memiliki tanggal kadaluarsa.")
                else:
                    f_exp = st.date_input(
                        "Tanggal Kadaluarsa",
                        value=None,
                        help="Isi sesuai tanggal expired di kemasan. Kosongkan jika tidak ada.",
                    )
            with cj:
                f_status = st.selectbox("Status Pembayaran *", STATUS_OPTIONS)

            f_catatan = st.text_area(
                "Catatan Tambahan",
                placeholder="Contoh: Tutup botol retak sudah diretur · Dapat diskon 5%",
                height=80,
            )

            submit_item = st.form_submit_button(
                "➕ Tambahkan Item ke Nota Ini",
                type="primary", use_container_width=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
            submit_langsung = st.form_submit_button(
                "💾 Submit Transaksi Baru (Item Tunggal — Langsung Simpan)",
                use_container_width=True,
                help="Gunakan tombol ini jika hanya membeli 1 jenis barang dan langsung ingin menyimpan tanpa keranjang."
            )

        # ── PROSES SUBMIT ITEM ────────────────────────────────────────────────
        if submit_item:
            sup_val      = st.session_state.get("s1_sup",      "").strip()
            pencatat_val = st.session_state.get("s1_pencatat", "").strip()
            nota_val     = st.session_state.get("s1_nota",     "").strip()
            tgl_val      = st.session_state.get("s1_tgl",      date.today())
            jam_val      = st.session_state.get("s1_jam",      datetime.now().time())
            kat_val      = st.session_state.get("s2_kategori", KATEGORI_OPTIONS[0])
            sub_val      = st.session_state.get("s2_sub",      "")
            nama_val     = _get_s2_nama()
            merk_val     = _get_s2_merk()
            grind_val    = _get_s2_grind()

            errors = []
            if not sup_val:       errors.append("Nama Supplier")
            if not pencatat_val:  errors.append("Nama Pencatat")
            if not nama_val:      errors.append("Nama Barang")
            if f_qty  <= 0:       errors.append("Kuantitas harus > 0")
            if f_harga_total <= 0: errors.append("Harga Total harus > 0")

            if errors:
                st.error("Harap lengkapi: " + " · ".join(errors))
            else:
                jam_str = jam_val.strftime("%H:%M:%S") if hasattr(jam_val, "strftime") else str(jam_val)
                item_baru = {
                    "cabang":            st.session_state.cabang,
                    "tanggal":           tgl_val.isoformat(),
                    "jam_transaksi":     jam_str,
                    "no_nota":           nota_val or None,
                    "supplier":          sup_val,
                    "nama_pencatat":     pencatat_val,
                    "kategori":          kat_val,
                    "sub_kategori":      sub_val,
                    "nama_barang":       nama_val,
                    "merk":              merk_val,
                    "grind_size":        grind_val,
                    "qty":               float(f_qty),
                    "uom_qty":           f_uom_qty,
                    "vol_per_unit":      float(f_vol) if f_vol > 0 else None,
                    "uom_vol":           f_uom_vol if f_vol > 0 else None,
                    "netto_total":       round(netto_total, 3) if netto_total > 0 else None,
                    "harga_total":       int(f_harga_total),
                    "tgl_kadaluarsa":    f_exp.isoformat() if f_exp else None,
                    "status_pembayaran": f_status,
                    "catatan":           f_catatan.strip() or None,
                    "foto_invoice":      _nama_foto or None,
                }
                st.session_state["item_keranjang"].append(item_baru)
                st.success(f"✅ **{nama_val}** ditambahkan ke nota. "
                           f"Tambah item lain atau tekan 'Simpan Semua' di atas.")
                st.rerun()

        # ── PROSES SUBMIT LANGSUNG (item tunggal, bypass keranjang) ──────────
        if submit_langsung:
            sup_val      = st.session_state.get("s1_sup",      "").strip()
            pencatat_val = st.session_state.get("s1_pencatat", "").strip()
            nota_val     = st.session_state.get("s1_nota",     "").strip()
            tgl_val      = st.session_state.get("s1_tgl",      date.today())
            jam_val      = st.session_state.get("s1_jam",      datetime.now().time())
            kat_val      = st.session_state.get("s2_kategori", KATEGORI_OPTIONS[0])
            sub_val      = st.session_state.get("s2_sub",      "")
            nama_val     = _get_s2_nama()
            merk_val     = _get_s2_merk()
            grind_val    = _get_s2_grind()

            errors = []
            if not sup_val:        errors.append("Nama Supplier")
            if not pencatat_val:   errors.append("Nama Pencatat")
            if not nama_val:       errors.append("Nama Barang")
            if f_qty  <= 0:        errors.append("Kuantitas harus > 0")
            if f_harga_total <= 0: errors.append("Harga Total harus > 0")
            if _foto_bytes is None: errors.append("Foto Invoice belum diambil")

            if errors:
                st.error("Harap lengkapi: " + " · ".join(errors))
            else:
                jam_str = jam_val.strftime("%H:%M:%S") if hasattr(jam_val, "strftime") else str(jam_val)
                ok = insert_row({
                    "cabang":            st.session_state.cabang,
                    "tanggal":           tgl_val.isoformat(),
                    "jam_transaksi":     jam_str,
                    "no_nota":           nota_val or None,
                    "supplier":          sup_val,
                    "nama_pencatat":     pencatat_val,
                    "kategori":          kat_val,
                    "sub_kategori":      sub_val,
                    "nama_barang":       nama_val,
                    "merk":              merk_val,
                    "grind_size":        grind_val,
                    "qty":               float(f_qty),
                    "uom_qty":           f_uom_qty,
                    "vol_per_unit":      float(f_vol) if f_vol > 0 else None,
                    "uom_vol":           f_uom_vol if f_vol > 0 else None,
                    "netto_total":       round(netto_total, 3) if netto_total > 0 else None,
                    "harga_total":       int(f_harga_total),
                    "tgl_kadaluarsa":    f_exp.isoformat() if f_exp else None,
                    "status_pembayaran": f_status,
                    "catatan":           f_catatan.strip() or None,
                    "foto_invoice":      _nama_foto or None,
                })
                if ok:
                    st.success(f"✅ Transaksi **{nama_val}** dari **{sup_val}** langsung disimpan!")
                    st.balloons()

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: RIWAYAT TRANSAKSI
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_riwayat:
        if df.empty:
            empty_state("📃", "Belum Ada Riwayat",
                        "Catat transaksi pertama di tab 'Catat Transaksi Baru'.")
        else:
            # ── Filter bar ────────────────────────────────────────────────────
            rf1, rf2, rf3, rf4, rf5 = st.columns(5)
            with rf1:
                cari    = st.text_input("🔍 Cari barang / supplier", key="r_cari")
            with rf2:
                fil_kat = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="r_kat")
            with rf3:
                fil_st  = st.selectbox("Status Bayar", ["Semua"] + STATUS_OPTIONS, key="r_st")
            with rf4:
                fil_bln = st.text_input("Bulan (YYYY-MM)", placeholder="2025-07", key="r_bln")
            with rf5:
                fil_nota = st.text_input("No. Nota", placeholder="INV-001", key="r_nota")

            hasil = df.copy()
            col_harga_r = "harga_total" if "harga_total" in hasil.columns else "total_harga"
            hasil[col_harga_r] = pd.to_numeric(hasil[col_harga_r], errors="coerce").fillna(0)

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
            if fil_nota:
                hasil = hasil[hasil["no_nota"].astype(str).str.contains(fil_nota, case=False, na=False)]

            urut = hasil.sort_values(["tanggal","no_nota"], ascending=False) \
                   if "tanggal" in hasil.columns else hasil

            # ── Mode tampilan ─────────────────────────────────────────────────
            view_mode = st.radio(
                "Mode Tampilan",
                ["📋 Detail per Item", "🧾 Summary per Nota"],
                horizontal=True, key="r_view_mode"
            )
            st.divider()

            if view_mode == "🧾 Summary per Nota":
                if "no_nota" in urut.columns:
                    urut["harga_total_num"] = pd.to_numeric(urut.get("harga_total", urut.get("total_harga", 0)), errors="coerce").fillna(0)
                    agg_dict = {
                        "supplier":     ("supplier", "first"),
                        "tanggal":      ("tanggal",  "first"),
                        "nama_pencatat":("nama_pencatat", "first") if "nama_pencatat" in urut.columns else ("supplier","first"),
                        "jumlah_item":  ("nama_barang", "count"),
                        "daftar_barang":("nama_barang", lambda x: " · ".join(x.dropna().unique()[:6])
                                         + ("…" if x.nunique() > 6 else "")),
                        "total_nota":   ("harga_total_num", "sum"),
                        "status":       ("status_pembayaran", lambda x: "✅ Lunas" if (x == "Lunas").all()
                                         else "⚠️ Ada Hutang"),
                    }
                    summary = (urut.groupby("no_nota", dropna=False)
                               .agg(**{k: v for k,v in agg_dict.items()})
                               .reset_index()
                               .sort_values("tanggal", ascending=False))
                    summary.columns = ["No. Nota","Supplier","Tanggal","Pencatat",
                                       "Jml Item","Daftar Barang","Total (Rp)","Status"]
                    summary["Total (Rp)"] = summary["Total (Rp)"].apply(lambda x: f"Rp {x:,.0f}")
                    st.dataframe(summary, use_container_width=True, hide_index=True)
                    st.caption(f"**{len(summary)} nota** dari filter yang aktif")
                else:
                    st.info("Kolom no_nota tidak tersedia.")

            else:  # Detail per item
                col_priority = [
                    "tanggal", "jam_transaksi", "no_nota", "supplier", "nama_pencatat",
                    "kategori", "sub_kategori", "nama_barang", "merk", "grind_size",
                    "qty", "uom_qty", "vol_per_unit", "uom_vol", "netto_total",
                    "harga_total", "total_harga",
                    "tgl_kadaluarsa",
                    "status_pembayaran", "catatan",
                ]
                cols_show = [c for c in col_priority if c in urut.columns]
                st.dataframe(urut[cols_show], use_container_width=True, hide_index=True)

                total_f = pd.to_numeric(
                    hasil.get(col_harga_r, pd.Series(dtype=float)), errors="coerce"
                ).sum()
                st.caption(f"**{len(hasil)} item** ditampilkan · Total: **Rp {total_f:,.0f}**")

            # ── Export ────────────────────────────────────────────────────────
            if st.session_state.role == "manager" and not hasil.empty:
                st.divider()
                csv_data = hasil.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Export Hasil Filter ke CSV",
                    data=csv_data,
                    file_name=f"riwayat_{st.session_state.cabang}_{date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

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

# ─── PAGE: KONTROL & AUDIT ────────────────────────────────────────────────────────
def page_kontrol_audit(df: pd.DataFrame):
    import numpy as np
    st.title("🔍 Kontrol & Audit")
    st.caption(f"Cabang **{st.session_state.cabang}** · {datetime.now().strftime('%d %b %Y, %H:%M')}")

    if df.empty:
        empty_state("🔍", "Belum Ada Data untuk Diaudit",
                    "Data audit muncul setelah transaksi dicatat.")
        return

    col_harga = "harga_total" if "harga_total" in df.columns else "total_harga"
    df[col_harga] = pd.to_numeric(df[col_harga], errors="coerce").fillna(0)
    df["qty"]     = pd.to_numeric(df.get("qty", 0), errors="coerce").fillna(0)
    if "tanggal" in df.columns:
        df["tanggal_dt"] = pd.to_datetime(df["tanggal"], errors="coerce")

    tab_exp, tab_kas, tab_stok, tab_log = st.tabs([
        "⏰ Monitor Kadaluarsa",
        "💳 Arus Kas & Hutang",
        "📦 Stok & Harga",
        "📋 Audit Log",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — MONITOR KADALUARSA
    # ══════════════════════════════════════════════════════════════════════════
    with tab_exp:
        st.subheader("📅 Status Kadaluarsa Barang")
        if "tgl_kadaluarsa" not in df.columns:
            st.info("Kolom kadaluarsa tidak tersedia.")
        else:
            today = pd.Timestamp.today().normalize()
            df_exp = df[
                df["tgl_kadaluarsa"].notna() &
                (df["tgl_kadaluarsa"].astype(str).str.strip() != "") &
                (df["tgl_kadaluarsa"].astype(str).str.strip() != "None")
            ].copy()

            if df_exp.empty:
                empty_state("📅", "Belum Ada Data Kadaluarsa",
                            "Isi kolom Tanggal Kadaluarsa saat mencatat transaksi bahan baku.")
            else:
                df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
                sudah_exp  = df_exp[df_exp["tgl_kadaluarsa"] < today]
                kritis     = df_exp[(df_exp["tgl_kadaluarsa"] >= today) &
                                    (df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=7))]
                mendekat   = df_exp[(df_exp["tgl_kadaluarsa"] > today + pd.Timedelta(days=7)) &
                                    (df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30))]
                aman       = df_exp[df_exp["tgl_kadaluarsa"] > today + pd.Timedelta(days=30)]

                ka, kb, kc, kd = st.columns(4)
                ka.metric("💀 Sudah Kadaluarsa",    len(sudah_exp), delta_color="inverse")
                kb.metric("🔴 Kritis (≤7 hari)",    len(kritis),    delta_color="inverse")
                kc.metric("🟡 Mendekat (8–30 hari)", len(mendekat), delta_color="inverse")
                kd.metric("🟢 Aman (>30 hari)",      len(aman))

                exp_cols = [c for c in ["nama_barang","merk","qty","uom_qty",
                                        "tgl_kadaluarsa","supplier","catatan"]
                            if c in df_exp.columns]

                if not sudah_exp.empty:
                    st.error(f"💀 **{len(sudah_exp)} item SUDAH KADALUARSA** — segera singkirkan!")
                    st.dataframe(sudah_exp[exp_cols].sort_values("tgl_kadaluarsa"),
                                 use_container_width=True, hide_index=True)

                if not kritis.empty:
                    st.error("🚨 Barang Kritis (≤7 hari) — Segera Pakai atau Retur ke Supplier!")
                    st.dataframe(kritis[exp_cols].sort_values("tgl_kadaluarsa"),
                                 use_container_width=True, hide_index=True)

                if not mendekat.empty:
                    st.warning("⚠️ Akan Kadaluarsa 8–30 Hari ke Depan")
                    st.dataframe(mendekat[exp_cols].sort_values("tgl_kadaluarsa"),
                                 use_container_width=True, hide_index=True)

                with st.expander(f"✅ Barang Aman — {len(aman)} item (>30 hari)"):
                    st.dataframe(aman[exp_cols].sort_values("tgl_kadaluarsa"),
                                 use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — ARUS KAS & HUTANG
    # ══════════════════════════════════════════════════════════════════════════
    with tab_kas:
        st.subheader("💸 Arus Kas Keluar & Status Pembayaran")

        total_all    = df[col_harga].sum()
        total_lunas  = df[df["status_pembayaran"] == "Lunas"][col_harga].sum() if "status_pembayaran" in df.columns else 0
        total_hutang = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)][col_harga].sum() if "status_pembayaran" in df.columns else 0
        rasio_lunas  = total_lunas / total_all * 100 if total_all > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Total Keluar",       f"Rp {total_all:,.0f}")
        k2.metric("✅ Sudah Lunas",         f"Rp {total_lunas:,.0f}")
        k3.metric("⏳ Belum Lunas",         f"Rp {total_hutang:,.0f}", delta_color="inverse")
        k4.metric("📊 Rasio Lunas",         f"{rasio_lunas:.1f}%")

        st.divider()
        col_h1, col_h2 = st.columns(2)

        with col_h1:
            st.markdown("**📋 Transaksi Belum Lunas**")
            belum = df[df["status_pembayaran"] != "Lunas"] if "status_pembayaran" in df.columns else pd.DataFrame()
            if not belum.empty:
                bl_cols = [c for c in ["tanggal","jam_transaksi","no_nota","supplier",
                                       "nama_barang","harga_total","total_harga",
                                       "status_pembayaran","catatan"]
                           if c in belum.columns]
                st.dataframe(belum[bl_cols].sort_values("tanggal") if "tanggal" in belum.columns
                             else belum[bl_cols],
                             use_container_width=True, hide_index=True)
            else:
                st.success("✅ Semua transaksi sudah berstatus Lunas!")

        with col_h2:
            st.markdown("**🏪 Pengeluaran per Supplier**")
            if "supplier" in df.columns:
                sup_stat = (df.groupby(["supplier","status_pembayaran"])[col_harga]
                            .sum().reset_index()
                            .sort_values(col_harga, ascending=False))
                sup_stat.columns = ["Supplier","Status","Total (Rp)"]
                sup_stat["Total (Rp)"] = sup_stat["Total (Rp)"].apply(lambda x: f"Rp {x:,.0f}")
                st.dataframe(sup_stat, use_container_width=True, hide_index=True)

        # Pengeluaran per bulan breakdown
        st.divider()
        st.markdown("**📅 Rekap Bulanan**")
        if "tanggal_dt" in df.columns:
            df["bulan_str"] = df["tanggal_dt"].dt.to_period("M").astype(str)
            rek = (df.groupby(["bulan_str","status_pembayaran"])[col_harga]
                   .sum().reset_index()
                   .rename(columns={"bulan_str":"Bulan","status_pembayaran":"Status",
                                    col_harga:"Total (Rp)"}))
            st.dataframe(rek.sort_values("Bulan", ascending=False),
                         use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — STOK & HARGA (konten dari page_detail_stok lama)
    # ══════════════════════════════════════════════════════════════════════════
    with tab_stok:
        st.subheader("📦 Ringkasan Stok & Analisis Harga")

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("💰 Total Pengeluaran",     f"Rp {df[col_harga].sum():,.0f}")
        s2.metric("📊 Rata-rata per Transaksi",f"Rp {df[col_harga].mean():,.0f}")
        s3.metric("🏆 Transaksi Terbesar",     f"Rp {df[col_harga].max():,.0f}")
        s4.metric("🗂️ Jenis Barang Unik",     df["nama_barang"].nunique() if "nama_barang" in df.columns else 0)

        st.divider()
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("**📊 Akumulasi Stok per Barang**")
            if "nama_barang" in df.columns:
                uom_col = "uom_qty" if "uom_qty" in df.columns else "uom"
                grp = df.groupby(["nama_barang"]).agg(
                    Total_Qty     =("qty",        "sum"),
                    Total_Spend   =(col_harga,    "sum"),
                    Jml_Transaksi =(col_harga,    "count"),
                ).reset_index()
                grp.columns = ["Nama Barang","Total Qty","Total Spend (Rp)","Jml Transaksi"]
                grp["Total Spend (Rp)"] = grp["Total Spend (Rp)"].apply(lambda x: f"Rp {x:,.0f}")
                st.dataframe(grp.sort_values("Jml Transaksi", ascending=False),
                             use_container_width=True, hide_index=True)

        with col_s2:
            st.markdown("**📈 Tren Harga + Volatilitas**")
            if "nama_barang" in df.columns and "tanggal_dt" in df.columns:
                pilih = st.selectbox("Pilih barang", sorted(df["nama_barang"].dropna().unique()),
                                     key="ka_tren_pilih")
                tren = df[df["nama_barang"] == pilih][["tanggal_dt", col_harga, "qty"]].copy()
                tren = tren.dropna(subset=["tanggal_dt"]).sort_values("tanggal_dt")
                tren["qty_safe"] = tren["qty"].replace(0, np.nan)
                tren["harga_pu"] = tren[col_harga] / tren["qty_safe"]
                tren = tren.dropna(subset=["harga_pu"]).set_index("tanggal_dt")

                if len(tren) >= 2:
                    tren["MA3"] = tren["harga_pu"].rolling(3, min_periods=1).mean()
                    st.line_chart(tren[["harga_pu","MA3"]], use_container_width=True)
                    mu = tren["harga_pu"].mean(); std = tren["harga_pu"].std()
                    cv = std / mu * 100 if mu > 0 else 0
                    st.caption(f"μ={mu:,.0f} · σ={std:,.0f} · CV={cv:.1f}%")
                elif len(tren) == 1:
                    st.info("Butuh ≥2 transaksi untuk grafik tren.")
                else:
                    st.info("Tidak ada data harga untuk produk ini.")

        st.divider()
        st.markdown("**🗓️ Pengeluaran per Bulan**")
        if "tanggal_dt" in df.columns:
            monthly = (df.assign(bulan=df["tanggal_dt"].dt.to_period("M").astype(str))
                       .groupby("bulan")[col_harga].sum().reset_index()
                       .sort_values("bulan"))
            monthly.columns = ["Bulan", "Total (Rp)"]
            if not monthly.empty:
                st.bar_chart(monthly.set_index("Bulan"), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — AUDIT LOG
    # ══════════════════════════════════════════════════════════════════════════
    with tab_log:
        st.subheader("📋 Log Seluruh Transaksi")

        lf1, lf2, lf3, lf4 = st.columns(4)
        with lf1:
            kat_f     = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="log_kat")
        with lf2:
            sort_f    = st.selectbox("Urutkan",
                                     [c for c in ["tanggal","harga_total","total_harga",
                                                   "supplier","nama_barang"] if c in df.columns],
                                     key="log_sort")
        with lf3:
            asc_f     = st.selectbox("Urutan", ["Terbaru dulu","Terlama dulu"], key="log_asc")
        with lf4:
            cari_log  = st.text_input("Cari barang/supplier", key="log_cari")

        log_df = df.copy()
        if kat_f != "Semua":
            log_df = log_df[log_df["kategori"] == kat_f]
        if cari_log:
            log_df = log_df[
                log_df["nama_barang"].str.contains(cari_log, case=False, na=False) |
                log_df["supplier"].str.contains(cari_log, case=False, na=False)
            ]
        if sort_f in log_df.columns:
            log_df = log_df.sort_values(sort_f, ascending=(asc_f == "Terlama dulu"))

        # Kolom audit yang relevan
        audit_cols = [c for c in [
            "id","tanggal","jam_transaksi","no_nota","supplier","nama_pencatat",
            "kategori","sub_kategori","nama_barang","merk","grind_size",
            "qty","uom_qty","vol_per_unit","uom_vol","netto_total",
            "harga_total","total_harga",
            "tgl_kadaluarsa","status_pembayaran","catatan","created_at"
        ] if c in log_df.columns]

        st.dataframe(log_df[audit_cols], use_container_width=True, hide_index=True)
        st.caption(f"{len(log_df)} baris ditampilkan")

        if st.session_state.role == "manager":
            st.markdown("---")
            csv = log_df[audit_cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Export CSV",
                data=csv,
                file_name=f"audit_{st.session_state.cabang}_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
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
    elif page == "🔍 Kontrol & Audit":  page_kontrol_audit(df)

if __name__ == "__main__":
    main()
