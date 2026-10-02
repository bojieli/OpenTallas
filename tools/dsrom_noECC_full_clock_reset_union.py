#!/usr/bin/env python3
"""Name every retained clock/reset consumer and construct full cell row sites.

This is a deterministic placement preview, not timing-driven placement or CTS.
No root/skew, extracted RC, or area embedding credit follows from row legality.
"""
import gzip, hashlib, json, math, re
from collections import Counter, defaultdict
from pathlib import Path
from dsrom_noECC_enable_distribution import trace, placed, bound
from dsrom_noECC_hold_station_geometry import pin_rects, center
from dsrom_noECC_liberty import cell_bodies, block, library_text
from dsrom_noECC_slew_enable_diagnosis import pin_models

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/uarch/dsrom_noECC_full_clock_reset_union_20261002'
U = ROOT/'results/uarch'
ENABLE = U/'dsrom_noECC_enable_distribution_20261002/model.json'
HOLD = U/'dsrom_noECC_hold_station_geometry_20261002/model.json'
STRIP = U/'dsrom_noECC_strip_clock_construction_20261002/model.json'
CTX = U/'dsrom_noECC_production_context_20261002/model.json'
CUT = U/'dsrom_noECC_production_context_20261002/local_cuts.json'
NATIVE = U/'dsrom_noECC_native_clock_access_20261002/model.json'
MACRO_LEF = U/'dsrom_noECC_enable_distribution_20261002/inputs/macro.lef'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write_gz(p, records):
    data = ''.join(json.dumps(r, sort_keys=True, separators=(',', ':'))+'\n' for r in records).encode()
    p.write_bytes(gzip.compress(data, mtime=0))

def intervals_without(blocks, lo, hi):
    """Disjoint available intervals, merging occupied source sites first."""
    out=[]; cursor=lo
    for a,b in sorted(blocks):
        a=max(a,lo); b=min(b,hi)
        if b<=cursor or a>=hi: continue
        if a>cursor: out.append((cursor,a))
        cursor=max(cursor,b)
    if cursor<hi: out.append((cursor,hi))
    return out

