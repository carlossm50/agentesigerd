import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import  Dict
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from api_keys import GEMINI_API_KEY
from models import GEMINI_FLASH

# Instanciamos el modelo de lenguaje de forma global
llm = ChatGoogleGenerativeAI(
    model=GEMINI_FLASH,
    temperature=0,
    google_api_key=GEMINI_API_KEY
)

# Optimizamos la carga y el procesamiento de documentos utilizando la caché de Streamlit
# Esto evita que se vuelvan a leer y vectorizar los PDFs en cada interacción de la UI
@st.cache_resource(show_spinner="Indexando documentos PDF del sistema SIGERD...")
def inicializar_base_conocimiento():
    docs = []
    directorio_datos = Path("datos/")
    
    # Creamos el directorio si no existe para evitar errores
    directorio_datos.mkdir(exist_ok=True)
    
    # Cargar archivos PDF
    for n in directorio_datos.glob("*.pdf"):
        try:
            loader = PyMuPDFLoader(str(n))
            docs.extend(loader.load())
            print(f"Archivo cargado: {n.name}")
        except Exception as e:
            print(f"Error cargando archivo: {n.name}: {e}")

    print(f"Total de documentos cargados: {len(docs)}")

    if not docs:
        print("ADVERTENCIA: No se encontraron documentos PDF en la carpeta 'datos/'.")
        # Creamos un vectorstore vacío o dummy para que no falle la app si no hay PDFs aún
        # En producción, asegúrate de tener al menos un PDF en datos/
        return None

    # Segmentar los textos
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    docs_splits = splitter.split_documents(docs)

    # Inicializar embeddings de Google
    modelo_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=GEMINI_API_KEY
    )

    # Crear el Vectorstore con FAISS
    vectorstore = FAISS.from_documents(docs_splits, modelo_embeddings)
    
    # Crear el recuperador (Retriever)
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"score_threshold": 0.3, "k": 4}
    )
    
    return retriever

# Intentar inicializar el recuperador
retriever = inicializar_base_conocimiento()

# Prompt del sistema para el especialista escolar
prompt_rag = ChatPromptTemplate(
    [
        ("system",
            """Eres el especialista en procesos de inscripcion escolar del sistema SIGERD.
            Responde siempre utilizando los conocimientos del contexto pasadas a ti.
            Si no hay informacion sobre la pregunta en los datos, responde solo 'No lo se'.
            """
        ),
        ("human", "Contexto: {context}\nPregunta del empleado: {input}")
    ]
)

document_chain = create_stuff_documents_chain(llm, prompt_rag)

def busqueda_de_respuestas_RAG(pregunta) -> Dict:
  # Si no hay documentos o falló la indexación por falta de PDFs
  if retriever is None:
      return {
          "respuesta": "No hay documentos de SIGERD cargados en el sistema.",
          "citaciones": [],
          "documentos_encontrados": False
      }

  documentos_relacionados = retriever.invoke(pregunta)
  if not documentos_relacionados:
    return {
        "respuesta": "No lo sé",
        "citaciones": [],
        "documentos_encontrados": False
    }
  
  answer = document_chain.invoke({
    "input": pregunta,
    "context": documentos_relacionados
  })
  
  if answer.rstrip(".!?") == "No lo sé" or answer.strip() == "No lo se":
    return {
        "respuesta": "No lo sé",
        "citaciones": [],
        "documentos_encontrados": False
    }
    
  return {
    "respuesta": answer,
    "citaciones": documentos_relacionados,
    "documentos_encontrados": True
  }

# Ejecución de pruebas aislada (solo corre si ejecutas "python agente.py" directamente)
if __name__ == "__main__":
    print("\n--- EJECUTANDO PRUEBAS DEL AGENTE ---")
    mensajes_de_prueba = [
        "¿Como puedo acceder al sistema?",
        "Quiero hacer una busqueda de estudiante",
        "¿Cómo reinscribo un estudiante?",
        "¿Como registro un personal nuevo?",
        "¿Quién fue Napoleon Bonaparte?"
    ]

    for pregunta in mensajes_de_prueba:
        respuesta_RAG = busqueda_de_respuestas_RAG(pregunta)
        print(f"PREGUNTA: {pregunta}")
        print(f"RESPUESTA: {respuesta_RAG['respuesta']}")
        print(f"DOCUMENTOS ENCONTRADOS: {respuesta_RAG['documentos_encontrados']}")
        if respuesta_RAG['documentos_encontrados']:
            for i, citacion in enumerate(respuesta_RAG['citaciones']):
                print(f"CITACION {i + 1}:")
                # Manejar metadatos de forma segura por si varía el parser de documentos
                file_path = citacion.metadata.get('file_path', citacion.metadata.get('source', 'Desconocido'))
                print(f"Camino del documento: {file_path}")
                print(f"Contenido: {citacion.page_content.replace('\n', ' ')}")
                print("-------------------")