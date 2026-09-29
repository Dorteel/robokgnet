"""The public RoboKGNet API, backed only by canonical concept and action JSON.

Resolvers return all exact lexical matches (case-insensitive), never guessed
senses. Missing IDs raise KeyError; unresolved terms return []. Getters return
copies so updates go through update_location(). Only save() writes to disk.
"""
from copy import deepcopy
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "robonet_graph"


class KnowledgeInterface:
    def __init__(self, concepts_path=DATA / "robokgconceptnet.json",
                 actions_path=DATA / "robokgverbnet_framenet.json"):
        self._concepts_path = Path(concepts_path)
        self._concepts = json.loads(self._concepts_path.read_text(encoding="utf-8"))
        actions = json.loads(Path(actions_path).read_text(encoding="utf-8"))
        self._actions = {actions["id"]: actions} if isinstance(actions.get("id"), str) else actions

    def resolve_concept(self, term):
        """Return complete entries matching an ID, type/name, or stored alias."""
        return [
            deepcopy(node) for _, node in sorted(self._concepts["nodes"].items())
            if node["id"] == term or any(
                isinstance(name, str) and name.casefold() == term.casefold()
                for name in [node.get("type"), node.get("name"),
                             *node.get("alternative_names", [])]
            )
        ]

    def get_concept(self, concept_id):
        """Return the complete stored entry for an exact synset ID."""
        return deepcopy(self._concepts["nodes"][concept_id])

    def get_alternative_names(self, concept_id):
        return self.get_concept(concept_id)["alternative_names"]

    def get_superclasses(self, concept_id):
        """Return direct superclass IDs, without recursive expansion."""
        return self.get_concept(concept_id)["superclass"]

    def get_subclasses(self, concept_id):
        """Return direct stored subclass IDs; never infer synonym relations."""
        self.get_concept(concept_id)  # Preserve unknown-ID validation.
        return sorted(node['id'] for node in self._concepts['nodes'].values()
                      if concept_id in node.get('superclass', []))

    def get_locations(self, concept_id):
        """Return (synset, count) pairs; break equal-count ties by synset ID."""
        histogram = self._concepts["nodes"][concept_id]["qualities"]["location"] or {}
        return sorted(histogram.items(), key=lambda item: (-item[1], item[0]))

    def update_location(self, concept_id, location_synset, increment=1):
        """Increment an in-memory histogram; locations may lie outside the backbone."""
        node = self._concepts["nodes"][concept_id]
        if type(increment) is not int or increment <= 0:
            raise ValueError("increment must be a positive integer")
        if not isinstance(location_synset, str) or not location_synset.strip():
            raise ValueError("location_synset must be a non-empty string")
        if node["qualities"]["location"] is None:
            node["qualities"]["location"] = {}
        histogram = node["qualities"]["location"]
        histogram[location_synset] = histogram.get(location_synset, 0) + increment

    def save(self):
        """Persist concepts to the configured path; action knowledge is never written.

        Rebuilding static resources replaces this file, including saved updates.
        """
        self._concepts_path.write_text(
            json.dumps(self._concepts, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def resolve_action(self, term):
        """Match only the stored ID, members, or lexical name fields."""
        matches = []
        for _, action in sorted(self._actions.items()):
            names = [*action["members"], *action.get("evoking_words", []),
                     action.get("name"), action.get("verb"),
                     *action.get("alternative_names", [])]
            if action["id"] == term or any(
                isinstance(name, str) and name.casefold() == term.casefold() for name in names
            ):
                matches.append(deepcopy(action))
        return matches

    def get_action(self, action_id):
        """Return the complete stored action; no runtime corpus lookup."""
        return deepcopy(self._actions[action_id])

    def get_action_frame(self, action_id):
        return self.get_action(action_id)["frame"]

    def get_frame_roles(self, action_id):
        return list(self.get_action_frame(action_id))

    def get_role(self, action_id, role):
        """Return the stored role value, including null when no mapping exists."""
        return self.get_action_frame(action_id)[role]

    def get_additional_frame_elements(self, action_id):
        return self.get_action(action_id).get("additional_frame_elements", {})

    def describe(self, term):
        """Return concept matches first, otherwise action matches, otherwise None."""
        return self.resolve_concept(term) or self.resolve_action(term) or None


if __name__ == "__main__":
    ki = KnowledgeInterface()
    # print(ki.resolve_concept("aircraft"))
    # print(ki.get_locations("aircraft.n.01"))
    # print(ki.resolve_action("take"))
    # print(ki.get_frame_roles("bring-11.3"))
    # print(ki.get_role("bring-11.3", "source"))
