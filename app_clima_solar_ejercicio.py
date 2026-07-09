"""
Aplicación de Clima Solar - Índice UV Ajustado por Nubes.

Este programa simula una aplicación móvil que obtiene el índice UV de una ubicación
y lo ajusta según la cobertura de nubes, mostrando el nivel de riesgo.

Autor: [Tu nombre]
Fecha: Junio 2026
"""

import streamlit as st
import requests
from typing import Optional, Tuple, Dict, Union
import pandas as pd

import plotly.graph_objects as go

from datetime import datetime
from zoneinfo import ZoneInfo
import locale

import folium
from streamlit_folium import st_folium


# --- CONSTANTES GLOBALES ---
MAX_AMORTIGUACION: float = 0.5
# float: Factor máximo de reducción del UV por nubes (0.5 = 50%).


# --- COMPLETAR RANGOS DE ÍNDICE UV ---
RANGOS_UV: Dict[str, Dict[str, Union[float, str]]] = {
    "Bajo": {
        "min": None,  # <--- Reemplaza None con el valor mínimo (ej. 0.0)
        "max": None,  # <--- Reemplaza None con el valor máximo (ej. 2.9)
        "color": "#00FF00"  # Verde
    },
    "Moderado": {
        "min": None,  # <--- Reemplaza None (ej. 3.0)
        "max": None,  # <--- Reemplaza None (ej. 5.9)
        "color": "#FFFF00"  # Amarillo
    },
    "Alto": {
        "min": None,  # <--- Reemplaza None (ej. 6.0)
        "max": None,  # <--- Reemplaza None (ej. 7.9)
        "color": "#FFA500"  # Naranja
    },
    "Muy Alto": {
        "min": None,  # <--- Reemplaza None (ej. 8.0)
        "max": None,  # <--- Reemplaza None (ej. 10.9)
        "color": "#FF0000"  # Rojo
    },
    "Extremo": {
        "min": None,  # <--- Reemplaza None (ej. 11.0)
        "max": None,  # <--- Reemplaza None (deja float('inf') para que no tenga límite superior)
        "color": "#8B00FF"  # Púrpura
    }
}
# --- FIN DE LA ZONA PARA COMPLETAR ---

# --- FACTORES DE FOTOTIPO PARA TIEMPO DE QUEMADURA ---
FACTORES_FOTOTIPO: Dict[str, float] = {
    "I (muy clara)": 0.8,
    "II (clara)": 1.0,
    "III (intermedia)": 1.5,
    "IV (morena)": 2.5,
    "V-VI (oscura)": 4.0
}


# URLS DE LAS APIS
URL_UV: str = "https://currentuvindex.com/api/v1/uvi"
URL_NUBES: str = "https://api.open-meteo.com/v1/forecast"


# --- FUNCIÓN 1: OBTENER UBICACIÓN ---
def obtener_ubicacion_predeterminada() -> Tuple[Optional[float], Optional[float]]:
    """
    [COMPLETAR] Obtiene las coordenadas de la ubicación.

    Tarea: Reemplaza los valores None con las coordenadas de tu ciudad.
    Puedes buscarlas en Google Maps o en cualquier servicio de mapas.

    Returns:
        Tuple[Optional[float], Optional[float]]: Un par (latitud, longitud).
        Si no se completan, retorna (None, None).
    """
    # --- COMPLETA AQUÍ LAS COORDENADAS ---
    latitud: Optional[float] = None   # <--- Reemplaza None con la latitud (ej. 4.750600)
    longitud: Optional[float] = None  # <--- Reemplaza None con la longitud (ej. -74.030370)
    # --- FIN DE LA ZONA PARA COMPLETAR ---

    return latitud, longitud

