"""Only location integer histograms may differ from the object backbone."""
import copy
import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from nltk.corpus import wordnet31 as wn31
from conceptnet_to_robokgconceptnet import build_histograms

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'alignment_evidence', 'metadata', 'status', 'reason', 'conceptnet_subjects',
             'conceptnet_id', 'conceptnet_ids', 'wordnet31_ids', 'seed_count',
             'observation_count', 'applied_assertions', 'unapplied_assertions'}


def mapping_uri(name):
    synset = wn31.synset(name)
    return f'http://wordnet-rdf.princeton.edu/wn31/1{synset.offset():08d}-n'


class ConceptNetTests(unittest.TestCase):
    def assert_only_locations_changed(self, original, actual):
        self.assertEqual(set(original), set(actual))
        self.assertEqual(set(original['nodes']), set(actual['nodes']))
        restored = copy.deepcopy(actual)
        for name, node in actual['nodes'].items():
            histogram = node['qualities']['location']
            if histogram is not None:
                self.assertIsInstance(histogram, dict)
                for key, count in histogram.items():
                    self.assertRegex(key, r'^.+\.[nvars]\.\d+$')
                    self.assertIs(type(count), int)
                    self.assertGreater(count, 0)
            restored['nodes'][name]['qualities']['location'] = original['nodes'][name]['qualities']['location']
        self.assertEqual(restored, original)
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & FORBIDDEN)
                for child in value.values(): check(child)
            elif isinstance(value, list):
                for child in value: check(child)
        check(actual)

    def test_actual_output_is_exact_backbone_plus_histograms(self):
        original = json.loads((ROOT/'robonet_graph/robokgwordnet.json').read_text())
        actual = json.loads((ROOT/'robonet_graph/robokgconceptnet.json').read_text())
        self.assert_only_locations_changed(original, actual)
        self.assertEqual(actual['nodes']['aircraft.n.01']['qualities']['location'], {'sky.n.01': 1})

    def test_repetition_ambiguity_and_determinism(self):
        original = json.loads((ROOT/'robonet_graph/robokgwordnet.json').read_text())
        original['nodes'] = {k: original['nodes'][k] for k in ('mug.n.04','cup.n.01')}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, mappings, base, output = [folder / n for n in ('source.csv','mappings.csv','base.json','out.json')]
            base.write_text(json.dumps(original))
            with source.open('w') as f:
                writer = csv.writer(f); writer.writerow(['subject','predicate','object'])
                writer.writerows([
                    ['/c/en/explicit_only','AtLocation','/c/en/place'],
                    ['/c/en/explicit_only','AtLocation','/c/en/place'],
                    ['/c/en/ambiguous','AtLocation','/c/en/place'],
                    ['/c/en/explicit_only','AtLocation','/c/en/ambiguous_place'],
                    ['/c/en/partial','AtLocation','/c/en/place'],
                    ['/c/en/book','AtLocation','/c/en/place'],
                    ['/c/en/explicit_only','UsedFor','/c/en/place'],
                    ['/c/en/explicit_only','IsA','/c/en/place']])
            with mappings.open('w') as f:
                writer = csv.writer(f); writer.writerow(['conceptnet_concept','wordnet_synset'])
                for concept, name in [('explicit_only','mug.n.04'), ('place','kitchen.n.01'),
                                      ('ambiguous','mug.n.04'), ('ambiguous','cup.n.01'),
                                      ('ambiguous_place','kitchen.n.01'), ('ambiguous_place','living_room.n.01'),
                                      ('partial','mug.n.04')]:
                    writer.writerow(['/c/en/'+concept,mapping_uri(name)])
                writer.writerow(['/c/en/partial','http://wordnet-rdf.princeton.edu/wn31/example-p#Component-1'])
            terminal = io.StringIO()
            with redirect_stdout(terminal):
                result = build_histograms(source,mappings,base,output)
            self.assertIn('Applied: 2',terminal.getvalue())
            self.assertIn('Ambiguous: 2',terminal.getvalue())
            self.assert_only_locations_changed(original,result)
            # The location may be a valid WordNet synset outside the object export.
            self.assertEqual(result['nodes']['mug.n.04']['qualities']['location'], {'kitchen.n.01':2})
            self.assertIsNone(result['nodes']['cup.n.01']['qualities']['location'])
            first = output.read_bytes()
            with redirect_stdout(io.StringIO()):
                build_histograms(source,mappings,base,output)
            self.assertEqual(first,output.read_bytes())
            self.assertEqual(json.loads(base.read_text()),original)


if __name__ == '__main__':
    unittest.main()
