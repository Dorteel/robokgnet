"""Temporary-file checks for multi-action creation and public API compatibility."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from add_action_frame import add_action_frame
from knowledge_interface import KnowledgeInterface
from verbnet_framenet_enrichment import save_action
from verbnet_to_robokgverbnet import build_verbnet_resource


def action(identifier):
    return dict(id=identifier, members=['take'], framenet_frame='Bringing',
                evoking_words=['carry'], frame={'source': None}, additional_frame_elements={})


class AddActionTests(unittest.TestCase):
    def test_upsert_and_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'actions.json'
            output.write_text('{}')
            first, second = action('bring-11.3'), action('mock-1')
            save_action(first, output)
            self.assertEqual(json.loads(output.read_text()), {first['id']: first})
            save_action(second, output)
            first['members'] = ['updated']
            save_action(first, output)
            expected = {first['id']: first, second['id']: second}
            self.assertEqual(json.loads(output.read_text()), expected)
            before = output.read_bytes()
            save_action(first, output)
            self.assertEqual(output.read_bytes(), before)
            output.write_text(json.dumps(second))  # Previous single-entry format.
            save_action(first, output)
            self.assertEqual(output.read_bytes(), before)
            concepts = Path(directory) / 'concepts.json'
            concepts.write_text('{"nodes": {}}')
            ki = KnowledgeInterface(concepts, output)
            self.assertEqual(ki.get_action(second['id']), second)
            self.assertEqual(len(ki.resolve_action('carry')), 2)

    def test_reuses_builders_and_writes_only_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            evidence = path / 'semlink.json'
            evidence.write_text('{"alignments": []}')
            output = path / 'actions.json'
            minimal = dict(id='mock-1', members=['take'], frame={'source': None})
            result = action('mock-1')
            with patch('add_action_frame.build_verbnet_resource', return_value=minimal) as build, \
                 patch('add_action_frame.enrich', return_value=result) as enrich:
                add_action_frame('mock-1', 'mock-schema', output, evidence)
                build.assert_called_once_with('mock-schema', 'mock-1')
                enrich.assert_called_once_with(minimal, [], ())
            stored = json.loads(output.read_text())['mock-1']
            self.assertEqual(set(stored), {'id', 'members', 'framenet_frame',
                                          'evoking_words', 'frame', 'additional_frame_elements'})
            self.assertEqual(set(path.iterdir()), {evidence, output})
            before = output.read_bytes()
            with patch('add_action_frame.build_verbnet_resource', return_value=minimal), \
                 patch('add_action_frame.enrich', side_effect=ValueError('no alignment')):
                with self.assertRaises(ValueError):
                    add_action_frame('mock-1', 'mock-schema', output, evidence)
            self.assertEqual(output.read_bytes(), before)

    def test_generic_schema_and_exact_class(self):
        with tempfile.TemporaryDirectory() as directory:
            schema = Path(directory) / 'schema.json'
            schema.write_text(json.dumps({
                'verbnet_class': 'mock-1', 'type': 'object',
                'properties': {'custom_role': {'type': ['string', 'null']}},
            }))
            xml = ET.fromstring('<VNCLASS ID="mock-1"><MEMBERS><MEMBER name="sample"/></MEMBERS>'
                                '<SUBCLASSES><VNSUBCLASS ID="mock-1-1"><MEMBERS>'
                                '<MEMBER name="excluded"/></MEMBERS></VNSUBCLASS></SUBCLASSES></VNCLASS>')
            with patch('verbnet_to_robokgverbnet.vn.vnclass', return_value=xml):
                result = build_verbnet_resource(schema, 'mock-1')
            self.assertEqual(result, {'id': 'mock-1', 'members': ['sample'],
                                      'frame': {'custom_role': None}})


if __name__ == '__main__':
    unittest.main()
