from pathlib import Path
import csv
import logging
from collections.abc import Iterable
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "sources" / "conceptnet" / "assertions.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "sources" / "conceptnet" / "filtered_conceptnet.csv"
DEFAULT_MAPPING_OUTPUT = PROJECT_ROOT / "sources" / "conceptnet" / "conceptnet_wordnet_mappings.csv"
WORDNET_RDF_PREFIX = "http://wordnet-rdf.princeton.edu/wn31/"

LOG_PREFIX = "[conceptnet-kg]"
YELLOW = "\033[93m"
RESET = "\033[0m"


logger = logging.getLogger("conceptnet-kg")


def setup_logger() -> None:
    """Configure logger once, with a yellow ConceptNet prefix."""
    if logger.handlers:
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter(f"{YELLOW}{LOG_PREFIX} %(message)s{RESET}")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _relation_name(relation_uri: str) -> str:
    """Convert '/r/AtLocation' to 'AtLocation'."""
    return relation_uri.removeprefix("/r/")


def _is_language_concept(uri: str, language: str) -> bool:
    """Check whether a ConceptNet URI is a concept in the requested language."""
    return uri.startswith(f"/c/{language}/")

def _is_conceptnet_concept(uri: str) -> bool:
    """Return True for ConceptNet concept URIs, e.g. /c/en/dog."""
    return uri.startswith("/c/")

def _collect_wordnet_mappings(
    input_path: Path,
    language: str,
) -> dict[str, set[str]]:
    """Collect ConceptNet concept -> Princeton WordNet synset mappings."""
    mappings: dict[str, set[str]] = defaultdict(set)

    with input_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.reader(infile, delimiter="\t")

        for row in reader:
            if len(row) != 5:
                continue

            _, relation_uri, start_uri, end_uri, _ = row

            if (
                _relation_name(relation_uri) == "ExternalURL"
                and _is_language_concept(start_uri, language)
                and end_uri.startswith(WORDNET_RDF_PREFIX)
            ):
                mappings[start_uri].add(end_uri)

    return mappings


