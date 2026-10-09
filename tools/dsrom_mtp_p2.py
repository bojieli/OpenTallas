#!/usr/bin/env python3
"""Opt-in MD-2 P2 storage allocation. This is a ROM storage map, not a qualified field schedule.

Pair images are two 272-bit fault-free ROM words per address, little endian,
34 bytes per bank. Five row replicas share each side/rank image.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, struct, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_1m_draft_blocks as D
DEPTH, PAIRS = 8192, 1792


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def allocate(snapshot):
    import dsrom_1m_field as FD
    headers = D._ckpt_headers(snapshot)
    entries = {}
    with gzip.open(FD.S81 / 'matrix_map.jsonl.gz', 'rt') as f:
        for line in f:
            e = json.loads(line)
            if e['layer'] == 0 and e['expert'] is not None and e['expert'] < 128:
                entries[e['alias']] = e
    cursors = dict(A=0, B=0)
    matrices = []
    covered = set()
    for stage in range(3):
        for expert in range(128):
            side = 'A' if stage == 0 or (stage == 2 and expert < 64) else 'B'
            for op in ('w1', 'w3', 'w2'):
                e = entries[f'exp{expert}.{op}']
                tensor = f'mtp.{stage}.ffn.experts.{expert}.{op}.weight'
                scale = tensor[:-6] + 'scale'
                assert tensor in headers and scale in headers
                covered.update((tensor, scale))
                assert e['format'] == 'fp4' and len(e['segments']) == 1
                assert headers[tensor]['dtype'] == 'I8' and headers[scale]['dtype'] == 'F8_E8M0'
                assert headers[tensor]['shape'][1] * 2 == e['K']
                assert headers[scale]['shape'] == [headers[tensor]['shape'][0], e['K']//32]
                # One rank's paired rows. Each FP4 pair word stores two 32-code blocks per bank.
                rows, k = e['rows'], e['K']
                assert rows % 2 == 0 and k % 256 == 0
                nword = rows // 2 * (math.ceil(k / 512) * 8)
                assert nword == sum(p[3] * p[6] for p in e['plans'])
                base = cursors[side]
                end = base + nword
                spans = []
                pos = base
                while pos < end:
                    count = min(end - pos, DEPTH - pos % DEPTH)
                    spans.append([pos // DEPTH, pos % DEPTH, count, pos - base])
                    pos += count
                assert end <= PAIRS * DEPTH
                slices = e['rank_slices']
                assert slices[0]['rows'][0] == 0 and slices[-1]['rows'][1] == headers[tensor]['shape'][0]
                assert all(slices[i]['rows'][1] == slices[i+1]['rows'][0] for i in range(3))
                matrices.append(dict(tensor=tensor, scale=scale, stage=stage, expert=expert, op=op,
                                     side=side, rows=rows, K=k, rank_slices=slices,
                                     words=nword, linear_base=base, spans=spans))
                cursors[side] = end
    assert len(covered) == 2304
    remaining = [dict(tensor=t, **headers[t], home=('head h0..h3 primary' if not t.split('.',2)[2].startswith(D.NONBLOCK_HEAD) else 'head term'))
                 for t in sorted(set(headers)-covered)]
    return dict(schema='opentallas.dsrom-mtp-p2-storage.v1', checkpoint=snapshot.resolve().name,
                source_commit=D.git_head(), source_sha256=digest(__file__), index_sha256=digest(snapshot/'model.safetensors.index.json'),
                opt_in=True, qualified_field_schedule=False,
                limitation='Dense ROM packing crosses paired-row boundaries; requires a new field configuration/read schedule and RTL timing/exactness qualification. Legacy L0 measured timing cannot establish P2 timing.',
                topology=dict(primary_head_dies=['h0','h1','h2','h3'], dedicated_expert_dies=40,
                              replicas=5, ranks=4, sides=['A','B'], primary_board_links=5,
                              expert_sum_home='A', expert_sum_order='router id order; B returns individual expert outputs'),
                capacity=dict(pair_words=DEPTH, pairs_per_die=PAIRS, words_per_side=cursors,
                              used_pairs={s:math.ceil(n/DEPTH) for s,n in cursors.items()}),
                coverage=dict(released_headers=len(headers), expert_headers=len(covered), other_headers=len(remaining),
                              complete=set(headers)==covered|{r['tensor'] for r in remaining}),
                word_order='superrow ascending; u ascending; b 0..7; halves 0,1; banks rows 2*superrow and 2*superrow+1',
                matrices=matrices, other_tensors=remaining)


class Raw:
    def __init__(self, snap):
        self.snap=snap
        self.index=json.loads((snap/'model.safetensors.index.json').read_text())['weight_map']
        self.headers={}
    def array(self, tensor):
        fn=self.index[tensor]
        if fn not in self.headers:
            with (self.snap/fn).open('rb') as f:
                n=struct.unpack('<Q',f.read(8))[0]
                self.headers[fn]=(8+n,json.loads(f.read(n)))
        base,h=self.headers[fn]; t=h[tensor]
        return np.memmap(self.snap/fn, dtype=np.uint8, mode='r', offset=base+t['data_offsets'][0], shape=tuple(t['shape']))


def image(plan, snapshot, side, rank, pair, output):
    assert 0<=rank<4 and 0<=pair<PAIRS
    raw=Raw(snapshot)
    bank=np.zeros((DEPTH,2,34),dtype=np.uint8)
    occupied=np.zeros(DEPTH,dtype=bool)
    checks=0
    for m in plan['matrices']:
        if m['side']!=side: continue
        spans=[s for s in m['spans'] if s[0]==pair]
        if not spans: continue
        packed=raw.array(m['tensor']); scale=raw.array(m['scale'])
        r0=m['rank_slices'][rank]['rows'][0]
        words_per_row=math.ceil(m['K']/512)*8
        for _,addr,count,start in spans:
            assert not occupied[addr:addr+count].any()
            for j in range(count):
                sr,w=divmod(start+j,words_per_row)
                u,b=divmod(w,8)
                for mb in range(2):
                    row=r0+2*sr+mb
                    for half in range(2):
                        block=(2*u+half)*8+b
                        if block*32 >= m['K']: continue
                        codes=packed[row,block*16:(block+1)*16]
                        exp=int(scale[row,block])
                        off=half*17
                        bank[addr+j,mb,off:off+16]=codes
                        bank[addr+j,mb,off+16]=exp
                        # Independent reconstruction validates bit packing against released bytes.
                        word=int.from_bytes(bank[addr+j,mb].tobytes(),'little')
                        assert ((word>>(136*half)) & ((1<<128)-1)) == int.from_bytes(codes.tobytes(),'little')
                        assert (word>>(136*half+128))&255 == exp
                        checks+=1
            occupied[addr:addr+count]=True
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError(output)
    output.write_bytes(bank.tobytes())
    return dict(side=side,rank=rank,pair=pair,occupied_words=int(occupied.sum()),released_block_checks=checks,
                image_sha256=digest(output),bytes=output.stat().st_size)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,default=D.SNAP_DEFAULT)
    p.add_argument('--record',type=Path,required=True)
    p.add_argument('--images',type=Path)
    p.add_argument('--side',choices=['A','B'],default='A')
    p.add_argument('--rank',type=int,default=0)
    p.add_argument('--pairs',type=int,nargs='+',default=[0])
    a=p.parse_args(); rec=allocate(a.snapshot)
    if a.images:
        rec['image_checks']=[image(rec,a.snapshot,a.side,a.rank,x,a.images/f'{a.side}.rank{a.rank}.pair{x}.bin') for x in a.pairs]
    a.record.parent.mkdir(parents=True,exist_ok=True)
    if a.record.exists(): raise FileExistsError(a.record)
    a.record.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({k:rec[k] for k in ['capacity','coverage','qualified_field_schedule']},indent=1))
if __name__=='__main__': main()
