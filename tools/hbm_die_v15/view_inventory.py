#!/usr/bin/env python3
"""View inventory of the v15 HBM die on compact660_v5 (H-DIE r3, 2026-10-15): for every plan block and every contract
instance, which view a die GRT/STA would bind -- REAL (closed view with LEF + TT/FF Liberty), SYNTH (current-source
synthesized netlist with a real outline: an estimate, never a sign-off view), RUNNING (synthesis in flight), or a gap
(NO_CONTRACT_INSTANCE: the plan block has no master in the source contract; PARTITION: one contract master spans several
plan blocks and has no physical sub-layout yet).  Never a stub.

    view_inventory.py [--synth results/arch/hbm_die_v15/views_v5/synth_runs.tsv] [--out .../inventory.json]
synth_runs.tsv: host, run, top, NL|RUNNING_OR_FAILED, mapped|coarse, std-cell area um2 (SRAM macros excluded)
"""
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json'
CONTRACT = ROOT / 'results/arch/hbm_die_v15/source_contract/contract.json'
CLOSED = {   # master -> closed view dir (LEF + TT/FF ETM of the routed tile, committed on main)
    'ot_hbm3e_phy_v41x_aw30_e8p5': 'physical/asap7_memory_macros/ot_hbm3e_phy_v41x_aw30_e8p5',
    'ot_hbm_svc_static_pc': 'physical/ref_tile/hv15_svc_pc/views/ot_hbm_svc_static_pc',
    'hfd_hgi_vm_calendar_SW': 'physical/ref_tile/hv15_vm_cal_sw/views/hfd_hgi_vm_calendar_SW',
    'hfd_hgi_vm_calendar_SE': 'physical/ref_tile/hv15_vm_cal_se/views/hfd_hgi_vm_calendar_SE',
    'hfd_hgi_vm_calendar_NW': 'physical/ref_tile/hv15_vm_cal_nw/views/hfd_hgi_vm_calendar_NW',
    'hfd_hgi_vm_calendar_NE': 'physical/ref_tile/hv15_vm_cal_ne/views/hfd_hgi_vm_calendar_NE',
    'ot_vms_status4_static': 'physical/ref_tile/hv15_vm_status4_margin1/views/ot_vms_status4_static',
}
# plan block kind -> (contract instances per quadrant pattern, owner, note)
KIND = {
    'phy': (['phy_{q}'], 'H-DIE', 'PHY+controller macro abstract (the allowed modelled hard core)'),
    'pc': (['svc_{q}_s*'], 'HBM-V15-HARDEN', 'band = wires around closed PCs; flattened to PC leaves in the die case'),
    'sm': ([], 'H-ELEM-A', 'SM compact tile (x-load static + attention on SM) not in the source contract'),
    'hc': ([], 'HC owner (H-ELEM-B/HC)', 'HC rows not in the source contract'),
    'sfu': (['hb_sfu_{q}'], 'H-ELEM-B', 'one engine master vs 4 bank-pair plan boxes: physical 4-leaf split requested'),
    'vmb': (['hb_vms_{q}'], 'H-ELEM-A (VM banks)', 'banks live inside hfd_hgi_vms_static_<q>: hub+8 banks need a sub-layout'),
    'vmh': (['hb_vms_{q}', 'calendar_{q}', 'lg_{q}_*', 'delivery_{q}'], 'h_vm / H-ELEM-A', 'VM hub group'),
    'su': (['hb_su_{q}'], 'H-ELEM-B', 'contract SU = VM-port shim only; whole-SU slices RTL pending'),
    'sucore': ([], 'H-ELEM-B', 'whole-SU core RTL pending'),
    'coll': (['hb_coll_{q}'], 'H-COLL', ''),
    'dbk': (['hb_dbk_{q}'], 'DMA owner', ''),
    'quant': (['hb_quant_NW'], 'H-ATTQ', 'one host master vs 4 plan boxes'),
    'idx': (['hb_idx'], 'H-IDX', 'client = 4 scorers (512 CLOSED hslices each) + glue; partition by grants v4'),
    'lk': ([], 'SerDes owner', 'die-to-die link layer not in the source contract'),
    'ep': ([], 'SerDes owner', 'endpoint not in the source contract'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synth', default=str(ROOT / 'results/arch/hbm_die_v15/views_v5/synth_runs.tsv'))
    ap.add_argument('--out', default=str(ROOT / 'results/arch/hbm_die_v15/views_v5/inventory.json'))
    a = ap.parse_args()
    P = json.loads(PLAN.read_text()); C = json.loads(CONTRACT.read_text())
    inst = C['instances']
    synth = defaultdict(list)
    for ln in Path(a.synth).read_text().splitlines():
        h, run, top, nl, mode, area = ln.split('\t')
        synth[top].append(dict(host=h, run=run, state='NETLIST' if nl == 'NL' else 'RUNNING_OR_FAILED', mode=mode,
                               std_area_um2=float(area or 0)))

    def view_of(master):
        if master in CLOSED and (ROOT / CLOSED[master]).exists():
            return dict(view='REAL', dir=CLOSED[master])
        s = synth.get(master, [])
        nl = [x for x in s if x['state'] == 'NETLIST' and x['mode'] == 'mapped']
        if nl:
            return dict(view='SYNTH', runs=nl)
        if any(x['state'] == 'NETLIST' for x in s):
            return dict(view='SYNTH_COARSE_ONLY', runs=s)
        if s:
            return dict(view='RUNNING', runs=s)
        return dict(view='NONE')

    by_inst = {}
    for n, r in inst.items():
        m = r['master']
        v = view_of(m)
        if m.startswith('hfd_svc_v15_'):
            v = dict(view='REAL_COMPOSED', leaves='ot_hbm_svc_static_pc', dir=CLOSED['ot_hbm_svc_static_pc'])
        by_inst[n] = dict(master=m, **v)
    blocks = {}
    for b, g in P.items():
        k = re.match(r'([a-z]+)', b).group(1)
        q = (re.search(r'_(SW|SE|NW|NE)', b) or [None, None])[1]
        pats, owner, note = KIND[k]
        ci = sorted({n for p in pats for n in inst if re.fullmatch(p.replace('{q}', q or '').replace('*', r'\w*'), n)})
        if not ci:
            status = 'NO_CONTRACT_INSTANCE'
        else:
            vs = [by_inst[n]['view'] for n in ci]
            if k in ('vmb', 'sfu', 'quant', 'idx', 'su'):
                status = 'PARTITION'
            elif all(v.startswith('REAL') for v in vs):
                status = 'REAL'
            elif all(v.startswith('REAL') or v == 'SYNTH' for v in vs):
                status = 'SYNTH'
            else:
                status = 'INCOMPLETE'
        blocks[b] = dict(kind=k, status=status, contract_instances=ci, owner=owner, note=note,
                         area_mm2=round(g['w'] * g['h'] / 1e6, 3))
    cnt = Counter(v['status'] for v in blocks.values())
    area = Counter()
    for v in blocks.values():
        area[v['status']] += v['area_mm2']
    res = dict(schema='opentallas.hbm_v15.view_inventory.v1', plan=str(PLAN.relative_to(ROOT)),
               contract=str(CONTRACT.relative_to(ROOT)),
               summary=dict(blocks=len(blocks), by_status=dict(cnt), area_mm2_by_status={k: round(v, 1) for k, v in area.items()},
                            instances=len(inst), instances_by_view=dict(Counter(v['view'] for v in by_inst.values()))),
               rule='REAL = closed LEF + TT/FF ETM; SYNTH = current-source mapped netlist + real outline (estimate); '
                    'no stub, no pin-only shell',
               blocks=blocks, instances=by_inst)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res['summary']))


if __name__ == '__main__':
    main()
