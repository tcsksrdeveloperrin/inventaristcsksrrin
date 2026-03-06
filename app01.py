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
        url = st.secrets["https://supabase.com/dashboard/project/psvkisbwzikhjsatdgjr"]
        key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBzdmtpc2J3emlraGpzYXRkZ2pyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxODIxNjAsImV4cCI6MjA4Nzc1ODE2MH0.2_gKwcctMt6Lf7Ay8M1oSYHK1uQzgcTd_M7vYFpYwFI"]
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
    .info-box {
        background: linear-gradient(135deg, #667eea15, #764ba215);
        border: 1px solid #667eea40;
        border-radius: 10px;
        padding: 0.7rem 1rem;
        font-size: 0.9rem;
        margin-top: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── KONSTANTA ───────────────────────────────────────────────────────────────────
KATEGORI_OPTIONS = ["Bahan Baku Minuman", "Bahan Baku Makanan", "Packaging"]

SUB_KATEGORI_MAP = {
    "Bahan Baku Minuman": ["Coffee Beans", "Dairy & Creamer", "Powder & Syrup", "Lainnya"],
    "Bahan Baku Makanan": ["Protein", "Fresh & Produce", "Tepung & Kering", "Bumbu", "Lainnya"],
    "Packaging":          ["Gelas & Tutup", "Sedotan", "Kantong Plastik", "Box Makanan", "Lainnya"],
}

UOM_OPTIONS    = ["kg", "gram", "liter", "ml", "pcs", "pack", "dus", "botol", "karton", "lusin"]
GRIND_OPTIONS  = ["-", "Whole Bean", "V60 (5-6)", "Vietnam Drip (3-4)", "Espresso (2-3)", "French Press (7-8)"]
STATUS_OPTIONS = ["Lunas", "Tempo (Hutang)", "DP/Uang Muka"]

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
        "local_data": [],   # fallback in-memory jika Supabase belum terhubung
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
            st.warning(f"⚠️ Gagal memuat data dari Supabase: {e}")
    rows = [r for r in st.session_state.local_data if r.get("cabang") == cabang]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=KOLOM_DB)

def insert_row(data: dict) -> bool:
    if supabase:
        try:
            supabase.table("transaksi").insert(data).execute()
            return True
        except Exception as e:
            st.error(f"❌ Gagal menyimpan ke database: {e}")
            return False
    data["id"]         = st.session_state.next_id
    data["created_at"] = datetime.now().isoformat()
    st.session_state.local_data.append(data.copy())
    st.session_state.next_id += 1
    return True

def update_row(row_id, data: dict) -> bool:
    if supabase:
        try:
            supabase.table("transaksi").update(data).eq("id", row_id).execute()
            return True
        except Exception as e:
            st.error(f"❌ Gagal memperbarui: {e}")
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
            st.error(f"❌ Gagal menghapus: {e}")
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
            st.warning(f"⚠️ Supabase belum terhubung: {e}")
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
            username  = st.text_input("👤 Username", placeholder="Masukkan username")
            password  = st.text_input("🔐 Password", type="password", placeholder="Masukkan password")
            login_btn = st.form_submit_button("Masuk →", use_container_width=True, type="primary")

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
                    st.error("❌ Username atau password salah. Hubungi manager jika lupa kredensial.")

        if not supabase:
            st.markdown("""
            <div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;
                        padding:0.8rem 1rem;margin-top:1rem;font-size:0.82rem;color:#9a3412;'>
            ⚠️ <b>Supabase belum terhubung.</b><br>
            Tambahkan <code>SUPABASE_URL</code> dan <code>SUPABASE_KEY</code>
            di file <code>.streamlit/secrets.toml</code> untuk mengaktifkan login dan penyimpanan data.
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

        st.markdown("""
        <div style='margin-top:2rem;border-top:1px solid rgba(255,255,255,0.1);
                    padding-top:1rem;'></div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Keluar", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    return page

# ─── PAGE: DASHBOARD ─────────────────────────────────────────────────────────────
def page_dashboard(df: pd.DataFrame):
    st.title("📊 Dashboard")
    st.caption(f"Cabang **{st.session_state.cabang}** · {datetime.now().strftime('%A, %d %B %Y')}")

    if df.empty:
        empty_state(
            "📊", "Belum Ada Data",
            "Mulai catat transaksi pertama kamu di halaman Administrasi → Catat Transaksi Baru."
        )
        return

    df["total_harga"]  = pd.to_numeric(df["total_harga"],  errors="coerce").fillna(0)
    df["harga_satuan"] = pd.to_numeric(df["harga_satuan"], errors="coerce").fillna(0)
    df["qty"]          = pd.to_numeric(df["qty"],          errors="coerce").fillna(0)

    total_keluar  = df["total_harga"].sum()
    total_trx     = len(df)
    n_lunas       = len(df[df["status_pembayaran"] == "Lunas"])
    total_hutang  = df[df["status_pembayaran"].str.contains("Tempo|DP", na=False)]["total_harga"].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💸 Total Pengeluaran",      f"Rp {total_keluar:,.0f}")
    with c2: st.metric("📝 Jumlah Transaksi",         total_trx)
    with c3: st.metric("✅ Lunas",                   f"{n_lunas} dari {total_trx}")
    with c4: st.metric("⏳ Total Hutang Supplier",   f"Rp {total_hutang:,.0f}")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📂 Pengeluaran per Kategori")
        if "kategori" in df.columns:
            kat = df.groupby("kategori")["total_harga"].sum().reset_index()
            kat.columns = ["Kategori", "Total (Rp)"]
            st.dataframe(kat.sort_values("Total (Rp)", ascending=False),
                         use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("🏪 Top Supplier")
        if "supplier" in df.columns:
            sup = df.groupby("supplier")["total_harga"].sum().reset_index()
            sup.columns = ["Supplier", "Total (Rp)"]
            st.dataframe(sup.sort_values("Total (Rp)", ascending=False).head(8),
                         use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⚠️ Peringatan Kadaluarsa — 30 Hari ke Depan")
    if "tgl_kadaluarsa" in df.columns:
        df_exp = df[
            df["tgl_kadaluarsa"].notna() &
            (df["tgl_kadaluarsa"].astype(str).str.strip() != "") &
            (df["tgl_kadaluarsa"].astype(str).str.strip() != "None")
        ].copy()
        if not df_exp.empty:
            df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
            today = pd.Timestamp.today().normalize()
            soon  = df_exp[df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30)]
            if not soon.empty:
                show_exp = ["nama_barang","merk","qty","uom","tgl_kadaluarsa"]
                show_exp = [c for c in show_exp if c in soon.columns]
                st.dataframe(soon[show_exp].sort_values("tgl_kadaluarsa"),
                             use_container_width=True, hide_index=True)
            else:
                st.success("✅ Tidak ada barang yang akan kadaluarsa dalam 30 hari ke depan.")
        else:
            st.info("Belum ada data kadaluarsa yang dicatat.")

# ─── PAGE: ADMINISTRASI ───────────────────────────────────────────────────────────
def page_administrasi(df: pd.DataFrame):
    st.title("📋 Administrasi — Jejak Rekam Transaksi")

    tab_catat, tab_riwayat, tab_kelola = st.tabs([
        "✏️ Catat Transaksi Baru",
        "📃 Riwayat Transaksi",
        "⚙️ Kelola Data",
    ])

    # ── TAB: CATAT TRANSAKSI BARU ────────────────────────────────────────────────
    with tab_catat:
        st.markdown("Isi form di bawah sesuai faktur / nota pembelian. Kolom bertanda **\*** wajib diisi.")
        st.markdown("")

        with st.form("form_catat", clear_on_submit=True):

            st.markdown('<div class="form-section-title">📋 Seksi 1 — Administrasi</div>',
                        unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                f_tanggal  = st.date_input("Tanggal Transaksi *", value=date.today())
            with col2:
                f_nota     = st.text_input("Nomor Nota / Invoice",
                                           placeholder="Contoh: INV-001")
            with col3:
                f_supplier = st.text_input("Nama Supplier *",
                                           placeholder="Contoh: Roastery A, Makmur Plastik")

            st.divider()
            st.markdown('<div class="form-section-title">🏷️ Seksi 2 — Identitas Barang</div>',
                        unsafe_allow_html=True)
            col4, col5 = st.columns(2)
            with col4:
                f_kategori = st.selectbox("Kategori *", KATEGORI_OPTIONS)
            with col5:
                f_sub      = st.selectbox("Sub Kategori *",
                                          SUB_KATEGORI_MAP.get(f_kategori, ["Lainnya"]))

            col6, col7, col8 = st.columns(3)
            with col6:
                f_nama  = st.text_input("Nama Barang *",
                                        placeholder="Contoh: Biji Kopi Arabika, Cup Paper 8oz Hot")
            with col7:
                f_merk  = st.text_input("Merk / Brand",
                                        placeholder="Contoh: Single Origin, Diamond, Fiesta")
            with col8:
                f_grind = st.selectbox("Grind Size (Khusus Kopi)", GRIND_OPTIONS)

            st.divider()
            st.markdown('<div class="form-section-title">📦 Seksi 3 — Detail Stok & Harga</div>',
                        unsafe_allow_html=True)
            col9, col10, col11 = st.columns(3)
            with col9:
                f_qty   = st.number_input("Kuantitas (Qty) *",
                                          min_value=0.0, step=0.5, format="%.2f",
                                          help="Jumlah fisik yang dibeli")
            with col10:
                f_uom   = st.selectbox("Satuan (UoM) *", UOM_OPTIONS,
                                       help="kg, liter, pcs, dus, dll")
            with col11:
                f_harga = st.number_input("Harga Satuan (Rp) *",
                                          min_value=0, step=500,
                                          help="Harga per 1 satuan sesuai UoM")

            f_total = f_qty * f_harga
            st.markdown(f"""
            <div class="info-box">
                💰 <b>Total Harga (otomatis):</b> Rp {f_total:,.0f}
                &nbsp;·&nbsp; {f_qty} {f_uom} × Rp {f_harga:,.0f}
            </div>
            """, unsafe_allow_html=True)

            st.divider()
            st.markdown('<div class="form-section-title">🔍 Seksi 4 — Kontrol & Audit</div>',
                        unsafe_allow_html=True)
            col12, col13 = st.columns(2)
            with col12:
                f_exp    = st.date_input("Tanggal Kadaluarsa",
                                         value=None,
                                         help="Kosongkan jika tidak ada / tidak relevan (Packaging, dll)")
            with col13:
                f_status = st.selectbox("Status Pembayaran *", STATUS_OPTIONS)

            f_catatan = st.text_area(
                "Catatan Tambahan",
                placeholder="Contoh: Tutup botol retak sudah diretur · Dapat diskon 5% · Barang titipan cabang",
                height=85,
            )

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button(
                "💾 Simpan Transaksi", type="primary", use_container_width=True
            )

        if submit:
            errors = []
            if not f_supplier.strip(): errors.append("Nama Supplier")
            if not f_nama.strip():     errors.append("Nama Barang")
            if f_qty <= 0:             errors.append("Kuantitas harus lebih dari 0")
            if f_harga <= 0:           errors.append("Harga Satuan harus lebih dari 0")

            if errors:
                st.error("❌ Harap lengkapi kolom berikut: " + " · ".join(errors))
            else:
                ok = insert_row({
                    "cabang":            st.session_state.cabang,
                    "tanggal":           f_tanggal.isoformat(),
                    "no_nota":           f_nota.strip() or None,
                    "supplier":          f_supplier.strip(),
                    "kategori":          f_kategori,
                    "sub_kategori":      f_sub,
                    "nama_barang":       f_nama.strip(),
                    "merk":              f_merk.strip() or "-",
                    "grind_size":        f_grind,
                    "qty":               float(f_qty),
                    "uom":               f_uom,
                    "harga_satuan":      int(f_harga),
                    "total_harga":       int(f_total),
                    "tgl_kadaluarsa":    f_exp.isoformat() if f_exp else None,
                    "status_pembayaran": f_status,
                    "catatan":           f_catatan.strip() or None,
                })
                if ok:
                    st.success(f"✅ Transaksi **{f_nama.strip()}** dari **{f_supplier.strip()}** berhasil dicatat!")
                    st.balloons()

    # ── TAB: RIWAYAT ─────────────────────────────────────────────────────────────
    with tab_riwayat:
        if df.empty:
            empty_state(
                "📃", "Belum Ada Riwayat Transaksi",
                "Catat transaksi pertama di tab 'Catat Transaksi Baru'."
            )
        else:
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                cari = st.text_input("🔍 Cari nama barang / supplier")
            with col_f2:
                fil_kat = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="r_kat")
            with col_f3:
                fil_st  = st.selectbox("Status Bayar", ["Semua"] + STATUS_OPTIONS, key="r_st")
            with col_f4:
                fil_bln = st.text_input("Bulan (YYYY-MM)", placeholder="Contoh: 2025-07")

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
                hasil["tanggal"] = hasil["tanggal"].astype(str)
                hasil = hasil[hasil["tanggal"].str.startswith(fil_bln)]

            tampil = ["tanggal","no_nota","supplier","nama_barang","merk",
                      "kategori","qty","uom","harga_satuan","total_harga","status_pembayaran"]
            tampil = [c for c in tampil if c in hasil.columns]
            urut = hasil.sort_values("tanggal", ascending=False) if "tanggal" in hasil.columns else hasil
            st.dataframe(urut[tampil], use_container_width=True, hide_index=True)

            total_f = pd.to_numeric(hasil["total_harga"], errors="coerce").sum()
            st.caption(f"**{len(hasil)}** transaksi ditampilkan · Total: **Rp {total_f:,.0f}**")

    # ── TAB: KELOLA ───────────────────────────────────────────────────────────────
    with tab_kelola:
        if st.session_state.role != "manager":
            st.info("🔒 Fitur edit dan hapus hanya tersedia untuk **Manager**.")
        elif df.empty:
            empty_state("⚙️", "Belum Ada Data", "Belum ada transaksi yang bisa dikelola.")
        else:
            if "id" not in df.columns:
                st.warning("Kolom ID tidak tersedia dari database.")
            else:
                col_sel, _ = st.columns([1, 2])
                with col_sel:
                    id_pilih = st.selectbox(
                        "Pilih ID Transaksi",
                        df["id"].tolist(),
                        format_func=lambda x: f"ID {x} — {df[df['id']==x]['nama_barang'].values[0] if not df[df['id']==x].empty else ''}"
                    )

                baris = df[df["id"] == id_pilih]
                if not baris.empty:
                    row = baris.iloc[0]
                    st.markdown(
                        f"**Terpilih:** {row.get('nama_barang','-')} · "
                        f"{row.get('supplier','-')} · {row.get('tanggal','-')}"
                    )

                    with st.expander("✏️ Edit Transaksi Ini", expanded=False):
                        with st.form(f"edit_{id_pilih}"):
                            ec1, ec2, ec3 = st.columns(3)
                            with ec1:
                                e_tgl  = st.date_input("Tanggal",
                                    value=pd.to_datetime(row.get("tanggal", date.today())).date())
                                e_nota = st.text_input("No. Nota",
                                    value=str(row.get("no_nota") or ""))
                            with ec2:
                                e_sup  = st.text_input("Supplier",
                                    value=str(row.get("supplier") or ""))
                                kat_n  = row.get("kategori", KATEGORI_OPTIONS[0])
                                e_kat  = st.selectbox("Kategori", KATEGORI_OPTIONS,
                                    index=KATEGORI_OPTIONS.index(kat_n) if kat_n in KATEGORI_OPTIONS else 0)
                            with ec3:
                                sub_l  = SUB_KATEGORI_MAP.get(e_kat, ["Lainnya"])
                                sub_n  = row.get("sub_kategori", sub_l[0])
                                e_sub  = st.selectbox("Sub Kategori", sub_l,
                                    index=sub_l.index(sub_n) if sub_n in sub_l else 0)
                                e_nama = st.text_input("Nama Barang",
                                    value=str(row.get("nama_barang") or ""))

                            ec4, ec5, ec6 = st.columns(3)
                            with ec4:
                                e_merk  = st.text_input("Merk",
                                    value=str(row.get("merk") or ""))
                            with ec5:
                                e_qty   = st.number_input("Qty",
                                    value=float(row.get("qty", 0)),
                                    min_value=0.0, step=0.5)
                                uom_n   = row.get("uom", UOM_OPTIONS[0])
                                e_uom   = st.selectbox("UoM", UOM_OPTIONS,
                                    index=UOM_OPTIONS.index(uom_n) if uom_n in UOM_OPTIONS else 0)
                            with ec6:
                                e_hrg   = st.number_input("Harga Satuan",
                                    value=int(row.get("harga_satuan", 0)),
                                    min_value=0, step=500)
                                st_n    = row.get("status_pembayaran", STATUS_OPTIONS[0])
                                e_st    = st.selectbox("Status Pembayaran", STATUS_OPTIONS,
                                    index=STATUS_OPTIONS.index(st_n) if st_n in STATUS_OPTIONS else 0)

                            exp_n   = row.get("tgl_kadaluarsa")
                            exp_v   = pd.to_datetime(exp_n).date() if exp_n and str(exp_n) not in ("None","") else None
                            e_exp   = st.date_input("Tgl Kadaluarsa", value=exp_v)
                            e_cat   = st.text_area("Catatan",
                                value=str(row.get("catatan") or ""), height=70)

                            e_total = e_qty * e_hrg
                            st.info(f"Total Harga (baru): **Rp {e_total:,.0f}**")

                            if st.form_submit_button("💾 Simpan Perubahan", type="primary"):
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
                                    st.success("✅ Data berhasil diperbarui!")
                                    st.rerun()

                    with st.expander("🗑️ Hapus Transaksi Ini", expanded=False):
                        st.warning(
                            f"Kamu akan menghapus: **{row.get('nama_barang','-')}** "
                            f"dari **{row.get('supplier','-')}**. "
                            "Tindakan ini **tidak bisa dibatalkan**."
                        )
                        konfirm = st.text_input('Ketik "HAPUS" untuk konfirmasi', key="konfirm_hapus")
                        if st.button("🗑️ Hapus Sekarang", type="primary"):
                            if konfirm.strip().upper() == "HAPUS":
                                ok = delete_row(id_pilih)
                                if ok:
                                    st.success("✅ Transaksi berhasil dihapus.")
                                    st.rerun()
                            else:
                                st.error('Ketik kata "HAPUS" (huruf kapital semua) untuk konfirmasi.')

# ─── PAGE: IDENTITAS BARANG ───────────────────────────────────────────────────────
def page_identitas(df: pd.DataFrame):
    st.title("🏷️ Identitas Barang — Spesifikasi Produk")

    if df.empty:
        empty_state(
            "🏷️", "Belum Ada Barang Tercatat",
            "Catat transaksi terlebih dahulu untuk melihat katalog barang."
        )
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fil_kat = st.selectbox("Filter Kategori", ["Semua"] + KATEGORI_OPTIONS)
    with col_f2:
        cari = st.text_input("🔍 Cari Nama Barang / Merk")

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
    katalog_cols = ["kategori","sub_kategori","nama_barang","merk","grind_size","uom"]
    katalog_cols = [c for c in katalog_cols if c in tampil.columns]
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
            pilih = st.selectbox("Pilih Barang", barang_list)
            detail = tampil[tampil["nama_barang"] == pilih]
            st.write(f"**{len(detail)} transaksi** untuk *{pilih}*")
            detail_cols = ["tanggal","supplier","merk","qty","uom","harga_satuan","total_harga","status_pembayaran"]
            detail_cols = [c for c in detail_cols if c in detail.columns]
            st.dataframe(detail[detail_cols], use_container_width=True, hide_index=True)

# ─── PAGE: DETAIL STOK ───────────────────────────────────────────────────────────
def page_detail_stok(df: pd.DataFrame):
    st.title("📦 Detail Stok — Kuantitas & Finansial")

    if df.empty:
        empty_state(
            "📦", "Belum Ada Data Stok",
            "Data stok akan muncul otomatis setelah transaksi pembelian dicatat."
        )
        return

    df["qty"]          = pd.to_numeric(df["qty"],          errors="coerce").fillna(0)
    df["harga_satuan"] = pd.to_numeric(df["harga_satuan"], errors="coerce").fillna(0)
    df["total_harga"]  = pd.to_numeric(df["total_harga"],  errors="coerce").fillna(0)

    st.subheader("💰 Ringkasan Finansial")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Pengeluaran",       f"Rp {df['total_harga'].sum():,.0f}")
    with c2: st.metric("Rata-rata per Transaksi", f"Rp {df['total_harga'].mean():,.0f}")
    with c3: st.metric("Transaksi Terbesar",      f"Rp {df['total_harga'].max():,.0f}")
    with c4: st.metric("Jenis Barang Unik",
                        df["nama_barang"].nunique() if "nama_barang" in df.columns else 0)

    st.markdown("---")
    col_kiri, col_kanan = st.columns(2)

    with col_kiri:
        st.subheader("📊 Akumulasi Stok per Barang")
        if "nama_barang" in df.columns and "uom" in df.columns:
            grp = df.groupby(["nama_barang","uom"]).agg(
                Total_Qty      =("qty",         "sum"),
                Total_Spend    =("total_harga", "sum"),
                Rata_Harga     =("harga_satuan","mean"),
                Jml_Transaksi  =("total_harga", "count"),
            ).reset_index()
            grp.columns = ["Nama Barang","UoM","Total Qty",
                           "Total Spend (Rp)","Rata-rata Harga (Rp)","Jml Transaksi"]
            st.dataframe(grp.sort_values("Total Spend (Rp)", ascending=False),
                         use_container_width=True, hide_index=True)

    with col_kanan:
        st.subheader("📈 Tren Harga Satuan")
        if "nama_barang" in df.columns and not df.empty:
            barang_list = sorted(df["nama_barang"].dropna().unique().tolist())
            pilih = st.selectbox("Pilih barang", barang_list, key="tren_pilih")
            tren = df[df["nama_barang"] == pilih][["tanggal","harga_satuan"]].copy()
            tren["tanggal"] = pd.to_datetime(tren["tanggal"], errors="coerce")
            tren = tren.dropna().sort_values("tanggal")
            if len(tren) >= 2:
                st.line_chart(
                    tren.rename(columns={"tanggal":"Tanggal","harga_satuan":"Harga Satuan (Rp)"})
                        .set_index("Tanggal")
                )
            elif len(tren) == 1:
                st.info("Baru 1 catatan harga. Butuh minimal 2 catatan untuk tren.")
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
    st.title("🔍 Kontrol & Audit — Quality Control & Arus Kas")

    if df.empty:
        empty_state(
            "🔍", "Belum Ada Data untuk Diaudit",
            "Data audit akan muncul setelah transaksi dicatat."
        )
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
                (df["tgl_kadaluarsa"].astype(str).str.strip() != "") &
                (df["tgl_kadaluarsa"].astype(str).str.strip() != "None")
            ].copy()

            if df_exp.empty:
                empty_state(
                    "📅", "Belum Ada Data Kadaluarsa",
                    "Isi kolom Tanggal Kadaluarsa saat mencatat transaksi bahan baku."
                )
            else:
                df_exp["tgl_kadaluarsa"] = pd.to_datetime(df_exp["tgl_kadaluarsa"], errors="coerce")
                today    = pd.Timestamp.today().normalize()
                kritis   = df_exp[df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=7)]
                mendekat = df_exp[
                    (df_exp["tgl_kadaluarsa"] > today + pd.Timedelta(days=7)) &
                    (df_exp["tgl_kadaluarsa"] <= today + pd.Timedelta(days=30))
                ]
                aman     = df_exp[df_exp["tgl_kadaluarsa"] > today + pd.Timedelta(days=30)]

                c1, c2, c3 = st.columns(3)
                c1.metric("🔴 Kritis (≤ 7 hari)",    len(kritis))
                c2.metric("🟡 Mendekat (8–30 hari)", len(mendekat))
                c3.metric("🟢 Aman (> 30 hari)",     len(aman))

                exp_cols = ["nama_barang","merk","qty","uom","tgl_kadaluarsa","catatan"]
                exp_cols = [c for c in exp_cols if c in df_exp.columns]

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
        with c1: st.metric("Total Keluar",              f"Rp {total_all:,.0f}")
        with c2: st.metric("✅ Sudah Lunas",             f"Rp {total_lunas:,.0f}")
        with c3: st.metric("⏳ Belum Lunas / Hutang",   f"Rp {total_hutang:,.0f}")

        st.markdown("---")
        st.subheader("📋 Transaksi Belum Lunas")
        belum = df[df["status_pembayaran"] != "Lunas"]
        if not belum.empty:
            bl_cols = ["tanggal","no_nota","supplier","nama_barang",
                       "total_harga","status_pembayaran","catatan"]
            bl_cols = [c for c in bl_cols if c in belum.columns]
            st.dataframe(
                belum[bl_cols].sort_values("tanggal") if "tanggal" in belum.columns else belum[bl_cols],
                use_container_width=True, hide_index=True
            )
            st.caption(f"Total hutang: **Rp {total_hutang:,.0f}**")
        else:
            st.success("🎉 Semua transaksi sudah berstatus Lunas!")

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

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            kat_f  = st.selectbox("Kategori", ["Semua"] + KATEGORI_OPTIONS, key="log_kat")
        with col_f2:
            sort_f = st.selectbox("Urutkan berdasarkan",
                                  ["tanggal","total_harga","supplier","nama_barang"],
                                  key="log_sort")
        with col_f3:
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