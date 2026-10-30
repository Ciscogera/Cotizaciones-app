import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Generador de Cotizaciones - El Bajo", layout="wide")

# --- COLORES BASE ---
COLOR_TEXT_BLACK = (18 / 255, 18 / 255, 16 / 255)
COLOR_TEXT_GRAY = (115 / 255, 110 / 255, 100 / 255)
COLOR_HEADER_META = (184 / 255, 179 / 255, 168 / 255)
COLOR_GOLD = (221 / 255, 160 / 255, 50 / 255)
COLOR_LINE_GRAY = (214 / 255, 209 / 255, 196 / 255)


def formato_clp(valor: int) -> str:
    return f"${valor:,.0f}".replace(",", ".")


def muestrear_color_pdf(page, x: float, y: float) -> tuple:
    pix = page.get_pixmap(clip=fitz.Rect(x, y, x + 2, y + 2))
    r, g, b = pix.pixel(0, 0)[:3]
    return (r / 255.0, g / 255.0, b / 255.0)


def envolver_texto(texto: str, font_obj, font_size: float, ancho_max: float) -> list:
    lineas_resultado = []
    for parrafo in texto.split("\n"):
        palabras = parrafo.split(" ")
        linea_actual = ""
        for p in palabras:
            prueba = f"{linea_actual} {p}".strip()
            if font_obj.text_length(prueba, fontsize=font_size) <= ancho_max:
                linea_actual = prueba
            else:
                if linea_actual:
                    lineas_resultado.append(linea_actual)
                linea_actual = p
        if linea_actual:
            lineas_resultado.append(linea_actual)
    return lineas_resultado


def simular_altura_pildoras(ancho_max, items, font_obj, font_size):
    """Calcula cuántas filas y alto ocuparán las cápsulas sin dibujarlas."""
    if not items:
        return 0
    x_actual = 0
    filas = 1
    pad_x = 10
    pad_y = 4.5
    alto_pildora = font_size + (pad_y * 2)
    espacio_x = 6
    espacio_y = 6

    for item in items:
        texto = item.strip()
        if not texto:
            continue
        ancho_pildora = font_obj.text_length(texto, fontsize=font_size) + (pad_x * 2)
        if x_actual + ancho_pildora > ancho_max and x_actual > 0:
            x_actual = 0
            filas += 1
        x_actual += ancho_pildora + espacio_x

    return filas * (alto_pildora + espacio_y)


def dibujar_pildoras(page, x_inicio, y_inicio, ancho_max, items, font_obj, font_name, font_size, bg_cream):
    x_actual = x_inicio
    y_actual = y_inicio
    pad_x = 10
    pad_y = 4.5
    alto_pildora = font_size + (pad_y * 2)
    espacio_x = 6
    espacio_y = 6

    for item in items:
        texto = item.strip()
        if not texto:
            continue
        ancho_pildora = font_obj.text_length(texto, fontsize=font_size) + (pad_x * 2)

        if x_actual + ancho_pildora > x_inicio + ancho_max and x_actual > x_inicio:
            x_actual = x_inicio
            y_actual += alto_pildora + espacio_y

        rect_pildora = fitz.Rect(x_actual, y_actual, x_actual + ancho_pildora, y_actual + alto_pildora)
        page.draw_rect(rect_pildora, color=COLOR_TEXT_BLACK, fill=bg_cream, width=1.0, radius=0.48)
        page.insert_text(fitz.Point(x_actual + pad_x, y_actual + pad_y + font_size * 0.82), texto, fontname=font_name, fontsize=font_size, color=COLOR_TEXT_BLACK)
        x_actual += ancho_pildora + espacio_x

    return y_actual + alto_pildora


def insertar_texto_derecha(page, x_derecha, y_base, texto, font_obj, font_name, font_size, color):
    ancho = font_obj.text_length(texto, fontsize=font_size)
    page.insert_text(fitz.Point(x_derecha - ancho, y_base), texto, fontname=font_name, fontsize=font_size, color=color)


# --- ESTADO INICIAL ---
if "comidas" not in st.session_state:
    st.session_state.comidas = [
        {"titulo": "Rodizio de pizzas · 15 pizzas", "pildoras": "Zócalo, Palta, Porteña, Del Bosque, Vegetariana"}
    ]

