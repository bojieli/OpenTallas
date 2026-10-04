#!/usr/bin/env python3
"""Explicit token-source authorization, separate from the decode position.

An initial token fixture may select a released prompt token at a target decode
position. This supplies neither a real 1M prompt history nor intermediate H.
The native reader still requests checkpoint bytes and publishes through VM ACK.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = 'opentallas.dsrom.S81.embedding-token-source.v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(value, low, high, name):
    if type(value) is not int or not low <= value < high:
        raise ValueError(name)
    return value


def select(prompt, token_index, position, identity):
    prompt = Path(prompt).resolve(strict=True)
    source = json.loads(prompt.read_text())
    ids = source['token_ids']
    integer(token_index, 0, len(ids), 'source prompt token index')
    token = integer(ids[token_index], 0, 129280, 'released token ID')
    integer(position, 0, 1 << 20, 'selected decode position')
    integer(identity, 0, 1 << 47, 'source identity')
    return dict(schema=SCHEMA, source_kind='initial_prompt_token_fixture',
                identity=identity, token=token, position=position,
                context=position + 1, prompt=str(prompt),
                prompt_sha256=digest(prompt), token_index=token_index,
                real_target_prompt_history=False, expected_intermediates=False,
                entry='native_embedding_ROM_request_then_same_VM_scalar_ACK')


class EmbeddingAuthorization:
    def __init__(self, *, prompt=None, binding=None):
        if binding is not None:
            self.binding_path = Path(binding).resolve(strict=True)
            record = json.loads(self.binding_path.read_text())
            if record.get('schema') != SCHEMA:
                raise ValueError('explicit S81 embedding source schema required')
            # Re-read the actual prompt, including its hash and selected token.
            expected = select(record['prompt'], record['token_index'],
                              record['position'], record['identity'])
            if record != expected:
                raise ValueError('embedding source binding changed or mislabelled')
            self.record = record
            self.ids = None
        else:
            if prompt is None:
                raise ValueError('actual prompt or explicit token source required')
            self.binding_path = None
            self.record = None
            self.ids = json.loads(Path(prompt).read_text())['token_ids']

    def authorize(self, identity, token, position):
        integer(identity, 0, 1 << 47, 'source identity')
        integer(token, 0, 129280, 'source token')
        integer(position, 0, 1 << 20, 'source decode position')
        if self.record is not None:
            if (identity, token, position) != tuple(
                    self.record[k] for k in ('identity', 'token', 'position')):
                raise ValueError('request differs from selected target token source')
        elif position >= len(self.ids) or self.ids[position] != token:
            raise ValueError('legacy prompt index binding; target source not authorized')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', type=Path, required=True)
    parser.add_argument('--token-index', type=int, required=True)
    parser.add_argument('--position', type=int, required=True)
    parser.add_argument('--identity', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    record = select(args.prompt, args.token_index, args.position, args.identity)
    # Never overwrite an existing source choice.
    with args.out.open('x') as output:
        json.dump(record, output, indent=2, sort_keys=True)
        output.write('\n')
    print(json.dumps(record, sort_keys=True))


if __name__ == '__main__':
    main()
