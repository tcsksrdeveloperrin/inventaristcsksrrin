import streamlit as st
import pandas as pd
import numpy as np
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

UOM_QTY_OPTIONS = [
    "pcs", "pack", "dus / karton", "kantong", "botol",
    "lusin", "ikat", "buah", "ekor", "bungkus",
    "tray", "galon", "roll", "sachet",
    "lembar", "bal", "porsi",
]
UOM_OPTIONS = UOM_QTY_OPTIONS  # Alias for simplified edit view
VOL_OPTIONS = ["ml", "liter", "gram (g)", "kg", "mg", "ons"]

VOL_FAKTOR = {
    "ml": 1, "liter": 1000,
    "gram (g)": 1, "kg": 1000, "mg": 0.001, "ons": 100,
}

QTY_MULTIPLIER = {
    "lusin": 12,
}

GRIND_OPTIONS  = ["-", "Whole Bean", "V60 (5-6)", "Vietnam Drip (3-4)", "Espresso (2-3)", "French Press (7-8)"]
STATUS_OPTIONS = ["Lunas", "Tempo (Hutang)", "DP/Uang Muka"]

KOLOM_DB = [
    "id", "cabang", "tanggal", "jam_transaksi", "no_nota", "supplier", "nama_pencatat",
    "kategori", "sub_kategori", "nama_barang", "merk", "grind_size",
    "qty", "uom_qty", "vol_per_unit", "uom_vol", "netto_total",
    "harga_total", "tgl_kadaluarsa", "status_pembayaran", "catatan", "created_at",
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
        "item_keranjang": [],
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
def _get_s2_nama() -> str:
    sel = st.session_state.get("s2_nama_sel", "Lainnya")
    if sel == "Lainnya":
        return st.session_state.get("s2_nama_custom", "").strip()
    return sel

def _get_s2_merk() -> str:
    sel = st.session_state.get("s2_nama_sel", "Lainnya")
    presets = MERK_MAP.get(sel)
    if presets:
        merk_sel = st.session_state.get("s2_merk_sel", presets[0])
        if merk_sel == "Lainnya":
            return st.session_state.get("s2_merk_custom", "").strip() or "-"
        return merk_sel
    return st.session_state.get("s2_merk_free", "").strip() or "-"

def _get_s2_grind() -> str:
    kat = st.session_state.get("s2_kategori", "")
    sub = st.session_state.get("s2_sub", "")
    if kat == "Bahan Baku Minuman" and sub == "Coffee Beans":
        return st.session_state.get("s2_grind", "-")
    return "-"

def render_foto_invoice():
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


# ─── PAGE: DASHBOARD ─────────────────────────────────────────────────────────────
def page_dashboard(df: pd.DataFrame):
    st.title("📊 Dashboard")
    st.caption(f"Cabang **{st.session_state.cabang}** · {datetime.now().strftime('%A, %d %B %Y')}")

    if df.empty:
        empty_state("📊", "Belum Ada Data",
                    "Mulai catat transaksi pertama di halaman Administrasi.")
        return

    df["harga_total"]  = pd.to_numeric(df["harga_total"],  errors="coerce").fillna(0)
    df["qty"]          = pd.to_numeric(df["qty"],          errors="coerce").fillna(0)

    # Calculate metrics
    total_keluar = df["harga_total"].sum()
    total_trx    = df["no_nota"].nunique() if "no_nota" in df.columns else len(df)
    total_hutang = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)]["harga_total"].sum()

    # Warning Kadaluarsa
    jml_peringatan = 0
    if "tgl_kadaluarsa" in df.columns:
        df_exp = df[df["tgl_kadaluarsa"].notna() & (df["tgl_kadaluarsa"].astype(str).str.strip().isin(["", "None"]) == False)].copy()
        if not df_exp.empty:
            df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
            today = pd.Timestamp.today().normalize()
            jml_peringatan = len(df_exp[df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30)])

    # ── Flashcards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💸 Total Pengeluaran",    f"Rp {total_keluar:,.0f}")
    c2.metric("📝 Jumlah Transaksi (Nota)", total_trx)
    c3.metric("⏳ Total Hutang",          f"Rp {total_hutang:,.0f}")
    c4.metric("⚠️ Peringatan (≤ 30 Hari)", f"{jml_peringatan} Item")

    st.markdown("---")
    
    # ── Chart 1 & Chart 2
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        st.subheader("📂 Pengeluaran per Kategori")
        kat = df.groupby("kategori")["harga_total"].sum().reset_index()
        kat.columns = ["Kategori", "Total (Rp)"]
        st.dataframe(kat.sort_values("Total (Rp)", ascending=False),
                     use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("📈 Analisis Time Series & Tren Pengeluaran")
        if "tanggal" in df.columns:
            # Mengelompokkan total harga berdasarkan tanggal
            daily_spend = df.groupby("tanggal")["harga_total"].sum().reset_index()
            daily_spend["tanggal"] = pd.to_datetime(daily_spend["tanggal"])
            daily_spend = daily_spend.sort_values("tanggal").dropna(subset=["harga_total"])
            
            if len(daily_spend) > 1:
                # 1. Menghitung Rolling Average (Time Series basic)
                daily_spend["Rata_rata_Bergerak_7h"] = daily_spend["harga_total"].rolling(window=7, min_periods=1).mean()
                
                # 2. Linear Regression (Analisis Tren)
                x = np.arange(len(daily_spend))
                y = daily_spend["harga_total"].values
                slope, intercept = np.polyfit(x, y, 1)
                daily_spend["Tren_Regresi_Linear"] = slope * x + intercept
                
                # Mempersiapkan data untuk chart
                chart_data = daily_spend.set_index("tanggal")[["harga_total", "Rata_rata_Bergerak_7h", "Tren_Regresi_Linear"]]
                chart_data.rename(columns={"harga_total": "Pengeluaran Aktual"}, inplace=True)
                
                st.line_chart(chart_data, use_container_width=True)
                st.caption("Visualisasi ini menggunakan **Regresi Linear** untuk garis tren dan **Rata-rata Bergerak 7 Hari (Rolling Average)** untuk meredam fluktuasi harian pengeluaran bahan baku.")
            else:
                st.info("Butuh minimal 2 hari transaksi untuk memproses visualisasi regresi dan time series.")


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
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_catat:
        st.caption("Kolom bertanda \\* wajib diisi.")

        st.markdown('<p class="form-section-title">📋 Seksi 1 — Administrasi</p>', unsafe_allow_html=True)

        c1a, c1b, c1c = st.columns(3)
        with c1a:
            st.date_input("Tanggal Transaksi *", value=date.today(), key="s1_tgl")
            st.time_input("Jam Transaksi *", value=datetime.now().time(), key="s1_jam")
        with c1b:
            st.text_input("Nomor Nota / Invoice", placeholder="Contoh: INV-001", key="s1_nota")
            st.text_input("Nama Supplier *", placeholder="Contoh: Roastery A, Makmur Plastik", key="s1_sup")
        with c1c:
            st.text_input("Nama Pencatat *", placeholder="Nama staf yang melakukan pembelian", key="s1_pencatat")

        st.markdown('<p class="form-section-title">📷 Foto Invoice — Wajib *</p>', unsafe_allow_html=True)
        st.caption("Satu foto untuk satu nota. Foto berlaku untuk semua item dalam nota yang sama.")
        _foto_bytes, _nama_foto, _jam_foto = render_foto_invoice()
        if _foto_bytes is None:
            st.warning("📷 Foto invoice belum diambil. Ambil foto nota sebelum menyimpan.")

        st.divider()

        st.markdown('<p class="form-section-title">🏷️ Seksi 2 — Identitas Barang</p>', unsafe_allow_html=True)

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
            nama_opts = NAMA_BARANG_MAP.get((st.session_state.s2_kategori, st.session_state.s2_sub), ["Lainnya"])
            if st.session_state.get("s2_nama_sel") not in nama_opts:
                st.session_state["s2_nama_sel"] = nama_opts[0]
            st.selectbox("Nama Barang *", nama_opts, key="s2_nama_sel")
            if st.session_state.s2_nama_sel == "Lainnya":
                st.text_input("Ketik Nama Barang Baru *", key="s2_nama_custom")
        with cd:
            presets = MERK_MAP.get(st.session_state.s2_nama_sel)
            if presets:
                st.selectbox("Merk / Brand", presets, key="s2_merk_sel")
                if st.session_state.get("s2_merk_sel") == "Lainnya":
                    st.text_input("Ketik Merk / Brand Baru", key="s2_merk_custom")
            else:
                st.text_input("Merk / Brand", key="s2_merk_free")
        with ce:
            is_kopi = (st.session_state.s2_kategori == "Bahan Baku Minuman" and st.session_state.s2_sub == "Coffee Beans")
            if is_kopi:
                st.selectbox("Grind Size (Khusus Kopi) *", GRIND_OPTIONS, key="s2_grind")
            else:
                st.selectbox("Grind Size", ["-"], key="s2_grind_dis", disabled=True)

        st.divider()

        st.markdown('<p class="form-section-title">📦 Seksi 3 — Detail Stok & Harga</p>', unsafe_allow_html=True)
        is_packaging = st.session_state.get("s2_kategori", "") == "Packaging"

        with st.form("form_catat", clear_on_submit=True):
            cA, cB, cC, cD = st.columns(4)
            with cA:
                f_qty = st.number_input("Kuantitas (Qty) *", min_value=0.0, step=1.0, format="%.2f")
            with cB:
                f_uom_qty = st.selectbox("Satuan Qty *", UOM_QTY_OPTIONS)
            with cC:
                f_vol = st.number_input("Berat/Vol per Unit", min_value=0.0, step=0.1, format="%.3f")
            with cD:
                f_uom_vol = st.selectbox("Satuan Vol", VOL_OPTIONS)

            multiplier  = QTY_MULTIPLIER.get(f_uom_qty, 1)
            faktor_vol  = VOL_FAKTOR.get(f_uom_vol, 1)
            netto_total = f_qty * multiplier * f_vol * faktor_vol

            st.divider()

            st.markdown("**💰 Harga**")
            cE, cF = st.columns([1, 2])
            with cE:
                f_harga_total = st.number_input("Harga Total (Rp) *", min_value=0, step=500)

            st.divider()
            st.markdown('<p class="form-section-title">🔍 Seksi 4 — Kontrol & Audit</p>', unsafe_allow_html=True)

            ci, cj = st.columns(2)
            with ci:
                if is_packaging:
                    f_exp = None
                    st.caption("ℹ️ Produk Packaging tidak memiliki tanggal kadaluarsa.")
                else:
                    f_exp = st.date_input("Tanggal Kadaluarsa", value=None)
            with cj:
                f_status = st.selectbox("Status Pembayaran *", STATUS_OPTIONS)

            f_catatan = st.text_area("Catatan Tambahan", height=80)

            submit_item = st.form_submit_button("➕ Tambahkan Item ke Nota Ini", type="primary", use_container_width=True)

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
                st.success(f"✅ **{nama_val}** ditambahkan ke nota. Tambah item lain atau Submit Transaksi Baru di bawah.")
                st.rerun()

        # ── KERANJANG DAN SUBMIT TRANSAKSI BARU ──────────────────────────────
        keranjang = st.session_state.get("item_keranjang", [])
        if keranjang:
            st.divider()
            st.markdown('<p class="form-section-title">🛒 Item dalam Nota Ini (Siap Disubmit)</p>', unsafe_allow_html=True)
            df_keranjang = pd.DataFrame(keranjang)
            cols_show_k = [c for c in ["nama_barang","merk","qty","uom_qty",
                                        "harga_total","tgl_kadaluarsa"] if c in df_keranjang.columns]
            st.dataframe(df_keranjang[cols_show_k], use_container_width=True, hide_index=True)
            
            total_keranjang = sum(item.get("harga_total", 0) for item in keranjang)
            st.info(f"🧾 **{len(keranjang)} item** · Total Estimasi: **Rp {total_keranjang:,.0f}**")

            col_simpan_all, col_batal = st.columns(2)
            with col_simpan_all:
                if st.button("💾 Submit Transaksi Baru (Simpan ke Database)", type="primary", use_container_width=True):
                    sup_val      = st.session_state.get("s1_sup", "").strip()
                    pencatat_val = st.session_state.get("s1_pencatat", "").strip()
                    nota_val     = st.session_state.get("s1_nota", "").strip()

                    errs_global = []
                    if not sup_val:       errs_global.append("Nama Supplier")
                    if not pencatat_val:  errs_global.append("Nama Pencatat")
                    if _foto_bytes is None: errs_global.append("Foto Invoice belum diambil")

                    if errs_global:
                        st.error("Harap penuhi di Seksi 1: " + " · ".join(errs_global))
                    else:
                        berhasil = 0
                        for item in keranjang:
                            ok = insert_row(item)
                            if ok:
                                berhasil += 1
                        if berhasil == len(keranjang):
                            st.success(f"✅ Transaksi nota **{nota_val or '-'}** berhasil disubmit!")
                            st.session_state["item_keranjang"] = []
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"Hanya {berhasil}/{len(keranjang)} item berhasil disimpan.")

            with col_batal:
                if st.button("🗑️ Batalkan Transaksi", use_container_width=True):
                    st.session_state["item_keranjang"] = []
                    st.rerun()

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: RIWAYAT TRANSAKSI
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_riwayat:
        if df.empty:
            empty_state("📃", "Belum Ada Riwayat", "Catat transaksi pertama di tab 'Catat Transaksi Baru'.")
        else:
            rf1, rf2, rf3 = st.columns(3)
            with rf1:
                cari = st.text_input("Cari Nama/Supplier", key="r_cari")
            with rf2:
                fil_kat = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="r_kat")
            with rf3:
                fil_st  = st.selectbox("Status", ["Semua"] + STATUS_OPTIONS, key="r_st")

            hasil = df.copy()
            if cari:
                mask = (
                    hasil["nama_barang"].str.contains(cari, case=False, na=False) |
                    hasil["supplier"].str.contains(cari, case=False, na=False) |
                    hasil["no_nota"].astype(str).str.contains(cari, case=False, na=False)
                )
                hasil = hasil[mask]
            if fil_kat != "Semua":
                hasil = hasil[hasil["kategori"] == fil_kat]
            if fil_st != "Semua":
                hasil = hasil[hasil["status_pembayaran"] == fil_st]

            urut = hasil.sort_values(["tanggal", "jam_transaksi"], ascending=False)
            
            # Tampilan Detail yang Informatif
            col_priority = [
                "tanggal", "no_nota", "supplier", "nama_barang", "merk",
                "qty", "uom_qty", "harga_total", "status_pembayaran", "nama_pencatat"
            ]
            cols_show = [c for c in col_priority if c in urut.columns]
            
            st.markdown("**(Hanya Menampilkan Kolom Utama)**")
            st.dataframe(urut[cols_show], use_container_width=True, hide_index=True)

            total_f = pd.to_numeric(hasil.get("harga_total", pd.Series()), errors="coerce").sum()
            st.caption(f"Menampilkan **{len(hasil)}** item · Total Nilai: **Rp {total_f:,.0f}**")

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
                "Pilih ID Transaksi untuk Diedit",
                df["id"].tolist(),
                format_func=lambda x: (
                    f"ID {x} — "
                    + str(df.loc[df["id"] == x, "nama_barang"].values[0])
                    if not df[df["id"] == x].empty else f"ID {x}"
                ),
                key="kelola_id",
            )

        baris = df[df["id"] == id_pilih]
        if baris.empty: return
        row = baris.iloc[0]

        with st.expander("✏️ Edit atau Hapus Transaksi Ini", expanded=True):
            with st.form(f"form_edit_{id_pilih}"):
                ea, eb, ec = st.columns(3)
                with ea:
                    e_tgl  = st.date_input("Tanggal", value=pd.to_datetime(row.get("tanggal", date.today())).date())
                    e_nota = st.text_input("No. Nota", value=str(row.get("no_nota") or ""))
                with eb:
                    e_sup  = st.text_input("Supplier", value=str(row.get("supplier") or ""))
                    e_qty  = st.number_input("Qty", value=float(row.get("qty", 0)), min_value=0.0, step=0.5)
                with ec:
                    e_hrg = st.number_input("Harga Total (Rp)", value=int(row.get("harga_total", 0)), min_value=0, step=500)
                    st_n  = row.get("status_pembayaran", STATUS_OPTIONS[0])
                    e_st  = st.selectbox("Status Pembayaran", STATUS_OPTIONS, index=STATUS_OPTIONS.index(st_n) if st_n in STATUS_OPTIONS else 0)

                if st.form_submit_button("Simpan Perubahan", type="primary"):
                    ok = update_row(id_pilih, {
                        "tanggal":           e_tgl.isoformat(),
                        "no_nota":           e_nota or None,
                        "supplier":          e_sup,
                        "qty":               float(e_qty),
                        "harga_total":       int(e_hrg),
                        "status_pembayaran": e_st,
                    })
                    if ok:
                        st.success("Data berhasil diperbarui!")
                        st.rerun()

            st.divider()
            konfirm = st.text_input('Ketik HAPUS untuk menghapus permanen data ini')
            if st.button("Hapus Sekarang", type="primary"):
                if konfirm.strip().upper() == "HAPUS":
                    ok = delete_row(id_pilih)
                    if ok:
                        st.success("Transaksi berhasil dihapus.")
                        st.rerun()
                else:
                    st.error('Ketik kata HAPUS (huruf kapital semua) untuk konfirmasi.')


