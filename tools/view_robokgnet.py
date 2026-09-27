"""Serve a small, offline RDF neighborhood viewer using rdflib and stdlib HTTP."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote
import webbrowser

from rdflib import Graph, Literal, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parents[1]
FILES = {'wordnet': 'robokgwordnet.ttl', 'conceptnet': 'robokgconceptnet.ttl'}
WN = 'https://w3id.org/robokgnet/wordnet/schema#'
CN = 'https://w3id.org/robokgnet/conceptnet/schema#'
AT_LOCATION = URIRef('http://api.conceptnet.io/r/AtLocation')
MAPPING = URIRef(CN + 'mapsToWordNet')
SOURCE = URIRef('http://purl.org/dc/terms/source')
# Type/source metadata belongs in the inspector, not in the neighborhood layout.
HIDDEN = {RDF.type, SOURCE}


def short(uri):
    return str(uri).rsplit('#', 1)[-1].rsplit('/', 1)[-1]


class Viewer:
    def __init__(self, graph, mode):
        self.graph, self.mode = graph, mode
        resources = set(graph.subjects()) | {o for o in graph.objects() if isinstance(o, URIRef)}
        self.nodes = {}
        for uri in sorted(resources, key=str):
            if not isinstance(uri, URIRef):
                continue
            pos = str(graph.value(uri, URIRef(WN + 'partOfSpeech')) or '')
            # Minimal WordNet RDF keeps canonical identity in the URI itself.
            if '/wordnet/' in str(uri) and '/synset/' in str(uri):
                parts = str(uri).rsplit('.', 2)
                if len(parts) == 3:
                    pos = {'n': 'noun', 'v': 'verb'}.get(parts[-2], pos)
            if pos in ('noun', 'verb'):
                kind = pos
            elif (uri, RDF.type, URIRef(CN + 'AtLocationAssertion')) in graph:
                kind = 'assertion'
            elif (uri, RDF.type, URIRef(CN + 'ConceptNetConcept')) in graph:
                kind = 'concept'
            elif str(uri).startswith('http://wordnet-rdf.princeton.edu/wn31/'):
                kind = 'wn31'
            else:
                kind = 'metadata'
            label = str(graph.value(uri, RDFS.label) or graph.value(uri, URIRef(CN + 'conceptId')) or short(uri))
            if kind == 'concept':
                path = urlparse(str(uri)).path.split('/')
                label = unquote(path[3]).replace('_', ' ') if len(path) > 3 else label
            elif kind == 'wn31':
                # External targets have no imported labels; do not invent synset names.
                label = 'WordNet 3.1 · ' + unquote(short(uri)).replace('+', ' ').replace('_', ' ')
            elif kind == 'assertion':
                label = 'AtLocation assertion'
            else:
                label = label.replace('_', ' ')
            self.nodes[str(uri)] = {'id': str(uri), 'label': label, 'kind': kind}
        # A read-only projection: assertions become semantic edges; RDF stays intact.
        self.semantic = Graph()
        self.evidence = {}
        for predicate in (RDFS.subClassOf, MAPPING, AT_LOCATION):
            for triple in graph.triples((None, predicate, None)):
                if triple[0] != URIRef(CN + 'AtLocationAssertion'):
                    self.semantic.add(triple)
        for assertion in graph.subjects(RDF.type, URIRef(CN + 'AtLocationAssertion')):
            subject, predicate, obj = (graph.value(assertion, p) for p in (RDF.subject, RDF.predicate, RDF.object))
            if predicate == AT_LOCATION and isinstance(subject, URIRef) and isinstance(obj, URIRef):
                triple = (subject, predicate, obj)
                self.semantic.add(triple)
                self.evidence.setdefault(tuple(map(str, triple)), []).append(str(assertion))
        self.search_text = {}
        for uri, node in self.nodes.items():
            labels = [str(o) for o in graph.objects(URIRef(uri)) if isinstance(o, Literal)]
            self.search_text[uri] = ' '.join([uri, node['label'], *labels]).lower()

    def search(self, query, view="semantic"):
        query = query.lower().strip()
        matches = [n for u, n in self.nodes.items() if query and query in self.search_text[u]
                   and (view == 'raw' or n['kind'] not in ('assertion', 'metadata'))]
        matches.sort(key=lambda n: (n['label'].lower() != query, n['kind'] != 'concept', n['kind'] == 'metadata', len(n['id']), n['label'], n['id']))
        return {'nodes': matches[:40], 'total': len(matches)}

    def inspect(self, uri):
        subject = URIRef(uri)
        return {**self.nodes[uri], 'properties': [
            {'predicate': str(p), 'value': str(o), 'resource': isinstance(o, URIRef)}
            for p, o in sorted(self.graph.predicate_objects(subject), key=lambda x: (str(x[0]), str(x[1])))
        ], 'incoming': sum(1 for _ in self.graph.triples((None, None, subject)))}

    def neighborhood(self, uri, offset=0, limit=40, view='semantic', relation='all', mappings=False):
        if view not in ('semantic', 'raw') or relation not in ('all', 'atlocation', 'mappings', 'hierarchy'):
            raise ValueError('Unknown view or relation filter')
        subject = URIRef(uri)
        # Switching away from a raw assertion returns to its actual subject.
        if view == 'semantic' and self.nodes[uri]['kind'] == 'assertion':
            subject = self.graph.value(subject, RDF.subject) or subject
            uri = str(subject)
        graph = self.graph if view == 'raw' else self.semantic
        edges = set(graph.triples((subject, None, None))) | set(graph.triples((None, None, subject)))

        def visible(s, p, o):
            if p in HIDDEN or not isinstance(o, URIRef):
                return False
            if relation == 'mappings':
                return p == MAPPING
            if relation == 'hierarchy':
                return p == RDFS.subClassOf
            if relation == 'atlocation':
                return p == AT_LOCATION or (view == 'raw' and p in (RDF.subject, RDF.predicate, RDF.object)
                                           and (s, RDF.type, URIRef(CN + 'AtLocationAssertion')) in self.graph)
            return view == 'raw' or p != MAPPING or mappings

        edges = sorted((str(s), str(p), str(o)) for s, p, o in edges
                       if visible(s, p, o) and str(s) in self.nodes and str(o) in self.nodes)
        chosen = edges[offset:offset + limit]
        ids = {uri} | {u for s, _, o in chosen for u in (s, o)}
        return {'nodes': [self.nodes[u] for u in sorted(ids)],
                'edges': [{'source': s, 'predicate': p, 'target': o,
                           'assertions': sorted(self.evidence.get((s, p, o), [])) if view == 'semantic' else []}
                          for s, p, o in chosen],
                'total': len(edges), 'offset': offset, 'limit': limit, 'focus': uri,
                'view': view, 'filter': relation}

    def summary(self):
        candidates = [
            ('Book · ConceptNet', 'http://api.conceptnet.io/c/en/book'),
            ('Physical mug · WordNet 3.0', 'https://w3id.org/robokgnet/wordnet/3.0/synset/mug.n.04'),
            ('Bring action · WordNet 3.0', 'https://w3id.org/robokgnet/wordnet/3.0/synset/bring.v.01'),
        ]
        return {'mode': self.mode, 'triples': len(self.graph), 'resources': len(self.nodes),
                'seeds': [{'label': label, 'id': uri} for label, uri in candidates if uri in self.nodes]}


HTML = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RoboKGNet · Graph explorer</title>
<style>
:root{font-family:system-ui,sans-serif;color:#dce5f3;background:#101725}*{box-sizing:border-box}body{margin:0}header{padding:22px 28px;border-bottom:1px solid #334155}h1{font-size:24px;margin:0 0 6px}p{color:#a8b8cd;line-height:1.5;margin:7px 0}main{display:grid;grid-template-columns:280px 1fr 310px;height:calc(100vh - 145px);min-height:530px}aside{padding:18px;overflow:auto;background:#151f30}section{position:relative;overflow:hidden}input,button,select{font:inherit;color:inherit;background:#23334b;border:1px solid #455571;border-radius:7px;padding:9px}input,select{width:100%}select{margin:6px 0 14px}input[type=checkbox]{width:auto}label.control{display:block;font-size:13px;margin:8px 0}button{cursor:pointer}button:hover{background:#354969}button:disabled{opacity:.4;cursor:default}.result{display:block;width:100%;text-align:left;margin-top:7px;font-size:13px;overflow-wrap:anywhere}.small{font-size:12px;color:#acbdd1}.legend{display:grid;gap:9px;margin:20px 0}.dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:8px}#canvas{width:100%;height:100%;touch-action:none;background:radial-gradient(ellipse at center,#1b2940,#101725)}#bar{position:absolute;top:12px;left:12px;right:12px;display:flex;gap:6px;flex-wrap:wrap}#count{position:absolute;bottom:12px;left:16px;background:#101725d9;padding:8px}.uri{overflow-wrap:anywhere;font-family:monospace;font-size:12px}h2{font-size:18px}.property{padding:9px 0;border-bottom:1px solid #334155;overflow-wrap:anywhere;font-size:12px}.key{color:#88bfff;margin-bottom:5px}.node{cursor:pointer}text{pointer-events:none;fill:#dce5f3;font-size:12px;paint-order:stroke;stroke:#101725;stroke-width:3px}line{stroke:#65748c;stroke-width:1.4}.edge-label{font-size:10px;fill:#aebdd0}#error{color:#ffadad}@media(max-width:1000px){main{grid-template-columns:220px 1fr}#inspector{grid-column:1/-1;max-height:300px}main{height:auto}section{height:600px}}
</style>
<header><h1>RoboKGNet <span style="color:#85a8d7">/ graph explorer</span></h1>
<p id="summary">Loading graph…</p><p class="small">Objects, locations, and their relationships. Search a concept to explore; mappings are optional.</p></header>
<main><aside><label class="control" for="view">View</label><select id="view"><option value="semantic">Simplified semantic view</option><option value="raw">Raw RDF view</option></select>
<label class="control" for="filter">Relations</label><select id="filter"><option value="all">Concept neighborhood</option><option value="atlocation">Only AtLocation</option><option value="mappings">Only mappings</option><option value="hierarchy">Only WordNet hierarchy</option></select>
<label class="control"><input type="checkbox" id="mappings"> Show WordNet mappings</label>
<input id="search" aria-label="Search labels or URIs" placeholder="Search book, mug, or a URI…"><p id="matches" class="small"></p><div id="results"></div><h2>Start exploring</h2><div id="seeds"></div><div class="legend" id="legend"></div><p class="small">Click: inspect · Double-click: explore<br>Drag background: pan · Wheel: zoom<br>Arrows point from object → location or child → parent.<br>Previous/Next pages through all incident relations.</p><p id="error"></p></aside>
<section><svg id="canvas" aria-label="Interactive RDF neighborhood"><defs><marker id="arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8fa2bd"/></marker></defs><g id="scene"></g></svg><div id="bar"><button id="back">Previous</button><button id="next">Next</button><button id="reset">Reset view</button></div><div id="count" class="small"></div></section>
<aside id="inspector"><h2>Node inspector</h2><p>Select a node to see its exact URI and outgoing RDF properties.</p></aside></main>
<script>
const colors = {
  noun: '#69c8ba',
  verb: '#b69aff',
  concept: '#f1bd65',
  assertion: '#f08196',
  wn31: '#74b5ff',
  metadata: '#9faabb'
};
const names = {
  noun: 'WordNet 3.0 noun',
  verb: 'WordNet 3.0 verb',
  concept: 'ConceptNet concept',
  assertion: 'AtLocation assertion',
  wn31: 'WordNet 3.1 mapping target',
  metadata: 'Schema / provenance'
};
const $ = id => document.getElementById(id),
  NS = 'http://www.w3.org/2000/svg';
let current = null,
  offset = 0,
  last = null,
  zoom = 1,
  panX = 0,
  panY = 0,
  drag = null,
  request = 0;

function short(uri) {
  return uri.split(/[\/#]/).pop()
}

function element(tag, attrs = {}) {
  let e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e
}

function button(label, action, parent) {
  let b = document.createElement('button');
  b.className = 'result';
  b.textContent = label;
  b.onclick = action;
  parent.appendChild(b)
}
async function api(path) {
  let r = await fetch(path);
  if (!r.ok) throw Error(await r.text());
  return r.json()
}

function fail(e) {
  $('error').textContent = e.message
}

function transform() {
  $('scene').setAttribute('transform', `translate(${panX},${panY}) scale(${zoom})`)
}

function reset() {
  zoom = 1;
  panX = panY = 0;
  transform()
}
// Render literal values with textContent so RDF data never becomes HTML.
async function inspect(uri) {
  try {
    let n = await api('/api/node?uri=' + encodeURIComponent(uri));
    let p = $('inspector');
    p.replaceChildren();
    let h = document.createElement('h2');
    h.textContent = n.label;
    p.appendChild(h);
    let kind = document.createElement('p');
    kind.textContent = names[n.kind];
    kind.style.color = colors[n.kind];
    p.appendChild(kind);
    let u = document.createElement('p');
    u.className = 'uri';
    u.textContent = n.id;
    p.appendChild(u);
    button('Explore this neighborhood', () => explore(uri), p);
    let incoming = document.createElement('p');
    incoming.className = 'small';
    incoming.textContent = n.incoming + ' incoming triples · ' + n.properties.length + ' outgoing properties';
    p.appendChild(incoming);
    if (!n.properties.length) {
      let note = document.createElement('p');
      note.textContent = 'Referenced resource only; its external ontology is not imported.';
      p.appendChild(note)
    }
    for (let prop of n.properties) {
      let row = document.createElement('div');
      row.className = 'property';
      let key = document.createElement('div');
      key.className = 'key';
      key.textContent = short(prop.predicate);
      key.title = prop.predicate;
      row.appendChild(key);
      let value = document.createElement('div');
      value.textContent = prop.value;
      row.appendChild(value);
      p.appendChild(row)
    }
  } catch (e) {
    fail(e)
  }
}

// Radial one-hop layout: no force simulation or external library.
function draw(data) {
  last = data;
  let scene = $('scene');
  scene.replaceChildren();
  const box = $('canvas').getBoundingClientRect(),
    cx = box.width / 2,
    cy = box.height / 2;
  let others = data.nodes.filter(n => n.id !== data.focus),
    positions = new Map([
      [data.focus, [cx, cy]]
    ]);
  others.forEach((n, i) => {
    let a = 2 * Math.PI * i / others.length - Math.PI / 2;
    let r = Math.min(box.width, box.height) * (.28 + (i % 2) * .12);
    positions.set(n.id, [cx + Math.cos(a) * r, cy + Math.sin(a) * r])
  });
  for (let edge of data.edges) {
    let [x1, y1] = positions.get(edge.source), [x2, y2] = positions.get(edge.target);
    let line = element('line', {
      x1,
      y1,
      x2,
      y2,
      'marker-end': 'url(#arrow)'
    });
    let title = element('title');
    title.textContent = edge.predicate + (edge.assertions.length ? '\nDerived from ' + edge.assertions.length + ' source assertion(s)' : '');
    line.appendChild(title);
    scene.appendChild(line);
    let t = element('text', {
      x: (x1 + x2) / 2,
      y: (y1 + y2) / 2 - 5,
      'text-anchor': 'middle',
      class: 'edge-label'
    });
    t.textContent = edge.predicate.endsWith('subClassOf') ? 'is a' : edge.predicate.endsWith('mapsToWordNet') ? 'maps to' : short(edge.predicate);
    scene.appendChild(t)
  }
  for (let n of data.nodes) {
    let [x, y] = positions.get(n.id), g = element('g', {
      class: 'node',
      transform: `translate(${x},${y})`
    });
    g.appendChild(element('circle', {
      r: n.id === data.focus ? 15 : 10,
      fill: colors[n.kind],
      stroke: n.id === data.focus ? 'white' : '#182235',
      'stroke-width': 2
    }));
    let t = element('text', {
      y: 27,
      'text-anchor': 'middle'
    });
    t.textContent = n.label.length > 27 ? n.label.slice(0, 24) + '…' : n.label;
    g.appendChild(t);
    let title = element('title');
    title.textContent = n.label + '\n' + n.id;
    g.appendChild(title);
    g.onclick = () => inspect(n.id);
    g.ondblclick = () => explore(n.id);
    scene.appendChild(g)
  }
  $('count').textContent = `${data.nodes.length} nodes · relations ${data.total?data.offset+1:0}–${Math.min(data.offset+data.limit,data.total)} of ${data.total} · ${data.view === 'semantic' ? 'semantic relations' : 'raw RDF relations'}`;
  $('back').disabled = data.offset === 0;
  $('next').disabled = data.offset + data.limit >= data.total;
  transform()
}
// Fetch one bounded page; ignore stale responses after rapid navigation.
async function explore(uri, page = 0) {
  try {
    let ticket = ++request;
    let data = await api('/api/graph?uri=' + encodeURIComponent(uri) + '&offset=' + page + '&view=' + $('view').value + '&filter=' + $('filter').value + '&mappings=' + ($('mappings').checked ? '1' : '0'));
    if (ticket !== request) return;
    current = data.focus;
    offset = page;
    reset();
    draw(data);
    inspect(current)
  } catch (e) {
    fail(e)
  }
}
$('back').onclick = () => explore(current, Math.max(0, offset - 40));
$('next').onclick = () => explore(current, offset + 40);
$('reset').onclick = reset;

function changeFilters() {
  $('mappings').disabled = $('view').value === 'raw' || $('filter').value !== 'all';
  if (current) explore(current);
}
for (const id of ['view', 'filter', 'mappings']) $(id).onchange = changeFilters;
$('canvas').onpointerdown = e => {
  if (e.target.closest('.node')) return;
  drag = [e.clientX, e.clientY, panX, panY];
  $('canvas').setPointerCapture(e.pointerId)
};
$('canvas').onpointermove = e => {
  if (drag) {
    panX = drag[2] + e.clientX - drag[0];
    panY = drag[3] + e.clientY - drag[1];
    transform()
  }
};
$('canvas').onpointerup = $('canvas').onpointercancel = () => drag = null;
$('canvas').addEventListener('wheel', e => {
  e.preventDefault();
  let b = $('canvas').getBoundingClientRect(),
    x = e.clientX - b.left,
    y = e.clientY - b.top,
    n = Math.min(5, Math.max(.2, zoom * Math.exp(-e.deltaY * .001)));
  panX = x - (x - panX) * n / zoom;
  panY = y - (y - panY) * n / zoom;
  zoom = n;
  transform()
}, {
  passive: false
});
let timer, searchTicket = 0;
async function search(centerFirst = false) {
  let ticket = ++searchTicket;
  try {
    let query = $('search').value.trim();
    let data = await api('/api/search?q=' + encodeURIComponent(query) + '&view=' + $('view').value);
    if (ticket !== searchTicket) return;
    $('results').replaceChildren();
    $('matches').textContent = `${data.total} matches (up to 40 shown)`;
    for (let n of data.nodes) button(n.label + ' · ' + names[n.kind], () => explore(n.id), $('results'));
    // Exact concept labels (especially ConceptNet) center immediately; Enter chooses the best match.
    const best = data.nodes[0];
    if (best && (centerFirst || best.label.toLowerCase() === query.toLowerCase() || best.id === query)) explore(best.id);
  } catch (e) {
    fail(e);
  }
}
$('search').oninput = () => {
  clearTimeout(timer);
  ++searchTicket;
  timer = setTimeout(() => search(), 220);
};
$('search').onkeydown = e => {
  if (e.key === 'Enter') {
    clearTimeout(timer);
    search(true);
  }
};
for (let [kind, label] of Object.entries(names)) {
  let row = document.createElement('div'),
    dot = document.createElement('span');
  dot.className = 'dot';
  dot.style.background = colors[kind];
  row.appendChild(dot);
  row.appendChild(document.createTextNode(label));
  $('legend').appendChild(row)
}
window.addEventListener('resize', () => {
  if (last) draw(last)
});
api('/api/summary').then(s => {
  $('summary').textContent = `${s.mode} · ${s.triples.toLocaleString()} RDF triples · ${s.resources.toLocaleString()} resources`;
  for (let seed of s.seeds) button(seed.label, () => explore(seed.id), $('seeds'));
  if (s.seeds.length) explore(s.seeds[0].id)
}).catch(fail);
</script></html>'''


def handler_for(viewer):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            url = urlparse(self.path)
            params = parse_qs(url.query)
            try:
                if url.path == '/':
                    body, content_type = HTML.encode(), 'text/html; charset=utf-8'
                else:
                    uri = params.get('uri', [''])[0]
                    if url.path == '/api/summary':
                        data = viewer.summary()
                    elif url.path == '/api/search':
                        data = viewer.search(params.get('q', [''])[0], params.get('view', ['semantic'])[0])
                    elif url.path in ('/api/node', '/api/graph') and uri in viewer.nodes:
                        data = viewer.inspect(uri) if url.path == '/api/node' else viewer.neighborhood(
                            uri, max(0, int(params.get('offset', ['0'])[0])),
                            view=params.get('view', ['semantic'])[0],
                            relation=params.get('filter', ['all'])[0],
                            mappings=params.get('mappings', ['0'])[0] == '1')
                    else:
                        self.send_error(404, 'Unknown route or resource')
                        return
                    body, content_type = json.dumps(data).encode(), 'application/json'
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except ValueError:
                self.send_error(400, 'Invalid query parameter')
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', choices=['wordnet', 'conceptnet', 'both'], default='both')
    parser.add_argument('--port', type=int, default=0, help='Local port; 0 selects an available port')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    graph = Graph()
    for name in (FILES if args.graph == 'both' else [args.graph]):
        path = ROOT / 'robonet_graph' / FILES[name]
        if not path.exists():
            parser.error(f'Missing {path}; see STATUS.md for regeneration commands')
        print(f'Loading {path.name}…', flush=True)
        graph.parse(path, format='turtle')
    print('Indexing labels and resources…', flush=True)
    viewer = Viewer(graph, args.graph)
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(viewer)) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'{len(graph):,} triples loaded. Open {url}\nPress Ctrl+C to stop.', flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
