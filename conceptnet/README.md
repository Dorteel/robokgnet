# Minimal ConceptNet enrichment

`conceptnet_to_robokgconceptnet.py` deep-copies `robokgwordnet.json` and modifies
only `nodes[subject_synset].qualities.location`. Every original node and all other
fields remain unchanged. Output is `robonet_graph/robokgconceptnet.json`.

```json
{"location": {"sky.n.01": 1}}
```

Only AtLocation rows are processed. Each usable row adds one integer occurrence;
repeated evidence increments that integer. Unchanged location fields remain as
they were in the backbone (currently null).

Mappings are construction details, not knowledge-resource fields. Numeric
WordNet 3.1 mapping URIs are resolved through exact shared sense keys to 3.0.
Both endpoints must resolve completely to one distinct synset. Ambiguous,
missing, non-synset, or partially unresolved mappings are skipped. Restricting a
candidate set to the backbone is not used as disambiguation. The subject must
exist in the backbone; a uniquely resolved location need not be exported there.
No English-label guessing occurs.

The output contains no added metadata, mapping evidence, statuses, source IDs,
or separate seed/observation counters. The generator prints diagnostics only to
the terminal; it does not write a diagnostic file. This task does not regenerate
Turtle. The existing TTL, its converter, and TTL-based consumers still represent
the earlier format and must not be mistaken for this updated canonical JSON.
Do not run the legacy `conceptnet/build_rdf.py` on this new format.

Setup if required:

```bash
.venv/bin/python -m nltk.downloader -d .venv/nltk_data wordnet wordnet31
```

Generate and test from the repository root:

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B conceptnet_to_robokgconceptnet.py
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B -m unittest discover -s tests -p 'test_conceptnet.py' -v
```

Optional input arguments remain `--source`, `--mappings`, `--backbone`, and
`--output`. Tests verify exact structural preservation, integer-only histograms,
repeated evidence, safe ambiguity rejection and deterministic output.
