"""Seed object location histograms from explicit ConceptNet mappings only."""
import argparse
from collections import Counter, defaultdict
import copy
import csv
import json
from pathlib import Path
import re

from nltk.corpus import wordnet as wn, wordnet31 as wn31
from nltk.corpus.reader.wordnet import WordNetError

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'robonet_graph'


def resolve_mapping(uri):
    """Resolve numeric 3.1 IDs by exact shared sense keys, never by labels."""
    match = re.fullmatch(r'http://wordnet-rdf.princeton.edu/wn31/([1-5])(\d{8})-([nvars])', uri)
    if not match:
        return set(), 'phrase/non-synset mapping'
    if {'1':'n','2':'v','3':'a','4':'r','5':'s'}[match[1]] != match[3]:
        return set(), 'invalid mapping'
    try:
        source = wn31.synset_from_pos_and_offset(match[3], int(match[2]))
    except (WordNetError, ValueError):
        source = None
    if source is None:
        return set(), 'invalid mapping'
    targets = set()
    for lemma in source.lemmas():
        try:
            targets.add(wn.lemma_from_key(lemma.key()).synset().name())
        except (WordNetError, ValueError):
            pass
    return targets, None if targets else 'no shared 3.1/3.0 sense key'


def build_histograms(source, mappings_path, backbone_path, output_path):
    backbone = json.loads(Path(backbone_path).read_text())
    if backbone['wordnet_version'] != '3.0' or wn.get_version() != '3.0' or wn31.get_version() != '3.1':
        raise ValueError('Expected WordNet 3.1 mappings and a WordNet 3.0 backbone')
    document = copy.deepcopy(backbone)
    mappings = defaultdict(set)
    with Path(mappings_path).open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            mappings[row['conceptnet_concept']].add(row['wordnet_synset'])
    with Path(source).open(newline='', encoding='utf-8') as stream:
        rows = [(r['subject'], r['object']) for r in csv.DictReader(stream) if r['predicate'] == 'AtLocation']
    resolved, cache = {}, {}
    for concept in {c for row in rows for c in row}:
        candidates, issues = set(), set()
        for uri in mappings[concept]:
            if uri not in cache:
                cache[uri] = resolve_mapping(uri)
            ids, issue = cache[uri]
            candidates.update(ids)
            if issue:
                issues.add(issue)
        if not mappings[concept]:
            issues.add('missing mapping')
        if len(candidates) > 1:
            issues.add('ambiguous senses')
        # Even one resolved candidate is unsafe when another mapping is unresolved.
        resolved[concept] = (candidates, issues)

    applied = ambiguous = outside_locations = 0
    failures = Counter()
    for subject, location in rows:
        subjects, subject_issues = resolved[subject]
        locations, location_issues = resolved[location]
        issues = {f'subject: {v}' for v in subject_issues} | {f'location: {v}' for v in location_issues}
        if subjects and not subjects <= backbone['nodes'].keys():
            issues.add('subject: outside backbone')
        if locations and not locations <= backbone['nodes'].keys():
            outside_locations += 1  # Locations need a WordNet ID, not a backbone node.
        ambiguous += 'ambiguous senses' in subject_issues or 'ambiguous senses' in location_issues
        if issues:
            failures.update(issues)
            continue
        subject_id, location_id = next(iter(subjects)), next(iter(locations))
        qualities = document['nodes'][subject_id]['qualities']
        if qualities['location'] is None:
            qualities['location'] = {}
        histogram = qualities['location']
        histogram[location_id] = histogram.get(location_id, 0) + 1
        applied += 1

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'AtLocation rows: {len(rows)}\nApplied: {applied}\nSkipped: {len(rows) - applied}\nAmbiguous: {ambiguous}')
    print('Failure flags (rows; categories can overlap):')
    for reason, count in sorted(failures.items()):
        print(f'  {reason}: {count}')
    print(f'Location outside backbone (informational, not itself rejected): {outside_locations}')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DATA / 'filtered_conceptnet.csv')
    parser.add_argument('--mappings', type=Path, default=DATA / 'conceptnet_wordnet_mappings.csv')
    parser.add_argument('--backbone', type=Path, default=DATA / 'robokgwordnet.json')
    parser.add_argument('--output', type=Path, default=DATA / 'robokgconceptnet.json')
    args = parser.parse_args()
    build_histograms(args.source, args.mappings, args.backbone, args.output)


if __name__ == '__main__':
    main()