def row_pack(cells, fixed, lef, outline, xlo=276480, ylo=0):
    """Literal site rows; each new body reserves its width again as whitespace.

    50% is this explicit placement allowance, never PG/routing qualification.
    Fixed source controls already have disjoint legal sites and are obstacles.
    """
    rows=defaultdict(list)
    for p in fixed:
        x,y,X,Y=p['bbox_DBU']
        for r in range(y//270, math.ceil(Y/270)):
            rows[r].append((x,X))
    slots=[]
    xmax=outline[2]//54*54
    for y in range(ylo,outline[3]//270*270,270):
        for a,b in intervals_without(rows[y//270],xlo,xmax):
            a=math.ceil(a/54)*54; b=b//54*54
            if b>a: slots.append([a,b,y])
    out=[]; missing=[]; j=0
    for c in cells:
        w,h=lef[c['master']]['size_DBU']
        if h!=270 or w%54: raise ValueError('source site mismatch')
        while j<len(slots) and slots[j][1]-slots[j][0]<2*w: j+=1
        if j==len(slots):
            missing.append(c); continue
        a,b,y=slots[j]
        out.append(placed(c['name'],c['master'],a,y,lef,'retained_source_compute_row_preview'))
        slots[j][0]+=2*w
    return out,missing

def endpoint(p, pin, lef, caps, net, source_kind):
    rr=pin_rects(p,lef[p['master']],pin)
    if not rr: raise ValueError('missing literal pin '+p['instance']+'/'+pin)
    return dict(instance=p['instance'],master=p['master'],pin=pin,net=net,
                source_kind=source_kind,bbox_DBU=p['bbox_DBU'],orientation=p['orientation'],
                translated_pin_rectangles=rr,
                SS_FF_max_pin_cap_fF={k:caps[k][p['master']][pin]['max_cap_fF'] for k in ('ss','ff')})

def build():
    BASE.mkdir(parents=True,exist_ok=True)
    e,h,s,ctx,cut,native=[json.loads(p.read_text()) for p in (ENABLE,HOLD,STRIP,CTX,CUT,NATIVE)]
    lef=dict(e['physical_master_templates'])
    for case in ('q','bfcolumn'):
        lef.update(ctx['cases'][case]['named_physical_master_inventory'])
    libs={k:cell_bodies(k) for k in ('ss','ff')}
    macro_text=MACRO_LEF.read_text()
    clk_body=re.search(r'  PIN clk\n(.*?)  END clk',macro_text,re.S)[1]
    clk_rect=[round(float(v)*1000) for v in re.search(r'RECT (.*?) ;',clk_body)[1].split()]
    lef['ot_rom_4096x274_m8']=dict(size_DBU=[125280,62910],pins=[dict(name='clk',rectangles=[dict(layer='M4',bbox_DBU=clk_rect)])])
    for k in ('ss','ff'):
        text=library_text('macro_'+k+'.lib')
        m=re.search(r'\bcell\s*\(ot_rom_4096x274_m8\)',text)
        libs[k]=dict(libs[k]);libs[k]['ot_rom_4096x274_m8']=block(text,m.start())
    caps={k:pin_models(libs[k]) for k in ('ss','ff')}
    result={}; inputs={str(p.relative_to(ROOT)):sha(p) for p in (ENABLE,HOLD,STRIP,CTX,CUT,NATIVE,MACRO_LEF)}
    for case in ('q','bfcolumn'):
        cs,ps,groups,mapped=trace(case); inputs[str(mapped.relative_to(ROOT))]=sha(mapped)
        ec,sc,hc,cc=e['cases'][case],s['cases'][case],h['cases'][case],ctx['cases'][case]
        fixed=list(ec['placements'])+list(hc['placements'])+list(sc['new_clock_buffer_placements'])+list(sc['retained_original_scalar_placements'])
        for item in cut['cases'][case]['source_clock_cell_slots']:
            fixed.append(placed(item['actual_instance'],item['master'],item['bbox_DBU'][0],item['bbox_DBU'][1],lef,item['role']))
        names=[p['instance'] for p in fixed]
        if len(names)!=len(set(names)): raise ValueError('duplicate fixed source instance')
        fixed_names=set(names)
        # The actual WAKE QN -> source INV -> ICG ENA path must not inherit
        # the arbitrary combinational row-pack distance. Retain its real INV.
        ena_nets={ps[n]['ENA']:n for n,c in cs.items() if c['master'].startswith('ICG')}
        ena_drivers={}
        for n,p in ps.items():
            if p.get('Y') in ena_nets:
                if p['Y'] in ena_drivers: raise ValueError('multiple source ICG ENA drivers')
                ena_drivers[p['Y']]=n
        if len(ena_drivers)!=8: raise ValueError('eight real source ENA drivers required')
        wake_paths=[]
        for net,icg in sorted(ena_nets.items()):
            inv=ena_drivers[net]
            if not cs[inv]['master'].startswith('INV'): raise ValueError('WAKE inversion source changed')
            target=next(p for p in fixed if p['instance']==icg)
            leaf=int(ps[icg]['GCLK'].split('[')[1].split(']')[0])
            # Dedicated source root cells use the following row. Macro strip
            # cells use the first legal interval to the right of their ICG.
            region=[0,0,target['bbox_DBU'][0]+4320,target['bbox_DBU'][3]+270]
            if leaf<4:
                ylo=target['bbox_DBU'][3]; xlo=target['bbox_DBU'][0]
            else:
                ylo=target['bbox_DBU'][1]; xlo=target['bbox_DBU'][2]
                region[2]=138240 if leaf<6 else 276480
            local_inv,unfit=row_pack([cs[inv]],fixed,lef,region,xlo=xlo,ylo=ylo)
            if unfit: raise ValueError('source WAKE inverter site unavailable')
            local_inv[0]['role']='retained_source_WAKE_polarity_INV'
            fixed+=local_inv; fixed_names.add(inv)
            wake_paths.append(dict(leaf=leaf,ICG_instance=icg,ENA_net=net,retained_INV_instance=inv,
                                   retained_INV_input_net=ps[inv]['A'],source_INV_bbox_DBU=local_inv[0]['bbox_DBU'],
                                   enable_setup_hold_pulse_width_and_wires_not_qualified=True))
        # Place actual direct scalar QN receivers in the already existing bank gap.
        # Preserve immutable strip/clock/D stations; this is not an added gate.
        qnets={ps[p['instance']]['QN'] for p in sc['retained_original_scalar_placements']}
        scalar_neighbors=[c for n,c in cs.items() if n not in fixed_names and any(v in qnets for v in ps[n].values())]
        scalar_neighbors.sort(key=lambda c:c['name'])
        local,local_missing=row_pack(scalar_neighbors,fixed,lef,[0,0,274320,71550],xlo=272160,ylo=67500)
        if local_missing: raise ValueError('source scalar neighbor station lacks legal sites')
        for p in local: p['role']='retained_source_scalar_direct_receiver'
        fixed+=local; fixed_names.update(p['instance'] for p in local)
        # Complete source instances, not only a FF stencil. No waveform/tensor payload reads.
        rest=[c for n,c in cs.items() if n not in fixed_names and c['master']!='ot_rom_4096x274_m8']
        rest.sort(key=lambda c:(0 if c['master'].startswith('DFF') else 1,ps[c['name']].get('CLK',''),c['name']))
        packed,missing=row_pack(rest,fixed,lef,cc['outline_DBU'])
        placements=fixed+packed; byname={p['instance']:p for p in placements}
        # Exact four ROM body placements are inferred from the retained capture-strip template.
        macros=[]
        for n,c in cs.items():
            if c['master']!='ot_rom_4096x274_m8': continue
            leaf=int(ps[n]['clk'].split('[')[1].split(']')[0]); mb=(leaf-4)//2; bank=(leaf-4)%2
            r=next(v['region_DBU'] for v in ec['strips'] if (v['MB'],v['bank'])==(mb,bank))
            p=dict(instance=n,master=c['master'],role='retained_source_ROM',bbox_DBU=[r[0]-125280,r[1],r[0],r[1]+62910],orientation='R0',clock=ps[n]['clk'])
            macros.append(p)
        endpoints=[endpoint(p,'clk',lef,caps,p['clock'],'retained_source_ROM_macro') for p in macros]; unplaced=[]
        for n,c in cs.items():
            if c['master']=='ot_rom_4096x274_m8': continue
            for pin in ('CLK','RESETN','SETN'):
                net=ps[n].get(pin)
                if net is None or "'" in net: continue
                if n not in byname:
                    unplaced.append(dict(instance=n,pin=pin,net=net)); continue
                endpoints.append(endpoint(byname[n],pin,lef,caps,net,'retained_mapped_source'))
        for p in fixed:
            if p['instance'] in cs: continue
            if p['role']=='control_state_replica':
                ports=[('CLK','leaf_clk[0]')]
                if any(v['name']=='RESETN' for v in lef[p['master']]['pins']): ports.append(('RESETN','rst_n'))
                for pin,net in ports:
                    endpoints.append(endpoint(p,pin,lef,caps,net,'proposed_enable_metadata_clone'))
        # Buffer A endpoints are physical receivers of the local tree, not FF or source-net aliases.
        buffer_inputs=[endpoint(p,'A',lef,caps,'local_clock_tree_parent','constructed_strip_clock_buffer') for p in sc['new_clock_buffer_placements']]
        domains={}
        for net in sorted({p['net'] for p in endpoints if p['pin'] in ('CLK','clk')}):
            ep=[p for p in endpoints if p['pin'] in ('CLK','clk') and p['net']==net]
            domains[net]=dict(named_endpoint_count=len(ep),masters=dict(Counter(p['master'] for p in ep)),
                             SS_FF_total_pin_cap_fF={k:sum(p['SS_FF_max_pin_cap_fF'][k] for p in ep) for k in ('ss','ff')},
                             endpoint_body_envelope_DBU=[min(p['bbox_DBU'][0] for p in ep),min(p['bbox_DBU'][1] for p in ep),max(p['bbox_DBU'][2] for p in ep),max(p['bbox_DBU'][3] for p in ep)])
        reset=[p for p in endpoints if p['pin'] in ('RESETN','SETN')]
        reset_by_net={}
        for net in sorted({p['net'] for p in reset}):
            ep=[p for p in reset if p['net']==net]
            worst=sum(max(p['SS_FF_max_pin_cap_fF'].values()) for p in ep)
            reset_by_net[net]=dict(named_endpoint_count=len(ep),SS_FF_pin_cap_fF={k:sum(p['SS_FF_max_pin_cap_fF'][k] for p in ep) for k in ('ss','ff')},
                                   pin_only_leaf_lower_bound_at_5p76_fF=math.ceil(worst/5.76),
                                   leaf_fanin_budget_scope='Maxwell reset tree pin allowance only; wire/native access added separately before admission',
                                   actual_release_waveform_and_tree_not_qualified=True)
        reset_contracts=[]
        for master,pin in sorted({(p['master'],p['pin']) for p in reset}):
            constraints={}
            for corner in ('ss','ff'):
                body=libs[corner][master]
                match=re.search(r'\bpin\s*\('+pin+r'\)',body)
                pb=block(body,match.start())
                recovery=bound(pb,('rise_constraint',),320,320,related='CLK',timing_type='recovery_rising')
                removal=bound(pb,('rise_constraint',),320,320,related='CLK',timing_type='removal_rising')
                constraints[corner]=dict(literal_pin_sha256=hashlib.sha256(pb.encode()).hexdigest(),
                                         source_recovery_upper_ps=recovery,source_removal_upper_ps=removal,
                                         input_reset_and_clock_slew_envelope_ps=320,
                                         policy_recovery_plus_setup_and_unproven_skew_ps=recovery+60+25,
                                         policy_removal_plus_hold_and_unproven_skew_ps=removal+25+25)
            reset_contracts.append(dict(master=master,pin=pin,count=sum(p['master']==master and p['pin']==pin for p in reset),corners=constraints,
                                        relative_skew_25ps_is_requirement_not_measured=True))
        # Actual source scalar fanouts with translated destination pins, no 1um placeholder.
        scalar=[]
        for p in sc['retained_original_scalar_placements']:
            net=ps[p['instance']]['QN']; receivers=[]
            src=center(max(pin_rects(p,lef[p['master']],'QN'),key=lambda r:r['bbox_DBU'][3]-r['bbox_DBU'][1])['bbox_DBU'])
            for n,ports in ps.items():
                if n==p['instance']: continue
                for pin,value in ports.items():
                    if value!=net: continue
                    if n not in byname: receivers.append(dict(instance=n,pin=pin,unplaced=True)); continue
                    dst=endpoint(byname[n],pin,lef,caps,net,'retained_scalar_QN_receiver')
                    pt=center(dst['translated_pin_rectangles'][0]['bbox_DBU'])
                    dst['endpoint_Manhattan_lower_bound_um']=(abs(src[0]-pt[0])+abs(src[1]-pt[1]))/1000
                    receivers.append(dst)
            scalar.append(dict(source_instance=p['instance'],QN_net=net,receivers=receivers,
                               wire_geometry_RC_clock_minmax_and_hold_not_qualified=True))
        write_gz(BASE/(case+'_placement.jsonl.gz'),placements+macros)
        write_gz(BASE/(case+'_endpoints.jsonl.gz'),endpoints+buffer_inputs)
        source_area=math.fsum(lef[c['master']]['area_um2'] for c in cs.values() if c['master']!='ot_rom_4096x274_m8')
        if abs(source_area-cc['physical_LEF_cell_union_area_um2'])>1e-5: raise ValueError('source area mismatch')
        added=[p for p in fixed if p['instance'] not in cs]
        result[case]=dict(retained_source_cell_count=len(cs),retained_source_stdcell_count=len(cs)-4,
                         retained_source_stdcell_area_um2=source_area,constructed_added_cell_count=len(added),
                         constructed_added_cell_area_um2=sum(lef[p['master']]['area_um2'] for p in added),
                         complete_macro_count=len(macros),fixed_cell_count=len(fixed),row_packed_cell_count=len(packed),
                         source_scalar_neighbor_relocation_count=len(local),source_scalar_neighbor_extra_area_um2=0,
                         unplaced_cell_count=len(missing),unplaced_area_um2=sum(lef[c['master']]['area_um2'] for c in missing),
                         unplaced_master_counts=dict(Counter(c['master'] for c in missing)),unplaced_clock_reset_endpoints=unplaced,
                         body_placement_preview_status='COMPLETE_BODY_PREVIEW' if not missing else 'FAIL_INCOMPLETE_BODY_PREVIEW',
                         compute_x_min_DBU=276480,outline_DBU=cc['outline_DBU'],row_pitch_DBU=270,site_pitch_DBU=54,
                         dynamic_body_whitespace_ratio=1,PG_bottom_strip_assumed_free=False,
                         clock_domains=domains,source_ICG_connections=[dict(instance=n,master=c['master'],ports=ps[n]) for n,c in cs.items() if c['master'].startswith('ICG')],
                         actual_WAKE_QN_INV_ICG_paths=wake_paths,
                         macro_leaf_clock_consumers=[dict(instance=p['instance'],net=p['clock'],bbox_DBU=p['bbox_DBU']) for p in macros],
                         reset_net_groups=reset_by_net,pin_specific_async_release_contracts=reset_contracts,retained_scalar_QN_fanouts=scalar,
                         existing_strip_clock_buffer_count=len(buffer_inputs),full_clock_reserve_embedding_credit_um2=0,
                         source_mapped_sha256=sha(mapped),placement_artifact_sha256=sha(BASE/(case+'_placement.jsonl.gz')),
                         endpoint_artifact_sha256=sha(BASE/(case+'_endpoints.jsonl.gz')))
    model=dict(schema='opentallas.dsrom.full-clock-reset-source-union.v1',candidate=e['candidate'],source_input_sha256=inputs,
               cases=result,physical_build_admitted=False,clock_period_ps=2500/3,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
               added_capture_edges=0,area_credit_um2=0,PG_OBS_pin_via_extraction_or_skew_credit=False,
               construction_scope='All retained source bodies and exact clock/reset endpoints; deterministic row preview, not timing-driven placement. Higher-layer PG over rows is permitted only after explicit endpoint native-access exclusion tests.',
               next_native_construction=['Disjoint root-to-eight-ICG paths and full leaf consumer forest including macro CLK pins',
                                         'Root/leaf minimum and maximum propagated clock paths, matched scalar QN/D wires and arithmetic capture hold',
                                         'All endpoint native pin/OBS/PG/via escape plus reset tree and source parent release waveform'],
               prior_native_access_FAIL_records_untouched=True)
    (BASE/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
    return model

if __name__=='__main__':
    x=build()
    print(json.dumps({k:{v:c[v] for v in ('retained_source_cell_count','row_packed_cell_count','unplaced_cell_count','clock_domains','reset_net_groups')} for k,c in x['cases'].items()},indent=2))
