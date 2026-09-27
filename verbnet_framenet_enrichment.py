"""Enrich a CMOC task frame using explicit SemLink links and FrameNet definitions."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from nltk.corpus import framenet as fn, verbnet as vn

ROOT = Path(__file__).resolve().parent


def enrich(document, alignments, role_mappings=()):
    """Role mappings, when supplied, are vncls elements from SemLink's role XML."""
    matches = [
        row for row in alignments
        if row['verbnet'] == document['id'] and row['member'] in document['members']
    ]
    names = {row['framenet'] for row in matches}
    if len(names) != 1:
        raise ValueError(f'Expected one explicitly aligned FrameNet frame, found {sorted(names)}')
    name = names.pop()
    frame = fn.frame_by_name(name)
    candidates = {}
    for mapping in role_mappings:
        # Never transfer a mapping from a different class or FrameNet frame.
        if (mapping.get('class') == vn.shortid(document['id'])
                and mapping.get('fnframe') == name):
            for role in mapping.findall('roles/role'):
                # CMOC uses lowercase VerbNet role names for its slot keys.
                candidates.setdefault(role.get('vnrole').lower(), set()).add(role.get('fnrole'))
    slots, represented = {}, set()
    for slot in document['frame']:
        targets = candidates.get(slot, set())
        slots[slot] = None
        if len(targets) == 1:
            target = next(iter(targets))
            if target in frame.FE:
                slots[slot] = {
                    'framenet_element': target,
                    'description': frame.FE[target].definition,
                }
                represented.add(target)
    return {
        'id': document['id'],
        'members': list(document['members']),
        'framenet_frame': name,
        # Drop only the final POS suffix, preserving multiword lexical forms.
        'evoking_words': sorted({lu.rsplit('.', 1)[0] for lu in frame.lexUnit}),
        'frame': slots,
        'additional_frame_elements': {
            key: {'description': fe.definition}
            for key, fe in sorted(frame.FE.items()) if key not in represented
        },
    }


def save_action(action, output_path):
    """Upsert one entry, migrating a single action without losing other entries."""
    output = Path(output_path)
    actions = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    if isinstance(actions.get('id'), str):
        actions = {actions['id']: actions}
    actions[action['id']] = action
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(actions, indent=2, sort_keys=True, ensure_ascii=False) + '\n',
                      encoding='utf-8')


def build_resource(input_path, output_path, semlink_path, role_mapping_path=None):
    document = json.loads(Path(input_path).read_text(encoding='utf-8'))
    evidence = json.loads(Path(semlink_path).read_text(encoding='utf-8'))
    # The bundled SemLink2 member/frame snapshot contains no role-level mappings.
    roles = ET.parse(role_mapping_path).getroot().findall('vncls') if role_mapping_path else ()
    result = enrich(document, evidence['alignments'], roles)
    output = Path(output_path)
    if output.resolve() == Path(input_path).resolve():
        raise ValueError('Output must not overwrite the VerbNet input')
    save_action(result, output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'robonet_graph/robokgverbnet.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'robonet_graph/robokgverbnet_framenet.json')
    parser.add_argument('--semlink', type=Path, default=ROOT / 'action_knowledge/semlink_demo.json')
    parser.add_argument('--role-mappings', type=Path,
                        help="Optional authoritative SemLink VN-FNRoleMapping XML file")
    args = parser.parse_args()
    result = build_resource(args.input, args.output, args.semlink, args.role_mappings)
    print(f"FrameNet frame: {result['framenet_frame']}")
    print('Unmapped slots:', ', '.join(k for k, v in result['frame'].items() if v is None))
    print(f'JSON: {args.output}')


if __name__ == '__main__':
    main()
