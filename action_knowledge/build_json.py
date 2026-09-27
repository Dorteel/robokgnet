"""Extract only two demo class scopes and explicitly aligned FrameNet frames."""
import json
from pathlib import Path
from nltk.corpus import verbnet as vn, framenet as fn, wordnet as wn
from nltk.corpus.reader.wordnet import WordNetError

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / 'robonet_graph'
CLASSES = ('bring-11.3', 'search-35.2')


def tree(element):
    """Lossless ordered XML structure, excluding formatting whitespace."""
    return {'tag': element.tag, 'attributes': dict(element.attrib),
            'text': (element.text or '').strip(), 'children': [tree(c) for c in element]}


def extract():
    evidence = json.loads((HERE / 'semlink_demo.json').read_text())
    classes = {}
    warnings = []
    for class_id in CLASSES:
        xml = vn.vnclass(class_id)
        members = []
        sources = [xml]
        # Keep only the bring member needed for the demo from its declaring subclass.
        if class_id == 'bring-11.3':
            sources.append(vn.vnclass('bring-11.3-1'))
        for source in sources:
            for member in source.findall('MEMBERS/MEMBER'):
                if source is not xml and member.get('name') != 'bring':
                    continue
                mappings = []
                for key in member.get('wn', '').split():
                    full = key if key.endswith('::') else key + '::'
                    if key.startswith('?'):
                        warnings.append(f"Uncertain WordNet key excluded: {key}")
                        continue
                    try:
                        mappings.append({'sense_key': full, 'synset_id': wn.lemma_from_key(full).synset().name()})
                    except (ValueError, WordNetError):
                        warnings.append(f"Unresolved WordNet key: {key}")
                members.append({'name': member.get('name'), 'declaring_class': source.get('ID'),
                                'attributes': dict(member.attrib), 'wordnet_mappings': mappings})
        classes[class_id] = {
            'members': sorted(members, key=lambda m: (m['name'], m['declaring_class'])),
            'roles': [tree(r) for r in xml.findall('THEMROLES/THEMROLE')],
            'frames': [{'description': dict(f.find('DESCRIPTION').attrib),
                        'examples': [e.text or '' for e in f.findall('EXAMPLES/EXAMPLE')],
                        'syntax': tree(f.find('SYNTAX')), 'semantics': tree(f.find('SEMANTICS'))}
                       for f in xml.findall('FRAMES/FRAME')],
        }
    frames = {}
    selected = sorted({r['framenet'] for r in evidence['demo_seeds']})
    for name in selected:
        frame = fn.frame_by_name(name)
        frames[name] = {
            'id': frame.ID, 'definition': frame.definition,
            'frame_elements': {n: {'id': fe.ID, 'definition': fe.definition, 'core_type': fe.coreType}
                               for n, fe in sorted(frame.FE.items())},
            'lexical_units': [{'id': lu.ID, 'name': n, 'pos': lu.POS,
                              'lexemes': [dict(lexeme) for lexeme in lu.lexemes]}
                             for n, lu in sorted(frame.lexUnit.items())],
        }
    alignments = []
    for record in evidence['alignments']:
        scope = 'bring-11.3' if record['verbnet'].startswith('bring-11.3') else record['verbnet']
        if not any(m['name'] == record['member'] and m['declaring_class'] == record['verbnet']
                   for m in classes[scope]['members']):
            raise ValueError(f'Alignment member absent from exact declaring class: {record}')
        alignments.append({**record, 'exported_class_scope': scope})
    common = {'semlink_evidence': evidence, 'scope': 'Demo bring/search only; member-specific alignments'}
    return ({'metadata': {**common, 'verbnet_version': '2.1', 'wordnet_version': wn.get_version(),
                          'warnings': sorted(warnings)}, 'classes': classes},
            {'metadata': {**common, 'framenet_version': '1.7'}, 'frames': frames, 'alignments': alignments})


def write_json(document, path):
    path.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')


def walk(node):
    yield node
    for child in node['children']:
        yield from walk(child)


def main():
    verbs, frames = extract()
    OUTPUT.mkdir(exist_ok=True)
    for name, document in [('verbnet', verbs), ('framenet', frames)]:
        path = OUTPUT / (name + '.json')
        write_json(document, path)
        print(f'{path.name} size: {path.stat().st_size:,} bytes')
    classes = verbs['classes'].values()
    print('VerbNet classes exported:', len(verbs['classes']))
    print('VerbNet members exported:', sum(len(c['members']) for c in classes))
    print('VerbNet roles exported:', sum(len(c['roles']) for c in classes))
    print('VerbNet semantic predicates exported:', sum(n['tag'] == 'PRED' for c in classes for f in c['frames'] for n in walk(f['semantics'])))
    print('FrameNet frames exported:', len(frames['frames']))
    print('Frame Elements exported:', sum(len(f['frame_elements']) for f in frames['frames'].values()))
    print('Lexical units exported:', sum(len(f['lexical_units']) for f in frames['frames'].values()))
    print('SemLink alignments exported:', len(frames['alignments']))


if __name__ == '__main__':
    main()
