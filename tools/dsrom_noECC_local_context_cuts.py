#!/usr/bin/env python3
"""Source-sized local clock slots and expanded PDN/via exclusion construction.

Analytical G0 inputs; does not invoke physical tools or claim installed geometry.
"""
import hashlib,json,re
from pathlib import Path
from dsrom_noECC_complete_element import tracks
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_production_context_20261002'
PRIOR=ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
OLD=ROOT/'results/uarch/dsrom_noECC_complete_element_20261002'
def pdn(width,height):
    out=[]
    for y in range(0,height,270):out.append({'layer':'M2','net':'VDD' if y%540==0 else 'VSS','bbox_DBU':[0,max(0,y-9),width,min(height,y+9)],'kind':'followpin_270DBU_shadow'})
    for layer,direction,w,s,p,o in [('M5','V',120,72,2700,300),('M6','H',288,96,5400,513),('M7','V',288,96,10800,1000)]:
        for origin in range(o,width if direction=='V' else height,p):
            for i in (0,1):
                c=origin+i*(w+s);r=[c-w//2,0,c+w//2,height] if direction=='V' else [0,c-w//2,width,c+w//2]
                if 0<=r[0]<r[2]<=width and 0<=r[1]<r[3]<=height:out.append({'layer':layer,'net':'VDD' if i==0 else 'VSS','bbox_DBU':r,'kind':'source_stripe'})
    return out
def via_at(grid,stack,x,y):
    return [{'layer':r['layer'],'bbox_DBU':[r['bbox'][0]+x,r['bbox'][1]+y,r['bbox'][2]+x,r['bbox'][3]+y],'kind':'fixed_source_via_enclosure','via':v} for v in stack for r in grid['tech_via_definitions'][v]]
def source_vias(grid,stripes,cut):
    # Only vias whose enclosure/spacing may intersect this actual cut are
    # materialized; all same-net source stacks are counted independently.
    specs=[('M2','M5',['VIA23','VIA34','VIA45']),('M5','M6',['VIA56']),('M6','M7',['VIA67'])];out=[];counts={}
    for a,b,stack in specs:
        A=[s for s in stripes if s['layer']==a];B=[s for s in stripes if s['layer']==b];count=0
        for u in A:
            for v in B:
                if u['net']!=v['net']:continue
                r,t=u['bbox_DBU'],v['bbox_DBU'];x0=max(r[0],t[0]);x1=min(r[2],t[2]);y0=max(r[1],t[1]);y1=min(r[3],t[3])
                if x0>=x1 or y0>=y1:continue
                x=(x0+x1)//2;y=(y0+y1)//2;count+=1
                if abs(x-cut)<=2360:out.extend(via_at(grid,stack,x,y))
        counts[a+'_'+b]=count
    return out,counts
def macro_timing():
    root=ROOT/'results/uarch/dsrom_noECC_physical_transition_20261002/inputs'
    def body(text,start):
        pos=text.index('{',start);depth=1;j=pos+1
        while depth:
            depth+=(text[j]=='{')-(text[j]=='}');j+=1
        return text[pos+1:j-1]
    def values(b):
        return [float(v) for z in re.finditer(r'values\s*\((.*?)\);',b,re.S) for v in re.findall(r'[-+]?\d+(?:\.\d+)?',z[1])]
    out={}
    for corner in ('ss','ff'):
        p=root/('macro_'+corner+'.lib');text=p.read_text()
        if 'time_unit : "1ps"' not in text or 'capacitive_load_unit (1, ff)' not in text:raise ValueError('macro units changed')
        q=body(text,text.index('bus (rd_out)'));delay=[]
        for kind in ('cell_rise','cell_fall'):delay+=values(body(q,q.index(kind+' (mc_delay)')))
        clk=body(text,text.index('pin (clk)'))
        record={'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'clkQ_min_ps':min(delay),'clkQ_max_ps':max(delay),
            'minimum_period_ps':float(re.search(r'min_period : ([\d.]+)',clk)[1]),'minimum_high_pulse_ps':float(re.search(r'min_pulse_width_high : ([\d.]+)',clk)[1]),'minimum_low_pulse_ps':float(re.search(r'min_pulse_width_low : ([\d.]+)',clk)[1]),'clock_slew_table_axis_ps':[5,20,80,160,320],'output_load_axis_fF':[.72,2.88,11.52,23.04,46.08],'nominal_clock_period_ps':833.3333333333334}
        for pin in ('ce_in','addr_in'):
            b=body(text,text.index(('pin' if pin=='ce_in' else 'bus')+' ('+pin+')'));types={}
            for m in re.finditer(r'timing \(\)',b):
                t=body(b,m.start());typ=re.search(r'timing_type : (\w+)',t)[1];v=values(t);types[typ]={'min_ps':min(v),'max_ps':max(v)}
            record[pin]=types
        out[corner]=record
    out['constraints']={'SS_macro_to_selected_capture_setup_edges':2,'hold_launch_edge_unchanged':True,'capture_to_lane_setup_edges':1,'metadata_arithmetic_have_no_multicycle_exception':True,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'SS_data_budget_before_capture_setup_mux_wire_and_skew_ps':2*833.3333333333334-60-out['ss']['clkQ_max_ps'],'zero_parent_IO_disallowed':True,'reset_recovery_removal_and_clockgate_enable_checks_required':True}
    return out

def build():
    prod=json.loads((BASE/'model.json').read_text());ctx=json.loads((PRIOR/'context_terminal.json').read_text());join=json.loads((PRIOR/'model.json').read_text());grid=json.loads((OLD/'inputs/grid.json').read_text());out={}
    pdn_source=(OLD/'inputs/pdn.tcl').read_text()
    for clause in ('-layer {M5} -width {0.12} -spacing {0.072} -pitch {2.7} -offset {0.300}','-layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}','-layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {1.0}'):
        if clause not in pdn_source:raise ValueError('PDN contract changed')
    for k,c in prod['cases'].items():
        geo=ctx['cases'][k]['physical_geometry_contract'];j=join['cases'][k];width,h=j['outline_DBU'][2:];cut=geo['compute_control_clock_region_DBU'][0]
        new=pdn(width,h);vias,vcounts=source_vias(grid,new,cut);raw=geo['translated_macro_pin_OBS_PG']+new+vias
        cap=[]
        for layer in ('M2','M4','M6'):
            ys=tracks(grid,layer,'Y',h);rs=[s['bbox_DBU'] for s in raw if s['layer']==layer and s['bbox_DBU'][0]<=cut<=s['bbox_DBU'][2]]
            blocked={y for y in ys if any(r[1]<=y<=r[3] for r in rs)}
            cap.append({'layer':layer,'grid_tracks':len(ys),'blocked_by_pin_OBS_PG_and_source_via_shapes':len(blocked),'remaining_before_clock_signal_spacing':len(ys)-len(blocked)})
        # Source-existing local WAKE and ICG cells are assigned disjoint slots;
        # this is a proposed placement contract, not a placed-device claim.
        ff=c['named_physical_master_inventory']['DFFASRHQNx1_ASAP7_75t_R']['size_DBU'];gate=c['named_physical_master_inventory']['ICGx1_ASAP7_75t_R']['size_DBU'];slots=[]
        wake=c['actual_Verilog_WAKEDFF'];igs=c['actual_Verilog_ICG']
        from dsrom_noECC_production_context import cells,read
        allcells=cells(read(PRIOR/k/'retained_mapped.v.gz'))
        def pin(z,p):return re.search(r'\.'+p+r'\((.*?)\)',z['ports'])[1].strip()
        # Bind FF -> actual inverter -> actual leaf ENA; never rely on cell order.
        invs={pin(z,'Y'):pin(z,'A') for z in allcells if z['master'].startswith('INV')}
        qff={pin(z,'QN'):z for z in wake}
        byff={}
        for g in igs:
            leaf=int(re.search(r'g_leaf\[(\d+)\]',g['name'])[1]);ena=pin(g,'ENA')
            if ena not in invs or invs[ena] not in qff:raise ValueError('actual WAKE->ENA cone missing')
            byff[leaf]=qff[invs[ena]]
        if len({z['name'] for z in byff.values()})!=8:raise ValueError('eight distinct physical leaf owners required')
        byleaf={int(re.search(r'g_leaf\[(\d+)\]',g['name'])[1]):g for g in igs}
        for n in range(8):
            if n<4:x=cut+n*(ff[0]+gate[0]+108);y=270
            else:
                mb=(n-4)//2;bank=(n-4)%2
                i=next(i for i in geo['macro_instances'] if i['MB']==mb and i['bank']==bank)
                x=i['bbox_DBU'][2]+4320;y=i['bbox_DBU'][1]+270
            slots.extend([{'role':'sourceWAKE','leaf':n,'actual_instance':byff[n]['name'],'master':byff[n]['master'],'bbox_DBU':[x,y,x+ff[0],y+ff[1]],'included_in_mapped_area':True}, {'role':'sourceICG','leaf':n,'actual_instance':byleaf[n]['name'],'master':byleaf[n]['master'],'bbox_DBU':[x+ff[0],y,x+ff[0]+gate[0],y+gate[1]],'included_in_mapped_area':True}])
        for s in slots:
            r=s['bbox_DBU']
            if not (0<=r[0]<r[2]<=width and 0<=r[1]<r[3]<=h):raise ValueError('sourceclockslot outside completeframe')
        clock_lanes=[]
        # Actual M4 grid tracks; guard shapes use raw VIA34/45 wide-metal
        # 72DBU spacing and half24DBU clock width around PG enclosures.
        forbidden=[v['bbox_DBU'] for v in raw if v['layer']=='M4' and v['bbox_DBU'][0]<=cut+2160 and v['bbox_DBU'][2]>=cut-2160]
        for y in tracks(grid,'M4','Y',h):
            if y<108 or y>h-108:continue
            if any(r[1]-96<=y<=r[3]+96 for r in forbidden):continue
            if any(abs(y-z['center_y_DBU'])<144 for z in clock_lanes):continue
            clock_lanes.append({'center_y_DBU':y,'layer':'M4','wire_DBU':[cut-2160,y-12,cut+2160,y+12],'guard_DBU':[cut-2160,y-60,cut+2160,y+60]})
            if len(clock_lanes)==6:break
        if len(clock_lanes)!=6:raise ValueError('six sourceclock/control crossing lanes do not fit source PG/via window')
        floor=sum(v['BUF4_capacitance_only']['cell_count'] for v in ctx['cases'][k]['SS_FF_pin_loads']['ff'].values())*.10206
        residual=j['margin_before_CTS_wires_PGvias_um2']-2*floor
        signals=geo['required_source_catalog_tracks'];rawbudget=sum(v['remaining_before_clock_signal_spacing'] for v in cap if v['layer'] in ('M2','M4'))
        out[k]={'outline_DBU':j['outline_DBU'],'FF_root_and_branch_pin_buffer_floor_um2':floor,'residual_after_pin_buffer_floor_um2':residual,'Maxwell_composition_source':'5cc5b1029','installed_CTS_or_PDN_not_a_prebuild_requirement':True,'crossing_x_DBU':cut,'expanded_source_PDN_rectangles':new,'same_net_stack_counts':vcounts,'source_via_enclosures_near_cut':vias,'crossing_capacity':cap,'existing_catalog_signal_tracks':signals,'proposed_clock_control_cut_nets':['rootCLKto4fieldICGs_and4fieldWAKE','leaf0_capture_clock_to4fieldcapturestrips','WAKE4ENA','WAKE5ENA','WAKE6ENA','WAKE7ENA'],'clock_control_cut_net_count':6,'clock_cut_track_reservation':18,'clock_cut_lanes':clock_lanes,'actual_WAKEDFF_to_leafENA_bijection':{n:z['name'] for n,z in byff.items()},'clock_cut_scope':'six unique nets, one route+two guardtracks each; branch/slew/CTS mustvalidate, not inserted buffers or routedcapacity','remaining_M2_M4_after_catalog_and_clock_cut_before_spacing':rawbudget-signals-18,'source_clock_cell_slots':slots,'leaf_pin_loads_full_source':ctx['cases'][k]['SS_FF_pin_loads'],'buffer_counts_pin_only_source':ctx['cases'][k]['SS_FF_pin_loads'],'no_WAKEDFF_or_ICG_doublecharge':True,'added_cycles':0,'PG_is_sourceconstruction_not_installed':True,'fixed_via_centers_need_actual_ontrack_array_legalization':True,'signal_clock_pin_escape_spacing_not_zero':True}
    return {'candidate':prod['candidate'],'schema':'opentallas.dsrom.local-context-cuts.v1','production_model_sha256':hashlib.sha256((BASE/'model.json').read_bytes()).hexdigest(),'PDN_source_sha256':hashlib.sha256(pdn_source.encode()).hexdigest(),'grid_via_source_sha256':hashlib.sha256((OLD/'inputs/grid.json').read_bytes()).hexdigest(),'cases':out,'actual_macro_timing_source':macro_timing(),'installed_CTS_PDN_not_prebuild_requirement':True,'physical_admission_requires':['sourcebounded_clockwire/slew/branchbufferconstruction','pin/OBS/PG/via/spacing exclusion model','parentactualdriverarrival/slew/receiverload','SSmacroclkQ+FFhold endpoint-specificSDC'],'PnR_admitted':False,'no_build_invoked':True}
if __name__=='__main__':
    (BASE/'local_cuts.json').write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
