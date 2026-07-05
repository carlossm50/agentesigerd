import streamlit as st
import requests
import time
import os
from api_keys import GEMINI_API_KEY
from style import MY_STYLE

# Importamos la lógica de búsqueda de nuestro agente RAG adaptado
from agente import busqueda_de_respuestas_RAG, retriever

api_key = GEMINI_API_KEY

# Configuración inicial de la página de Streamlit
st.set_page_config(
    page_title="Asistente de IA Inteligente - SIGERD",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para mejorar el aspecto visual (Premium, moderno y adaptable)
st.markdown(MY_STYLE, unsafe_allow_html=True)

# Inicializar estados de la sesión de Streamlit para el historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Encabezado principal de la interfaz
st.markdown("""
    <div class="main-header">
        <h1>Asistente de IA SIGERD</h1>
        <p>Realiza consultas sobre inscripción escolar, procesos del sistema o explora la web</p>
    </div>
    <div class="decorator-line"></div>
""", unsafe_allow_html=True)

# --- PANEL LATERAL (Configuraciones de la IA) ---
with st.sidebar:
    st.header("⚙️ Configuración del Asistente")
    
    # 1. Selector del Modo de Operación (Integrando RAG de agente.py)
    st.subheader("📁 Origen de Datos")
    modo_consulta = st.radio(
        "Modo de consulta:",
        [
            "Híbrido (RAG + Web)", 
            "Solo RAG (Documentos SIGERD) 🌟", 
            "Solo Chat General (Web)"
        ],
        index=1,
        help=(
            "Híbrido busca primero en tus PDFs de SIGERD y si no encuentra respuesta, "
            "busca en Google. Solo RAG se limita a tus documentos locales."
        )
    )
    
    st.write("---")
    
    # Selector de Personalidades (Instrucciones del Sistema para consultas web)
    personality = st.selectbox(
        "Personalidad de la IA (para modo General/Web):",
        ["Asistente General", "Programador Experto", "Escritor Creativo", "Traductor Políglota"]
    )
    
    # Mapeo de instrucciones de sistema según selección
    system_instructions = {
        "Asistente General": "Eres un asistente de inteligencia artificial amigable, educado y altamente servicial. Responde siempre de manera concisa y útil.",
        "Programador Experto": "Eres un ingeniero de software senior experimentado. Analiza problemas, escribe código limpio, bien comentado y con buenas prácticas de desarrollo.",
        "Escritor Creativo": "Eres un redactor y autor literario creativo. Redacta de forma elocuente, utiliza ricas metáforas y ayuda al usuario a expandir sus ideas narrativas.",
        "Traductor Políglota": "Eres un traductor experto y lingüista profesional. Ayuda al usuario a traducir textos con la gramática perfecta, explicando sutiles diferencias lingüísticas si es relevante."
    }
    
    st.write("---")
    
    # Habilitar o deshabilitar Google Search Grounding de la API de Gemini
    use_google_search = st.toggle(
        "🔍 Habilitar Búsqueda en Google", 
        value=True, 
        help="Permite a la IA buscar en internet en tiempo real para brindarte información actualizada si no está en el RAG."
    )
    
    # Indicador de estado del RAG
    st.write("---")
    if retriever is not None:
        st.success("✅ Base de Conocimiento RAG (SIGERD) lista.")
    else:
        st.warning("⚠️ Sin documentos PDF en la carpeta 'datos/'. El modo RAG no devolverá resultados.")
    
    st.write("---")
    
    # Opción para restablecer la sesión de chat
    if st.button("🗑️ Borrar Historial de Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- FUNCIÓN CONECTORA CON LA API DE GEMINI CON RETRY & BACKOFF ---
def call_gemini_api(prompt, system_prompt, use_search):
    """
    Realiza una solicitud HTTP POST a la API de Gemini usando requests.
    Implementa un mecanismo de reintento exponencial (1s, 2s, 4s, 8s, 16s) ante fallos.
    """
    # Endpoint oficial de Gemini 2.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    # Estructuración de los datos del Payload
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }
    
    # Si se activa la búsqueda en Google, agregarla a la lista de herramientas (Tools)
    if use_search:
        payload["tools"] = [{"google_search": {}}]
        
    headers = {"Content-Type": "application/json"}
    
    # Configuración de los reintentos (Exponential Backoff)
    retry_delays = [1, 2, 4, 8, 16]
    
    for delay in retry_delays:
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=35)
            
            # Si la respuesta es exitosa (HTTP 200)
            if response.status_code == 200:
                result = response.json()
                
                # Extraer el texto de la respuesta
                candidates = result.get("candidates", [])
                if not candidates:
                    return "No se ha podido generar una respuesta apropiada.", []
                
                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    return "No se recibió contenido en la respuesta.", []
                
                text_response = content_parts[0].get("text", "")
                
                # Extraer fuentes web de la búsqueda de Google (si se habilitó)
                sources = []
                grounding_metadata = candidates[0].get("groundingMetadata", {})
                attributions = grounding_metadata.get("groundingAttributions", [])
                
                for attr in attributions:
                    web_info = attr.get("web", {})
                    if web_info:
                        sources.append({
                            "title": web_info.get("title", "Fuentes de Información"),
                            "uri": web_info.get("uri", "#")
                        })
                
                return text_response, sources
                
            # Si hay error 429 (Límite de tasa) u otros errores del servidor, reintentar con delay
            else:
                time.sleep(delay)
                
        except requests.exceptions.RequestException:
            # En caso de fallas de conexión o tiempo de espera agotado, aplicar el delay
            time.sleep(delay)
            
    # Si todos los reintentos fallaron, elevar un error descriptivo
    raise Exception("Error de conexión: No se pudo contactar con la API de Gemini después de varios intentos. Verifica tu conectividad.")

