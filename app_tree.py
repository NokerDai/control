import json
from pathlib import Path
import uuid
from typing import Dict, List, Optional
import base64 # Necesario para el truco del SVG

import streamlit as st
from pyvis.network import Network
import networkx as nx
import streamlit.components.v1 as components


# -----------------------------
# Modelo de datos (Sin cambios)
# -----------------------------
class Node:
    def __init__(
        self,
        title: str,
        author: Optional[str] = None,
        image_url: Optional[str] = None,
        antes: Optional[List[str]] = None,
        id: Optional[str] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.author = author
        self.image_url = image_url
        self.antes = antes or []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "image_url": self.image_url,
            "antes": self.antes,
        }

    @staticmethod
    def from_dict(d: Dict):
        return Node(
            id=d.get("id"),
            title=d["title"],
            author=d.get("author"),
            image_url=d.get("image_url"),
            antes=d.get("antes", []),
        )


class ReadingTree:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(
        self,
        title: str,
        author: Optional[str] = None,
        image_url: Optional[str] = None,
        antes: Optional[List[str]] = None,
    ):
        if title in self.nodes:
            raise ValueError("Ya existe una obra con ese título")
        self.nodes[title] = Node(title, author, image_url, antes or [])

    def to_graph(self) -> nx.DiGraph:
        G = nx.DiGraph()
        for t in self.nodes:
            G.add_node(t)
        for t, n in self.nodes.items():
            for b in n.antes:
                if b in self.nodes:
                    G.add_edge(b, t)
        return G

    def save(self, path: str):
        data = [n.to_dict() for n in self.nodes.values()]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        self.nodes = {}
        for d in data:
            n = Node.from_dict(d)
            self.nodes[n.title] = n


# -----------------------------
# Funciones Auxiliares (NUEVO)
# -----------------------------
def create_card_svg(title: str, author: Optional[str], image_url: Optional[str]) -> str:
    """
    Genera un SVG dinámico que parece una carta coleccionable.
    Incrusta la imagen (si existe) y el texto dentro de un rectángulo.
    """
    # Dimensiones de la carta
    card_width = 220
    card_height = 320
    image_height = 200
    padding = 12

    # Textos por defecto
    safe_title = title[:50] + "..." if len(title) > 50 else title
    safe_author = author[:40] + "..." if author and len(author) > 40 else (author or "")
    
    # Colores estilo carta
    bg_color = "#2A2A2A"
    border_color = "#D4AF37" # Un dorado para el borde estilo carta rara
    text_color_title = "#FFFFFF"
    text_color_author = "#CCCCCC"
    placeholder_color = "#141414"

    # Construcción del SVG
    svg_content = f'''
    <svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="{card_height}">
      <defs>
        <clipPath id="rounded-corners">
          <rect x="{padding}" y="{padding}" width="{card_width - padding*2}" height="{image_height}" rx="8" ry="8"/>
        </clipPath>
      </defs>

      <rect x="0" y="0" width="{card_width}" height="{card_height}" rx="15" ry="15" fill="{bg_color}" stroke="{border_color}" stroke-width="4"/>
      
      <rect x="{padding}" y="{padding}" width="{card_width - padding*2}" height="{image_height}" rx="8" ry="8" fill="{placeholder_color}"/>
    '''

    # Área de Imagen
    if image_url and image_url.strip():
        # Usamos preserveAspectRatio="xMidYMid slice" para que actúe como object-fit: cover
        svg_content += f'''
        <image href="{image_url}" x="{padding}" y="{padding}" width="{card_width - padding*2}" height="{image_height}" 
               preserveAspectRatio="xMidYMid slice" clip-path="url(#rounded-corners)"/>
        '''
    else:
        # Placeholder si no hay URL
        svg_content += f'''
         <text x="{card_width/2}" y="{image_height/2 + padding}" text-anchor="middle" fill="#555555" font-family="Arial" font-size="14">Sin imagen</text>
        '''

    # Área de Texto (Título y Autor debajo de la imagen)
    text_start_y = image_height + padding + 30
    svg_content += f'''
      <text x="{card_width/2}" y="{text_start_y}" text-anchor="middle" fill="{text_color_title}" 
            font-family="'Segoe UI', Arial, sans-serif" font-size="16" font-weight="bold">{safe_title}</text>
      
      <text x="{card_width/2}" y="{text_start_y + 25}" text-anchor="middle" fill="{text_color_author}" 
            font-family="'Segoe UI', Arial, sans-serif" font-size="13" font-style="italic">{safe_author}</text>
    </svg>
    '''
    
    # Codificar el SVG a base64 para usarlo como Data URI
    encoded_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{encoded_svg}"


