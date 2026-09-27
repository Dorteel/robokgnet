"""Serialize the two demo JSON resources into separate deterministic RDF graphs."""
import json
from pathlib import Path
import re
from urllib.parse import quote
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef, XSD

OUTPUT = Path(__file__).resolve().parents[1] / 'robonet_graph'
KG = Namespace('https://w3id.org/robokgnet/action/schema#')
VN = Namespace('https://w3id.org/robokgnet/verbnet/2.1/')
FN = Namespace('https://w3id.org/robokgnet/framenet/1.7/')
PROV = Namespace('http://www.w3.org/ns/prov#')


def node(base, path):
    return URIRef(str(base) + quote(path, safe='/'))


def typed(graph, uri, kind, label=None):
    graph.add((uri, RDF.type, KG[kind]))
    if label is not None:
        graph.add((uri, RDFS.label, Literal(label)))
    return uri


def emit_tree(graph, data, uri, frame=None, roles=None):
    """Preserve ordered nested XML, including restrictions and conditional structure."""
    kind = {'PRED': 'SemanticPredicate', 'ARG': 'SemanticArgument'}.get(data['tag'], 'Structure')
    typed(graph, uri, kind)
    graph.add((uri, KG.tag, Literal(data['tag'])))
    for key, value in sorted(data['attributes'].items()):
        graph.add((uri, KG['attribute_' + key], Literal(value)))
    if data['text']:
        graph.add((uri, KG.text, Literal(data['text'])))
    if frame is not None and data['tag'] == 'PRED':
        graph.add((frame, KG.hasPredicate, uri))
    if data['tag'] == 'ARG' and frame is not None:
        attrs = data['attributes']
        value = attrs.get('value', '')
        if attrs.get('type') == 'Event':
            match = re.fullmatch(r'(?:(start|during|end)\()?([A-Za-z]\w*)\)?', value)
            if match:
                event = typed(graph, node(str(frame) + '/event/', match[2]), 'EventVariable', match[2])
                graph.add((uri, KG.event, event))
                if match[1]:
                    graph.add((uri, KG.phase, Literal(match[1])))
        if attrs.get('type') == 'ThemRole' and value in (roles or {}):
            graph.add((uri, KG.role, roles[value]))
    for index, child in enumerate(data['children']):
        child_uri = URIRef(str(uri) + '/' + str(index))
        graph.add((uri, KG.child, child_uri))
        graph.add((child_uri, KG.position, Literal(index)))
        emit_tree(graph, child, child_uri, frame, roles)


def verbnet_graph(document):
    graph = Graph()
    for class_id, cls in document['classes'].items():
        root = typed(graph, node(VN, class_id), 'VerbNetClass', class_id)
        roles = {}
        for role in cls['roles']:
            name = role['attributes']['type']
            uri = typed(graph, node(VN, class_id + '/role/' + name), 'ThematicRole', name)
            roles[name] = uri
            graph.add((root, KG.hasRole, uri))
            emit_tree(graph, role, uri)
        for member in cls['members']:
            # Identity records the declaring subclass without importing that class.
            uri = typed(graph, node(VN, member['declaring_class'] + '/member/' + member['name']), 'VerbMember', member['name'])
            graph.add((root, KG.hasScopedMember, uri))
            graph.add((uri, KG.declaringClassId, Literal(member['declaring_class'])))
            for key, value in member['attributes'].items():
                graph.add((uri, KG['attribute_' + key], Literal(value)))
            for mapping in member['wordnet_mappings']:
                graph.add((uri, KG.wordnetSenseKey, Literal(mapping['sense_key'])))
                graph.add((uri, KG.mapsToWordNet, node('https://w3id.org/robokgnet/wordnet/' + document['metadata']['wordnet_version'] + '/synset/', mapping['synset_id'])))
        for index, frame in enumerate(cls['frames']):
            uri = typed(graph, node(VN, class_id + '/frame/' + str(index)), 'VerbNetFrame')
            graph.add((root, KG.hasFrame, uri))
            graph.add((uri, KG.position, Literal(index)))
            for key, value in frame['description'].items():
                graph.add((uri, KG['description_' + key], Literal(value)))
            for example in frame['examples']:
                graph.add((uri, KG.example, Literal(example)))
            for name in ('syntax', 'semantics'):
                tree_uri = URIRef(str(uri) + '/' + name)
                graph.add((uri, KG[name], tree_uri))
                emit_tree(graph, frame[name], tree_uri, uri if name == 'semantics' else None, roles)
    return graph


def framenet_graph(document):
    graph = Graph()
    for name, frame in document['frames'].items():
        root = typed(graph, node(FN, name), 'FrameNetFrame', name)
        graph.add((root, KG.corpusId, Literal(frame['id'])))
        graph.add((root, KG.definition, Literal(frame['definition'])))
        for fe_name, fe in frame['frame_elements'].items():
            uri = typed(graph, node(FN, name + '/fe/' + fe_name), 'FrameElement', fe_name)
            graph.add((root, KG.hasFrameElement, uri))
            for key in ('definition', 'core_type', 'id'):
                graph.add((uri, KG[key], Literal(fe[key])))
        for lu in frame['lexical_units']:
            uri = typed(graph, node(FN, 'lu/' + str(lu['id'])), 'LexicalUnit', lu['name'])
            graph.add((root, KG.evokedBy, uri))
            graph.add((uri, KG.partOfSpeech, Literal(lu['pos'])))
            graph.add((uri, KG.corpusId, Literal(lu['id'])))
            for index, lexeme in enumerate(lu['lexemes']):
                part = node(str(uri) + '/lexeme/', str(index))
                graph.add((uri, KG.lexeme, part))
                graph.add((part, KG.position, Literal(index)))
                for key, value in lexeme.items():
                    graph.add((part, KG[key], Literal(value)))
    evidence = document['metadata']['semlink_evidence']
    source = URIRef('urn:sha256:' + evidence['parsed_table_sha256'])
    graph.add((source, PROV.hadPrimarySource, URIRef(evidence['source'])))
    graph.add((source, KG.retrieved, Literal(evidence['retrieved'])))
    for record in document['alignments']:
        uri = node(FN, 'alignment/' + record['verbnet'] + '/' + record['member'] + '/' + record['framenet'])
        typed(graph, uri, 'SemLinkAlignment')
        graph.add((uri, KG.frame, node(FN, record['framenet'])))
        graph.add((uri, KG.member, node(VN, record['verbnet'] + '/member/' + record['member'])))
        graph.add((uri, KG.declaringClassId, Literal(record['verbnet'])))
        graph.add((uri, KG.exportedClassScope, node(VN, record['exported_class_scope'])))
        graph.add((uri, PROV.wasDerivedFrom, source))
    return graph


def save(graph, path):
    prefixes = {'kg': KG, 'vn': VN, 'fn': FN, 'rdf': RDF, 'rdfs': RDFS, 'prov': PROV, 'xsd': XSD}
    for prefix, namespace in prefixes.items():
        graph.bind(prefix, namespace, replace=True)
    header = ''.join(f'@prefix {p}: <{ns}> .\n' for p, ns in sorted(prefixes.items()))
    lines = sorted(' '.join(term.n3(graph.namespace_manager) for term in triple) + ' .\n' for triple in graph)
    path.write_text(header + '\n' + ''.join(lines), encoding='utf-8')


def main():
    for name, builder in [('framenet', framenet_graph)]:
        graph = builder(json.loads((OUTPUT / (name + '.json')).read_text()))
        path = OUTPUT / ('robokg' + name + '.ttl')
        save(graph, path)
        print(f'{path.name}: {len(graph):,} triples, {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
