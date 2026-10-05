#!/usr/bin/env python3
"""Standalone bounded TC-successor geometry; never generates RTL, LEF or P&R.

Offline reproduction uses only pinned Git records and retained platform text.
The grid is a reservation proposal; its analytical track ceiling is not free
routed capacity or physical qualification. No full-SM admission follows.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from hbm_tc_nested_dot_delta import selected_grid

ROOT = Path(__file__).resolve().parents[1]
BASE = 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
PRIOR = 'd8fe3fd2140ff953a47bf9277360f3689e8c61ee'
SOURCE = '000ba0898f5120a66d5905ccff333ebbbe28394d'
OUT = 'results/uarch/hbm_tc_geometry_prerequisite_20261001'
ABS = 'results/physical_abi3/asap7/chip/abstracts/'
QTERM = 'results/physical_abi3/asap7/gpu/w13_tc_col_terminal_20261001T2112Z'
DTERM = 'results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z'
SX, SY, HALO, EDGE, UTIL, KEEP = .432, 2.16, 6., 24., .45, .1


def ceilgrid(x, q):
    return round(math.ceil((x-1e-9)/q)*q, 6)


def lef(text):
    size = list(map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text).groups()))
    pins = []
    for name, body in re.findall(r'\bPIN\s+(\S+)\s+(.*?)\n\s*END\s+\1(?:\s|$)', text, re.S):
        for layer, a, b, c, d in re.findall(r'LAYER\s+(\w+)\s*;\s*RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', body):
            rect = list(map(float, [a,b,c,d]));x,y=(rect[0]+rect[2])/2,(rect[1]+rect[3])/2
            distances={'W':x,'E':size[0]-x,'S':y,'N':size[1]-y}
            pins.append(dict(pin=name,layer=layer,rect_um=rect,center_um=[x,y],edge=min(distances,key=distances.get)))
    obs=[]
    if '\n  OBS' in text:
        for layer,body in re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|END)',text.split('\n  OBS',1)[1],re.S):
            for r in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',body):obs.append(dict(layer=layer,rect_um=list(map(float,r))))
    return dict(size_um=size,pins=pins,OBS=obs)


def conflicts(rows, halo=0):
    out=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            dx=min(a['x']+a['w']+halo,b['x']+b['w']+halo)-max(a['x']-halo,b['x']-halo)
            dy=min(a['y']+a['h']+halo,b['y']+b['h']+halo)-max(a['y']-halo,b['y']-halo)
            if dx>1e-8 and dy>1e-8:out.append([a['name'],b['name'],round(dx,6),round(dy,6)])
    return out


def platform(data, lock):
    fs=data['files']
    for path,f in fs.items():
        if hashlib.sha256(f['text'].encode()).hexdigest()!=f['sha256']:raise ValueError('platform text hash '+path)
        if path in lock and f['sha256']!=lock[path]:raise ValueError('locked platform mismatch '+path)
    tech=fs['lef/asap7_tech_1x_201209.lef']['text'];tracks=fs['openRoad/make_tracks.tcl']['text'];layers={}
    for name,body in re.findall(r'LAYER (M[4-9])\n(.*?)END \1',tech,re.S):
        direction=re.search(r'DIRECTION\s+(\w+)',body)[1];axis='y' if direction=='HORIZONTAL' else 'x'
        t=re.search(r'make_tracks '+name+r'\s+([^\n]+)',tracks)[1]
        layers[name]=dict(direction=direction,axis=axis,offset=float(re.search('-'+axis+r'_offset ([\d.]+)',t)[1]),pitch=float(re.search('-'+axis+r'_pitch ([\d.]+)',t)[1]),width=float(re.search(r'WIDTH\s+([\d.]+)',body)[1]))
    cells=[]
    for name,body in re.findall(r'MACRO\s+(\S+)\n(.*?)END\s+\1',fs['lef/asap7sc7p5t_28_R_1x_220121a.lef']['text'],re.S):
        m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',body)
        if m:cells.append((float(m[1])*float(m[2]),name))
    return layers,dict(stock_cell_count=len(cells),largest_stock_cell_um2=max(cells)[0],largest_stock_cell=max(cells)[1],largest_DFF_um2=max(a for a,n in cells if 'DFF' in n),basis='Locked standard-cell LEF physical area, no Liberty timing inference')


def pdn(text):
    rails={}
    for layer,w,s,p,o in re.findall(r'add_pdn_stripe -grid \{top\} -layer \{(M[5-8])\} -width \{([\d.]+)\} -spacing \{([\d.]+)\} -pitch \{([\d.]+)\} -offset \{([\d.]+)\}',text):
        rails[layer]=dict(width=float(w),spacing=float(s),pitch=float(p),offset=float(o))
    if len(rails)!=4:raise ValueError('PDN source changed')
    return rails


def capacity(span, direction, layers, rails):
    # Worst phase bound: at most ceil(span/railpitch)+2 pairs intersect;
    # charge each rail independently (including double-counting overlaps).
    result={}
    for name,l in layers.items():
        if l['direction']!=direction:continue
        raw=max(0,math.floor(span/l['pitch'])-1)
        r=rails.get(name);blocked=0
        if r:
            pairs=math.ceil(span/r['pitch'])+2
            blocked=2*pairs*(math.ceil((r['width']+2*KEEP+l['width'])/l['pitch'])+1)
        result[name]=dict(phase_independent_track_floor=raw,PDN_worst_phase_blocked_upper=blocked,model_reserved_signal_tracks=max(0,math.floor((raw-blocked)*.5)))
    return dict(layers=result,reserved_capacity=sum(x['model_reserved_signal_tracks'] for x in result.values()),actual_available_track_lower_bound=0,meaning='Reserved corridor sizing bound with 50% extra occupancy; not observed routed free tracks')


def need_span(demand, direction, layers, rails):
    q=SX if direction=='VERTICAL' else SY
    for n in range(1,10000):
        if capacity(n*q,direction,layers,rails)['reserved_capacity']>=demand:return round(n*q,6)
    raise ValueError('reservation exceeds bounded search')


def mask(start, end, layer, layers, rails):
    l=layers[layer];r=rails.get(layer);first=math.ceil((start-l['offset'])/l['pitch']);last=math.floor((end-l['offset'])/l['pitch']);blocked=0
    for k in range(first,last+1):
        t=l['offset']+k*l['pitch']
        if r:
            blocked+=any(abs(t-(r['offset']+n*r['pitch']+shift))<=r['width']/2+KEEP+l['width']/2 for n in range(math.floor((t-r['offset'])/r['pitch'])-2,math.floor((t-r['offset'])/r['pitch'])+3) for shift in (0,r['width']+r['spacing']))
    return dict(layer=layer,start_um=round(start,6),end_um=round(end,6),first_track_index=first,last_track_index=last,track_count=max(0,last-first+1),PDN_masked_tracks=blocked,remaining_geometric_ceiling=max(0,last-first+1-blocked),actual_available_track_lower_bound=0)


def banks(info, lanes, annex, cell_area):
    result=[]
    for lane in range(lanes):
        ports={}
        for port in ['w','x']:
            pp=[p for p in info['pins'] if re.fullmatch(port+r'\[\d+\]',p['pin']) and lane*16<=int(re.search(r'\[(\d+)\]',p['pin'])[1])<(lane+1)*16]
            if len(pp)!=16:raise ValueError('lane pin binding incomplete')
            ports[port]=dict(edge=pp[0]['edge'],layer=pp[0]['layer'],pins=[p['pin'] for p in pp],pin_rectangles_um=[p['rect_um'] for p in pp],centroid_um=[sum(p['center_um'][i] for p in pp)/16 for i in [0,1]])
        # A proposed bank shares the whole lane's equal-height strip; archival
        # pins are access anchors, not evidence of internal lane placement.
        y=info['size_um'][1]*(lane+.5)/lanes;cut=[annex/2,y]
        w_anchor=[annex+ports['w']['centroid_um'][0],ports['w']['centroid_um'][1]]
        x_anchor=[annex+ports['x']['centroid_um'][0],ports['x']['centroid_um'][1]]
        # Select the actual archived north operand (w), not a guessed edge.
        north=next(p['centroid_um'] for p in ports.values() if p['edge']=='N')
        west=next(p['centroid_um'] for p in ports.values() if p['edge']=='W')
        north_path=annex+north[0]-cut[0]+info['size_um'][1]-cut[1]
        west_path=abs(annex+west[0]-cut[0])+abs(west[1]-cut[1])
        perimeter=max(north_path,west_path)+annex
        result.append(dict(lane=lane,source_edge_access=ports,proposed_cut_center_um=cut,proposed_lane_band_y_um=[lane*info['size_um'][1]/lanes,(lane+1)*info['size_um'][1]/lanes],cut_bits=40,register_bank_cell_area_upper_um2=40*cell_area,perimeter_wire_length_bound_um=round(perimeter,6),wire_stages_at_SS504=math.ceil(perimeter/504),internal_lane_location_status='No archived DEF/internal register coordinates; cut location is proposed, not measured',source_w_anchor_translated_um=w_anchor,source_x_anchor_translated_um=x_anchor,source_decode_cut_bindings={'lane_decode':'rtl/v41rom/ot_v41_bmul2.sv: dec BF16 unpack, before exponent add s1_e', 'valid_control':'rtl/gpu/ot_gpu_tc_col.sv: g_lane, v_q, bubble gate; successor local valid is bank metadata', 'physical_location':'Proposed west bank in a new monolithic successor outline; failed macro is a silhouette, not a reusable black box'}))
    return result


def build():
    pins=[]
    def raw(path,rev=BASE):
        b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT);pins.append(dict(git=rev,path=path,sha256=hashlib.sha256(b).hexdigest()));return b
    def rec(path,rev=BASE):return json.loads(raw(path,rev))
    source_platform=(ROOT/OUT/'platform_source.json').read_bytes();pdata=json.loads(source_platform)
    lock=rec('configs/pdk/asap7_physical_lock.json')['toolchain']['asap7']['files'];layers,cells=platform(pdata,lock)
    fp=raw('tools/chip_assembly/floorplans.py').decode();rails=pdn(raw('tools/chip_assembly/tcl/pdn_sm.tcl').decode())
    for p in ['tools/uarch_model.py','tools/hbm_gpu_floorplan.py','tools/chip_assembly/macros.py','rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_sm_v.sv','rtl/gpu/ot_gpu_xstore.sv']:raw(p)
    failed_source_locations={}
    for path,terms in [('rtl/v41rom/ot_v41_bmul2.sv',['dec','s1_e','s1_s']),('rtl/gpu/ot_gpu_tc_col.sv',['v_q','g_lane','fl[','vl['])]:
        text=raw(path,SOURCE).decode()
        failed_source_locations[path]=[{'line':i,'text':line.strip()} for i,line in enumerate(text.splitlines(),1) if any(t in line for t in terms)]
    prior=rec('results/uarch/hbm_tc_nested_dot_delta_20261001_r2/summary.json',PRIOR)
    initial=rec('results/uarch/hbm_tc_column_failure_prerequisite_20261001/model.json',PRIOR)
    memories={}
    for k,n in [('big','ot_sram_1r1w_1024x256_m2_r2c2'),('small','ot_sram_1r1w_128x256_m1_r2c2'),('scale','ot_sram_1r1w_256x256_m2_r2c2')]:
        memories[k]=lef(raw('physical/asap7_memory_macros/'+n+'/'+n+'.lef').decode())
    bd=lef(raw(ABS+'ot_gpu_bd_col/ot_gpu_bd_col.lef').decode());bd_record=rec('results/physical_abi3/asap7/chip/blocks/ot_gpu_bd_col.json')
    bd_same=rec('results/physical_abi3/asap7/gpu/w13_followup_20261001/terminal_snapshot/ot_gpu_bd_col/blocks.json')
    out={}
    for model,lane,term,macro,which,oldslot in [('qwen',32,QTERM,'ot_gpu_tc_col','q',[1900,2150]),('deepseek_v41',16,DTERM,'ot_gpu_tc16','v',[1400,1640])]:
        receipt=rec(term+'/receipt.json');assert receipt['source_git']==SOURCE and receipt['engineering_verdict']=='FAIL'
        path='records/'+ABS+macro+'/'+macro+'.lef';b=raw(term+'/'+path)
        assert hashlib.sha256(b).hexdigest()==receipt['files'][path]
        arch=lef(b.decode());legacy=arch if which=='q' else lef(raw(ABS+macro+'/'+macro+'.lef').decode());baseline=[max(a,b) for a,b in zip(arch['size_um'],legacy['size_um'])]
        nff=40*lane+20;control=64*lane+64;clock=math.ceil(nff/16)+lane
        # Engineering caps are explicit rejection thresholds, not proof that
        # SS/FF repair is achieved by this many cells.
        hold=2*nff+2*35*(2*lane-1)
        counts=dict(predecode_and_alignment_FF=nff,extra_control_two_input_cells_cap=control,extra_clock_buffers_cap=clock,extra_hold_buffers_cap=hold)
        area=nff*cells['largest_DFF_um2']+(control+clock+hold)*cells['largest_stock_cell_um2']
        annex=ceilgrid(area/(UTIL*arch['size_um'][1]),SX)
        shape=[ceilgrid(baseline[0]+annex,SX),ceilgrid(baseline[1],SY)]
        lane_banks=banks(arch,lane,annex,cells['largest_DFF_um2'])
        # Both adjacent columns' BF16 input edges + two output bundles,
        # metadata, and one entire local predecode cut as a conservative
        # escape cut. No compression/serialization or operand reuse credit.
        demand=2*(16*lane)+2*50+2*19+40*lane
        fragment=32768 if which=='q' else 25216
        # Eight explicitly reserved vertical spokes carry distinct fragment
        # slices, the full shared weight bus, metadata/results and local cut.
        # Row corridors additionally reserve all eight per-column weight
        # branches without multicast credit; DS also covers wider BD edges.
        vdemand=max(demand,math.ceil(fragment/8)+(2048 if which=='q' else 1088)+8*50+19+40*lane)
        hdemand=max(demand,8*(max(16*lane,532 if which=='v' else 0)+50+20)+40*lane)
        clearx=need_span(vdemand,'VERTICAL',layers,rails);cleary=need_span(hdemand,'HORIZONTAL',layers,rails)
        gapx=ceilgrid(2*HALO+clearx,SX);gapy=ceilgrid(2*HALO+cleary,SY)
        rows=[];corridors=[];y=ceilgrid(EDGE,SY)
        def addrow(names,kind,w,h):
            nonlocal y
            x=ceilgrid(EDGE,SX);row=[]
            for name in names:
                r=dict(name=name,kind=kind,x=x,y=y,w=w,h=h);rows.append(r);row.append(r);x=ceilgrid(x+shape[0]+gapx,SX)
            for a,c in zip(row,row[1:]):
                start=a['x']+shape[0]+HALO;end=c['x']-HALO
                corridors.append(dict(direction='VERTICAL',between=[a['name'],c['name']],clear_span_um=round(end-start,6),demand_bits=vdemand,tracks=[mask(start,end,l,layers,rails) for l in ['M5','M7','M9']]))
            if row:
                # The eighth spine is reserved to the east of the last macro.
                start=row[-1]['x']+shape[0]+HALO;end=start+clearx
                corridors.append(dict(direction='VERTICAL',between=[row[-1]['name'],'east_reserved_spine'],clear_span_um=clearx,demand_bits=vdemand,tracks=[mask(start,end,l,layers,rails) for l in ['M5','M7','M9']]))
                start=y+h+HALO;end=ceilgrid(y+h+gapy,SY)-HALO
                corridors.append(dict(direction='HORIZONTAL',row_names=names,clear_span_um=round(end-start,6),demand_bits=hdemand,tracks=[mask(start,end,l,layers,rails) for l in ['M4','M6','M8']]))
            y=ceilgrid(y+h+gapy,SY)
        grid=selected_grid(fp,which);tc=[n for n,x,y in grid if n.endswith('u_tc')];bdnames=[n for n,x,y in grid if n.endswith('u_bd')]
        if which=='q':
            for i in range(0,64,8):addrow(tc[i:i+8],'successor_TC',*shape)
            memnames=[n for n,x,y in grid if not n.endswith('u_tc')]
            for i in range(0,len(memnames),8):addrow(memnames[i:i+8],'SRAM_big_envelope',*memories['big']['size_um'])
        else:
            for i in range(0,32,8):
                addrow(bdnames[i:i+8],'retained_BD_envelope',*bd['size_um']);addrow(tc[i:i+8],'successor_TC',*shape)
            names=[n for n,x,y in grid if n.startswith('g_xm')]
            for i in range(0,len(names),8):addrow(names[i:i+8],'SRAM_small',*memories['small']['size_um'])
            addrow([n for n,x,y in grid if n.startswith('u_bc')],'SRAM_ring',*memories['big']['size_um'])
        w=ceilgrid(max(r['x']+r['w'] for r in rows)+EDGE+clearx+HALO,SX);h=ceilgrid(max(r['y']+r['h'] for r in rows)+EDGE,SY)
        assert not conflicts(rows,HALO)
        global_spines=[dict(spoke=i,rectangle_um=[ceilgrid(EDGE,SX)+i*ceilgrid(shape[0]+gapx,SX)+shape[0]+HALO,EDGE,ceilgrid(EDGE,SX)+i*ceilgrid(shape[0]+gapx,SX)+shape[0]+HALO+clearx,h-EDGE],fragment_slice_bits=[math.floor(fragment*i/8),math.floor(fragment*(i+1)/8)-1],fragment_source='Qwen staged u_x double buffer -> ix; DS g_xm read -> ix',stage_register_count_upper=max(0,math.ceil((h-2*EDGE)/504)-1),wire_FF_bits_upper=vdemand*max(0,math.ceil((h-2*EDGE)/504)-1)) for i in range(8)]
        historical=[]
        for name,x,y in grid:
            sz=legacy['size_um'] if name.endswith('u_tc') else bd['size_um'] if name.endswith('u_bd') else memories['small']['size_um'] if name.startswith('g_xm') else memories['big']['size_um']
            historical.append(dict(name=name,x=x,y=y,w=sz[0],h=sz[1]))
        die=rec('results/floorplan/hbm_gpu/'+('qwen' if which=='q' else 'v41')+'_hbm_die.json')
        dx=max(0,w-oldslot[0]);dy=max(0,h-oldslot[1]);arraygrow=[8*dx,4*dy]
        # Retain centered 8x4 die organization and fixed existing channels/hub.
        # Farthest Manhattan endpoint displacement <= half total array growth;
        # a path between two moving endpoints <= total array growth.
        crossings=[]
        for c in die['crossings']:
            extra=sum(arraygrow) if c['name'].startswith('barrier') else sum(arraygrow)/2
            oldst=math.ceil(c['distance_um']/504);newst=math.ceil((c['distance_um']+extra)/504)
            crossings.append(dict(name=c['name'],old_distance_um=c['distance_um'],candidate_distance_upper_um=round(c['distance_um']+extra,6),old_stages_SS504=oldst,candidate_stages_upper_SS504=newst,delta_stages_upper=newst-oldst,retained_crossings_per_token=c['per_token_crossings'],token_cycles_upper=(newst-oldst)*c['per_token_crossings'],requires_actual_event_binding=True))
        core=die['core_um'];newarray=[die['array']['w']+arraygrow[0],die['array']['h']+arraygrow[1]]
        overflow=[max(0,newarray[0]-(core['x1']-core['x0'])),max(0,newarray[1]-(core['y1']-core['y0']-1400))]
        newdie=[ceilgrid(die['die_um'][i]+overflow[i],SX if i==0 else SY) for i in [0,1]]
        # External endpoint displacement when expanding the die is not free.
        # Bound two moving endpoints by the entire additional die span.
        for c in crossings:
            c['candidate_distance_upper_um']=round(c['candidate_distance_upper_um']+sum(newdie[i]-die['die_um'][i] for i in [0,1]),6)
            c['candidate_stages_upper_SS504']=math.ceil(c['candidate_distance_upper_um']/504)
            c['delta_stages_upper']=c['candidate_stages_upper_SS504']-c['old_stages_SS504']
            c['token_cycles_upper']=c['delta_stages_upper']*c['retained_crossings_per_token']
        out[model]=dict(archived_pin_coordinates_and_OBS=arch,global_legacy_OBS=legacy['OBS'],failed_source_outline_um=arch['size_um'],retained_global_outline_um=legacy['size_um'],baseline_geometric_envelope_um=baseline,source_same_failed_LEF_sha256=hashlib.sha256(b).hexdigest(),failed_LEF_qualification_transfer=False,failed_unchanged=receipt,
            bounded_added_overhead=dict(count_caps=counts,area_upper_um2=area,area_bound_source=cells,annex_utilization_cap=UTIL,west_annex_um=annex,cap_exceeded_action='Reject geometry; recompose model before any build',hold_budget_is_timing_cure=False),successor_reservation_outline_um=shape,lane_predecode_cut_banks=lane_banks,
            reservations=dict(columns_per_row=8,HALO_each_side_um=HALO,edge_ring_and_escape_um=EDGE,clear_vertical_corridor_um=clearx,clear_horizontal_corridor_um=cleary,macro_gap_x_um=gapx,macro_gap_y_um=gapy,cut_demand_bits=demand,vertical_spine_demand_bits=vdemand,horizontal_row_demand_bits=hdemand,demand_formula='2*16L + 2*50 output + 2*19 input metadata + 40L local predecode escape',vertical_bound=capacity(clearx,'VERTICAL',layers,rails),horizontal_bound=capacity(cleary,'HORIZONTAL',layers,rails),M4_permission='Only in new reserved corridors outside all expanded macro/annex/halo OBS; no M4 over macro credit'),
            placements=rows,global_fragment_spines=global_spines,global_spine_wire_FF_area_upper_um2=sum(x['wire_FF_bits_upper'] for x in global_spines)*cells['largest_DFF_um2'],global_spine_wire_FF_area_basis='Count entire reserved cut width at each SS504 stage; existing parent pipeline endpoints may share registers, but no credit taken. Placement inside clear spines requires owner composition and cannot consume the reserved routing half without repricing.',corridor_track_grid=corridors,placement_count_by_kind=dict(Counter(r['kind'] for r in rows)),minimum_slot_for_declared_grid_um=[w,h],minimum_is='Column/memory/cut grid with eight reserved fragment/weight spines and row branches; parent SIMD/RF/glue still need composition. Smallest snapped bounding box of this explicit 8-wide policy, not global packing optimum or complete-SM minimum',existing_slot_um=oldslot,existing_slot_fits=w<=oldslot[0] and h<=oldslot[1],retained_global_column_grid_hard_overlap_count=len(conflicts([r for r in historical if r['name'].endswith(('u_tc','u_bd'))])),retained_global_grid_all_macro_hard_overlap_count=len(conflicts(historical)),retained_global_grid_halo_overlap_count=len(conflicts(historical,6 if which=='q' else 4)),corrected_hard_overlap_count=0,corrected_halo_overlap_count=0,
            SM_slot_area_increase_mm2=(w*h-oldslot[0]*oldslot[1])/1e6,SM32_die_reserved_area_increase_mm2=32*(w*h-oldslot[0]*oldslot[1])/1e6,retained_array_growth_upper_um=arraygrow,candidate_array_um=newarray,retained_die_um=die['die_um'],minimum_die_um_for_retained_array_policy=newdie,die_outline_increase_mm2=(newdie[0]*newdie[1]-die['die_um'][0]*die['die_um'][1])/1e6,
            token_wire_sensitivity=dict(reach_um_per_stage=504,source='tools/uarch_model.py:WIRE_REACH_SS_UM; tools/hbm_gpu_floorplan.py crossing construction',paths=crossings,retained_event_count_upper_delta_stream_cycles=sum(c['token_cycles_upper'] for c in crossings),retained_event_count_is_not_complete_calendar=True,local_new_cut_stage=1,local_additional_wire_stages_above_one=max(b['wire_stages_at_SS504']-1 for b in lane_banks),parent_required='Rebind per-node event endpoints to corrected SM placements; retain TC +1 once per result drain. Add wire delta on actual dependency edges, never on every MAC or opcode. DS four WK nested projections +93 explicit TC candidates; index FMUL/FADD remain zero TC delta. Qwen bind complete-program matrix edges; retained181 broadcasts are sensitivity counts only. SRAM/BD/glue event latencies need their own endpoints.'),
            parent_full_fragment_trunk_prerequisite=dict(TC_x_fragment_bits_per_cycle=32*lane*(64 if which=='q' else 32)//2,BD_x_fragment_bits_per_cycle=0 if which=='q' else 32*532,total_fragment_bits_per_cycle=32768 if which=='q' else 25216,SRAM_read_bits_per_cycle=4096 if which=='q' else 25344,Qwen_prefetch_cycles_per_fragment=8 if which=='q' else 'DS whole-fragment single read',weight_bus_shared_bits_per_cycle=2048 if which=='q' else 1024,logical_weight_sinks=64 if which=='q' else 32,fragment_consumer_source='rtl/gpu/ot_gpu_sm_q.sv: xs=ix[(col*L+sp*LS+q)*16 +:16], FRAGW=L*NC*16; rtl/gpu/ot_gpu_sm_v.sv: xq_s/xe_s/xf_s slices of ix[col*XC+...], XC=LB*266+LF*16',whole_fragment_single_vertical_trunk_min_clear_um=need_span(32768 if which=='q' else 25216,'VERTICAL',layers,rails),whole_fragment_single_horizontal_trunk_min_clear_um=need_span(32768 if which=='q' else 25216,'HORIZONTAL',layers,rails),eight_vertical_spoke_min_clear_um_each=need_span(math.ceil((32768 if which=='q' else 25216)/8),'VERTICAL',layers,rails),local_grid_trunks_include_full_fragment=True,eight_spine_reservation='Seven inter-column corridors plus eighth east corridor; each sized for fragment/8 + shared weight bus + results/metadata + local cut. No routed availability claim.',owner_action='Bind the eight reserved disjoint spokes (or recompose a full-width trunk alternative) with source-located fragment buffers and weights/control broadcast. Smaller geometry may reserve over-macro M7-M9 only from real occupancy. Compose inserted wire/register stages on SRAM-prefetch->ix->TC/BD dependency events; no added service II assumed.'),no_complete_SM_fit_claim='Existing SIMD/RF/glue, PDN vias, congestion and stage-register placement still need owner composition. This sizes mandatory columns+memories and reservations only.')
    return dict(schema='opentallas.hbm-tc-geometry-prerequisite.v1',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),base_git=BASE,prior_git=PRIOR,source_pins=pins,platform_source_sha256=hashlib.sha256(source_platform).hexdigest(),track_script_authority='Public ORFS reference revision; tech and cell LEFs match immutable image lock by SHA. Exact image make_tracks bytes require provider confirmation before physical admission.',ASAP7_directional_grid=layers,PDN_source_parameters=rails,PDN_model='Two-rail pair per pitch, both rails charged independently with 0.1um additional keepout and half remaining tracks reserved. Not extracted via occupancy.',stock_cell_area_bounds=cells,memory_abstracts=memories,BD_abstract=bd,models=out,BD_geometry_provenance=dict(global_outline_um=bd['size_um'],global_record_git=bd_record['git'],same_source_retained_record_outline_um=bd_same['die_um'],same_source_LEF_sha256=bd_same['abstract']['lef']['sha256'],same_source_104_LEF_status='Not in this retained archive; 150um global LEF used as conservative geometric envelope only; no timing transfer'),failed_source_cut_locations=failed_source_locations,prior_event_delta=prior['composition_delta'],failure_unchanged=initial['failure_unchanged'],no_admission=True,remaining_gate=dict(provider='W13_GEOMETRY_CONTEXTUAL_OCCUPANCY_AND_PARENT_EVENT_ENDPOINTS',required_artifacts=['Source-matched successor DEF/LEF/OBS and pin-to-register placements after fully composed model; no failed qualification transfer','Owner model composition of existing SIMD/RF/glue area and every local/die wire event endpoint for both full calendars','Read-only retained floorplan track/OBS/PDN-via/route occupancy from source-matched SM context, or explicit empty-corridor reservation contract; no checkpoint payload needed','Pinned image make_tracks.tcl bytes matching the reference script; archived signal pin grids confirm M4/M5 phases only', 'Confirmed stock-cell implementation and counts within FF/control/clock/hold caps; bit-exact arithmetic and opt-in mapping; contextual SS/FF and port budgets after model admission'],current_geometry_result='Actionable conservative placements and explicit conditional slot/die costs; track availability and full-SM admission remain closed'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output');ap.add_argument('--check');args=ap.parse_args()
    b=(json.dumps(build(),sort_keys=True,indent=2)+'\n').encode()
    if args.check:
        if Path(args.check).read_bytes()!=b:raise SystemExit('geometry reproduction mismatch')
        print('PASS geometry reproduction; FAIL unchanged; no admission')
    elif args.output:
        p=Path(args.output)
        if p.exists():raise SystemExit('refuse to overwrite evidence')
        p.write_bytes(b)
    else:print(b.decode(),end='')

if __name__=='__main__':main()
