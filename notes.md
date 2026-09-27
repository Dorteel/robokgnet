# Deferred architectural improvements

Keep this file curated: record important future design work intentionally excluded
from the current demo, not routine tasks. Update it alongside changes that make
such decisions; remove or revise entries when their limitations are resolved.

## Non-object semantic properties

### Why it matters
Future ORKA observations and semantic reasoning need to ground observed properties
as well as entity classes: colours, materials, weights, sizes, textures, shapes,
temperatures, and other perceptual or physical attributes.

### Current limitation
The WordNet backbone intentionally covers physical objects and demo-relevant
verbs. It does not provide a general property vocabulary or quantitative values
with units; the object subtree also omits some substance/material branches.

### Future direction
Decide whether additional WordNet branches, dedicated property vocabularies and
ontologies, or a mixed approach best represent these concepts. Distinguish
categorical properties from measured values and their units. Do not add them to
the current backbone yet.

## WordNet version alignment

### Why it matters
Lexical resources must share identities without silently merging different senses.

### Current limitation
Numeric ConceptNet WordNet 3.1 mappings now resolve to 3.0 through exact shared
sense keys, preserving all targets. This does not resolve lexical/phrase-component
URIs or prove that cross-version synsets are semantically interchangeable.

### Future direction
Validate wider coverage against authoritative version mappings, retaining splits,
merges, unmatched cases, and their provenance instead of selecting one sense.

## ConceptNet mapping quality and ambiguity

### Why it matters
Explicit ConceptNet links are useful evidence but do not always identify a single
canonical WordNet synset suitable for reasoning or learned relation counts.

### Current limitation
The mapping CSV includes lexical/phrase-component targets (for example, book),
not only numeric synset URIs, and many concepts have multiple candidates. The
AtLocation export preserves every target without guessing a preferred sense.
Two invalid source IRIs require percent-encoding in RDF; original strings remain
available as provenance.

### Future direction
Validate target kinds and use authoritative lexical-to-synset and cross-version
links before canonical grounding. Define an explicit ambiguity policy for future
reasoning and observations; do not silently collapse candidates or count each as
an independently observed relation.

## Broader action coverage and sense selection

### Why it matters
New robot actions will require defensible links across WordNet, VerbNet, and
FrameNet, and may need a narrower interpretation than a lexical member provides.

### Current limitation
The canonical WordNet artifact is now the schema-driven object branch only.
Separate VerbNet and FrameNet demo resources cover bring/search, but do not
materialize their referenced verb synsets into that WordNet branch. Historical bring alignment evidence retains three declared WordNet
senses, including `bring.v.06` ("be accompanied by"); this is not a
curated physical-delivery-only sense set. Other WordNet action seeds and descendants are excluded; explicit VerbNet
WordNet links can therefore point outside the current WordNet artifact. SemLink2 targets VerbNet 3.3 while the inspected NLTK corpus is 2.1.

### Future direction
Expand action coverage through explicit versioned alignments. Define a documented
policy for selecting robot-relevant senses when member-level mappings are broader
than the supported action; retain evidence for each inclusion or exclusion.

## Role-level semantic alignment

### Why it matters
Connecting action participants across resources needs more than matching frame
and class names.

### Current limitation
The inspected SemLink2 table supplies class/member-to-frame links, not role-level
alignments or direct WordNet-sense-to-frame assertions. The JSON enrichment leaves
bring's four slots null and lists all Bringing FEs separately. SemLink's older
`other_resources/VN-FNRoleMapping.txt` links class 11.3 to Carry_goods, not Bringing;
those links cannot be transferred to Bringing.

### Future direction
Use an authoritative role mapping when available, or separately document curated
mappings and uncertainty. Do not infer role equivalence from similar labels.

## UsedFor commonsense

### Why it matters
Requests such as "bring me something to wipe the floor" require grounding a
purpose in suitable object types.

### Current limitation
Filtered UsedFor triples exist as source data but are not connected to canonical
WordNet types or a task interpretation/query layer.

### Future direction
Resolve the lexical identities and model purpose relations with provenance before
adding purpose-based object retrieval. Keep this separate from the current
WordNet export.

## Deferred: learned semantic memory from grounded occurrences

### Why it matters
Current WordNet, ConceptNet, VerbNet, FrameNet, and SemLink resources provide
**static / prior semantic knowledge**. Future learning should capture empirical
role combinations from actual robot experience, rather than treating those
priors as observations.

### Current limitation
KnowledgeInterface now supports in-memory location-count increments and explicit
saving to the concept JSON. Counts do not distinguish seeds from observations;
regeneration replaces saved updates. No grounded occurrence store or episode-based
learning mechanism exists yet.

### Future direction
Keep **episodic memory** for individual concrete observations/events. Derive
**learned semantic memory** from repeated grounded frame-role instantiations in
those episodes, separately from the static priors.

For each observed/executed bring-11.3 event, retain a new occurrence of the
schema-defined tuple `(agent, destination, source, theme)`, for example
`(robot, dining_table, kitchen, muffin)`. Preserve repeated occurrences instead
of immediately collapsing identical tuples:

```text
bring-11.3:
  occurrences:
    (robot, dining_table, kitchen, muffin)
    (robot, dining_table, kitchen, muffin)
    ...
```

