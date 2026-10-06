#!/usr/bin/env python3
"""Retained L20 rank operands and actual native top512 plane publication.

No golden arithmetic runs here. Saved scores are comparator-only. Publication
uses only accepted native outputs, retaining striped literal IDs. The existing
hardware order adapter, not this emitter, provides final global-ID ordering.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

TP, CONTEXT, PER_RANK = 96, 1048576, 512
PHASE = 'L20.op14.index_scores.pre_candidate_mask.local_top512'
STORE_SHA = 'f55ba8392f2474fbb8a460cc867829345a923773f563c8b52340043848b55790'
TB = 'rtl/test/hbm_accel/tb_hbm_index_tp96_rank.sv'
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def score_key(v):
    if type(v) is not int or not 0 <= v <= 65535 or (v & 0x7f80 == 0x7f80 and v & 127):
        raise ValueError('non-NaN BF16 score required')
    return 0x8000 if v & 0x7fff == 0 else (~v & 65535) if v & 0x8000 else v | 0x8000


def owned_ids(rank):
    if type(rank) is not int or not 0 <= rank < TP:
        raise ValueError('TP96 rank required')
    return [8 * (rank + TP * b) + l
            for b in range((131072 + 95 - rank) // TP) for l in range(8)]


def write_json(path, record):
    with Path(path).open('x') as f:
        json.dump(record, f, indent=2)
        f.write('\n')


def prepare(store, gold, ranks, out):
    import numpy as np
    from rtl_hdc_v41x_idx_campaign import to_codes
    if sha(store) != STORE_SHA:
        raise ValueError('retained full L20 entering-key source pin differs')
    keys = np.load(store, mmap_mode='r')
    z = np.load(gold)
    if keys.shape != (CONTEXT-1, 128) or keys.dtype != np.float32:
        raise ValueError('actual entering L20 store shape/type required')
    if z['ik20'].shape != (128,) or z['L20.index_scores'].shape != (CONTEXT,):
        raise ValueError('saved actual append and independent all-rank score reference required')
    out.mkdir(parents=True, exist_ok=False)
    pins = {str(store): STORE_SHA, str(gold): sha(gold)}
    for rank in ranks:
        ids = owned_ids(rank)
        values = np.empty((len(ids),128), np.float32)
        old = np.asarray(ids) < CONTEXT-1
        values[old] = keys[np.asarray(ids)[old]]
        values[~old] = z['ik20']  # saved appended key operand, never a score
        codes, scales = to_codes(values)  # lossless codec, no dot/reduction/golden
        encoded = []
        for j, gid in enumerate(ids):
            payload = sum(int(c) << (4*i) for i,c in enumerate(codes[j]))
            payload |= sum(int(u) << (512+8*i) for i,u in enumerate(scales[j]))
            encoded.append(payload | (1 << 544) | (gid << 546) | (1 << 566))
        directory = out / f'rank{rank:02d}'
        directory.mkdir()
        # Four disjoint contiguous owned-block ranges; no rank-zero replication.
        words = [encoded[j] if j < min((q+1)*342*8,len(ids)) else 0
                 for beat in range(171) for q in range(4) for lane in range(16)
                 for j in [q*342*8+beat*16+lane]]
        (directory/'keys.mem').write_text(''.join(f'{v:0142x}\n' for v in words))
        expected = np.asarray(z['L20.index_scores'][ids],np.float32).view(np.uint32)
        if np.any(expected & 65535):
            raise ValueError('independent captured BF16 scores required')
        (directory/'scores.mem').write_text(''.join(f'{int(v)>>16:04x}\n' for v in expected))
        write_json(directory/'inputs.json', dict(rank=rank, keys=len(ids), beats=171,
            blocks=len(ids)//8, quarter_block_limit=342, source_phase=PHASE,
            source_pins=pins, append_source='saved actual ik20 row',
            comparison_only='scores.mem; never a DUT operand',
            payload_sha256=hashlib.sha256(values.tobytes()).hexdigest(),
            outputs={n:sha(directory/n) for n in ('keys.mem','scores.mem')}))


def compare(run, inputs):
    from hbm_index_path_sources import RTL
    meta = json.loads((inputs/'inputs.json').read_text())
    rank = meta['rank']
    ids = owned_ids(rank)
    scores = [int(s,16) for s in (inputs/'scores.mem').read_text().split()]
    if meta['keys'] != len(ids) or len(scores) != len(ids):
        raise ValueError('actual full rank reference extent required')
    if any(sha(inputs/n) != h for n,h in meta['outputs'].items()):
        raise ValueError('rank input pin changed')
    source = json.loads((run/'source.json').read_text())
    if any(source['source_pins'].get(p) != sha(ROOT/p) for p in RTL):
        raise ValueError('native producer RTL pins differ')
    bench = TB if rank else 'rtl/test/hbm_accel/tb_hbm_index_connected.sv'
    if source['source_pins'].get(bench) != sha(ROOT/bench):
        raise ValueError('actual rank bench pin differs')
    if rank and any(source['inputs'].get(str(inputs/n)) != sha(inputs/n)
                    for n in ('keys.mem','scores.mem','inputs.json')):
        raise ValueError('actual runtime source input pins differ')
    wanted = set(sorted(range(len(ids)), key=lambda j:(-score_key(scores[j]),ids[j]))[:512])
    quarters = [[] for _ in range(4)]
    seen = set()
    for line in (run/'topk.txt').read_text().splitlines():
        gid, val = line.split(); gid, val = int(gid), int(val,16)
        j = gid//8//TP*8+gid%8
        if gid//8%TP != rank or j >= len(ids) or gid != ids[j] or val != scores[j] or gid in seen:
            raise ValueError('actual local top512 score/literal-ID mismatch')
        seen.add(gid)
        quarters[j//8//342].append((gid,val))
    if seen != {ids[j] for j in wanted}:
        raise ValueError('independent full rank top512/tie membership differs')
    # Accepted quarter streams may interleave. Concatenate source ranges only;
    # sorting arbitrary output IDs here would conceal a hardware ordering defect.
    rows = [row for q in quarters for row in q]
    if any(a[0] >= b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('actual within-quarter native order differs')
    blocks = set()
    for line in (run/'candidates.txt').read_text().splitlines():
        block, val = line.split(); block,val = int(block),int(val,16)
        j = block//TP
        if block%TP != rank or j >= len(ids)//8 or block in blocks:
            raise ValueError('actual candidate ownership/count mismatch')
        expected = 0x7f80 if block == (CONTEXT-1)//8 else max(scores[j*8:j*8+8],key=score_key)
        if val != expected:
            raise ValueError('actual block maximum/newest pin differs')
        blocks.add(block)
    if len(blocks) != len(ids)//8:
        raise ValueError('candidate stream incomplete')
    log = (run/'runtime.log').read_text()
    if f'PASS_HBM_NATIVE_CONNECTED_INDEX rank={rank} ' not in log:
        raise ValueError('source-matched terminal runtime PASS missing')
    return rows, dict(rank=rank, score_compares=len(ids), topk_exact=512,
        candidate_exact=len(blocks), source_phase=PHASE,
        native_source_record_sha256=sha(run/'source.json'),
        input_record_sha256=sha(inputs/'inputs.json'),
        native_output_pins={n:sha(run/n) for n in ('topk.txt','candidates.txt','runtime.log')},
        full_token_qualified=False, SS_FF_closed=False)


def emit(entries, out):
    """Convert actual 96 native publications into distinct score/ID planes."""
    if len(entries) != TP or sorted(e['rank'] for e in entries) != list(range(TP)):
        raise ValueError('96 distinct actual rank publications required')
    results, scores, ids = [], [], []
    for entry in sorted(entries,key=lambda e:e['rank']):
        rows, result = compare(Path(entry['run']),Path(entry['inputs']))
        if result['rank'] != entry['rank']:
            raise ValueError('rank source directory identity differs')
        results.append(result)
        scores.extend(v << 16 for _,v in rows)
        ids.extend(i for i,_ in rows)
    if len(set(ids)) != TP*PER_RANK:
        raise ValueError('duplicated/relabelled rank source IDs')
    out.mkdir(parents=True,exist_ok=False)
    for name, values in [('scores',scores),('ids',ids)]:
        (out/(name+'.u32')).write_bytes(struct.pack('<'+str(len(values))+'I',*values))
        # 16 little-endian U32 lanes per real 512-bit source VM word.
        (out/(name+'.mem')).write_text(''.join(''.join(f'{v:08x}' for v in reversed(values[j:j+16]))+'\n'
                                             for j in range(0,len(values),16)))
    write_json(out/'source_phase.json',dict(source_phase=PHASE, ranks=results,
        score_conversion='actual BF16 bits <<16; no numerical rounding',
        id_conversion='actual literal global ID zero-extended to U32',
        quarter_conversion='concatenate ordered disjoint quarter ranges',
        global_order_provider='rtl/hbm_accel/index/ot_hbm_accel_index_order_adapter.sv',
        candidate_mask_applied=False, final_index_qualified=False))
    write_json(out/'producer.json',dict(rank_count=96,candidates_per_rank=512,
        score_dtype='FP32',id_dtype='U32',scores_span_name='scores',ids_span_name='ids',
        source_path='tools/hbm_index_tp96_producer.py',source_phase_path=str(out/'source_phase.json'),
        source_phase=PHASE, rank_stride_bytes=2048, plane_bytes=196608,
        payload_pins={n:sha(out/n) for n in ('scores.u32','ids.u32','scores.mem','ids.mem')},
        installed_spans_required=True, full_index_qualified=False, SS_FF_closed=False))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('prepare')
    for n in ('store','gold','out'):a.add_argument('--'+n,type=Path,required=True)
    a.add_argument('--ranks',type=int,nargs='+',required=True)
    a=sub.add_parser('compare');a.add_argument('--run',type=Path,required=True);a.add_argument('--inputs',type=Path,required=True)
    a=sub.add_parser('emit');a.add_argument('--entries',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.store,a.gold,a.ranks,a.out)
    elif a.mode=='compare':print(json.dumps(compare(a.run,a.inputs)[1],indent=2))
    else:emit(json.loads(a.entries.read_text()),a.out)


if __name__=='__main__':main()
