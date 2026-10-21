#!/usr/bin/env python3
"""TOKSIM-HBM-su 10-19: Qwen SFU.GLU (swiglu) bench case for tb_toksim_glu_split.sv at W words on ONE sfucore.

Generalises tools/hbm_static/make_qswiglu_gate.py + make_qswiglu_io_calendar.py (canonical W=3072, unchanged math):
the operands/golden are the FIRST W words of the canonical Qwen3-8B fixture (hbm-sim TP4 P8191 L0 swiglu; the op is
element-wise, so the first W golden words are exactly the golden of the W-word record), programme = compile_vector(W),
IO calendar = the canonical rows with W/16 prefetch / drain beats.  DRAIN_LAG = drain start - arith start
(canonical overlap 190; smaller values are tried and the bench's bit-exact readback is the oracle).
usage: gen_glu_case.py FIXTURE OUT WORDS OVERLAP(0|1) DRAIN_LAG LG_PATH
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sfu_control_image import encode
from sfu_vector_calendar import compile_vector

fixture, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
W, overlap, lag, lg_path = int(sys.argv[3]), sys.argv[4] == '1', int(sys.argv[5]), int(sys.argv[6])
assert W % 64 == 0 and 64 <= W <= 3072
meta = json.loads((fixture/'su_prod.json').read_text()); case = meta['cases'][0]
assert case['tag'] == 'swiglu' and case['roles'] == {'A': [168960, 172031, 3072], 'B': [172032, 175103, 3072], 'C': [12672, 12672, 1], 'O': [175104, 178175, 3072]}
def read_vm(path):
    words = {}
    for line in path.read_text().splitlines():
        sector = int(line[:8], 16); payload = int(line[8:], 16)
        for i in range(8): words[sector*8+i] = payload >> (32*i) & 0xffffffff
    return words
vin, vout = read_vm(fixture/'su_vmi.mem'), read_vm(fixture/'su_vme.mem')
for name, base, count, src in [('gate', 168960, W, vin), ('up', 172032, W, vin), ('route', 12672, 1, vin), ('gold', 175104, W, vout)]:
    (out/(name+'.hex')).write_text(''.join(f'{src[base+i]:08x}\n' for i in range(count)))
program = compile_vector(words=W, bases=(0, 12672, 0, 0, 0), strides=(1, 0, 1, 1, 1), amin=1, cclip=1, imm3=0x7f7fffff, sfu=5, e1=1, e2=1, rnd=1)
words = encode(program)
(out/'image.hex').write_text(''.join(f'{w:0436x}\n' for w in words))
vm = {}
for i in range(W):
    vm[i] = vin[168960+i]; vm[1026*8+i] = vin[172032+i]
vm[2052*8] = vin[12672]
(out/'vm_init.hex').write_text(''.join(f'{sum(vm.get(s*8+w, 0) << (32*w) for w in range(8)):064x}\n' for s in range(2056)))
F = [('prefetch_v', 8), ('prefetch_scalar', 8), ('prefetch_sector', 128), ('prefetch_group', 16), ('prefetch_local_addr', 120),
     ('prefetch_word', 24), ('scalar_addr', 96), ('scalar_enable', 4), ('drain_v', 2), ('drain_addr', 30), ('drain_vm_sector', 32),
     ('drain_round_bf16', 2), ('arith_start', 1)]
B = W//16
if overlap: scalar_edge, arith_edge = 0, 20
else: scalar_edge, arith_edge = B, B+18
drain_edge = arith_edge+lag
length = drain_edge+B+30
shift = 2*lg_path
length, arith_edge, drain_edge = length+shift, arith_edge+shift, drain_edge+shift
rows = []
for t in range(length):
    d = dict(scalar_addr=12672 << 24, scalar_enable=2)
    if t < B:
        d.update(prefetch_v=0, prefetch_sector=0, prefetch_group=0, prefetch_local_addr=0)
        for part in range(2):
            for base, group in ((0, 0), (1026, 2)):
                sector = base+t*2+part; b = sector % 8
                d['prefetch_v'] |= 1 << b; d['prefetch_sector'] |= sector << (16*b)
                d['prefetch_group'] |= group << (2*b); d['prefetch_local_addr'] |= (t*16+part*8) << (15*b)
    if t == scalar_edge:
        d['prefetch_v'] = d.get('prefetch_v', 0) | 16; d['prefetch_scalar'] = 16
        d['prefetch_sector'] = d.get('prefetch_sector', 0) | (2052 << 64); d['prefetch_group'] = d.get('prefetch_group', 0) | (1 << 8)
    if t == arith_edge: d['arith_start'] = 1
    if drain_edge <= t < drain_edge+B:
        beat = t-drain_edge
        d.update(drain_v=3, drain_addr=(beat*16) | ((beat*16+8) << 15), drain_vm_sector=(4096+beat*2) | ((4096+beat*2+1) << 16))
    word = 0; off = 0
    for name, w in F:
        v = d.get(name, 0); assert 0 <= v < 1 << w, (t, name, v); word |= v << off; off += w
    rows.append(word)
(out/'io.hex').write_text(''.join(f'{w:0118x}\n' for w in rows))
ADV = 2
rows_r10 = [w & ~(1 << 470) for w in rows]; rows_r10[arith_edge-ADV] |= 1 << 470
(out/'io_store_r10.hex').write_text(''.join(f'{w:0118x}\n' for w in rows_r10))
(out/'io_manifest.json').write_text(json.dumps(dict(width=471, rows=length, words=W, ninst=len(words), prefetch_edges=B, scalar_prefetch_edge=scalar_edge,
    arith_start_edge=arith_edge, drain_edges=[drain_edge, drain_edge+B], drain_lag=lag, overlap=overlap, lg_path=lg_path, latency_shift_edges=shift,
    fixture_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir() if p.is_file()}), indent=2)+'\n')
print(f'GLU_CASE W={W} ninst={len(words)} io_rows={length} arith={arith_edge} drain={drain_edge} overlap={int(overlap)} lag={lag}')
