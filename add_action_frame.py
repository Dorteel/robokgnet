"""Build and upsert one schema-driven action using explicit semantic alignment."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from verbnet_to_robokgverbnet import build_verbnet_resource
from verbnet_framenet_enrichment import enrich, save_action

ROOT = Path(__file__).resolve().parent


def add_action_frame(verbnet_class, schema_path,
                     output_path=ROOT / 'robonet_graph/robokgverbnet_framenet.json',
                     semlink_path=ROOT / 'action_knowledge/semlink_demo.json',
                     role_mapping_path=None):
    action = build_verbnet_resource(schema_path, verbnet_class)
    evidence = json.loads(Path(semlink_path).read_text(encoding='utf-8'))
    roles = ET.parse(role_mapping_path).getroot().findall('vncls') if role_mapping_path else ()
    enriched = enrich(action, evidence['alignments'], roles)
    save_action(enriched, output_path)
    return enriched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verbnet-class', required=True)
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'robonet_graph/robokgverbnet_framenet.json')
    parser.add_argument('--semlink', type=Path, default=ROOT / 'action_knowledge/semlink_demo.json')
    parser.add_argument('--role-mappings', type=Path)
    args = parser.parse_args()
    add_action_frame(args.verbnet_class, args.schema, args.output, args.semlink, args.role_mappings)
    print(f'Updated {args.verbnet_class}: {args.output}')


if __name__ == '__main__':
    main()
