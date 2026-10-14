#!/usr/bin/env python3
"""qwen-split/kvsys: publish a KV/system die contract revision from a prepped run (chain/kvsys_prep.sh OUT).

Writes results/arch/qwen_split_1014/kvsys_v<tag>/:
  contract.json     every slot: outline, instances + orientation, pins per bus (face / layer / offset / bits / direction),
                    clock entries, PG (tools/qwen_kv_die/hier_contract_export.slot on the prepped case, real views bound)
  pins/INDEX.json   master list: status (CLOSED_VIEW_BOUND / UNCLOSED / HARD_PHY / RELAY), port-bind class, count, outline
  pins/<m>.json     the ASSIGNED pin file of every unclosed master (top-down, owner 10-13): the tile kit consumes it
  port_bind.json, window.json, views.json, clocks.json, plan.json (kv_die plan record: legality, reach, stack-local reach)

    python3 tools/qwen_kv_die/kvsys_contract.py --run OUT --tag 1_1 --version 1.1 --source <commit>
"""
import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import hier_contract_export as H   # noqa: E402
import kv_die as K   # noqa: E402

# per-child clock entries and child sub-slots of the wires-only parents (die-assigned, v1.1)
EXTRA = dict(
    qkd_rhead=dict(
        rtl='rtl/qwen_sys/split_20261014/ot_qkh_head_native.sv ot_qkh_head_native (Q_FP32 1)',
        clock_entries={**{'ck_f': 'ck_front', 'ck_k': 'ck_kt', 'ck_s': 'ck_score'},
                       **{f'ck_t{i}': f'ck_station[{i}]' for i in range(16)}, **{f'ck_l{i}': f'ck_lane[{i}]' for i in range(16)}},
        clock_rule='each entry is delivered at phi - R_child (R = that child view\'s insertion.json boundary mean); '
                   'the die model holds them as 35 separate CTS sinks on the stack trunk (frames: R 0 until the views exist)',
        subslots_canonical_R0=dict(
            note='canonical orientation R0 = control tile BELOW (S face = control face). Heads below their control tile are '
                 'placed MX by the die (their S face then faces up). A feasible fit, not a mandate: the head team may move '
                 'children inside the slot but must keep the die pins and the reach rules below',
            front=dict(xy=[216.0, 16.2], wh=[648.0, 21.6], why='under the control tile t span (x 224.8..673.8 in head coords)'),
            lanes='16 x ot_qkh_lane8 (lane_b view 129.6 x 129.6) on a 3 x 6 grid: x = 43.2 + 172.8 c, y = 54 + 151.2 r '
                  '(18 cells; 16 lanes + ktree + score)',
            ktree=dict(cell='one free cell + its 43.2 column gap (172.8 >= 151.2)', wh=[151.2, 97.2]),
            score=dict(cell='the other free cell', wh=[43.2, 43.2]),
            stations='16 x station <= 32.4 x 32.4, in the 43.2-um column gaps beside their lanes (2 per gap per row)'),
        reach_rules=['die pin -> first register <= 500 um: the ti / e inputs land in the front at the S face, s leaves '
                     'the score; nb leaves on the E face (astk side)',
                     'inside the head every register-to-register hop <= 500 um: with the head 1,080 um wide, the native '
                     'station (one leaf, D = 2 co-located) CANNOT reach both its lane and the E face from the far columns '
                     '(nb from a column-0 station to the E face ~ 900 um): split the station nb stage into station D 1 + an '
                     'nb relay leaf D 1 at the E side (latency unchanged), and keep every station within 500 um of the '
                     'front f_dr pins (else split the front NRS stage the same way)']),
    qkd_ectl=dict(
        rtl='rtl/qwen_sys/split_20261014/qkd_ectl3_s.sv qkd_ectl3_s = qkd_ectl_a_tp8 | qkd_ectl_b_tp8 | qkd_ectl_c_tp8 '
            '(rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv, native HEADS 1 / Q_FP32 1)',
        clock_entries={'ck_a': 'ck[0] (leaf A)', 'ck_b': 'ck[1] (leaf B)', 'ck_c': 'ck[2] (leaf C)'},
        subslots=dict(a=dict(xy=[0.0, 0.0], wh=[254.88, 129.6]), b=dict(xy=[254.88, 0.0], wh=[254.88, 129.6]),
                      c=dict(xy=[509.76, 0.0], wh=[138.24, 129.6])),
        note='the historical closed A/B/C views are HEADS 2 / Q_FP32 0 builds: native views are owed (Codex 11:05). The t0 / t1 '
             'pins (S / N face, M5, 6-track pitch, x 8.5..457.5) are bit-aligned with every head ti; e0/e1 + s0/s1 side by '
             'side at x 470 / 490 (S), e2/e3 + s2/s3 the same on N'),
)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--version', required=True)
    ap.add_argument('--source', required=True)
    a = ap.parse_args(argv)
    K._set_geometry(True)
    out = ROOT / 'results/arch/qwen_split_1014' / f'kvsys_v{a.tag}'
    (out / 'pins').mkdir(parents=True, exist_ok=True)
    c = a.run / 'case_kv'
    lef = {}
    for f in sorted(c.glob('*.lef')):
        H.parse_lef(f, lef)
    master = {}
    for line in open(c / 'die.v'):
        mm = __import__('re').match(r'\s*(\w+)\s+(\\?\S+)\s*\(', line)
        if mm and mm.group(1) in lef:
            master[mm.group(2).lstrip('\\')] = mm.group(1)
    insts = defaultdict(list)
    for line in open(c / 'place.tcl'):
        mm = __import__('re').search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', line)
        if mm and mm.group(1) in master:
            insts[master[mm.group(1)]].append((mm.group(1), float(mm.group(2)), float(mm.group(3)), mm.group(4)))
    slots = {n: H.slot(n, lef[n], insts.get(n, []), {}) for n in sorted(lef) if insts.get(n)}
    pb = json.loads((a.run / 'port_bind.json').read_text())['masters']
    views = json.loads((a.run / 'libs/views.json').read_text())['views']
    clocks = json.loads((a.run / 'libs/clocks.json').read_text())
    # the die clock pins of the generated frames (H.slot only recognises clk / ck names)
    for n, e in EXTRA.items():
        if n in slots:
            s = slots[n]
            s['clock_entry'] = [dict(die_pin=k, rtl=v, **{kk: vv for kk, vv in s['pins'].get(k, {}).items()
                                                          if kk in ('face', 'layers', 'offset_um')})
                                for k, v in e['clock_entries'].items()]
            s.update({k: v for k, v in e.items() if k != 'clock_entries'})
    contract = dict(schema='qwen-hier-contract/0 (provisional; migrate to tools/hier_contract/)', die='qwen_kvsys',
                    version=a.version, source=a.source, period_ps=H.PERIOD_PS, die_outline='qwen_kv',
                    die_um=json.loads((c / 'manifest.json').read_text()).get('die_um'),
                    layer_contract=dict(leaf_signals='M1-M5 (new leaves: M5 cap)', leaf_pg='M5 / M6 / M7 stripes per view',
                                        parent_straps='one layer above children PG', die_top='M8/M9 only'),
                    clocks=dict(rule=clocks['rule'], sinks=clocks['sinks'], measured=clocks['measured']),
                    slots=slots)
    (out / 'contract.json').write_text(json.dumps(contract, indent=1) + '\n')
    index = {}
    for n, s in sorted(slots.items()):
        cls = pb.get(n, {}).get('cls', 'NONE')
        if n.startswith('qkd_rly'):
            status = 'RELAY'
        elif cls == 'HARD_PHY':
            status = 'HARD_PHY'
        elif views.get(n, {}).get('bound'):
            status = 'CLOSED_VIEW_BOUND'
        else:
            status = 'UNCLOSED'
        pf = None
        if status == 'UNCLOSED':
            pf = f'pins/{n}.json'
            rec = dict(master=n, status=status, port_bind=cls, rtl=pb.get(n, {}).get('module'),
                       port_bind_detail={k: pb.get(n, {}).get(k) for k in ('width_or_missing', 'die_ports_not_bound',
                                                                            'rtl_inputs_unconnected', 'rtl_outputs_unread', 'note')},
                       outline_um=s['outline_um'], count=s['count'], instances=s['instances'], clock_entry=s['clock_entry'],
                       pins=s['pins'], contract_version=a.version, source=a.source,
                       rule='die-assigned (top-down, owner 10-13): the tile kit consumes these faces / layers / offsets; '
                            'a pin the tile cannot build is a request in el1014-qwen-split-kvsys.log (next revision)')
            for k in ('rtl', 'subslots', 'subslots_canonical_R0', 'reach_rules', 'note', 'clock_rule'):
                if k in s:
                    rec[k] = s[k]
            (out / pf).write_text(json.dumps(rec, indent=1) + '\n')
        if status != 'RELAY':
            index[n] = dict(status=status, port_bind=cls, count=s['count'], outline_um=s['outline_um'], pin_file=pf,
                            ports=len(s['pins']))
    relays = {n: s['count'] for n, s in slots.items() if n.startswith('qkd_rly')}
    index['_relays'] = dict(status='RELAY', masters=len(relays), instances=sum(relays.values()),
                            note='die relay frames (one per width); real relay RTL with per-bit direction owed (queue)')
    (out / 'pins/INDEX.json').write_text(json.dumps(index, indent=1) + '\n')
    for f, g in (('port_bind.json', 'port_bind.json'), ('window.json', 'window.json'), ('libs/views.json', 'views.json'),
                 ('libs/clocks.json', 'clocks.json')):
        shutil.copy(a.run / f, out / g)
    m = K.build(kv_wq_mirror=True, split=True)
    rec = K.record(m)
    M = K.masters(m, 1)
    rec.update(legality=K.check(m), strict_ports=K.strict_ports(M), pin_reach=K.pin_reach(m, M),
               stack_local_reach=K.stack_local_reach(m, M))
    (out / 'plan.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(json.dumps(dict(out=str(out.relative_to(ROOT)), slots=len(slots), unclosed=sum(1 for v in index.values() if v.get('status') == 'UNCLOSED'),
                          real=sum(1 for v in index.values() if v.get('status') == 'CLOSED_VIEW_BOUND'))))


if __name__ == '__main__':
    main()
