"""Seed object location histograms from explicit ConceptNet mappings only."""
import argparse
from collections import defaultdict
import copy
import csv
import json
from pathlib import Path
import re
from urllib.parse import unquote

from nltk.corpus import wordnet as wn, wordnet31 as wn31
from nltk.corpus.reader.wordnet import WordNetError

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'robonet_graph'


def resolve_mapping(uri):
    """Bridge a numeric WN3.1 URI to WN3.0 by exact shared lemma sense keys.

    Unlike NLTK's map_to_one, retain every target, not a majority winner.
    Phrase/component resources are unresolved, never guessed from English.
    """
    match = re.fullmatch(r'http://wordnet-rdf.princeton.edu/wn31/([1-5])(\d{8})-([nvars])', uri)
    if not match:
        return {'wordnet_ids': [], 'sense_keys': [], 'status': 'not_numeric_synset'}
    if {'1':'n','2':'v','3':'a','4':'r','5':'s'}[match[1]] != match[3]:
        return {'wordnet_ids': [], 'sense_keys': [], 'status': 'invalid_pos'}
    try:
        source = wn31.synset_from_pos_and_offset(match[3], int(match[2]))
    except (WordNetError, ValueError):
        source = None
    ids, keys = set(), []
    if source is not None:
        for lemma in source.lemmas():
            try:
                target = wn.lemma_from_key(lemma.key()).synset()
            except (WordNetError, ValueError):
                continue
            ids.add(target.name())
            keys.append({'sense_key': lemma.key(), 'wordnet_id': target.name()})
    return {'wordnet_ids': sorted(ids), 'sense_keys': sorted(keys, key=lambda r: r['sense_key']),
            'status': 'resolved' if ids else 'no_shared_sense_key'}


def build_histograms(source, mappings_path, backbone_path, output_path):
    backbone = json.loads(Path(backbone_path).read_text())
    if backbone['wordnet_version'] != '3.0' or wn.get_version() != '3.0' or wn31.get_version() != '3.1':
        raise ValueError('This explicit sense-key bridge requires WordNet 3.1 source and 3.0 backbone')
    mappings = defaultdict(set)
    with Path(mappings_path).open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            mappings[row['conceptnet_concept']].add(row['wordnet_synset'])
    with Path(source).open(newline='', encoding='utf-8') as stream:
        assertions = sorted((r['subject'], r['object']) for r in csv.DictReader(stream) if r['predicate'] == 'AtLocation')
    # Resolve only endpoint resources used by AtLocation, retaining reusable evidence.
    concepts = {c for row in assertions for c in row}
    evidence = {uri: resolve_mapping(uri) for uri in sorted({u for c in concepts for u in mappings[c]})}
    candidates = {c: sorted({name for uri in mappings[c] for name in evidence[uri]['wordnet_ids']}) for c in concepts}
    nodes, subjects, skipped = {}, defaultdict(dict), []
    accepted = 0
    for subject, obj in assertions:
        targets = [name for name in candidates[subject] if name in backbone['nodes']]
        if not targets:
            skipped.append({'subject': subject, 'object': obj, 'wordnet31_ids': sorted(mappings[subject]),
                            'wordnet_ids': candidates[subject],
                            'reason': 'outside_backbone' if candidates[subject] else 'unresolved_subject'})
            continue
        accepted += 1
        # A display key only: never used to resolve identity. Merge equal names
        # while retaining every source URI and every location grounding candidate.
        parts = obj.split('/')
        location = unquote(parts[3]) if len(parts) > 3 else obj
        for name in targets:
            if name not in nodes:
                nodes[name] = copy.deepcopy(backbone['nodes'][name])
                # A seed build starts afresh; it is not a runtime observation update.
                nodes[name]['qualities']['location'] = {}
            subjects[name][subject] = {'conceptnet_id': subject, 'wordnet31_ids': sorted(mappings[subject]),
                                       'wordnet_ids': candidates[subject]}
            histogram = nodes[name]['qualities']['location']
            entry = histogram.setdefault(location, {'seed_count': 0, 'observation_count': 0, 'count': 0,
                                                    'conceptnet_ids': [], 'wordnet31_ids': [], 'wordnet_ids': []})
            entry['seed_count'] += 1
            entry['count'] = entry['seed_count'] + entry['observation_count']
            entry['conceptnet_ids'] = sorted(set(entry['conceptnet_ids']) | {obj})
            entry['wordnet31_ids'] = sorted(set(entry['wordnet31_ids']) | mappings[obj])
            entry['wordnet_ids'] = sorted(set(entry['wordnet_ids']) | set(candidates[obj]))
    for name, node in nodes.items():
        node['conceptnet_subjects'] = [subjects[name][key] for key in sorted(subjects[name])]
    document = {
        'metadata': {'predicate': 'AtLocation', 'wordnet_version': '3.0', 'mapping_source_version': '3.1',
                     'alignment': 'Exact shared WordNet lemma sense keys; all candidates retained',
                     'count_policy': 'One seed per CSV row per distinct in-backbone subject candidate; alternative hypotheses, not independent observations',
                     'location_key_policy': 'ConceptNet lexical segment; collisions merge with all IDs preserved',
                     'source_assertions': len(assertions), 'applied_assertions': accepted,
                     'skipped_assertions': len(skipped), 'enriched_concepts': len(nodes)},
        'nodes': nodes, 'alignment_evidence': evidence, 'unapplied_assertions': skipped,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DATA / 'filtered_conceptnet.csv')
    parser.add_argument('--mappings', type=Path, default=DATA / 'conceptnet_wordnet_mappings.csv')
    parser.add_argument('--backbone', type=Path, default=DATA / 'robokgwordnet.json')
    parser.add_argument('--output', type=Path, default=DATA / 'robokgconceptnet.json')
    args = parser.parse_args()
    document = build_histograms(args.source, args.mappings, args.backbone, args.output)
    for key, value in document['metadata'].items():
        if isinstance(value, int):
            print(f'{key}: {value}')
    print(f'JSON size: {args.output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