if "bebestibles" not in st.session_state:
    st.session_state.bebestibles = [
        {"cant": "60", "titulo": "Botellines de cerveza", "desc": "Royal Guard y Heineken"},
        {"cant": "25", "titulo": "Bebestibles sin alcohol", "desc": "Jugo del día, bebidas y agua mineral\ncon o sin gas"}
    ]

if "valores_items" not in st.session_state:
    st.session_state.valores_items = [
        {"concepto": "Servicio de alimentos y bebestibles", "nota": "(IVA incluido)", "monto": 500000},
        {"concepto": "Técnica · sonidista", "nota": "", "monto": 70000}
    ]


# --- INTERFAZ STREAMLIT ---
st.title("Generador de Cotizaciones · El Bajo")

with st.sidebar:
    st.header("1. Plantilla Base y Fuentes")
    pdf_base = st.file_uploader("Sube el PDF original de referencia", type=["pdf"])

    st.markdown("---")
    st.subheader("Tipografías (.ttf / .otf)")
    font_regular_file = st.file_uploader("Fuente Cuerpo Regular", type=["ttf", "otf"])
    font_bold_file = st.file_uploader("Fuente Cuerpo Negrita (Bold)", type=["ttf", "otf"])
    font_display_file = st.file_uploader("Fuente Números/Títulos (Display Black)", type=["ttf", "otf"])


col_form, col_preview = st.columns([1.15, 1])

with col_form:
    st.subheader("Datos de Cabecera y Evento")
    c1, c2 = st.columns(2)
    with c1:
        num_cotizacion = st.text_input("N.º Cotización", value="[001]")
        fecha_evento = st.text_input("FECHA", value="Jue 29 oct 2026")
        invitados = st.text_input("INVITADOS", value="40 aprox.")
    with c2:
        fecha_emision = st.text_input("Fecha de Emisión", value="21/10/2026")
        horario = st.text_input("HORARIO", value="PM · [hora]")
        espacio = st.text_area("ESPACIO (usa Enter para 2 líneas)", value="Terraza exclusiva\nT4", height=68)

    st.markdown("---")
    col_c_head, col_c_btn = st.columns([3, 1])
    with col_c_head:
        st.subheader("01 COMIDA")
    with col_c_btn:
        if st.button("+ Agregar Comida", use_container_width=True):
            st.session_state.comidas.append({"titulo": "", "pildoras": ""})
            st.rerun()

    formato_comida = st.text_input("Subtítulo Formato", value="FORMATO CÓCTEL")

    for idx, item_c in enumerate(st.session_state.comidas):
        with st.container(border=True):
            cc1, cc2 = st.columns([5, 1])
            with cc1:
                st.session_state.comidas[idx]["titulo"] = st.text_input(f"Plato #{idx + 1}", value=item_c["titulo"], key=f"com_tit_{idx}")
                st.session_state.comidas[idx]["pildoras"] = st.text_input(f"Variedades #{idx + 1} (separadas por coma)", value=item_c["pildoras"], key=f"com_pil_{idx}")
            with cc2:
                st.write("")
                st.write("")
                if len(st.session_state.comidas) > 1:
                    if st.button("Quitar", key=f"del_com_{idx}", use_container_width=True):
                        st.session_state.comidas.pop(idx)
                        st.rerun()

    st.markdown("---")
    col_b_head, col_b_btn = st.columns([3, 1])
    with col_b_head:
        st.subheader("02 BEBESTIBLES")
    with col_b_btn:
        if st.button("+ Agregar Bebestible", use_container_width=True):
            st.session_state.bebestibles.append({"cant": "10", "titulo": "", "desc": ""})
            st.rerun()

    for idx, item_b in enumerate(st.session_state.bebestibles):
        with st.container(border=True):
            bc1, bc2, bc3, bc4 = st.columns([1.2, 2.5, 3, 1])
            with bc1:
                st.session_state.bebestibles[idx]["cant"] = st.text_input("Cant", value=item_b["cant"], key=f"beb_cant_{idx}")
            with bc2:
                st.session_state.bebestibles[idx]["titulo"] = st.text_input("Ítem", value=item_b["titulo"], key=f"beb_tit_{idx}")
            with bc3:
                st.session_state.bebestibles[idx]["desc"] = st.text_area("Detalle", value=item_b["desc"], key=f"beb_desc_{idx}", height=68)
            with bc4:
                st.write("")
                st.write("")
                if len(st.session_state.bebestibles) > 1:
                    if st.button("Quitar", key=f"del_beb_{idx}", use_container_width=True):
                        st.session_state.bebestibles.pop(idx)
                        st.rerun()

    st.markdown("---")
    col_v_head, col_v_btn = st.columns([3, 1])
    with col_v_head:
        st.subheader("03 VALORES")
    with col_v_btn:
        if st.button("+ Agregar Cobro", use_container_width=True):
            st.session_state.valores_items.append({"concepto": "", "nota": "", "monto": 0})
            st.rerun()

    for idx, item_v in enumerate(st.session_state.valores_items):
        vc1, vc2, vc3, vc4 = st.columns([3, 2, 2, 1])
        with vc1:
            st.session_state.valores_items[idx]["concepto"] = st.text_input(f"Concepto #{idx + 1}", value=item_v["concepto"], key=f"val_con_{idx}")
        with vc2:
            st.session_state.valores_items[idx]["nota"] = st.text_input("Nota gris", value=item_v["nota"], key=f"val_not_{idx}")
        with vc3:
            st.session_state.valores_items[idx]["monto"] = st.number_input("Monto ($)", value=int(item_v["monto"]), step=10000, key=f"val_mon_{idx}")
        with vc4:
            st.write("")
            st.write("")
            if len(st.session_state.valores_items) > 1:
                if st.button("X", key=f"del_val_{idx}", use_container_width=True):
                    st.session_state.valores_items.pop(idx)
                    st.rerun()

    st.markdown("##### Propina")
    vp1, vp2, vp3 = st.columns([2, 2, 2])
    with vp1:
        incluir_propina = st.checkbox("Incluir línea de propina", value=True)
    with vp2:
        propina_auto = st.checkbox("Calcular 10% automático", value=True, disabled=not incluir_propina)
    with vp3:
        base_propina = st.session_state.valores_items[0]["monto"] if st.session_state.valores_items else 0
        val_propina_def = int(base_propina * 0.10) if propina_auto else 50000
        monto_propina = st.number_input("Monto Propina ($)", value=val_propina_def, step=5000, disabled=(not incluir_propina or propina_auto))

    subtotal_items = sum(i["monto"] for i in st.session_state.valores_items)
    total_evento = subtotal_items + (monto_propina if incluir_propina else 0)
    st.markdown(f"**TOTAL EVENTO:** `{formato_clp(total_evento)}`")