# --- FUNCIÓN 2: OBTENER ÍNDICE UV Y HORA DEL REPORTE DESDE LA API ---
def obtener_uvi(lat: float, lon: float) -> Tuple[float, str]:
    """
    Obtiene el índice UV actual y su hora desde la API de CurrentUVIndex.

    Realiza una petición GET a la API con las coordenadas proporcionadas
    y extrae el valor del índice UV y la hora del momento actual.

    Args:
        lat (float): Latitud de la ubicación (ej. 4.750600).
        lon (float): Longitud de la ubicación (ej. -74.030370).

    Returns:
        Tuple[float, str]: Un par con:
            - float: Valor del índice UV actual. Retorna 0.0 si ocurre un error.
            - str: Hora en formato ISO (ej. "2026-06-24T14:00:00Z"). Retorna
              cadena vacía si ocurre un error.

    Raises:
        requests.exceptions.RequestException: Si la petición HTTP falla.

    Example:
        >>> uvi, hora = obtener_uvi(4.7506, -74.03037)
        >>> print(f"UVI: {uvi:.1f} a las {hora}")
        UVI: 10.8 a las 2026-06-24T14:00:00Z
    """
    url: str = f"{URL_UV}?latitude={lat}&longitude={lon}"

    try:
        respuesta: requests.Response = requests.get(url)
        respuesta.raise_for_status()  # Lanza excepción si el status no es 200
        datos: Dict = respuesta.json()

        # Extraer el valor de 'uvi' del objeto 'now'
        uvi: float = float(datos['now']['uvi'])
        hora_iso: str = datos['now']['time']  # Ej: "2026-06-24T14:00:00Z"
        return uvi, hora_iso

    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión al obtener datos de UV: {e}")
        return 0.0
    except (KeyError, ValueError) as e:
        st.error(f"Error al parsear los datos de UV: {e}")
        return 0.0


def mostrar_mapa(lat: float, lon: float, zoom: int = 15, width: int = 700, height: int = 450) -> None:
    """
    Muestra un mapa de calles interactivo con un marcador en la ubicación especificada.

    Args:
        lat (float): Latitud de la ubicación.
        lon (float): Longitud de la ubicación.
        zoom (int): Nivel de zoom del mapa (por defecto 14).
        width (int): Ancho del mapa en píxeles (por defecto 700).
        height (int): Alto del mapa en píxeles (por defecto 450).

    Returns:
        None: La función muestra el mapa directamente en la interfaz de Streamlit.

    Example:
        >>> lat, lon = obtener_ubicacion_predeterminada()
        >>> mostrar_mapa(lat, lon, zoom=15)
    """
    # Crear el mapa centrado en la ubicación
    mapa = folium.Map(
        location=[lat, lon],
        zoom_start=zoom,
        tiles='OpenStreetMap'
    )

    # Añadir un marcador en la ubicación
    folium.Marker(
        location=[lat, lon],
        popup=f"""
            <div style="background-color: #000000; padding: 8px; border-radius: 5px; color: white; font-weight: bold;">
                🌤️ {lat:.4f}, {lon:.4f}
            </div>
            """,
        icon=folium.Icon(color='orange', icon='graduation-cap', prefix='fa')
    ).add_to(mapa)

    # Mostrar el mapa en Streamlit con tamaño exacto
    mapa_html = mapa._repr_html_()
    st.components.v1.html(mapa_html, width=width, height=height)


