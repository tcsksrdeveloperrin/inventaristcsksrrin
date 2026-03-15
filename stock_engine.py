"""
stock_engine.py
================
Mesin pelacak stok real-time berbasis inferensi statistik.

Cara kerja tanpa resep eksplisit:
  1. Setiap transaksi POS masuk → product_id di-lookup ke tabel
     product_ingredient_groups → bahan baku yang terlibat dicatat
     di inventory_usage_log sebagai "estimasi keluar".
  2. Koefisien pemakaian (gram/ml per cup) dihitung dari:
       konsumsi_aktual (dari opname) ÷ qty_terjual
  3. Reorder alert = stok_estimasi < (avg_harian × lead_time) + safety_stock

Tiga tabel baru di Supabase inventaris (TIDAK menyentuh DB POS):
  - product_ingredient_groups  : mapping produk POS → bahan baku
  - stock_opname               : stok fisik mingguan
  - reorder_config             : lead time & safety stock per bahan
  - inventory_usage_log        : log pemakaian otomatis (generated)
"""

from __future__ import annotations
import json
import re
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st


# ─── SQL untuk buat tabel di Supabase ────────────────────────────────────────
SUPABASE_DDL = """
-- Jalankan sekali di SQL Editor Supabase inventaris kamu

-- 1. Mapping: produk POS → kelompok bahan baku inventaris
CREATE TABLE IF NOT EXISTS product_ingredient_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      TEXT NOT NULL,       -- UUID dari products_wka / products_buper
    product_name    TEXT NOT NULL,
    branch          TEXT NOT NULL,       -- 'WKA' | 'BUPER'
    bahan_baku      TEXT NOT NULL,       -- nama bahan di tabel transaksi inventaris
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pig_product ON product_ingredient_groups(product_id, branch);

-- 2. Stok opname mingguan
CREATE TABLE IF NOT EXISTS stock_opname (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cabang          TEXT NOT NULL,
    nama_barang     TEXT NOT NULL,
    stok_fisik      FLOAT NOT NULL,
    satuan          TEXT NOT NULL,
    tanggal         DATE NOT NULL,
    pencatat        TEXT,
    catatan         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_opname_cabang_tgl ON stock_opname(cabang, tanggal DESC);

-- 3. Konfigurasi reorder per bahan
CREATE TABLE IF NOT EXISTS reorder_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nama_barang     TEXT NOT NULL,
    cabang          TEXT NOT NULL,
    lead_time_hari  INT DEFAULT 2,
    safety_stock    FLOAT DEFAULT 0,
    satuan          TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(nama_barang, cabang)
);

-- 4. Log pemakaian otomatis dari sinkronisasi POS
CREATE TABLE IF NOT EXISTS inventory_usage_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cabang          TEXT NOT NULL,
    transaction_id  TEXT NOT NULL,       -- id dari tabel transactions POS
    product_id      TEXT NOT NULL,
    product_name    TEXT,
    bahan_baku      TEXT NOT NULL,
    qty_terjual     INT NOT NULL,
    estimasi_pakai  FLOAT,               -- qty bahan terpakai (dari koefisien)
    satuan          TEXT,
    tanggal         DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(transaction_id, product_id, bahan_baku)   -- idempoten
);
CREATE INDEX IF NOT EXISTS idx_usage_cabang_tgl ON inventory_usage_log(cabang, tanggal DESC);
"""

# ─── Mapping awal (seed) dari analisis CSV transaksi POS ─────────────────────
# Ini adalah hasil klasifikasi otomatis berdasarkan nama produk + coffee_type.
# Manager bisa edit/tambah via UI nanti.