# ─── PAGE: KONTROL & AUDIT ────────────────────────────────────────────────────────
def page_kontrol_audit(df: pd.DataFrame):
    st.title("🔍 Kontrol & Audit")

    if df.empty:
        empty_state("🔍", "Belum Ada Data", "Data muncul setelah transaksi dicatat.")
        return

    df["harga_total"] = pd.to_numeric(df["harga_total"], errors="coerce").fillna(0)

    tab_exp, tab_kas, tab_log = st.tabs([
        "⚠️ Peringatan Kadaluarsa",
        "💳 Arus Kas & Hutang",
        "📋 Audit Log",
    ])

    # ── KADALUARSA ───────────────────────────────────────────────────────────────
    with tab_exp:
        st.subheader("📅 Status Peringatan Kadaluarsa")
        if "tgl_kadaluarsa" not in df.columns:
            st.info("Kolom kadaluarsa tidak tersedia.")
        else:
            df_exp = df[df["tgl_kadaluarsa"].notna() & (df["tgl_kadaluarsa"].astype(str).str.strip().isin(["", "None"]) == False)].copy()

            if df_exp.empty:
                empty_state("📅", "Aman", "Belum ada item bahan baku yang didaftarkan tanggal kadaluarsanya.")
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
                c1.metric("🔴 Kritis (≤7 hari)", len(kritis))
                c2.metric("🟡 Mendekat (8–30 hari)", len(mendekat))
                c3.metric("🟢 Aman (>30 hari)", len(aman))

                exp_cols = [c for c in ["nama_barang","merk","qty","uom_qty","tgl_kadaluarsa","catatan"] if c in df_exp.columns]
                
                if not kritis.empty:
                    st.error("🚨 Barang Kritis — Segera Pakai atau Retur ke Supplier!")
                    st.dataframe(kritis[exp_cols].sort_values("tgl_kadaluarsa"), use_container_width=True, hide_index=True)
                if not mendekat.empty:
                    st.warning("⚠️ Akan Kadaluarsa dalam 30 Hari")
                    st.dataframe(mendekat[exp_cols].sort_values("tgl_kadaluarsa"), use_container_width=True, hide_index=True)

    # ── ARUS KAS ─────────────────────────────────────────────────────────────────
    with tab_kas:
        st.subheader("💸 Pengawasan Arus Kas Keluar")
        total_all    = df["harga_total"].sum()
        total_lunas  = df[df["status_pembayaran"] == "Lunas"]["harga_total"].sum()
        total_hutang = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)]["harga_total"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Pembelian", f"Rp {total_all:,.0f}")
        c2.metric("✅ Sudah Lunas", f"Rp {total_lunas:,.0f}")
        c3.metric("⏳ Belum Lunas / Hutang", f"Rp {total_hutang:,.0f}")

        st.markdown("---")
        st.subheader("📋 Transaksi Membutuhkan Pelunasan (Hutang/Tempo)")
        belum = df[df["status_pembayaran"] != "Lunas"]
        if not belum.empty:
            bl_cols = [c for c in ["tanggal","no_nota","supplier","nama_barang","harga_total","status_pembayaran"] if c in belum.columns]
            bl_sorted = belum[bl_cols].sort_values("tanggal") if "tanggal" in belum.columns else belum[bl_cols]
            st.dataframe(bl_sorted, use_container_width=True, hide_index=True)
        else:
            st.success("Semua transaksi sudah berstatus Lunas!")

    # ── AUDIT LOG ────────────────────────────────────────────────────────────────
    with tab_log:
        st.subheader("📋 Log Keseluruhan")

        lf1, lf2, lf3 = st.columns(3)
        with lf1:
            kat_f  = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="log_kat")
        with lf2:
            sort_f = st.selectbox("Urutkan", ["tanggal","harga_total","supplier","nama_barang"], key="log_sort")
        with lf3:
            asc_f  = st.selectbox("Urutan", ["Terbaru dulu","Terlama dulu"], key="log_asc")

        log_df = df.copy()
        if kat_f != "Semua": log_df = log_df[log_df["kategori"] == kat_f]
        if sort_f in log_df.columns:
            log_df = log_df.sort_values(sort_f, ascending=(asc_f == "Terlama dulu"))

        st.dataframe(log_df, use_container_width=True, hide_index=True)

        if st.session_state.role == "manager":
            csv = log_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Export Data ke CSV",
                data=csv,
                file_name=f"audit_log_{st.session_state.cabang}_{date.today()}.csv",
                mime="text/csv",
            )


# ─── MAIN ────────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        show_login()
        return

    page = show_sidebar()
    df   = get_data(st.session_state.cabang)

    if   page == "📊 Dashboard":       page_dashboard(df)
    elif page == "📋 Administrasi":    page_administrasi(df)
    elif page == "🔍 Kontrol & Audit": page_kontrol_audit(df)

if __name__ == "__main__":
    main()
