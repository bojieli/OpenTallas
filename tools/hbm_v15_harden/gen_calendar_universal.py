#!/usr/bin/env python3
"""H-HARDEN 2026-10-15: stimulus for the ONE VM calendar master hfd_hgi_vm_calendar (universal programme layout).
Per quadrant: a seeded random legal schedule (every field at the quadrant's own width and resource bounds; LG taps off,
the LG transport is proven by run_lg_static_programmed) is compiled by tools/hbm_vm_static_calendar.py into the
universal layout; the same values compiled into the old per-quadrant layout must unpack to identical field values
(the universal master is a strict superset).  Writes cfg.hex (addr data), start.txt, expect.hex (one 187-bit calendar
word per output edge, in order)."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_vm_static_calendar as C  # noqa: E402

q, out = sys.argv[1], Path(sys.argv[2])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
loops = int(sys.argv[4]) if len(sys.argv) > 4 else 3
abi = json.loads((ROOT / 'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
U = C.layout(abi, q, universal=True)
Q = C.layout(abi, q)
P = Q['params']
bits = {f['name']: f['bits'] for f in Q['fields']}
rnd = random.Random({'SW': 11, 'SE': 12, 'NW': 13, 'NE': 14}[q])


def per(nf, w, hi):
    return sum(rnd.randint(0, hi) << (i * w) for i in range(nf))


cycles = []
for _ in range(n):
    v = {}
    for f in ('client_seq', 'response_enable', 'response_seq', 'hub_ring_enable', 'hub_ring_client', 'replay_enable',
              'replay_source', 'bank_enable', 'rslot_v', 'wslot_v', 'ring_tx_enable'):
        v[f] = rnd.getrandbits(bits[f])
    v['rslot'] = per(8, P['RB'], min(P['RG'], (1 << P['RB']) - 1))
    v['wslot'] = per(8, P['WB'], min(P['WG'] + 4, (1 << P['WB']) - 1))
    v['bank_client'] = per(8, P['CW'], min(P['NC'], (1 << P['CW']) - 1))
    v['ring_tx_source'] = per(2, 3, 4)
    v['lg_local_read'] = v['lg_local_write'] = 0
    cycles.append(v)
sched = dict(base=rnd.randint(0, 1024 - n), loops=loops, cycles=cycles)
pu = C.compile_schedule(U, sched)
pq = C.compile_schedule(Q, sched)
# superset check: per-quadrant word and universal word carry the same field values
for wu, wq in zip(pu['configuration_writes'], pq['configuration_writes']):
    a, b = int(wu['data'], 16), int(wq['data'], 16)
    assert a >> 224 == b >> 224
    for fu, fq in zip(U['fields'], Q['fields']):
        assert fu['name'] == fq['name'] and fu['bits'] >= fq['bits']
        vu = (a >> fu['lo']) & ((1 << fu['bits']) - 1)
        vq = (b >> fq['lo']) & ((1 << fq['bits']) - 1)
        assert vu == vq, (fu['name'], vu, vq)
out.mkdir(parents=True, exist_ok=True)
(out / 'cfg.hex').write_text(''.join(f"{w['addr']:03x}_{w['data']}\n" for w in pu['configuration_writes']))
s = pu['start']
(out / 'start.txt').write_text(f"{s['base']} {s['limit']} {s['loops']} {len(pu['configuration_writes'])} {pu['output_edges']}\n")
words = [int(w['data'], 16) & ((1 << U['bits']) - 1) for w in pu['configuration_writes']]
(out / 'expect.hex').write_text(''.join(f'{words[i % n]:047x}\n' for i in range(pu['output_edges'])))
print(f'CAL_UNIVERSAL_STIM {q} words={n} loops={loops} edges={pu["output_edges"]} W={U["bits"]} superset=OK')
