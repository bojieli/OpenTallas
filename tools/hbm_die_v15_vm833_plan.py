#!/usr/bin/env python3
"""v15 833.333-ps VM slice variant plan (owner 10-14 21:35 option a1, static schedule rule 0an).

Source-bound: clock roots come from the v15 source contract; per-element physical state
comes from the committed ref_tile gate results / closed views on the given git ref. No
timing is inferred: an element without a closed 833.333-ps view is listed OPEN.
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIOD = 833.333
# master -> physical leaf kits that implement it at 833.333 ps (static successors only;
# closed 1,111-era vms_bank/vms_hub/vms_rstop views are historical credit RTL, not aliased).
LEAF_KITS = {
    'bank RG5/WG1 (SW, SE)': 'vms_bank_static_rg5wg1_1015',
    'bank RG7/WG3 (NW, NE)': 'vms_bank_static_rg7wg3_1015',
    'LG tap bank leaf (ot_hbm_vm_lg_static_bank, R0 only)': 'vm_lg_bank_hc_static_1015',
}
NO_KIT = ['ot_vms_hub_static (clk_hub)', 'ot_vms_rstop_static/ot_vms_rcl_static ring (clk_ring[2])',
          'replay (clk_replay)', 'hfd_hgi_vm_calendar_static (calendar clk)', 'ot_vms_status4_static',
          'ot_hbm_svc_static_vm_delivery (dq)']


def show(ref, path):
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('contract', type=Path)
    ap.add_argument('--ref', default='origin/main')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.contract.read_text())
    quads = {}
    for q in ('SW', 'SE', 'NW', 'NE'):
        insts = ['hb_vms_' + q, 'calendar_' + q] + [f'lg_{q}_{i}' for i in range(3)]
        roots = [r for r in c['clock_roots'] if r['instance'] in insts]
        bad = [r for r in roots if r['source'] != ['hb_ckgen', 'pll_stream']]
        assert not bad, bad
        by = {}
        for r in roots:
            by.setdefault(f"{r['instance']}.{r['port']}", 0)
            by[f"{r['instance']}.{r['port']}"] += 1
        p = c['instances']['hb_vms_' + q]
        quads[q] = dict(master=p['master'], roots=len(roots), roots_by_port=by,
                        clock='clk_stream 833.333 ps (hb_ckgen.pll_stream), same edge/phase every root',
                        cdc_crossers=0)
    kits = {}
    for role, kit in LEAF_KITS.items():
        g = show(a.ref, f'physical/ref_tile/{kit}/gate_result.json')
        sdc = show(a.ref, f'physical/ref_tile/{kit}/clock.sdc') or ''
        rec = dict(kit=kit, period_ps=PERIOD if f'-period {PERIOD}' in sdc else None)
        if g:
            gr = json.loads(g)
            ck = gr.get('clock', {})
            rec.update(gate_verdict=gr.get('verdict'), cts=gr.get('cts'), max_root_sinks=ck.get('max_root_sinks'),
                       tt_insertion_ps=ck.get('tt_insertion_ps'), tt_spread_ps=ck.get('tt_spread_ps'),
                       warnings=[i['message'] for i in gr.get('items', []) if i.get('severity') == 'WARN'][:4],
                       status='GATED, not routed/closed')
        else:
            views = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '--name-only', a.ref,
                                    f'physical/ref_tile/{kit}/views/'], capture_output=True, text=True).stdout.split()
            rec.update(status='CLOSED view present' if views else 'ABSENT', views=views)
        if rec.get('tt_spread_ps') is not None and rec['tt_spread_ps'] > 80:
            rec['clock_finding'] = (f"spread {rec['tt_spread_ps']} ps > 80 ps at 833.333 ps "
                                    f"({100 * rec['tt_spread_ps'] / PERIOD:.1f}% of the cycle): structural CTS "
                                    "(macro-clock grouping / smaller outline, gate util WARN) before route")
        kits[role] = rec
    plan = dict(schema='opentallas.hbm.v15-vm833-plan.v1', period_ps=PERIOD,
                decision='owner 2026-10-14 21:35 option a1: VM slices on the 833.333-ps engine clock; '
                         'static schedule (0an): no credits/ready on chip; SU<->slice lane CDC crossers removed',
                quadrants=quads, leaf_kits=kits, no_physical_kit_yet=NO_KIT,
                compiler_model=['bank read n+1 sample / n+7 response (bank ABI n+6) for direct groups (DMA back, IDX, COLL)',
                                'LG taps fixed returns SU 10/7, SFU 14/11, HC 18/15 (tap params, contract-asserted)',
                                'every physical relay/station added by the die plan must be added to these counts'],
                pin_decisions=['NW bank: GEO-H candidate B adopted (coordinator 10-15)',
                               'NE: LG-west/attention-east only with D2 central corridor',
                               'SW/SE keep RG5/WG1',
                               'engines: >=4 LG port groups/quadrant (5 on SW/SE), contract engine_lg_port_group_rule'],
                qualification=dict(native=False, TT=False, FF=False, DRC=False),
                next=['bank kits: NW re-pin (B), then CTS structural fix for spread, then route at 833.333',
                      'hub/ring/replay/calendar/status/delivery static leaves: kits (h_vm)',
                      'die chain consumes only CLOSED 833.333 views; nothing aliased from 1,111-era tiles'])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(plan, indent=1) + '\n')
    print(json.dumps({q: v['roots'] for q, v in quads.items()}),
          json.dumps({k: (v.get('status'), v.get('tt_spread_ps')) for k, v in kits.items()}))


if __name__ == '__main__':
    main()