def _save_wordnet_mappings(
    mappings: dict[str, set[str]],
    output_path: Path = DEFAULT_MAPPING_OUTPUT,
) -> None:
    """Save ConceptNet -> WordNet mappings as a small CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["conceptnet_concept", "wordnet_synset"])

        for concept, synsets in sorted(mappings.items()):
            for synset in sorted(synsets):
                writer.writerow([concept, synset])


def filter_conceptnet_legacy(
    predicates: Iterable[str],
    language: str = "en",
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    progress_every: int = 1_000_000,
) -> int:
    """
    Stream-filter a huge ConceptNet TSV file.

    Keeps rows where:
    - predicate is in `predicates`
    - start concept has the requested language tag
    - end concept has the requested language tag, unless predicate is ExternalURL

    Returns the number of rows written.
    """
    setup_logger()

    predicates = set(predicates)
    rows_seen = 0
    rows_written = 0

    logger.info("starting ConceptNet filtering")
    logger.info(f"input: {input_path}")
    logger.info(f"output: {output_path}")
    logger.info(f"language: {language}")
    logger.info(f"predicates: {sorted(predicates)}")

    with (
        input_path.open("r", encoding="utf-8", newline="") as infile,
        output_path.open("w", encoding="utf-8", newline="") as outfile,
    ):
        reader = csv.reader(infile, delimiter="\t")
        writer = csv.writer(outfile)

        writer.writerow(["subject", "predicate", "object"])

        for row in reader:
            rows_seen += 1

            if rows_seen % progress_every == 0:
                logger.info(f"processed {rows_seen:,} rows, kept {rows_written:,}")

            if len(row) != 5:
                continue

            _, relation_uri, start_uri, end_uri, _ = row
            predicate = _relation_name(relation_uri)

            if predicate not in predicates:
                continue

            if not _is_language_concept(start_uri, language):
                continue

            if predicate == "ExternalURL":
                # Keep only links to Princeton WordNet RDF.
                if not end_uri.startswith(WORDNET_RDF_PREFIX):
                    continue
            else:
                # For normal ConceptNet triples, require both sides to be in the chosen language.
                if not _is_language_concept(end_uri, language):
                    continue

            writer.writerow([start_uri, predicate, end_uri])
            rows_written += 1

    logger.info(f"finished filtering: processed {rows_seen:,}, kept {rows_written:,}")
    return rows_written

def analyze_filtered_conceptnet(
    input_path: Path = DEFAULT_OUTPUT,
) -> dict[str, int]:
    """
    Analyze the filtered ConceptNet CSV.

    Returns:
    - distinct_concepts: number of unique ConceptNet concepts
    - concepts_with_wordnet_synsets: concepts linked to >= 1 WordNet synset
    - concepts_with_multiple_wordnet_synsets: concepts linked to > 1 WordNet synset
    """
    setup_logger()

    concepts: set[str] = set()
    concept_to_synsets: dict[str, set[str]] = defaultdict(set)

    logger.info("starting filtered ConceptNet analysis")
    logger.info(f"input: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)

        for row in reader:
            subject = row["subject"]
            predicate = row["predicate"]
            obj = row["object"]

            # Count normal ConceptNet concept nodes.
            if _is_conceptnet_concept(subject):
                concepts.add(subject)

            if _is_conceptnet_concept(obj):
                concepts.add(obj)

            # ExternalURL rows connect a ConceptNet concept to a WordNet synset.
            if (
                predicate == "ExternalURL"
                and obj.startswith(WORDNET_RDF_PREFIX)
                and _is_conceptnet_concept(subject)
            ):
                concept_to_synsets[subject].add(obj)

    result = {
        "distinct_concepts": len(concepts),
        "concepts_with_wordnet_synsets": sum(
            len(synsets) >= 1 for synsets in concept_to_synsets.values()
        ),
        "concepts_with_multiple_wordnet_synsets": sum(
            len(synsets) > 1 for synsets in concept_to_synsets.values()
        ),
    }

    logger.info(f"distinct concepts: {result['distinct_concepts']:,}")
    logger.info(
        f"concepts with WordNet synsets: "
        f"{result['concepts_with_wordnet_synsets']:,}"
    )
    logger.info(
        f"concepts with multiple WordNet synsets: "
        f"{result['concepts_with_multiple_wordnet_synsets']:,}"
    )
    logger.info("finished filtered ConceptNet analysis")

    return result

def _collect_wordnet_linked_concepts(
    input_path: Path,
    language: str,
) -> set[str]:
    """Collect concepts that have a Princeton WordNet ExternalURL link."""
    linked_concepts: set[str] = set()

    with input_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.reader(infile, delimiter="\t")

        for row in reader:
            if len(row) != 5:
                continue

            _, relation_uri, start_uri, end_uri, _ = row

            if (
                _relation_name(relation_uri) == "ExternalURL"
                and _is_language_concept(start_uri, language)
                and end_uri.startswith(WORDNET_RDF_PREFIX)
            ):
                linked_concepts.add(start_uri)

    return linked_concepts


def filter_conceptnet(
    predicates: Iterable[str],
    language: str = "en",
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    mapping_output_path: Path = DEFAULT_MAPPING_OUTPUT,
    progress_every: int = 1_000_000,
    require_wordnet_linked_endpoints: bool = False,
) -> int:
    """
    Stream-filter ConceptNet.

    When require_wordnet_linked_endpoints=True:
    - saves ConceptNet -> WordNet mappings separately
    - keeps only triples where subject and object both have WordNet mappings
    - skips ExternalURL rows in the filtered KG output
    """
    setup_logger()

    predicates = set(predicates)
    rows_seen = 0
    rows_written = 0
    wordnet_linked_concepts: set[str] = set()

    if require_wordnet_linked_endpoints:
        logger.info("collecting ConceptNet -> WordNet mappings")

        mappings = _collect_wordnet_mappings(
            input_path=input_path,
            language=language,
        )

        _save_wordnet_mappings(
            mappings=mappings,
            output_path=mapping_output_path,
        )

        wordnet_linked_concepts = set(mappings)

        logger.info(f"saved mappings to: {mapping_output_path}")
        logger.info(f"found {len(wordnet_linked_concepts):,} WordNet-linked concepts")

    logger.info("starting ConceptNet filtering")
    logger.info(f"input: {input_path}")
    logger.info(f"output: {output_path}")
    logger.info(f"language: {language}")
    logger.info(f"predicates: {sorted(predicates)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        input_path.open("r", encoding="utf-8", newline="") as infile,
        output_path.open("w", encoding="utf-8", newline="") as outfile,
    ):
        reader = csv.reader(infile, delimiter="\t")
        writer = csv.writer(outfile)

        writer.writerow(["subject", "predicate", "object"])

        for row in reader:
            rows_seen += 1

            if rows_seen % progress_every == 0:
                logger.info(f"processed {rows_seen:,} rows, kept {rows_written:,}")

            if len(row) != 5:
                continue

            _, relation_uri, start_uri, end_uri, _ = row
            predicate = _relation_name(relation_uri)

            # ExternalURL is used only for the mapping file now.
            if predicate == "ExternalURL":
                continue

            if predicate not in predicates:
                continue

            if not _is_language_concept(start_uri, language):
                continue

            if not _is_language_concept(end_uri, language):
                continue

            if require_wordnet_linked_endpoints:
                if start_uri not in wordnet_linked_concepts:
                    continue

                if end_uri not in wordnet_linked_concepts:
                    continue

            writer.writerow([start_uri, predicate, end_uri])
            rows_written += 1

    logger.info(f"finished filtering: processed {rows_seen:,}, kept {rows_written:,}")

    return rows_written