#!/usr/bin/env python3
"""QKO-SLICE2 10-21: w12 = w11 (s8 lp: kept FDN selectors, SU reset split, bounded TAP + 6 kept xt_v readers)
with ON-TRACK head-column packing. w10/w11 n691 packing put 12 x leaves in MY/R180 -> REF_TILE macro_grid FAIL
(656 pins off asap7 tracks; no origin fixes it). head_pack3.py (head R0, leaves R0/MX only) is INFEASIBLE at
691.2 and OPTIMAL at 734.4 (max matching-bit 403.686 um, N boundary 390.705 um) -> parent ENLARGED +43.2 um in Y:
2462.376 x 4319.976 (full reticle height is available; QKO-QDIE slot updated).
usage: slice12_kit.py a|b|e|f [--census]   (--census: census-only kit w12c*, station_tail1 x8 + crh_rp1 SOFT from
exact new source; never gated/bound. Gate kits REFUSE without the exact new CLOSED views, as slice11.)"""
import sys,json
CENSUS='--census' in sys.argv
# QE3-SLICE2 10-21: --census-hard = census-only kit w13c/w13cb with EVERY child hard, exactly as the gate kit sees it:
# CRH-RP1 = its CLOSED view (main 61befcda5); station_tail1 x8 = census-only PROXY view (stn_census_proxy.py: CLOSED
# stnrgc g3 abstract renamed; identical 19 ports / pin regions / 151.2 outline) until the station closes. Never gated/bound.
CHARD='--census-hard' in sys.argv
import slice11_kit as k
import slice10_kit as s10
g=k.g
P=json.loads((k.R/'results/arch/codex_slice2_native_1021/head_pack/o734.4.json').read_text())
assert P['status']=='OPTIMAL' and P['independent_matching_bit_max_um']<=405 and P['independent_N_boundary_max_um']<=405
assert all(q['orientation'] in (0,2) for q in P['placements'].values())
s10.PACK=P
g.H=round(g.H+43.2,3)
base={'a':'qfd_dv_slice2_w12','b':'qfd_dv_slice2_w12b','e':'qfd_dv_slice2_e12','f':'qfd_dv_slice2_e12b'}[g.V]
g.NAME=base.replace('_w12','_w12c').replace('_e12','_e12c') if CENSUS else base
if CHARD:g.NAME=base.replace('_w12','_w13c').replace('_e12','_e13c')
if CENSUS:
    old=g.children
    def children():
        return [c for c in old() if not (c['inst'].startswith('u_r') and c['inst'][3:].isdigit()) and 'crh' not in c['view']]
    g.children=children
    for s in range(8):g.SOFT.setdefault(f'r_st{s}',[]).append(f'u_r{s}')
def main():
    if CENSUS:g.main()
    else:k.main()
    if CHARD:
        p=k.R/f'{g.SPEC_DIR}/{g.NAME}.json';s=json.loads(p.read_text())
        s['diagnostic']='CENSUS-ONLY (QE3-SLICE2): all children hard; station_tail1 = census proxy view (g3 abstract renamed). Never gated/bound.'
        p.write_text(json.dumps(s,indent=1)+'\n')
    p=k.R/f'{g.SPEC_DIR}/{g.NAME}.json';s=json.loads(p.read_text())
    s['structural_change']=('CENSUS-ONLY (not a gate kit): station_tail1 x8 + crh_rp1 soft from exact new source. ' if CENSUS else '')+('CENSUS-ONLY HARD (not a gate kit): station proxy view. ' if CHARD else '')+\
        'On-track head-column packing o734.4 (leaves R0/MX), parent +43.2 um Y (4319.976). '+s.get('structural_change','')
    p.write_text(json.dumps(s,indent=1)+'\n')
if __name__=='__main__':main()
