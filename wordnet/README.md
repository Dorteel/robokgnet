# Conceptual RoboKGWordNet

The canonical human-readable artifact is now `robonet_graph/robokgwordnet.json`.
The pipeline is:

```text
NLTK WordNet + JSON Schema → wordnet_to_robokgwordnet.py
  → robokgwordnet.json → wordnet/build_rdf.py → robokgwordnet.ttl
```

## Actual CMOC schema

`schemas/objects.json` is an unchanged copy of
`/home/kai/ros2_ws/src/cmoc/schemas/objects.json`. Its node fields are `id`, `type`,
and `qualities`. Accordingly the first WordNet lemma fills **type**, not a newly
invented name field. `id` is the canonical synset name. Synonyms and taxonomy add
`alternative_names` and `superclass`; the original schema permits additional
properties. Neither the source schema nor its property names are rewritten.

The generic `instantiate_schema()` helper recursively follows object properties
and local `$ref` definitions. Unknown leaves, including arrays, become null.
External/cyclic references and schema composition (`allOf`/`anyOf`/`oneOf`) fail
clearly instead of guessing a structure. This is deliberately a small template
instantiator, not a full JSON Schema implementation.

**Schema-shaped does not mean schema-valid observations.** CMOC's numeric and
array quality fields do not admit null. Per the requested unknown-quality policy,
the conceptual type templates still initialize them to null. No zero coordinates,
quaternions, sizes, or other measurements are invented. Validation of completed
observations and the distinction between type qualities and instance state are
deferred in `notes.md`.

Example generated node:

```json
{
  "id": "mug.n.04",
  "type": "mug",
  "alternative_names": [],
  "superclass": ["drinking_vessel.n.01"],
  "qualities": {
    "area": null,
    "color": null,
    "location": null,
    "material": null,
    "orientation": null,
    "shape": null,
    "size": null
  }
}
```

No synonym such as coffee_mug is invented if WordNet does not supply it.

## Taxonomy and identity

The document contains `root`, `wordnet_version`, a small schema fingerprint/name
record, and `nodes`, a dictionary keyed by canonical synset ID. Each node appears
once. `superclass` is always a **list** of direct parents inside this branch,
because WordNet is a DAG with multiple inheritance, not strictly a tree. The
root has an empty parent list. Out-of-scope ancestors are omitted, and children
can be found by reversing the parent references.

The demo uses `object.n.01` (alias `physical_object.n.01`), ordinary recursive
hyponyms only, with no named-instance traversal. It has **29,581 nodes**. The
noun scope is unchanged, but the old bring verb branch is no longer part of this
artifact. Any synset can be supplied as a root; no noun filter is hardcoded.
A later schema may use `name` instead of `type`; both are recognized for the
lexical name. The schema must supply `id` and one of those fields.

WordNet IDs remain versioned (currently 3.0). Existing ConceptNet 3.1 mappings
are not reinterpreted. VerbNet can reference WordNet resources absent from this
particular exported branch; those references do not expand this artifact.

## Minimal RDF

The converter reads **only the conceptual JSON**. Canonical identity lives in
the versioned resource URI. It emits `rdfs:label`, `skos:altLabel`, and
`rdfs:subClassOf`, without duplicate synsetId, partOfSpeech, or rdf:type triples.
Null properties have no RDF assertion. The JSON remains authoritative for unknown
property slots; an RDF-only round trip cannot recover which null slots existed.
Non-null nested properties can be encoded through the small property namespace;
no runtime observation or learning logic is introduced.

The object artifact has **84,063 triples**. JSON is **11,815,636 bytes**; Turtle
is **4,473,718 bytes**. Output is deterministically sorted.

## Regenerate

From the repository root, after the existing NLTK/rdflib setup:

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B wordnet_to_robokgwordnet.py --schema schemas/objects.json --root object.n.01 --output robonet_graph/robokgwordnet.json
.venv/bin/python -B wordnet/build_rdf.py
```

The generic Python API is
`build_wordnet_branch(schema_path, root_synset, output_path)`.
The RDF converter accepts `--input` and `--output` for separate future branches.
Each build writes one branch; merging/appending multiple branches is deferred.
Do not manually edit generated Turtle.

```bash
NLTK_DATA="$PWD/.venv/nltk_data" .venv/bin/python -B -m unittest discover -s tests -p 'test_wordnet.py' -v
```

Tests use tiny subtrees and an alternate nested schema, checking identities,
WordNet-derived synonyms, exact parents, nulls, deterministic JSON/Turtle and RDF
reload. They do not rebuild the entire object branch.

`wordnet/build_wordnet.py` is a retired entry point that exits with migration
instructions. The old `wordnet.json` was removed to avoid two apparent canonical
sources. `bring_alignment.json` remains historical alignment evidence, not input
to this object-branch generator. Other lexical resources are not regenerated.

The lexical data is derived from Princeton WordNet 3.0; its terms remain in
[LICENSE.wordnet](LICENSE.wordnet).
