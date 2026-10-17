#!/usr/bin/env python3
"""Bit-level net map of the SOFT IDX client composition (H-NETLIST/IDXP 2026-10-16).

    idx_soft_netmap_1016.py OUT_JSON

Elaborates rtl/hbm_accel/index/soft_1016/ot_hbm_idx_client_static_soft.sv with yosys, every child master read as a
blackbox from its real source (ot_hbm_idx_ctl_static included), and writes for every child port bit what it connects
to: ["P", <client port>, bit] (a port of hb_idx = ot_hbm_idx_client_static_sw, identical port list), ["C", 0|1], or
["N", <net id>] (an internal child-to-child net). Consumed by full_die_v16.py --soft-idx (tools/hbm_die_v15/
soft_parent.py), which replaces the die instance hb_idx by its children hb_idx__<child>. The module must hold wires
and constants only (asserted: no cell other than the children).
"""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDX = 'rtl/hbm_accel/index/'
SOFT = IDX + 'soft_1016/ot_hbm_idx_client_static_soft.sv'
CHILD_SRC = {
    'ot_hbm_idx_ctl_static': IDX + 'soft_1016/ot_hbm_idx_ctl_static.sv',
    'ot_hbm_idx_vm_query_static': IDX + 'ot_hbm_idx_vm_query_static.sv',
    'ot_hbm_idx_query_static': IDX + 'ot_hbm_idx_query_static.sv',
    'ot_hbm_idx_score_static': IDX + 'ot_hbm_idx_score_static.sv',
    'ot_hbm_idx_selector_static': IDX + 'ot_hbm_idx_selector_static.sv',
    'ot_hbm_idx_topk_link_static': IDX + 'ot_hbm_idx_topk_link_static.sv',
}
TOP = 'ot_hbm_idx_client_static_soft'


def main():
    out = Path(sys.argv[1])
    nq = int(sys.argv[2]) if len(sys.argv) > 2 else 4          # N_Q of the composition (A2P half die: 2)
    with tempfile.TemporaryDirectory() as td:
        j = Path(td) / 'soft.json'
        lib = ' '.join(str(ROOT / f) for f in CHILD_SRC.values())
        r = subprocess.run(['yosys', '-q', '-p', f'read_verilog -sv -lib {lib}; read_verilog -sv {ROOT / SOFT}; '
                            f'chparam -set N_Q {nq} {TOP}; hierarchy -top {TOP}; proc; opt_clean -purge; write_json {j}'], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
        d = json.loads(j.read_text())
    m = d['modules'][TOP]
    port_of = {}
    for p, x in m['ports'].items():
        for b, bit in enumerate(x['bits']):
            if isinstance(bit, int):
                port_of.setdefault(bit, []).append((p, b, x['direction']))
    children = {}
    for cn, c in m['cells'].items():
        if c['type'] not in CHILD_SRC:
            sys.exit(f'soft module holds a non-child cell {cn} ({c["type"]}): glue must live in ot_hbm_idx_ctl_static')
        conns = {}
        for p, bits in c['connections'].items():
            v = []
            for bit in bits:
                if bit in ('0', '1'):
                    v.append(['C', int(bit)])
                elif bit in ('x', 'z'):
                    sys.exit(f'{cn}.{p}: undriven/x bit')
                elif bit in port_of and any(dr == 'input' for _, _, dr in port_of[bit]):
                    pp, bb, _ = next(t for t in port_of[bit] if t[2] == 'input')
                    v.append(['P', pp, bb])
                else:
                    v.append(['N', bit])
            conns[p] = dict(direction=c['port_directions'][p], bits=v)
        children[re.sub(r'^gscore\[(\d)\]\.scorer$', r'scorer\1', cn.lstrip('\\'))] = dict(master=c['type'], source=CHILD_SRC[c['type']], ports=conns)
    # client outputs: which net / constant / input drives each bit
    outs = {}
    for p, x in m['ports'].items():
        if x['direction'] != 'output':
            continue
        v = []
        for bit in x['bits']:
            if bit in ('0', '1'):
                v.append(['C', int(bit)])
            elif any(dr == 'input' for _, _, dr in port_of.get(bit, [])):
                pp, bb, _ = next(t for t in port_of[bit] if t[2] == 'input'); v.append(['P', pp, bb])
            else:
                v.append(['N', bit])
        outs[p] = v
    drivers = {}
    for cn, c in children.items():
        for p, x in c['ports'].items():
            if x['direction'] == 'output':
                for b, t in enumerate(x['bits']):
                    if t[0] == 'N':
                        assert t[1] not in drivers, ('multi-driven net', t, cn, p)
                        drivers[t[1]] = [cn, p, b]
    for cn, c in children.items():
        for p, x in c['ports'].items():
            if x['direction'] == 'input':
                for t in x['bits']:
                    assert t[0] != 'N' or t[1] in drivers, ('undriven child input net', cn, p)
    for p, v in outs.items():
        for t in v:
            assert t[0] != 'N' or t[1] in drivers, ('undriven client output', p)
    rec = dict(schema='opentallas.hbm_idx_soft_netmap.v1', top=TOP, params=dict(N_Q=nq), replaces='hb_idx (ot_hbm_idx_client_static_sw)',
               sources={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in [SOFT] + list(CHILD_SRC.values())},
               children=children, outputs=outs, net_drivers={str(k): v for k, v in drivers.items()})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=0) + '\n')
    print(json.dumps(dict(children={k: v['master'] for k, v in children.items()}, nets=len(drivers),
                          outputs=len(outs))))


if __name__ == '__main__':
    main()
