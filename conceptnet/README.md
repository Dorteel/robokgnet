# ConceptNet AtLocation backbone

Pipeline:

```text
robonet_graph/filtered_conceptnet.csv + conceptnet_wordnet_mappings.csv
  → align_conceptnet_wordnet.py
  → robonet_graph/conceptnet_atlocation_aligned.json
  → build_rdf.py
  → robonet_graph/robokgconceptnet.ttl
```

The aligner uses Python's standard library. The RDF converter needs `rdflib`
(already included in `wordnet/requirements.txt`). No NLTK corpus, network access,
label lookup, or WordNet 3.0 conversion is involved.

## Alignment and limitations

Keep every AtLocation CSV row, including duplicate rows or unmapped endpoints.
Ignore IsA and UsedFor during export without modifying either source CSV.
Each endpoint retains its exact `/c/...` identifier and a sorted, deduplicated
list of **all** explicit mapping targets under `subject_wordnet_mappings` or
`object_wordnet_mappings`. Empty lists mean unmapped; lists with multiple values
remain ambiguous. No preferred sense is selected and no Cartesian product of
candidate WordNet relations is asserted.

The mapping column is called `wordnet_synset` in the input, but its targets are
not all numeric synsets. For example, `/c/en/book` links to two phrase-component
resources (`don't+judge+a+book+by+the+cover-p#Component-4` and
`take+a+leaf+out+of+someone's+book-p#Component-7`). Preserve these links as source
evidence, **not verified synset equivalences**. Obtaining a verified canonical
synset for every endpoint is deferred; no `book.n.01` guess is substituted.

Targets retain the exact Princeton WordNet **3.1** identifiers. The existing
WordNet backbone uses **3.0**, and no verified conversion exists in the inspected
repository. This export does not join them. Metadata records both versions,
input filenames and SHA-256 fingerprints, and the absence of conversion.
See [notes.md](../notes.md) for deferred version alignment and mapping quality.

## Minimal RDF model

ConceptNet resources use `http://api.conceptnet.io` followed by their exact
`/c/...` path. Original strings are also retained as `kg:conceptId` literals.
The provisional project vocabulary is
`https://w3id.org/robokgnet/conceptnet/schema#` (an identifier convention, not a
claim that the URLs are registered or served).

```text
assertion rdf:type kg:AtLocationAssertion
assertion rdf:subject ConceptNet-subject
assertion rdf:predicate <http://api.conceptnet.io/r/AtLocation>
assertion rdf:object ConceptNet-object
ConceptNet-concept kg:mapsToWordNet <original-WordNet-3.1-target>
ConceptNet-concept kg:mappingStatus "single" / "ambiguous" / "unmapped"
```

`AtLocationAssertion` is a subclass of `rdf:Statement`. Assertion resources use
SHA-256 of the source triple plus a duplicate occurrence number, making IDs
stable under row reordering and keeping duplicates distinct. `dcterms:source`
links assertions to the source CSV fingerprint and concept mappings to the
mapping CSV fingerprint; each fingerprint resource has the source filename.
There is no `owl:sameAs`, merged WordNet class, WordNet taxonomy copy, or direct
AtLocation edge between candidate WordNet resources.

Two source targets contain illegal IRI backticks. The RDF converter percent-
encodes those characters (`%60`) and stores the exact original string as
`kg:sourceMappingIdentifier` on the target. JSON retains the original unchanged.
URI escaping is serialization hygiene, not a sense or version conversion.

JSON keys, candidate lists, assertions, and Turtle triples are sorted for stable
output. The converter consumes only the aligned JSON. Assertion resources can
later carry prior_count, observation_count, and weight; none are fabricated now.

## Regenerate and test

Run from the repository root:

```bash
.venv/bin/python -B conceptnet/align_conceptnet_wordnet.py
.venv/bin/python -B conceptnet/build_rdf.py
.venv/bin/python -B -m unittest discover -s tests -p 'test_conceptnet.py' -v
```

The aligner accepts `--source`, `--mappings`, and `--output`; the converter accepts
`--input` and `--output`. Defaults resolve relative to the repository. Tests check
source row multiplicity, exact mappings on both ends, ambiguity, unmapped cases,
no guessed mappings, deterministic artifacts, RDF reload, and source-IRI escaping.

## Current statistics

Endpoint statistics count **distinct ConceptNet concepts per role**, not rows or
candidate links. A concept appearing in both roles counts in each role.

| Metric | Count |
| --- | ---: |
| AtLocation source/exported assertions | 261 |
| Aligned subject concepts | 127 |
| Aligned object concepts | 99 |
| Ambiguous subject mappings | 57 |
| Ambiguous object mappings | 36 |
| Unmapped subjects | 0 |
| Unmapped objects | 0 |
| JSON size | 166,903 bytes |
| TTL triples | 2,410 |
| TTL size | 302,999 bytes |

All 261 current rows are retained. Here "aligned" means an explicit source
mapping exists, not that its target is disambiguated or verified as a synset.
