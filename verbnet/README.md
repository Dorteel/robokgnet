# Schema-driven bring resource

Pipeline: `schemas/bring-11.3.json` + NLTK VerbNet →
`verbnet_to_robokgverbnet.py` → `robonet_graph/robokgverbnet.json`. This build generates JSON only.

## Schema boundary

The schema is an unchanged copy of
`/home/kai/ros2_ws/src/cmoc/schemas/task_frames/bring-11.3.json`.
It permits exactly four nullable entity-ID slots: agent, theme, source, destination.
It does **not** define a class-level semantics representation, and forbids extra
properties. Therefore **only the JSON's `frame` object is a schema instance**:

```json
{"agent": null, "theme": null, "source": null, "destination": null}
```

VerbNet describes roles, not observed entities, so all slots are unknown. No role
name is fabricated as an entity ID. Class-level `id`, `members`, `role_definitions`, and
`frames` are separate annotations around that schema-valid instance. The whole
resource is not claimed to validate against the task-instance schema. This small
wrapper is necessary to retain the requested formal semantics without altering
the actual CMOC schema.

`role_definitions` retains the exact Agent, Theme, Source and Destination names
and nested AND/OR selectional restrictions. `frames` retains the six direct
frames, source descriptions, examples and ordered semantic records. Predicates
are motion, equals, cause and location. Each argument retains its source type and
value (including during/start/end and distinct E0/E1 variables); polarity and other
source attributes are preserved. Conditional grouping is retained if present,
never inferred from missing arguments or examples.

Direct lexical members are retained alongside the schema instance. In NLTK VerbNet 2.1,
the parent bring-11.3 directly contains take, while bring is declared in subclass
bring-11.3-1. This export contains only the parent's direct roles and frames; it
does not import subclass frames, flatten inheritance, or add SemLink/FrameNet data.
Search is intentionally absent. Existing FrameNet artifacts remain unchanged and
may still reference classes/members not materialized in the new VerbNet artifact.

## Existing RDF

The existing TTL and RDF converter are historical artifacts, untouched by this
JSON-only build. They should not be assumed to reflect the current JSON.

## Build and test

Setup, if not already installed:

```bash
.venv/bin/python -m pip install -r wordnet/requirements.txt
.venv/bin/python -m nltk.downloader -d .venv/nltk_data verbnet
```

From the repository root:

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B verbnet_to_robokgverbnet.py --schema schemas/bring-11.3.json --class bring-11.3 --output robonet_graph/robokgverbnet.json
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B -m unittest discover -s tests -p 'test_verbnet.py' -v
```

Python API: `build_verbnet_resource(schema_path, verbnet_class, output_path)`.
The generator checks that the schema class matches the requested class. Future
classes require their own actual schema; they are not part of this demo build.
The focused test checks the actual schema's allowed/required nullable slots,
compares predicates/argument ordering against NLTK's independent high-level
frame reader, and verifies deterministic JSON and absence of metadata or extra output files.
