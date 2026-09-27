"""Build a CMOC task frame with its VerbNet class ID and direct members."""
import argparse
import json
from pathlib import Path
from nltk.corpus import verbnet as vn

ROOT = Path(__file__).resolve().parent


def build_verbnet_resource(schema_path, verbnet_class, output_path=None):
    """Build one exact class; optionally write its minimal JSON entry."""
    schema = json.loads(Path(schema_path).read_text())
    xml = vn.vnclass(verbnet_class)
    class_id = xml.get('ID')
    if schema.get('verbnet_class') != class_id:
        raise ValueError('Schema verbnet_class does not match the requested class')
    if schema.get('type') != 'object':
        raise ValueError('Expected an object task-frame schema')
    template = {}
    for field, definition in schema['properties'].items():
        types = definition.get('type', [])
        if types == 'null' or (isinstance(types, list) and 'null' in types):
            template[field] = None
        elif 'default' in definition:
            template[field] = definition['default']
        else:
            raise ValueError(f'Unknown slot {field!r} has no permitted null or default')
    document = {'id': class_id,
                'members': sorted(m.get('name') for m in xml.findall('MEMBERS/MEMBER')),
                'frame': template}
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', type=Path, default=ROOT / 'schemas/bring-11.3.json')
    parser.add_argument('--class', dest='class_id', default='bring-11.3')
    parser.add_argument('--output', type=Path, default=ROOT / 'robonet_graph/robokgverbnet.json')
    args = parser.parse_args()
    build_verbnet_resource(args.schema, args.class_id, args.output)
    print(f"JSON: {args.output}")


if __name__ == '__main__':
    main()
