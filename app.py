"""
=============================================================================
SISTEM INVENTARIS REAL-TIME PT. SARI TROPIS INDONESIA
=============================================================================
Arsitektur: Event-Driven + Relational Data Modeling
Database   : Supabase (Inventory DB + POS DB)
Framework  : Streamlit

STRUKTUR TABEL SUPABASE (jalankan SQL ini di Supabase SQL Editor):
--------------------------------------------------------------------
-- branches, ingredients, menu_items, recipes, inventory_logs
-- Lihat komentar di bagian SUPABASE SCHEMA REFERENCE di bawah ini.
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from io import BytesIO
import json
import requests

# ==========================================
# 1. KONFIGURASI HALAMAN & SUPABASE CLIENT
# ==========================================
st.set_page_config(
    page_title="Real-Time Inventory – PT. Sari Tropis Indonesia",
    layout="wide",
    page_icon="☕"
)

# Kredensial diambil dari secrets.toml (Streamlit Cloud) atau environment
SUPABASE_INV_URL = st.secrets["SUPABASE_INV_URL"]
SUPABASE_INV_KEY = st.secrets["SUPABASE_INV_KEY"]

SUPABASE_POS_URL = st.secrets["SUPABASE_POS_URL"]
SUPABASE_POS_KEY = st.secrets["SUPABASE_POS_KEY"]

# ===========================================================================
# SUPABASE SCHEMA REFERENCE
# Jalankan SQL berikut di Supabase SQL Editor (Database Inventory):
#
# CREATE TABLE branches (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     branch_name TEXT NOT NULL,   -- 'Buper', 'WKA'
#     location TEXT
# );
#
# CREATE TABLE ingredients (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     branch_id UUID REFERENCES branches(id),
#     item_name TEXT NOT NULL,
#     category TEXT,               -- 'Bahan Baku' | 'Packaging'
#     brand TEXT,
#     stock_quantity DECIMAL DEFAULT 0,
#     unit TEXT,                   -- 'ml' | 'gr' | 'pcs'
#     reorder_level DECIMAL DEFAULT 10,
#     unit_price DECIMAL,
#     purchase_date DATE,
#     expiry_date DATE,
#     last_updated TIMESTAMPTZ DEFAULT NOW()
# );
#
# CREATE TABLE menu_items (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     menu_name TEXT NOT NULL UNIQUE,
#     category TEXT                -- 'Makanan' | 'Minuman Panas' | 'Minuman Dingin'
# );
#
# CREATE TABLE recipes (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     menu_id UUID REFERENCES menu_items(id),
#     ingredient_id UUID REFERENCES ingredients(id),
#     quantity_required DECIMAL NOT NULL,
#     component_type TEXT          -- 'bahan' | 'packaging'
# );
#
# CREATE TABLE inventory_logs (
#     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
#     branch_id UUID REFERENCES branches(id),
#     ingredient_id UUID REFERENCES ingredients(id),
#     ingredient_name TEXT,
#     change_type TEXT,            -- 'POS_SYNC' | 'Testing' | 'Content' | 'Staff' | 'Restock'
#     quantity_changed DECIMAL,    -- negatif = berkurang, positif = bertambah
#     menu_name TEXT,
#     noted_by TEXT,
#     notes TEXT,
#     created_at TIMESTAMPTZ DEFAULT NOW()
# );
# ===========================================================================


# ==========================================
# 2. SUPABASE REST API HELPERS
# ==========================================

def _inv_headers():
    return {
        "apikey": SUPABASE_INV_KEY,
        "Authorization": f"Bearer {SUPABASE_INV_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def _pos_headers():
    return {
        "apikey": SUPABASE_POS_KEY,
        "Authorization": f"Bearer {SUPABASE_POS_KEY}",
        "Content-Type": "application/json"
    }


def supabase_inv_get(table: str, params: dict = None) -> list:
    """GET dari tabel Inventory Supabase."""
    try:
        url = f"{SUPABASE_INV_URL}/rest/v1/{table}"
        r = requests.get(url, headers=_inv_headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"[INV DB] Gagal membaca '{table}': {e}. Menggunakan data dummy.")
        return []


def supabase_inv_post(table: str, payload: dict) -> dict:
    """INSERT ke tabel Inventory Supabase."""
    try:
        url = f"{SUPABASE_INV_URL}/rest/v1/{table}"
        r = requests.post(url, headers=_inv_headers(), json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"[INV DB] Gagal insert ke '{table}': {e}")
        return {}


def supabase_inv_patch(table: str, filters: dict, payload: dict) -> dict:
    """UPDATE tabel Inventory Supabase dengan filter."""
    try:
        url = f"{SUPABASE_INV_URL}/rest/v1/{table}"
        params = {k: f"eq.{v}" for k, v in filters.items()}
        r = requests.patch(url, headers=_inv_headers(), params=params, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"[INV DB] Gagal update '{table}': {e}")
        return {}


def supabase_pos_get(table: str, params: dict = None) -> list:
    """GET dari tabel POS Supabase."""
    try:
        url = f"{SUPABASE_POS_URL}/rest/v1/{table}"
        r = requests.get(url, headers=_pos_headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"[POS DB] Gagal membaca '{table}': {e}. Menggunakan data dummy.")
        return []


# ==========================================
# 3. UNIT CONVERSION HANDLER
# Konversi unit pembelian → unit resep
# Misal: beli 1 karton susu (12 Liter) → 12.000 ml di database
# ==========================================

UNIT_CONVERSION = {
    # (unit_beli, unit_resep): faktor_konversi
    ("liter", "ml"): 1000,
    ("kg", "gr"): 1000,
    ("karton_susu", "ml"): 12000,   # 1 karton = 12 botol x 1000ml
    ("dus_gelas", "pcs"): 50,       # 1 dus gelas = 50 pcs
    ("pack_sedotan", "pcs"): 100,
    ("botol_sirup", "ml"): 600,     # 1 botol sirup 600ml
    ("kantong_kopi", "gr"): 200,    # 1 kantong 200gr
}

def convert_unit(quantity: float, unit_beli: str, unit_resep: str) -> float:
    """
    Mengkonversi kuantitas dari satuan pembelian ke satuan resep.
    Contoh: convert_unit(1, 'karton_susu', 'ml') → 12000.0
    """
    key = (unit_beli.lower(), unit_resep.lower())
    if key in UNIT_CONVERSION:
        return quantity * UNIT_CONVERSION[key]
    elif unit_beli.lower() == unit_resep.lower():
        return quantity  # sudah sama, tidak perlu konversi
    else:
        st.warning(f"Konversi '{unit_beli}' → '{unit_resep}' tidak ditemukan. Gunakan nilai asli.")
        return quantity


# ==========================================
# 4. STANDAR RESEP (Dari PDF Panduan Resep)
# Struktur: menu_name → {bahan: {nama: takaran}, packaging: {nama: qty}, kategori}
# Nama menu HARUS sinkron dengan field 'name' di tabel transactions_rows POS
# ==========================================

RESEP_STANDAR = {
    # ===== MAKANAN =====
    "Kentang Goreng": {
        "bahan": {"Kentang (gr)": 100, "Minyak Goreng (ml)": 50},
        "packaging": {"Packaging Makanan (box)": 1, "Kresek": 1},
        "kategori": "Makanan"
    },
    "Kentang Sosis": {
        "bahan": {"Kentang (gr)": 100, "Sosis (pcs)": 2, "Minyak Goreng (ml)": 50},
        "packaging": {"Packaging Makanan (box)": 1, "Kresek": 1},
        "kategori": "Makanan"
    },
    "Pisang Keju": {
        "bahan": {"Pisang (pcs)": 2, "Keju (gr)": 15, "Susu Kental Manis (ml)": 10},
        "packaging": {"Packaging Makanan (box)": 1, "Kresek": 1},
        "kategori": "Makanan"
    },
    "Dimsum": {
        "bahan": {"Dimsum (pcs)": 5},
        "packaging": {"Packaging Makanan (box)": 1, "Kresek": 1},
        "kategori": "Makanan"
    },

    # ===== MINUMAN PANAS =====
    "Kopi Tubruk": {
        "bahan": {"Beans Natural (gr)": 13, "Gula (gr)": 10, "Air Panas (ml)": 150},
        "packaging": {"Cup Panas": 1, "Tutup Cup Panas": 1},
        "kategori": "Minuman Panas"
    },
    "Americano Hot": {
        "bahan": {"Espresso (ml)": 36, "Air Panas (ml)": 120},
        "packaging": {"Cup Panas": 1, "Tutup Cup Panas": 1},
        "kategori": "Minuman Panas"
    },
    "Latte Hot": {
        "bahan": {"Espresso (ml)": 36, "Susu Diamond (ml)": 150},
        "packaging": {"Cup Panas": 1, "Tutup Cup Panas": 1},
        "kategori": "Minuman Panas"
    },

    # ===== MINUMAN DINGIN =====
    "Latte Series (Ice)": {
        "bahan": {"Powder (gr)": 25, "Es Batu (gr)": 100, "Susu Diamond (ml)": 200},
        "packaging": {"Cup Dingin (Large)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
    "Greentea Latte": {
        "bahan": {
            "Greentea Powder (gr)": 7,
            "Susu Kental Manis (ml)": 10,
            "Simple Syrup (ml)": 10,
            "Es Batu (gr)": 100,
            "Susu Diamond (ml)": 100
        },
        "packaging": {"Cup Dingin (Large)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
    "Americano Ice": {
        "bahan": {"Espresso (ml)": 36, "Es Batu (gr)": 40, "Air Mineral (ml)": 100},
        "packaging": {"Cup Dingin (Medium)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
    "Es Kopi Lemon": {
        "bahan": {
            "Espresso (ml)": 36,
            "Gula Aren (ml)": 25,
            "Perasan Lemon (ml)": 10,
            "Es Batu (gr)": 100
        },
        "packaging": {"Cup Dingin (Large)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
    "Kopi Susu Gula Aren": {
        "bahan": {
            "Espresso (ml)": 36,
            "Gula Aren (ml)": 30,
            "Susu Diamond (ml)": 150,
            "Es Batu (gr)": 100
        },
        "packaging": {"Cup Dingin (Large)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
    "Matcha Latte": {
        "bahan": {
            "Matcha Powder (gr)": 8,
            "Simple Syrup (ml)": 15,
            "Es Batu (gr)": 100,
            "Susu Diamond (ml)": 150
        },
        "packaging": {"Cup Dingin (Large)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
    "Taro Latte": {
        "bahan": {
            "Taro Powder (gr)": 25,
            "Simple Syrup (ml)": 10,
            "Es Batu (gr)": 100,
            "Susu Diamond (ml)": 150
        },
        "packaging": {"Cup Dingin (Large)": 1, "Tutup Cup Dingin": 1},
        "kategori": "Minuman Dingin"
    },
}


# ==========================================
# 5. ENGINE: PEMOTONGAN STOK
# ==========================================

def get_pemotongan_stok(nama_menu: str, jumlah: int, mode: str = "full") -> dict:
    """
    Hitung pengurangan stok berdasarkan resep standar.

    Args:
        nama_menu : nama menu (harus ada di RESEP_STANDAR)
        jumlah    : jumlah porsi/cup yang dibuat
        mode      : 'full'           → potong bahan + packaging
                    'bahan_only'     → potong bahan saja (uji resep)
                    'packaging_only' → potong packaging saja

    Returns:
        dict {nama_bahan/packaging: total_pengurangan}
    """
    resep = RESEP_STANDAR.get(nama_menu, {})
    stok_dipotong = {}

    if mode in ("full", "bahan_only"):
        for bahan, takaran in resep.get("bahan", {}).items():
            stok_dipotong[bahan] = round(takaran * jumlah, 2)

    if mode in ("full", "packaging_only"):
        for pkg, qty in resep.get("packaging", {}).items():
            stok_dipotong[pkg] = round(qty * jumlah, 2)

    return stok_dipotong


# ==========================================
# 6. ENGINE: SINKRONISASI OTOMATIS POS → INVENTORY
# Dipanggil setiap ada transaksi baru di POS
# ==========================================

def sync_pos_to_inventory(pos_transaction_data: dict, cabang: str, dry_run: bool = False) -> dict:
    """
    Trigger utama: memproses satu record transaksi dari POS dan
    mengurangi stok inventory secara otomatis.

    Args:
        pos_transaction_data : dict dengan key 'items' (list of {name, quantity})
        cabang               : nama cabang ('Buper' atau 'WKA')
        dry_run              : jika True, hanya simulasi tanpa tulis ke DB

    Returns:
        dict ringkasan {menu: {bahan: jumlah_dikurangi}}
    """
    ringkasan = {}

    items = pos_transaction_data.get("items", [])
    if not items:
        return ringkasan

    for item in items:
        menu_name = item.get("name", "")
        qty_ordered = item.get("quantity", 1)

        # 1. Cari resep berdasarkan nama menu (lookup dari RESEP_STANDAR)
        if menu_name not in RESEP_STANDAR:
            st.warning(f"⚠️ Menu '{menu_name}' tidak ditemukan di Standar Resep. Stok tidak dipotong.")
            continue

        # 2. Hitung total kebutuhan bahan (Takaran × Jumlah Pesanan)
        stok_dipotong = get_pemotongan_stok(menu_name, qty_ordered, mode="full")
        ringkasan[menu_name] = stok_dipotong

        # 3. Update stok di Supabase Inventory (per bahan)
        for nama_bahan, jumlah_kurang in stok_dipotong.items():
            if not dry_run:
                # UPDATE ingredients SET stock_quantity = stock_quantity - jumlah_kurang
                # WHERE item_name = nama_bahan AND branch = cabang
                supabase_inv_patch(
                    table="ingredients",
                    filters={"item_name": nama_bahan, "branch_name": cabang},
                    payload={"stock_quantity": f"stock_quantity - {jumlah_kurang}"}
                    # Catatan: Supabase mendukung RPC untuk operasi atomik seperti ini.
                    # Gunakan Supabase Function/RPC untuk produksi agar tidak race condition.
                )

                # 4. Catat ke inventory_logs
                supabase_inv_post("inventory_logs", {
                    "ingredient_name": nama_bahan,
                    "change_type": "POS_SYNC",
                    "quantity_changed": -jumlah_kurang,
                    "menu_name": menu_name,
                    "noted_by": "SYSTEM_POS",
                    "notes": f"Auto-sync dari transaksi POS: {menu_name} x{qty_ordered}",
                    "created_at": datetime.now().isoformat()
                })

                # 5. Cek peringatan restock
                check_restock_alert(nama_bahan, cabang)

    return ringkasan


def check_restock_alert(nama_bahan: str, cabang: str) -> str:
    """
    Mengecek status stok setelah pengurangan dan mengembalikan level peringatan.

    Returns:
        'CRITICAL' | 'WARNING' | 'SAFE'
    """
    rows = supabase_inv_get("ingredients", {
        "item_name": f"eq.{nama_bahan}",
        "select": "stock_quantity,reorder_level"
    })

    if not rows:
        return "UNKNOWN"

    stock = rows[0].get("stock_quantity", 0)
    reorder = rows[0].get("reorder_level", 10)

    if stock <= 0:
        return "CRITICAL"
    elif stock < reorder:
        return "WARNING"
    return "SAFE"


# ==========================================
# 7. ENGINE: PREDIKSI RESTOCK (ROP + Moving Average)
# Reorder Point (ROP) = (ADU × Lead Time) + Safety Stock
# ==========================================

def calculate_inventory_prediction(df_inventory: pd.DataFrame,
                                   df_logs: pd.DataFrame,
                                   lead_time_days: int = 2,
                                   safety_stock_days: int = 3,
                                   window_days: int = 7) -> pd.DataFrame:
    """
    Menghitung prediksi ketersediaan stok menggunakan:
    - Average Daily Usage (ADU) dari log 'window_days' hari terakhir
    - Reorder Point (ROP) = ADU × Lead Time + Safety Stock
    - Estimasi tanggal habis dan status peringatan

    Args:
        df_inventory   : DataFrame stok saat ini
        df_logs        : DataFrame inventory_logs (history penggunaan)
        lead_time_days : estimasi hari pengiriman supplier
        safety_stock_days: cadangan stok (dalam hari pemakaian)
        window_days    : jendela analisis moving average

    Returns:
        df_inventory yang sudah ditambahkan kolom prediksi
    """
    df = df_inventory.copy()

    # Hitung ADU dari log history (7 hari terakhir)
    if not df_logs.empty and "ingredient_name" in df_logs.columns:
        cutoff = datetime.now() - timedelta(days=window_days)
        df_logs["created_at"] = pd.to_datetime(df_logs["created_at"], errors="coerce")
        recent_logs = df_logs[
            (df_logs["created_at"] >= cutoff) &
            (df_logs["quantity_changed"] < 0)  # hanya pengurangan
        ].copy()
        recent_logs["quantity_changed"] = recent_logs["quantity_changed"].abs()

        adu_map = recent_logs.groupby("ingredient_name")["quantity_changed"].sum() / window_days
    else:
        adu_map = pd.Series(dtype=float)

    # Gabungkan ADU ke df inventory
    df["ADU (per hari)"] = df["Item"].map(adu_map).fillna(0)
    # Jika ADU = 0 (tidak ada log), gunakan estimasi kasar: stok / 30 hari
    df["ADU (per hari)"] = df.apply(
        lambda r: r["ADU (per hari)"] if r["ADU (per hari)"] > 0
        else max(0.1, round(r["Sisa Stok"] / 30, 2)),
        axis=1
    )

    # Estimasi hari tersisa
    df["Estimasi Habis (Hari)"] = (df["Sisa Stok"] / df["ADU (per hari)"]).apply(
        lambda x: round(max(x, 0), 1)
    )

    # Reorder Point
    df["ROP"] = df["ADU (per hari)"] * (lead_time_days + safety_stock_days)
    df["ROP"] = df["ROP"].apply(lambda x: round(x, 1))

    # Prediksi tanggal habis & restock
    df["Prediksi Habis"] = df["Estimasi Habis (Hari)"].apply(
        lambda x: (datetime.now() + timedelta(days=x)).strftime("%d %b %Y")
    )
    df["Tanggal Restock"] = df["Estimasi Habis (Hari)"].apply(
        lambda x: max(0, x - lead_time_days)
    ).apply(
        lambda x: (datetime.now() + timedelta(days=x)).strftime("%d %b %Y")
    )

    # Status berdasarkan ROP dan hari tersisa
    def tentukan_status(row):
        if row["Sisa Stok"] <= 0:
            return "🚫 Habis!"
        elif row["Sisa Stok"] < row["ROP"] or row["Sisa Stok"] < row["Batas Aman"]:
            return "🚨 Restock!"
        elif row["Estimasi Habis (Hari)"] <= 5:
            return "⚠️ Segera Restock"
        elif row["Estimasi Habis (Hari)"] <= 7:
            return "🟡 Perhatian"
        return "✅ Aman"

    df["Status"] = df.apply(tentukan_status, axis=1)
    return df


def check_fefo_alerts(df_inventory: pd.DataFrame, hari_peringatan: int = 7) -> pd.DataFrame:
    """
    FEFO: First Expired First Out
    Mengembalikan item yang akan kedaluwarsa dalam 'hari_peringatan' hari ke depan.
    """
    df = df_inventory.copy()
    df["Tanggal Kadaluwarsa"] = pd.to_datetime(df["Tanggal Kadaluwarsa"], errors="coerce")
    batas = datetime.now() + timedelta(days=hari_peringatan)
    akan_exp = df[df["Tanggal Kadaluwarsa"].notna() & (df["Tanggal Kadaluwarsa"] <= batas)]
    return akan_exp


# ==========================================
# 8. DUMMY DATABASE (Fallback jika Supabase tidak tersambung)
# ==========================================

def get_dummy_inventory(cabang: str = "Buper") -> pd.DataFrame:
    data = {
        "Buper": pd.DataFrame({
            "ID": range(1, 19),
            "Item": [
                "Kentang (gr)", "Sosis (pcs)", "Minyak Goreng (ml)", "Pisang (pcs)",
                "Keju (gr)", "Dimsum (pcs)", "Beans Natural (gr)", "Espresso (ml)",
                "Susu Diamond (ml)", "Susu Kental Manis (ml)", "Simple Syrup (ml)",
                "Gula Aren (ml)", "Es Batu (gr)", "Greentea Powder (gr)",
                "Cup Dingin (Large)", "Cup Panas", "Packaging Makanan (box)", "Kresek"
            ],
            "Merk": [
                "Lokal", "Champ", "Bimoli", "Lokal",
                "Kraft", "Siomay Merek A", "Mandailing", "",
                "Diamond", "Frisian Flag", "Homemade", "Homemade", "", "Matcha JP",
                "Gelas Plastik 16oz", "Gelas Kertas", "Kraft Box S", "Hdpe"
            ],
            "Kategori": [
                "Bahan Baku", "Bahan Baku", "Bahan Baku", "Bahan Baku",
                "Bahan Baku", "Bahan Baku", "Bahan Baku", "Bahan Baku",
                "Bahan Baku", "Bahan Baku", "Bahan Baku", "Bahan Baku", "Bahan Baku", "Bahan Baku",
                "Packaging", "Packaging", "Packaging", "Packaging"
            ],
            "Sisa Stok": [
                1500, 20, 3000, 30,
                200, 50, 500, 720,
                4000, 800, 600, 700, 5000, 80,
                45, 30, 120, 200
            ],
            "Satuan": [
                "gr", "pcs", "ml", "pcs",
                "gr", "pcs", "gr", "ml",
                "ml", "ml", "ml", "ml", "gr", "gr",
                "pcs", "pcs", "pcs", "pcs"
            ],
            "Batas Aman": [
                2000, 50, 2000, 50,
                300, 100, 1000, 1000,
                5000, 1000, 500, 500, 3000, 200,
                100, 100, 100, 100
            ],
            "Tanggal Beli": ["2025-07-01"] * 18,
            "Tanggal Kadaluwarsa": [
                "2025-12-31", "2025-09-01", "2026-01-01", "2025-07-10",
                "2025-11-01", "2025-09-15", "2026-03-01", "",
                "2025-08-01", "2025-10-01", "2025-08-20", "2025-08-20",
                "", "2026-06-01",
                "2026-06-01", "2026-06-01", "2026-06-01", "2026-06-01"
            ],
            "Harga Beli (Rp)": [
                15000, 25000, 30000, 10000,
                22000, 18000, 120000, 0,
                28000, 12000, 5000, 8000, 5000, 85000,
                45000, 30000, 25000, 8000
            ],
            "Cabang": ["Buper"] * 18
        }),
        "WKA": pd.DataFrame({
            "ID": range(1, 15),
            "Item": [
                "Kentang (gr)", "Sosis (pcs)", "Beans Natural (gr)",
                "Susu Diamond (ml)", "Simple Syrup (ml)",
                "Gula Aren (ml)", "Es Batu (gr)", "Matcha Powder (gr)",
                "Cup Dingin (Large)", "Cup Panas", "Packaging Makanan (box)", "Kresek",
                "Espresso (ml)", "Susu Kental Manis (ml)"
            ],
            "Merk": [
                "Lokal", "Champ", "Mandailing",
                "Diamond", "Homemade",
                "Homemade", "", "Matcha JP",
                "Gelas Plastik 16oz", "Gelas Kertas", "Kraft Box S", "Hdpe",
                "", "Frisian Flag"
            ],
            "Kategori": [
                "Bahan Baku", "Bahan Baku", "Bahan Baku",
                "Bahan Baku", "Bahan Baku",
                "Bahan Baku", "Bahan Baku", "Bahan Baku",
                "Packaging", "Packaging", "Packaging", "Packaging",
                "Bahan Baku", "Bahan Baku"
            ],
            "Sisa Stok": [
                800, 10, 300,
                2000, 250,
                300, 4000, 50,
                20, 15, 60, 100,
                500, 400
            ],
            "Satuan": [
                "gr", "pcs", "gr",
                "ml", "ml",
                "ml", "gr", "gr",
                "pcs", "pcs", "pcs", "pcs",
                "ml", "ml"
            ],
            "Batas Aman": [
                2000, 50, 1000,
                5000, 500,
                500, 3000, 200,
                100, 100, 100, 100,
                1000, 1000
            ],
            "Tanggal Beli": ["2025-07-01"] * 14,
            "Tanggal Kadaluwarsa": [
                "2025-12-31", "2025-09-01", "2026-03-01",
                "2025-08-01", "2025-08-20",
                "2025-08-20", "", "2026-06-01",
                "2026-06-01", "2026-06-01", "2026-06-01", "2026-06-01",
                "", "2025-10-01"
            ],
            "Harga Beli (Rp)": [
                15000, 25000, 120000,
                28000, 5000,
                8000, 5000, 85000,
                45000, 30000, 25000, 8000,
                0, 12000
            ],
            "Cabang": ["WKA"] * 14
        })
    }
    return data.get(cabang, data["Buper"])


def get_dummy_logs() -> pd.DataFrame:
    """Dummy log penggunaan untuk 7 hari ke belakang (simulasi ADU)."""
    today = datetime.now()
    rows = []
    items_sample = [
        ("Susu Diamond (ml)", -200), ("Espresso (ml)", -72), ("Es Batu (gr)", -300),
        ("Gula Aren (ml)", -50), ("Cup Dingin (Large)", -3), ("Beans Natural (gr)", -26),
        ("Packaging Makanan (box)", -2), ("Sosis (pcs)", -4), ("Greentea Powder (gr)", -14),
    ]
    for i in range(7):
        tgl = today - timedelta(days=i)
        for nama, qty in items_sample:
            rows.append({
                "ingredient_name": nama,
                "quantity_changed": qty * (1 + i % 2),
                "change_type": "POS_SYNC",
                "created_at": tgl.isoformat(),
                "noted_by": "SYSTEM_POS",
                "menu_name": "Berbagai Menu"
            })
    return pd.DataFrame(rows)


def load_inventory(cabang: str) -> pd.DataFrame:
    """
    Load data inventory dari Supabase (primary) atau dummy (fallback).
    """
    rows = supabase_inv_get("ingredients", {"branch_name": f"eq.{cabang}"})
    if rows:
        df = pd.DataFrame(rows)
        # Rename kolom agar konsisten dengan dummy
        rename_map = {
            "item_name": "Item", "category": "Kategori", "brand": "Merk",
            "stock_quantity": "Sisa Stok", "unit": "Satuan",
            "reorder_level": "Batas Aman", "purchase_date": "Tanggal Beli",
            "expiry_date": "Tanggal Kadaluwarsa", "unit_price": "Harga Beli (Rp)"
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        df["Cabang"] = cabang
        return df
    # Fallback ke dummy
    return get_dummy_inventory(cabang)


def load_logs(cabang: str, days: int = 7) -> pd.DataFrame:
    """
    Load log penggunaan dari Supabase (primary) atau dummy (fallback).
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = supabase_inv_get("inventory_logs", {
        "created_at": f"gte.{cutoff}",
        "order": "created_at.desc"
    })
    if rows:
        return pd.DataFrame(rows)
    return get_dummy_logs()


