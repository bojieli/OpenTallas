#!/usr/bin/env python3
"""QKO-SLICE2 10-21: CENSUS-ONLY w11c/w11cb kit = slice11 (s8 lp: kept FDN selectors, SU reset split,
bounded TAP + six kept xt_v readers) with the two not-yet-CLOSED successors (qfd_dv_s8_station_tail1 x8,
qfd_dv_s8_crh_rp1) synthesized SOFT from their exact new source instead of hard views.
Never gated, never bound: soft synthesis only makes the parent native census stricter (their internal
nets are counted too). The gate kits stay slice11_kit.py w11/w11b, which still REFUSE without the exact new views."""
import sys
V=sys.argv[1]
import slice11_kit as k
g=k.g
g.NAME={'a':'qfd_dv_slice2_w11c','b':'qfd_dv_slice2_w11cb'}[V]
old=g.children
def children():
    out=[]
    for c in old():
        if c['inst'].startswith('u_r') and c['inst'][3:].isdigit():continue
        if 'crh' in c['view']:continue
        out.append(c)
    return out
g.children=children
for s in range(8):
    g.SOFT.setdefault(f'r_st{s}',[]).append(f'u_r{s}')
if __name__=='__main__':
    g.main()
    import json
    p=k.R/f'{g.SPEC_DIR}/{g.NAME}.json';s=json.loads(p.read_text())
    s['structural_change']='CENSUS-ONLY (not a gate kit): station_tail1 x8 + crh_rp1 soft from exact new source. '+s.get('structural_change','')
    p.write_text(json.dumps(s,indent=1)+'\n')
