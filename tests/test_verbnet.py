"""Focused tests for the minimal CMOC task-frame export."""
import json
from pathlib import Path
import tempfile
import unittest

from nltk.corpus import verbnet as vn
from verbnet_to_robokgverbnet import build_verbnet_resource

ROOT = Path(__file__).resolve().parents[1]


class VerbNetTests(unittest.TestCase):
    def test_exact_structure_and_determinism(self):
        schema_path = ROOT / 'schemas/bring-11.3.json'
        schema = json.loads(schema_path.read_text())
        expected = {
            'id': 'bring-11.3',
            'members': ['take'],
            'frame': dict.fromkeys(['agent', 'destination', 'source', 'theme']),
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'bring.json'
            document = build_verbnet_resource(schema_path, 'bring-11.3', output)
            self.assertEqual(document, expected)
            self.assertEqual(set(document), {'id', 'members', 'frame'})
            self.assertEqual(set(document['frame']),
                             {'agent', 'destination', 'source', 'theme'})
            self.assertEqual(set(document['frame']), set(schema['properties']))
            self.assertTrue(set(schema['required']) <= set(document['frame']))
            for field in document['frame']:
                self.assertIn('null', schema['properties'][field]['type'])
            direct_members = [
                member.get('name')
                for member in vn.vnclass('bring-11.3').findall('MEMBERS/MEMBER')
            ]
            self.assertEqual(document['members'], sorted(direct_members))
            self.assertEqual(json.loads(output.read_text()), expected)
            before = output.read_bytes()
            build_verbnet_resource(schema_path, 'bring-11.3', output)
            self.assertEqual(before, output.read_bytes())
            self.assertEqual(before, (ROOT / 'robonet_graph/robokgverbnet.json').read_bytes())
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_other_classes_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'bring.json'
            for class_id in ('bring-11.3-1', 'search-35.2'):
                with self.assertRaisesRegex(ValueError, 'Schema verbnet_class does not match'):
                    build_verbnet_resource(ROOT / 'schemas/bring-11.3.json',
                                           class_id, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
