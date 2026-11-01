#!/usr/bin/env python3
"""Fix S81 ES PHY power metadata without moving its signal IO contract.

Usage: delta_es_pg_parts_1101.py CURRENT_PLAN IO_REFERENCE_PLAN
The reference is the canonical plan before the rejected e7a458702 candidate.
The exact nested PMA TX/RX leaves define the PG body. Decoder SRAM stays core VDD.
"""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import schema as S
import die_io


def fix(raw, reference):
    before=copy.deepcopy(raw);P=S.Plan(raw)
    io={w['name']:w for w in reference['die']['io']}
    changed=[]
    for d in raw['die']['pg']['domains']:
        if d['name'] not in ('phy_lk_ES0','phy_lk_ES1'):continue
        pn=d['name'][4:];q=P.parts[pn];t=P.ptype(pn)
        logical=next(c for c in t['contents'] if c['inst']=='u_phy')
        parts=[r for r in logical['physical_parts'] if r['physical_master'] in ('ot_s81_pma_txm','ot_s81_pma_rxm')]
        assert len(parts)==2 and len({r['physical_master'] for r in parts})==2
        d['phy_macro_binding']=dict(part=pn,inst=logical['inst'],module=logical['module'],
                                    physical_parts=[r['physical_inst'] for r in parts])
        d['phy_macro_um']=[round(v,4) for v in die_io.bound_phy_macro(P,d)['rect_um']]
        # Keep the existing, measured PHY power-bump footprint. It covers the
        # placed logical lot, while the explicit power body is the actual PMA pair.
        x,y=logical['origin_um'];w,h=logical['outline_um']
        a=P.to_die(pn,(x,y));b=P.to_die(pn,(x+w,y+h))
        d['bumps']['rect_um']=[round(min(a[0],b[0]),4),round(min(a[1],b[1]),4),
                               round(max(a[0],b[0]),4),round(max(a[1],b[1]),4)]
        r=d['rect_um'];x0,y0,x1,y1=P.rect(pn)
        strips=[[x0,y0,x1,r[1]]]
        if x0<r[0]:strips.append([x0,r[1],r[0],y1])
        if r[2]<x1:strips.append([r[2],r[1],x1,y1])
        d['core_strip_um']=[[round(v,4) for v in s] for s in strips]
        for name in d['io']:
            idx=next(i for i,w in enumerate(raw['die']['io']) if w['name']==name)
            raw['die']['io'][idx]=copy.deepcopy(io[name])
        changed.append(dict(domain=d['name'],physical_parts=d['phy_macro_binding']['physical_parts'],
                            actual_phy_um=d['phy_macro_um']))
    assert len(changed)==2
    assert raw['die']['io']==reference['die']['io'],'signal IO contract must stay byte/semantic-identical'
    for key in raw:
        if key!='die':assert raw[key]==before[key],key
    return changed


def main():
    path=Path(sys.argv[1]);text=path.read_text();raw=json.loads(text)
    report=fix(raw,json.loads(Path(sys.argv[2]).read_text()))
    start=text.index(' "die": {');end=text.index(' "partition_types": {',start)
    die=json.dumps({'die':raw['die']},indent=1).splitlines()[1:-1]
    text=text[:start]+'\n'.join(die)+',\n'+text[end:]
    assert json.loads(text)==raw
    path.write_text(text);print(json.dumps(report,indent=1))

if __name__=='__main__':main()
