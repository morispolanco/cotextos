import streamlit as st
from docx import Document
from io import BytesIO
from textblob import TextBlob
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import requests
import re

# Descargar recursos necesarios para nltk y textblob
nltk.download('punkt')
nltk.download('stopwords')

# Configuración del API de LanguageTool
LANGUAGE_TOOL_API_URL = "https://api.languagetool.org/v2/check"

# Función para corregir texto usando el API público de LanguageTool
def corregir_texto(texto):
    partes = separar_citas(texto)
    texto_corregido = ""

    for parte in partes:
        if re.match(r'(\".*?\"|“.*?”|‘.*?’)', parte):
            texto_corregido += parte
        else:
            try:
                texto_corregido += corregir_segmento(parte)
            except Exception as e:
                st.error(f"Error al corregir el texto: {e}")
                texto_corregido += parte

    return texto_corregido

# Función para corregir un segmento de texto usando el API de LanguageTool
def corregir_segmento(texto):
    payload = {'text': texto, 'language': 'es'}
    response = requests.post(LANGUAGE_TOOL_API_URL, data=payload)

    if response.status_code != 200:
        raise Exception(f"Error en la API de LanguageTool: {response.status_code} - {response.text}")

    resultado = response.json()
    matches = resultado.get('matches', [])
    texto_modificado = texto
    offset_correction = 0

    for match in sorted(matches, key=lambda x: x['offset']):
        offset = match['offset'] + offset_correction
        length = match['length']
        replacements = match.get('replacements', [])

        if not replacements:
            continue

        replacement = replacements[0]['value']
        texto_modificado = (
            texto_modificado[:offset] +
            replacement +
            texto_modificado[offset + length:]
        )
        offset_correction += len(replacement) - length

    blob = TextBlob(texto_modificado)
    texto_corregido_final = str(blob.correct())
    texto_corregido_final = capitalizar_primer_caracter(texto_corregido_final)
    texto_corregido_final = eliminar_repeticiones(texto_corregido_final)

    return texto_corregido_final

# Función para eliminar repeticiones de palabras
def eliminar_repeticiones(texto):
    palabras = word_tokenize(texto, language='spanish')
    stop_words = set(stopwords.words('spanish'))
    palabras_filtradas = []
    palabras_vistas = set()

    for palabra in palabras:
        palabra_lower = palabra.lower()
        if palabra_lower not in palabras_vistas or palabra_lower in stop_words:
            palabras_filtradas.append(palabra)
            palabras_vistas.add(palabra_lower)

    return ' '.join(palabras_filtradas)

# Función para separar texto dentro y fuera de comillas
def separar_citas(texto):
    pattern = r'(\".*?\"|“.*?”|‘.*?’)'
    partes = re.split(pattern, texto)
    return partes

# Función para capitalizar la primera letra de un texto
def capitalizar_primer_caracter(texto):
    if not texto:
        return texto
    return texto[0].upper() + texto[1:]

# Función para procesar el documento .docx y aplicar correcciones
def procesar_documento(doc_bytes):
    try:
        # Cargar el archivo .docx en un objeto Document
        documento = Document(BytesIO(doc_bytes))
    except Exception as e:
        st.error(f"Error al abrir el archivo: {e}")
        return None

    # Iterar sobre cada párrafo y aplicar correcciones
    for para in documento.paragraphs:
        texto_original = para.text
        if texto_original.strip() == '':
            continue  # Ignorar párrafos vacíos

        texto_corregido = corregir_texto(texto_original)
        para.text = texto_corregido  # Reemplazar el texto con el texto corregido

    corrected_doc = BytesIO()
    documento.save(corrected_doc)
    corrected_doc.seek(0)

    return corrected_doc

# Función para dividir textos largos en párrafos usando NLTK
def dividir_en_parrafos(texto, max_sentencias=5):
    oraciones = sent_tokenize(texto, language='spanish')
    parrafos = []
    parrafo_actual = []

    for oracion in oraciones:
        parrafo_actual.append(oracion)
        if len(parrafo_actual) >= max_sentencias:
            parrafos.append(' '.join(parrafo_actual))
            parrafo_actual = []

    if parrafo_actual:
        parrafos.append(' '.join(parrafo_actual))

    return parrafos

# Interfaz de usuario de Streamlit
def main():
    st.set_page_config(page_title="Corrector de Textos en Español", layout="wide")
    st.title("Corrector de Textos en Español")

    # Subir archivo .docx
    st.header("Corrige tu Documento `.docx`")
    st.write("Sube un archivo `.docx` para aplicar correcciones.")

    uploaded_file = st.file_uploader("Selecciona un archivo `.docx`", type="docx")

    if uploaded_file is not None:
        st.success("Archivo cargado exitosamente.")

        # Procesar el documento cuando se haga clic en el botón
        if st.button("Corregir Documento"):
            with st.spinner("Procesando..."):
                corrected_doc = procesar_documento(uploaded_file.read())

                if corrected_doc is not None:
                    st.success("Documento corregido exitosamente.")
                    st.download_button(
                        label="Descargar Documento Corregido",
                        data=corrected_doc,
                        file_name="documento_corregido.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.error("No se pudo procesar el documento.")

if __name__ == "__main__":
    main()
