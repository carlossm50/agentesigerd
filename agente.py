import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
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
