"""
streamlit_app_pyvis.py

App Streamlit con canvas explorable tipo Obsidian usando PyVis (vis.js).
Árbol jerárquico de arriba hacia abajo.
Nodos representados como tarjetas HTML: imagen arriba, título y autor debajo.
El canvas ocupa toda la pantalla (100vh).

Correcciones varias: inyección JS más robusta para que las tarjetas HTML se creen incluso si los nombres de variables de pyvis cambian.
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
# CANVAS EXPLORABLE (PYVIS)
# =============================
st.subheader("Canvas de lecturas")

if not tree.nodes:
    st.info("Aún no hay obras cargadas")
else:
    G = tree.to_graph()

    net = Network(
        height="100%",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        notebook=False,
    )

    # Opciones jerárquicas (JSON válido)
    options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",
                "sortMethod": "directed",
                "levelSeparation": 150,
                "nodeSpacing": 200,
            }
        },
        "physics": {"enabled": False},
        # ocultamos nodos por defecto (vamos a renderizar tarjetas HTML encima)
        "nodes": {"shape": "dot", "size": 0, "font": {"color": "transparent"}},
    }
    net.set_options(json.dumps(options))

    # Añadir nodos como elementos de datos (serán representados luego como tarjetas HTML)
    for title, n in tree.nodes.items():
        label = f"{n.title}\n{n.author or ''}"
        # guardamos image en la propiedad 'image' (pyvis/vis.js la reconoce)
        net.add_node(
            title,
            label=label,
            title=label,
            image=n.image_url or "",
            author=n.author or "",
            shape="dot",
            size=0,
        )

    # Añadir aristas
    for u, v in G.edges():
        net.add_edge(u, v, arrows="to")

    # Guardar HTML temporal
    html_file = "canvas.html"
    net.save_graph(html_file)

    # Post-procesar el HTML para inyectar tarjetas HTML sobre el canvas y ajustar tamaño a pantalla completa
    html = Path(html_file).read_text(encoding="utf-8")

    inject = """

    <style>
    html, body, #mynetwork { height: 100vh; margin: 0; padding: 0; }
    #mynetwork { position: relative; }
    #card-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 50; }
    .node-card { position: absolute; width: 160px; pointer-events: auto; background: #fff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.12); overflow: hidden; text-align: center; font-family: Arial, Helvetica, sans-serif; z-index: 60; }
    .node-card img { width: 100%; height: auto; display: block; }
    .node-card .card-title { font-weight: 600; padding: 6px 8px; font-size: 14px; }
    .node-card .card-author { font-size: 12px; color: #555; padding-bottom: 8px; }
    </style>

    <script>
    (function() {
        function getContainer() {
            return document.getElementById('mynetwork') || document.querySelector('.vis-network') || document.querySelector('div[id^="mynetwork"]');
        }

        function getNetworkObject() {
            return window.network || (typeof network !== 'undefined' ? network : null);
        }

        function getNodesDataSet(net) {
            if (window.nodes) return window.nodes;
            if (typeof nodes !== 'undefined') return nodes;
            try {
                if (net && net.body && net.body.data && net.body.data.nodes) return net.body.data.nodes;
            } catch(e) {}
            return null;
        }

        function createCards() {
            var container = getContainer();
            var net = getNetworkObject();
            var nodesDS = getNodesDataSet(net);
            if (!container || !net || !nodesDS) {
                // si falla, intentamos reintentar más tarde
                setTimeout(createCards, 200);
                return;
            }

            // crear overlay si no existe
            var overlay = document.getElementById('card-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'card-overlay';
                container.appendChild(overlay);
            }

            // limpiar overlay
            overlay.innerHTML = '';

            var positions = net.getPositions();
            var allNodes = nodesDS.get();

            allNodes.forEach(function(nd) {
                var id = nd.id;
                var pos = positions[id];
                if (!pos) return;

                var domPos = net.canvasToDOM(pos);

                var card = document.createElement('div');
                card.className = 'node-card';
                card.style.left = domPos.x + 'px';
                card.style.top = domPos.y + 'px';
                card.style.transform = 'translate(-50%, -50%)';

                var imgHtml = nd.image ? ('<img src="' + nd.image + '" alt=""/>') : '';
                var lines = (nd.label || '').split('\n');
                var title = lines[0] || '';
                var author = lines[1] || nd.author || '';

                card.innerHTML = imgHtml + '<div class="card-title">' + title + '</div>' + '<div class="card-author">' + author + '</div>';

                // arrastrar tarjeta: actualiza visualmente y luego mueve el nodo en la red
                card.style.cursor = 'grab';
                var dragging = false;
                var startX = 0, startY = 0;

                card.addEventListener('mousedown', function(e) {
                    dragging = true;
                    startX = e.clientX;
                    startY = e.clientY;
                    card.style.cursor = 'grabbing';
                    e.preventDefault();
                });

                window.addEventListener('mousemove', function(e) {
                    if (!dragging) return;
                    var dx = e.clientX - startX;
                    var dy = e.clientY - startY;
                    startX = e.clientX;
                    startY = e.clientY;
                    var left = parseFloat(card.style.left || 0);
                    var top = parseFloat(card.style.top || 0);
                    card.style.left = (left + dx) + 'px';
                    card.style.top = (top + dy) + 'px';
                });

                window.addEventListener('mouseup', function(e) {
                    if (!dragging) return;
                    dragging = false;
                    card.style.cursor = 'grab';

                    // al soltar, convertir posición DOM a canvas y mover el nodo
                    var rect = container.getBoundingClientRect();
                    var x = parseFloat(card.style.left) - rect.left;
                    var y = parseFloat(card.style.top) - rect.top;
                    var canvasPos = net.DOMtoCanvas({ x: x, y: y });

                    try {
                        net.moveNode(id, canvasPos.x, canvasPos.y);
                    } catch(err) {
                        console.warn('No se pudo mover el nodo:', err);
                    }
                });

                overlay.appendChild(card);
            });
        }

        // re-renderizar tarjetas en eventos importantes
        function attachEvents() {
            var net = getNetworkObject();
            if (!net) { setTimeout(attachEvents, 200); return; }
            net.on('stabilizationIterationsDone', function() { setTimeout(createCards, 80); });
            net.on('afterDrawing', function() { setTimeout(createCards, 20); });
            net.on('dragEnd', function() { setTimeout(createCards, 50); });
            net.on('zoom', function() { setTimeout(createCards, 20); });
            window.addEventListener('resize', function() { setTimeout(createCards, 200); });
        }

        if (document.readyState === 'complete') {
            attachEvents();
            setTimeout(createCards, 200);
        } else {
            window.addEventListener('load', function() { attachEvents(); setTimeout(createCards, 200); });
        }
    })();
    </script>

    </body>
    """

    # inyectar antes del cierre </body>
    if '</body>' in html:
        html = html.replace('</body>', inject)
    else:
        html = html + inject

    # mostrar en streamlit ocupando toda la pantalla
    components.html(html, height=900, scrolling=True)