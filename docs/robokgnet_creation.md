# Creating RoboKGNet

RoboKGNet builds static, prior semantic knowledge as four readable JSON resources.
The object pipeline is WordNet → ConceptNet enrichment; the action pipeline is
VerbNet → FrameNet enrichment. The rebuild runs them in that order.

## Standard rebuild

From the repository root, activate the environment with the installed dependencies:

```bash
source .venv/bin/activate
python recreate_robokgnet.py
```

The wrapper uses the same Python interpreter, runs each existing generator from
the repository root, and includes `.venv/nltk_data` in its corpus search path.
It prints four progress lines and a success message. If a stage fails, it prints
the captured error and exits immediately without running later stages. Earlier
completed outputs remain; the rebuild is not transactional.

For a new environment, install dependencies and corpora once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r wordnet/requirements.txt
python -m nltk.downloader -d .venv/nltk_data wordnet wordnet31 verbnet framenet_v17
```

Normal rebuilds use installed corpora and checked-in schemas, CSV files, and
SemLink snapshot; they do not fetch new knowledge. Reproducibility requires keeping
those inputs and corpus versions fixed. Existing generated JSON files are replaced.
No runtime observations are read or retained by these builders.

For the individual commands below, use the activated environment and set:

```bash
export NLTK_DATA="$PWD/.venv/nltk_data"
```

## 1. WordNet: object backbone

**Generator:** `wordnet_to_robokgwordnet.py`

**Inputs and sources:** NLTK WordNet 3.0 and `schemas/objects.json`, the copied
CMOC object schema. The schema supplies the nested object structure; WordNet
supplies identities and hierarchy.

**Output:** `robonet_graph/robokgwordnet.json`.

The builder traverses `object.n.01` and its noun hyponyms, assigning canonical
synset IDs, primary names, alternative names, and superclass links within the
selected branch. Unknown schema leaves are initialized to null, including
`qualities.location`. These are conceptual type templates, not fully populated
observed objects; null initialization does not imply validation against every
measurement constraint in CMOC's instance schema.

```bash
python -B wordnet_to_robokgwordnet.py --schema schemas/objects.json --root object.n.01 --output robonet_graph/robokgwordnet.json
```

## 2. ConceptNet: seed location histograms

**Generator:** `conceptnet_to_robokgconceptnet.py`

**Inputs:**
- `robonet_graph/robokgwordnet.json`
- `robonet_graph/filtered_conceptnet.csv`
- `robonet_graph/conceptnet_wordnet_mappings.csv`

**Sources:** filtered ConceptNet AtLocation assertions and explicit ConceptNet →
WordNet mappings. NLTK WordNet 3.1 and 3.0 provide exact shared sense keys for
converting numeric mapping targets.

**Schema:** inherits the CMOC object structure from the backbone; no new schema.

**Output:** `robonet_graph/robokgconceptnet.json`.

The output is structurally a full copy of `robokgwordnet.json`. Only
`qualities.location` may change, becoming a histogram such as:

```json
{"sky.n.01": 1, "hangar.n.01": 3}
```

Each applicable AtLocation row adds one integer occurrence. Both endpoints must
resolve unambiguously through explicit mappings, and the subject must exist in
the backbone. A location needs a valid WordNet synset but need not be a backbone
node. Missing, ambiguous, or partly unresolved mappings are skipped; names are
not used to guess senses. IsA and UsedFor rows are ignored. Diagnostics are printed
only, and are suppressed by the wrapper on successful runs.

```bash
python -B conceptnet_to_robokgconceptnet.py
```

## 3. VerbNet: minimal task frame

**Generator:** `verbnet_to_robokgverbnet.py`

**Inputs and sources:** installed NLTK VerbNet (`bring-11.3` only) and
`schemas/bring-11.3.json`, copied unchanged from CMOC's
`schemas/task_frames/bring-11.3.json`.

**Output:** `robonet_graph/robokgverbnet.json`.

CMOC defines the four frame slots; VerbNet supplies the class ID and direct lexical
members. The complete resource is:

```json
{
  "id": "bring-11.3",
  "members": ["take"],
  "frame": {
    "agent": null,
    "destination": null,
    "source": null,
    "theme": null
  }
}
```

Only `frame` is an instance of the CMOC task-frame schema. The class ID and
members sit outside it. In the installed VerbNet 2.1 corpus, `bring` belongs to
the excluded subclass `bring-11.3-1`; it is not manually added.

```bash
python -B verbnet_to_robokgverbnet.py
```

## 4. FrameNet: explicit semantic enrichment

**Generator:** `verbnet_framenet_enrichment.py`

**Inputs:** `robonet_graph/robokgverbnet.json`,
`action_knowledge/semlink_demo.json`, and installed NLTK FrameNet 1.7.

**Sources:** the repository's SemLink2 member/frame snapshot from
`instances/vn-fn2.json`, and original FrameNet Frame Element definitions.

**Schema:** retains the CMOC-derived slot keys; no additional CMOC schema is read.

**Output:** `robonet_graph/robokgverbnet_framenet.json`. The VerbNet input is
unchanged.

The explicit member-specific mapping `11.3-take → Bringing` selects the frame.
The output contains exactly `id`, `members`, `framenet_frame`, `frame`, and
`additional_frame_elements`.

The current SemLink2 snapshot supplies no role mappings. All four slots therefore
remain null, and all 24 Bringing Frame Elements appear separately with their
original descriptions. Similar role names are not treated as equivalence evidence.
The older SemLink role file maps class 11.3 to Carry_goods, not Bringing, so its
links cannot fill these slots. The generator accepts an optional authoritative
role-mapping file, but the standard build supplies none.

```bash
python -B verbnet_framenet_enrichment.py
```

## Rebuild outputs

All four files are written under `robonet_graph/`:

1. `robokgwordnet.json`
2. `robokgconceptnet.json`
3. `robokgverbnet.json`
4. `robokgverbnet_framenet.json`

These resources provide prior knowledge. Learning from repeated grounded robot
experiences is deferred; see [notes.md](../notes.md).
