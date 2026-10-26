#!/usr/bin/env python3
"""Classify the HBM v15 die's exposed (undriven) functional inputs by the stream that owns their producer
(H-DIE 2026-10-15 17:05 charter item '1,072 exposed inputs').

Source = results/arch/hbm_die_v15/source_contract/contract.json unbound_ports (direction input), excluding clock roots
(contract clock_roots: die CTS, NEEDS_REAL_CTS_VIEW) and reset ports (staged reset tree).  Every remaining row is a real
RTL input of a contract instance with no producer in the die netlist: it must be bound to a real producer, never tied.

    exposed_inputs.py [--out results/arch/hbm_die_v15/views_v5/exposed_inputs_by_owner_1705.json]
"""
import argparse, json, re
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'results/arch/hbm_die_v15/source_contract/contract.json'
STREAM = {   # contract required_owner -> owning stream (CHARTERS_1705) + the structural action
    'actual PHY service band / compiler block command source':
        ('H-DIE', 'SM-specific 4-PC service engine (Codex DECISION 14:40, ot_hbm_svc_sm_stack_native) drives the band '
                  'cmd/K ports; bind its outputs into the die contract'),
    'actual VM programme SRAM calendar issuer': ('H-SM', 'VM calendar issuer (programme SRAM) into hb_vms/calendar'),
    'actual static client source migration': ('H-SM', 'VM client cq/wq static source migration'),
    'actual service key staging (key_slot/key_index/key_lines)': ('H-SM', 'attention-on-SM key staging producer'),
    'actual SFU programme loader / CP and lane reset tree': ('H-SU', 'SFU programme loader (4-leaf SFU split)'),
    'actual SFU operand SRAM / SU join': ('H-SU', 'SFU operand store <- whole-SU join'),
    'actual static SU arithmetic su_rq/su_wq producer (H-ELEM-B)': ('H-SU', 'whole-SU arithmetic producer'),
    'actual SU static logit stream (MTP, H-ELEM-B/s_mtp)': ('H-SU', 'MTP logit stream'),
    'actual static DMA dispatcher (cycle/move/issue_at/drain_at)': ('H-HARDEN', 'static DMA dispatcher'),
    'actual service WB band (static block reservation)': ('H-HARDEN', 'service write-back band reservation'),
    'actual INDEX programme loader / CP': ('H-COLL+IDX', 'INDEX programme loader'),
    'actual ARGMAX record issuer (programme loader / CP)': ('H-COLL+IDX', 'ARGMAX record issuer'),
    'OFF-DIE die-to-die/package SerDes link (link-level flow control allowed, HANDOFF 0az)':
        ('H-COLL+IDX', 'ep_* link-capture group over lk_* ot_pdie_serdes (elastic at the off-die boundary only)'),
    'actual host/CP loader (NW target 48)': ('H-DIE (host_cp)', 'host_cp programme loader parent over host_cp_ingress'),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/hbm_die_v15/views_v5/exposed_inputs_by_owner_1705.json')
    a = ap.parse_args()
    C = json.loads(CONTRACT.read_text())
    ck = {(r['instance'], r['port']) for r in C['clock_roots']}
    rows = [x for x in C['unbound_ports'] if x['direction'] == 'input' and (x['instance'], x['port']) not in ck
            and not re.fullmatch(r'(rst|rst_n|\w*_rst_n|clk\w*)', x['port'])]
    by = defaultdict(lambda: dict(ports=0, bits=0, instances=set(), action=''))
    unknown = []
    for x in rows:
        if x['required_owner'] not in STREAM:
            unknown.append(x['required_owner']); continue
        s, act = STREAM[x['required_owner']]
        r = by[s]; r['ports'] += 1; r['bits'] += x['unbound_bits']; r['instances'].add(x['instance'])
        r.setdefault('producers', defaultdict(lambda: [0, 0]))
        r['producers'][x['required_owner']][0] += 1; r['producers'][x['required_owner']][1] += x['unbound_bits']
    assert not unknown, sorted(set(unknown))
    out = dict(schema='opentallas.hbm_v15.exposed_inputs.v1', contract=str(CONTRACT.relative_to(ROOT)),
               total_ports=len(rows), total_bits=sum(x['unbound_bits'] for x in rows),
               excluded='clock roots (die CTS) and reset ports (staged reset tree)',
               by_stream={s: dict(ports=r['ports'], bits=r['bits'], instances=len(r['instances']),
                                  producers={k: dict(ports=v[0], bits=v[1], action=STREAM[k][1])
                                             for k, v in r['producers'].items()})
                          for s, r in sorted(by.items(), key=lambda t: -t[1]['ports'])},
               rule='bind to a real producer; never tie, stub or alias (owner 10-14 08:05)')
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({s: (v['ports'], v['bits']) for s, v in out['by_stream'].items()}), out['total_ports'], out['total_bits'])


if __name__ == '__main__':
    main()
