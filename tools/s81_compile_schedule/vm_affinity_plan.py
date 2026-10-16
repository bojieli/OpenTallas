#!/usr/bin/env python3
"""Client-affine S81 VM banking plan on the ACTUAL compiler tensor inventory (S-FUNC 2026-10-16).

Inputs (no fixture values): the compiler-owned SU operand allocations (operand_layout.LAYOUT +
full_su_operand_layout.layout(): name, rows, producer, consumer) and the MIX4 HLAYOUT=1 view (H 640 rows shared by
HC / MIX4 / SU, K 1,280 + W 1,280 + V 320 MIX-only rows on Engram stages).  Every producer / consumer string is
classified to a VM CLIENT by the explicit table below (unknown -> hard error, never a default).

Plan: each tensor lives in the slice set of its PRIMARY consumer (mapping A of S-FUNC -> S-VM 10-15: su [0,1],
mix [0,2], hc [3], pq/field/gather [3], coll [1], svc/sel [1], sseq [0]); producers write into the consumer's set
(cross-client writes are allowed only through an explicitly wired port and are listed).  Reports, per stage kind
(dense/MoE stage; Engram stage = + MIX4):
  * per-slice physical-row occupancy vs 16,384 (vm_slice_affinity.allocate; overflow = infeasible, no shrink);
  * the exact read / write slice reach each client port must be wired to (the RTL obligation);
  * every cross-set access (producer or secondary consumer outside its home set) = the extra reach S-VM prices.
Two spans are reported for the MoE expert outputs: as allocated today (320-row reserved spans with row stride 4 =
the striped SU read colour rule) and compact (80 used rows), because the colour rule is a property of the striped
read router that an affine router replaces.  Neither is assumed silently: both are in the record.

    python3 tools/s81_compile_schedule/vm_affinity_plan.py --out results/arch/s81_vm_affinity_1016/plan.json
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_compile_schedule'))
sys.path.insert(0, str(ROOT / 'tools/s81_suhc'))
sys.path.insert(0, str(ROOT / 'tools/s81_engram_mix'))
import operand_layout as FIRST  # noqa: E402
import full_su_operand_layout as FULL  # noqa: E402
import vm_slice_affinity as VSA  # noqa: E402

MAPPING_A = dict(su=[0, 1], mix=[0, 2], hc=[3], pq=[3], coll=[1], svc=[1], sel=[1], sseq=[0])

# literal producer/consumer text -> VM client (first matching rule wins; order matters, no fallback)
RULES = [
    ('TP4 all-gather', 'coll'), ('TP4 activation gather', 'coll'), ('allgather', 'coll'), ('a_allgather', 'coll'),
    ('own_row_write', 'svc'),
    ('wq_b', 'pq'), ('WO_A', 'pq'), ('WO_B', 'pq'), ('W2 all72column', 'pq'),
    ('W1/W3', 'capture'), ('expert slot', 'capture'), ('shared.w2', 'capture'),
    ('constant boot', 'boot'),
    ('attn.', 'su'), ('ffn.', 'su'), ('native QK', 'su'), ('native PV', 'su'), ('SE', 'su'), ('SO', 'su'), ('QB', 'su'),
    ('MOE', 'su'), ('SW576', 'su'), ('SU kernels', 'su'), ('ratio1 CN', 'su'),
]
# producer client -> the port that writes the VM (field results land through the capture face)
WRITER_PORT = dict(su='su', coll='coll', capture='capture', boot='wfc', svc='svc', hc='hc', mix='mix', pq='pq')


# a field matmul named as a PRODUCER lands through the capture face (its consumer-side name is the PQ/gather read)
FIELD_MATMULS = ('wq_b', 'WO_A', 'WO_B', 'W2 all72column')


def classify(text: str, role: str = 'consumer') -> str:
    if role == 'producer' and any(k in text for k in FIELD_MATMULS):
        return 'capture'
    for key, client in RULES:
        if key in text:
            return client
    raise ValueError(f'unclassified VM producer/consumer {text!r}: extend RULES with the real client')


def su_inventory(compact_moe: bool) -> list:
    items = dict(FIRST.LAYOUT)
    items.update(FULL.layout())
    out = []
    for name, v in sorted(items.items(), key=lambda kv: kv[1]['base_row']):
        rows = v['nrows']                      # as allocated (MoE: 320-row reserved span at row stride 4)
        if compact_moe and v.get('used_rows'):
            rows = v['used_rows']               # rows actually written/read (MoE: 80)
        prod = v.get('producer', '')
        cons = v.get('consumer', '')
        # 'X then Y': only X reads THIS tensor (Y reads X's result); 'X and Y' / 'X or Y': both read it
        first = cons.split(' then ')[0]
        consumers = list(dict.fromkeys(classify(c.strip()) for c in first.replace(' or ', ' and ').split(' and ')))
        out.append(dict(name=name, rows=rows, producer=classify(prod, 'producer'), consumers=consumers,
                        producer_text=prod, consumer_text=cons, source='operand_layout/full_su_operand_layout'))
    return out


def mix_inventory() -> list:
    # MIX4 HLAYOUT=1 (tools/s81_engram_mix/layout.py): H = HC hidden rows (640), consumed by HC (primary: HC pre/post
    # every layer), MIX4 (Engram stages) and SU (hc_pre/attn.quant read H); K/W four copies x 160 beats x 2 rows;
    # V one shared copy 160 x 2 rows.  K/W/V are Engram field outputs (E.wkv) read only by MIX4.
    return [dict(name='hc_H', rows=640, producer=['hc', 'mix'], consumers=['hc', 'mix', 'su'], source='engram_mix/layout.py HLAYOUT=1'),
            dict(name='mix_K', rows=1280, producer='capture', consumers=['mix'], source='engram_mix/layout.py'),
            dict(name='mix_W', rows=1280, producer='capture', consumers=['mix'], source='engram_mix/layout.py'),
            dict(name='mix_V', rows=320, producer='capture', consumers=['mix'], source='engram_mix/layout.py')]


def plan(tensors: list, mapping: dict) -> dict:
    placed, reach, cross = [], {}, []
    for t in tensors:
        home = mapping[t['consumers'][0]]
        placed.append(dict(name=t['name'], rows=t['rows'], slices=home))
        for c in t['consumers']:
            r = reach.setdefault(c, dict(read=set(), write=set()))
            r['read'] |= set(home)
            if mapping.get(c) != home:
                cross.append(dict(tensor=t['name'], rows=t['rows'], access='read', client=c, home=home,
                                  client_set=mapping.get(c)))
        for prod in ([t['producer']] if isinstance(t['producer'], str) else t['producer']):
            w = WRITER_PORT[prod]
            r = reach.setdefault(w, dict(read=set(), write=set()))
            r['write'] |= set(home)
            if mapping.get(w) != home:
                cross.append(dict(tensor=t['name'], rows=t['rows'], access='write', client=w, home=home,
                                  client_set=mapping.get(w)))
    alloc = VSA.allocate(placed)
    by_set = {}
    for p in placed:
        by_set[str(p['slices'])] = by_set.get(str(p['slices']), 0) + p['rows']
    return dict(logical_rows_by_set=by_set, slice_rows_used=alloc['slice_rows_used'], slice_rows=VSA.SLICE_ROWS,
                fits=not alloc['overflow'], overflow=alloc['overflow'],
                client_reach={c: dict(read=sorted(v['read']), write=sorted(v['write'])) for c, v in sorted(reach.items())},
                cross_set_accesses=cross, regions=alloc['regions'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    res = dict(schema='opentallas.s81.vm-affinity-plan.v1', mapping=MAPPING_A, qualified=False,
               grade='COMPILER PLAN on the actual tensor inventory; no RTL, no routed relay, no performance acceptance',
               slice_rows=VSA.SLICE_ROWS, cases={})
    for compact in (False, True):
        su = su_inventory(compact)
        tag = 'compact_moe' if compact else 'as_allocated'
        res['cases'][f'dense_stage.{tag}'] = plan(su + mix_inventory()[:1], MAPPING_A)
        res['cases'][f'engram_stage.{tag}'] = plan(su + mix_inventory(), MAPPING_A)
    res['inventory'] = [dict({k: v for k, v in t.items()}) for t in su_inventory(False) + mix_inventory()]
    res['not_inventoried'] = ['HC private coefficient/sumsq rows (HC owner)', 'collective landing/scratch rows',
                              'PQ/gather staging rows', 'WFC/boot parameter rows beyond parameter_storage',
                              'Engram lookup rows (static lookup element)']
    txt = json.dumps(res, indent=1) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(txt)
    for k, v in res['cases'].items():
        print(k, 'fits' if v['fits'] else 'OVERFLOW', v['slice_rows_used'], v['logical_rows_by_set'])
    print(json.dumps(res['cases']['engram_stage.compact_moe']['client_reach']))


if __name__ == '__main__':
    main()
