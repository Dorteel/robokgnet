"""Serialize canonical conceptual location histograms as minimal RDF."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph, Namespace, Literal, URIRef, RDFS, SKOS, XSD

GRAPH_DIR = Path(__file__).resolve().parents[1] / 'robonet_graph'
HIST = Namespace('https://w3id.org/robokgnet/location#')


def build_graph(document):
    graph = Graph()
    ns = Namespace('https://w3id.org/robokgnet/wordnet/' + document['metadata']['wordnet_version'] + '/synset/')
    for name, node in document['nodes'].items():
        subject = ns[quote(name, safe='')]
        graph.add((subject, RDFS.label, Literal(node['type'])))
        for label in node['alternative_names']:
            graph.add((subject, SKOS.altLabel, Literal(label)))
        for parent in node['superclass']:
            graph.add((subject, RDFS.subClassOf, ns[quote(parent, safe='')]))
        for location, entry in node['qualities']['location'].items():
            uri = URIRef(str(subject) + '/location/' + quote(location, safe=''))
            graph.add((subject, HIST.location, uri))
            graph.add((uri, RDFS.label, Literal(location)))
            for count in ('seed_count', 'observation_count', 'count'):
                graph.add((uri, HIST[count], Literal(entry[count])))
            for key in ('conceptnet_ids', 'wordnet31_ids', 'wordnet_ids'):
                for value in entry[key]:
                    # Original mapping spellings may be illegal IRIs; preserve them as IDs.
                    graph.add((uri, HIST[key], Literal(value)))
        # Keep subject ambiguity visible without duplicating the entire alignment table.
        for index, evidence in enumerate(node['conceptnet_subjects']):
            uri = URIRef(str(subject) + '/conceptnet/' + str(index))
            graph.add((subject, HIST.grounding, uri))
            graph.add((uri, HIST.conceptnet_id, Literal(evidence['conceptnet_id'])))
            for key in ('wordnet31_ids', 'wordnet_ids'):
                for value in evidence[key]:
                    graph.add((uri, HIST[key], Literal(value)))
    return graph


def convert(input_path, output_path):
    graph = build_graph(json.loads(Path(input_path).read_text()))
    prefixes = {'location': HIST, 'rdfs': RDFS, 'xsd': XSD, 'skos': SKOS}
    for prefix, namespace in prefixes.items():
        graph.bind(prefix, namespace, replace=True)
    header = ''.join(f'@prefix {p}: <{ns}> .\n' for p, ns in sorted(prefixes.items()))
    lines = sorted(' '.join(term.n3(graph.namespace_manager) for term in triple) + ' .\n' for triple in graph)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(header + '\n' + ''.join(lines), encoding='utf-8')
    return len(graph)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=GRAPH_DIR / 'robokgconceptnet.json')
    parser.add_argument('--output', type=Path, default=GRAPH_DIR / 'robokgconceptnet.ttl')
    args = parser.parse_args()
    print('TTL triples:', convert(args.input, args.output))


if __name__ == '__main__':
    main()
