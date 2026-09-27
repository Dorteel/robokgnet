"""Build a schema-shaped conceptual WordNet branch, without RDF details."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from nltk.corpus import wordnet as wn

ROOT = Path(__file__).resolve().parent


def instantiate_schema(schema, document=None, references=()):
    """Preserve object nesting; initialize every unknown leaf (including arrays) to null.

    This instantiates a template, not a JSON Schema validator. No measurements or
    schema defaults are invented. Local references are supported; ambiguous
    composition is rejected rather than silently choosing a structure.
    """
    document = schema if document is None else document
    if '$ref' in schema:
        ref = schema['$ref']
        if not ref.startswith('#/') or ref in references:
            raise ValueError(f'Unsupported external or cyclic schema reference: {ref}')
        target = document
        for part in ref[2:].split('/'):
            target = target[part.replace('~1', '/').replace('~0', '~')]
        return instantiate_schema(target, document, references + (ref,))
    if any(key in schema for key in ('allOf', 'anyOf', 'oneOf')):
        raise ValueError('Schema composition is not supported; provide an explicit object template')
    if 'properties' in schema or schema.get('type') == 'object':
        return {key: instantiate_schema(value, document, references)
                for key, value in sorted(schema.get('properties', {}).items())}
    return None


def build_wordnet_branch(schema_path, root_synset, output_path):
    schema_path, output_path = Path(schema_path), Path(output_path)
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    template = instantiate_schema(schema)
    if not isinstance(template, dict):
        raise ValueError('The node schema must describe an object')
    # CMOC calls the type's human-readable name "type". Other schemas can use name.
    name_field = 'name' if 'name' in template else 'type' if 'type' in template else None
    if name_field is None or 'id' not in template:
        raise ValueError('Node schema must supply id and either name or type')
    root = wn.synset(root_synset)  # Accept canonical names and WordNet aliases.
    selected, pending = {}, [root]
    while pending:
        synset = pending.pop()
        if synset.name() in selected:
            continue
        selected[synset.name()] = synset
        pending.extend(synset.hyponyms())
    nodes = {}
    for name, synset in sorted(selected.items()):
        node = copy.deepcopy(template)
        lemmas = synset.lemma_names()
        node.update({'id': name, name_field: lemmas[0],
                     'alternative_names': sorted(set(lemmas[1:]) - {lemmas[0]}),
                     'superclass': sorted(p.name() for p in synset.hypernyms() if p.name() in selected)})
        nodes[name] = node
    document = {'root': root.name(), 'wordnet_version': wn.get_version(),
                'schema': {'file': schema_path.name, 'sha256': hashlib.sha256(schema_path.read_bytes()).hexdigest(),
                           'name_field': name_field}, 'nodes': nodes}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--root', required=True, help='WordNet synset name, e.g. object.n.01')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    document = build_wordnet_branch(args.schema, args.root, args.output)
    print(f"Root: {document['root']}\nNodes: {len(document['nodes']):,}\nJSON: {args.output} ({args.output.stat().st_size:,} bytes)")


if __name__ == '__main__':
    main()
