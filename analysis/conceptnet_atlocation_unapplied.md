# Why ConceptNet AtLocation assertions are unapplied

Diagnostic audit of the current filtered CSV, mapping CSV, object backbone, and
`conceptnet_to_robokgconceptnet.py`. All **261** AtLocation rows were examined.
Ordinary-noun lookups below use installed NLTK WordNet **3.0**, for diagnosis only.
No generator, alignment policy, or knowledge artifact was changed.

## Outcome and failure counts

**7 applied; 254 unapplied.** There are **122 distinct subject ConceptNet IDs in
unapplied rows**. This includes subjects whose mapping succeeds but whose location
is ambiguous; it does not mean all 122 subject mappings are broken. Furniture has
both an applied row and an unapplied row.

| Mutually exclusive outcome | Rows |
| --- | ---: |
| Both endpoints have phrase-component mappings, not synset mappings | 242 |
| Subject ambiguous; location unambiguous | 7 |
| Location ambiguous; subject unambiguous | 3 |
| Both endpoints ambiguous | 2 |
| Applied | 7 |
| **Total** | **261** |

Thus ambiguity blocks **12 distinct rows**: subject ambiguity appears in **9**,
location ambiguity in **5**, with **2** overlapping. These are competing explicit
synset candidates, not merely multiple labels for one synset.

| Additional check | Rows / targets |
| --- | ---: |
| Missing endpoint mappings | 0 rows |
| Numeric mapping cannot resolve through shared 3.1→3.0 sense keys | 0 rows |
| Resolved subject outside the object backbone | 0 rows |
| Invalid numeric identifier/POS mapping | 0 rows |
| Other rejection causes under the current policy | 0 rows |
| Location outside the object backbone | 4 rows, **all applied** |

A location needs a valid WordNet synset, not an exported subject node. The four
accepted out-of-backbone locations are sky (aircraft), body of water (boat and
ferry), and railway (bullet train). They are not alignment failures.

## What the failed subjects actually map to

Classification below covers the **122 subjects appearing in failed rows**. Counts
of targets are distinct `(ConceptNet subject, mapping target)` pairs; the target
URIs also happen to be globally distinct within this group.

| Mapping target kind | Distinct subjects | Target pairs |
| --- | ---: | ---: |
| Numeric WordNet synset URI | 10 | 22 |
| Phrase-component URI (`…-p#Component-N`) | 112 | 198 |
| Missing mapping | 0 | 0 |
| Other | 0 | 0 |
| **Total** | **122** | **220** |

Among the ten numerically mapped subjects, **seven subjects** are themselves
ambiguous (nine rows): accelerator, battery, box, brake, bus, column, elevator.
The other three—bulb, furniture, push_button—have valid unique subject mappings
and fail because of their locations. If “failed subject mappings” is interpreted
strictly, exclude those three: **119 subjects**, comprising **112 phrase-only
subjects / 198 targets** and **7 ambiguous numeric subjects / 19 targets**.

## Root cause

The main problem is **over-permissive mapping extraction**, not failed version
conversion. `utils/conceptnet_utils.py::_collect_wordnet_mappings()` accepts every
`ExternalURL` beginning `http://wordnet-rdf.princeton.edu/wn31/` and calls the target
a synset. That prefix also contains lexical phrase components. For example, cat
and bag link to different components of **“let the cat out of the bag”**, not to
the animal and container synsets. Such source links can be legitimate lexical
links; they are unsuitable as direct concept-to-synset grounding.

There is no evidence here of broken CSV parsing or syntactically malformed numeric
IDs. The original `sources/conceptnet/assertions.csv` is absent, so this audit
cannot establish whether useful numeric links were omitted upstream. The filtered
file's WordNet-linked-endpoint gate only checks link existence, not target kind;
it therefore does not guarantee meaningful synset coverage.

Across **all AtLocation endpoints**, all **49 distinct numeric targets** resolve
to exactly one WordNet 3.0 synset each through shared sense keys. The observed
numeric ambiguity originates in concepts with multiple explicit target URIs,
not splits or failures introduced by this version conversion.

The previous **19/261** application rate was exactly the numeric-endpoint subset.
Its candidate fan-out applied the twelve ambiguous rows too. The stricter policy
correctly reduces this to seven; relaxing version checks would not recover the
242 phrase-component rows.

## Representative unapplied assertions

All names below denote `/c/en/<name>` unless the row says “sense-qualified.”
Target examples abbreviate the common WordNet URI prefix. Noun suggestions are
**candidates, not accepted disambiguations**. Row counts are failed rows for that
subject, not just the displayed subject/location pair.

