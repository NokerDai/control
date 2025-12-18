"""
streamlit_app_pyvis.py

VERSIÓN COMPATIBLE CON STREAMLIT CLOUD / WEB.

IMPORTANTE:
Streamlit ejecuta el HTML de PyVis dentro de un iframe con sandbox.
Esto IMPIDE overlays JS externos y manipulación directa del DOM.

Solución robusta:
Usar nodos HTML NATIVOS de vis.js (label con <img> + texto) sin overlays.
Esto funciona en web, cloud y local.

Resultado:
Tarjeta real dentro del nodo (imagen arriba, título y autor debajo).
Árbol jerárquico de arriba hacia abajo.
Pantalla completa.
"""

import json
from pathlib import Path
import uuid
from typing import Dict, List, Optional

import streamlit as st
from pyvis.network import Network
import networkx as nx
import streamlit.components.v1 as components


# =============================
# MODELO DE DATOS
# =============================
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
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        self.nodes = {}
        for d in data:
            n = Node.from_dict(d)
            self.nodes[n.title] = n


# =============================
# STREAMLIT SETUP
# =============================
st.set_page_config(page_title="Árbol de lecturas (Canvas)", layout="wide")
st.title("Árbol de lecturas – Canvas explorable")

DATA_FILE = "reading_tree.json"

if "tree" not in st.session_state:
    tree = ReadingTree()
    tree.load(DATA_FILE)
    st.session_state.tree = tree


tree: ReadingTree = st.session_state.tree


# =============================
# SIDEBAR – AÑADIR OBRAS
# =============================
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
                tree.add_node(
                    title=title,
                    author=author or None,
                    image_url=image_url or None,
                    antes=antes,
                )
                tree.save(DATA_FILE)
                st.sidebar.success("Obra añadida")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))


# =============================
# CANVAS (PYVIS COMPATIBLE WEB)
# =============================
st.subheader("Canvas de lecturas")

if not tree.nodes:
    st.info("Aún no hay obras cargadas")
else:
    G = tree.to_graph()

    net = Network(
        height="100vh",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        notebook=False,
    )

    options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",
                "sortMethod": "directed",
                "levelSeparation": 220,
                "nodeSpacing": 260,
                "treeSpacing": 300,
            }
        },
        "physics": {"enabled": False},
        "edges": {
            "arrows": {
                "to": {
                    "enabled": True,
                    "scaleFactor": 1.2
                }
            },
            "smooth": {
                "type": "cubicBezier",
                "forceDirection": "vertical",
                "roundness": 0.4
            },
            "width": 1.6
        }
    }
    net.set_options(json.dumps(options))(json.dumps(options))

    # Nodos como tarjeta: imagen arriba + label abajo
    for title, n in tree.nodes.items():
        # label como texto plano (dos líneas: título y autor)
        label_text = f"{n.title}{n.author or ''}"

        if n.image_url:
            # nodo con imagen; label se mostrará DEBAJO de la imagen en vis.js
            net.add_node(
                title,
                label=label_text,
                shape="image",
                image=n.image_url,
                size=60,
                font={"size": 12},
            )
        else:
            # nodo caja con texto dentro
            net.add_node(
                title,
                label=label_text,
                shape="box",
                margin=10,
                font={"size": 12},
            )

    # Aristas
    for u, v in G.edges():
        net.add_edge(u, v, arrows="to")

    # Render
    html_file = "canvas.html"
    net.save_graph(html_file)

    components.html(
        Path(html_file).read_text(encoding="utf-8"),
        height=900,
        scrolling=True,
    )