"""Convert conceptual RoboKGWordNet JSON into minimal Turtle (no corpus reads)."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph, Literal, Namespace, RDF, RDFS, SKOS, URIRef, XSD

GRAPH_DIR = Path(__file__).resolve().parents[1] / 'robonet_graph'
PROPERTIES = Namespace('https://w3id.org/robokgnet/wordnet/property/')


def synset_namespace(version):
    return Namespace(f'https://w3id.org/robokgnet/wordnet/{quote(version, safe="")}/synset/')


def build_graph(document):
    graph = Graph()
    ns = synset_namespace(document['wordnet_version'])
    name_field = document['schema']['name_field']

    def properties(subject, field, value):
        # Null means unknown, not a fact. Do not invent RDF nulls or measurements.
        if value is None:
            return
        predicate = PROPERTIES[quote(field, safe='')]
        if isinstance(value, (dict, list)):
            child = URIRef(str(subject) + '/' + quote(field, safe=''))
            before = len(graph)
            entries = value.items() if isinstance(value, dict) else enumerate(value)
            for key, part in entries:
                properties(child, str(key), part)
            if len(graph) > before:
                graph.add((subject, predicate, child))
        else:
            graph.add((subject, predicate, Literal(value)))

    for key, node in document['nodes'].items():
        if node['id'] != key:
            raise ValueError(f'Node key/id mismatch: {key}')
        subject = ns[quote(key, safe='')]
        graph.add((subject, RDFS.label, Literal(node[name_field], lang='en')))
        for label in node['alternative_names']:
            graph.add((subject, SKOS.altLabel, Literal(label, lang='en')))
        for parent in node['superclass']:
            if parent not in document['nodes']:
                raise ValueError(f'Dangling superclass: {parent}')
            graph.add((subject, RDFS.subClassOf, ns[quote(parent, safe='')]))
        for field, value in node.items():
            if field not in ('id', name_field, 'alternative_names', 'superclass'):
                properties(subject, field, value)
    return graph


def convert(input_path, output_path):
    document = json.loads(Path(input_path).read_text(encoding='utf-8'))
    graph = build_graph(document)
    prefixes = {'rdfs': RDFS, 'skos': SKOS, 'syn': synset_namespace(document['wordnet_version']),
                'property': PROPERTIES, 'xsd': XSD}
    for prefix, namespace in prefixes.items():
        graph.bind(prefix, namespace, replace=True)
    header = ''.join(f'@prefix {p}: <{ns}> .\n' for p, ns in sorted(prefixes.items()))
    lines = sorted(' '.join(term.n3(graph.namespace_manager) for term in triple) + ' .\n' for triple in graph)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(header + '\n' + ''.join(lines), encoding='utf-8')
    return len(graph)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=GRAPH_DIR / 'robokgwordnet.json')
    parser.add_argument('--output', type=Path, default=GRAPH_DIR / 'robokgwordnet.ttl')
    args = parser.parse_args()
    print(f'TTL triples: {convert(args.input, args.output):,}\nTTL: {args.output} ({args.output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
