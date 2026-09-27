"""Focused corpus-backed checks for the demo lexical resources."""
import json
from pathlib import Path
import tempfile
import unittest
from nltk.corpus import verbnet as vn, framenet as fn
from rdflib import Graph, RDF, Literal, URIRef
from action_knowledge.build_json import extract, tree, walk, write_json
from action_knowledge.build_rdf import KG, VN, FN, node, verbnet_graph, framenet_graph, save, PROV

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'robonet_graph'


def read_tree(graph, uri):
    """Reconstruct ordered structure, ensuring RDF did not flatten it."""
    children = sorted(graph.objects(uri, KG.child), key=lambda c: int(graph.value(c, KG.position)))
    return {'tag': str(graph.value(uri, KG.tag)),
            'attributes': {str(p)[len(str(KG)+'attribute_'):]: str(o)
                           for p, o in graph.predicate_objects(uri) if str(p).startswith(str(KG)+'attribute_')},
            'text': str(graph.value(uri, KG.text) or ''),
            'children': [read_tree(graph, c) for c in children]}


class ActionKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verbs = json.loads((DATA / 'verbnet.json').read_text())
        cls.frames = json.loads((DATA / 'framenet.json').read_text())

    def test_scope_roles_and_exact_structured_semantics(self):
        self.assertEqual(set(self.verbs['classes']), {'bring-11.3', 'search-35.2'})
        graph = verbnet_graph(self.verbs)
        self.assertEqual(len(set(graph.subjects(RDF.type, KG.VerbNetClass))), 2)
        for name, record in self.verbs['classes'].items():
            xml = vn.vnclass(name)
            self.assertEqual(record['roles'], [tree(r) for r in xml.findall('THEMROLES/THEMROLE')])
            for role in record['roles']:
                self.assertEqual(read_tree(graph, node(VN, name + '/role/' + role['attributes']['type'])), role)
            for index, source in enumerate(xml.findall('FRAMES/FRAME')):
                for part in ('semantics', 'syntax'):
                    self.assertEqual(record['frames'][index][part], tree(source.find(part.upper())))
                    self.assertEqual(read_tree(graph, node(VN, name + '/frame/' + str(index) + '/' + part)), record['frames'][index][part])
        self.assertTrue(list(graph.triples((None, KG.phase, Literal('start')))))
        self.assertTrue(list(graph.triples((None, KG.phase, Literal('end')))))
        self.assertTrue(list(graph.triples((None, KG.role, node(VN, 'bring-11.3/role/Source')))))
        bring = next(m for m in self.verbs['classes']['bring-11.3']['members'] if m['name'] == 'bring')
        self.assertEqual(bring['declaring_class'], 'bring-11.3-1')

    def test_framenet_definitions_lexical_units_and_explicit_alignments(self):
        seeds = self.frames['metadata']['semlink_evidence']['demo_seeds']
        self.assertEqual(set(self.frames['frames']), {r['framenet'] for r in seeds})
        self.assertEqual(set(self.frames['frames']), {'Bringing', 'Scrutiny'})
        graph = framenet_graph(self.frames)
        for name, record in self.frames['frames'].items():
            source = fn.frame_by_name(name)
            self.assertEqual(record['definition'], source.definition)
            self.assertEqual(set(record['frame_elements']), set(source.FE))
            self.assertEqual({lu['name'] for lu in record['lexical_units']}, set(source.lexUnit))
            for fe, data in record['frame_elements'].items():
                self.assertEqual(data['definition'], source.FE[fe].definition)
                self.assertEqual(data['core_type'], source.FE[fe].coreType)
        self.assertEqual(len(set(graph.subjects(RDF.type, KG.FrameNetFrame))), 2)
        self.assertEqual(len(set(graph.subjects(RDF.type, KG.SemLinkAlignment))), 6)
        for record in self.frames['alignments']:
            self.assertIn({k:v for k,v in record.items() if k != 'exported_class_scope'},
                          self.frames['metadata']['semlink_evidence']['alignments'])
            member = node(VN, record['verbnet'] + '/member/' + record['member'])
            self.assertIn((member, RDF.type, KG.VerbMember), verbnet_graph(self.verbs))
        self.assertEqual({r['member'] for r in self.frames['alignments']}, {'bring','take','check','probe','scour','search'})
        self.assertEqual(len(list(graph.triples((None, PROV.wasDerivedFrom, None)))), 6)

    def test_deterministic_json_and_turtle_reload(self):
        self.assertEqual(extract(), (self.verbs, self.frames))
        with tempfile.TemporaryDirectory() as directory:
            for name, document, builder in [('verbnet', self.verbs, verbnet_graph), ('framenet', self.frames, framenet_graph)]:
                path = Path(directory) / (name + '.json')
                write_json(document, path)
                self.assertEqual(path.read_bytes(), (DATA / path.name).read_bytes())
                graph = builder(document)
                ttl = Path(directory) / ('robokg' + name + '.ttl')
                save(graph, ttl)
                self.assertEqual(ttl.read_bytes(), (DATA / ttl.name).read_bytes())
                loaded = Graph().parse(ttl, format='turtle')
                self.assertEqual(set(loaded), set(graph))


if __name__ == '__main__':
    unittest.main()
