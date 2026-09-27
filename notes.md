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
NLTK supplies WordNet 3.0; the existing ConceptNet mapping CSV targets Princeton
WordNet 3.1. The AtLocation JSON/RDF now preserves these 3.1 targets without
joining the 3.0 backbone. No verified conversion exists; versioned IRIs alone
do not solve cross-version alignment.

### Future direction
Introduce an explicit, provenance-backed 3.0 ↔ 3.1 mapping, preserving ambiguous
and unmatched cases rather than equating identifiers or labels directly.

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
alignments or direct WordNet-sense-to-frame assertions.

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

## Learned semantic-memory weighting

### Why it matters
Object-location knowledge should improve from successful robot observations.

### Current limitation
AtLocation now has stable, provenance-bearing assertion resources with explicit
WordNet 3.1 mapping candidates. There are no runtime counts, learned weights,
or observation ingestion; ambiguous mappings are unresolved.

### Future direction
Extend the assertion model with prior_count, observation_count, and weight.
Keep seed priors separate from observation counts, persist evidence, and derive
ranked weighted relations per object type. Define observation identity and
normalization before integrating ORKA updates.

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
