import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Simple Sales App", layout="wide")
st.title("🛒 Aplikasi Penjualan Sederhana")

# --------- Initialization in session state ----------
if "products" not in st.session_state:
    # sample products
    st.session_state.products = pd.DataFrame([
        {"id": "P001", "name": "Kopi Arabika 250g", "price": 75000.0, "stock": 10},
        {"id": "P002", "name": "Teh Hijau 200g", "price": 45000.0, "stock": 15},
        {"id": "P003", "name": "Roti Tawar", "price": 20000.0, "stock": 30},
    ])

if "cart" not in st.session_state:
    st.session_state.cart = []  # each item: {"id","name","price","qty","line_total"}

if "sales" not in st.session_state:
    st.session_state.sales = []  # list of invoices (dicts)

# --------- Sidebar: Add new product ----------
st.sidebar.header("Tambah produk baru")
with st.sidebar.form("add_product_form", clear_on_submit=True):
    new_name = st.text_input("Nama produk")
    new_price = st.number_input("Harga (Rp)", min_value=0.0, value=10000.0, step=1000.0, format="%.2f")
    new_stock = st.number_input("Stok", min_value=0, value=10, step=1)
    submitted = st.form_submit_button("Tambah produk")
    if submitted:
        if not new_name.strip():
            st.sidebar.error("Nama produk tidak boleh kosong.")
        else:
            new_id = f"P{str(len(st.session_state.products) + 1).zfill(3)}"
            st.session_state.products = pd.concat([
                st.session_state.products,
                pd.DataFrame([{"id": new_id, "name": new_name.strip(), "price": float(new_price), "stock": int(new_stock)}])
            ], ignore_index=True)
            st.sidebar.success(f"Produk {new_name} ditambahkan (ID: {new_id}).")

st.sidebar.markdown("---")
st.sidebar.subheader("Keranjang")
if st.sidebar.button("Kosongkan keranjang"):
    st.session_state.cart = []
    st.sidebar.success("Keranjang dikosongkan.")

# --------- Main layout: two columns ----------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Katalog produk")
    products = st.session_state.products.copy()
    products_display = products[["id", "name", "price", "stock"]].rename(columns={
        "id": "ID", "name": "Nama", "price": "Harga (Rp)", "stock": "Stok"
    })
    st.dataframe(products_display, use_container_width=True)

    st.markdown("**Tambah ke keranjang**")
    product_choice = st.selectbox("Pilih produk", options=products["id"].tolist(),
                                  format_func=lambda pid: f"{pid} — {products.loc[products['id']==pid, 'name'].values[0]}")
    chosen_row = products.loc[products["id"] == product_choice].iloc[0]
    qty = st.number_input("Jumlah", min_value=1, max_value=int(chosen_row["stock"]), value=1, step=1)
    if st.button("Tambah ke keranjang"):
        line_total = round(chosen_row["price"] * qty, 2)
        st.session_state.cart.append({
            "id": chosen_row["id"],
            "name": chosen_row["name"],
            "price": float(chosen_row["price"]),
            "qty": int(qty),
            "line_total": line_total
        })
        st.success(f"{qty} x {chosen_row['name']} ditambahkan ke keranjang.")

    st.markdown("---")
    st.subheader("Keranjang (preview)")
    if not st.session_state.cart:
        st.info("Keranjang kosong. Tambah produk dari katalog.")
    else:
        cart_df = pd.DataFrame(st.session_state.cart)
        cart_df_display = cart_df[["id", "name", "price", "qty", "line_total"]].rename(columns={
            "id":"ID","name":"Nama","price":"Harga (Rp)", "qty":"Qty", "line_total":"Subtotal (Rp)"
        })
        st.dataframe(cart_df_display, use_container_width=True)

        # allow remove items
        to_remove = st.multiselect("Pilih ID untuk dihapus dari keranjang", options=cart_df["id"].tolist())
        if st.button("Hapus terpilih dari keranjang"):
            if to_remove:
                st.session_state.cart = [i for i in st.session_state.cart if i["id"] not in to_remove]
                st.success("Item terhapus.")
            else:
                st.warning("Pilih minimal satu item untuk dihapus.")

