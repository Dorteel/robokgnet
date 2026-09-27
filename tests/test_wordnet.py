"""Small-subtree tests for schema-driven conceptual WordNet export."""
import json
from pathlib import Path
import tempfile
import unittest
from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import WordNetError
from rdflib import Graph, RDF, RDFS
from wordnet_to_robokgwordnet import build_wordnet_branch, instantiate_schema
from wordnet.build_rdf import build_graph, convert

ROOT = Path(__file__).resolve().parents[1]


class WordNetTests(unittest.TestCase):
    def test_small_branch_schema_taxonomy_and_roundtrip(self):
        schema = ROOT / 'schemas/objects.json'
        template = instantiate_schema(json.loads(schema.read_text()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'branch.json'
            data = build_wordnet_branch(schema, 'drinking_vessel.n.01', output)
            root = wn.synset(data['root'])
            expected = {root.name()} | {s.name() for s in root.closure(lambda s: s.hyponyms())}
            self.assertEqual(set(data['nodes']), expected)
            for name, node in data['nodes'].items():
                synset = wn.synset(name)
                self.assertEqual(node['id'], name)
                self.assertEqual(node['type'], synset.lemma_names()[0])
                self.assertEqual(node['alternative_names'], sorted(set(synset.lemma_names()[1:]) - {node['type']}))
                self.assertEqual(node['qualities'], template['qualities'])
                self.assertTrue(all(v is None for v in node['qualities'].values()))
                self.assertEqual(node['superclass'], sorted(p.name() for p in synset.hypernyms() if p.name() in expected))
                self.assertEqual(set(node), set(template) | {'alternative_names', 'superclass'})
            self.assertEqual(data['nodes']['mug.n.04']['superclass'], ['drinking_vessel.n.01'])
            before = output.read_bytes()
            self.assertEqual(build_wordnet_branch(schema, 'drinking_vessel.n.01', output), data)
            self.assertEqual(before, output.read_bytes())
            ttl = Path(directory) / 'branch.ttl'
            convert(output, ttl)
            graph = Graph().parse(ttl, format='turtle')
            self.assertEqual(set(graph), set(build_graph(data)))
            self.assertEqual(list(graph.triples((None, RDF.type, None))), [])
            self.assertTrue(list(graph.triples((None, RDFS.subClassOf, None))))
            original = ttl.read_bytes()
            convert(output, ttl)
            self.assertEqual(original, ttl.read_bytes())

    def test_nested_template_and_other_root(self):
        schema = {'type': 'object', 'properties': {
            'id': {'type': 'string'}, 'name': {'type': 'string'},
            'properties': {'type': 'object', 'properties': {
                'custom': {'$ref': '#/$defs/custom'}, 'vector': {'type': 'array'}}}},
            '$defs': {'custom': {'type': 'object', 'properties': {'unknown': {'type': 'number'}}}}}
        self.assertEqual(instantiate_schema(schema)['properties'], {'custom': {'unknown': None}, 'vector': None})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'schema.json'
            path.write_text(json.dumps(schema))
            data = build_wordnet_branch(path, 'bring.v.01', Path(directory) / 'verbs.json')
            self.assertIn('bring.v.01', data['nodes'])
            self.assertEqual(data['nodes']['bring.v.01']['name'], wn.synset('bring.v.01').lemma_names()[0])
            with self.assertRaises(WordNetError):
                build_wordnet_branch(path, 'not_a_synset.n.01', Path(directory) / 'bad.json')


if __name__ == '__main__':
    unittest.main()
