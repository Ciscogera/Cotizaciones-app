import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Generador de Cotizaciones - El Bajo", layout="wide")

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

    st.markdown("---")
    st.subheader("Observaciones / Comentarios (Opcional)")
    observaciones = st.text_area(
        "Texto de observaciones para el cliente",
        value="",
        placeholder="Ej: El horario de término es a las 02:00 hrs. Monto no reembolsable en caso de cancelación con menos de 48 hrs.",
        height=85
    )


# --- PROCESAMIENTO DEL PDF ---
if pdf_base is not None:
    raw_pdf_bytes = pdf_base.getvalue()
    doc = fitz.open(stream=raw_pdf_bytes, filetype="pdf")
    page1 = doc[0]
    W, H = page1.rect.width, page1.rect.height

    COLOR_BG_BLACK = muestrear_color_pdf(page1, W * 0.50, 15)
    COLOR_BG_CREAM = muestrear_color_pdf(page1, W * 0.50, H * 0.90)

    # Configuración de fuentes
    fname_reg = "F_Reg" if font_regular_file else "helv"
    fname_bold = "F_Bold" if font_bold_file else "hebo"
    fname_disp = "F_Disp" if font_display_file else fname_bold

    def registrar_fuentes_en_pagina(p):
        if font_regular_file:
            p.insert_font(fontname=fname_reg, fontbuffer=font_regular_file.getvalue())
        if font_bold_file:
            p.insert_font(fontname=fname_bold, fontbuffer=font_bold_file.getvalue())
        if font_display_file:
            p.insert_font(fontname=fname_disp, fontbuffer=font_display_file.getvalue())

    registrar_fuentes_en_pagina(page1)

    font_obj_reg = fitz.Font(fontbuffer=font_regular_file.getvalue()) if font_regular_file else fitz.Font("helv")
    font_obj_bold = fitz.Font(fontbuffer=font_bold_file.getvalue()) if font_bold_file else fitz.Font("hebo")
    font_obj_disp = fitz.Font(fontbuffer=font_display_file.getvalue()) if font_display_file else font_obj_bold

    # 1. Cabecera en Página 1
    r_emitida = page1.search_for("Emitida")
    if r_emitida:
        y_meta = r_emitida[0].y1 - 1.5
        page1.draw_rect(fitz.Rect(W * 0.55, r_emitida[0].y0 - 3, W * 0.95, r_emitida[0].y1 + 3), color=COLOR_BG_BLACK, fill=COLOR_BG_BLACK)
        insertar_texto_derecha(page1, W * 0.931, y_meta, f"N.º {num_cotizacion} · Emitida {fecha_emision}", font_obj_reg, fname_reg, 9.5, COLOR_HEADER_META)

    # 2. Grilla 4 columnas en Página 1
    r_fecha_lbl = page1.search_for("FECHA")
    r_horario_lbl = page1.search_for("HORARIO")
    r_inv_lbl = page1.search_for("INVITADOS")
    r_esp_lbl = page1.search_for("ESPACIO")

    if r_fecha_lbl and r_horario_lbl and r_inv_lbl and r_esp_lbl:
        y_top_val = r_fecha_lbl[0].y1 + 4
        y_base_val = r_fecha_lbl[0].y1 + 17

        page1.draw_rect(fitz.Rect(r_fecha_lbl[0].x0 - 2, y_top_val, r_horario_lbl[0].x0 - 15, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
        page1.draw_rect(fitz.Rect(r_horario_lbl[0].x0 - 2, y_top_val, r_inv_lbl[0].x0 - 15, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
        page1.draw_rect(fitz.Rect(r_inv_lbl[0].x0 - 2, y_top_val, r_esp_lbl[0].x0 - 15, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
        page1.draw_rect(fitz.Rect(r_esp_lbl[0].x0 - 2, y_top_val, W * 0.94, y_top_val + 38), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)

        page1.insert_text(fitz.Point(r_fecha_lbl[0].x0, y_base_val), fecha_evento, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)
        page1.insert_text(fitz.Point(r_horario_lbl[0].x0, y_base_val), horario, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)
        page1.insert_text(fitz.Point(r_inv_lbl[0].x0, y_base_val), invitados, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)

        for idx, lin in enumerate(espacio.split("\n")[:2]):
            page1.insert_text(fitz.Point(r_esp_lbl[0].x0, y_base_val + (idx * 14)), lin, fontname=fname_bold, fontsize=11.5, color=COLOR_TEXT_BLACK)

    # 3. Posicionamiento dinámico multicanal
    r_comida = page1.search_for("COMIDA")
    r_bebestibles = page1.search_for("BEBESTIBLES")
    r_valores = page1.search_for("VALORES")

    if r_comida and r_bebestibles and r_valores:
        rects_01 = [r for r in page1.search_for("01") if abs(r.y0 - r_comida[0].y0) < 15]
        rects_02 = [r for r in page1.search_for("02") if abs(r.y0 - r_bebestibles[0].y0) < 15]

        x_col1 = rects_01[0].x0 if rects_01 else (r_fecha_lbl[0].x0 if r_fecha_lbl else W * 0.068)
        x_col2 = rects_02[0].x0 if rects_02 else (r_bebestibles[0].x0 - 22)
        x_der = W * 0.931
        ancho_max_col1 = (x_col2 - x_col1) - 24
        ancho_max_col2 = x_der - (x_col2 + 46)

        y_inicio_secciones = r_comida[0].y1 + 8
        y_original_valores = r_valores[0].y0

        # Límites verticales
        LIMITE_Y_PAGINA = H * 0.925   # Margen inferior antes del pie de página
        ALTO_BLOQUE_PAGO = 145        # Caja Total Evento + Forma de Pago + Transferencia

        # Limpiar área editable en página 1
        page1.draw_rect(fitz.Rect(0, y_inicio_secciones - 4, W, H), color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)

        # Referencia al documento original para clonar encabezados y footer
        doc_orig = fitz.open(stream=raw_pdf_bytes, filetype="pdf")
        r_total_orig = doc_orig[0].search_for("TOTAL EVENTO")[0]
        y_caja_negra_orig = r_total_orig.y0 - 17
        alto_bloque_pago_real = (H * 0.82) - y_caja_negra_orig

        def crear_nueva_pagina():
            nueva_p = doc.new_page(width=W, height=H)
            nueva_p.draw_rect(nueva_p.rect, color=COLOR_BG_CREAM, fill=COLOR_BG_CREAM)
            registrar_fuentes_en_pagina(nueva_p)
            return nueva_p

        # --- DIBUJO DE COMIDA Y BEBESTIBLES CON SALTO INTELIGENTE ---
        # Calculamos cuánto cabe en Página 1
        y_c = y_inicio_secciones
        if formato_comida.strip():
            y_c += 12
            page1.insert_text(fitz.Point(x_col1, y_c), " ".join(list(formato_comida.strip().upper())), fontname=fname_reg, fontsize=7.5, color=COLOR_TEXT_GRAY)
            y_c += 8

        comidas_p1, comidas_restantes = [], []
        for idx, item_c in enumerate(st.session_state.comidas):
            tit = item_c["titulo"].strip()
            pils = [p.strip() for p in item_c["pildoras"].split(",") if p.strip()]
            alt_est = len(envolver_texto(tit, font_obj_bold, 12.0, ancho_max_col1)) * 16 + 20
            if pils:
                alt_est += 14 + (len(pils) // 2 + 1) * 20
            if y_c + alt_est < LIMITE_Y_PAGINA - 80:
                comidas_p1.append(item_c)
                if tit:
                    for l_tit in envolver_texto(tit, font_obj_bold, 12.0, ancho_max_col1):
                        y_c += 16
                        page1.insert_text(fitz.Point(x_col1, y_c), l_tit, fontname=fname_bold, fontsize=12.0, color=COLOR_TEXT_BLACK)
                if pils:
                    y_c += 12
                    y_c = dibujar_pildoras(page1, x_col1, y_c, ancho_max_col1, pils, font_obj_reg, fname_reg, 9.5, COLOR_BG_CREAM)
                y_c += 10
                page1.draw_line(fitz.Point(x_col1, y_c), fitz.Point(x_col1 + ancho_max_col1, y_c), color=COLOR_LINE_GRAY, width=0.8)
                y_c += 4
            else:
                comidas_restantes.append(item_c)

        y_b = y_inicio_secciones + 4
        items_beb_validos = [b for b in st.session_state.bebestibles if b["cant"].strip() or b["titulo"].strip() or b["desc"].strip()]
        bebestibles_p1, bebestibles_restantes = [], []

        for idx, item_b in enumerate(items_beb_validos):
            cant_str = item_b["cant"].strip()
            tit_b = item_b["titulo"].strip()
            desc_b = item_b["desc"].strip()
            alt_b_est = 35 + len(envolver_texto(desc_b, font_obj_reg, 9.8, ancho_max_col2)) * 13

            if y_b + alt_b_est < LIMITE_Y_PAGINA - 80:
                bebestibles_p1.append(item_b)
                page1.insert_text(fitz.Point(x_col2, y_b + 21), cant_str, fontname=fname_disp, fontsize=20, color=COLOR_TEXT_BLACK)
                y_txt_b = y_b + 12
                if tit_b:
                    for l_tb in envolver_texto(tit_b, font_obj_bold, 10.0, ancho_max_col2):
                        page1.insert_text(fitz.Point(x_col2 + 46, y_txt_b), l_tb, fontname=fname_bold, fontsize=10.0, color=COLOR_TEXT_BLACK)
                        y_txt_b += 13
                if desc_b:
                    for l_db in envolver_texto(desc_b, font_obj_reg, 9.8, ancho_max_col2):
                        page1.insert_text(fitz.Point(x_col2 + 46, y_txt_b), l_db, fontname=fname_reg, fontsize=9.8, color=COLOR_TEXT_BLACK)
                        y_txt_b += 13
                y_b = max(y_b + 27, y_txt_b - 4) + 8
                page1.draw_line(fitz.Point(x_col2, y_b), fitz.Point(x_der, y_b), color=COLOR_LINE_GRAY, width=0.8)
                y_b += 6
            else:
                bebestibles_restantes.append(item_b)

        y_max_p1 = max(y_c, y_b)

        # Preparar datos de valores
        filas_valores = [(v["concepto"].strip(), v["nota"].strip(), v["monto"]) for v in st.session_state.valores_items if v["concepto"].strip() or v["monto"] > 0]
        if incluir_propina:
            filas_valores.append(("Propina sugerida 10%", "", monto_propina))
        alto_tabla_val = 35 + (len(filas_valores) * 28)
        alto_obs_est = (len(envolver_texto(observaciones.strip(), font_obj_reg, 9.5, x_der - x_col1)) * 13 + 30) if observaciones.strip() else 0

        # Función auxiliar para renderizar bloque de valores
        def render_seccion_valores(target_page, y_start):
            target_page.show_pdf_page(fitz.Rect(0, y_start - 4, W, y_start + 28), doc_orig, 0, clip=fitz.Rect(0, y_original_valores - 4, W, y_original_valores + 28))
            y_f = y_start + r_valores[0].height + 30
            for idx, (concepto, nota, monto) in enumerate(filas_valores):
                target_page.insert_text(fitz.Point(x_col1, y_f), concepto, fontname=fname_reg, fontsize=10.5, color=COLOR_TEXT_BLACK)
                if nota:
                    target_page.insert_text(fitz.Point(x_col1 + font_obj_reg.text_length(concepto + " ", fontsize=10.5), y_f), nota, fontname=fname_reg, fontsize=10.5, color=COLOR_TEXT_GRAY)
                insertar_texto_derecha(target_page, x_der, y_f, formato_clp(monto), font_obj_bold, fname_bold, 11, COLOR_TEXT_BLACK)
                if idx < len(filas_valores) - 1:
                    target_page.draw_line(fitz.Point(x_col1, y_f + 10), fitz.Point(x_der, y_f + 10), color=COLOR_LINE_GRAY, width=0.8)
                y_f += 28
            return y_f

        # Función auxiliar para renderizar bloque inferior de pago
        def render_bloque_pago(target_page, y_top):
            target_page.show_pdf_page(fitz.Rect(0, y_top, W, y_top + alto_bloque_pago_real), doc_orig, 0, clip=fitz.Rect(0, y_caja_negra_orig, W, H * 0.82))
            offset = y_top - y_caja_negra_orig
            target_page.draw_rect(fitz.Rect(W * 0.55, r_total_orig.y0 + offset - 10, x_der - 8, r_total_orig.y1 + offset + 10), color=COLOR_BG_BLACK, fill=COLOR_BG_BLACK)
            insertar_texto_derecha(target_page, x_der - 16, r_total_orig.y1 + offset + 3, formato_clp(total_evento), font_obj_disp, fname_disp, 22, COLOR_GOLD)

        # DECISIÓN INTELIGENTE: ¿1, 2 o 3 páginas?
        hay_desborde_items = bool(comidas_restantes or bebestibles_restantes)
        cabe_todo_en_p1 = (not hay_desborde_items) and ((y_max_p1 + alto_tabla_val + alto_obs_est + ALTO_BLOQUE_PAGO) < LIMITE_Y_PAGINA)

        if cabe_todo_en_p1:
            # === CASO: 1 PÁGINA ===
            y_val_p1 = max(y_original_valores, y_max_p1 + 12)
            y_fin_val_p1 = render_seccion_valores(page1, y_val_p1)
            y_obs_p1 = y_fin_val_p1 + 6
            if observaciones.strip():
                page1.insert_text(fitz.Point(x_col1, y_obs_p1), "OBSERVACIONES", fontname=fname_bold, fontsize=9.0, color=COLOR_TEXT_GRAY)
                y_obs_p1 += 12
                for l_obs in envolver_texto(observaciones.strip(), font_obj_reg, 9.5, x_der - x_col1):
                    page1.insert_text(fitz.Point(x_col1, y_obs_p1), l_obs, fontname=fname_reg, fontsize=9.5, color=COLOR_TEXT_BLACK)
                    y_obs_p1 += 13
                y_obs_p1 += 8
            render_bloque_pago(page1, max(y_obs_p1 + 6, y_caja_negra_orig + (y_val_p1 - y_original_valores)))
            page1.show_pdf_page(fitz.Rect(0, H * 0.945, W, H), doc_orig, 0, clip=fitz.Rect(0, H * 0.945, W, H))

        else:
            # Cierra pie de página 1
            page1.show_pdf_page(fitz.Rect(0, H * 0.945, W, H), doc_orig, 0, clip=fitz.Rect(0, H * 0.945, W, H))

            # === PÁGINA 2 ===
            page2 = crear_nueva_pagina()
            y_p2 = 45

            # Si quedaron comidas o bebestibles pendientes, se dibujan arriba en página 2
            if hay_desborde_items:
                y_c2, y_b2 = y_p2, y_p2
                for item_c in comidas_restantes:
                    tit = item_c["titulo"].strip()
                    pils = [p.strip() for p in item_c["pildoras"].split(",") if p.strip()]
                    if tit:
                        for l_tit in envolver_texto(tit, font_obj_bold, 12.0, ancho_max_col1):
                            y_c2 += 16
                            page2.insert_text(fitz.Point(x_col1, y_c2), l_tit, fontname=fname_bold, fontsize=12.0, color=COLOR_TEXT_BLACK)
                    if pils:
                        y_c2 += 12
                        y_c2 = dibujar_pildoras(page2, x_col1, y_c2, ancho_max_col1, pils, font_obj_reg, fname_reg, 9.5, COLOR_BG_CREAM)
                    y_c2 += 12
                    page2.draw_line(fitz.Point(x_col1, y_c2), fitz.Point(x_col1 + ancho_max_col1, y_c2), color=COLOR_LINE_GRAY, width=0.8)
                    y_c2 += 4

                for item_b in bebestibles_restantes:
                    cant_str = item_b["cant"].strip()
                    tit_b = item_b["titulo"].strip()
                    desc_b = item_b["desc"].strip()
                    page2.insert_text(fitz.Point(x_col2, y_b2 + 21), cant_str, fontname=fname_disp, fontsize=20, color=COLOR_TEXT_BLACK)
                    y_txt_b = y_b2 + 12
                    if tit_b:
                        for l_tb in envolver_texto(tit_b, font_obj_bold, 10.0, ancho_max_col2):
                            page2.insert_text(fitz.Point(x_col2 + 46, y_txt_b), l_tb, fontname=fname_bold, fontsize=10.0, color=COLOR_TEXT_BLACK)
                            y_txt_b += 13
                    if desc_b:
                        for l_db in envolver_texto(desc_b, font_obj_reg, 9.8, ancho_max_col2):
                            page2.insert_text(fitz.Point(x_col2 + 46, y_txt_b), l_db, fontname=fname_reg, fontsize=9.8, color=COLOR_TEXT_BLACK)
                            y_txt_b += 13
                    y_b2 = max(y_b2 + 27, y_txt_b - 4) + 8
                    page2.draw_line(fitz.Point(x_col2, y_b2), fitz.Point(x_der, y_b2), color=COLOR_LINE_GRAY, width=0.8)
                    y_b2 += 6

                y_p2 = max(y_c2, y_b2) + 16

            # Evaluamos si en Página 2 cabe Valores + Observaciones + Pagos
            cabe_todo_en_p2 = (y_p2 + alto_tabla_val + alto_obs_est + ALTO_BLOQUE_PAGO) < LIMITE_Y_PAGINA

            if cabe_todo_en_p2:
                # Todo entra en Página 2 (Total: 2 páginas)
                y_fin_val_p2 = render_seccion_valores(page2, y_p2)
                y_obs_p2 = y_fin_val_p2 + 6
                if observaciones.strip():
                    page2.insert_text(fitz.Point(x_col1, y_obs_p2), "OBSERVACIONES", fontname=fname_bold, fontsize=9.0, color=COLOR_TEXT_GRAY)
                    y_obs_p2 += 12
                    for l_obs in envolver_texto(observaciones.strip(), font_obj_reg, 9.5, x_der - x_col1):
                        page2.insert_text(fitz.Point(x_col1, y_obs_p2), l_obs, fontname=fname_reg, fontsize=9.5, color=COLOR_TEXT_BLACK)
                        y_obs_p2 += 13
                    y_obs_p2 += 10
                render_bloque_pago(page2, max(y_obs_p2 + 8, y_caja_negra_orig))
                page2.show_pdf_page(fitz.Rect(0, H * 0.945, W, H), doc_orig, 0, clip=fitz.Rect(0, H * 0.945, W, H))

            else:
                # === CASO: 3 PÁGINAS ===
                # En página 2 colocamos los valores (y observaciones si alcanzan)
                y_fin_val_p2 = render_seccion_valores(page2, y_p2)
                page2.show_pdf_page(fitz.Rect(0, H * 0.945, W, H), doc_orig, 0, clip=fitz.Rect(0, H * 0.945, W, H))

                # Crear Página 3 para Observaciones y Pagos
                page3 = crear_nueva_pagina()
                y_p3 = 50

                if observaciones.strip():
                    page3.insert_text(fitz.Point(x_col1, y_p3), "OBSERVACIONES", fontname=fname_bold, fontsize=10.0, color=COLOR_TEXT_GRAY)
                    y_p3 += 16
                    for l_obs in envolver_texto(observaciones.strip(), font_obj_reg, 9.8, x_der - x_col1):
                        page3.insert_text(fitz.Point(x_col1, y_p3), l_obs, fontname=fname_reg, fontsize=9.8, color=COLOR_TEXT_BLACK)
                        y_p3 += 14
                    y_p3 += 20

                render_bloque_pago(page3, max(y_p3 + 10, 220))
                page3.show_pdf_page(fitz.Rect(0, H * 0.945, W, H), doc_orig, 0, clip=fitz.Rect(0, H * 0.945, W, H))

        doc_orig.close()

    # Guardar y previsualizar de forma segura
    pdf_out = io.BytesIO()
    doc.save(pdf_out)

    with col_preview:
        st.subheader("Vista Previa en Tiempo Real")
        st.download_button(
            "Descargar Cotización en PDF",
            data=pdf_out.getvalue(),
            file_name=f"Cotizacion_El_Bajo_{num_cotizacion.strip('[]')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        for num_p, p in enumerate(doc):
            pix = p.get_pixmap(dpi=150)
            st.caption(f"Página {num_p + 1}")
            st.image(pix.tobytes("png"), use_container_width=True)

    doc.close()
else:
    with col_preview:
        st.info("Sube el archivo PDF original en el menú izquierdo para comenzar.")