# --- FUNCIÓN 3: OBTENER FACTOR DE NUBES Y PORCENTAJE DE COBERTURA ---
def obtener_factor_nubes(lat: float, lon: float) -> Tuple[float, float]:
    """
    Obtiene el factor de atenuación y el porcentaje de cobertura nubosa desde Open-Meteo.

    Consulta la API de Open-Meteo para obtener el porcentaje de cobertura nubosa
    y lo convierte en un factor de atenuación entre 0 y MAX_AMORTIGUACION.

    Args:
        lat (float): Latitud de la ubicación (ej. 4.750600).
        lon (float): Longitud de la ubicación (ej. -74.030370).

    Returns:
        Tuple[float, float]: Un par con:
            - float: Factor de atenuación entre 0 y MAX_AMORTIGUACION (0.5).
            - float: Porcentaje de cobertura nubosa (0-100).
            Retorna (0.0, 0.0) si ocurre un error en la conexión o en el parseo.

    Raises:
        requests.exceptions.RequestException: Si la petición HTTP falla.

    Example:
        >>> factor, porcentaje = obtener_factor_nubes(4.7506, -74.03037)
        >>> print(f"Factor: {factor:.2f}, Nubes: {porcentaje:.0f}%")
        Factor: 0.18, Nubes: 37%

    Nota:
        El cálculo es lineal: factor = (porcentaje_nubes / 100) * MAX_AMORTIGUACION.
        Esto es una simplificación educativa; en la realidad la relación no es lineal.
    """
    url: str = f"{URL_NUBES}?latitude={lat}&longitude={lon}&current=cloud_cover"

    try:
        respuesta: requests.Response = requests.get(url)
        respuesta.raise_for_status()
        datos: Dict = respuesta.json()

        # Calcular factor proporcional: nubes 0% -> 0, nubes 100% -> MAX_AMORTIGUACION
        porcentaje_nubes: float = float(datos['current']['cloud_cover'])
        factor: float = (porcentaje_nubes / 100.0) * MAX_AMORTIGUACION
        return factor, porcentaje_nubes

    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión al obtener datos de nubes: {e}")
        return 0.0, 0.0
    except (KeyError, ValueError) as e:
        st.error(f"Error al parsear los datos de nubes: {e}")
        return 0.0, 0.0

def obtener_icono_nubes(porcentaje: float) -> str:
    """
    Retorna un ícono representativo según el porcentaje de cobertura nubosa.

    Args:
        porcentaje (float): Porcentaje de cobertura de nubes (0-100).

    Returns:
        str: Emoji que representa el estado del cielo.

    Examples:
        >>> obtener_icono_nubes(90)
        '☁️'
        >>> obtener_icono_nubes(65)
        '⛅'
        >>> obtener_icono_nubes(30)
        '🌤️'
        >>> obtener_icono_nubes(5)
        '☀️'
    """
    if porcentaje >= 80:
        return "☁️"   # Muy nublado
    elif porcentaje >= 50:
        return "⛅"   # Parcialmente nublado
    elif porcentaje >= 20:
        return "🌤️"  # Mayormente soleado
    else:
        return "☀️"   # Despejado


# --- FUNCIÓN 4: CALCULAR UVI AJUSTADO ---
def calcular_uvi_ajustado(uvi: float, factor_nubes: float) -> float:
    """
    Aplica la atenuación por nubes al índice UV original.

    La fórmula de atenuación es: uvi_ajustado = uvi * (1 - factor_nubes).

    Args:
        uvi (float): Índice UV original (sin atenuar).
        factor_nubes (float): Factor de atenuación entre 0 y 1.

    Returns:
        float: Índice UV ajustado (atenuado por las nubes).

    Example:
        >>> uvi_ajustado = calcular_uvi_ajustado(10.8, 0.18)
        >>> print(f"UVI ajustado: {uvi_ajustado:.1f}")
        UVI ajustado: 8.9  # 10.8 * (1 - 0.18) = 8.856 ≈ 8.9
    """
    return uvi * (1.0 - factor_nubes)


