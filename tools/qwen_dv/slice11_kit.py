#!/usr/bin/env python3
"""Exact w10 hard-pin geometry + recovered actual1/1/RP1/ARF1 split s8 source.
Requires independently CLOSED qfd_dv_s8_crh_rp1 before ref_tile gen/gate.
No old CRH view fallback. Does not launch layout or alter schedule defaults.
"""
import json
from pathlib import Path
import slice10_kit as h
import gen_slice8_lp_spec as src
g=h.g
R=Path(__file__).resolve().parents[2]
g.NAME={'a':'qfd_dv_slice2_w11','b':'qfd_dv_slice2_w11b','e':'qfd_dv_slice2_e11','f':'qfd_dv_slice2_e11b'}[g.V]
oldchildren=set(g.g6.CHILD_SOURCES)
g.g6=src
g.LPN='qfd_dv_s8b' if g.GEOB else 'qfd_dv_s8'
g.TOP=g.LPN+'_lp'
g.LP_SPEC=f'tools/landed_parent/specs/{g.LPN}.json'
g.REC=f'{src.REC_DIR}/{g.TOP}_record.json'
g.SOURCES=[f'{src.OUT_DIR}/{g.TOP}.sv']+[p for p in g.SOURCES[1:] if p not in oldchildren]+src.CHILD_SOURCES
g.KEEP=[p.replace('qfd_dv_s5_vm8q','qfd_dv_s8_vm8q_rp1') for p in g.KEEP]
g.SOFT['r_ctl']=g.SOFT['r_ctl']+['u_rp']
g.VSTN='physical/ref_tile/qfd_dv_s8_station_tail1/views/qfd_dv_s8_station_tail1'
g.VVM8['crh']='physical/ref_tile/qfd_dv_s8_crh_rp1/views/qfd_dv_s8_crh_rp1'

def main():
    if not (R/g.VVM8['crh']/'qfd_dv_s8_crh_rp1.lef').exists():
        raise SystemExit('HOLD exact new RP1 CRH CLOSED view absent; old CRH alias forbidden')
    if not (R/g.VSTN/'qfd_dv_s8_station_tail1.lef').exists():
        raise SystemExit('HOLD exact LASTK-tail station CLOSED view absent; old station alias forbidden')
    g.main()
    p=R/f'{g.SPEC_DIR}/{g.NAME}.json';s=json.loads(p.read_text())
    for b in s['job']['benches']:
        b['cmd']=b['cmd'].replace('run_s7.sh','run_s8.sh')
        b['name']=b['name'].replace('s6_','s8_')
    s['job']['branch']='codex/q-slice2-rp-1021'
    s['structural_change']='S8 exact closed leaf READ1/FILL1 simulation; recovered existing RP1/ARF1 with real new CRH1 source. No old CRH view alias. '+s['structural_change']
    s['safe_design_checklist']['8_schedule']='OWED measured selected187landing programme ages; added STM->RPctl->SU crossing and3/5edge pad explicit in lagref. No inherited187/248 or projected192/253 claim.'
    p.write_text(json.dumps(s,indent=1)+'\n')
if __name__=='__main__':main()
