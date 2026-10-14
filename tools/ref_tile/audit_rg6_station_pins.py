#!/usr/bin/env python3
"""Audit immutable RG6 regional/band candidates against exact actual ETM pins.

No SS wire coefficient is inferred. TT0.76 and FF0.112 remain separately labelled
budget calibrations. Direct O-R/S+R values are kept distinct from producer sides
which additionally include explicit boundary-extrema adjustments.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--region-root', type=Path, required=True)
    p.add_argument('--band-root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
    import pinreg_audit as A
    rd=a.region_root/'results/arch/qwen_tp8_1012'
    bd=a.band_root/'results/arch/qwen_tp8_1012'
    rf=rd/'vm_joint_g1_boundary_station_candidate.json'
    pf=bd/'vm_band_boundary_packet_codex.json.gz'
    sf=bd/'vm_band_joint_selected_pinmap_codex.json'
    region=json.loads(rf.read_text()); packet=json.load(gzip.open(pf,'rt')); selected=json.loads(sf.read_text())
    assert selected['regional_packet_sha256']==sha(rf)
    summary=json.loads((bd/'vm_band_boundary_packet_codex.json').read_text())
    assert summary['packet']['sha256']==sha(pf)
    frozen_hashes=summary['view_hashes']; tables={}; sides={}; view_hashes={}; rows=[]
    def side(view,pin,corner):
        key=f'{view}|{pin}|{corner}'
        if key in sides:return key
        tkey=view,corner
        if tkey not in tables:
            vd=a.region_root/view
            f=next(vd.glob(f'*_{corner}.lib')); ins=vd/'insertion.json'
            for z in (f,ins):
                rel=str(z.relative_to(a.region_root)); view_hashes[rel]=sha(z)
                assert frozen_hashes[rel]==sha(z),f'stale bound view {z}'
            lib=A.parse_lib(f); refs=A.clock_refs(lib,json.loads(ins.read_text()),corner)
            tables[tkey]=lib,refs
        lib,refs=tables[tkey]; pdata=lib['pins'][pin]
        arcclocks={rel for typ,rel,v in pdata['arcs'] if typ in ('rising_edge','falling_edge') or typ.startswith(('setup_','hold_'))}
        assert len(arcclocks)==1, (view,pin,arcclocks)
        ck=next(iter(arcclocks)); ref=refs[ck]; assert ref['src']=='insertion.json boundary mean'
        R=ref['rise']; O=[]; l=[]; S=[]; H=[]
        for typ,rel,v in pdata['arcs']:
            if typ=='rising_edge':
                vals=[v[k][0] for k in ('cell_rise','cell_fall') if v.get(k)]
                O.extend(vals);l.extend(vals)
            elif typ=='setup_rising':S.extend(x for k in ('rise_constraint','fall_constraint') for x in v.get(k,[]))
            elif typ=='hold_rising':H.extend(x for k in ('rise_constraint','fall_constraint') for x in v.get(k,[]))
            elif typ in ('falling_edge','setup_falling','hold_falling'):raise ValueError('unsupported edge in same-rising candidate')
        sides[key]={'view':view,'pin':pin,'corner':corner,'clock':ck,'R_ps':R,'boundary_min_ps':ref['bmin'],'boundary_max_ps':ref['bmax'],
                    'O_ps':max(O) if O else None,'l_raw_ps':min(l) if l else None,'S_ps':max(S) if S else None,'h_raw_ps':max(H) if H else None,
                    'o_ps':max(O)-R if O else None,'l_ps':min(l)-R if l else None,'s_ps':max(S)+R if S else None,'h_ps':max(H)-R if H else None}
        return key
    def verify_packet(record,record_corner):
        k=side(record['view'],record['pin'],record_corner); actual=sides[k]
        assert abs(record['R_ps']-actual['R_ps'])<1e-6
        # Preserve producer's explicit extrema extras, but never call them raw O-R.
        expected={'o_ps': None if actual['o_ps'] is None else actual['o_ps']+actual['boundary_max_ps']-actual['R_ps'],
                  's_ps': None if actual['s_ps'] is None else actual['s_ps']+actual['R_ps']-actual['boundary_min_ps'],
                  'l_ps': None if actual['l_ps'] is None else actual['l_ps']+actual['boundary_min_ps']-actual['R_ps'],
                  'h_ps': None if actual['h_ps'] is None else actual['h_ps']+actual['R_ps']-actual['boundary_max_ps']}
        for field,value in expected.items():
            assert (value is None and record[field] is None) or abs(value-record[field])<1e-5,(record['pin'],field,value,record[field])
        return k
    def hop(kind,lane,bit,launch,capture,Axy,Bxy,context):
        L=sum(abs(x-y) for x,y in zip(Axy,Bxy)); corners={}
        for co in ('tt','ff','ss'):
            lk=side(launch['view'],launch['pin'],co);ck=side(capture['view'],capture['pin'],co)
            x=sides[lk];y=sides[ck]
            assert x['o_ps'] is not None and y['s_ps'] is not None and x['l_ps'] is not None and y['h_ps'] is not None
            corners[co]={'launch':lk,'capture':ck,'actual_zero_wire_setup_ps':833.333-210-x['o_ps']-y['s_ps'],
                         'actual_zero_wire_hold_ps':x['l_ps']-y['h_ps']-100}
        corners['tt']['TT_calibrated_0.76_setup_ps']=corners['tt']['actual_zero_wire_setup_ps']-.76*L
        corners['ff']['FF_ideal_0.112_hold_ps']=corners['ff']['actual_zero_wire_hold_ps']+.112*L
        rows.append({'kind':kind,'lane':lane,'bit':bit,'length_um':L,'launch_xy_um':Axy,'capture_xy_um':Bxy,'corners':corners,'context':context})
    old={}
    for e in packet['boundary_edges']:
        if e['region']==1:old[e['lane'],e['bit']]=e
    regionbits={}
    for st in region['stations']:
        for match in st['matches']:
            for b in match['bits']:
                e=old[b['lane'],b['bit']]; idx=int(re.search(r'\[(\d+)\]',b['region1_station_pin'])[1])
                dp=packet['one_stage_relay_actual_pins']['W']['d'][idx]
                dxy=[x+y for x,y in zip(st['at_um'],dp['xy_um'])]
                assert abs(sum(abs(x-y) for x,y in zip(e['launch_xy_um'],dxy))-b['input_hop_manhattan_um'])<1e-6
                for record_corner in ('tt','ff','ss'):
                    verify_packet(e['corner_budgets'][record_corner]['launch'],record_corner);verify_packet(dp['corners'][record_corner],record_corner);verify_packet(b['new_launch_corners'][record_corner],record_corner);verify_packet(b['original_capture_corners'][record_corner],record_corner)
                hop('regional_input',b['lane'],b['bit'],e['corner_budgets']['tt']['launch'],dp['corners']['tt'],e['launch_xy_um'],dxy,{'source_stage':e['launch_stage'],'station':st['name'],'station_pin':dp['corners']['tt']['pin']})
                regionbits[b['lane'],b['bit']]=b,st
    for stage in selected['selected']['stages']:
        kind=stage['relay_kind']
        for b in stage['bits']:
            rb,st=regionbits[b['lane'],b['bit']];pins=packet['one_stage_relay_actual_pins'][kind];idx=b['band_pin_bit'];dp=pins['d'][idx];qp=pins['q'][idx]
            for record_corner in ('tt','ff','ss'):verify_packet(dp['corners'][record_corner],record_corner);verify_packet(qp['corners'][record_corner],record_corner)
            hop('regional_to_bandstation',b['lane'],b['bit'],rb['new_launch_corners']['tt'],dp['corners']['tt'],b['A'],b['D'],{'region_station':st['name'],'band_slot':stage['band_slot'],'relay_kind':kind})
            hop('bandstation_to_target',b['lane'],b['bit'],qp['corners']['tt'],rb['original_capture_corners']['tt'],b['Q'],b['B'],{'band_slot':stage['band_slot'],'target_stage':b['original_capture_stage'],'relay_kind':kind})
    assert len(rows)==2064 and sum(r['kind']=='regional_input' for r in rows)==688
    report={'scope':'Actual per-bit ETM first-load-table-point normalization; candidate-only, no SS wire coefficient, no physical timing qualification. Both O-R/S+R direct and producer boundary-extrema extras independently checked.',
            'inputs':{str(f):sha(f) for f in (rf,pf,sf)},'actual_view_hashes':view_hashes,'setup_reserve_ps':210,'hold_margin_ps':100,'rows':rows,'sides':sides}
    detail=a.out/'pin_audit.json.gz'
    with gzip.open(detail,'wt') as f:json.dump(report,f,separators=(',',':'))
    minima={}
    for kind in ('regional_input','regional_to_bandstation','bandstation_to_target'):
        rr=[r for r in rows if r['kind']==kind];metrics={}
        for co,field in [('tt','TT_calibrated_0.76_setup_ps'),('ff','FF_ideal_0.112_hold_ps'),('ss','actual_zero_wire_setup_ps')]:
            w=min(rr,key=lambda r:r['corners'][co][field]);metrics[field]={'margin_ps':w['corners'][co][field],'lane':w['lane'],'bit':w['bit'],'length_um':w['length_um'],'row_index':rows.index(w)}
        launch=[sides[r['corners']['tt']['launch']]['o_ps'] for r in rr]
        capture=[sides[r['corners']['tt']['capture']]['s_ps'] for r in rr]
        minima[kind]={'bits':len(rr),'actual_first_loadpoint_TT_launch_gt220':sum(x>220 for x in launch),'actual_first_loadpoint_TT_max_launch_ps':max(launch),'actual_first_loadpoint_TT_capture_gt190':sum(x>190 for x in capture),'actual_first_loadpoint_TT_max_capture_ps':max(capture),'metrics':metrics,'max_length_um':max(r['length_um'] for r in rr)}
    summaryout={'scope':report['scope'],'inputs':report['inputs'],'actual_view_hashes':view_hashes,'minima':minima,'detail':{'path':str(detail),'sha256':sha(detail)},'actual_SS_wire_status':'OPEN; no SS wire coefficient or credit invented'}
    (a.out/'summary.json').write_text(json.dumps(summaryout,indent=2)+'\n');print(json.dumps(minima,indent=2))


if __name__=='__main__':main()
