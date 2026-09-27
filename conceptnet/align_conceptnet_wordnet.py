"""Align AtLocation endpoints using explicit WordNet 3.1 CSV mappings only."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

GRAPH_DIR = Path(__file__).resolve().parents[1] / 'robonet_graph'
WORDNET_PREFIX = 'http://wordnet-rdf.princeton.edu/wn31/'


def align(source, mappings_path):
    mappings = defaultdict(set)
    with mappings_path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            target = row['wordnet_synset']
            if not target.startswith(WORDNET_PREFIX):
                raise ValueError(f'Expected explicit WordNet 3.1 resource: {target!r}')
            mappings[row['conceptnet_concept']].add(target)
    with source.open(encoding='utf-8', newline='') as stream:
        triples = sorted((r['subject'], r['predicate'], r['object'])
                         for r in csv.DictReader(stream) if r['predicate'] == 'AtLocation')
    assertions = []
    occurrences = Counter()
    for subject, predicate, obj in triples:
        triple = (subject, predicate, obj)
        occurrences[triple] += 1
        digest = hashlib.sha256(json.dumps(triple, ensure_ascii=False).encode()).hexdigest()
        assertions.append({
            'id': f'atlocation-{digest}-{occurrences[triple]}',
            'subject': subject,
            'subject_wordnet_mappings': sorted(mappings[subject]),
            'predicate': predicate,
            'object': obj,
            'object_wordnet_mappings': sorted(mappings[obj]),
        })
    statistics = {'atlocation_source_triples': len(triples)}
    for role in ('subject', 'object'):
        concepts = {a[role] for a in assertions}
        statistics[f'aligned_{role}_concepts'] = sum(bool(mappings[c]) for c in concepts)
        statistics[f'ambiguous_{role}_mappings'] = sum(len(mappings[c]) > 1 for c in concepts)
        statistics[f'unmapped_{role}s'] = sorted(c for c in concepts if not mappings[c])
    return {
        'metadata': {
            'predicate': 'AtLocation',
            'source': source.name,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'mapping_source': mappings_path.name,
            'mapping_source_sha256': hashlib.sha256(mappings_path.read_bytes()).hexdigest(),
            'wordnet_mapping_version': '3.1',
            'robokgnet_wordnet_version': '3.0',
            'wordnet_3_0_conversion': 'Not performed: no verified cross-version mapping available',
            'mapping_semantics': 'Exact source links, including lexical/phrase targets; not verified synset equivalences',
            'statistics_unit': 'Distinct concepts per endpoint role; source triples count CSV rows',
            'statistics': statistics,
        },
        'assertions': assertions,
    }


def write_aligned(source, mappings, output):
    document = align(source, mappings)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=GRAPH_DIR / 'filtered_conceptnet.csv')
    parser.add_argument('--mappings', type=Path, default=GRAPH_DIR / 'conceptnet_wordnet_mappings.csv')
    parser.add_argument('--output', type=Path, default=GRAPH_DIR / 'conceptnet_atlocation_aligned.json')
    args = parser.parse_args()
    stats = write_aligned(args.source, args.mappings, args.output)['metadata']['statistics']
    print(f"AtLocation source triples: {stats['atlocation_source_triples']}")
    for role in ('subject', 'object'):
        print(f"Aligned {role} concepts: {stats[f'aligned_{role}_concepts']}")
        print(f"Ambiguous {role} mappings: {stats[f'ambiguous_{role}_mappings']}")
        print(f"Unmapped {role}s: {len(stats[f'unmapped_{role}s'])}")
    print(f'JSON size: {args.output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
