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
    # Separar el texto en partes dentro y fuera de comillas
    partes = separar_citas(texto)
    texto_corregido = ""

    for parte in partes:
        # Si la parte está dentro de comillas, no se corrige
        if re.match(r'(\".*?\"|“.*?”|‘.*?’)', parte):
            texto_corregido += parte
        else:
            # Aplicar correcciones al texto fuera de comillas
            try:
                texto_corregido += corregir_segmento(parte)
            except Exception as e:
                st.error(f"Error al corregir el texto: {e}")
                texto_corregido += parte  # Mantener el texto original en caso de error

    return texto_corregido

# Función para corregir un segmento de texto usando el API de LanguageTool
def corregir_segmento(texto):
    payload = {
        'text': texto,
        'language': 'es',
        'enabledOnly': False,
        'removeDuplicates': 'true'
    }

    response = requests.post(LANGUAGE_TOOL_API_URL, data=payload)

    if response.status_code != 200:
        raise Exception(f"Error en la API de LanguageTool: {response.status_code} - {response.text}")

    resultado = response.json()

    matches = resultado.get('matches', [])

    # Aplicar correcciones de atrás hacia adelante para no alterar los índices
    texto_modificado = texto
    offset_correction = 0  # Corrección acumulada de los offsets debido a cambios en el texto

    for match in sorted(matches, key=lambda x: x['offset']):
        offset = match['offset'] + offset_correction
        length = match['length']
        replacements = match.get('replacements', [])

        if not replacements:
            continue  # No hay sugerencias de corrección

        replacement = replacements[0]['value']

        # Reemplazar el texto en el rango especificado
        texto_modificado = (
            texto_modificado[:offset] +
            replacement +
            texto_modificado[offset + length:]
        )

        # Actualizar la corrección acumulada
        offset_correction += len(replacement) - length

    # Corrección de acentos con TextBlob
    blob = TextBlob(texto_modificado)
    texto_corregido_final = str(blob.correct())

    # Corrección de capitalización
    texto_corregido_final = capitalizar_primer_caracter(texto_corregido_final)

    # Eliminación de repeticiones de palabras
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
    texto_corregido = ' '.join(palabras_filtradas)
    return texto_corregido

# Función para separar texto dentro y fuera de comillas
def separar_citas(texto):
    # Expresión regular para encontrar textos entre comillas simples o dobles
    pattern = r'(\".*?\"|“.*?”|‘.*?’)'
    partes = re.split(pattern, texto)
    return partes

# Función para capitalizar la primera letra de un texto
def capitalizar_primer_caracter(texto):
    if not texto:
        return texto
    return texto[0].upper() + texto[1:]

# Función principal para procesar el documento .docx
def procesar_documento(doc_bytes):
    # Cargar el documento
    documento = Document(BytesIO(doc_bytes))
    
    # Iterar sobre cada párrafo y aplicar las correcciones
    for para in documento.paragraphs:
        texto_original = para.text
        if texto_original.strip() == '':
            continue  # Salta párrafos vacíos
        
        # Corregir el texto del párrafo
        texto_corregido = corregir_texto(texto_original)
        
        # Reemplazar el texto del párrafo con el texto corregido
        para.text = texto_corregido
    
    # Guardar el documento corregido en un objeto BytesIO
    corrected_doc = BytesIO()
    documento.save(corrected_doc)
    corrected_doc.seek(0)
    
    return corrected_doc

# Función para dividir textos largos en párrafos usando NLTK
def dividir_en_parrafos(texto, max_sentencias=5):
    # Tokenizar el texto en oraciones
    oraciones = sent_tokenize(texto, language='spanish')
    parrafos = []
    parrafo_actual = []

    for oracion in oraciones:
        parrafo_actual.append(oracion)
        if len(parrafo_actual) >= max_sentencias:
            parrafos.append(' '.join(parrafo_actual))
            parrafo_actual = []
    
    # Añadir el último párrafo si tiene oraciones
    if parrafo_actual:
        parrafos.append(' '.join(parrafo_actual))
    
    return parrafos

# Interfaz de usuario con Streamlit
def main():
    st.set_page_config(page_title="Corrector y Divisor de Textos en Español", layout="wide")
    st.title("Corrector y Divisor de Textos en Español")
    st.write("""
        Esta aplicación permite:
        1. **Corregir documentos `.docx`**: Errores ortográficos, acentos, capitalización, repeticiones de palabras y puntuación.
        2. **Dividir textos largos en párrafos**: Utilizando procesamiento de lenguaje natural para una división lógica.
    """)
    
    # Crear pestañas para separar funcionalidades
    pestañas = st.tabs(["🔧 Corregir Documento `.docx`", "✂️ Dividir Texto en Párrafos"])
    
    # Pestaña 1: Corregir Documento `.docx`
    with pestañas[0]:
        st.header("Corregir Documento `.docx`")
        st.write("Sube un archivo `.docx` para corregir errores ortográficos, acentos, capitalización, repeticiones de palabras y puntuación. **Las citas textuales y las notas a pie de página no serán corregidas.**")
        
        uploaded_file = st.file_uploader("Elige un archivo `.docx`", type="docx")
        
        if uploaded_file is not None:
            st.success("Archivo cargado exitosamente.")
            
            # Procesar el documento al hacer clic en el botón
            if st.button("Corregir Documento"):
                with st.spinner("Procesando el documento..."):
                    try:
                        corrected_doc = procesar_documento(uploaded_file.read())
                        st.success("Documento corregido exitosamente.")
                        
                        # Permitir al usuario descargar el archivo corregido
                        st.download_button(
                            label="Descargar Documento Corregido",
                            data=corrected_doc,
                            file_name="documento_corregido.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    except Exception as e:
                        st.error(f"Error al procesar el documento: {e}")

    # Pestaña 2: Dividir Texto en Párrafos
    with pestañas[1]:
        st.header("Dividir Texto en Párrafos")
        st.write("Puedes cargar un archivo de texto `.txt` o pegar texto largo en el cuadro de texto a continuación para dividirlo en párrafos.")
        
        # Opciones para cargar un archivo o pegar texto
        opciones = ["Cargar Archivo `.txt`", "Pegar Texto"]
        seleccion = st.radio("Selecciona una opción:", opciones)
        
        texto_procesar = ""
        
        if seleccion == "Cargar Archivo `.txt`":
            uploaded_txt = st.file_uploader("Elige un archivo `.txt`", type="txt")
            if uploaded_txt is not None:
                bytes_data = uploaded_txt.read()
                try:
                    texto_procesar = bytes_data.decode('utf-8')
                    st.success("Archivo de texto cargado exitosamente.")
                except UnicodeDecodeError:
                    st.error("Error al decodificar el archivo. Asegúrate de que esté en formato UTF-8.")
        
        elif seleccion == "Pegar Texto":
            texto_procesar = st.text_area("Pega tu texto aquí:", height=300)
        
        if texto_procesar:
            if st.button("Dividir en Párrafos"):
                with st.spinner("Dividiendo el texto en párrafos..."):
                    try:
                        parrafos = dividir_en_parrafos(texto_procesar)
                        st.success("Texto dividido en párrafos exitosamente.")
                        
                        st.write("### Párrafos Resultantes:")
                        for idx, parrafo in enumerate(parrafos, 1):
                            st.write(f"**Párrafo {idx}:** {parrafo}")
                    except Exception as e:
                        st.error(f"Error al dividir el texto: {e}")

if __name__ == "__main__":
    main()
