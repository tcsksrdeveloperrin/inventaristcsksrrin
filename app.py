import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import json

# ==========================================
# 1. KONFIGURASI HALAMAN & SUPABASE
# ==========================================
st.set_page_config(
    page_title="Real-Time Inventory PT. Sari Tropis Indonesia",
    layout="wide",
    page_icon="☕"
)

# Mengambil kredensial secara aman dari file secrets.toml
SUPABASE_INV_URL = st.secrets["SUPABASE_INV_URL"]
SUPABASE_INV_KEY = st.secrets["SUPABASE_INV_KEY"]

SUPABASE_POS_URL = st.secrets["SUPABASE_POS_URL"]
SUPABASE_POS_KEY = st.secrets["SUPABASE_POS_KEY"]

# ==========================================
# 2. STANDAR RESEP (Diambil dari PDF Panduan Resep)
# Format: "Nama Menu": {
#     "bahan": {"nama_bahan": takaran},
#     "packaging": {"nama_packaging": jumlah},
#     "kategori": "Minuman Panas" / "Minuman Dingin" / "Makanan"
# }
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

# Helper: flatten resep ke satu dict bahan+packaging berdasarkan jenis penggunaan
def get_pemotongan_stok(nama_menu, jumlah, mode="full"):
    """
    mode:
      'full'         => potong bahan + packaging (transaksi POS / konten / konsumsi pribadi)
      'bahan_only'   => potong bahan saja (uji coba resep)
      'packaging_only' => potong packaging saja
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
# 3. DUMMY DATABASE INVENTORY
# (Nantinya diganti dengan query Supabase)
# ==========================================
def get_dummy_inventory(cabang="Buper"):
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
                "Kraft", "Siomay Merek A", "Mandailing", "—",
                "Diamond", "Frisian Flag", "Homemade", "Homemade", "—", "Matcha JP",
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
            "Tanggal Beli": [
                "2025-07-01"]*18,
            "Tanggal Kadaluwarsa": [
                "2025-12-31", "2025-09-01", "2026-01-01", "2025-07-10",
                "2025-11-01", "2025-09-15", "2026-03-01", "—",
                "2025-08-01", "2025-10-01", "2025-08-20", "2025-08-20",
                "—", "2026-06-01",
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
                "Homemade", "—", "Matcha JP",
                "Gelas Plastik 16oz", "Gelas Kertas", "Kraft Box S", "Hdpe",
                "—", "Frisian Flag"
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
                "2025-08-20", "—", "2026-06-01",
                "2026-06-01", "2026-06-01", "2026-06-01", "2026-06-01",
                "—", "2025-10-01"
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


# ==========================================
# 4. MANAJEMEN SESSION STATE (LOGIN)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "cabang" not in st.session_state:
    st.session_state.cabang = ""
if "log_transaksi_manual" not in st.session_state:
    st.session_state.log_transaksi_manual = []

# Dummy Akun untuk Login
USERS = {
    "kasir_buper": {"password": "123", "role": "Kasir", "cabang": "Buper"},
    "kasir_wka": {"password": "123", "role": "Kasir", "cabang": "WKA"},
    "manager_buper": {"password": "123", "role": "Manager", "cabang": "Buper"},
    "manager_wka": {"password": "123", "role": "Manager", "cabang": "WKA"},
    "owner_buper": {"password": "123", "role": "Owner Cabang", "cabang": "Buper"},
    "owner_wka": {"password": "123", "role": "Owner Cabang", "cabang": "WKA"},
    "owner_pusat": {"password": "123", "role": "Owner Pusat", "cabang": "Semua"}
}


def login():
    st.title("☕ Login - Sistem Inventaris PT. Sari Tropis Indonesia")
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
                    st.success(f"🟩 Berhasil login sebagai {st.session_state.role} - Cabang {st.session_state.cabang}")
                    st.rerun()
                else:
                    st.error("🟥 Username atau Password salah!")

def logout():
    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.cabang = ""
    st.rerun()


# ==========================================
# 5. HALAMAN KASIR - Pencatatan Manual Non-POS
# ==========================================
def halaman_kasir():
    st.header(f"Panel Kasir — Cabang {st.session_state.cabang}")
    st.info(
        "Formulir ini digunakan untuk mencatat **penggunaan bahan baku di luar transaksi POS resmi**. "
        "Pengurangan stok akibat transaksi pembelian pelanggan sudah terjadi secara otomatis dari sistem POS."
    )

    tab1, tab2 = st.tabs(["📝 Catat Penggunaan Manual", "📋 Riwayat Pencatatan Hari Ini"])

    with tab1:
        kategori_penggunaan = {
            "Uji Coba Resep (Bahan Baku Saja — tanpa Packaging)": "bahan_only",
            "Foto/Konten Promosi Sosmed (Bahan Baku + Packaging)": "full",
            "Konsumsi Pribadi Barista (Bahan Baku + Packaging)": "full",
            "Konsumsi Pribadi Barista (Packaging Saja — bahan tidak dari stok)": "packaging_only",
        }

        with st.form("form_penggunaan_manual"):
            st.subheader("Catat Penggunaan Internal")
            col_a, col_b = st.columns(2)
            with col_a:
                jenis_label = st.selectbox("Tujuan Penggunaan", list(kategori_penggunaan.keys()))
                nama_barista = st.text_input("Nama Barista")
            with col_b:
                menu_terkait = st.selectbox("Pilih Menu/Item", list(RESEP_STANDAR.keys()))
                jumlah = st.number_input("Jumlah Porsi / Cup", min_value=1, step=1, value=1)

            catatan = st.text_area("Catatan Tambahan", placeholder="Contoh: Latihan untuk lomba barista, foto untuk Instagram")
            submit_manual = st.form_submit_button("✅ Catat & Potong Stok", use_container_width=True)

            if submit_manual:
                mode = kategori_penggunaan[jenis_label]
                stok_dipotong = get_pemotongan_stok(menu_terkait, jumlah, mode=mode)

                log_entry = {
                    "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "barista": nama_barista if nama_barista else "Tidak Disebutkan",
                    "tujuan": jenis_label,
                    "menu": menu_terkait,
                    "jumlah": jumlah,
                    "stok_dipotong": stok_dipotong,
                    "catatan": catatan,
                    "cabang": st.session_state.cabang
                }
                st.session_state.log_transaksi_manual.append(log_entry)

                st.success(f"✅ Berhasil dicatat! Stok berikut telah dikurangi:")
                df_potong = pd.DataFrame(
                    [{"Bahan / Packaging": k, "Jumlah Dikurangi": v}
                     for k, v in stok_dipotong.items()]
                )
                st.dataframe(df_potong, use_container_width=True)
                st.caption("⚡ Catatan ini akan dikirim ke database inventaris secara real-time.")
                # TODO: inv_db.table('inventory_manual_log').insert(log_entry).execute()
                # TODO: Panggil fungsi update stok di tabel inventory Supabase

    with tab2:
        if st.session_state.log_transaksi_manual:
            logs = [
                {
                    "Waktu": l["waktu"],
                    "Barista": l["barista"],
                    "Tujuan": l["tujuan"],
                    "Menu": l["menu"],
                    "Jumlah": l["jumlah"],
                    "Cabang": l["cabang"],
                    "Catatan": l["catatan"]
                }
                for l in st.session_state.log_transaksi_manual
            ]
            st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else:
            st.info("Belum ada pencatatan manual hari ini.")


# ==========================================
# 6. HALAMAN MANAGER - Dashboard, Peringatan & Export
# ==========================================
def halaman_manager():
    st.header(f"📊 Dashboard Manager — Cabang {st.session_state.cabang}")

    data_inv = get_dummy_inventory(st.session_state.cabang)
    data_inv["Status"] = data_inv.apply(
        lambda x: "🚨 Restock!" if x["Sisa Stok"] < x["Batas Aman"] else "✅ Aman", axis=1
    )
    # Estimasi hari tersisa (asumsi: rata-rata penggunaan per hari dari data dummy)
    data_inv["Rata-rata Pakai/Hari"] = data_inv["Sisa Stok"].apply(
        lambda x: max(1, round(x / 30, 1))
    )
    data_inv["Estimasi Habis (Hari)"] = (
        data_inv["Sisa Stok"] / data_inv["Rata-rata Pakai/Hari"]
    ).apply(lambda x: round(x, 1))
    data_inv["Prediksi Restock"] = data_inv["Estimasi Habis (Hari)"].apply(
        lambda x: (datetime.now() + timedelta(days=x)).strftime("%d %b %Y")
    )

    # === Kartu Ringkasan ===
    col1, col2, col3, col4 = st.columns(4)
    total_item = len(data_inv)
    butuh_restock = (data_inv["Status"] == "🚨 Restock!").sum()
    aman = total_item - butuh_restock
    hampir_habis = ((data_inv["Estimasi Habis (Hari)"] <= 7) & (data_inv["Status"] != "🚨 Restock!")).sum()

    col1.metric("Total Item Inventaris", total_item)
    col2.metric("✅ Stok Aman", aman)
    col3.metric("⚠️ Hampir Habis (≤7 hari)", hampir_habis)
    col4.metric("🚨 Perlu Restock Segera", butuh_restock)

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Tabel Stok", "⚠️ Peringatan Restock", "📈 Grafik Tren", "📥 Export Laporan"
    ])

    with tab1:
        st.subheader("Status Inventory Saat Ini")
        kategori_filter = st.multiselect(
            "Filter Kategori:",
            options=data_inv["Kategori"].unique().tolist(),
            default=data_inv["Kategori"].unique().tolist()
        )
        df_filtered = data_inv[data_inv["Kategori"].isin(kategori_filter)]

        def color_status(val):
            if "Restock" in str(val):
                return "background-color: #ffcccc"
            return "background-color: #ccffcc"

        styled = df_filtered[[
            "Item", "Merk", "Kategori", "Sisa Stok", "Satuan",
            "Batas Aman", "Status", "Estimasi Habis (Hari)", "Prediksi Restock",
            "Tanggal Kadaluwarsa", "Harga Beli (Rp)"
        ]].style.applymap(color_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True)

    with tab2:
        st.subheader("🚨 Peringatan Stok Kritis")
        darurat = data_inv[data_inv["Status"] == "🚨 Restock!"]
        hampir = data_inv[
            (data_inv["Estimasi Habis (Hari)"] <= 7) & (data_inv["Status"] != "🚨 Restock!")
        ]

        if not darurat.empty:
            st.error(f"**{len(darurat)} item** perlu restock SEGERA!")
            for _, row in darurat.iterrows():
                st.error(
                    f"🔴 **{row['Item']}** — Sisa: {row['Sisa Stok']} {row['Satuan']} "
                    f"| Batas Aman: {row['Batas Aman']} | "
                    f"Prediksi Habis: {row['Prediksi Restock']}"
                )
        else:
            st.success("Tidak ada item yang perlu restock segera.")

        if not hampir.empty:
            st.warning(f"**{len(hampir)} item** akan habis dalam 7 hari ke depan:")
            for _, row in hampir.iterrows():
                st.warning(
                    f"🟡 **{row['Item']}** — Estimasi habis: {row['Estimasi Habis (Hari)']} hari "
                    f"({row['Prediksi Restock']})"
                )

    with tab3:
        st.subheader("📊 Visualisasi Stok vs. Batas Aman")

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Sisa Stok",
            x=data_inv["Item"],
            y=data_inv["Sisa Stok"],
            marker_color="steelblue"
        ))
        fig_bar.add_trace(go.Bar(
            name="Batas Aman",
            x=data_inv["Item"],
            y=data_inv["Batas Aman"],
            marker_color="salmon"
        ))
        fig_bar.update_layout(
            barmode="group", xaxis_tickangle=-45,
            title="Perbandingan Sisa Stok vs. Batas Aman",
            height=500
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        fig_pie = px.pie(
            data_inv,
            names="Kategori",
            values="Sisa Stok",
            title="Distribusi Stok per Kategori"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab4:
        st.subheader("Export Laporan Inventaris")
        col_a, col_b = st.columns(2)
        with col_a:
            tgl_mulai = st.date_input("Tanggal Mulai", value=datetime.now().date() - timedelta(days=30))
        with col_b:
            tgl_akhir = st.date_input("Tanggal Akhir", value=datetime.now().date())

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            data_inv.to_excel(writer, index=False, sheet_name='Inventory')
            # Sheet tambahan: resep standar
            resep_rows = []
            for menu, detail in RESEP_STANDAR.items():
                for bahan, takaran in detail.get("bahan", {}).items():
                    resep_rows.append({"Menu": menu, "Kategori Menu": detail.get("kategori",""), "Bahan/Packaging": bahan, "Jenis": "Bahan", "Takaran": takaran})
                for pkg, qty in detail.get("packaging", {}).items():
                    resep_rows.append({"Menu": menu, "Kategori Menu": detail.get("kategori",""), "Bahan/Packaging": pkg, "Jenis": "Packaging", "Takaran": qty})
            pd.DataFrame(resep_rows).to_excel(writer, index=False, sheet_name='Resep Standar')

        st.download_button(
            label="📥 Download Laporan Excel",
            data=output.getvalue(),
            file_name=f"Laporan_Inventory_{st.session_state.cabang}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ==========================================
# 7. HALAMAN OWNER CABANG - Dashboard Satu Cabang
# ==========================================
def halaman_owner_cabang():
    cabang = st.session_state.cabang
    st.header(f"📈 Executive Dashboard — Cabang {cabang}")
    st.write(f"Menampilkan data untuk cabang: **{cabang}**")

    data_inv = get_dummy_inventory(cabang)
    data_inv["Status"] = data_inv.apply(
        lambda x: "🚨 Restock!" if x["Sisa Stok"] < x["Batas Aman"] else "✅ Aman", axis=1
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Item Dipantau", len(data_inv))
    col2.metric("✅ Stok Aman", (data_inv["Status"] == "✅ Aman").sum())
    col3.metric("🚨 Perlu Restock", (data_inv["Status"] == "🚨 Restock!").sum())

    st.markdown("---")

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Sisa Stok", x=data_inv["Item"], y=data_inv["Sisa Stok"], marker_color="steelblue"))
    fig.add_trace(go.Bar(name="Batas Aman", x=data_inv["Item"], y=data_inv["Batas Aman"], marker_color="salmon"))
    fig.update_layout(barmode="group", xaxis_tickangle=-45, title=f"Status Stok Cabang {cabang}", height=450)
    st.plotly_chart(fig, use_container_width=True)

    fig_cat = px.pie(data_inv, names="Kategori", values="Sisa Stok", title="Komposisi Stok: Bahan Baku vs Packaging")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.subheader("Tabel Ringkasan Stok")
    st.dataframe(
        data_inv[["Item", "Kategori", "Sisa Stok", "Satuan", "Batas Aman", "Status"]],
        use_container_width=True
    )


# ==========================================
# 8. HALAMAN OWNER PUSAT - Dashboard Multi-Cabang + Drill Down
# ==========================================
def halaman_owner_pusat():
    st.header("🏢 Executive Dashboard — Owner Pusat")
    st.write("Pantau seluruh cabang kafe PT. Sari Tropis Indonesia dari satu layar.")

    # Drill down selector
    cabang_pilihan = st.selectbox(
        "🔍 Drill Down — Pilih Cabang:",
        ["Semua Cabang", "Buper", "WKA"]
    )

    # Gabungkan data semua cabang
    df_buper = get_dummy_inventory("Buper")
    df_wka = get_dummy_inventory("WKA")
    df_all = pd.concat([df_buper, df_wka], ignore_index=True)
    df_all["Status"] = df_all.apply(
        lambda x: "🚨 Restock!" if x["Sisa Stok"] < x["Batas Aman"] else "✅ Aman", axis=1
    )

    if cabang_pilihan != "Semua Cabang":
        df_view = df_all[df_all["Cabang"] == cabang_pilihan]
        label_cabang = cabang_pilihan
    else:
        df_view = df_all
        label_cabang = "Semua Cabang"

    # KPI
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cabang Aktif", 2 if cabang_pilihan == "Semua Cabang" else 1)
    col2.metric("Total Item Dipantau", len(df_view))
    col3.metric("✅ Stok Aman", (df_view["Status"] == "✅ Aman").sum())
    col4.metric("🚨 Perlu Restock", (df_view["Status"] == "🚨 Restock!").sum())

    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 Grafik Perbandingan", "📋 Detail Stok"])

    with tab1:
        # Grouped bar per cabang per kategori
        df_agg = df_view.groupby(["Cabang", "Kategori"])["Sisa Stok"].sum().reset_index()
        fig1 = px.bar(
            df_agg, x="Kategori", y="Sisa Stok", color="Cabang",
            barmode="group", title=f"Perbandingan Sisa Stok — {label_cabang}"
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Estimasi nilai stok (harga beli x sisa)
        df_view2 = df_view.copy()
        df_view2["Nilai Stok (Rp)"] = df_view2["Sisa Stok"] * (df_view2["Harga Beli (Rp)"] / 1000)
        df_nilai = df_view2.groupby(["Cabang", "Kategori"])["Nilai Stok (Rp)"].sum().reset_index()
        fig2 = px.bar(
            df_nilai, x="Kategori", y="Nilai Stok (Rp)", color="Cabang",
            barmode="group", title=f"Estimasi Nilai Stok (per 1000 unit) — {label_cabang}"
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader(f"Detail Stok — {label_cabang}")
        st.dataframe(
            df_view[["Cabang", "Item", "Kategori", "Sisa Stok", "Satuan", "Batas Aman", "Status"]],
            use_container_width=True
        )

        # Highlight item kritis lintas cabang
        kritis = df_view[df_view["Status"] == "🚨 Restock!"]
        if not kritis.empty:
            st.error(f"⚠️ Ada **{len(kritis)} item** yang perlu restock di {label_cabang}:")
            for _, row in kritis.iterrows():
                st.error(f"🔴 [{row['Cabang']}] {row['Item']} — Sisa: {row['Sisa Stok']} {row['Satuan']}")


# ==========================================
# 9. SIDEBAR & INTEGRASI POS (Simulasi)
# ==========================================
def tampilkan_sidebar():
    with st.sidebar:
        st.title("☕ Menu Utama")
        st.write(f"👤 **{st.session_state.role}**")
        st.write(f"📍 Cabang: **{st.session_state.cabang}**")
        st.write(f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}")
        st.markdown("---")

        # Simulasi notifikasi dari POS
        st.subheader("🔔 Transaksi POS Terbaru")
        transaksi_pos_dummy = [
            {"waktu": "10:32", "item": "Latte Series (Ice)", "qty": 2, "cabang": "Buper"},
            {"waktu": "10:45", "item": "Kentang Goreng", "qty": 1, "cabang": "WKA"},
            {"waktu": "11:01", "item": "Americano Ice", "qty": 1, "cabang": "Buper"},
        ]
        for t in transaksi_pos_dummy:
            if st.session_state.cabang == "Semua" or t["cabang"] == st.session_state.cabang:
                st.caption(
                    f"⏱ {t['waktu']} — **{t['item']}** x{t['qty']} [{t['cabang']}]\n"
                    f"↳ Stok otomatis terpotong via POS"
                )

        st.markdown("---")
        st.caption("📡 Sistem terhubung ke database POS secara real-time")
        st.markdown("---")
        st.button("🚪 Logout", on_click=logout, use_container_width=True)


# ==========================================
# 10. MAIN ROUTING
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