# --- FUNCIÓN 5: CLASIFICAR UVI ---
def clasificar_uvi(valor_uvi: float) -> Tuple[str, str]:
    """
    Clasifica el índice UV en un nivel de riesgo con su color asociado.

    Utiliza rangos predefinidos según la escala internacional de la OMS:
        - Bajo: 0.0 - 2.9
        - Moderado: 3.0 - 5.9
        - Alto: 6.0 - 7.9
        - Muy Alto: 8.0 - 10.9
        - Extremo: 11.0 en adelante

    Args:
        valor_uvi (float): Índice UV a clasificar.

    Returns:
        Tuple[str, str]: Un par (mensaje, color) donde:
            - mensaje (str): Nivel de riesgo (ej. "Muy Alto").
            - color (str): Color asociado en formato HEX (ej. "#FF0000").

    Example:
        >>> mensaje, color = clasificar_uvi(10.8)
        >>> print(f"{mensaje} -> {color}")
        Muy Alto -> #FF0000

        >>> mensaje, color = clasificar_uvi(2.5)
        >>> print(f"{mensaje} -> {color}")
        Bajo -> #00FF00
    """
    for nivel, rango in RANGOS_UV.items():
        if rango["min"] <= valor_uvi <= rango["max"]:
            return nivel, rango["color"]
    return "Sin clasificar", "#808080"

def crear_gauge_uvi(valor_uvi: float, color_texto: str, maximo: float = 14.0) -> go.Figure:
    """
    Crea un gráfico de tipo gauge (velocímetro) para el índice UV.
    Los rangos y colores se obtienen automáticamente de la constante global RANGOS_UV.

    Args:
        valor_uvi (float): Valor del UVI a mostrar.
        color_texto (str): Color en formato HEX para el número del valor.
        maximo (float): Valor máximo de la escala (por defecto 14).

    Returns:
        go.Figure: Figura de Plotly con el gauge.
    """
    # Construir los steps del gauge a partir de los rangos globales
    steps = []
    for rango in RANGOS_UV.values():
        max_rango = min(rango["max"], maximo) if rango["max"] != float('inf') else maximo
        steps.append({
            'range': [rango["min"], max_rango],
            'color': rango["color"]
        })

    # Crear la figura con los steps generados
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_uvi,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'font': {'color': color_texto, 'size': 60}},  # <--- Color dinámico
        gauge={
            'axis': {'range': [None, maximo], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "white"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': steps,
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 1,
                'value': valor_uvi
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "black"}
    )
    return fig

def formatear_hora(hora_iso: str) -> tuple:
    """
    Convierte una hora en formato ISO (UTC) a la zona horaria de Bogotá
    y la devuelve formateada en español.

    Args:
        hora_iso (str): Cadena con la hora en formato ISO (ej. "2026-06-24T16:00:00Z")

    Returns:
        tuple: (fecha_formateada, hora_formateada)
               Ejemplo: ("24 de junio de 2026", "11:00 AM")
    """
    try:
        # Configurar locale a español (solo una vez)
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'spanish')
            except:
                pass

        # Convertir UTC a Bogotá
        hora_utc = datetime.fromisoformat(hora_iso.replace('Z', '+00:00'))
        hora_utc = hora_utc.replace(tzinfo=ZoneInfo('UTC'))
        hora_local = hora_utc.astimezone(ZoneInfo('America/Bogota'))

        # Formatear
        fecha = hora_local.strftime("%d de %B de %Y")
        hora = hora_local.strftime("%I:%M %p")

        return fecha, hora

    except Exception as e:
        return "Fecha no disponible", "Hora no disponible"