INITIAL_MAPPING: list[dict] = [
    # ── WKA ──────────────────────────────────────────────────────────────────
    {"product_id": "f2747fa1-00bf-49d3-a43d-30b95c95bda7", "product_name": "Kopi susu gula aren",  "branch": "WKA",   "bahan_baku": "Susu Full Cream"},
    {"product_id": "f2747fa1-00bf-49d3-a43d-30b95c95bda7", "product_name": "Kopi susu gula aren",  "branch": "WKA",   "bahan_baku": "Beans Natural"},
    {"product_id": "f2747fa1-00bf-49d3-a43d-30b95c95bda7", "product_name": "Kopi susu gula aren",  "branch": "WKA",   "bahan_baku": "Gula Aren / Aren Liquid"},
    {"product_id": "f2747fa1-00bf-49d3-a43d-30b95c95bda7", "product_name": "Kopi susu gula aren",  "branch": "WKA",   "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "f2747fa1-00bf-49d3-a43d-30b95c95bda7", "product_name": "Kopi susu gula aren",  "branch": "WKA",   "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "dd54b05c-17f5-458e-b63d-5bb1bb5df37d", "product_name": "Greentea latte",       "branch": "WKA",   "bahan_baku": "Susu UHT Full Cream"},
    {"product_id": "dd54b05c-17f5-458e-b63d-5bb1bb5df37d", "product_name": "Greentea latte",       "branch": "WKA",   "bahan_baku": "Powder Greentea / Matcha"},
    {"product_id": "dd54b05c-17f5-458e-b63d-5bb1bb5df37d", "product_name": "Greentea latte",       "branch": "WKA",   "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "dd54b05c-17f5-458e-b63d-5bb1bb5df37d", "product_name": "Greentea latte",       "branch": "WKA",   "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "c22b1e9a-6344-43a0-9564-5f6a893cac55", "product_name": "Coffee latte",         "branch": "WKA",   "bahan_baku": "Susu Full Cream"},
    {"product_id": "c22b1e9a-6344-43a0-9564-5f6a893cac55", "product_name": "Coffee latte",         "branch": "WKA",   "bahan_baku": "Beans Natural"},
    {"product_id": "c22b1e9a-6344-43a0-9564-5f6a893cac55", "product_name": "Coffee latte",         "branch": "WKA",   "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "c22b1e9a-6344-43a0-9564-5f6a893cac55", "product_name": "Coffee latte",         "branch": "WKA",   "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "81e594e1-be20-4d5a-ae62-9a211f9e65f5", "product_name": "Chocolate latte",      "branch": "WKA",   "bahan_baku": "Susu Full Cream"},
    {"product_id": "81e594e1-be20-4d5a-ae62-9a211f9e65f5", "product_name": "Chocolate latte",      "branch": "WKA",   "bahan_baku": "Powder Chocolate / Coklat Bubuk"},
    {"product_id": "81e594e1-be20-4d5a-ae62-9a211f9e65f5", "product_name": "Chocolate latte",      "branch": "WKA",   "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "81e594e1-be20-4d5a-ae62-9a211f9e65f5", "product_name": "Chocolate latte",      "branch": "WKA",   "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "41ac262f-3909-4bb2-8bd8-54b2121c38d3", "product_name": "Kentang",              "branch": "WKA",   "bahan_baku": "Kentang"},
    {"product_id": "41ac262f-3909-4bb2-8bd8-54b2121c38d3", "product_name": "Kentang",              "branch": "WKA",   "bahan_baku": "Minyak Goreng"},
    {"product_id": "41ac262f-3909-4bb2-8bd8-54b2121c38d3", "product_name": "Kentang",              "branch": "WKA",   "bahan_baku": "Box Snack Kertas Kecil"},
    {"product_id": "2c6a249f-8c06-49b3-b3c2-1e8d9fd10522", "product_name": "Pempek original",     "branch": "WKA",   "bahan_baku": "Pempek Original"},
    {"product_id": "2c6a249f-8c06-49b3-b3c2-1e8d9fd10522", "product_name": "Pempek original",     "branch": "WKA",   "bahan_baku": "Cuko Pempek"},
    {"product_id": "2c6a249f-8c06-49b3-b3c2-1e8d9fd10522", "product_name": "Pempek original",     "branch": "WKA",   "bahan_baku": "Tray Plastik PP (untuk Pempek)"},
    # ── BUPER ─────────────────────────────────────────────────────────────────
    {"product_id": "f3f2c5c9-3617-42d6-94da-4ecbed9e737f", "product_name": "Kopi Susu Gula aren",  "branch": "BUPER", "bahan_baku": "Susu Full Cream"},
    {"product_id": "f3f2c5c9-3617-42d6-94da-4ecbed9e737f", "product_name": "Kopi Susu Gula aren",  "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "f3f2c5c9-3617-42d6-94da-4ecbed9e737f", "product_name": "Kopi Susu Gula aren",  "branch": "BUPER", "bahan_baku": "Gula Aren / Aren Liquid"},
    {"product_id": "f3f2c5c9-3617-42d6-94da-4ecbed9e737f", "product_name": "Kopi Susu Gula aren",  "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "f3f2c5c9-3617-42d6-94da-4ecbed9e737f", "product_name": "Kopi Susu Gula aren",  "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "0b85892b-9e6c-41f1-8eee-c9851b7c6977", "product_name": "Es Teh Manis",         "branch": "BUPER", "bahan_baku": "Teh Celup / Teh Bubuk"},
    {"product_id": "0b85892b-9e6c-41f1-8eee-c9851b7c6977", "product_name": "Es Teh Manis",         "branch": "BUPER", "bahan_baku": "Simple Syrup (Gula Cair)"},
    {"product_id": "0b85892b-9e6c-41f1-8eee-c9851b7c6977", "product_name": "Es Teh Manis",         "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "0b85892b-9e6c-41f1-8eee-c9851b7c6977", "product_name": "Es Teh Manis",         "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "3df9c553-162c-464b-a3dc-e564e2aa6569", "product_name": "Caramel machiato",     "branch": "BUPER", "bahan_baku": "Susu Full Cream"},
    {"product_id": "3df9c553-162c-464b-a3dc-e564e2aa6569", "product_name": "Caramel machiato",     "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "3df9c553-162c-464b-a3dc-e564e2aa6569", "product_name": "Caramel machiato",     "branch": "BUPER", "bahan_baku": "Syrup Hazelnut"},
    {"product_id": "3df9c553-162c-464b-a3dc-e564e2aa6569", "product_name": "Caramel machiato",     "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "3df9c553-162c-464b-a3dc-e564e2aa6569", "product_name": "Caramel machiato",     "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "bc2c32ce-f413-4dcc-a402-7c76dfd73df6", "product_name": "Macha Lattee",         "branch": "BUPER", "bahan_baku": "Powder Greentea / Matcha"},
    {"product_id": "bc2c32ce-f413-4dcc-a402-7c76dfd73df6", "product_name": "Macha Lattee",         "branch": "BUPER", "bahan_baku": "Susu UHT Full Cream"},
    {"product_id": "bc2c32ce-f413-4dcc-a402-7c76dfd73df6", "product_name": "Macha Lattee",         "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "bc2c32ce-f413-4dcc-a402-7c76dfd73df6", "product_name": "Macha Lattee",         "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "30a8e9ea-66e2-47b7-9417-c1be92235067", "product_name": "Nasi Goreng",          "branch": "BUPER", "bahan_baku": "Beras (Nasi Putih)"},
    {"product_id": "30a8e9ea-66e2-47b7-9417-c1be92235067", "product_name": "Nasi Goreng",          "branch": "BUPER", "bahan_baku": "Minyak Goreng"},
    {"product_id": "30a8e9ea-66e2-47b7-9417-c1be92235067", "product_name": "Nasi Goreng",          "branch": "BUPER", "bahan_baku": "Nasi Box / Rice Box Kertas"},
    {"product_id": "30a8e9ea-66e2-47b7-9417-c1be92235067", "product_name": "Nasi Goreng",          "branch": "BUPER", "bahan_baku": "Sendok Plastik Takeaway"},
    {"product_id": "4ee93bf0-0d35-40a0-879e-a07916ee6fd8", "product_name": "Nasi Telor Kecap",     "branch": "BUPER", "bahan_baku": "Beras (Nasi Putih)"},
    {"product_id": "4ee93bf0-0d35-40a0-879e-a07916ee6fd8", "product_name": "Nasi Telor Kecap",     "branch": "BUPER", "bahan_baku": "Telur Ayam"},
    {"product_id": "4ee93bf0-0d35-40a0-879e-a07916ee6fd8", "product_name": "Nasi Telor Kecap",     "branch": "BUPER", "bahan_baku": "Nasi Box / Rice Box Kertas"},
    {"product_id": "4ee93bf0-0d35-40a0-879e-a07916ee6fd8", "product_name": "Nasi Telor Kecap",     "branch": "BUPER", "bahan_baku": "Sendok Plastik Takeaway"},
    {"product_id": "6988907f-2939-40dd-a55c-bb7461597512", "product_name": "Kentang goreng",       "branch": "BUPER", "bahan_baku": "Kentang"},
    {"product_id": "6988907f-2939-40dd-a55c-bb7461597512", "product_name": "Kentang goreng",       "branch": "BUPER", "bahan_baku": "Minyak Goreng"},
    {"product_id": "6988907f-2939-40dd-a55c-bb7461597512", "product_name": "Kentang goreng",       "branch": "BUPER", "bahan_baku": "Box Snack Kertas Kecil"},
    {"product_id": "843798c4-9991-4576-8c3d-5cd3187fb6ce", "product_name": "Kentang Sosis",        "branch": "BUPER", "bahan_baku": "Kentang"},
    {"product_id": "843798c4-9991-4576-8c3d-5cd3187fb6ce", "product_name": "Kentang Sosis",        "branch": "BUPER", "bahan_baku": "Sosis Ayam / Sosis Sapi"},
    {"product_id": "843798c4-9991-4576-8c3d-5cd3187fb6ce", "product_name": "Kentang Sosis",        "branch": "BUPER", "bahan_baku": "Minyak Goreng"},
    {"product_id": "843798c4-9991-4576-8c3d-5cd3187fb6ce", "product_name": "Kentang Sosis",        "branch": "BUPER", "bahan_baku": "Box Snack Kertas Kecil"},
    {"product_id": "398189f6-7529-4f9c-b8d1-17b746f2a62b", "product_name": "Kopi Susu Halzenut",   "branch": "BUPER", "bahan_baku": "Susu Full Cream"},
    {"product_id": "398189f6-7529-4f9c-b8d1-17b746f2a62b", "product_name": "Kopi Susu Halzenut",   "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "398189f6-7529-4f9c-b8d1-17b746f2a62b", "product_name": "Kopi Susu Halzenut",   "branch": "BUPER", "bahan_baku": "Syrup Hazelnut"},
    {"product_id": "398189f6-7529-4f9c-b8d1-17b746f2a62b", "product_name": "Kopi Susu Halzenut",   "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "398189f6-7529-4f9c-b8d1-17b746f2a62b", "product_name": "Kopi Susu Halzenut",   "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "4a3f94d1-cb25-4f35-867c-00c6743a9d55", "product_name": "Pisang Cokelat",       "branch": "BUPER", "bahan_baku": "Pisang Kepok / Cavendish"},
    {"product_id": "4a3f94d1-cb25-4f35-867c-00c6743a9d55", "product_name": "Pisang Cokelat",       "branch": "BUPER", "bahan_baku": "Pasta Cokelat / Dark Chocolate"},
    {"product_id": "4a3f94d1-cb25-4f35-867c-00c6743a9d55", "product_name": "Pisang Cokelat",       "branch": "BUPER", "bahan_baku": "Box Snack Kertas Kecil"},
    {"product_id": "b46aa96f-2240-4731-aee1-80da5413bb2c", "product_name": "Pisang Keju",          "branch": "BUPER", "bahan_baku": "Pisang Kepok / Cavendish"},
    {"product_id": "b46aa96f-2240-4731-aee1-80da5413bb2c", "product_name": "Pisang Keju",          "branch": "BUPER", "bahan_baku": "Keju Cheddar"},
    {"product_id": "b46aa96f-2240-4731-aee1-80da5413bb2c", "product_name": "Pisang Keju",          "branch": "BUPER", "bahan_baku": "Box Snack Kertas Kecil"},
    {"product_id": "3fad68d4-2180-4433-be90-337f77f2524e", "product_name": "Coklat Lattee",        "branch": "BUPER", "bahan_baku": "Powder Chocolate / Coklat Bubuk"},
    {"product_id": "3fad68d4-2180-4433-be90-337f77f2524e", "product_name": "Coklat Lattee",        "branch": "BUPER", "bahan_baku": "Susu Full Cream"},
    {"product_id": "3fad68d4-2180-4433-be90-337f77f2524e", "product_name": "Coklat Lattee",        "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "3fad68d4-2180-4433-be90-337f77f2524e", "product_name": "Coklat Lattee",        "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "08e51690-acdc-4cd5-8861-dc4d01bb6fc7", "product_name": "V60",                  "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "08e51690-acdc-4cd5-8861-dc4d01bb6fc7", "product_name": "V60",                  "branch": "BUPER", "bahan_baku": "Cup Paper 8oz Hot"},
    {"product_id": "0cdfea58-1d5e-4835-b935-e0c0e4e17a6c", "product_name": "Vietnam Drip",         "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "0cdfea58-1d5e-4835-b935-e0c0e4e17a6c", "product_name": "Vietnam Drip",         "branch": "BUPER", "bahan_baku": "Cup Paper 8oz Hot"},
    {"product_id": "b266d161-faca-41f4-a8ba-30c9321d7f5b", "product_name": "Red valvet lattee",    "branch": "BUPER", "bahan_baku": "Powder Red Velvet"},
    {"product_id": "b266d161-faca-41f4-a8ba-30c9321d7f5b", "product_name": "Red valvet lattee",    "branch": "BUPER", "bahan_baku": "Susu UHT Full Cream"},
    {"product_id": "b266d161-faca-41f4-a8ba-30c9321d7f5b", "product_name": "Red valvet lattee",    "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "b266d161-faca-41f4-a8ba-30c9321d7f5b", "product_name": "Red valvet lattee",    "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "bb71a975-dae1-4dec-a2a6-d7d7f7536667", "product_name": "Pempek Kapal Selam",   "branch": "BUPER", "bahan_baku": "Pempek Kapal Selam"},
    {"product_id": "bb71a975-dae1-4dec-a2a6-d7d7f7536667", "product_name": "Pempek Kapal Selam",   "branch": "BUPER", "bahan_baku": "Cuko Pempek"},
    {"product_id": "bb71a975-dae1-4dec-a2a6-d7d7f7536667", "product_name": "Pempek Kapal Selam",   "branch": "BUPER", "bahan_baku": "Tray Plastik PP (untuk Pempek)"},
    {"product_id": "03ee7f1c-8a69-4539-af55-f0095a296527", "product_name": "Coffee Lattee",        "branch": "BUPER", "bahan_baku": "Susu Full Cream"},
    {"product_id": "03ee7f1c-8a69-4539-af55-f0095a296527", "product_name": "Coffee Lattee",        "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "03ee7f1c-8a69-4539-af55-f0095a296527", "product_name": "Coffee Lattee",        "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "03ee7f1c-8a69-4539-af55-f0095a296527", "product_name": "Coffee Lattee",        "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
    {"product_id": "37403b7e-f6ed-462f-a396-df3f1fbb529f", "product_name": "Caramel Lattee",       "branch": "BUPER", "bahan_baku": "Susu Full Cream"},
    {"product_id": "37403b7e-f6ed-462f-a396-df3f1fbb529f", "product_name": "Caramel Lattee",       "branch": "BUPER", "bahan_baku": "Beans Natural"},
    {"product_id": "37403b7e-f6ed-462f-a396-df3f1fbb529f", "product_name": "Caramel Lattee",       "branch": "BUPER", "bahan_baku": "Syrup Hazelnut"},
    {"product_id": "37403b7e-f6ed-462f-a396-df3f1fbb529f", "product_name": "Caramel Lattee",       "branch": "BUPER", "bahan_baku": "Cold Cup Plastik 16oz"},
    {"product_id": "37403b7e-f6ed-462f-a396-df3f1fbb529f", "product_name": "Caramel Lattee",       "branch": "BUPER", "bahan_baku": "Sedotan Bening Standar"},
]


# ─── DB helpers ──────────────────────────────────────────────────────────────

POS_SUPABASE_URL = "https://wmtgotkjwmaxqxljcnrr.supabase.co"
POS_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGdvdGtqd21heHF4bGpjbnJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk5Mzc0NTEsImV4cCI6MjA3NTUxMzQ1MX0.vw_u2QroJXy3zCpAfQstgYYmlVMYocadfLmHIfg2uIs"


@st.cache_resource
def get_pos_client():
    """Koneksi read-only ke Supabase POS (project terpisah)."""
    try:
        from supabase import create_client
        return create_client(POS_SUPABASE_URL, POS_SUPABASE_KEY)
    except Exception as e:
        st.warning(f"Tidak dapat terhubung ke DB POS: {e}")
        return None


def fetch_pos_transactions(branch: str, since: datetime) -> pd.DataFrame:
    """
    Ambil transaksi baru dari DB POS sejak `since`.
    Return DataFrame dengan kolom: id, created_at, branch, items (JSON string).
    """
    pos = get_pos_client()
    if not pos:
        return pd.DataFrame()
    try:
        res = (pos.table("transactions")
               .select("id, created_at, branch, items")
               .eq("branch", branch)
               .gte("created_at", since.isoformat())
               .order("created_at", desc=False)
               .execute())
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Gagal ambil transaksi POS: {e}")
        return pd.DataFrame()


def get_mapping(supabase_inv, branch: str) -> dict[str, list[str]]:
    """
    Ambil mapping product_id → [bahan_baku] dari tabel product_ingredient_groups.
    Return: {product_id: [nama_bahan, ...]}
    """
    if not supabase_inv:
        # Fallback ke INITIAL_MAPPING
        mapping: dict[str, list[str]] = {}
        for row in INITIAL_MAPPING:
            if row["branch"] == branch:
                mapping.setdefault(row["product_id"], []).append(row["bahan_baku"])
        return mapping
    try:
        res = (supabase_inv.table("product_ingredient_groups")
               .select("product_id, bahan_baku")
               .eq("branch", branch)
               .eq("active", True)
               .execute())
        mapping: dict[str, list[str]] = {}
        for row in (res.data or []):
            mapping.setdefault(row["product_id"], []).append(row["bahan_baku"])
        # Jika kosong (belum di-seed), pakai INITIAL_MAPPING
        if not mapping:
            for row in INITIAL_MAPPING:
                if row["branch"] == branch:
                    mapping.setdefault(row["product_id"], []).append(row["bahan_baku"])
        return mapping
    except Exception as e:
        st.warning(f"Gagal ambil mapping: {e}. Menggunakan mapping bawaan.")
        mapping = {}
        for row in INITIAL_MAPPING:
            if row["branch"] == branch:
                mapping.setdefault(row["product_id"], []).append(row["bahan_baku"])
        return mapping


def get_last_sync_time(supabase_inv, branch: str) -> datetime:
    """Ambil waktu transaksi terakhir yang sudah di-sync."""
    if not supabase_inv:
        return datetime.now() - timedelta(days=7)
    try:
        res = (supabase_inv.table("inventory_usage_log")
               .select("created_at")
               .eq("cabang", branch)
               .order("created_at", desc=True)
               .limit(1)
               .execute())
        if res.data:
            ts = res.data[0]["created_at"]
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        pass
    return datetime.now() - timedelta(days=30)


def sync_pos_to_inventory(supabase_inv, branch: str) -> dict:
    """
    Core sync function:
    1. Ambil transaksi POS baru sejak last sync
    2. Untuk setiap item terjual, cari bahan baku yang terlibat via mapping
    3. Insert ke inventory_usage_log (idempoten — UNIQUE constraint)
    4. Return summary: {synced: N, skipped: N, bahan_terdampak: [...]}
    """
    last_sync = get_last_sync_time(supabase_inv, branch)
    df_pos = fetch_pos_transactions(branch, last_sync)

    if df_pos.empty:
        return {"synced": 0, "skipped": 0, "new_trx": 0, "bahan_terdampak": []}

    mapping = get_mapping(supabase_inv, branch)
    logs_to_insert = []
    bahan_terdampak = set()

    for _, trx in df_pos.iterrows():
        trx_id = trx["id"]
        trx_date = trx["created_at"][:10]  # YYYY-MM-DD
        items_raw = trx.get("items", "[]")

        # Parse items JSON (bisa string atau list)
        if isinstance(items_raw, str):
            try:
                items = json.loads(items_raw)
            except Exception:
                continue
        else:
            items = items_raw or []

        for item in items:
            pid      = item.get("id", "")
            pname    = item.get("name", "").strip()
            qty      = int(item.get("quantity", 1))
            bahan_list = mapping.get(pid, [])

            if not bahan_list:
                # Coba fuzzy fallback berdasarkan nama
                bahan_list = _infer_ingredients_by_name(pname, item.get("coffee_type"))

            for bahan in bahan_list:
                logs_to_insert.append({
                    "cabang":          branch,
                    "transaction_id":  trx_id,
                    "product_id":      pid,
                    "product_name":    pname,
                    "bahan_baku":      bahan,
                    "qty_terjual":     qty,
                    "estimasi_pakai":  None,  # diisi setelah koefisien dihitung
                    "satuan":          None,
                    "tanggal":         trx_date,
                })
                bahan_terdampak.add(bahan)

    synced = skipped = 0
    if logs_to_insert and supabase_inv:
        try:
            # upsert dengan on_conflict untuk idempoten
            res = (supabase_inv.table("inventory_usage_log")
                   .upsert(logs_to_insert,
                           on_conflict="transaction_id,product_id,bahan_baku")
                   .execute())
            synced = len(logs_to_insert)
        except Exception as e:
            st.error(f"Gagal insert usage log: {e}")
            skipped = len(logs_to_insert)
    elif logs_to_insert:
        # Mode lokal — simpan di session_state
        existing = st.session_state.get("usage_log_local", [])
        existing_keys = {(r["transaction_id"], r["product_id"], r["bahan_baku"])
                         for r in existing}
        new_rows = [r for r in logs_to_insert
                    if (r["transaction_id"], r["product_id"], r["bahan_baku"])
                    not in existing_keys]
        existing.extend(new_rows)
        st.session_state["usage_log_local"] = existing
        synced = len(new_rows)
        skipped = len(logs_to_insert) - synced

    return {
        "synced": synced,
        "skipped": skipped,
        "new_trx": len(df_pos),
        "bahan_terdampak": sorted(bahan_terdampak),
    }


def _infer_ingredients_by_name(name: str, coffee_type: Optional[str] = None) -> list[str]:
    """
    Fallback: infer bahan baku dari nama produk untuk produk yang belum
    ada di mapping (produk baru ditambah ke POS setelah mapping dibuat).
    """
    n = name.lower()
    groups = []
    coffee_kw = ["kopi", "coffee", "latte", "machiato", "v60", "vietnam", "espresso", "americano"]
    dairy_kw  = ["susu", "latte", "milk", "machiato", "chocolate", "coklat", "greentea",
                 "matcha", "macha", "red velvet", "hazelnut", "caramel"]

    if any(k in n for k in coffee_kw):
        groups.extend(["Beans Natural", "Cold Cup Plastik 16oz", "Sedotan Bening Standar"])
    if any(k in n for k in dairy_kw):
        groups.append("Susu Full Cream")
    if "gula aren" in n or "aren" in n:
        groups.append("Gula Aren / Aren Liquid")
    if "greentea" in n or "macha" in n or "matcha" in n:
        groups.append("Powder Greentea / Matcha")
    if "chocolate" in n or "coklat" in n:
        groups.append("Powder Chocolate / Coklat Bubuk")
    if "red velvet" in n or "red valvet" in n:
        groups.append("Powder Red Velvet")
    if "hazelnut" in n or "halzenut" in n:
        groups.append("Syrup Hazelnut")
    if "teh" in n or "tea" in n:
        groups.extend(["Teh Celup / Teh Bubuk", "Simple Syrup (Gula Cair)",
                        "Cold Cup Plastik 16oz", "Sedotan Bening Standar"])
    if "nasi" in n:
        groups.extend(["Beras (Nasi Putih)", "Minyak Goreng",
                        "Nasi Box / Rice Box Kertas", "Sendok Plastik Takeaway"])
    if "kentang" in n:
        groups.extend(["Kentang", "Minyak Goreng", "Box Snack Kertas Kecil"])
    if "pempek" in n:
        groups.extend(["Pempek Original", "Cuko Pempek", "Tray Plastik PP (untuk Pempek)"])
    if "pisang" in n:
        groups.append("Pisang Kepok / Cavendish")
    if "sosis" in n:
        groups.append("Sosis Ayam / Sosis Sapi")
    if "dimsum" in n:
        groups.extend(["Box Snack Kertas Kecil", "Sendok Plastik Takeaway"])

    return list(set(groups))


# ─── Statistik inferensial ───────────────────────────────────────────────────

def compute_coefficients(supabase_inv, supabase_invent, branch: str) -> pd.DataFrame:
    """
    Hitung koefisien pemakaian bahan baku per unit terjual.

    Metode:
      Untuk setiap periode opname:
        konsumsi_aktual = stok_masuk - stok_opname_akhir
        qty_terjual     = dari usage_log dalam periode yang sama
        koefisien       = konsumsi_aktual / qty_terjual

    Return DataFrame: [bahan_baku, koefisien_avg, satuan, n_periode, cv_pct]
    """
    # Ambil opname
    opname_rows = []
    if supabase_inv:
        try:
            res = (supabase_inv.table("stock_opname")
                   .select("*")
                   .eq("cabang", branch)
                   .order("tanggal", desc=False)
                   .execute())
            opname_rows = res.data or []
        except Exception:
            pass
    else:
        opname_rows = [r for r in st.session_state.get("opname_local", [])
                       if r.get("cabang") == branch]

    if len(opname_rows) < 2:
        return pd.DataFrame(columns=["bahan_baku", "koefisien_avg", "satuan",
                                      "n_periode", "cv_pct"])

    df_opname = pd.DataFrame(opname_rows)
    df_opname["tanggal"] = pd.to_datetime(df_opname["tanggal"])

    # Ambil stok masuk (dari tabel transaksi inventaris)
    stok_masuk_rows = []
    if supabase_invent:
        try:
            res = (supabase_invent.table("transaksi")
                   .select("tanggal, nama_barang, qty, uom_qty")
                   .eq("cabang", branch)
                   .execute())
            stok_masuk_rows = res.data or []
        except Exception:
            pass

    df_masuk = pd.DataFrame(stok_masuk_rows) if stok_masuk_rows else pd.DataFrame()

    # Ambil usage log
    usage_rows = []
    if supabase_inv:
        try:
            res = (supabase_inv.table("inventory_usage_log")
                   .select("tanggal, bahan_baku, qty_terjual")
                   .eq("cabang", branch)
                   .execute())
            usage_rows = res.data or []
        except Exception:
            pass
    else:
        usage_rows = [r for r in st.session_state.get("usage_log_local", [])
                      if r.get("cabang") == branch]

    df_usage = pd.DataFrame(usage_rows) if usage_rows else pd.DataFrame()

    if df_usage.empty or df_masuk.empty:
        return pd.DataFrame(columns=["bahan_baku", "koefisien_avg", "satuan",
                                      "n_periode", "cv_pct"])

    df_masuk["tanggal"] = pd.to_datetime(df_masuk["tanggal"])
    df_usage["tanggal"] = pd.to_datetime(df_usage["tanggal"])

    results = []
    bahan_list = df_opname["nama_barang"].unique()

    for bahan in bahan_list:
        op_bahan = df_opname[df_opname["nama_barang"] == bahan].sort_values("tanggal")
        koefs = []

        for i in range(1, len(op_bahan)):
            t_start = op_bahan.iloc[i - 1]["tanggal"]
            t_end   = op_bahan.iloc[i]["tanggal"]
            stok_awal = float(op_bahan.iloc[i - 1]["stok_fisik"])
            stok_akhir = float(op_bahan.iloc[i]["stok_fisik"])

            # Stok masuk dalam periode
            masuk_periode = df_masuk[
                (df_masuk["nama_barang"] == bahan) &
                (df_masuk["tanggal"] > t_start) &
                (df_masuk["tanggal"] <= t_end)
            ]["qty"].sum()

            konsumsi = stok_awal + masuk_periode - stok_akhir
            if konsumsi <= 0:
                continue

            # Qty terjual produk yang pakai bahan ini
            qty_sold = df_usage[
                (df_usage["bahan_baku"] == bahan) &
                (df_usage["tanggal"] > t_start) &
                (df_usage["tanggal"] <= t_end)
            ]["qty_terjual"].sum()

            if qty_sold > 0:
                koefs.append(konsumsi / qty_sold)

        if koefs:
            import numpy as np
            avg = float(np.mean(koefs))
            cv  = float(np.std(koefs) / avg * 100) if len(koefs) > 1 else 0
            satuan = op_bahan.iloc[0].get("satuan", "unit")
            results.append({
                "bahan_baku":     bahan,
                "koefisien_avg":  round(avg, 4),
                "satuan":         satuan,
                "n_periode":      len(koefs),
                "cv_pct":         round(cv, 1),
            })

    return pd.DataFrame(results).sort_values("bahan_baku") if results else \
           pd.DataFrame(columns=["bahan_baku", "koefisien_avg", "satuan", "n_periode", "cv_pct"])


def compute_reorder_alerts(supabase_inv, supabase_invent, branch: str) -> pd.DataFrame:
    """
    Hitung reorder alert untuk setiap bahan baku.

    Stok estimasi sekarang =
      stok_masuk_total - konsumsi_estimasi (dari usage_log × koefisien)

    Alert jika:
      stok_estimasi < (avg_harian × lead_time_hari) + safety_stock

    Return DataFrame siap tampil di dashboard.
    """
    import numpy as np

    df_koef = compute_coefficients(supabase_inv, supabase_invent, branch)

    # Stok masuk total per bahan
    stok_masuk = {}
    if supabase_invent:
        try:
            res = (supabase_invent.table("transaksi")
                   .select("nama_barang, qty, uom_qty")
                   .eq("cabang", branch)
                   .execute())
            for r in (res.data or []):
                bahan = r["nama_barang"]
                stok_masuk[bahan] = stok_masuk.get(bahan, 0) + float(r.get("qty", 0))
        except Exception:
            pass

    # Usage log total per bahan
    usage_total = {}
    if supabase_inv:
        try:
            res = (supabase_inv.table("inventory_usage_log")
                   .select("bahan_baku, qty_terjual")
                   .eq("cabang", branch)
                   .execute())
            for r in (res.data or []):
                b = r["bahan_baku"]
                usage_total[b] = usage_total.get(b, 0) + int(r.get("qty_terjual", 0))
        except Exception:
            pass
    else:
        for r in st.session_state.get("usage_log_local", []):
            if r.get("cabang") == branch:
                b = r["bahan_baku"]
                usage_total[b] = usage_total.get(b, 0) + int(r.get("qty_terjual", 0))

    # Opname terakhir per bahan (override estimasi)
    opname_latest = {}
    if supabase_inv:
        try:
            res = (supabase_inv.table("stock_opname")
                   .select("nama_barang, stok_fisik, satuan, tanggal")
                   .eq("cabang", branch)
                   .order("tanggal", desc=True)
                   .execute())
            seen = set()
            for r in (res.data or []):
                bahan = r["nama_barang"]
                if bahan not in seen:
                    opname_latest[bahan] = {
                        "stok_fisik": float(r["stok_fisik"]),
                        "satuan":     r.get("satuan", "unit"),
                        "tanggal":    r["tanggal"],
                    }
                    seen.add(bahan)
        except Exception:
            pass

    # Reorder config
    reorder_cfg = {}
    if supabase_inv:
        try:
            res = (supabase_inv.table("reorder_config")
                   .select("*")
                   .eq("cabang", branch)
                   .execute())
            for r in (res.data or []):
                reorder_cfg[r["nama_barang"]] = r
        except Exception:
            pass

    # Usage 7 hari terakhir untuk avg harian
    cutoff_7d = (datetime.now() - timedelta(days=7)).date().isoformat()
    usage_7d = {}
    if supabase_inv:
        try:
            res = (supabase_inv.table("inventory_usage_log")
                   .select("bahan_baku, qty_terjual")
                   .eq("cabang", branch)
                   .gte("tanggal", cutoff_7d)
                   .execute())
            for r in (res.data or []):
                b = r["bahan_baku"]
                usage_7d[b] = usage_7d.get(b, 0) + int(r.get("qty_terjual", 0))
        except Exception:
            pass

    # Semua bahan yang punya data
    all_bahan = set(stok_masuk) | set(usage_total) | set(opname_latest)
    if df_koef is not None and not df_koef.empty:
        all_bahan |= set(df_koef["bahan_baku"])

    rows = []
    for bahan in sorted(all_bahan):
        # Koefisien
        koef_row = None
        if df_koef is not None and not df_koef.empty:
            koef_rows = df_koef[df_koef["bahan_baku"] == bahan]
            if not koef_rows.empty:
                koef_row = koef_rows.iloc[0]
        koef    = float(koef_row["koefisien_avg"]) if koef_row is not None else 1.0
        satuan  = (koef_row["satuan"] if koef_row is not None
                   else opname_latest.get(bahan, {}).get("satuan", "unit"))
        cv_pct  = float(koef_row["cv_pct"]) if koef_row is not None else None

        # Stok estimasi
        if bahan in opname_latest:
            # Ada opname → lebih akurat: pakai stok fisik + stok masuk setelah opname
            op = opname_latest[bahan]
            stok_est = float(op["stok_fisik"])
            # tambah stok masuk setelah opname terakhir (tidak di-implement penuh di sini)
        else:
            # Estimasi kasar: masuk - estimasi_keluar
            masuk = stok_masuk.get(bahan, 0)
            keluar_estimasi = usage_total.get(bahan, 0) * koef
            stok_est = max(masuk - keluar_estimasi, 0)

        # Avg harian dari 7 hari terakhir
        sold_7d    = usage_7d.get(bahan, 0)
        avg_harian = (sold_7d * koef) / 7 if sold_7d > 0 else 0

        # Reorder config
        cfg         = reorder_cfg.get(bahan, {})
        lead_time   = int(cfg.get("lead_time_hari", 2))
        safety      = float(cfg.get("safety_stock", 0))
        reorder_pt  = (avg_harian * lead_time) + safety

        # Status
        if stok_est <= 0:
            status = "HABIS"
            color  = "kpi-danger"
        elif reorder_pt > 0 and stok_est <= reorder_pt:
            status = "REORDER"
            color  = "kpi-warning"
        elif reorder_pt > 0 and stok_est <= reorder_pt * 1.5:
            status = "PERHATIAN"
            color  = "kpi-warning"
        else:
            status = "AMAN"
            color  = "kpi-success"

        hari_tersisa = (stok_est / avg_harian) if avg_harian > 0 else None

        rows.append({
            "Bahan Baku":       bahan,
            "Stok Estimasi":    round(stok_est, 2),
            "Satuan":           satuan,
            "Avg Pakai/Hari":   round(avg_harian, 3),
            "Reorder Point":    round(reorder_pt, 2),
            "Lead Time (hari)": lead_time,
            "Hari Tersisa":     round(hari_tersisa, 1) if hari_tersisa else None,
            "Status":           status,
            "_color":           color,
            "_cv":              cv_pct,
        })

    return pd.DataFrame(rows)


# ─── Streamlit page ──────────────────────────────────────────────────────────

def page_stock_tracker(supabase_inv, cabang: str):
    """
    Halaman utama modul Stock Tracker.
    Tab 1: Reorder Alert Dashboard (auto-refresh)
    Tab 2: Sinkronisasi POS
    Tab 3: Stock Opname
    Tab 4: Mapping Produk → Bahan Baku
    Tab 5: Konfigurasi Reorder
    """
    import numpy as np

    st.title("Stok Real-Time")
    st.caption(
        f"Cabang {cabang}  ·  Sinkron otomatis dari POS  ·  "
        f"{datetime.now().strftime('%d %b %Y, %H:%M')}"
    )

    # Tombol sync manual di atas
    col_sync, col_info = st.columns([1, 4])
    with col_sync:
        if st.button("Sinkron POS Sekarang", type="primary", use_container_width=True):
            with st.spinner("Mengambil transaksi baru dari POS..."):
                result = sync_pos_to_inventory(supabase_inv, cabang)
            if result["new_trx"] == 0:
                st.info("Tidak ada transaksi baru sejak sinkronisasi terakhir.")
            else:
                st.success(
                    f"{result['new_trx']} transaksi baru  ·  "
                    f"{result['synced']} entri usage log ditambahkan  ·  "
                    f"{len(result['bahan_terdampak'])} bahan terdampak"
                )
    with col_info:
        last_sync = get_last_sync_time(supabase_inv, cabang)
        st.caption(
            f"Sinkronisasi terakhir: **{last_sync.strftime('%d %b %Y %H:%M')}**  ·  "
            "Klik 'Sinkron POS Sekarang' untuk update manual. "
            "Atau pasang Supabase Webhook di POS untuk sinkron otomatis tiap transaksi."
        )

    st.divider()

    tab_alert, tab_sync, tab_opname, tab_mapping, tab_config = st.tabs([
        "Reorder Alert",
        "Log Sinkronisasi",
        "Stock Opname",
        "Mapping Produk",
        "Konfigurasi Reorder",
    ])

    # ── TAB 1: REORDER ALERT ─────────────────────────────────────────────────
    with tab_alert:
        st.markdown('<div class="section-header">STATUS STOK ESTIMASI REAL-TIME</div>',
                    unsafe_allow_html=True)

        with st.spinner("Menghitung stok estimasi..."):
            df_alert = compute_reorder_alerts(supabase_inv, supabase_inv, cabang)

        if df_alert.empty:
            st.info(
                "Belum ada data cukup untuk menghitung reorder alert.  \n"
                "Langkah pertama: lakukan Sinkronisasi POS, lalu input Stock Opname "
                "minimal satu kali di tab 'Stock Opname'."
            )
        else:
            # Ringkasan KPI
            n_habis    = len(df_alert[df_alert["Status"] == "HABIS"])
            n_reorder  = len(df_alert[df_alert["Status"] == "REORDER"])
            n_perhatian= len(df_alert[df_alert["Status"] == "PERHATIAN"])
            n_aman     = len(df_alert[df_alert["Status"] == "AMAN"])

            c1, c2, c3, c4 = st.columns(4)
            def _kpi(col, label, val, theme):
                col.markdown(
                    f'<div class="kpi-card {theme}">'
                    f'<div class="kpi-accent"></div>'
                    f'<div class="kpi-label">{label}</div>'
                    f'<div class="kpi-value">{val}</div>'
                    f'</div>', unsafe_allow_html=True)

            _kpi(c1, "HABIS", f"{n_habis} bahan",     "kpi-danger"  if n_habis    else "kpi-success")
            _kpi(c2, "REORDER", f"{n_reorder} bahan", "kpi-warning" if n_reorder  else "kpi-success")
            _kpi(c3, "PERHATIAN", f"{n_perhatian} bahan", "kpi-warning" if n_perhatian else "kpi-success")
            _kpi(c4, "AMAN", f"{n_aman} bahan", "kpi-success")

            st.divider()

            # Tabel alert — hanya tampilkan yang bukan AMAN dulu
            filter_status = st.radio(
                "Filter status",
                ["Semua", "Butuh Tindakan (Habis + Reorder)", "Aman saja"],
                horizontal=True, key="alert_filter"
            )

            df_show = df_alert.copy()
            if filter_status == "Butuh Tindakan (Habis + Reorder)":
                df_show = df_show[df_show["Status"].isin(["HABIS", "REORDER", "PERHATIAN"])]
            elif filter_status == "Aman saja":
                df_show = df_show[df_show["Status"] == "AMAN"]

            display_cols = ["Bahan Baku", "Stok Estimasi", "Satuan",
                            "Avg Pakai/Hari", "Reorder Point", "Hari Tersisa", "Status"]
            display_cols = [c for c in display_cols if c in df_show.columns]

            st.dataframe(
                df_show[display_cols].sort_values(
                    "Status",
                    key=lambda s: s.map({"HABIS": 0, "REORDER": 1, "PERHATIAN": 2, "AMAN": 3})
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Catatan: Stok estimasi dihitung dari stok masuk (inventaris) dikurangi "
                "estimasi pemakaian (usage log POS × koefisien). Akurasi meningkat seiring "
                "bertambahnya data opname dan histori transaksi."
            )

    # ── TAB 2: LOG SINKRONISASI ───────────────────────────────────────────────
    with tab_sync:
        st.subheader("Log Pemakaian dari POS")

        usage_rows = []
        if supabase_inv:
            try:
                res = (supabase_inv.table("inventory_usage_log")
                       .select("tanggal, product_name, bahan_baku, qty_terjual, cabang")
                       .eq("cabang", cabang)
                       .order("tanggal", desc=True)
                       .limit(200)
                       .execute())
                usage_rows = res.data or []
            except Exception as e:
                st.warning(f"Gagal memuat log: {e}")
        else:
            usage_rows = [r for r in st.session_state.get("usage_log_local", [])
                          if r.get("cabang") == cabang]

        if usage_rows:
            df_log = pd.DataFrame(usage_rows)
            st.dataframe(df_log, use_container_width=True, hide_index=True)
            st.caption(f"{len(df_log)} entri usage log ditampilkan")
        else:
            st.info("Belum ada log sinkronisasi. Klik 'Sinkron POS Sekarang' di atas.")

    # ── TAB 3: STOCK OPNAME ───────────────────────────────────────────────────
    with tab_opname:
        st.subheader("Input Stock Opname")
        st.caption(
            "Hitung stok fisik setiap Senin pagi sebelum toko buka. "
            "Data ini digunakan untuk menghitung koefisien pemakaian aktual."
        )

        # Form input
        with st.form("form_opname"):
            col_tgl, col_pencatat = st.columns(2)
            with col_tgl:
                tgl_opname = st.date_input("Tanggal opname", value=date.today())
            with col_pencatat:
                pencatat = st.text_input("Nama pencatat", placeholder="Nama kasir/manager")

            st.markdown("**Isi stok fisik tiap bahan (kosongkan jika tidak dihitung):**")

            # Ambil daftar bahan dari transaksi inventaris
            bahan_list_inv = []
            if supabase_inv:
                try:
                    res = (supabase_inv.table("transaksi")
                           .select("nama_barang, uom_qty")
                           .eq("cabang", cabang)
                           .execute())
                    seen = set()
                    for r in (res.data or []):
                        if r["nama_barang"] not in seen:
                            bahan_list_inv.append(r)
                            seen.add(r["nama_barang"])
                except Exception:
                    pass

            if not bahan_list_inv:
                st.warning("Tidak ada data bahan baku inventaris. Catat pembelian dulu.")
            else:
                opname_inputs = {}
                cols = st.columns(3)
                for i, b in enumerate(bahan_list_inv):
                    with cols[i % 3]:
                        val = st.number_input(
                            b["nama_barang"],
                            min_value=0.0, step=0.5, format="%.2f",
                            key=f"opname_{b['nama_barang']}",
                            label_visibility="visible",
                        )
                        opname_inputs[b["nama_barang"]] = {
                            "nilai": val, "satuan": b.get("uom_qty", "unit")}

            catatan = st.text_area("Catatan", height=60)
            submit_opname = st.form_submit_button("Simpan Opname", type="primary")

        if submit_opname:
            rows_to_save = [
                {
                    "cabang":     cabang,
                    "nama_barang": bahan,
                    "stok_fisik":  vals["nilai"],
                    "satuan":      vals["satuan"],
                    "tanggal":     tgl_opname.isoformat(),
                    "pencatat":    pencatat,
                    "catatan":     catatan or None,
                }
                for bahan, vals in opname_inputs.items()
                if vals["nilai"] > 0
            ]
            if rows_to_save:
                if supabase_inv:
                    try:
                        supabase_inv.table("stock_opname").insert(rows_to_save).execute()
                        st.success(f"Opname {len(rows_to_save)} bahan tersimpan.")
                    except Exception as e:
                        st.error(f"Gagal simpan opname: {e}")
                else:
                    existing = st.session_state.get("opname_local", [])
                    existing.extend(rows_to_save)
                    st.session_state["opname_local"] = existing
                    st.success(f"Opname {len(rows_to_save)} bahan tersimpan (mode lokal).")
            else:
                st.warning("Tidak ada bahan yang diisi. Isi minimal satu nilai > 0.")

        # Riwayat opname
        st.divider()
        st.markdown("**Riwayat Opname Terakhir**")
        opname_hist = []
        if supabase_inv:
            try:
                res = (supabase_inv.table("stock_opname")
                       .select("*")
                       .eq("cabang", cabang)
                       .order("tanggal", desc=True)
                       .limit(50)
                       .execute())
                opname_hist = res.data or []
            except Exception:
                pass
        else:
            opname_hist = sorted(
                [r for r in st.session_state.get("opname_local", []) if r.get("cabang") == cabang],
                key=lambda x: x["tanggal"], reverse=True
            )[:50]

        if opname_hist:
            st.dataframe(pd.DataFrame(opname_hist), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat opname.")

    # ── TAB 4: MAPPING PRODUK ─────────────────────────────────────────────────
    with tab_mapping:
        st.subheader("Mapping Produk POS ke Bahan Baku")
        st.caption(
            "Tabel ini menghubungkan setiap menu di POS dengan bahan baku yang terlibat. "
            "Sudah diisi otomatis — manager dapat menambah, mengubah, atau menonaktifkan baris."
        )

        # Tampilkan mapping saat ini
        current_mapping = get_mapping(supabase_inv, cabang)
        mapping_rows = []
        for pid, bahans in current_mapping.items():
            # Cari nama produk
            prod_name = next((r["product_name"] for r in INITIAL_MAPPING
                              if r["product_id"] == pid and r["branch"] == cabang), pid[:8])
            for b in bahans:
                mapping_rows.append({"Product ID": pid[:8], "Nama Produk": prod_name, "Bahan Baku": b})

        if mapping_rows:
            df_map = pd.DataFrame(mapping_rows)
            st.dataframe(df_map, use_container_width=True, hide_index=True)
            st.caption(f"{len(mapping_rows)} baris mapping aktif untuk cabang {cabang}")

        st.divider()
        st.markdown("**Tambah Mapping Baru**")
        with st.form("form_mapping"):
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                new_pid   = st.text_input("Product ID (UUID dari POS)")
            with mc2:
                new_pname = st.text_input("Nama Produk")
            with mc3:
                new_bahan = st.text_input("Nama Bahan Baku (harus sama persis dengan inventaris)")
            save_map = st.form_submit_button("Tambah Mapping")

        if save_map and new_pid and new_bahan:
            row = {
                "product_id": new_pid.strip(),
                "product_name": new_pname.strip(),
                "branch": cabang,
                "bahan_baku": new_bahan.strip(),
                "active": True,
            }
            if supabase_inv:
                try:
                    supabase_inv.table("product_ingredient_groups").insert([row]).execute()
                    st.success("Mapping berhasil ditambahkan.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")
            else:
                INITIAL_MAPPING.append({**row})
                st.success("Mapping ditambahkan (mode lokal, tidak persisten).")

    # ── TAB 5: KONFIGURASI REORDER ────────────────────────────────────────────
    with tab_config:
        st.subheader("Konfigurasi Reorder Point per Bahan")
        st.caption(
            "Atur lead time supplier dan safety stock untuk setiap bahan baku. "
            "Semakin akurat nilainya, semakin tepat alert reorder."
        )

        # Ambil config saat ini
        cfg_rows = []
        if supabase_inv:
            try:
                res = (supabase_inv.table("reorder_config")
                       .select("*")
                       .eq("cabang", cabang)
                       .execute())
                cfg_rows = res.data or []
            except Exception:
                pass

        if cfg_rows:
            df_cfg = pd.DataFrame(cfg_rows)[["nama_barang", "lead_time_hari", "safety_stock", "satuan"]]
            st.dataframe(df_cfg, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("**Tambah / Ubah Konfigurasi**")
        with st.form("form_reorder_cfg"):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                rc_bahan = st.text_input("Nama Bahan Baku")
            with rc2:
                rc_lead  = st.number_input("Lead Time (hari)", min_value=1, value=2)
            with rc3:
                rc_safety= st.number_input("Safety Stock", min_value=0.0, step=0.5)
            with rc4:
                rc_satuan= st.text_input("Satuan", placeholder="liter, pack, kg...")
            save_cfg = st.form_submit_button("Simpan Konfigurasi")

        if save_cfg and rc_bahan:
            cfg_row = {
                "nama_barang":    rc_bahan.strip(),
                "cabang":         cabang,
                "lead_time_hari": int(rc_lead),
                "safety_stock":   float(rc_safety),
                "satuan":         rc_satuan.strip() or None,
            }
            if supabase_inv:
                try:
                    supabase_inv.table("reorder_config").upsert(
                        [cfg_row], on_conflict="nama_barang,cabang"
                    ).execute()
                    st.success("Konfigurasi tersimpan.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")
            else:
                st.info("Mode lokal — konfigurasi tidak persisten.")