# --- PROCESAMIENTO DEL PDF ---
if pdf_base is not None:
    raw_pdf_bytes = pdf_base.getvalue()
    doc = fitz.open(stream=raw_pdf_bytes, filetype="pdf")
    page = doc[0]
    W, H = page.rect.width, page.rect.height

    COLOR_BG_BLACK = muestrear_color_pdf(page, W * 0.50, 15)
    COLOR_BG_CREAM = muestrear_color_pdf(page, W * 0.50, H * 0.90)

    # Configurar fuentes
    fname_reg = "F_Reg" if font_regular_file else "helv"
    if font_regular_file:
        page.insert_font(fontname=fname_reg, fontbuffer=font_regular_file.getvalue())
    font_obj_reg = fitz.Font(fontbuffer=font_regular_file.getvalue()) if font_regular_file else fitz.Font("helv")

    fname_bold = "F_Bold" if font_bold_file else "hebo"
    if font_bold_file:
        page.insert_font(fontname=fname_bold, fontbuffer=font_bold_file.getvalue())
    font_obj_bold = fitz.Font(fontbuffer=font_bold_file.getvalue()) if font_bold_file else fitz.Font("hebo")

    fname_disp = "F_Disp" if font_display_file else fname_bold
    if font_display_file:
        page.insert_font(fontname=fname_disp, fontbuffer=font_display_file.getvalue())
    font_obj_disp = fitz.Font(fontbuffer=font_display_file.getvalue()) if font_display_file else font_obj_bold

    # 1. CABECERA
    r_emitida = page.search_for("Emitida")
    if r_emitida:
        y_meta = r_emitida[0].y1 - 1.5
        page.draw_rect(fitz.Rect(W * 0.55, r_emitida[0].y0 - 3, W * 0.95, r_emitida[0].y1 + 3), color=COLOR_BG_BLACK, fill=COLOR_BG_BLACK)
        insertar_texto_derecha(page, W * 0.931, y_meta, f"N.º {num_cotizacion} · Emitida {fecha_emision}", font_obj_reg, fname_reg, 9.5, COLOR_HEADER_META)

    # 2. GRILLA DE 4 COLUMNAS
    r_fecha_lbl = page.search_for("FECHA")
    r_horario_lbl = page.search_for("HORARIO")
    r_inv_lbl = page.search_for("INVITADOS")
    r_esp_lbl = page.search_for("ESPACIO")

    if r_fecha_lbl and r_horario_lbl and r_inv_lbl and r_esp_lbl:
        y_top_val = r_fecha_lbl[0].y1 + 4
        y_base_val = r_fecha_lbl[0].y1 + 17

        page.draw_rect(fitz.Rect(r_fecha_lbl[0].x0 - 2, y_top_val, r_horario_lbl[0].x0 - 15, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
        page.draw_rect(fitz.Rect(r_horario_lbl[0].x0 - 2, y_top_val, r_inv_lbl[0].x0 - 15, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
        page.draw_rect(fitz.Rect(r_inv_lbl[0].x0 - 2, y_top_val, r_esp_lbl[0].x0 - 15, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
        page.draw_rect(fitz.Rect(r_esp_lbl[0].x0 - 2, y_top_val, W * 0.94, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)

        page.insert_text(fitz.Point(r_fecha_lbl[0].x0, y_base_val), fecha_evento, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)
        page.insert_text(fitz.Point(r_horario_lbl[0].x0, y_base_val), horario, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)
        page.insert_text(fitz.Point(r_inv_lbl[0].x0, y_base_val), invitados, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)

        for idx, lin in enumerate(espacio.split("\n")[:2]):
            page.insert_text(fitz.Point(r_esp_lbl[0].x0, y_base_val + (idx * 14)), lin, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)

    # 3. SECCIÓN 01 COMIDA Y 02 BEBESTIBLES
    r_comida = page.search_for("COMIDA")
    r_bebestibles = page.search_for("BEBESTIBLES")
    r_valores = page.search_for("VALORES")

    if r_comida and r_bebestibles and r_valores:
        rects_01 = [r for r in page.search_for("01") if abs(r.y0 - r_comida[0].y0) < 15]
        rects_02 = [r for r in page.search_for("02") if abs(r.y0 - r_bebestibles[0].y0) < 15]

        x_col1 = rects_01[0].x0 if rects_01 else (r_fecha_lbl[0].x0 if r_fecha_lbl else W * 0.068)
        x_col2 = rects_02[0].x0 if rects_02 else (r_bebestibles[0].x0 - 22)
        x_der = W * 0.931

        ancho_max_col1 = (x_col2 - x_col1) - 24
        y_inicio_secciones = r_comida[0].y1 + 8
        y_original_valores = r_valores[0].y0

        # --- CÁLCULO PREVIO DE ALTURAS PARA COMIDA Y BEBESTIBLES ---
        y_cursor_c_sim = y_inicio_secciones
        if formato_comida.strip():
            y_cursor_c_sim += 20
        for item_c in st.session_state.comidas:
            tit = item_c["titulo"].strip()
            pils = [p.strip() for p in item_c["pildoras"].split(",") if p.strip()]
            if tit:
                num_lineas_t = len(envolver_texto(tit, font_obj_bold, 12.0, ancho_max_col1))
                y_cursor_c_sim += num_lineas_t * 16 + 4
            if pils:
                y_cursor_c_sim += 12 + simular_altura_pildoras(ancho_max_col1, pils, font_obj_reg, 9.5)
            y_cursor_c_sim += 14

        y_cursor_b_sim = y_inicio_secciones + 4
        ancho_max_texto_beb = x_der - (x_col2 + 46)
        items_beb_validos = [b for b in st.session_state.bebestibles if b["cant"].strip() or b["titulo"].strip() or b["desc"].strip()]
        for item_b in items_beb_validos:
            tit_b = item_b["titulo"].strip()
            desc_b = item_b["desc"].strip()
            altura_bloque_b = 26
            if tit_b:
                altura_bloque_b += len(envolver_texto(tit_b, font_obj_bold, 10.0, ancho_max_texto_beb)) * 13
            if desc_b:
                altura_bloque_b += len(envolver_texto(desc_b, font_obj_reg, 9.8, ancho_max_texto_beb)) * 13
            y_cursor_b_sim += altura_bloque_b + 14

        # Determinar nueva posición de VALORES basada en el contenido real
        y_max_contenido = max(y_cursor_c_sim, y_cursor_b_sim)
        y_nuevo_valores = max(y_original_valores, y_max_contenido + 10)
        desplazamiento_y = y_nuevo_valores - y_original_valores

        # LIMPIAR COMPLETAMENTE TODO EL BLOQUE CENTRAL SUPERIOR E INTERMEDIO
        page.draw_rect(fitz.Rect(0, y_inicio_secciones - 4, W, H * 0.85), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)

        # --- DIBUJAR 01 COMIDA ---
        y_cursor_c = y_inicio_secciones
        if formato_comida.strip():
            y_cursor_c += 12
            page.insert_text(fitz.Point(x_col1, y_cursor_c), " ".join(list(formato_comida.strip().upper())), fontname=fname_reg, fontsize=7.5, color=COLOR_TEXT_GRAY)
            y_cursor_c += 8

        for idx, item_c in enumerate(st.session_state.comidas):
            tit = item_c["titulo"].strip()
            pils = [p.strip() for p in item_c["pildoras"].split(",") if p.strip()]

            if tit:
                for l_tit in envolver_texto(tit, font_obj_bold, 12.0, ancho_max_col1):
                    y_cursor_c += 16
                    page.insert_text(fitz.Point(x_col1, y_cursor_c), l_tit, fontname=fname_bold, fontsize=12.0, color=COLOR_TEXT_BLACK)

            if pils:
                y_cursor_c += 12
                y_cursor_c = dibujar_pildoras(page, x_col1, y_cursor_c, ancho_max_col1, pils, font_obj_reg, fname_reg, 9.5, COLOR_BG_CREAM)

            if idx < len(st.session_state.comidas) - 1 and (tit or pils):
                y_cursor_c += 10
                page.draw_line(fitz.Point(x_col1, y_cursor_c), fitz.Point(x_col1 + ancho_max_col1, y_cursor_c), color=COLOR_LINE_GRAY, width=0.8)
                y_cursor_c += 4

        # --- DIBUJAR 02 BEBESTIBLES ---
        y_cursor_b = y_inicio_secciones + 4
        x_texto_beb = x_col2 + 46

        for idx, item_b in enumerate(items_beb_validos):
            cant_str = item_b["cant"].strip()
            tit_b = item_b["titulo"].strip()
            desc_b = item_b["desc"].strip()

            y_num_base = y_cursor_b + 21
            page.insert_text(fitz.Point(x_col2, y_num_base), cant_str, fontname=fname_disp, fontsize=20, color=COLOR_TEXT_BLACK)

            y_txt_b = y_cursor_b + 12
            if tit_b:
                for l_tb in envolver_texto(tit_b, font_obj_bold, 10.0, ancho_max_texto_beb):
                    page.insert_text(fitz.Point(x_texto_beb, y_txt_b), l_tb, fontname=fname_bold, fontsize=10.0, color=COLOR_TEXT_BLACK)
                    y_txt_b += 13

            if desc_b:
                for l_db in envolver_texto(desc_b, font_obj_reg, 9.8, ancho_max_texto_beb):
                    page.insert_text(fitz.Point(x_texto_beb, y_txt_b), l_db, fontname=fname_reg, fontsize=9.8, color=COLOR_TEXT_BLACK)
                    y_txt_b += 13

            y_cursor_b = max(y_num_base + 6, y_txt_b - 4)

            if idx < len(items_beb_validos) - 1:
                y_cursor_b += 8
                page.draw_line(fitz.Point(x_col2, y_cursor_b), fitz.Point(x_der, y_cursor_b), color=COLOR_LINE_GRAY, width=0.8)
                y_cursor_b += 6

        # --- 4. RENDERIZAR 03 VALORES Y BLOQUE INFERIOR DESPLAZADOS ---
        doc_orig = fitz.open(stream=raw_pdf_bytes, filetype="pdf")

        # Estampar el título original "03 VALORES" y su línea superior en la nueva posición calculada
        page.show_pdf_page(fitz.Rect(0, y_nuevo_valores - 4, W, y_nuevo_valores + 28), doc_orig, 0, clip=fitz.Rect(0, y_original_valores - 4, W, y_original_valores + 28))

        filas_valores = [(v["concepto"].strip(), v["nota"].strip(), v["monto"]) for v in st.session_state.valores_items if v["concepto"].strip() or v["monto"] > 0]
        if incluir_propina:
            filas_valores.append(("Propina sugerida 10%", "", monto_propina))

        r_total_lbl_orig = doc_orig[0].search_for("TOTAL EVENTO")[0]
        y_caja_negra_orig_top = r_total_lbl_orig.y0 - 17

        y_inicio_filas_val = y_nuevo_valores + r_valores[0].height + 14
        alto_fila_val = 28
        y_caja_negra_nuevo_top = max(y_caja_negra_orig_top + desplazamiento_y, y_inicio_filas_val + (len(filas_valores) * alto_fila_val) + 6)

        # Dibujar filas de valores
        y_fila = y_inicio_filas_val + 16
        for idx, (concepto, nota, monto) in enumerate(filas_valores):
            page.insert_text(fitz.Point(x_col1, y_fila), concepto, fontname=fname_reg, fontsize=10.5, color=COLOR_TEXT_BLACK)
            if nota:
                page.insert_text(fitz.Point(x_col1 + font_obj_reg.text_length(concepto + " ", fontsize=10.5), y_fila), nota, fontname=fname_reg, fontsize=10.5, color=COLOR_TEXT_GRAY)

            insertar_texto_derecha(page, x_der, y_fila, formato_clp(monto), font_obj_bold, fname_bold, 11, COLOR_TEXT_BLACK)

            if idx < len(filas_valores) - 1:
                page.draw_line(fitz.Point(x_col1, y_fila + 10), fitz.Point(x_der, y_fila + 10), color=COLOR_LINE_GRAY, width=0.8)
            y_fila += alto_fila_val

        # Estampar bloque inferior completo (Total, Forma de pago, Transferencia) en la nueva posición
        page.show_pdf_page(fitz.Rect(0, y_caja_negra_nuevo_top, W, y_caja_negra_nuevo_top + ((H * 0.80) - y_caja_negra_orig_top)), doc_orig, 0, clip=fitz.Rect(0, y_caja_negra_orig_top, W, H * 0.80))

        # Actualizar monto total en la franja negra
        offset_inf = y_caja_negra_nuevo_top - y_caja_negra_orig_top
        y_tot_top = r_total_lbl_orig.y0 + offset_inf
        y_tot_bot = r_total_lbl_orig.y1 + offset_inf
        page.draw_rect(fitz.Rect(W * 0.55, y_tot_top - 10, x_der - 8, y_tot_bot + 10), color=COLOR_BG_BLACK, fill=COLOR_BG_BLACK)
        insertar_texto_derecha(page, x_der - 16, y_tot_bot + 3, formato_clp(total_evento), font_obj_disp, fname_disp, 22, COLOR_GOLD)
        doc_orig.close()

    # Vista previa
    pix = page.get_pixmap(dpi=200)
    pdf_out = io.BytesIO()
    doc.save(pdf_out)
    doc.close()

    with col_preview:
        st.subheader("Vista Previa en Tiempo Real")
        st.download_button("Descargar Cotización en PDF", data=pdf_out.getvalue(), file_name=f"Cotizacion_El_Bajo_{num_cotizacion.strip('[]')}.pdf", mime="application/pdf", use_container_width=True)
        st.image(pix.tobytes("png"), use_container_width=True)
else:
    with col_preview:
        st.info("Sube el archivo PDF original en el menú izquierdo para comenzar.")