#!/usr/bin/env python3
"""Emit executable router-only row-half HGI records; physical ownership stays explicit.

The actual TP96 programme owns four expert scores per rank. This transform
partitions each pointwise SPSQRT record into two two-word records without
changing arithmetic, neighbouring words, or importing a fixture result.
The emitted native-rank numbers are candidate configuration values, not proof
that the selected TP192 collective has been configured or received its data.
"""
import argparse
import copy
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgi_sim import records as R


def halves(record):
    if record.unit != 'SU' or record.op != 'VOP' or set(record.desc) != {'A', 'O'}:
        raise ValueError('requires the actual router A-to-O SU.VOP record')
    # Opcode six is the source-defined sqrt(softplus) side operation. Other
    # reduction, gather and arithmetic profiles require their own transform.
    if not record.sut or record.sut.get('sfu') != 6 or record.sut.get('red', 0):
        raise ValueError('requires pointwise SPSQRT with no reduction')
    for md in record.desc.values():
        if (md.n != 4 or md.m != 1 or md.space != 'VM' or md.fmt != 'FP32'
                or (md.istride or 1) != 1 or md.indexed or md.ibcast
                or any(getattr(md, k) for k in ('dyn_sel','dyn_mul','n_sel','lstride','l1stride'))):
            raise ValueError('requires four contiguous static FP32 VM words')
    out = []
    for half in range(2):
        q = copy.deepcopy(record)
        q.desc = {k: dataclasses.replace(md, base=md.base + 2 * half, n=2)
                  for k, md in record.desc.items()}
        out.append(q)
    # Encode/decode the concrete source ABI, then independently check that the
    # exact original byte footprint was partitioned once with no overlap.
    for role in ('A', 'O'):
        intervals = []
        for q in out:
            decoded, end = R.decode_one(q.encode(), 0)
            if end != len(q.encode()) or decoded.sut != record.sut:
                raise ValueError('encoded shard changes the source arithmetic')
            md = decoded.desc[role]
            intervals.extend(range(md.base, md.base + md.n))
        md = record.desc[role]
        if intervals != list(range(md.base, md.base + 4)):
            raise ValueError('source footprint partition failed')
    return out


def emit(programme):
    if programme['tp'] != 96:
        raise ValueError('only the actual TP96 source programme is accepted')
    ranks = programme['ranks']
    if not isinstance(ranks, list) or sorted(x['rank'] for x in ranks) != list(range(96)):
        raise ValueError('the complete real 96-rank source programme is required')
    tags = programme['record_tags']
    rows = []
    for rank in sorted(ranks, key=lambda x: x['rank']):
        source = bytes.fromhex(rank['image_hex'])
        decoded = R.decode_program(source)
        matches = [i for i, tag in enumerate(tags) if tag == 'router_act']
        if len(matches) != 1 or len(decoded) != len(tags):
            raise ValueError('one actual router activation per source rank is required')
        k = matches[0]
        original = decoded[k]
        for half, shard in enumerate(halves(original)):
            logical_rank = rank['rank']
            expert_first = 4 * logical_rank + 2 * half
            md = shard.desc['O']
            rows.append(dict(layer_id=programme['layer'], logical_tp=96,
                logical_parent_rank=logical_rank, logical_record=k, half=half,
                candidate_producer_tp=192, candidate_rank=2 * logical_rank + half,
                logical_expert_range=[expert_first, expert_first + 2], word_count=2,
                source_record_sha256=hashlib.sha256(original.encode()).hexdigest(),
                shard_record_hex=shard.encode().hex(),
                shard_record_sha256=hashlib.sha256(shard.encode()).hexdigest(),
                source_VM_first_word=shard.desc['A'].base,
                destination_VM_first_word=md.base,
                destination_sector=md.base // 8,
                destination_word_mask=((1 << md.n) - 1) << (md.base % 8),
                physical_column=None, actual_rank_configuration=None,
                native_commit_edge=None, readable_edge=None, release_edge=None))
    return dict(schema='opentallas.router_row_half_commands.v1',
        status='EXECUTABLE_COMMANDS_ONLY', layer_id=programme['layer'],
        physical_ownership_qualified=False, complete_token_qualified=False,
        source_programme_sha256=hashlib.sha256(json.dumps(programme,sort_keys=True).encode()).hexdigest(),
        scope='Actual four-word TP96 source descriptors split into executable two-word pointwise records. TP192 rank/configuration, native all-rank production, transfer and retention remain required.',
        commands=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--programme',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=emit(json.loads(a.programme.read_text()));result['source_file_sha256']=hashlib.sha256(a.programme.read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(layer=result['layer_id'],commands=len(result['commands']),word_coverage=sum(x['word_count'] for x in result['commands']),physical_ownership_qualified=False)))

if __name__=='__main__':main()