# ==========================================
# 9. MANAJEMEN SESSION STATE
# ==========================================

for key, default in [
    ("logged_in", False),
    ("role", ""),
    ("cabang", ""),
    ("log_transaksi_manual", []),
    ("last_pos_sync", None),
    ("pos_sync_results", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

USERS = {
    "kasir_buper": {"password": "123", "role": "Kasir", "cabang": "Buper"},
    "kasir_wka":   {"password": "123", "role": "Kasir", "cabang": "WKA"},
    "manager_buper": {"password": "123", "role": "Manager", "cabang": "Buper"},
    "manager_wka":   {"password": "123", "role": "Manager", "cabang": "WKA"},
    "owner_buper": {"password": "123", "role": "Owner Cabang", "cabang": "Buper"},
    "owner_wka":   {"password": "123", "role": "Owner Cabang", "cabang": "WKA"},
    "owner_pusat": {"password": "123", "role": "Owner Pusat", "cabang": "Semua"}
}


# ==========================================
# 10. HALAMAN LOGIN
# ==========================================

def login():
    st.title("☕ Login – Sistem Inventaris PT. Sari Tropis Indonesia")
    st.subheader("Sistem Pencatatan & Dashboard Prediksi Stok Inventaris Bahan Baku dan Packaging")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### Silakan masuk sesuai peran Anda")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("🔓 Masuk", use_container_width=True)
            if submit:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.role = USERS[username]["role"]
                    st.session_state.cabang = USERS[username]["cabang"]
                    st.success(f"✅ Login sebagai **{st.session_state.role}** – Cabang {st.session_state.cabang}")
                    st.rerun()
                else:
                    st.error("❌ Username atau Password salah!")

def logout():
    for key in ["logged_in", "role", "cabang", "log_transaksi_manual",
                "last_pos_sync", "pos_sync_results"]:
        st.session_state[key] = False if key == "logged_in" else "" if key in ("role", "cabang") else [] if key == "log_transaksi_manual" else None if "sync" in key else {}
    st.rerun()


# ==========================================
# 11. HALAMAN KASIR – Pencatatan Manual Non-POS
# ==========================================

def halaman_kasir():
    st.header(f"Panel Kasir  Cabang {st.session_state.cabang}")
    st.info(
        "Formulir ini untuk mencatat **penggunaan bahan baku di luar transaksi POS resmi**. "
        "Pengurangan stok dari transaksi pelanggan sudah otomatis terjadi via sinkronisasi POS."
    )

    tab1, tab2, tab3 = st.tabs([
        "📝 Catat Penggunaan Manual",
        "📋 Riwayat Pencatatan Hari Ini",
        "🔄 Simulasi Sync POS"
    ])

    # ── Tab 1: Input Manual ──────────────────────────────────────
    with tab1:
        KATEGORI_MAP = {
            "Uji Coba Resep (Bahan Baku Saja  tanpa Packaging)": "bahan_only",
            "Foto/Konten Promosi Sosmed (Bahan Baku + Packaging)": "full",
            "Konsumsi Pribadi Barista (Bahan Baku + Packaging)": "full",
            "Konsumsi Pribadi Barista (Packaging Saja  bahan tidak dari stok)": "packaging_only",
        }

        with st.form("form_penggunaan_manual"):
            st.subheader("Catat Penggunaan Internal")
            col_a, col_b = st.columns(2)
            with col_a:
                jenis_label = st.selectbox("Tujuan Penggunaan", list(KATEGORI_MAP.keys()))
                nama_barista = st.text_input("Nama Barista")
            with col_b:
                menu_terkait = st.selectbox("Pilih Menu/Item", list(RESEP_STANDAR.keys()))
                jumlah = st.number_input("Jumlah Porsi / Cup", min_value=1, step=1, value=1)

            catatan = st.text_area(
                "Catatan Tambahan",
                placeholder="Contoh: Latihan lomba barista, foto untuk Instagram @saritropis"
            )
            submit_manual = st.form_submit_button("✅ Catat & Potong Stok", use_container_width=True)

            if submit_manual:
                mode = KATEGORI_MAP[jenis_label]
                # Tentukan change_type untuk log
                change_type_map = {
                    "bahan_only": "Testing",
                    "full": "Content" if "Konten" in jenis_label else "Staff",
                    "packaging_only": "Staff"
                }
                change_type = change_type_map.get(mode, "Staff")

                stok_dipotong = get_pemotongan_stok(menu_terkait, jumlah, mode=mode)

                log_entry = {
                    "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "barista": nama_barista or "Tidak Disebutkan",
                    "tujuan": jenis_label,
                    "menu": menu_terkait,
                    "jumlah": jumlah,
                    "stok_dipotong": stok_dipotong,
                    "catatan": catatan,
                    "cabang": st.session_state.cabang,
                    "change_type": change_type
                }
                st.session_state.log_transaksi_manual.append(log_entry)

                # Kirim ke Supabase inventory_logs + update stok
                for nama_bahan, jumlah_kurang in stok_dipotong.items():
                    supabase_inv_post("inventory_logs", {
                        "ingredient_name": nama_bahan,
                        "change_type": change_type,
                        "quantity_changed": -jumlah_kurang,
                        "menu_name": menu_terkait,
                        "noted_by": nama_barista or "Tidak Disebutkan",
                        "notes": catatan,
                        "created_at": datetime.now().isoformat()
                    })
                    # Update stok
                    supabase_inv_patch(
                        "ingredients",
                        {"item_name": nama_bahan},
                        {"stock_quantity": f"stock_quantity - {jumlah_kurang}"}
                    )

                st.success("✅ Berhasil dicatat! Stok berikut telah dikurangi:")
                df_potong = pd.DataFrame([
                    {"Bahan / Packaging": k, "Jumlah Dikurangi": v, "Satuan": k.split("(")[-1].rstrip(")") if "(" in k else ""}
                    for k, v in stok_dipotong.items()
                ])
                st.dataframe(df_potong, use_container_width=True)
                st.caption("⚡ Data dikirim ke database Supabase Inventory secara real-time.")

    # ── Tab 2: Riwayat ───────────────────────────────────────────
    with tab2:
        if st.session_state.log_transaksi_manual:
            logs_display = [
                {
                    "Waktu": l["waktu"],
                    "Barista": l["barista"],
                    "Tujuan": l["tujuan"],
                    "Menu": l["menu"],
                    "Jumlah": l["jumlah"],
                    "Tipe": l["change_type"],
                    "Cabang": l["cabang"],
                    "Catatan": l["catatan"]
                }
                for l in st.session_state.log_transaksi_manual
            ]
            st.dataframe(pd.DataFrame(logs_display), use_container_width=True)
        else:
            st.info("Belum ada pencatatan manual hari ini.")

    # ── Tab 3: Simulasi Sync POS ─────────────────────────────────
    with tab3:
        st.subheader("🔄 Simulasi Sinkronisasi Otomatis dari POS")
        st.caption(
            "Fitur ini mensimulasikan bagaimana sistem membaca transaksi dari POS "
            "dan otomatis memotong stok inventory sesuai resep standar."
        )

        # Ambil transaksi POS dummy / dari Supabase POS
        pos_dummy = {
            "transaction_id": "TRX-2025-001",
            "timestamp": datetime.now().isoformat(),
            "cabang": st.session_state.cabang,
            "items": [
                {"name": "Americano Ice", "quantity": 2},
                {"name": "Kentang Goreng", "quantity": 1},
                {"name": "Kopi Susu Gula Aren", "quantity": 1},
            ]
        }

        st.json(pos_dummy)

        if st.button("▶️ Jalankan Sync (Dry Run  tidak tulis ke DB)", use_container_width=True):
            hasil = sync_pos_to_inventory(pos_dummy, st.session_state.cabang, dry_run=True)
            st.session_state.pos_sync_results = hasil
            st.session_state.last_pos_sync = datetime.now().strftime("%H:%M:%S")

        if st.session_state.pos_sync_results:
            st.success(f"✅ Sync berhasil pada {st.session_state.last_pos_sync}")
            for menu, cuts in st.session_state.pos_sync_results.items():
                with st.expander(f"📌 {menu}"):
                    df_cut = pd.DataFrame([
                        {"Bahan / Packaging": k, "Dikurangi": v}
                        for k, v in cuts.items()
                    ])
                    st.dataframe(df_cut, use_container_width=True)


# ==========================================
# 12. HALAMAN MANAGER – Dashboard Lengkap
# ==========================================

def halaman_manager():
    st.header(f"📊 Dashboard Manager  Cabang {st.session_state.cabang}")

    # Parameter prediksi (bisa diatur oleh Manager)
    with st.expander("⚙️ Pengaturan Parameter Prediksi"):
        col_p1, col_p2, col_p3 = st.columns(3)
        lead_time = col_p1.number_input("Lead Time Supplier (hari)", min_value=1, max_value=14, value=2)
        safety_days = col_p2.number_input("Safety Stock (hari pemakaian)", min_value=1, max_value=14, value=3)
        fefo_days = col_p3.number_input("Peringatan Kadaluwarsa (hari ke depan)", min_value=1, max_value=30, value=7)

    # Load data
    data_inv = load_inventory(st.session_state.cabang)
    df_logs = load_logs(st.session_state.cabang)

    # Hitung prediksi dengan engine ROP
    data_inv = calculate_inventory_prediction(data_inv, df_logs, lead_time, safety_days)

    # ── KPI Cards ────────────────────────────────────────────────
    total_item = len(data_inv)
    habis = (data_inv["Status"] == "🚫 Habis!").sum()
    restock_segera = (data_inv["Status"] == "🚨 Restock!").sum()
    perhatian = data_inv["Status"].isin(["⚠️ Segera Restock", "🟡 Perhatian"]).sum()
    aman = (data_inv["Status"] == "✅ Aman").sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Item", total_item)
    c2.metric("✅ Aman", aman)
    c3.metric("🟡 Perhatian", perhatian)
    c4.metric("🚨 Restock Segera", restock_segera)
    c5.metric("🚫 Habis", habis)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Tabel Stok & Prediksi",
        "⚠️ Peringatan Restock",
        "🏷️ FEFO – Kadaluwarsa",
        "📈 Grafik & Analitik",
        "📥 Export Laporan"
    ])

    # ── Tab 1: Tabel ──────────────────────────────────────────────
    with tab1:
        st.subheader("Status Inventory & Prediksi Restock (ROP)")

        kategori_filter = st.multiselect(
            "Filter Kategori:",
            options=data_inv["Kategori"].unique().tolist(),
            default=data_inv["Kategori"].unique().tolist()
        )
        df_filtered = data_inv[data_inv["Kategori"].isin(kategori_filter)]

        def color_status(val):
            if "Habis" in str(val):   return "background-color:#ff4d4d;color:white"
            if "Restock!" in str(val): return "background-color:#ffcccc"
            if "Segera" in str(val):   return "background-color:#ffe0b2"
            if "Perhatian" in str(val):return "background-color:#fff9c4"
            return "background-color:#ccffcc"

        cols_show = [
            "Item", "Merk", "Kategori", "Sisa Stok", "Satuan",
            "Batas Aman", "ROP", "ADU (per hari)",
            "Estimasi Habis (Hari)", "Prediksi Habis", "Tanggal Restock",
            "Status", "Tanggal Kadaluwarsa", "Harga Beli (Rp)"
        ]
        cols_show = [c for c in cols_show if c in df_filtered.columns]
        styled = df_filtered[cols_show].style.applymap(color_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True)

        st.caption(
            f"**ROP** (Reorder Point) = ADU × (Lead Time {lead_time} hari + Safety Stock {safety_days} hari). "
            "Jika Sisa Stok < ROP, sistem menandai item perlu restock."
        )

    # ── Tab 2: Peringatan Restock ─────────────────────────────────
    with tab2:
        st.subheader("🚨 Peringatan Stok Kritis")

        for status_label, fn_color in [
            ("🚫 Habis!", st.error),
            ("🚨 Restock!", st.error),
            ("⚠️ Segera Restock", st.warning),
            ("🟡 Perhatian", st.warning),
        ]:
            subset = data_inv[data_inv["Status"] == status_label]
            if not subset.empty:
                fn_color(f"**{len(subset)} item** dengan status '{status_label}':")
                for _, row in subset.iterrows():
                    fn_color(
                        f"{status_label} **{row['Item']}**  "
                        f"Sisa: {row['Sisa Stok']} {row['Satuan']} | "
                        f"ROP: {row['ROP']} | ADU: {row['ADU (per hari)']}/hari | "
                        f"Habis: {row['Prediksi Habis']} | Restock: {row['Tanggal Restock']}"
                    )

        if restock_segera == 0 and habis == 0:
            st.success("✅ Semua item dalam kondisi aman!")

    # ── Tab 3: FEFO ───────────────────────────────────────────────
    with tab3:
        st.subheader(f"🏷️ FEFO  Item Kadaluwarsa dalam {fefo_days} Hari ke Depan")
        st.caption("First Expired First Out: prioritaskan penggunaan bahan yang lebih cepat kedaluwarsa.")

        fefo_alerts = check_fefo_alerts(data_inv, fefo_days)
        if not fefo_alerts.empty:
            for _, row in fefo_alerts.iterrows():
                exp_date = row["Tanggal Kadaluwarsa"]
                days_left = (pd.to_datetime(exp_date) - datetime.now()).days
                if days_left <= 0:
                    st.error(f"🔴 **{row['Item']}**  SUDAH KADALUWARSA ({exp_date})")
                elif days_left <= 3:
                    st.error(f"🟠 **{row['Item']}**  Kadaluwarsa {days_left} hari lagi ({exp_date})")
                else:
                    st.warning(f"🟡 **{row['Item']}**  Kadaluwarsa {days_left} hari lagi ({exp_date})")
        else:
            st.success(f"✅ Tidak ada item yang akan kadaluwarsa dalam {fefo_days} hari ke depan.")

    # ── Tab 4: Grafik ─────────────────────────────────────────────
    with tab4:
        st.subheader("📊 Visualisasi Stok vs. Batas Aman & ROP")

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Sisa Stok", x=data_inv["Item"], y=data_inv["Sisa Stok"], marker_color="steelblue"))
        fig_bar.add_trace(go.Bar(name="Batas Aman", x=data_inv["Item"], y=data_inv["Batas Aman"], marker_color="salmon"))
        if "ROP" in data_inv.columns:
            fig_bar.add_trace(go.Scatter(
                name="ROP", x=data_inv["Item"], y=data_inv["ROP"],
                mode="markers+lines", marker=dict(color="darkorange", size=8, symbol="diamond")
            ))
        fig_bar.update_layout(
            barmode="group", xaxis_tickangle=-45,
            title="Perbandingan Sisa Stok vs. Batas Aman vs. ROP",
            height=500, legend=dict(orientation="h")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_pie = px.pie(data_inv, names="Kategori", values="Sisa Stok",
                             title="Distribusi Stok: Bahan Baku vs Packaging")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            # Estimasi nilai stok tersisa
            data_inv["Nilai Sisa (Rp)"] = data_inv["Sisa Stok"] * data_inv["Harga Beli (Rp)"].fillna(0)
            top_nilai = data_inv.nlargest(8, "Nilai Sisa (Rp)")
            fig_nilai = px.bar(top_nilai, x="Item", y="Nilai Sisa (Rp)",
                               color="Kategori", title="Top 8 Item Berdasarkan Nilai Stok")
            fig_nilai.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig_nilai, use_container_width=True)

        # Tren ADU (dari log)
        if not df_logs.empty and "ingredient_name" in df_logs.columns:
            df_logs["created_at"] = pd.to_datetime(df_logs["created_at"], errors="coerce")
            df_logs["Tanggal"] = df_logs["created_at"].dt.date
            df_tren = df_logs[df_logs["quantity_changed"] < 0].copy()
            df_tren["quantity_changed"] = df_tren["quantity_changed"].abs()
            df_tren_agg = df_tren.groupby(["Tanggal", "ingredient_name"])["quantity_changed"].sum().reset_index()
            df_tren_agg.columns = ["Tanggal", "Bahan", "Penggunaan"]

            top_items = df_tren_agg.groupby("Bahan")["Penggunaan"].sum().nlargest(5).index.tolist()
            df_tren_top = df_tren_agg[df_tren_agg["Bahan"].isin(top_items)]
            fig_tren = px.line(df_tren_top, x="Tanggal", y="Penggunaan", color="Bahan",
                               title="Tren Penggunaan Harian – Top 5 Bahan (7 Hari Terakhir)",
                               markers=True)
            st.plotly_chart(fig_tren, use_container_width=True)

    # ── Tab 5: Export ─────────────────────────────────────────────
    with tab5:
        st.subheader("📥 Export Laporan Inventaris")
        col_a, col_b = st.columns(2)
        with col_a:
            tgl_mulai = st.date_input("Dari Tanggal", value=datetime.now().date() - timedelta(days=30))
        with col_b:
            tgl_akhir = st.date_input("Sampai Tanggal", value=datetime.now().date())

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Sheet 1: Inventory + Prediksi
            cols_export = [c for c in [
                "Item", "Merk", "Kategori", "Sisa Stok", "Satuan", "Batas Aman",
                "ROP", "ADU (per hari)", "Estimasi Habis (Hari)",
                "Prediksi Habis", "Tanggal Restock", "Status",
                "Tanggal Kadaluwarsa", "Harga Beli (Rp)", "Nilai Sisa (Rp)", "Cabang"
            ] if c in data_inv.columns]
            data_inv[cols_export].to_excel(writer, index=False, sheet_name="Inventory & Prediksi")

            # Sheet 2: Resep Standar
            resep_rows = []
            for menu, detail in RESEP_STANDAR.items():
                for bahan, takaran in detail.get("bahan", {}).items():
                    resep_rows.append({"Menu": menu, "Kategori Menu": detail.get("kategori", ""),
                                       "Bahan/Packaging": bahan, "Jenis": "Bahan", "Takaran": takaran})
                for pkg, qty in detail.get("packaging", {}).items():
                    resep_rows.append({"Menu": menu, "Kategori Menu": detail.get("kategori", ""),
                                       "Bahan/Packaging": pkg, "Jenis": "Packaging", "Takaran": qty})
            pd.DataFrame(resep_rows).to_excel(writer, index=False, sheet_name="Resep Standar")

            # Sheet 3: Log Penggunaan (dalam rentang tanggal)
            if not df_logs.empty:
                df_logs["created_at"] = pd.to_datetime(df_logs["created_at"], errors="coerce")
                df_range = df_logs[
                    (df_logs["created_at"].dt.date >= tgl_mulai) &
                    (df_logs["created_at"].dt.date <= tgl_akhir)
                ]
                df_range.to_excel(writer, index=False, sheet_name="Log Penggunaan")

        st.download_button(
            label="📥 Download Laporan Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"Laporan_Inventory_{st.session_state.cabang}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ==========================================
# 13. HALAMAN OWNER CABANG
# ==========================================

def halaman_owner_cabang():
    cabang = st.session_state.cabang
    st.header(f"Executive Dashboard  Cabang {cabang}")

    data_inv = load_inventory(cabang)
    df_logs = load_logs(cabang)
    data_inv = calculate_inventory_prediction(data_inv, df_logs)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Item Dipantau", len(data_inv))
    col2.metric("✅ Stok Aman", (data_inv["Status"] == "✅ Aman").sum())
    col3.metric("⚠️ Perhatian", data_inv["Status"].isin(["⚠️ Segera Restock", "🟡 Perhatian"]).sum())
    col4.metric("🚨 Perlu Restock", data_inv["Status"].isin(["🚨 Restock!", "🚫 Habis!"]).sum())

    st.markdown("---")

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Sisa Stok", x=data_inv["Item"], y=data_inv["Sisa Stok"], marker_color="steelblue"))
    fig.add_trace(go.Bar(name="Batas Aman", x=data_inv["Item"], y=data_inv["Batas Aman"], marker_color="salmon"))
    fig.update_layout(barmode="group", xaxis_tickangle=-45, title=f"Status Stok  Cabang {cabang}", height=450)
    st.plotly_chart(fig, use_container_width=True)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_cat = px.pie(data_inv, names="Kategori", values="Sisa Stok",
                         title="Komposisi Stok: Bahan Baku vs Packaging")
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_g2:
        status_count = data_inv["Status"].value_counts().reset_index()
        status_count.columns = ["Status", "Jumlah Item"]
        fig_status = px.bar(status_count, x="Status", y="Jumlah Item",
                            color="Status", title="Distribusi Status Stok")
        st.plotly_chart(fig_status, use_container_width=True)

    st.subheader("Tabel Ringkasan Stok")
    cols_o = [c for c in ["Item", "Kategori", "Sisa Stok", "Satuan", "Batas Aman",
                           "Estimasi Habis (Hari)", "Prediksi Habis", "Status"] if c in data_inv.columns]
    st.dataframe(data_inv[cols_o], use_container_width=True)


# ==========================================
# 14. HALAMAN OWNER PUSAT – Multi-Cabang + Drill Down
# ==========================================

def halaman_owner_pusat():
    st.header("Executive Dashboard  Owner Pusat")
    st.write("Pantau seluruh cabang kafe PT. Sari Tropis Indonesia dari satu layar.")

    cabang_pilihan = st.selectbox("🔍 Drill Down  Pilih Cabang:", ["Semua Cabang", "Buper", "WKA"])

    df_buper = load_inventory("Buper")
    df_wka = load_inventory("WKA")
    df_logs_buper = load_logs("Buper")
    df_logs_wka = load_logs("WKA")

    df_buper = calculate_inventory_prediction(df_buper, df_logs_buper)
    df_wka = calculate_inventory_prediction(df_wka, df_logs_wka)
    df_all = pd.concat([df_buper, df_wka], ignore_index=True)

    df_view = df_all if cabang_pilihan == "Semua Cabang" else df_all[df_all["Cabang"] == cabang_pilihan]
    label = cabang_pilihan

    # KPI Multi-Cabang
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cabang Aktif", 2 if cabang_pilihan == "Semua Cabang" else 1)
    c2.metric("Total Item", len(df_view))
    c3.metric("✅ Aman", (df_view["Status"] == "✅ Aman").sum())
    c4.metric("🚨 Restock", df_view["Status"].isin(["🚨 Restock!", "🚫 Habis!"]).sum())
    c5.metric("⚠️ Perhatian", df_view["Status"].isin(["⚠️ Segera Restock", "🟡 Perhatian"]).sum())

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 Grafik Perbandingan", "📋 Detail Stok", "📈 Analitik Nilai"])

    with tab1:
        # SQL equivalent: SELECT name, SUM(stock_quantity) FROM ingredients GROUP BY name, branch
        df_agg = df_view.groupby(["Cabang", "Kategori"])["Sisa Stok"].sum().reset_index()
        fig1 = px.bar(df_agg, x="Kategori", y="Sisa Stok", color="Cabang",
                      barmode="group", title=f"Perbandingan Sisa Stok  {label}")
        st.plotly_chart(fig1, use_container_width=True)

        # Status distribution per cabang
        df_status = df_view.groupby(["Cabang", "Status"]).size().reset_index(name="Jumlah")
        fig_s = px.bar(df_status, x="Status", y="Jumlah", color="Cabang",
                       barmode="group", title="Distribusi Status Stok per Cabang")
        st.plotly_chart(fig_s, use_container_width=True)

    with tab2:
        st.subheader(f"Detail Stok  {label}")
        cols_detail = [c for c in [
            "Cabang", "Item", "Kategori", "Sisa Stok", "Satuan",
            "Batas Aman", "ROP", "Estimasi Habis (Hari)", "Prediksi Habis", "Status"
        ] if c in df_view.columns]
        st.dataframe(df_view[cols_detail], use_container_width=True)

        # Alert kritis lintas cabang
        kritis = df_view[df_view["Status"].isin(["🚨 Restock!", "🚫 Habis!"])]
        if not kritis.empty:
            st.error(f"⚠️ **{len(kritis)} item** membutuhkan perhatian di {label}:")
            for _, row in kritis.iterrows():
                st.error(
                    f"🔴 [{row['Cabang']}] **{row['Item']}**  "
                    f"Sisa: {row['Sisa Stok']} {row['Satuan']} | {row['Status']}"
                )

    with tab3:
        # Estimasi nilai stok: Harga Beli × Sisa Stok
        df_view2 = df_view.copy()
        df_view2["Nilai Stok (Rp)"] = df_view2["Sisa Stok"] * df_view2["Harga Beli (Rp)"].fillna(0)
        df_nilai = df_view2.groupby(["Cabang", "Kategori"])["Nilai Stok (Rp)"].sum().reset_index()
        fig_nilai = px.bar(df_nilai, x="Kategori", y="Nilai Stok (Rp)", color="Cabang",
                           barmode="group", title=f"Estimasi Nilai Stok (Rp)  {label}")
        st.plotly_chart(fig_nilai, use_container_width=True)

        # ROP comparison per cabang
        if "ROP" in df_view.columns:
            rop_compare = df_view.groupby(["Cabang"])[["Sisa Stok", "ROP", "Batas Aman"]].mean().reset_index()
            fig_rop = px.bar(rop_compare.melt(id_vars="Cabang"),
                             x="Cabang", y="value", color="variable", barmode="group",
                             title="Rata-rata Stok vs ROP vs Batas Aman per Cabang")
            st.plotly_chart(fig_rop, use_container_width=True)


# ==========================================
# 15. SIDEBAR
# ==========================================

def tampilkan_sidebar():
    with st.sidebar:
        st.title("☕ Menu Utama")
        st.write(f"👤 **{st.session_state.role}**")
        st.write(f"📍 Cabang: **{st.session_state.cabang}**")
        st.write(f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}")
        st.markdown("---")

        # Feed transaksi POS real-time (dummy)
        st.subheader("🔔 Transaksi POS Terbaru")
        transaksi_pos_dummy = [
            {"waktu": "10:32", "item": "Kopi Susu Gula Aren", "qty": 2, "cabang": "Buper"},
            {"waktu": "10:45", "item": "Kentang Goreng",       "qty": 1, "cabang": "WKA"},
            {"waktu": "11:01", "item": "Americano Ice",        "qty": 1, "cabang": "Buper"},
            {"waktu": "11:15", "item": "Greentea Latte",       "qty": 2, "cabang": "WKA"},
        ]
        for t in transaksi_pos_dummy:
            if st.session_state.cabang in ("Semua", t["cabang"]):
                stok_info = get_pemotongan_stok(t["item"], t["qty"])
                bahan_list = ", ".join([f"{k}: -{v}" for k, v in list(stok_info.items())[:2]])
                st.caption(
                    f"⏱ **{t['waktu']}**  {t['item']} ×{t['qty']} [{t['cabang']}]\n"
                    f"↳ _{bahan_list}_"
                )

        st.markdown("---")
        st.caption("📡 Terhubung ke Supabase POS & Inventory")
        st.markdown("---")
        st.button("🚪 Logout", on_click=logout, use_container_width=True)


# ==========================================
# 16. MAIN ROUTING
# ==========================================

def main():
    if not st.session_state.logged_in:
        login()
    else:
        tampilkan_sidebar()
        role = st.session_state.role

        if role == "Kasir":
            halaman_kasir()
        elif role == "Manager":
            halaman_manager()
        elif role == "Owner Cabang":
            halaman_owner_cabang()
        elif role == "Owner Pusat":
            halaman_owner_pusat()
        else:
            st.error("Role tidak dikenali. Silakan logout dan login ulang.")


if __name__ == "__main__":
    main()

