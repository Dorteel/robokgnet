# Demo action knowledge: bring and search

`build_json.py` reads installed NLTK corpora and the small offline
`semlink_demo.json` snapshot. `build_rdf.py` reads only the resulting JSON files.
No existing WordNet, ConceptNet, or planning artifact is modified.

## Exact scope and alignment evidence

Export only `bring-11.3` and `search-35.2` as VerbNet class resources. Read their
**direct** thematic roles and frames through NLTK's XML reader, consistent with
CMOC's existing `tools/verbnet_semantic_patterns.py`. Do not use that utility's
per-predicate event normalization: it intentionally loses cross-predicate event
identity, which this export must preserve.

NLTK VerbNet 2.1 declares **take** directly in `bring-11.3`, while **bring** is
in `bring-11.3-1`. Include the latter member as scoped evidence, recording its
actual `declaring_class`; do not pretend it is a direct parent member or import
a third class's roles/frames. `hasScopedMember` intentionally reflects this scope.
Search's 24 direct members are retained. No inferred inherited subclass semantics
are introduced.

The existing CMOC SemLink snapshot comes from
https://raw.githubusercontent.com/cu-clear/semlink/master/instances/vn-fn2.json.
The local evidence file retains its retrieval date and parsed-table fingerprint.
Frame selection follows the exact demo member records `bring-11.3-1/bring` and
`search-35.2/search`, yielding **Bringing** and **Scrutiny**, respectively. Retain
all observed class/member records in the two demo scopes targeting those selected
frames:

| Declaring class | Member | FrameNet frame |
| --- | --- | --- |
| bring-11.3 | take | Bringing |
| bring-11.3-1 | bring | Bringing |
| search-35.2 | check | Scrutiny |
| search-35.2 | probe | Scrutiny |
| search-35.2 | scour | Scrutiny |
| search-35.2 | search | Scrutiny |

The broader search class also has members aligned to other frames; those do not
expand the demo frame selection. Alignment resources carry frame, exact member,
declaring class ID, exported class scope, and SemLink provenance. They are **not
class-wide equivalences** or role-level mappings. SemLink2 targets VerbNet 3.3,
while NLTK supplies 2.1; only exact observed class/member matches are retained.

## JSON and RDF structure

VerbNet roles, syntax, and semantics use a small ordered XML-tree representation:
`tag`, `attributes`, `text`, `children`. This preserves nested restriction logic,
all predicate arguments in order, original event variables/phases, polarity, and
any source conditional structures without flattening them into strings. Literal
argument values such as `start(E0)` are kept exactly; RDF additionally links event
arguments to frame-scoped EventVariable resources and records their phases.
No conditional action rules are inferred from optional syntax or frame frequency.

RDF has VerbNetClass, VerbMember, ThematicRole, VerbNetFrame, SemanticPredicate,
and SemanticArgument types. `hasFrame`, `hasRole`, and `hasPredicate` provide entry
points. Tree edges use `child` and zero-based `position`; `attribute_value`,
`attribute_type`, and other `attribute_*` predicates preserve source attributes.
An argument naming an exact declared role also has a `role` link. For example,
inspect a bring frame's location predicate arguments to find the Theme, Source,
Destination, and `start`/`end` event phases. Different source events (E0, E1) are
never renamed or equated unless the source itself expresses that relation.

FrameNet definitions and Frame Element definitions are copied verbatim from the
NLTK FrameNet 1.7 reader. Keep all FEs, core types, and lexical units of the two
selected frames. Lexical units preserve original names/POS, corpus IDs, and ordered
lexeme records, allowing future evoking-word lookup without implementing parsing.
RDF has FrameNetFrame, FrameElement, and LexicalUnit types with `hasFrameElement`,
`evokedBy`, and `definition`. Broader frame relations are intentionally deferred.

Namespaces are provisional project identities:

- vocabulary: `https://w3id.org/robokgnet/action/schema#`
- VerbNet: `https://w3id.org/robokgnet/verbnet/2.1/`
- FrameNet: `https://w3id.org/robokgnet/framenet/1.7/`

Explicit member WordNet keys are resolved using the existing semantic bridge's
policy: append missing `::`, resolve with `lemma_from_key`, never search a lemma.
Uncertain or unresolved keys remain in the source attributes and are reported as
warnings, not guessed. RDF references versioned WordNet 3.0 resources. Some targets
are outside the bring-only WordNet artifact; referencing them does not import or
expand that graph. There are 32 resolved member-sense links. Three uncertain
source keys (two for dive, one for shop) are recorded in metadata warnings and
excluded from WordNet grounding. Separate graph files are preserved.

## Regeneration and validation

From the repository root, install dependencies and corpora if missing:

```bash
.venv/bin/python -m pip install -r wordnet/requirements.txt
.venv/bin/python -m nltk.downloader -d .venv/nltk_data wordnet verbnet framenet_v17
```

Build JSON, then RDF:

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B action_knowledge/build_json.py
.venv/bin/python -B action_knowledge/build_rdf.py
```

Test:

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B -m unittest discover -s tests -p 'test_action_knowledge.py' -v
```

Tests compare the exact source scope, nested role restrictions, ordered semantics
and syntax, original FrameNet wording, lexical units, and explicit member links.
They reconstruct the ordered tree from RDF, verify deterministic JSON/Turtle,
and reload both generated Turtle files. No network access occurs during builds
or tests; already installed NLTK corpora are also discovered through NLTK's normal
search paths.

## Current statistics

| Metric | Value |
| --- | ---: |
| VerbNet class scopes | 2 |
| VerbNet members | 26 |
| VerbNet roles | 7 |
| VerbNet frames | 10 |
| Semantic predicate occurrences | 40 |
| FrameNet frames | 2 |
| Frame Elements | 35 |
| Lexical units | 80 |
| SemLink member alignments | 6 |
| verbnet.json | 91,211 bytes |
| framenet.json | 39,394 bytes |
| robokgverbnet.ttl | 2,071 triples; 230,658 bytes |
| robokgframenet.ttl | 1,237 triples; 112,829 bytes |

Source attribution: [VerbNet](https://verbs.colorado.edu/verbnet/),
[FrameNet](https://framenet.icsi.berkeley.edu/),
[SemLink](https://github.com/cu-clear/semlink), and
[WordNet](https://wordnet.princeton.edu/). Corpus excerpts retain their original
resource terms; these exports do not relicense them.
