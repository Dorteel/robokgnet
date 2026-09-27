"""Public, read-only semantic access to the four generated RoboKGNet graphs.

Queries return candidates, never disambiguated senses. Unknown identifiers return
empty lists/dicts. Hierarchy queries are direct, exported edges only. No corpus
installation is needed: all knowledge comes from the existing Turtle artifacts.
"""
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from rdflib import Graph, Literal, Namespace, RDF, RDFS, SKOS, URIRef

WN = Namespace('https://w3id.org/robokgnet/wordnet/schema#')
CN = Namespace('https://w3id.org/robokgnet/conceptnet/schema#')
ACTION = Namespace('https://w3id.org/robokgnet/action/schema#')
AT_LOCATION = URIRef('http://api.conceptnet.io/r/AtLocation')


def normalized(value):
    """Normalize labels for exact matching, without guessing a word sense."""
    return str(value).replace('_', ' ').strip().casefold()


class KnowledgeInterface:
    def __init__(self, resource_dir=None):
        directory = Path(resource_dir) if resource_dir is not None else Path(__file__).resolve().parent / 'robonet_graph'
        # Discover actual files in the resource directory, independently of cwd.
        available = {path.name: path for path in directory.glob('*.ttl')}
        expected = {name: f'robokg{name}.ttl' for name in ('wordnet', 'conceptnet', 'framenet', 'verbnet')}
        missing = [filename for filename in expected.values() if filename not in available]
        if missing:
            raise FileNotFoundError(f"Missing RoboKGNet graph(s) in {directory}: {', '.join(missing)}. See README.md regeneration commands.")
        self.loaded_resources = {name: available[filename] for name, filename in expected.items()}
        self._graphs = {name: Graph().parse(path, format='turtle') for name, path in self.loaded_resources.items()}

    def _wordnet_nodes(self):
        # The minimal WordNet artifact identifies synsets in their versioned URI;
        # it no longer repeats that identity through rdf:type/synsetId triples.
        graph = self._graphs['wordnet']
        return sorted({u for u in graph.subjects(RDFS.label, None)
                       if '/wordnet/' in str(u) and '/synset/' in str(u)}, key=str)

    def _wordnet_record(self, uri):
        graph = self._graphs['wordnet']
        identifier = unquote(str(uri).rsplit('/', 1)[-1])
        return {'synset_id': identifier,
                'label': str(graph.value(uri, RDFS.label)).replace('_', ' '),
                'alternative_labels': sorted(str(v).replace('_', ' ') for v in graph.objects(uri, SKOS.altLabel)),
                'pos': {'n': 'noun', 'v': 'verb'}.get(identifier.rsplit('.', 2)[-2], ''), 'uri': str(uri)}

    def resolve_wordnet(self, term):
        """Return every exported synset matching an exact label, ID, or URI."""
        graph = self._graphs['wordnet']
        matches = []
        for uri in self._wordnet_nodes():
            values = [uri, unquote(str(uri).rsplit('/', 1)[-1]), graph.value(uri, RDFS.label), *graph.objects(uri, SKOS.altLabel)]
            if any(v is not None and normalized(v) == normalized(term) for v in values):
                matches.append(self._wordnet_record(uri))
        return sorted(matches, key=lambda r: r['synset_id'])

    def _hierarchy(self, synset_id, parents):
        graph = self._graphs['wordnet']
        # Accept canonical identifiers, not a potentially ambiguous English word.
        subject = next((u for u in self._wordnet_nodes()
                        if str(u) == synset_id or unquote(str(u).rsplit('/', 1)[-1]) == synset_id), None)
        if subject is None:
            return []
        targets = graph.objects(subject, RDFS.subClassOf) if parents else graph.subjects(RDFS.subClassOf, subject)
        return sorted((self._wordnet_record(u) for u in targets if (u, RDFS.label, None) in graph),
                      key=lambda r: r['synset_id'])

    def get_superclasses(self, synset_id):
        """Direct exported hypernyms as synset records."""
        return self._hierarchy(synset_id, True)

    def get_subclasses(self, synset_id):
        """Direct exported hyponyms as synset records."""
        return self._hierarchy(synset_id, False)

    def _frame_uri(self, frame):
        graph = self._graphs['framenet']
        return next((u for u in graph.subjects(RDF.type, ACTION.FrameNetFrame)
                     if str(u) == frame or normalized(graph.value(u, RDFS.label)) == normalized(frame)), None)

    def get_frame_for_word(self, word):
        """Frame candidates from exact lexical-unit/lexeme names, not a hardcoded map."""
        graph = self._graphs['framenet']
        frames = set()
        for frame, _, lu in graph.triples((None, ACTION.evokedBy, None)):
            # FrameNet LU labels carry a POS suffix, e.g. bring.v or search.n.
            label = str(graph.value(lu, RDFS.label))
            values = [label, label.rsplit('.', 1)[0]]
            values.extend(str(graph.value(lexeme, ACTION.name)) for lexeme in graph.objects(lu, ACTION.lexeme))
            if normalized(word) in {normalized(v) for v in values}:
                frames.add(str(graph.value(frame, RDFS.label)))
        return sorted(frames)

    def get_frame_elements(self, frame):
        graph = self._graphs['framenet']
        uri = self._frame_uri(frame)
        if uri is None:
            return []
        return sorted([{'name': str(graph.value(fe, RDFS.label)), 'definition': str(graph.value(fe, ACTION.definition)),
                        'core_type': str(graph.value(fe, ACTION.core_type)), 'uri': str(fe)}
                       for fe in graph.objects(uri, ACTION.hasFrameElement)], key=lambda r: r['name'])

    def get_role_descriptions(self, frame):
        """Original FrameNet FE wording, not a mapping to VerbNet roles."""
        return {fe['name']: fe['definition'] for fe in self.get_frame_elements(frame)}

    def _alignments(self, frame_or_word):
        graph = self._graphs['framenet']
        frame_uri = self._frame_uri(frame_or_word)
        frames = [frame_uri] if frame_uri is not None else [self._frame_uri(f) for f in self.get_frame_for_word(frame_or_word)]
        records = []
        for alignment in graph.subjects(RDF.type, ACTION.SemLinkAlignment):
            frame = graph.value(alignment, ACTION.frame)
            if frame not in frames:
                continue
            member = graph.value(alignment, ACTION.member)
            records.append({'frame': str(graph.value(frame, RDFS.label)),
                            'verbnet_class': unquote(str(graph.value(alignment, ACTION.exportedClassScope)).rsplit('/', 1)[-1]),
                            'declaring_class': str(graph.value(alignment, ACTION.declaringClassId)),
                            'member': str(self._graphs['verbnet'].value(member, RDFS.label)),
                            'alignment_uri': str(alignment)})
        # Prefer the exact member when querying a word. Otherwise retain all
        # frame-supported candidates; do not claim an unobserved member alignment.
        exact = [r for r in records if normalized(r['member']) == normalized(frame_or_word)]
        return sorted(exact or records, key=lambda r: r['alignment_uri'])

    def get_verbnet_class(self, frame_or_word):
        """Return exported class-scope candidates via explicit member alignments."""
        return sorted({r['verbnet_class'] for r in self._alignments(frame_or_word)})

    def _class_uri(self, class_id):
        graph = self._graphs['verbnet']
        return next((u for u in graph.subjects(RDF.type, ACTION.VerbNetClass)
                     if str(u) == class_id or str(graph.value(u, RDFS.label)) == class_id), None)

    def _tree(self, uri):
        """Reconstruct the original ordered structure from child/position links."""
        graph = self._graphs['verbnet']
        prefix = str(ACTION) + 'attribute_'
        children = sorted(graph.objects(uri, ACTION.child), key=lambda c: int(graph.value(c, ACTION.position)))
        return {'tag': str(graph.value(uri, ACTION.tag)),
                'attributes': {str(p)[len(prefix):]: str(o) for p, o in sorted(graph.predicate_objects(uri), key=lambda t: str(t[0])) if str(p).startswith(prefix)},
                'text': str(graph.value(uri, ACTION.text) or ''),
                'children': [self._tree(child) for child in children]}

    def get_verbnet_roles(self, verbnet_class):
        graph = self._graphs['verbnet']
        uri = self._class_uri(verbnet_class)
        if uri is None:
            return []
        return sorted([{'name': str(graph.value(role, RDFS.label)), 'structure': self._tree(role)}
                       for role in graph.objects(uri, ACTION.hasRole)], key=lambda r: r['name'])

    def get_verbnet_semantics(self, verbnet_class):
        """Ordered frames with intact predicate arguments, events and conditions."""
        graph = self._graphs['verbnet']
        uri = self._class_uri(verbnet_class)
        if uri is None:
            return []
        frames = sorted(graph.objects(uri, ACTION.hasFrame), key=lambda f: int(graph.value(f, ACTION.position)))
        return [{'frame_index': int(graph.value(frame, ACTION.position)),
                 'description': {str(p).removeprefix(str(ACTION) + 'description_'): str(o)
                                 for p, o in sorted(graph.predicate_objects(frame), key=lambda t: str(t[0]))
                                 if str(p).startswith(str(ACTION) + 'description_')},
                 'examples': sorted(str(v) for v in graph.objects(frame, ACTION.example)),
                 'semantics': self._tree(graph.value(frame, ACTION.semantics))} for frame in frames]

    def _concept_label(self, uri):
        parts = urlparse(str(uri)).path.split('/')
        return unquote(parts[3]).replace('_', ' ') if len(parts) > 3 else str(uri)

    def _mappings(self, concept):
        graph = self._graphs['conceptnet']
        # Recover exact source spelling when Turtle required URI escaping.
        return sorted(str(graph.value(target, CN.sourceMappingIdentifier) or target)
                      for target in graph.objects(concept, CN.mapsToWordNet))

    def get_at_locations(self, term):
        """Stored outgoing assertions for exact concepts/labels or WN 3.1 targets.

        WN 3.0 synset IDs cannot be joined safely to 3.1 and return no fabricated
        matches. Each result retains its subject candidate and all mapping targets.
        """
        graph = self._graphs['conceptnet']
        subjects = set()
        for concept in graph.subjects(RDF.type, CN.ConceptNetConcept):
            values = [str(concept), str(graph.value(concept, CN.conceptId)), self._concept_label(concept),
                      *self._mappings(concept)]
            if any(str(term) == v or (v == self._concept_label(concept) and normalized(term) == normalized(v)) for v in values):
                subjects.add(concept)
        results = []
        for assertion in graph.subjects(RDF.type, CN.AtLocationAssertion):
            subject = graph.value(assertion, RDF.subject)
            if subject not in subjects or graph.value(assertion, RDF.predicate) != AT_LOCATION:
                continue
            obj = graph.value(assertion, RDF.object)
            results.append({'subject': self._concept_label(subject),
                            'subject_conceptnet_uri': str(graph.value(subject, CN.conceptId)),
                            'subject_wordnet_mappings': self._mappings(subject),
                            'location': self._concept_label(obj),
                            'conceptnet_uri': str(graph.value(obj, CN.conceptId)),
                            'wordnet_mappings': self._mappings(obj), 'wordnet_version': '3.1',
                            'assertion_uri': str(assertion)})
        return sorted(results, key=lambda r: (r['subject_conceptnet_uri'], r['conceptnet_uri'], r['assertion_uri']))

    def describe_action(self, word):
        """Combine frame/class candidates without asserting role equivalence."""
        frames = []
        for frame in self.get_frame_for_word(word):
            alignments = [r for r in self._alignments(word) if r['frame'] == frame]
            classes = sorted({r['verbnet_class'] for r in alignments})
            frames.append({'framenet_frame': frame, 'frame_elements': self.get_frame_elements(frame),
                           'role_descriptions': self.get_role_descriptions(frame), 'alignments': alignments,
                           'verbnet_candidates': [{'verbnet_class': c, 'verbnet_roles': self.get_verbnet_roles(c),
                                                   'semantics': self.get_verbnet_semantics(c)} for c in classes]})
        return {'word': word, 'frame_candidates': frames}


