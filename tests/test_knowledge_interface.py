"""API checks use temporary JSON exclusively, never writable real resources."""
import json
from pathlib import Path
import tempfile
import unittest

from knowledge_interface import KnowledgeInterface


class KnowledgeInterfaceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.concepts_path = Path(directory.name) / "concepts.json"
        self.actions_path = Path(directory.name) / "actions.json"
        self.concepts = {
            "root": "object.n.01", "wordnet_version": "3.0",
            "nodes": {
                "mug.n.04": {
                    "id": "mug.n.04", "type": "mug", "alternative_names": ["coffee_mug"],
                    "superclass": ["drinking_vessel.n.01"], "qualities": {"location": None},
                },
                "mug.n.01": {
                    "id": "mug.n.01", "name": "mug", "alternative_names": [],
                    "superclass": [], "qualities": {"location": {}},
                },
            },
        }
        self.action = {
            "id": "bring-11.3", "members": ["take"], "framenet_frame": "Bringing",
            "frame": {"source": None, "custom_role": {
                "framenet_element": "Theme", "description": "Stored description.",
            }},
            "additional_frame_elements": {"Goal": {"description": "Stored goal."}},
        }
        self.concepts_path.write_text(json.dumps(self.concepts))
        self.actions_path.write_text(json.dumps(self.action))
        self.ki = KnowledgeInterface(self.concepts_path, self.actions_path)

    def test_concept_resolution_and_hierarchy(self):
        node = self.concepts["nodes"]["mug.n.04"]
        self.assertEqual(self.ki.get_concept("mug.n.04"), node)
        self.assertEqual(self.ki.resolve_concept("mug.n.04"), [node])
        self.assertEqual(self.ki.resolve_concept("COFFEE_MUG"), [node])
        self.assertEqual(len(self.ki.resolve_concept("MUG")), 2)
        self.assertEqual(self.ki.get_alternative_names("mug.n.04"), ["coffee_mug"])
        self.assertEqual(self.ki.get_superclasses("mug.n.04"), ["drinking_vessel.n.01"])
        self.assertEqual(self.ki.describe("mug"), self.ki.resolve_concept("mug"))
        self.assertIsNone(self.ki.describe("unknown"))
        with self.assertRaises(KeyError):
            self.ki.get_concept("unknown")

    def test_updates_save_and_reload(self):
        original = self.concepts_path.read_bytes()
        actions_before = self.actions_path.read_bytes()
        self.assertEqual(self.ki.get_locations("mug.n.04"), [])
        self.assertEqual(self.ki.get_locations("mug.n.01"), [])
        self.ki.update_location("mug.n.04", "kitchen.n.01")
        self.ki.update_location("mug.n.04", "kitchen.n.01")
        self.ki.update_location("mug.n.04", "table.n.01", 3)
        self.assertEqual(self.ki.get_locations("mug.n.04"),
                         [("table.n.01", 3), ("kitchen.n.01", 2)])
        self.assertEqual(self.concepts_path.read_bytes(), original)
        self.ki.save()
        reloaded = KnowledgeInterface(self.concepts_path, self.actions_path)
        self.assertEqual(reloaded.get_locations("mug.n.04"), self.ki.get_locations("mug.n.04"))
        first = self.concepts_path.read_bytes()
        reloaded.save()
        self.assertEqual(self.concepts_path.read_bytes(), first)
        self.assertEqual(self.actions_path.read_bytes(), actions_before)

    def test_validation_and_copy_isolation(self):
        for increment in (0, -1, True, 1.5, "1"):
            with self.assertRaises(ValueError):
                self.ki.update_location("mug.n.04", "kitchen.n.01", increment)
        for location in ("", "  ", None, 5):
            with self.assertRaises(ValueError):
                self.ki.update_location("mug.n.04", location)
        with self.assertRaises(KeyError):
            self.ki.update_location("unknown", "kitchen.n.01")
        node = self.ki.get_concept("mug.n.04")
        node["qualities"]["location"] = {"fake": 99}
        self.assertEqual(self.ki.get_locations("mug.n.04"), [])

    def test_action_and_dynamic_roles(self):
        self.assertEqual(self.ki.get_action("bring-11.3"), self.action)
        self.assertEqual(self.ki.resolve_action("bring-11.3"), [self.action])
        self.assertEqual(self.ki.resolve_action("TAKE"), [self.action])
        self.assertEqual(self.ki.resolve_action("bring"), [])
        self.assertEqual(self.ki.get_action_frame("bring-11.3"), self.action["frame"])
        self.assertEqual(self.ki.get_frame_roles("bring-11.3"), ["source", "custom_role"])
        self.assertIsNone(self.ki.get_role("bring-11.3", "source"))
        self.assertEqual(self.ki.get_role("bring-11.3", "custom_role"),
                         self.action["frame"]["custom_role"])
        self.assertEqual(self.ki.get_additional_frame_elements("bring-11.3"),
                         self.action["additional_frame_elements"])
        self.assertEqual(self.ki.describe("take"), [self.action])
        with self.assertRaises(KeyError):
            self.ki.get_action("unknown")

    def test_loads_once(self):
        self.concepts_path.unlink()
        self.actions_path.unlink()
        self.assertTrue(self.ki.resolve_concept("mug"))
        self.assertTrue(self.ki.resolve_action("take"))


if __name__ == "__main__":
    unittest.main()