# --- DISPLAY DEL HISTORIAL DE CHAT ---
# Renderizar todos los mensajes previos guardados en la sesión actual
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # Si el mensaje del asistente contiene fuentes web
        if "sources" in message and message["sources"]:
            st.markdown("**Fuentes web consultadas:**")
            for src in message["sources"]:
                st.markdown(f'<a href="{src["uri"]}" target="_blank" class="source-badge">🌐 {src["title"]}</a>', unsafe_allow_html=True)
                
        # Si contiene citas del RAG (Documentos locales)
        if "citations" in message and message["citations"]:
            st.markdown("**Documentos de SIGERD consultados:**")
            for idx, cit in enumerate(message["citations"]):
                source_name = cit.get("source", "Documento SIGERD")
                content_preview = cit.get("content", "")
                page = cit.get("page", "")
                with st.expander(f"📄 [{idx+1}] {source_name} {f'(Pág. {page})' if page else ''}"):
                    st.write(f"*{content_preview}*")

# --- CAPTURA DE NUEVO MENSAJE DEL USUARIO ---
if user_input := st.chat_input("Escribe tu pregunta para el Asistente de IA..."):
    
    # 1. Mostrar el mensaje del usuario en el contenedor
    with st.chat_message("user"):
        st.write(user_input)
        
    # Guardar en el historial de sesión
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 2. Generar y mostrar la respuesta del Asistente
    with st.chat_message("assistant"):
        with st.spinner("Procesando tu consulta..."):
            try:
                ai_response = ""
                web_sources = []
                rag_citations = []
                documentos_encontrados = False
                
                # --- PASO A: EJECUTAR BÚSQUEDA RAG SI ESTÁ ACTIVA ---
                if "RAG" in modo_consulta:
                    respuesta_RAG = busqueda_de_respuestas_RAG(user_input)
                    
                    if respuesta_RAG["documentos_encontrados"]:
                        ai_response = respuesta_RAG["respuesta"]
                        documentos_encontrados = True
                        
                        # Extraer información de citas para mostrarla estéticamente
                        for doc in respuesta_RAG["citaciones"]:
                            orig_path = doc.metadata.get("file_path", doc.metadata.get("source", "Archivo SIGERD"))
                            # Simplificar el path para mostrar solo el nombre del archivo
                            file_name = os.path.basename(orig_path)
                            page = doc.metadata.get("page", "")
                            
                            rag_citations.append({
                                "source": file_name,
                                "content": doc.page_content.strip(),
                                "page": page + 1 if isinstance(page, int) else page # PyMuPDF suele indexar desde 0
                            })
                
                # --- PASO B: FALLBACK / CHAT GENERAL (SI EL RAG NO ENCONTRÓ O ESTÁ APAGADO) ---
                if not documentos_encontrados:
                    if "Solo RAG" in modo_consulta:
                        ai_response = "Lo siento, no encontré información sobre eso en los documentos del sistema SIGERD."
                    else:
                        # Modo Híbrido (RAG no encontró) o Modo Solo Chat General
                        current_system_prompt = system_instructions[personality]
                        
                        # Modificamos el system prompt ligeramente en el modo híbrido para informar al usuario
                        if "Híbrido" in modo_consulta:
                            current_system_prompt += (
                                " Nota: La base de datos local de SIGERD no contenía información directa sobre esto, "
                                "así que utiliza tu conocimiento general o búsqueda web para responder cordialmente."
                            )
                        
                        ai_response, web_sources = call_gemini_api(user_input, current_system_prompt, use_google_search)
                
                # --- PASO C: MOSTRAR RESPUESTA Y CITAS EN LA UI ---
                st.write(ai_response)
                
                # Si es respuesta del RAG, mostrar los PDFs consultados
                if rag_citations:
                    st.write("")
                    st.markdown("**Documentos de SIGERD consultados:**")
                    for idx, cit in enumerate(rag_citations):
                        source_name = cit["source"]
                        content_preview = cit["content"]
                        page = cit["page"]
                        # Creamos un bloque expandible interactivo de Streamlit para cada cita
                        with st.expander(f"📄 [{idx+1}] {source_name} {f'(Pág. {page})' if page else ''}"):
                            st.write(f"*{content_preview}*")
                
                # Si hay fuentes web asociadas (por fallback en modo Híbrido o Chat General)
                if web_sources:
                    st.write("")
                    st.markdown("**Fuentes web consultadas:**")
                    for src in web_sources:
                        st.markdown(f'<a href="{src["uri"]}" target="_blank" class="source-badge">🌐 {src["title"]}</a>', unsafe_allow_html=True)
                
                # Guardar la respuesta del asistente en el historial de sesión
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ai_response,
                    "sources": web_sources,
                    "citations": rag_citations
                })
                
            except Exception as e:
                # Mostrar un mensaje de error elegante y amigable en la interfaz
                st.error(f"⚠️ Ocurrió un inconveniente: {str(e)}")
