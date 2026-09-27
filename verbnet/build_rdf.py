"""Serialize the conceptual VerbNet JSON only; never read VerbNet directly."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph, Namespace, RDFS, Literal, URIRef, XSD

ROOT = Path(__file__).resolve().parents[1]
VOCAB = Namespace('https://w3id.org/robokgnet/verbnet/property/')
BASE = 'https://w3id.org/robokgnet/verbnet/2.1/'


def build_graph(document):
    graph = Graph()
    root = URIRef(BASE + quote(document['id'], safe=''))
    graph.add((root, RDFS.label, Literal(document['id'])))

    def emit(subject, key, value):
        # Unknown task slots are not facts. JSON retains their schema-defined nulls.
        if value is None:
            return
        predicate = VOCAB[quote(key, safe='')]
        if isinstance(value, dict):
            child = URIRef(str(subject) + '/' + quote(key, safe=''))
            for name, part in value.items():
                emit(child, name, part)
            if any(graph.triples((child, None, None))):
                graph.add((subject, predicate, child))
        elif isinstance(value, list):
            for index, part in enumerate(value):
                child = URIRef(str(subject) + '/' + quote(key, safe='') + '/' + str(index))
                graph.add((subject, predicate, child))
                graph.add((child, VOCAB.position, Literal(index)))
                if isinstance(part, dict):
                    for name, item in part.items():
                        emit(child, name, item)
                else:
                    emit(child, 'value', part)
        else:
            graph.add((subject, predicate, Literal(value)))

    for field, value in document.items():
        if field not in ('id', 'schema'):
            emit(root, field, value)
    return graph


def convert(input_path, output_path):
    graph = build_graph(json.loads(Path(input_path).read_text()))
    prefixes = {'vn': Namespace(BASE), 'property': VOCAB, 'rdfs': RDFS, 'xsd': XSD}
    for prefix, ns in prefixes.items():
        graph.bind(prefix, ns, replace=True)
    header = ''.join(f'@prefix {p}: <{ns}> .\n' for p, ns in sorted(prefixes.items()))
    lines = sorted(' '.join(t.n3(graph.namespace_manager) for t in triple) + ' .\n' for triple in graph)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + '\n' + ''.join(lines), encoding='utf-8')
    return len(graph)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'robonet_graph/robokgverbnet.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'robonet_graph/robokgverbnet.ttl')
    args = parser.parse_args()
    print('TTL triples:', convert(args.input, args.output))


if __name__ == '__main__':
    main()
