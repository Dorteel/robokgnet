# RoboKGNet

RoboKGNet provides schema-shaped WordNet object types, ConceptNet-seeded location
histograms, and small VerbNet/FrameNet demo resources. Canonical JSON artifacts
are human-readable; Turtle files are generated machine representations.

## RoboKGNet creation

With the project environment activated, rebuild the four canonical JSON resources:

```bash
python recreate_robokgnet.py
```

See [the creation pipeline](docs/robokgnet_creation.md) for inputs, schemas,
setup, and individual stage commands.

## Add an action frame

See [action frame creation](docs/action_frame_creation.md) for schema and alignment requirements.

```bash
python add_action_frame.py --verbnet-class <class> --schema <schema>
```

## Explore visually

From the repository root, using the local environment:

```bash
.venv/bin/python -B tools/view_robokgnet.py --graph both
```

A local browser view opens automatically after loading. Choose `--graph wordnet`
or `--graph conceptnet` to load just one artifact. Use `--no-browser` to print the
URL without opening a browser, and optionally `--port 8765` for a fixed port.
Stop with Ctrl+C. No internet connection or JavaScript library is needed.

The default **Simplified semantic view** starts at an enriched object when
ConceptNet is loaded. Search `aircraft` to inspect its seeded `sky` location.
Book has no histogram because its explicit source mappings are unresolved. Labels omit `/c/en/` and
replace underscores with spaces; exact resource URIs remain in the inspector.

- **View** switches between **Simplified semantic view** and **Raw RDF view**.
  Raw view exposes the original assertion nodes and RDF relationships.
- **Relations** offers **Concept neighborhood**, **Only AtLocation**,
  **Only mappings**, and **Only WordNet hierarchy**.
- **Show WordNet mappings** adds mapping candidates to the default semantic
  neighborhood; mappings are hidden until requested. **Only mappings** shows
  them regardless of the checkbox. Other exclusive filters stay exclusive.
- Exact label searches center automatically (ConceptNet concepts first); press
  Enter to select the best partial match, or choose a result. Search remains
  local to the artifacts loaded by `--graph`.
- Click to inspect, double-click to explore, drag the background to pan, and
  use the wheel to zoom. Large neighborhoods page through 40 relations at a time.

The simplified graph is a **visualization projection only**: original RDF
assertions, mappings, provenance, and version boundaries remain unchanged.
External WordNet 3.1 targets without imported labels keep an identifier-based
caption; the viewer does not invent names or resolve ambiguous mappings.

## Current resources

| Resource | Content | Generated artifacts |
| --- | --- | --- |
| WordNet 3.0 | 29,581 schema-shaped physical-object types | [robokgwordnet.json](robonet_graph/robokgwordnet.json), [robokgwordnet.ttl](robonet_graph/robokgwordnet.ttl) |
| ConceptNet AtLocation | Exact object-backbone copy with integer location histograms only | [robokgconceptnet.json](robonet_graph/robokgconceptnet.json) |
| VerbNet 2.1 | Schema-valid bring-11.3 template plus four role definitions and six formal semantic frames | [robokgverbnet.json](robonet_graph/robokgverbnet.json), [robokgverbnet.ttl](robonet_graph/robokgverbnet.ttl) |
| FrameNet 1.7 + SemLink | Bringing/Scrutiny: definitions, Frame Elements, evoking lexical units, explicit member alignments | [framenet.json](robonet_graph/framenet.json), [robokgframenet.ttl](robonet_graph/robokgframenet.ttl) |
| Planning prototype | RDFS builder and static task/YAML/PDDL resources; not connected to the generated graphs | [planning.py](planning.py), `bringup/` |

**Artifacts remain separately generated.** Numeric ConceptNet WordNet 3.1
mappings now connect to the 3.0 object backbone through exact shared sense keys;
all candidates and unresolved cases are preserved. No label-based sense guessing
or runtime learning is performed.

## Setup

Python 3.10+ is recommended (validated with Python 3.12).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r wordnet/requirements.txt
```

The viewer currently supports WordNet and ConceptNet only. This is enough to view the existing TTL files. Regeneration and corpus-backed
tests require the following explicit corpus setup:

```bash
.venv/bin/python -m nltk.downloader -d .venv/nltk_data wordnet wordnet31 verbnet framenet_v17
```

## Build and test

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B wordnet_to_robokgwordnet.py --schema schemas/objects.json --root object.n.01 --output robonet_graph/robokgwordnet.json
.venv/bin/python -B wordnet/build_rdf.py
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B conceptnet_to_robokgconceptnet.py
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B verbnet_to_robokgverbnet.py
# FrameNet is a separate, unchanged resource; its legacy pipeline is documented separately.
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B -m unittest discover -s tests -v
```