Each distinct event contributes an occurrence; multiple reports of the same event
should not inflate frequency. Retain grounding and links to the contributing
episodes. Later aggregation can derive counts, histograms, and distributions to
answer where muffins are usually brought from/to, which objects commonly come
from kitchens, and which role combinations have occurred before.

Generalize to other frames such as search-35.2 using each frame's actual schema
roles, rather than fixing every event to bring's tuple. Keep learned occurrences
persistent across prior-resource rebuilds and preserve empirical counts when
combining learned distributions with prior knowledge. This is deferred design
only; no runtime learning or Search support is implemented.

## Planning ontology integration

### Why it matters
Planning should connect executable action models to shared semantic identities
without conflating lexical senses, action schemas, and world-state instances.

### Current limitation
The planning RDF prototype remains separate and has incomplete population,
name-based identity collisions, and schema/query inconsistencies. The current
WordNet work does not repair or integrate it.

### Future direction
Clarify those identities and repair the existing schema/population path before
adding explicit semantic links and PDDL/Unified Planning adapters.

## Graph visualization at larger scale

### Why it matters
Inspecting larger merged resources will require usable navigation without hiding
provenance, version boundaries, or important graph structure.

### Current limitation
The local viewer parses the full selected RDF into memory but renders only paged
one-hop neighborhoods. Its simple radial layout can overlap labels; it provides
no multi-hop layout, provenance comparison, or version-alignment visualization.
The semantic view projects AtLocation assertions into direct edges, but external
WordNet 3.1 targets without imported labels retain identifier-based captions.

### Future direction
Consider indexed/lazy graph queries and selectable multi-hop expansion if resource
size demands them. Preserve explicit resource identities and distinguish genuine
alignment edges from merely loading multiple graphs into the same view.

## Richer FrameNet relations and action-class inheritance

### Why it matters
Broader instruction understanding may need relations between frames and faithful
inheritance across VerbNet subclasses, beyond lexical member lookup.

### Current limitation
The demo keeps Bringing and Scrutiny with their FEs and lexical units, without
importing related frames. VerbNet exports only direct roles/frames of bring-11.3
and search-35.2; the bring member retains its declaring subclass as evidence,
without importing that subclass's semantics. No runtime frame selection exists.

### Future direction
Add selected frame relations and explicit subclass inheritance when a demo needs
them. Expand WordNet verb coverage through verified sense keys rather than silently
materializing every referenced target or broadening the current noun extraction.

## Schema-shaped type templates and future branches

### Why it matters
The same WordNet traversal should later build colour, material, shape, or other
branches from suitable schemas without coupling extraction to physical objects.

### Current limitation
CMOC's object schema describes observed instances as well as properties: numeric
area and measurement arrays do not accept null, but new type templates deliberately
use null for every unknown quality. Position/orientation do not necessarily belong
to type-level knowledge. Minimal RDF omits nulls and cannot recover those template
slots alone. Each build writes one branch, without branch merging.

### Future direction
Separate observation-validation schemas from type templates and define nullability
explicitly. Select appropriate schemas and WordNet roots for future semantic
branches, then design deduplicated merging that preserves multiple inheritance.
Do not implement colour/material/shape branches or guess measurements now.

## Schema-driven VerbNet class coverage

### Why it matters
Additional formal actions should be driven by their actual CMOC schemas, without
mixing unknown entity bindings with class-level linguistic knowledge.

### Current limitation
The canonical VerbNet resource now covers only bring-11.3. CMOC's schema describes
four nullable task-instance slots and forbids extra fields; role restrictions and
semantics therefore live outside the schema-valid frame in a small class wrapper.
Direct lexical members also live outside the task schema; subclass semantics and
search are not imported. TTL regeneration is deferred for this JSON-only resource.
Existing FrameNet links may reference absent formal class/member resources.

### Future direction
Add search-35.2 only when its corresponding schema is available, using the same
build_verbnet_resource API. Decide whether class definitions need their own schema
and how explicit subclass/member provenance should connect separately to FrameNet.
Do not fabricate entity bindings or role equivalences to bridge these layers.

## Minimal ConceptNet histogram projection

### Why it matters
The conceptual object resource should remain readable without construction-time
alignment evidence or diagnostic payloads mixed into its nodes.

### Current limitation
Location histograms now contain only synset-to-integer counts in a full backbone
copy. Ambiguous or partly unresolved mappings are skipped rather than fanned out;
there is no runtime observation API or persisted source-count split. The previous
ConceptNet TTL and its consumers are not regenerated by this JSON-only step.

### Future direction
Improve explicit disambiguation separately, without adding construction metadata
to object nodes. Migrate the RDF projection and consumers to this canonical shape
in a separate task. Define runtime count persistence before adding observations.

## Multiple FrameNet candidates for one action

### Why it matters
Member-specific alignments may associate one VerbNet class with several frames.

### Current limitation
The reusable action builder requires one uniquely matched FrameNet frame and
fails before writing when mappings are absent or ambiguous. Search is not added.

### Future direction
Define explicit selection or a reviewed multi-frame representation before extending
to ambiguous classes; do not silently select the first alignment.
