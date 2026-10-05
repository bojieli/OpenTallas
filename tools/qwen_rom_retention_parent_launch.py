#!/usr/bin/env python3
"""Additive retained85 launch/data-load pricing; preserves failed r1 evidence."""
import copy
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import qwen_rom_retention_physical_allocation as S
R=S.R
M=S.M
OUT=Path('results/uarch/qwen_rom_retention_parent_launch_20261002')


def constraint(cell,kind,transition,data_slew,clock_slew):
    blocks=[R.C.block(cell,m.start()) for m in re.finditer(r'\btiming\s*\(',cell)]
    blocks=[b for b in blocks if re.search(r'timing_type\s*:\s*'+kind+r'_rising',b)]
    values=[]
    for block in blocks:
        for table in R.tables(block,transition+'_constraint'):
            for d in (data_slew[0],data_slew[1]):
                for c in (clock_slew[0],clock_slew[1]):
                    values.append(R.interpolate(table,d,c))
    if not values:raise ValueError('missing actual FF constraint')
    return max(values)


def launch_graph(g):
    g=copy.deepcopy(g);cells=g['added_primitive_cells'];coords=g['nominal_node_coordinates_um']
    sink=R.price()['provider']['actual_ib_go_first_mapped_sink']['instance']
    origin=coords['context_provider'];target=coords[sink]
    distance=max(16,sum(abs(a-b) for a,b in zip(origin,target)))
    count=math.ceil(distance/128)
    bit=max(b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
    for i in range(count):
        name='retained_launch_segment'+str(i)
        cells[name]=dict(type=R.BUF,connections=dict(A=[bit-1] if i else ['SOURCE_PROVIDER_LAUNCH'],Y=[bit]))
        coords[name]=[origin[d]+(target[d]-origin[d])*i/count for d in (0,1)]
        if i:g['wire_edges'].append(dict(driver='retained_launch_segment'+str(i-1),sink=name,pin='A',length_um=distance/count))
        bit+=1
    g['wire_edges'].append(dict(driver=name,sink=sink,pin='D',length_um=distance/count))
    g['original_cell_pin_edits'].setdefault(sink,{})['D']=[bit-1]
    g['launch_route']=dict(actual_sink=sink,provider_to_sink_distance_um=distance,
        provider_to_first_buffer_um=16,added_buffers=count,source_driver='provider buffered AND3 launch output',
        functional_data_binding_qualified=False)
    return g


def data_price(g):
    result={}
    for corner in ('ss','ff'):
        _,lib,caps=R.library(corner);bufcap=caps[(R.BUF,'A')]['cap_fF'];inv=lib[S.INV];ff=lib[R.ASR]
        rows=[]
        for row in g['source_control_cells']:
            # Bank QN also feeds the three existing source strobe buffers.
            # Restoration drives one code_sel_q2 CE mux; mask restoration
            #drives its constructed selector tree. These are reserved routes.
            qcap=row['restoring_INV_input_cap_fF'][corner]
            if row['role']=='bank_strobe':qcap+=3*(bufcap+16*.165790)
            invcap=(bufcap if row['role']=='mask' else M.pin_cap('NAND2xp33_ASAP7_75t_R','A',corner))+(2 if row['role']=='mask' else 3)*.165790
            q={t:R.envelope(ff,'cell_'+t,qcap,related='CLK') for t in ('rise','fall')}
            qs={t:R.envelope(ff,t+'_transition',qcap,related='CLK') for t in ('rise','fall')}
            delay={};slew={}
            for t,related in (('rise','fall'),('fall','rise')):
                delay[t]=R.envelope(inv,'cell_'+t,invcap,*qs[related])
                slew[t]=R.envelope(inv,t+'_transition',invcap,*qs[related])
            if max(s[1] for s in slew.values())>320:raise ValueError('restoring INV slew failure')
            rows.append(dict(instance=row['instance'],QN_total_cap_fF=qcap,INV_output_cap_fF=invcap,
                QN_clkq_minmax_ps=q,restoring_INV_delay_minmax_ps=delay,restoring_INV_slew_minmax_ps=slew,
                INV_output_wire_um=2 if row['role']=='mask' else 3,route_cap_is_reserved_not_extracted=True,bank_strobe_QN_existing_BUF_sinks=3 if row['role']=='bank_strobe' else 0))
        # All80 mask selector buffer trees are actually LUT evaluated, from
        #the INV output slew, through finite edges to33declared loads each.
        seeds={r['instance']+'.selector_driver':{t:[0,0,*r['restoring_INV_slew_minmax_ps'][t]] for t in ('rise','fall')}
               for r in rows if '.g_mask[' in r['instance']}
        states,_,loads=M.propagate(g,{'cells':{}},corner,seeds)
        result[corner]=dict(source_cells=rows,selector_buffer_max_load_fF=max(loads.values()),
            selector_consumer_pins=sum(':A' in n and '.consumer' in n for n in states),
            source_QN_and_INV_loads_characterized=True,whole_data_setup_hold_qualified=False)
    return result


def launch_price(g,net):
    result={};p=R.price();sink=g['launch_route']['actual_sink']
    for corner in ('ss','ff'):
        _,lib,caps=R.library(corner)
        ck,_,_=M.propagate(g,net,corner,{'bind_clock_entry':{t:[0,0,5,80] for t in ('rise','fall')}})
        source=ck['context_provider:clk_stream']['rise'];capture=ck[sink+':CLK']['rise']
        join=p['provider_LUT_envelopes'][corner]
        cap=caps[(R.BUF,'A')]['cap_fF']+16*.165790
        delay={t:R.envelope(lib[R.BUF],'cell_'+t,cap,*join['launch_join_slew_minmax_ps']) for t in ('rise','fall')}
        slew={t:R.envelope(lib[R.BUF],t+'_transition',cap,*join['launch_join_slew_minmax_ps']) for t in ('rise','fall')}
        seeds={'retained_launch_segment0':{t:[join['launch_join_rise_minmax_ps'][0]+delay[t][0],
            join['launch_join_rise_minmax_ps'][1]+delay[t][1],*slew[t]] for t in ('rise','fall')}}
        waves,_,loads=M.propagate(g,net,corner,seeds)
        w=waves[sink+':D']['rise']
        setup=constraint(lib[R.ASR],'setup','rise',w[2:],capture[2:])
        hold=constraint(lib[R.ASR],'hold','rise',w[2:],capture[2:])
        lower=capture[1]-source[0]+hold+25-w[0]
        upper=833.3333333333334+capture[0]-source[1]-setup-60-w[1]
        result[corner]=dict(source_CLK_minmax_ps=source[:2],actual_capture_CLK_minmax_ps=capture[:2],
            finite_route_delay_minmax_ps=w[:2],capture_D_slew_minmax_ps=w[2:],setup_constraint_ps=setup,hold_constraint_ps=hold,
            required_external_go_ready_arrival_after_provider_CLK_ps=[lower,upper],
            proposed_local_source_window_ps=[50,650],proposed_source_window_pass=50>=lower and 650<=upper,
            clock_period_ps=833.3333333333334,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            max_BUF_cap_fF=max(loads.values()),source_arrivals_observed=False,contextual_SSFF=False)
    return result


def main():
    out=R.ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    if (out/'model-r1.json').exists():raise ValueError('preserve existing verdict')
    g=json.loads(gzip.decompress((R.ROOT/S.OUT/'successor-allocation-r1.json.gz').read_bytes()))
    raw=(R.LIVE/'mapped.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=M.MAP_SHA:raise ValueError('different map')
    net=json.loads(raw)['modules']['ot_qwen_rom_fulltile_tp4_context_top']
    # Clock graph is fully carried in g; original deleted FFs never reappear.
    for name in g['removed_old_control_FFs']:net['cells'].pop(name)
    for row in g['source_control_cells']:net['cells'][row['instance']]=dict(type=R.ASR,connections={})
    data=data_price(g);g=launch_graph(g);launch=launch_price(g,net)
    baseline=R.obj(M.OUT/'model-r1.json');successor=R.obj(S.OUT/'model-r1.json')
    result=dict(successor,schema='QWEN_RETAINED85_COMPOSED_CONTEXT_V2',
        baseline_clock_balance_failure={c:dict(clock_sinks=102299,reset_sinks=56630,
          clock_minmax_ps=r['clock_arrival_minmax_ps'],span_ps=r['clock_arrival_minmax_ps'][1]-r['clock_arrival_minmax_ps'][0],
          clock_skew_target_ps=20,status='FAIL_NOMINAL_CLOCK_BALANCE',balanced_CTS=False) for c,r in baseline['timing_preflight'].items()},
        restoring_data_load_price=data,actual_parent_launch=launch,launch_route=g['launch_route'],
        conservative_reserved_area_um2=successor['conservative_reserved_area_um2']+g['launch_route']['added_buffers']*.10206,
        external_RESETN_source_requirement=dict(deassert_after_primary_clock_ps=[262,823],minimum_low_pulse_ps=359,
            input_slew_ps=[5,80],scope='Root input route only; successor reset endpoints FAIL and this is not a complete startup protocol'),
        mapped_provider_extra_clock_sinks=2,mapped_provider_extra_reset_sinks=2,
        finite_macro_input_CLOCK_ports=12,
        persistent_KV=R.obj(R.C.OUT/'model-r1.json')['persistent_KV'],
        current_once_calendar=R.obj(R.C.OUT/'model-r1.json')['current_once_calendar'],
        finite_data_route_proof_scope='85restoring INV loads and80mask selector trees characterized. Source expressions and bank strobe routes remain source-allocation constraints, not full semantic data graph proof.',
        selected_model_extension='qwen-retained85-composed-context',source_map_admission=False,
        next_construction='Balanced source clock and metadata reset allocation at these actual positions; then recompute launch window/startup and prove binary/init and semantic graph before single admitted source map.')
    payload=gzip.compress(R.canon(g),mtime=0);(out/'composed-allocation-r1.json.gz').write_bytes(payload)
    result['composed_allocation_sha256']=hashlib.sha256(payload).hexdigest()
    M.write(out/'model-r1.json',result)
    paths=[Path(__file__).relative_to(R.ROOT),Path('tests/test_qwen_rom_retention_parent_launch.py'),Path('tools/uarch_model_qwen_retained_context.py'),
        S.OUT/'model-r1.json',S.OUT/'sourcepins-r1.json',S.OUT/'successor-allocation-r1.json.gz',M.OUT/'sourcepins-r1.json',R.C.OUT/'model-r1.json',R.C.OUT/'sourcepins-r1.json']
    M.write(out/'sourcepins-r1.json',dict(sha256={str(p):M.digest(p) for p in paths}))
    M.write(out/'artifact-sha256-r1.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='artifact-sha256-r1.json'})
    print(json.dumps(dict(status=result['status'],area=result['conservative_reserved_area_um2'],launch=launch),indent=2))

if __name__=='__main__':main()