| Subject → example location | Failed rows | Existing target / obstacle | Ordinary noun lookup assessment |
| --- | ---: | --- | --- |
| book → bed | 4 | `don't+judge+a+book+by+the+cover-p#Component-4` (also another phrase) | book.n.01, book.n.02, book.n.11 are in scope; sense choice remains. |
| cat → bag | 14 | `let+the+cat+out+of+the+bag-p#Component-3` | cat.n.01 is plausible, but six exported noun candidates exist. |
| bag → bed | 1 | Same phrase, `#Component-7` | bag.n.01 is plausible; five exported noun candidates exist. |
| water → bottle | 14 | `fish+out+of+water-p#Component-4` and three other phrases | water.n.01 is outside scope. The sole exported candidate, water_system.n.02, is not a safe substitute. |
| milk → bottle | 1 | `don't+cry+over+spilt+milk-p#Component-5` | milk.n.01 is an ordinary substance sense; all four noun senses are outside scope. |
| fish → boat | 3 | `fish+out+of+water-p#Component-1` | fish.n.01 (animal) is in scope; fish.n.02 (food) is not. Another exported sense is pisces.n.02. |
| beans → can | 3 | `spill+the+beans-p#Component-3` | Edible bean.n.01 is outside scope; bean.n.02 (seed/fruit) and bean.n.03 (plant) are inside. |
| chips → bar | 1 | `cash+in+your+chips-p#Component-4` | Food senses french_fries.n.01/chip.n.04 are outside scope; exported chip senses include gambling counters/electronics. |
| cookie → jar | 1 | `caught+with+your+hand+in+the+cookie+jar-p#Component-7` | Food cookie.n.01 is outside scope; sole exported cookie.n.02 means a cook (person). |
| peas → can | 3 | `like+two+peas+in+a+pod-p#Component-3` | Food pea.n.01 is outside; pea.n.02 (seed/fruit) and pea.n.03 (plant) are inside. |
| pie → home | 2 | `eat+humble+pie-p#Component-3` | pie.n.01 exists, but neither noun sense is in the backbone. |
| handle → door | 1 | `get+a+handle+on-p#Component-3` and another phrase | Only handle.n.01 exists as a noun and is exported: good subject-recovery candidate. |
| moss → bridge | 4 | `a+rolling+stone+gathers+no+moss-p#Component-6` | Only moss.n.01 exists as a noun and is exported: good subject-recovery candidate. |
| accelerator → vehicle (sense-qualified) | 1 | Three numeric targets: accelerator.n.01/.02/.04 | Already converted successfully; genuine source-candidate ambiguity remains. |
| furniture → house (sense-qualified) | 1 | Subject resolves to furniture.n.01; location to house.n.01 and house.n.12 | Subject needs no repair; location needs disambiguation. |

**Mug/coffee mug:** no AtLocation row contains mug or coffee_mug on either endpoint.
There is therefore no unapplied mug assertion to recover from this input. Adding
such knowledge would require additional source assertions, not alignment repair.

## What ordinary noun lookup can and cannot recover

For the 122 distinct subjects in unapplied rows, ordinary
`wn.synsets(lexical_term, pos='n')` yields:

| Diagnostic candidate coverage | Subjects |
| --- | ---: |
| More than one candidate inside the backbone | 78 |
| Exactly one candidate inside the backbone | 24 |
| Noun senses exist, but all are outside the backbone | 17 |
| No noun senses | 3 |

The last three are **dirty, eat, yourself**, showing that the input is not purely
an object-type vocabulary. This lookup uses NLTK's normal morphology (e.g. plurals),
not a newly implemented runtime resolver.

“Exactly one in scope” is **not safe disambiguation**: water and cookie demonstrate
why filtering away the intended substance/food sense can leave the wrong sense.
Of the 24, only five have exactly one noun sense *before* filtering: handle, moss,
sword, furniture and push_button. The latter two are already explicitly grounded
and fail only on their location.

The strongest simple lookup repair candidates are therefore **handle.n.01,
moss.n.01, sword.n.01**: three currently phrase-only subjects spanning six rejected
rows. Their locations are also phrase-mapped, so repairing these subjects alone
would not make the six assertions applicable. Bucket/candle and book/cat/bag have
plausible ordinary senses, but require an explicit sense decision. Food/substance
cases often additionally require a deliberate backbone-scope decision. No noun
lookup performed in this audit changes a stored mapping or count.

## Smallest robust improvement

1. **Separate target kinds at extraction.** Only actual numeric synset links
   should satisfy the “WordNet-linked endpoint” condition. Keep phrase-component
   links out of that synset mapping; retaining them as lexical evidence is a
   separate concern. This fixes the misleading coverage claim, not coverage itself.
2. **Use a tiny reviewed mapping supplement for demo-critical endpoints.** Suggest
   ordinary noun candidates for both ends, starting with handle/moss/sword, then
   explicitly review desired book/cat/bag and location senses. Store any approved
   mapping separately from the conceptual knowledge resource. Never use first
   sense or “only candidate inside object.n.01” as an automatic rule.
3. **Keep the current all-candidates check and exact sense-key bridge.** Do not
   weaken version checks, fan out ambiguous rows, or broaden the noun backbone
   merely to improve the application count. Food/material scope and genuine
   multi-sense cases need separate, intentional decisions.

No code or mapping change is implemented by this report. The immediate bottleneck
is target-kind quality plus disambiguation, not the numeric 3.1→3.0 bridge.