with col2:
    st.subheader("Checkout")
    if not st.session_state.cart:
        st.info("Keranjang kosong — tidak bisa checkout.")
    else:
        cart_df = pd.DataFrame(st.session_state.cart)
        subtotal = cart_df["line_total"].sum()
        st.write(f"Subtotal: Rp {subtotal:,.2f}")

        tax_pct = st.number_input("Pajak (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, format="%.2f")
        discount = st.number_input("Diskon (Rp)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")

        tax_amount = round(subtotal * tax_pct / 100.0, 2)
        total = round(subtotal + tax_amount - float(discount), 2)
        if total < 0:
            st.error("Total negatif — cek diskon.")
        st.write(f"Pajak: Rp {tax_amount:,.2f}")
        st.write(f"Diskon: Rp {discount:,.2f}")
        st.markdown(f"**Total bayar: Rp {total:,.2f}**")

        buyer = st.text_input("Nama pembeli (opsional)", value="Pelanggan")
        if st.button("Proses pembayaran / Buat invoice"):
            invoice_id = str(uuid.uuid4())[:8]
            invoice_date = datetime.now().isoformat(timespec='seconds')
            invoice_items = cart_df.copy()
            invoice_items["invoice_id"] = invoice_id
            invoice_items["date"] = invoice_date

            invoice_record = {
                "invoice_id": invoice_id,
                "date": invoice_date,
                "buyer": buyer,
                "subtotal": float(subtotal),
                "tax_pct": float(tax_pct),
                "tax_amount": float(tax_amount),
                "discount": float(discount),
                "total": float(total),
                "items": invoice_items  # DataFrame
            }
            st.session_state.sales.append(invoice_record)

            # decrement stock in products
            for it in st.session_state.cart:
                idx = st.session_state.products.index[st.session_state.products["id"] == it["id"]]
                if len(idx) > 0:
                    i = idx[0]
                    st.session_state.products.at[i, "stock"] = max(0, int(st.session_state.products.at[i, "stock"] - it["qty"]))
            st.session_state.cart = []  # clear cart
            st.success(f"Invoice {invoice_id} dibuat — Total Rp {total:,.2f}")

# --------- Sales history and exports ----------
st.markdown("---")
st.subheader("Riwayat penjualan")
if not st.session_state.sales:
    st.info("Belum ada penjualan.")
else:
    # summary table
    sales_summary = pd.DataFrame([{
        "invoice_id": s["invoice_id"],
        "date": s["date"],
        "buyer": s.get("buyer", ""),
        "total": s["total"]
    } for s in st.session_state.sales])
    st.dataframe(sales_summary.sort_values("date", ascending=False), use_container_width=True)

    # download full sales (items) as CSV
    all_items = pd.concat([s["items"] for s in st.session_state.sales], ignore_index=True)
    all_items = all_items[["invoice_id", "date", "id", "name", "price", "qty", "line_total"]]
    csv_bytes = all_items.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Unduh semua item penjualan (CSV)", data=csv_bytes, file_name="sales_items.csv", mime="text/csv")

    # allow selecting an invoice to view details and download invoice CSV
    sel = st.selectbox("Pilih invoice untuk detail", options=[s["invoice_id"] for s in st.session_state.sales])
    selected = next(s for s in st.session_state.sales if s["invoice_id"] == sel)
    st.markdown(f"**Invoice**: {selected['invoice_id']}  •  Tanggal: {selected['date']}  •  Buyer: {selected.get('buyer','')}")
    st.dataframe(selected["items"][["id", "name", "price", "qty", "line_total"]], use_container_width=True)

    # prepare invoice CSV downloadable
    buf = BytesIO()
    inv_df = selected["items"][["id", "name", "price", "qty", "line_total"]].copy()
    footer = pd.DataFrame([{"id": "", "name": "Subtotal", "price": "", "qty": "", "line_total": selected["subtotal"]},
                           {"id": "", "name": f"Pajak ({selected['tax_pct']}%)", "price": "", "qty": "", "line_total": selected["tax_amount"]},
                           {"id": "", "name": "Diskon", "price": "", "qty": "", "line_total": selected["discount"]},
                           {"id": "", "name": "Total", "price": "", "qty": "", "line_total": selected["total"]}])
    out = pd.concat([inv_df, footer], ignore_index=True)
    out.to_csv(buf, index=False)
    st.download_button("⬇️ Unduh invoice (CSV)", data=buf.getvalue(), file_name=f"invoice_{selected['invoice_id']}.csv", mime="text/csv")

    # simple sales by product chart
    st.markdown("**Ringkasan: Penjualan per produk**")
    sold = all_items.groupby("name")["qty"].sum().sort_values(ascending=False)
    st.bar_chart(sold)

st.caption("Aplikasi demo: sederhana, cocok untuk latihan/keperluan jualan kecil. Untuk produksi butuh penyimpanan permanen (DB) dan autentikasi.")