# -----------------------------
# Streamlit setup
# -----------------------------
st.set_page_config(page_title="Árbol de lecturas (Canvas)", layout="wide")
st.title("Árbol de lecturas – Canvas estilo Cartas")

DATA_FILE = "reading_tree.json"

if "tree" not in st.session_state:
    tree = ReadingTree()
    tree.load(DATA_FILE)
    st.session_state.tree = tree


tree: ReadingTree = st.session_state.tree


# -----------------------------
# Sidebar: añadir obras
# -----------------------------
st.sidebar.header("Añadir obra")

with st.sidebar.form("add_form"):
    title = st.text_input("Título")
    author = st.text_input("Autor")
    image_url = st.text_input("URL de imagen")
    antes = st.multiselect("Leer antes", options=sorted(tree.nodes.keys()))
    submitted = st.form_submit_button("Añadir")

    if submitted:
        if not title:
            st.sidebar.error("El título es obligatorio")
        else:
            try:
                tree.add_node(title=title, author=author or None, image_url=image_url or None, antes=antes)
                tree.save(DATA_FILE)
                st.sidebar.success("Obra añadida")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))


# -----------------------------
# Canvas interactivo (PyVis)
# -----------------------------
st.subheader("Canvas de lecturas")

if not tree.nodes:
    st.info("Aún no hay obras cargadas")
else:
    G = tree.to_graph()

    net = Network(
        height="90vh", # Un poco menos para ajustar
        width="100%",
        directed=True,
        bgcolor="#0E0E11", # Fondo muy oscuro para que resalten las cartas
        notebook=False,
    )

    options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",
                "sortMethod": "directed",
                # Aumentamos la separación porque las cartas son grandes
                "levelSeparation": 350, 
                "nodeSpacing": 250,
                "treeSpacing": 300,
            }
        },
        "physics": {"enabled": False},
        "interaction": {
            "hover": True, 
            "zoomView": True,
             # Importante para poder mover cartas grandes fácilmente
            "dragNodes": True
        },
        "edges": {
            "arrows": {
                "to": {"enabled": True, "scaleFactor": 1.5}
            },
            "smooth": {"type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.5},
            "width": 3,
            "color": {"color": "#D4AF37", "opacity": 0.6}, # Conectores dorados
            "shadow": {"enabled": True, "color": "black", "size": 5, "x": 2, "y": 2}
        },
        "configure": {"enabled": False}
    }

    net.set_options(json.dumps(options))

    # =========================================================================
    # BUCLE PRINCIPAL: Usando el generador de SVG
    # =========================================================================
    for title_key, n in tree.nodes.items():
        # 1. Generamos la imagen SVG para este nodo
        svg_card_uri = create_card_svg(n.title, n.author, n.image_url)

        net.add_node(
            title_key,
            # IMPORTANTE: No ponemos 'label'. El texto ya está dentro del SVG.
            # label=... (eliminado)
            
            # Usamos 'image' para que renderice el SVG que hemos creado
            shape="image",
            image=svg_card_uri,
            
            # Tamaño de la imagen en el canvas (debe coincidir aprox con el viewBox del SVG)
            size=110, # La mitad del width del SVG (220/2) suele funcionar bien como escala base
            
            # Sombra general para dar profundidad a la carta
            shadow={
                "enabled": True,
                "color": "rgba(0,0,0,0.8)",
                "size": 15,
                "x": 5,
                "y": 5,
            },
            borderWidth=0, # El borde ya está en el SVG
            shapeProperties={
                "useImageSize": False, # Usar el tamaño definido por 'size'
                "interpolation": True # Mejor calidad al hacer zoom
            }
        )

    # Aristas
    for u, v in G.edges():
        net.add_edge(u, v)

    # Guardar y renderizar
    html_file = "canvas_cards.html"
    net.save_graph(html_file)
    html_content = Path(html_file).read_text(encoding="utf-8")

    # Ajuste de altura para ver bien las cartas grandes
    components.html(html_content, height=1000, scrolling=True)