# --- INTERFAZ DE STREAMLIT ---
# --- INTERFAZ DE STREAMLIT ---
def main() -> None:
    """
    Función principal que construye la interfaz gráfica en Streamlit.

    [INSTRUCCIONES PARA COMPLETAR]
    Lee los comentarios marcados con "TODO" para saber qué funciones debes llamar
    y qué datos necesitas obtener de cada una.
    """
    st.set_page_config(page_title="Clima Solar - Bogotá", page_icon="🌦️")
    st.title("🌦️ App del Clima Solar - Bogotá")

    # ----------------------------------------------------------------------
    # TODO: Obtener la ubicación
    #
    # Debes llamar a la función 'obtener_ubicacion_predeterminada()' que
    # retorna dos valores: latitud y longitud.
    #
    # ¿Por qué? La aplicación necesita saber dónde estás para consultar el
    # índice UV y la cobertura de nubes en esa ubicación exacta.
    #
    # Ejemplo:
    # lat, lon = obtener_ubicacion_predeterminada()
    # ----------------------------------------------------------------------
    # --- COMPLETA AQUÍ LA LLAMADA A LA FUNCIÓN ---
    lat = None   # <--- Reemplaza None con la llamada correcta
    lon = None   # <--- Reemplaza None con la llamada correcta
    # --- FIN DE LA ZONA PARA COMPLETAR ---

    # Mostrar coordenadas actuales (si están disponibles)
    if lat is not None and lon is not None:
        st.info(f"📍 Ubicación: Bogotá, Colombia (Lat: {lat}, Lon: {lon})")
    else:
        st.warning("⚠️ No se ha obtenido la ubicación. Completa la sección correspondiente.")

    # ----------------------------------------------------------------------
    # TODO: Mostrar el mapa
    #
    # Debes llamar a la función 'mostrar_mapa(lat, lon)' para que aparezca
    # el mapa con la ubicación.
    #
    # ¿Por qué? El mapa te permite visualizar la ubicación y entender cómo
    # se relacionan las coordenadas con el lugar real.
    # ----------------------------------------------------------------------
    st.subheader("🗺️ Ubicación en el mapa")
    # --- COMPLETA AQUÍ LA LLAMADA A LA FUNCIÓN ---
    # mostrar_mapa(lat, lon)  # <--- Descomenta y completa la llamada
    # --- FIN DE LA ZONA PARA COMPLETAR ---

    # Selector para incluir nubes
    incluir_nubes: bool = st.checkbox("☁️ Considerar cobertura de nubes", value=True)
    porcentaje_nubes = 0  # Valor por defecto

    # Selector de fototipo
    fototipo = st.selectbox(
        "🧴 Selecciona tu fototipo de piel (para estimar tiempo de quemadura):",
        options=["I (muy clara)", "II (clara)", "III (intermedia)", "IV (morena)", "V-VI (oscura)"],
        index=1  # Por defecto: II (clara)
    )

    # --- AVISO CORTO SOBRE TIEMPOS DE QUEMADURA ---
    st.info(
        "⏱️ **Tiempo de quemadura:** Cálculo orientativo y educativo. "
        "Siempre usa protector solar. "
        "[Más información en el desplegable de documentación](#)."
    )

    # Botón de acción principal
    if st.button("🚀 Obtener Índice UV", type="primary"):
        with st.spinner("Consultando datos meteorológicos..."):
            # ------------------------------------------------------------------
            # TODO: Obtener el índice UV y la hora
            #
            # Debes llamar a la función 'obtener_uvi(lat, lon)' que retorna
            # dos valores: el índice UV actual y la hora en formato ISO.
            #
            # ¿Por qué? El índice UV es el dato central de la aplicación.
            # La hora permite saber cuándo se actualizó el dato.
            # ------------------------------------------------------------------
            # --- COMPLETA AQUÍ LA LLAMADA A LA FUNCIÓN ---
            uvi_original = None   # <--- Reemplaza None con la llamada correcta
            hora_iso = None       # <--- Reemplaza None con la llamada correcta
            # --- FIN DE LA ZONA PARA COMPLETAR ---

            # Convertir la hora (si está disponible)
            if hora_iso is not None:
                fecha_formateada, hora_formateada = formatear_hora(hora_iso)
                # Mostrar en la interfaz
                st.markdown(f"""
                <div style='text-align: center; margin: 10px 0;'>
                    <p style='font-size: 14px; color: gray;'>Datos actualizados al:</p>
                    <p style='font-size: 28px; font-weight: bold;'>{fecha_formateada} - {hora_formateada}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ No se pudo obtener la hora del dato. Completa la sección correspondiente.")

            # ------------------------------------------------------------------
            # TODO: Obtener factor de nubes (si está activado)
            #
            # Si 'incluir_nubes' es True, debes llamar a la función
            # 'obtener_factor_nubes(lat, lon)' que retorna dos valores:
            # el factor de atenuación y el porcentaje de nubes.
            #
            # ¿Por qué? Las nubes atenúan la radiación UV, por lo que el
            # factor permite ajustar el índice UV a las condiciones reales.
            # ------------------------------------------------------------------
            if incluir_nubes:
                # --- COMPLETA AQUÍ LA LLAMADA A LA FUNCIÓN ---
                factor_nubes = 0.0     # <--- Reemplaza con la llamada correcta
                porcentaje_nubes = 0   # <--- Reemplaza con la llamada correcta
                # --- FIN DE LA ZONA PARA COMPLETAR ---
                icono_nubes = obtener_icono_nubes(porcentaje_nubes) if porcentaje_nubes is not None else "☀️"
            else:
                factor_nubes = 0.0
                porcentaje_nubes = 0
                icono_nubes = "☀️"

            # ------------------------------------------------------------------
            # TODO: Calcular el UVI ajustado
            #
            # Debes llamar a la función 'calcular_uvi_ajustado(uvi_original, factor_nubes)'
            # que retorna un valor numérico (float).
            #
            # ¿Por qué? El UVI ajustado considera el efecto de las nubes,
            # dando una estimación más realista de la radiación que llega al suelo.
            # ------------------------------------------------------------------
            # --- COMPLETA AQUÍ LA LLAMADA A LA FUNCIÓN ---
            uvi_ajustado = 0.0   # <--- Reemplaza con la llamada correcta
            # --- FIN DE LA ZONA PARA COMPLETAR ---

            # ------------------------------------------------------------------
            # TODO: Clasificar el UVI ajustado
            #
            # Debes llamar a la función 'clasificar_uvi(uvi_ajustado)' que
            # retorna dos valores: el mensaje de riesgo y el color asociado.
            #
            # ¿Por qué? Clasificar el UVI en niveles (Bajo, Moderado, Alto, etc.)
            # ayuda a entender el riesgo de exposición al sol de forma intuitiva.
            # ------------------------------------------------------------------
            # --- COMPLETA AQUÍ LA LLAMADA A LA FUNCIÓN ---
            mensaje = ""   # <--- Reemplaza con la llamada correcta
            color = ""     # <--- Reemplaza con la llamada correcta
            # --- FIN DE LA ZONA PARA COMPLETAR ---

            # Calcular tiempo de quemadura (solo si el UVI es > 0)
            if uvi_ajustado > 0:
                factor_fototipo = FACTORES_FOTOTIPO[fototipo]
                tiempo_quemadura = (50 / uvi_ajustado) * factor_fototipo
                # Mostrar con un formato limpio
                if tiempo_quemadura > 120:
                    tiempo_mostrar = "> 120 min"
                elif tiempo_quemadura < 1:
                    tiempo_mostrar = "< 1 min"
                else:
                    tiempo_mostrar = f"{tiempo_quemadura:.0f} min"
            else:
                tiempo_mostrar = "--"

            # 5. Mostrar resultados en columnas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🌞 UV Original", f"{uvi_original:.1f}" if uvi_original is not None else "--")

            if incluir_nubes:
                # Si se consideran nubes, mostrar los valores calculados
                col2.metric("☁️ Factor Nubes", f"{factor_nubes:.2f} {icono_nubes}" if factor_nubes is not None else "--")
                col3.metric("🌤️ UV Ajustado", f"{uvi_ajustado:.1f}" if uvi_ajustado is not None else "--")
            else:
                # Si NO se consideran nubes, mostrar "--"
                col2.metric("☁️ Factor Nubes", "--")
                col3.metric("🌤️ UV Ajustado", "--")

            # Mostrar tiempo de quemadura
            col4.metric("⏱️ Tiempo para quemadura", tiempo_mostrar)

            # Mostrar el gauge (si hay datos)
            if uvi_ajustado is not None and color is not None:
                st.subheader("📊 Medidor de Índice UV")
                st.plotly_chart(crear_gauge_uvi(uvi_ajustado, color), use_container_width=True)
            else:
                st.warning("⚠️ No se pudo generar el gauge. Completa la clasificación del UVI.")

            # 6. Mostrar el nivel de riesgo con el color asociado
            if mensaje and color:
                st.markdown(
                    f"<h1 style='color: {color}; text-align: center;'>"
                    f"{mensaje}</h1>",
                    unsafe_allow_html=True
                )
            else:
                st.warning("⚠️ No se pudo mostrar el nivel de riesgo. Completa la clasificación del UVI.")

            # 7. Mostrar detalles técnicos
            with st.expander("Ver detalles de la API"):
                st.write(f"**Latitud:** {lat if lat is not None else 'No disponible'}")
                st.write(f"**Longitud:** {lon if lon is not None else 'No disponible'}")
                st.write(f"**Factor máximo de amortiguación:** {MAX_AMORTIGUACION}")
                if incluir_nubes:
                    st.write("**Cobertura de nubes:** Considerada en el cálculo.")
                else:
                    st.write("**Cobertura de nubes:** No considerada.")

            # --- DOCUMENTACIÓN DE LAS APIS (después de mostrar resultados, antes del pie) ---
            with st.expander("🌐 Documentación de las APIs utilizadas"):
                st.markdown("""
                **API de Índice UV (CurrentUVIndex)**
                - Documentación: [https://currentuvindex.com/](https://currentuvindex.com/)
                - Endpoint utilizado: `https://currentuvindex.com/api/v1/uvi?latitude={lat}&longitude={lon}`

                **API de Cobertura de Nubes (Open-Meteo)**
                - Documentación: [https://open-meteo.com/en/docs](https://open-meteo.com/en/docs)
                - Endpoint utilizado: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=cloud_cover`

                **⚠️ Precisión de los datos:**
                Las APIs utilizadas en esta demostración se basan en **modelos de pronóstico**. Los datos son estimaciones, no mediciones en tiempo real.
                Para aplicaciones que requieran datos precisos del índice UV, se recomienda utilizar servicios especializados como [OpenUV.io](https://www.openuv.io/) (requiere clave de API).

                ---
                **⚠️ Nota sobre los tiempos de quemadura:**
                El tiempo estimado para quemadura mostrado en esta aplicación es un **cálculo puramente orientativo y educativo**, basado en aproximaciones matemáticas generales y en el Índice UV pronosticado. No sustituye en ningún caso la recomendación de un profesional de la salud. La sensibilidad al sol varía según cada persona, incluso dentro del mismo fototipo. Siempre se recomienda el uso de protector solar, ropa y sombrero, independientemente del tiempo estimado. Este cálculo es parte de un **ejercicio académico de programación** para demostrar la integración de APIs y el procesamiento de datos en tiempo real. Los resultados no deben utilizarse como guía para la exposición al sol. Para información precisa y personalizada, consulta siempre fuentes oficiales como la [Organización Mundial de la Salud (OMS)](https://www.who.int/news-room/questions-answers/item/ultraviolet-uv-radiation-and-the-uv-index) o herramientas especializadas como [UV-DERMA](https://uv-derma.com/).
                """)

    st.markdown("---")
    st.markdown("""
        **Desarrollado para el Family Experience 2026**\n
        Tecnología en Desarrollo de Software\n
        **Nicolás Gómez Jaramillo** | [ngomez@usbbog.edu.co](ngomez@usbbog.edu.co) | [https://co.linkedin.com/in/nicolasgomezjaramillo](https://co.linkedin.com/in/nicolasgomezjaramillo)
    """)
    st.markdown("---")
    st.markdown("""
        ℹ️ **Nota sobre los datos:** Esta aplicación utiliza servicios de pronóstico. \n
        Los valores del Índice UV son estimaciones. Para datos precisos, consulta [OpenUV.io](https://www.openuv.io/).
    """)

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    main()
