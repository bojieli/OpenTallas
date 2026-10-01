#!/usr/bin/env python3
"""Model-first analytical interface predicates at W11 conditional coordinates.

Never generates a placement, PG database, route, RTL or headline model. Candidate
PG means a source-derived untrimmed stripe envelope, not actual generated PG.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from decimal import Decimal
import w10_allport_access_audit as A
import w10_connected_escape_audit as E
import w10_fullmap_slot_fit as S

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('results/uarch/w10_conditional_interface_r1')
PHASE=Path('results/uarch/w11_conditional_pin_phase_20261001/audit.json')
LOCAL=Path('results/uarch/w10_baseline_wake/local_fit_r1/audit.json')
SLOT=Path('results/uarch/w10_baseline_wake/slot_fit_r1/model.json')
PDN=Path('physical/abi3/w10_wake_pdn.tcl')


def candidate_stripes(pdn,core, pitch_override=None):
    m=re.search(r'add_pdn_stripe -grid \{top\} -layer \{M5\} -width \{([\d.]+)\} -spacing \{([\d.]+)\} -pitch \{([\d.]+)\} -offset \{([\d.]+)\}',pdn)
    if not m:raise ValueError('unsupported source PDN stripe definition')
    width,space,pitch,offset=map(E.nm,m.groups())
    if pitch_override is not None:pitch=pitch_override
    # Power/ground order is deliberately not inferred. Union geometry only.
    xlo,ylo,xhi,yhi=core; shapes=[]
    for i in range(math.ceil((xhi-xlo)/pitch)+1):
        for phase in range(2):
            cx=xlo+offset+i*pitch+phase*(width+space)
            rect=(cx-width//2,ylo,cx+width//2,yhi)
            if rect[0]<xlo or rect[2]>xhi:continue
            shapes.append(dict(rect_nm=rect,center_x_nm=cx,phase=phase,index=i))
    return shapes


def source_rect_bound(tech,name):
    body=E.layer(tech,name)
    fields=[]
    for key in ('LEF58_SPACING','LEF58_CORNERSPACING','LEF58_EOLKEEPOUT'):
        value=re.search(r'PROPERTY '+key+r' "(.*?)"',body,re.S)
        if not value:raise ValueError('missing actual rectangular rule '+key)
        fields.extend(math.ceil(Decimal(x)*1000) for x in re.findall(r'(?<![A-Za-z])[0-9]+\.[0-9]+',value[1]))
    return max(fields)


def inputs():
    phase=json.loads((ROOT/PHASE).read_text());local=json.loads((ROOT/LOCAL).read_text());slot=json.loads((ROOT/SLOT).read_text())
    dims,ports,obs=A.parse_lef((ROOT/A.LEF).read_text())
    _,via,tracks,_,historical=A.read_inspection((ROOT/A.DIR/'inspection.log').read_text())
    return phase,local,slot,dims,ports,obs,via,tracks,historical


def size():
    phase,local,slot,dims,ports,obs,via,tracks,historical=inputs()
    b=S.budget()
    for key,value in b.items():
        if slot['minimum_site_budget'][key]!=value:raise ValueError('current slot budget disagrees; parent reprice required')
    if local['capture_flops']!=1088 or len(local['icg_gates'])!=8:raise ValueError('fullmapped boundary changed')
    if any(e['conservative_bundle_packing_min_width_sites_in_actual_pin_band']!=192 for e in local['edge_budgets']):
        raise ValueError('conditional capture corridor changed')
    core=(2160,2160,2160+round(b['core_um'][0]*1000),2160+round(b['core_um'][1]*1000))
    pg=candidate_stripes((ROOT/PDN).read_text(),core)
    tech=(ROOT/E.OUT/'actual_db.lef').read_text();rules=E.parse_rules(tech)
    wide_spacing=rules['M5']['prl_rows'][-1]['spacing_nm']
    block_margin=60+12+max(wide_spacing,source_rect_bound(tech,'M5'))
    # Verify this source-derived lattice against historical wire observations;
    # this verifies stripe algebra, never transfers those shapes to the candidate.
    old_centers={sum(p['rect_nm'][i] for i in (0,2))//2 for p in historical if p['layer']=='M5' and p['kind']=='wire' and p['rect_nm'][2]-p['rect_nm'][0]==120}
    derived={p['center_x_nm'] for p in pg}
    if not old_centers or not old_centers<=derived:raise ValueError('PDN lattice lacks historical centreline witness')
    channels=[]
    for m in phase['conditional']['macros']:
        for side in ('left','right'):
            edge=m['bbox_nm'][0 if side=='left' else 2]
            xlo,xhi=(edge-13824,edge) if side=='left' else (edge,edge+13824)
            o,p=tracks['M5','X'];xs=range(o+math.ceil((xlo-o)/p)*p,xhi+1,p)
            candidates=list(xs)
            free=[x for x in candidates if all(abs(x-q['center_x_nm'])>=block_margin for q in pg)]
            channels.append(dict(macro=m['name'],side=side,channel_nm=[xlo,xhi],M5_centrelines=len(candidates),
                after_120nm_PG_72nm_spacing_24nm_wire=len(free),necessary_ports_per_edge=144,
                one_dimensional_count_sufficient=len(free)>=144,
                scope='Geometric centreline count only; simultaneous paths and capture/mux endpoints not assigned'))
    return dict(schema='opentallas.w10.conditional_interface.sizing.v1',verdict='MODEL_FIRST_NECESSARY_BOUND_ONLY',
        current_fixed_density_budget=b,current_slot_model_sha256=A.sha(ROOT/SLOT),
        capture_localfit_sha256=A.sha(ROOT/LOCAL),phase_sha256=A.sha(ROOT/PHASE),
        core_bbox_nm=core,channels=channels,port_instances=1152,capture_flops=1088,physical_ICGs=8,
        additions=dict(extra_registers=0,extra_placed_cells=0,extra_memory_ports=0,extra_latency_cycles=0,
            note='Analytical escape geometry only; no capture area double count, no clock buffer reserve invented'),
        capture_boundary=dict(width_sites=192,width_nm=10368,corridor120_overflow_retained=True,
            mux_site_bins='Use existing named FF+AO21+NOR certificates; no rerun/replication or placement emitted'),
        icg_endpoint_loads_ff=[g['total_endpoint_CLK_capacitance_ff'] for g in local['icg_gates']],
        clock_buffer_sites_skew_slew_and_SSFF='MISSING; pre-CTS loads do not qualify clock trees',
        source_sha256={str(p):A.sha(ROOT/p) for p in [PDN,E.OUT/'actual_db.lef',Path('tools/w10_fullmap_slot_fit.py'),Path('tools/w10_conditional_interface_audit.py')]},
        headline_rates_changed=False,physical_admission=False,model_generator_sha256=A.sha(ROOT/'tools/uarch_model.py'))


def macro_power(lef,dims,macros):
    records=[]
    for net in ('VDD','VSS'):
        body=re.search(r'\bPIN '+net+r'\n(.*?)\n  END '+net,lef,re.S)[1]
        for m in macros:
            for r in A.rects(body):records.append(dict(net=net,macro=m['name'],rect_nm=A.transform(r,dims,m)))
    return records


def audit(model):
    expected=json.loads(json.dumps(size()))
    if model!=expected:raise ValueError('sizing receipt mismatch: model first required')
    phase,local,slot,dims,ports,obs,via,tracks,_=inputs()
    macros=phase['conditional']['macros']
    shapes=E.escape_shapes(ports,dims,macros,tracks,via)
    pg=candidate_stripes((ROOT/PDN).read_text(),tuple(model['core_bbox_nm']))
    power=macro_power((ROOT/A.LEF).read_text(),dims,macros)
    tech=(ROOT/E.OUT/'actual_db.lef').read_text()
    rules=E.parse_rules(tech)
    E.validate_source_rules(rules,(ROOT/E.OUT/'applicable_rules.log').read_text())
    records=[]
    for i,s in enumerate(shapes):
        pin=s['pin_nm'];m4=s['rects']['M4'];m5=s['rects']['M5'];cut=s['rects']['V4']
        checks=dict(connected_pin_union_RECTONLY=A.check(A.contained(pin,m4),pin_nm=pin,patch_nm=m4,
            scope='This isolated pin/patch union is a rectangle: exact-build rectOnly checker returns for one maximal rectangle; no exemption assumption'),
            M4_union_widthtable=A.check(E.width(m4)==24 and A.contained(pin,m4),width_nm=E.width(m4),
                scope='Only isolated union; full net geometry at cell endpoints absent'),
            same_fixed_density_boundary=A.check(A.contained(m4,model['core_bbox_nm']) and A.contained(m5,model['core_bbox_nm']),core_nm=model['core_bbox_nm']))
        for l in ('M4','M5'):
            r=s['rects'][l];area=(r[2]-r[0])*(r[3]-r[1])
            side=min(cut[0]-r[0],r[2]-cut[2]);end=min(cut[1]-r[1],r[3]-cut[3])
            checks[l+'_area']=A.check(area>=2000,area_nm2=area,required_nm2=2000)
            checks[l+'_ordinary_enclosure']=A.check((side>=11 and end>=0) or (end>=11 and side>=0),side_nm=side,end_nm=end,ordinary_rule_nm=[11,0])
            peer=[];bound=source_rect_bound(tech,l)
            for j,o in enumerate(shapes):
                if i==j:continue
                gap=A.gap(r,o['rects'][l])
                # 48nm sufficient envelope includes known convex corner and
                # EOL keepout extensions, beyond 40nm EOL-end spacing.
                if gap<bound:peer.append(dict(peer=o['macro']+':'+o['port'],gap_nm=gap,rect_nm=o['rects'][l]))
            checks[l+'_peer_EOL_corner_keepout_bound']=A.check(not peer,conflicts=peer,bound_nm=bound,
                rule_width_threshold_nm=25,patch_end_width_nm=24,
                scope='Conservative sufficient envelope for these simple rectangles only; no actual full-net DRC verdict')
        m4_pg=[dict(p,gap_nm=A.gap(m4,p['rect_nm'])) for p in power if A.gap(m4,p['rect_nm'])<72]
        m5_pg=[dict(p,gap_nm=A.gap(m5,p['rect_nm'])) for p in pg if A.gap(m5,p['rect_nm'])<72]
        checks['M4_macro_power_PRL_bound']=A.check(not m4_pg,conflicts=m4_pg,bound_nm=72,
            scope='Transformed original macro power ports only; generated intermediate PG metal missing')
        checks['M5_source_stripe_PRL_bound']=A.check(not m5_pg,conflicts=m5_pg,bound_nm=72,
            scope='Source-derived untrimmed120nm stripe envelope, not generated candidate PG')
        other_cuts=[dict(peer=o['macro']+':'+o['port'],rect_nm=o['rects']['V4'],gap_nm=A.gap(cut,o['rects']['V4'])) for j,o in enumerate(shapes) if i!=j and A.gap(cut,o['rects']['V4'])<34]
        checks['V4_signal_cuts_default_spacing']=A.check(not other_cuts,conflicts=other_cuts,bound_nm=34)
        checks['candidate_generated_PG']=A.missing('Candidate PG trimming/metal extensions, standard-cell supply rails, intermediate via-array M4/V4 footprints and connectivity not generated; historical PG is not reused as proof')
        checks['Vx_EOL_specific_enclosure']=A.missing('Separate EOL class-rule collection; ordinary-checker proof does not waive physical EOL enclosure contract')
        checks['capture_mux_clock_SSFF']=A.missing('Existing192site named certificates are relative bins; no fixed cell pin assignment, buffered clock topology, wire parasitics or contextual SS setup/FF hold')
        records.append(dict(macro=s['macro'],orientation=s['orientation'],port=s['port'],geometry=s['rects'],constraints=checks))
    counts={}
    for r in records:
        for k,v in r['constraints'].items():counts.setdefault(k,Counter())[v['classification']]+=1
    return dict(schema='opentallas.w10.conditional_interface.audit.v1',verdict='NECESSARY_INTERFACE_PROOFS_ONLY_PHYSICAL_HOLD',
        model=model,classifications=counts,records=records,
        authoritative_coordinates=macros,reference_phase_commit='085ea91bb9faf67378e0380581f6a8a2ec7e412b',
        historical_refutations_retained=True,new_PnR=False,full_legal_access_proved=False,physical_admission=False,
        source_sha256={str(p):A.sha(ROOT/p) for p in [PHASE,LOCAL,SLOT,PDN,A.LEF,Path('tools/uarch_model.py'),
            Path('tools/w10_conditional_interface_audit.py'),E.OUT/'actual_db.lef',E.OUT/'applicable_rules.log',
            OUT/'source_semantics.json']})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--size',action='store_true');p.add_argument('--model',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.size:result=size()
    else:
        if not a.model:p.error('--model required before audit')
        result=audit(json.loads(a.model.read_text()))
    records=result.pop('records',None)
    if records is None:payload=json.dumps(result,indent=2)+'\n'
    else:payload=json.dumps(result,indent=2)[:-2]+',\n  "records": [\n'+',\n'.join('    '+json.dumps(r,separators=(',',':')) for r in records)+'\n  ]\n}\n'
    a.output.write_text(payload)

if __name__=='__main__':main()
