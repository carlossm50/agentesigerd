MY_STYLE = """
<style>
    /* Estilo del contenedor principal */
    .reportview-container {
        background-color: #0e1117;
    }
    
    /* Encabezado con gradiente llamativo */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        margin: 0;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
    }
    .main-header p {
        margin: 8px 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Estilos para badges de fuentes de búsqueda */
    .source-badge {
        display: inline-block;
        background-color: #262730;
        border: 1px solid #464855;
        border-radius: 20px;
        padding: 4px 12px;
        margin: 4px;
        font-size: 0.85rem;
        color: #00d4ff;
        text-decoration: none;
        transition: all 0.3s ease;
    }
    .source-badge:hover {
        background-color: #00d4ff;
        color: #121212;
        border-color: #00d4ff;
        transform: translateY(-2px);
    }
    
    /* Separador decorativo */
    .decorator-line {
        height: 4px;
        background: linear-gradient(90deg, #ff8a00, #da1b60);
        margin-bottom: 20px;
        border-radius: 2px;
    }
</style>
"""