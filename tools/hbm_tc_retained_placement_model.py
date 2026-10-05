#!/usr/bin/env python3
"""Compose retained text placement metadata into the pending TC model gates.

Candidate FF sites are cell occupancy bounds, not a routed successor or a safe
cut. All parent endpoint costs remain individually bound to their providers.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from hbm_tc_unique_net_sourceplan import full_lef

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'results/uarch/hbm_tc_retained_placement_20261002'
PRIOR = ROOT/'results/uarch/hbm_tc_unique_net_sourceplan_20261002/model.json'
PLATFORM = ROOT/'results/uarch/hbm_tc_geometry_prerequisite_20261001/platform_source.json'


def norm(s): return s.replace('\\', '')


def gaps(intervals, lo, hi):
    end = lo
    result = []
    for a, b in sorted(intervals):
        a, b = max(a, lo), min(b, hi)
        if a > end: result.append((end, a))
        end = max(end, b)
    if end < hi: result.append((end, hi))
    return result


def pin_position(c, master, pin):
    rs = master['pins'][pin]['rectangles']
    if not rs: raise ValueError('missing pin rectangles')
    # Use the first physical access rectangle, explicitly retaining that choice.
    a,b,x,y = rs[0]['rect_um']; px,py=(a+x)/2,(b+y)/2
    w,h=master['size_um']
    if c[4]=='FS': py=h-py
    elif c[4]=='FN': px=w-px
    elif c[4]=='S': px,py=w-px,h-py
    elif c[4]!='N': raise ValueError('unsupported orientation')
    return [c[2]/1000+px,c[3]/1000+py]


def placement(d, masters, lanes):
    comps = {norm(c[0]):c for c in d['components']}
    unknown=sorted({c[1] for c in comps.values()}-masters.keys())
    if unknown: raise ValueError('unknown masters '+str(unknown))
    rows=[]
    for s in d['header']:
        m=re.match(r'ROW \S+ \S+ (\d+) (\d+) (\S+) DO (\d+) BY 1 STEP (\d+) 0',s)
        if m: rows.append(tuple([int(m[1]),int(m[2]),m[3],int(m[4]),int(m[5])]))
    occupied=defaultdict(list); mandatory=defaultdict(list); no_decap=defaultdict(list)
    removed=Counter(); master_counts=Counter(); decaps=defaultdict(list)
    for c in comps.values():
        w,h=masters[c[1]]['size_um']; w,h=round(w*1000),round(h*1000)
        if h!=270: raise ValueError('multi-row master requires interval extension')
        occupied[c[3]].append((c[2],c[2]+w));master_counts[c[1]]+=1
        if c[1].startswith('FILLER'): removed[c[1]]+=1
        else: mandatory[c[3]].append((c[2],c[2]+w))
        if not c[1].startswith(('FILLER','DECAP')): no_decap[c[3]].append((c[2],c[2]+w))
        if c[1].startswith('DECAP'): decaps[c[3]].append((norm(c[0]),c[1],c[2],c[2]+w))
    endpoint_nets={}
    for record in d['selected_nets']:
        head=record.split('+',1)[0]
        pairs=[(norm(n),pin) for n,pin in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',head) if norm(n) in comps]
        drivers=[dict(instance=n,pin=pin,first_access_center_um=pin_position(comps[n],masters[comps[n][1]],pin)) for n,pin in pairs if masters[comps[n][1]]['pins'].get(pin,{}).get('direction')=='OUTPUT']
        net=re.match(r'-\s+(\S+)',record)[1]
        for n,pin in pairs:
            if pin in ('D','CLK'): endpoint_nets[(n,pin)]=dict(net=net,drivers=drivers,connection_count=len(pairs),route_provider='selected_nets in placement.json.gz')
    free_sites=[]; conditional_sites=[]; actual_gaps=[]; removable_gaps=[]; decap_gaps=[]
    # Largest pinned standard-cell FF: 1.404 x .270 um (26 x one site).
    width=1404
    for x,y,o,n,step in rows:
        hi=x+n*step
        for a,b in gaps(occupied[y],x,hi): actual_gaps.append([a,y,b,y+270])
        for a,b in gaps(mandatory[y],x,hi):
            removable_gaps.append([a,y,b,y+270])
            start=x+((a-x+step-1)//step)*step
            for xx in range(start,b-width+1,width): free_sites.append((xx,y,o))
        for a,b in gaps(no_decap[y],x,hi):
            decap_gaps.append([a,y,b,y+270])
            start=x+((a-x+step-1)//step)*step
            for xx in range(start,b-width+1,width): conditional_sites.append((xx,y,o))
    lane_data=[]; used=set(); conditional_used=set()
    for lane in range(lanes):
        rx=re.compile(r'(?:^|\.)g_lane\['+str(lane)+r'\]\.u_mul\.s1_e\[\d+\]\$_DFF_P_$')
        endpoints=[(n,c) for n,c in comps.items() if rx.search(n)]
        if len(endpoints)!=11: raise ValueError('lane exponent endpoint count')
        positions=[pin_position(c,masters[c[1]],'D') for n,c in endpoints]
        center=[sum(v[i] for v in positions)/len(positions) for i in (0,1)]
        candidates=sorted((s for s in free_sites if s[:2] not in used),key=lambda s:abs(s[0]/1000+.702-center[0])+abs(s[1]/1000+.135-center[1]))[:40]
        used.update(s[:2] for s in candidates)
        conditional=sorted((s for s in conditional_sites if s[:2] not in conditional_used),key=lambda s:abs(s[0]/1000+.702-center[0])+abs(s[1]/1000+.135-center[1]))[:40]
        conditional_used.update(s[:2] for s in conditional)
        affected={n:(master,a,b) for x,y,o in conditional for n,master,a,b in decaps[y] if a<x+width and b>x}
        lane_data.append(dict(lane=lane,existing_s1_e_D_pins=[dict(instance=n,pin='D',first_access_center_um=p,data_net=endpoint_nets.get((n,'D')),clock_net=endpoint_nets.get((n,'CLK'))) for (n,c),p in zip(endpoints,positions)],
            candidate_FF_sites_dbu=[list(s) for s in candidates],requested_sites=40,
            conditional_decap_release_FF_sites_dbu=[list(s) for s in conditional],
            conditional_sites_status='REQUIRES_EXPLICIT_DECAP_REPLACEMENT_BUDGET_AND_POWER_INTEGRITY_EVIDENCE_NOT_FREE_SPACE',
            conditional_decap_instances_to_replace=sorted(affected),
            conditional_decap_removed_full_cell_area_um2=sum((b-a)*270/1e6 for master,a,b in affected.values()),
            largest_site_center_distance_from_exponent_centroid_um=max((abs(s[0]/1000+.702-center[0])+abs(s[1]/1000+.135-center[1]) for s in candidates),default=None),
            candidate_status='FILLER_REMOVAL_CELL_OCCUPANCY_ONLY_NOT_SAFE_CUT',
            missing=['predecode output cone/pin binding','signal route/via keepout intersection','clock branch load/skew after 40 new FF','FF min-delay paths/repair margin']))
    critical={}
    rptdir=ROOT/'results/physical_abi3/asap7/gpu/w13_tc_col_signoff_failure_20261001T2110Z/run'
    if lanes==32:
        for corner in ['ss_max','ff_min']:
            p=rptdir/('corner_'+corner+'.rpt');text=p.read_text()
            pins=re.findall(r'[\^v]\s+(\S+)/(\w+)\s+\(',text)
            critical[corner]=dict(report=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                placed_path_pins=[dict(instance=n,pin=pin,first_access_center_um=pin_position(comps[n],masters[comps[n][1]],pin),endpoint_net=endpoint_nets.get((n,pin))) for n,pin in pins],
                interpretation='existing failed route only; successor parasitics/CTS unknown')
    return dict(master_counts=dict(master_counts),removable_filler_master_counts=dict(removed),
        row_gap_geometry_provider='reproduce from compressed component coordinates and pinned master dimensions',
        genuine_unoccupied_gap_count=len(actual_gaps),pure_filler_removal_gap_count=len(removable_gaps),
        largest_pure_filler_removal_gap_width_um=max((r[2]-r[0])/1000 for r in removable_gaps),
        genuine_unoccupied_area_um2=sum((b-a)*(d-c)/1e6 for a,c,b,d in actual_gaps),
        filler_removal_available_area_um2=sum((b-a)*(d-c)/1e6 for a,c,b,d in removable_gaps),
        conditional_decap_release_area_um2=sum((b-a)*(d-c)/1e6 for a,c,b,d in decap_gaps),
        decap_tie_clock_hold_logic_retained=True,lanes=lane_data,critical_paths=critical,
        alignment_FF_sites_unallocated=19,safe_cut_established=False)


def power(d):
    definitions={}
    for s in d['vias']:
        name=re.match(r'- (\S+)',s)[1];m=re.search(r'ROWCOL (\d+) (\d+)',s)
        definitions[name]=dict(raw_definition=s,cuts_per_placement=int(m[1])*int(m[2]) if m else None)
    result=[]
    for s in d['specialnets']:
        counts=Counter(re.findall(r'\b(?:via\w+|VIA\d+)\b',s));layers=Counter(re.findall(r'(?:ROUTED|NEW) (M\d+) ',s))
        result.append(dict(net=re.match(r'- (\S+)',s)[1],layer_path_tokens=dict(layers),via_placement_counts=dict(counts),
            explicit_generated_array_cuts=sum(v*definitions[k]['cuts_per_placement'] for k,v in counts.items() if k in definitions and definitions[k]['cuts_per_placement'] is not None),
            raw_geometry_provider='placement.json.gz specialnets; exact DEF widths/points/via placements',
            no_track_availability_inferred=True))
    return dict(via_definitions=definitions,nets=result,scope='column routed power only; parent unavailable')


def abstract_binding(d, path):
    lef=full_lef(path.read_text()); matched=[]
    for s in d['pins']:
        if '+ USE SIGNAL' not in s and '+ USE CLOCK' not in s: continue
        name=norm(re.match(r'- (\S+)',s)[1])
        p=re.search(r'\+ (?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\S+)',s)
        if p[3]!='N': raise ValueError('non-N top pin requires transform')
        rectangles=[]
        for layer,a,b,c,e in re.findall(r'\+ LAYER (\w+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)',s):
            rectangles.append(dict(layer=layer,rect_dbu=[int(a)+int(p[1]),int(b)+int(p[2]),int(c)+int(p[1]),int(e)+int(p[2])]))
        expected=[dict(layer=r['layer'],rect_dbu=[round(v*1000) for v in r['rect_um']]) for r in lef['pins'][name]['rectangles']]
        if rectangles!=expected: raise ValueError('terminal abstract pin mismatch '+name)
        matched.append(name)
    signal_count=sum(v['use'] not in ('POWER','GROUND') for v in lef['pins'].values())
    if len(matched)!=signal_count: raise ValueError('terminal abstract incomplete signal pin binding')
    return dict(terminal_LEF_path=str(path.relative_to(ROOT)),terminal_LEF_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        exact_signal_pin_rectangles_matched=len(matched),power_not_compared_to_clipped_abstract=True)


def build():
    prior=json.loads(PRIOR.read_text()); platform=json.loads(PLATFORM.read_text()); observations=json.loads((DEST/'source_observations.json').read_text())
    text=platform['files']['lef/asap7sc7p5t_28_R_1x_220121a.lef']['text']
    masters={n:full_lef('MACRO '+n+body) for n,body in re.findall(r'MACRO\s+(\S+)(.*?)END\s+\1',text,re.S)}
    for n,body in re.findall(r'MACRO\s+(\S+)(.*?)END\s+\1',text,re.S):
        for pin,pinbody in re.findall(r'\bPIN\s+(\S+)\s+(.*?)\n\s*END\s+\1(?:\s|$)',body,re.S):
            m=re.search(r'DIRECTION\s+(\w+)',pinbody)
            if m: masters[n]['pins'][pin]['direction']=m[1]
    models={}
    for label,lanes in [('DS',16),('Qwen',32)]:
        p=DEST/(label+'_placement.json.gz');d=json.loads(gzip.decompress(p.read_bytes()))
        archive='w13_tc16_terminal_20261001T120346Z' if label=='DS' else 'w13_tc_col_terminal_20261001T2112Z'
        block='ot_gpu_tc16' if label=='DS' else 'ot_gpu_tc_col'
        lef=ROOT/f'results/physical_abi3/asap7/gpu/{archive}/records/results/physical_abi3/asap7/chip/abstracts/{block}/{block}.lef'
        models[label]=dict(metadata_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),def_sha256=d['sha256'],
            def_path=d['path'],stable_read=d['stable_read'],counts=d['category_counts'],sections=d['parsed_counts'],
            actual_tracks=[s for s in d['header'] if s.startswith('TRACKS ')],
            placement=placement(d,masters,lanes),power=power(d),terminal_abstract_binding=abstract_binding(d,lef),
            source_binding='archived same-job report matches and every terminal signal pin rectangle matches; Qwen config/constraints also match; DEF hash newly observed, no historical DEF hash')
    files=observations['files']
    expected={'tc_col_13/config.mk':'a0a5b41104bc232bb73d1eed6c0d4b5c5bbc2c70a1c2df8fb8a14d36b6e33d4e',
        'tc_col_13/constraint.sdc':'00f50660ac54c896e66005fd2ee7534076714a035c58870120efd3a0a8801cdf',
        'tc_col_13/logs/asap7/chip_ot_gpu_tc_col/base/6_report.json':'85fb2ba36d6422acb0e6a3b03f55317ee8b5bde74a07802e979a8f81afa20a71',
        'tc16_12/reports/asap7/chip_ot_gpu_tc16/base/6_finish.rpt':'923fd20c6dbfd6f348d4dbbbf1da3e725f2d5cd674c0ae8178b57b48a34dba02'}
    for k,v in expected.items():
        if files[k]['sha256']!=v: raise ValueError('retained binding mismatch '+k)
    parent_lef=full_lef(files['sm_v12/views/ot_gpu_tc16.lef']['text'])
    terminal=ROOT/'results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z/records/results/physical_abi3/asap7/chip/abstracts/ot_gpu_tc16/ot_gpu_tc16.lef'
    archived=full_lef(terminal.read_text())
    differing_pins=[k for k,v in archived['pins'].items() if v!=parent_lef['pins'].get(k)]
    events=[]
    for e in prior['event_dependency_plan']:
        if e['model']!='deepseek_v41': continue
        events.append(dict(e,endpoint_cost_status='AWAITING_EXACT_PARENT_ENDPOINT_PROVIDER',
            provider_payload_required=dict(input=['ix/iwf SRAM read output -> lane input staging D/Q readiness and routed endpoints'],
                output=['TC y/ov/otag/fault -> column combine -> stack -> commit/resultvisible endpoints'],
                calendar=['call count/II/service already pinned; expose readiness slack and dependency commit slack']),
            column_metadata_ref='DS_placement.json.gz',wire_delay_not_inferred_from_clock_or_cell_counts=True))
    return dict(schema='hbm-tc-retained-placement-prerequisite-v1',source='000ba0898f5120a66d5905ccff333ebbbe28394d',
        prior_model_sha256=hashlib.sha256(PRIOR.read_bytes()).hexdigest(),platform_sha256=hashlib.sha256(PLATFORM.read_bytes()).hexdigest(),
        reused_program_source_pins=[p for p in prior['pins'] if p['path'].startswith('results/rtl/')],
        extractor_sha256=hashlib.sha256((ROOT/'tools/hbm_tc_retained_def_metadata.py').read_bytes()).hexdigest(),
        model_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_observations_sha256=hashlib.sha256((DEST/'source_observations.json').read_bytes()).hexdigest(),
        archived_binding_hashes=expected,models=models,DS_dependency_endpoint_plan=events,
        parent=dict(absent_paths=[k for k,v in files.items() if not v['exists']],
            old_sm_v12_TC_LEF_sha256=files['sm_v12/views/ot_gpu_tc16.lef']['sha256'],
            terminal_TC_LEF_sha256=hashlib.sha256(terminal.read_bytes()).hexdigest(),
            old_sm_v12_mismatched_TC_pin_count=len(differing_pins),old_sm_v12_mismatched_TC_pins=differing_pins,
            occupancy='NO_SOURCE_MATCHED_PARENT_ROUTED_DEF_RETAINED_AT_RECORDED_PATHS',
            floorplan_PDN_checkpoint_present_but_not_read=True),
        next_source_plan=dict(status='MODEL_INPUT_EXTRACTION_PLAN_ONLY_NO_RUN',
            column_text_remaining='one bounded pass per retained DEF: signal wire/via rectangles intersecting 48 lane candidate sets; retain source net IDs, driver/sink pin access coordinates, decode-cone intermediate net names. Exact predecode semantic mapping needs the same-job synthesis name map if DEF names are anonymous. No physical tools needed.',
            clock='extract selected CTS net CLK connections and library input capacitance; bound 659/1299 new loads and insertion/skew before adding FF; no inherited closure',
            cell_space='existing route has zero vacant row area and pure filler-only gaps at most .162 um; .270-high FF widths >=1.080 um. Conditional per-lane sites require decap replacement, not just filler removal. No architectural impossibility or larger-die adoption follows.',
            hold='source-pinned FF min corner report old deficit 0.9053036098549683 ps; require added minimum delay >= deficit + capture-minus-launch skew delta + explicit guard; predecode does not fix tree bypass',
            parent_provider='owner supplies same-source routed parent DEF or bounded metadata export: macro origins/orientations+LEF hashes, producer/consumer instance/pin coordinates, wire/via rectangles on M4-M9, PDN shapes/vias, clock/hold endpoints; 97 event provider IDs enumerated',
            hold_provider='same-source FF minimum-delay standard-cell libraries plus old SPEF/name map; bounded min-path data for tree bypass and all added FF D/Q/CLK edges, capture-minus-launch skew and guard. Do not derive a hold cell count from .9053 ps alone.',
            optional_floorplan_export='only after owner review: bounded read-only 2_4_floorplan_pdn.odb metadata export; no timing/routes and mismatched TC pins, so cannot substitute for parent route',
            extraction_budgets=dict(text_DEF_bytes=320000000,components=500000,record_bytes=8000000,events=97),
            review_order=['confirm retained DEF provenance','bind actual predecode cone and 19 alignment FF sites','intersect cell sites with signal+PDN/via keepouts','bound new CTS skew/load and FF hold repair','fill all 97 parent event endpoint costs','parent compose both program calendars and review model']),
        failed_unchanged=prior['failed_unchanged'],no_admission=True,no_RTL_PnR_retry=True,no_rate_or_die_adoption=True,
        upper_policy_counterfactuals_preserved=True)


if __name__=='__main__':
    model=build();(DEST/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:dict(counts=v['counts'],genuine_area=v['placement']['genuine_unoccupied_area_um2'],filler_removal_area=v['placement']['filler_removal_available_area_um2'],allocated_candidates=sum(len(l['candidate_FF_sites_dbu']) for l in v['placement']['lanes'])) for k,v in model['models'].items()}))
