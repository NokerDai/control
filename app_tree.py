"""
streamlit_app_pyvis.py

App Streamlit con canvas explorable tipo Obsidian usando PyVis (vis.js).
Nodos como tarjetas: Imagen / Título / Autor.
Zoom, drag y exploración libre.

Ejecutar:
    pip install streamlit pyvis networkx
    streamlit run streamlit_app_pyvis.py
"""

import json
from pathlib import Path
import uuid
from typing import Dict, List, Optional

import streamlit as st
from pyvis.network import Network
import networkx as nx
import streamlit.components.v1 as components


# -----------------------------
# MODELO DE DATOS
# -----------------------------
class Node:
    def __init__(self, title: str, author: Optional[str] = None, image_url: Optional[str] = None, antes: Optional[List[str]] = None, id: Optional[str] = None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.author = author
        self.image_url = image_url
        self.antes = antes or []

    def to_dict(self):
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

    def add_node(self, title, author=None, image_url=None, antes=None):
        if title in self.nodes:
            raise ValueError("Ya existe ese título")
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
        for d in data:
            n = Node.from_dict(d)
            self.nodes[n.title] = n


# -----------------------------
# STREAMLIT SETUP
# -----------------------------
st.set_page_config(page_title="Árbol de lecturas (Canvas)", layout="wide")
st.title("Árbol de lecturas – Canvas explorable")

DATA_FILE = "reading_tree.json"

if "tree" not in st.session_state:
    tree = ReadingTree()
    tree.load(DATA_FILE)
    st.session_state.tree = tree

tree: ReadingTree = st.session_state.tree


# -----------------------------
# SIDEBAR – AÑADIR OBRAS
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
                tree.add_node(title, author or None, image_url or None, antes)
                tree.save(DATA_FILE)
                st.sidebar.success("Obra añadida")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))


# -----------------------------
# CANVAS EXPLORABLE (PYVIS)
# -----------------------------
st.subheader("Canvas de lecturas")

if tree.nodes:
    G = tree.to_graph()

    net = Network(height="750px", width="100%", directed=True, bgcolor="#ffffff")
    
    # Layout jerárquico: raíces arriba, descendientes abajo
    options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",
                "sortMethod": "directed",
                "levelSeparation": 150,
                "nodeSpacing": 200
            }
        },
        "physics": {"enabled": False}
    }
    net.set_options(json.dumps(options))
    net.barnes_hut()

    # Añadir nodos como tarjetas (imagen + título + autor)
    for title, n in tree.nodes.items():
        label = f"{n.title}
{n.author or ''}"

        if n.image_url:
            net.add_node(
                title,
                label=label,
                title=label,
                shape="image",
                image=n.image_url,
                size=30,
                font={"size": 14},
                borderWidth=1
            )
        else:
            net.add_node(
                title,
                label=label,
                title=label,
                shape="box",
                margin=10,
                font={"size": 14},
                borderWidth=1
            )

            html=html
        )

    # Añadir relaciones
    for u, v in G.edges():
        net.add_edge(u, v, arrows="to")

    # Guardar HTML temporal
    html_file = "canvas.html"
    net.save_graph(html_file)

    # Mostrar en Streamlit
    components.html(Path(html_file).read_text(encoding="utf-8"), height=800, scrolling=True)

else:
    st.info("Aún no hay obras cargadas")