if __name__ == '__main__':
    def show(label, value):
        print(f'\n=== {label} ===')
        print(json.dumps(value, indent=2, ensure_ascii=False))

    ki = KnowledgeInterface()
    show('LOADED RESOURCES', {k: str(v) for k, v in ki.loaded_resources.items()})
    show('WORDNET: mug candidates', ki.resolve_wordnet('mug'))
    show('WORDNET: mug.n.04 superclasses', ki.get_superclasses('mug.n.04'))
    show('WORDNET: drinking_vessel.n.01 subclasses', ki.get_subclasses('drinking_vessel.n.01'))
    for word in ('bring', 'search'):
        show(f'FRAMENET: {word}', ki.get_frame_for_word(word))
        for frame in ki.get_frame_for_word(word):
            show(f'FRAME ELEMENTS: {frame}', ki.get_frame_elements(frame))
            show(f'ROLE DESCRIPTIONS: {frame}', ki.get_role_descriptions(frame))
            show(f'VERBNET CLASSES: {frame}', ki.get_verbnet_class(frame))
            for cls in ki.get_verbnet_class(frame):
                show(f'VERBNET ROLES: {cls}', ki.get_verbnet_roles(cls))
                semantics = ki.get_verbnet_semantics(cls)
                show(f'VERBNET SEMANTICS: {cls} (first of {len(semantics)} frames)', semantics[:1])
        description = ki.describe_action(word)
        # Print the combined structure, limiting only repeated frame semantics.
        for frame in description['frame_candidates']:
            for cls in frame['verbnet_candidates']:
                cls['semantics'] = cls['semantics'][:1]
        show(f'ACTION: {word} (first semantic frame per class shown)', description)
    show('ATLOCATION: book', ki.get_at_locations('book'))
    show('UNKNOWN TERM', ki.describe_action('not_a_demo_action'))