See [STATUS.md](STATUS.md) for the architecture, file responsibilities, exact
commands, and current limitations. Details live in [wordnet/README.md](wordnet/README.md)
and [conceptnet/README.md](conceptnet/README.md). Important deferred design work
is curated in [notes.md](notes.md).

## Action-knowledge layers

- **WordNet:** schema-shaped object types and taxonomy; the canonical branch is now object-only.
- **FrameNet:** frame discovery, original Frame Element descriptions, and evoking words.
- **VerbNet:** formal action roles, restrictions, and structured event semantics.
- **SemLink2:** explicit member-level FrameNet ↔ VerbNet evidence, without invented role mappings.

See [action_knowledge/README.md](action_knowledge/README.md) for the exact six
alignments, subclass handling, statistics, and focused test command. There is no
runtime instruction parser or planning integration in this pipeline.

## Knowledge Interface

Downstream code should use [knowledge_interface.py](knowledge_interface.py) as
its public access layer, rather than querying RDF directly. `KnowledgeInterface`
loads all four generated TTL files relative to its own repository location,
independently of the current working directory. Missing graphs raise an actionable
error; no corpora or network requests are needed at runtime.

```python
from knowledge_interface import KnowledgeInterface

ki = KnowledgeInterface()
ki.resolve_wordnet("mug")          # List of exported synset candidates and labels
ki.get_frame_for_word("bring")     # List of FrameNet frame names from evoking words
ki.get_verbnet_class("Bringing")   # List of exported VerbNet class scopes
ki.describe_action("bring")        # Combined frame/class candidates with evidence
ki.get_at_locations("aircraft")    # Seed histogram, counts, and grounding IDs
```

Hierarchy methods `get_superclasses()` and `get_subclasses()` accept canonical
synset IDs/URIs and return **direct exported** neighbors. Frame Element methods
return original descriptions; VerbNet roles include restriction trees and
semantics retain ordered arguments, event names, and conditional structure.
Unknown terms return empty collections. Candidate lists are never silently
reduced to a preferred sense or frame. `describe_action()` returns
`{word, frame_candidates: [...]}`; each frame includes `verbnet_candidates` and
member-specific alignment records, so multiple interpretations remain explicit.

AtLocation accepts a grounded subject's label, canonical synset ID, URI, or
recorded source grounding. Results expose seed/observation/total counts and all
location IDs. Book currently returns no result: its phrase-component source
mappings cannot be safely grounded to the object backbone.
This layer is a lookup interface, not an instruction parser or Scenario builder.
The older interface inside `planning.py` remains a separate prototype, not the
entry point for current generated resources.

Run the labeled bring/search demo (it abbreviates repeated semantics to the first
frame when printing, while API calls return all frames):

```bash
.venv/bin/python -B knowledge_interface.py
```

Run its focused tests:

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_knowledge_interface.py' -v
```

## Simplified WordNet source

The WordNet source representation is now `robokgwordnet.json`, generated from an
unchanged copy of CMOC's `schemas/objects.json`. It uses `id`, lexical `type`,
`alternative_names`, a list of direct `superclass` IDs, and schema-derived null
qualities. Turtle is only a generated machine artifact. See
[wordnet/README.md](wordnet/README.md) for the node example, schema-nullability
limitation, generic root API, and focused tiny-subtree tests.

## Simplified VerbNet source

[robokgverbnet.json](robonet_graph/robokgverbnet.json) is now the canonical
**bring-11.3-only** resource. CMOC's unchanged schema defines the four nullable
entity slots in `frame`; source role restrictions and ordered semantics are
class-level annotations alongside it. Search and subclass semantics are not
imported. See [verbnet/README.md](verbnet/README.md) for the exact schema boundary,
regeneration command, and focused tests. The generator writes JSON only; existing
VerbNet TTL is not regenerated. WordNet and ConceptNet are unchanged.

## Current ConceptNet JSON simplification

The canonical ConceptNet JSON now copies every WordNet node unchanged except
for populated `qualities.location` values of the form `{"sky.n.01": 1}`.
Unsafe or ambiguous mappings are skipped, never distributed over candidates;
diagnostics appear only in the terminal. No Turtle was regenerated in this step.
The existing ConceptNet TTL, viewer and TTL-based interface still reflect the
previous representation until separately migrated. See
[conceptnet/README.md](conceptnet/README.md) for the current JSON-only command.
