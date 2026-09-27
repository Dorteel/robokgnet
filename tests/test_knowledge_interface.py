"""Small public API checks against the generated resources."""
import json
from pathlib import Path
import tempfile
import unittest
from knowledge_interface import KnowledgeInterface

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ki = KnowledgeInterface()

    def test_resources_wordnet_and_hierarchy(self):
        self.assertEqual(set(self.ki.loaded_resources), {'wordnet', 'conceptnet', 'verbnet', 'framenet'})
        self.assertTrue(all(p.is_absolute() and p.exists() for p in self.ki.loaded_resources.values()))
        candidates = self.ki.resolve_wordnet('mug')
        self.assertGreater(len(candidates), 1)
        self.assertIn('mug.n.04', {r['synset_id'] for r in candidates})
        self.assertTrue(all(r['label'] and r['uri'] for r in candidates))
        self.assertEqual([r['synset_id'] for r in self.ki.get_superclasses('mug.n.04')], ['drinking_vessel.n.01'])
        self.assertIn('mug.n.04', {r['synset_id'] for r in self.ki.get_subclasses('drinking_vessel.n.01')})

    def test_action_lookup_and_structured_semantics(self):
        source = json.loads((ROOT / 'robonet_graph/verbnet.json').read_text())
        for word, frame, cls in [('bring', 'Bringing', 'bring-11.3'), ('search', 'Scrutiny', 'search-35.2')]:
            self.assertIn(frame, self.ki.get_frame_for_word(word))
            self.assertEqual(self.ki.get_verbnet_class(frame), [cls])
            self.assertEqual(self.ki.get_verbnet_class(word), [cls])
            descriptions = self.ki.get_role_descriptions(frame)
            self.assertTrue(descriptions)
            self.assertTrue(all(descriptions.values()))
            semantics = self.ki.get_verbnet_semantics(cls)
            self.assertEqual([f['semantics'] for f in semantics], [f['semantics'] for f in source['classes'][cls]['frames']])
            combined = self.ki.describe_action(word)['frame_candidates']
            match = next(r for r in combined if r['framenet_frame'] == frame)
            self.assertEqual(match['verbnet_candidates'][0]['verbnet_class'], cls)
            self.assertTrue(all(r['member'] == word for r in match['alignments']))
        self.assertEqual({r['name'] for r in self.ki.get_verbnet_roles('bring-11.3')}, {'Agent', 'Theme', 'Source', 'Destination'})
        self.assertIn('Agent', self.ki.get_role_descriptions('Bringing'))

    def test_locations_and_unknowns(self):
        results = self.ki.get_at_locations('book')
        self.assertEqual({r['location'] for r in results}, {'bed', 'floor', 'row', 'stack'})
        self.assertEqual(results, self.ki.get_at_locations('/c/en/book'))
        for r in results:
            self.assertEqual(r['wordnet_version'], '3.1')
            self.assertEqual(len(r['subject_wordnet_mappings']), 2)
            self.assertTrue(r['wordnet_mappings'])
            self.assertNotIn('weight', r)
        self.assertEqual(self.ki.get_at_locations(results[0]['subject_wordnet_mappings'][0]), results)
        self.assertEqual(self.ki.get_at_locations('book.n.01'), [])  # No guessed 3.0/3.1 bridge.
        for method in ('resolve_wordnet','get_superclasses','get_subclasses','get_frame_for_word',
                       'get_frame_elements','get_verbnet_class','get_verbnet_roles','get_verbnet_semantics','get_at_locations'):
            self.assertEqual(getattr(self.ki, method)('not_a_real_resource'), [], method)
        self.assertEqual(self.ki.get_role_descriptions('not_a_real_resource'), {})
        self.assertEqual(self.ki.describe_action('not_a_demo_action')['frame_candidates'], [])

    def test_missing_graph_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, 'Missing RoboKGNet graph.*robokgwordnet.ttl'):
                KnowledgeInterface(directory)


if __name__ == '__main__':
    unittest.main()
