"""Small tests for explicit semantic alignment without name-based guesses."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from nltk.corpus import framenet as fn
from verbnet_framenet_enrichment import build_resource, enrich

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'robonet_graph/robokgverbnet.json'
SEMLINK = ROOT / 'action_knowledge/semlink_demo.json'


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(INPUT.read_text())
        self.alignments = json.loads(SEMLINK.read_text())['alignments']

    def test_real_resource_and_determinism(self):
        before = INPUT.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'enriched.json'
            result = build_resource(INPUT, output, SEMLINK)
            self.assertEqual(set(result), {
                'id', 'members', 'framenet_frame', 'evoking_words', 'frame', 'additional_frame_elements'
            })
            self.assertEqual(result['id'], self.document['id'])
            self.assertEqual(result['members'], ['take'])
            self.assertEqual(result['framenet_frame'], 'Bringing')
            self.assertEqual(result['frame'], self.document['frame'])
            words = result['evoking_words']
            self.assertIsInstance(words, list)
            self.assertTrue(words)
            self.assertTrue(all(isinstance(word, str) for word in words))
            self.assertEqual(words, sorted(set(words)))
            self.assertIn('bring', words)
            self.assertIn('carry', words)
            self.assertIn('take', words)
            source = fn.frame_by_name('Bringing')
            for lu in source.lexUnit.values():
                self.assertIn(lu.name.removesuffix('.' + lu.POS.lower()), words)
            elements = source.FE
            self.assertEqual(result['additional_frame_elements'], {
                name: {'description': fe.definition} for name, fe in elements.items()
            })
            first = output.read_bytes()
            build_resource(INPUT, output, SEMLINK)
            self.assertEqual(first, output.read_bytes())
            self.assertEqual(list(Path(directory).iterdir()), [output])
        self.assertEqual(INPUT.read_bytes(), before)

    def test_duplicate_lexical_forms_and_multiword_units(self):
        frame = SimpleNamespace(
            FE={}, lexUnit={'carry.v': {}, 'carry.n': {}, 'take away.v': {}},
        )
        with patch.object(fn, 'frame_by_name', return_value=frame):
            result = enrich(self.document, self.alignments)
        self.assertEqual(result['evoking_words'], ['carry', 'take away'])

    def test_only_explicit_role_links_are_used(self):
        # Synthetic XML tests the mapping mechanism, not a claimed source alignment.
        mappings = ET.fromstring("""
        <root>
          <vncls class="11.3" fnframe="Bringing"><roles>
            <role vnrole="Destination" fnrole="Goal"/>
          </roles></vncls>
          <vncls class="11.3-1" fnframe="Bringing"><roles>
            <role vnrole="Agent" fnrole="Agent"/>
          </roles></vncls>
          <vncls class="11.3" fnframe="Carry_goods"><roles>
            <role vnrole="Theme" fnrole="Theme"/>
          </roles></vncls>
        </root>
        """).findall('vncls')
        before = copy.deepcopy(self.document)
        result = enrich(self.document, self.alignments, mappings)
        self.assertEqual(self.document, before)
        self.assertEqual(result['frame']['destination'], {
            'framenet_element': 'Goal',
            'description': fn.frame_by_name('Bringing').FE['Goal'].definition,
        })
        for slot in ('agent', 'source', 'theme'):
            self.assertIsNone(result['frame'][slot])
        self.assertNotIn('Goal', result['additional_frame_elements'])
        self.assertIn('Agent', result['additional_frame_elements'])
        # Conflicting explicit links must not be silently resolved.
        ET.SubElement(mappings[0].find('roles'), 'role',
                      vnrole='Destination', fnrole='Source')
        self.assertIsNone(enrich(self.document, self.alignments, mappings)['frame']['destination'])

    def test_exact_member_scope_and_ambiguous_frames(self):
        for rows in (
            [],
            [{'verbnet': 'bring-11.3-1', 'member': 'take', 'framenet': 'Bringing'}],
            [{'verbnet': 'bring-11.3', 'member': 'bring', 'framenet': 'Bringing'}],
            self.alignments + [
                {'verbnet': 'bring-11.3', 'member': 'take', 'framenet': 'Taking'}
            ],
        ):
            with self.assertRaises(ValueError):
                enrich(self.document, rows)

    def test_cannot_overwrite_input(self):
        before = INPUT.read_bytes()
        with self.assertRaisesRegex(ValueError, 'must not overwrite'):
            build_resource(INPUT, INPUT, SEMLINK)
        self.assertEqual(INPUT.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
