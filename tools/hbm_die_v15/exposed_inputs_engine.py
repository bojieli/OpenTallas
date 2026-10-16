#!/usr/bin/env python3
"""Disposition of H-DIE's exposed die inputs under the SM-specific service engine (H-DIE 2026-10-15 18:15).

The 816 H-DIE inputs of exposed_inputs_by_owner_1705.json ('actual PHY service band / compiler block command source')
are three groups of v15.1 contract instances.  With the engine (ot_hbm_svc_sm_group = issuer + feed, 32 real controller
leaves per stack, PHY-only abstract) each group gets a disposition; the engine's own inputs are listed with their owner.
    exposed_inputs_engine.py [--out results/arch/hbm_die_v15/views_v5/exposed_inputs_engine_1815.json]
"""
import argparse, json, re
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'results/arch/hbm_die_v15/source_contract/contract.json'
DISP = {
 'svc': ('RETIRED_BY_ENGINE', 'the 34 svc bands (and their 128 PCs) are replaced by the SM service groups + controller leaves; '
         'open/fill/read/retire/cmd are now generated INSIDE ot_hbm_svc_sm_group by ot_hbm_svc_sm_issuer (reserve/start/go) '
         'and the feed programme (read/retire); hardware-issued bench rtl/hbm_accel/loader/service_native/run_sm_groups_issued.sh'),
 'phy': ('RETIRED_BY_PHY_ONLY', 'W loader port (w_v/w_addr/w_len/w_tag/wr_rdy) belonged to the modelled controller of '
         'ot_hbm3e_phy_v41x; the PHY-only abstract ot_hbm3e_phy_rc_e8p5 has row/column/data pins only. Host writes to HBM '
         'go through a controller K port: OPEN (host loader, H-DIE host_cp)'),
 'delivery': ('OPEN_H-DIE', 'VM delivery (HBM -> VM dq) has no producer once the bands retire: every PC K port belongs to '
              'an SM group. Needs a static (compiler-windowed) K-port share or dedicated delivery PCs -- H-DIE structural item'),
}
ENGINE_INPUTS = dict(per_group=dict(program_cfg_we=1, program_cfg_addr=10, program_cfg_data=256, desc_we=1, desc_addr=7,
                                    desc_data=256, run_v=1, run_base=7, run_count=8),
                     groups=32, owner='H-DIE host_cp (host loader, placeholder window): initialization tables + one launch',
                     note='clock/reset ports excluded; K ports are bound to the controller leaves; sm_packet/sm_command '
                          'drive the SM')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/hbm_die_v15/views_v5/exposed_inputs_engine_1815.json')
    a = ap.parse_args()
    C = json.loads(CONTRACT.read_text())
    ck = {(r['instance'], r['port']) for r in C['clock_roots']}
    rows = [x for x in C['unbound_ports'] if x['direction'] == 'input' and (x['instance'], x['port']) not in ck
            and not re.fullmatch(r'(rst|rst_n|\w*_rst_n|clk\w*)', x['port'])
            and x['required_owner'].startswith('actual PHY service band')]
    by = defaultdict(lambda: dict(ports=0, bits=0, port_names=set()))
    for x in rows:
        k = x['instance'].split('_')[0]
        by[k]['ports'] += 1; by[k]['bits'] += x['unbound_bits']; by[k]['port_names'].add(x['port'])
    groups = {k: dict(ports=v['ports'], bits=v['bits'], disposition=DISP[k][0], why=DISP[k][1],
                      ports_named=sorted(v['port_names'])) for k, v in by.items()}
    pg = ENGINE_INPUTS['per_group']
    eng = dict(ENGINE_INPUTS, ports=len(pg) * 32, bits=sum(pg.values()) * 32)
    out = dict(schema='opentallas.hbm_v15.exposed_inputs_engine.v1', contract=str(CONTRACT.relative_to(ROOT)),
               h_die_inputs_before=dict(ports=len(rows), bits=sum(x['unbound_bits'] for x in rows)),
               groups=groups,
               remaining_h_die_open=dict(ports=sum(g['ports'] for g in groups.values() if g['disposition'].startswith('OPEN')),
                                         bits=sum(g['bits'] for g in groups.values() if g['disposition'].startswith('OPEN'))),
               engine_inputs=eng,
               rule='bind to a real producer; never tie, stub or alias (owner 10-14 08:05)')
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: (v['ports'], v['bits'], v['disposition']) for k, v in groups.items()}), out['remaining_h_die_open'], eng['ports'], eng['bits'])


if __name__ == '__main__':
    main()
