"""Exact-source alignment checks, including ambiguity and missing mappings."""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import tempfile
import unittest

from rdflib import Graph, Literal, RDF, URIRef

from conceptnet.align_conceptnet_wordnet import align, write_aligned
from conceptnet.build_rdf import ASSERTION, AT_LOCATION, SCHEMA, build_graph, convert

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'robonet_graph'


class ConceptNetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((DATA / 'conceptnet_atlocation_aligned.json').read_text())
        with (DATA / 'filtered_conceptnet.csv').open() as stream:
            cls.source = [r for r in csv.DictReader(stream) if r['predicate'] == 'AtLocation']
        cls.mappings = defaultdict(set)
        with (DATA / 'conceptnet_wordnet_mappings.csv').open() as stream:
            for row in csv.DictReader(stream):
                cls.mappings[row['conceptnet_concept']].add(row['wordnet_synset'])

    def test_all_source_rows_and_exact_mapping_candidates_preserved(self):
        def triples(rows):
            return Counter((r['subject'], r['predicate'], r['object']) for r in rows)
        assertions = self.document['assertions']
        self.assertEqual(len(assertions), 261)
        self.assertEqual(triples(assertions), triples(self.source))
        self.assertEqual(len({a['id'] for a in assertions}), len(assertions))
        for assertion in assertions:
            for role in ('subject', 'object'):
                self.assertEqual(assertion[f'{role}_wordnet_mappings'], sorted(self.mappings[assertion[role]]))
        stats = self.document['metadata']['statistics']
        self.assertEqual(stats, {
            'atlocation_source_triples': 261,
            'aligned_subject_concepts': 127, 'aligned_object_concepts': 99,
            'ambiguous_subject_mappings': 57, 'ambiguous_object_mappings': 36,
            'unmapped_subjects': [], 'unmapped_objects': [],
        })
        book = next(a for a in assertions if a['subject'] == '/c/en/book')
        self.assertEqual(len(book['subject_wordnet_mappings']), 2)
        self.assertTrue(all('#Component-' in uri for uri in book['subject_wordnet_mappings']))

    def test_deterministic_json_and_rdf_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'aligned.json'
            document = write_aligned(DATA / 'filtered_conceptnet.csv', DATA / 'conceptnet_wordnet_mappings.csv', output)
            self.assertEqual(document, self.document)
            self.assertEqual(output.read_bytes(), (DATA / 'conceptnet_atlocation_aligned.json').read_bytes())
            ttl = Path(directory) / 'conceptnet.ttl'
            count = convert(output, ttl)
            self.assertEqual(ttl.read_bytes(), (DATA / 'robokgconceptnet.ttl').read_bytes())
            graph = Graph().parse(ttl, format='turtle')
            self.assertEqual(len(graph), count)
            self.assertEqual(set(graph), set(build_graph(document)))
            self.assertEqual(set(graph.objects(None, RDF.predicate)), {AT_LOCATION})
            self.assertEqual(len(set(graph.subjects(RDF.type, SCHEMA.AtLocationAssertion))), 261)
            for assertion in document['assertions']:
                node = ASSERTION[assertion['id']]
                for role, predicate in [('subject', RDF.subject), ('object', RDF.object)]:
                    concept = URIRef('http://api.conceptnet.io' + assertion[role])
                    self.assertIn((node, predicate, concept), graph)
                    self.assertIn((concept, SCHEMA.conceptId, Literal(assertion[role])), graph)
                    raw = assertion[f'{role}_wordnet_mappings']
                    # The current source's two illegal IRIs contain backticks.
                    self.assertEqual(set(graph.objects(concept, SCHEMA.mapsToWordNet)),
                                     {URIRef(s.replace('`', '%60')) for s in raw})
                    for s in raw:
                        if '`' in s:
                            self.assertIn((URIRef(s.replace('`', '%60')), SCHEMA.sourceMappingIdentifier, Literal(s)), graph)
            self.assertFalse(any('/wordnet/3.0/' in str(t) for triple in graph for t in triple))

    def test_missing_ambiguous_and_duplicate_rows_are_not_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.csv'
            mappings = Path(directory) / 'mappings.csv'
            source.write_text('subject,predicate,object\n/c/en/x,AtLocation,/c/en/y\n/c/en/x,AtLocation,/c/en/y\n/c/en/y,UsedFor,/c/en/x\n/c/en/x,IsA,/c/en/y\n/c/en/y,AtLocation,/c/en/x\n')
            prefix = 'http://wordnet-rdf.princeton.edu/wn31/'
            mappings.write_text('conceptnet_concept,wordnet_synset\n/c/en/x,' + prefix + '100000001-n\n/c/en/x,' + prefix + '100000002-n\n')
            document = align(source, mappings)
            self.assertEqual(len(document['assertions']), 3)
            self.assertEqual(len({a['id'] for a in document['assertions']}), 3)
            self.assertEqual(document['metadata']['statistics']['unmapped_subjects'], ['/c/en/y'])
            self.assertEqual(document['metadata']['statistics']['unmapped_objects'], ['/c/en/y'])
            for assertion in document['assertions']:
                for role in ('subject', 'object'):
                    targets = assertion[f'{role}_wordnet_mappings']
                    self.assertEqual(len(targets), 2 if assertion[role] == '/c/en/x' else 0)
            graph = build_graph(document)
            self.assertEqual(len(set(graph.subjects(RDF.type, SCHEMA.AtLocationAssertion))), 3)
            self.assertIn((URIRef('http://api.conceptnet.io/c/en/y'), SCHEMA.mappingStatus, Literal('unmapped')), graph)


if __name__ == '__main__':
    unittest.main()
