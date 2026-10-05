#!/usr/bin/env python3
"""Export reservations and parent contracts in the existing HBM floorplan.

No build, new die architecture, peer RTL writer, or clock/IO qualification.
"""
import contextlib
import hashlib
import io
import json
import math
import re
from pathlib import Path
import hbm_accel_die_fp as F
import hbm_accel_die_price as P
import uarch_model as U
from chip_assembly.v41_die import ASAP7_LAYERS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/hbm_child_contract_20261005'
CP='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_bind.sv'
W2='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv'
ASSOC='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_association.sv'
PARENT='rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv'


def ports(path):
    # This exporter accepts only the two literal-width ANSI module headers.
    header=(ROOT/path).read_text().split(');',1)[0].split(')(',1)[1]
    header=re.sub(r'//[^\n]*','',header)
    direction=None; width=1; out=[]
    for part in header.split(','):
        d=re.search(r'\b(input|output)\b',part)
        if d: direction=d.group(1); width=1
        w=re.search(r'\[(\d+):(\d+)\]',part)
        if w: width=abs(int(w[1])-int(w[2]))+1
        name=re.findall(r'\b[A-Za-z_]\w*\b',part)[-1]
        assert direction and name not in ('wire','input','output')
        out.append(dict(name=name,direction=direction,bits=width))
    return out


def rect_area(r): return (r[2]-r[0])*(r[3]-r[1])
def intersects(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def absolute(rect,parent): return [round(v+(parent.x if i%2==0 else parent.y),6) for i,v in enumerate(rect)]


def allocations(m):
    platform=json.loads((OUT/'inputs/platform_boundary_constants.json').read_text())
    cp_ports,w2_ports=ports(CP),ports(W2)
    assoc_ports=ports(ASSOC)
    # Do not assume mapped aliases/copy removal for the real association join.
    cp_ports += [dict(p,name='association/'+p['name']) for p in assoc_ports if p['name'] not in ('clk','por_n')]
    model=U.hbm_existing_die_child_model(cp_ports,w2_ports,platform)
    parent=m['hub']['cmdproc']
    for key,ps,instance in [('CP',cp_ports,'g_on.g_die[d].u_su_cp'),('W2',w2_ports,'g_on.g_die[d].u_w2_sink')]:
        c=model[key]
        c.update(logical_instance=instance,physical_reservation=f'hb_cmdproc/{key.lower()}',
                 core_bbox_um=absolute(c['core_relative_um'],parent),
                 gross_bbox_um=absolute(c['gross_relative_um'],parent),ports=ps,
                 optimisation_default_off=True,macro_abstract_installed=False)
    model['CP']['submodules']=[
        dict(instance='u_su_cp',source=CP,ports=ports(CP),
             relative_bbox_um=[600.48,43.2,643.68,82.08]),
        dict(instance='u_su_association',source=ASSOC,ports=assoc_ports,
             relative_bbox_um=[600.48,82.08,605.664,86.4],
             source_FF_bits=2,added_executor_admission_cycles=1)]
    model['parent']=dict(instance='hb_cmdproc',bbox_um=list(parent.box()),
                         source_snapshot=PARENT,clock_port='clk_sm',
                         original_claim_preserved=True,lower_metal='M6 horizontal/M7 vertical local exclusive reservation',
                         external_parent_trunks='M8/M9 over service block; no released PG or trunk credit')
    # No retained cells may occupy these lower-metal access channels. The old
    # outer M1-M7 OBS remains; child abstracts will replace it when integrated.
    channel_specs=[('CP','west_all',[557.28,43.2,600.48,86.4],'M6',set()),
                   ('W2','provider',[17.28,43.2,250.56,129.6],'M6',{'req','req_v','req_r','rsp','rsp_v','rsp_r'}),
                   ('W2','result',[250.56,302.4,336.96,345.6],'M7',{'result_v','result_op','result_row','result_data','native_done'}),
                   ('W2','metadata',[336.96,302.4,423.36,345.6],'M7',set())]
    used=set();channels=[]
    for key,name,rect,layer,names in channel_specs:
        ps=[p for p in model[key]['ports'] if p['name'] not in ('clk','por_n')]
        if key=='W2':
            if names: ps=[p for p in ps if p['name'] in names]; used |= names
            else: ps=[p for p in ps if p['name'] not in used]
        n=sum(p['bits'] for p in ps)
        info=next(x for x in ASAP7_LAYERS if x[0]==layer)
        # native die grid, not k16 bundle pilot pitch
        _,direction,pitch,_,_,offset=info
        ar=absolute(rect,parent)
        axis=1 if direction=='HORIZONTAL' else 0
        start=math.ceil((ar[axis]-offset)/pitch)
        stop=math.floor((ar[axis+2]-offset)/pitch)
        raw=stop-start+1; via=math.ceil(raw*F.VIA_OBS); clock=64
        available=raw-via-clock
        assert n<=available,(key,name,n,available)
        tracks=[];idx=start+via+clock
        for p in ps:
            for b in range(p['bits']):
                tracks.append(dict(port=p['name'],bit=b,coordinate_um=round(offset+idx*pitch,6)))
                idx+=1
        channels.append(dict(child=key,group=name,relative_bbox_um=rect,bbox_um=ar,
                             layer=layer,pitch_um=pitch,offset_um=offset,raw_tracks=raw,
                             via_escape_tracks_reserved=via,clock_other_tracks_reserved=clock,
                             competing_local_signal_tracks=0,
                             exclusive_reservation=True,available_signal_tracks=available,demand_tracks=n,
                             residual_tracks=available-n,pin_track_allocation=tracks,
                             ports=[p['name'] for p in ps]))
    model['channels']=channels
    claims=[model[k]['gross_relative_um'] for k in ('CP','W2')]
    claims += [model['retained_cmdproc_logic_relative_um'],model['gateway_relative_um']]
    for r in claims:
        assert 0<=r[0]<r[2]<=parent.w and 0<=r[1]<r[3]<=parent.h,r
    for i,a in enumerate(claims):
        for b in claims[i+1:]: assert not intersects(a,b),(a,b)
    for ch in channels:
        for r in claims[2:]: assert not intersects(ch['relative_bbox_um'],r),(ch['group'],r)
    # Two wire stages allocated for each source/receiver boundary path through
    # the finite gateway (<= 600um routed envelope), rather than free wires.
    model['boundary_transport']=dict(source_receiver_gateway_bbox_um=absolute(model['gateway_relative_um'],parent),
         routed_envelope_um=600,wire_stage_budget_each_direction=2,stage_quantum_um=430.56,
         extra_roundtrip_cycles_per_transaction_budget=4,roundtrip_target_ns=4/1.2,
         measured_wire_delay_ps=None,
         RTL_stage_installation='caller owner must insert/price transport cuts before clock qualification; reservation alone installs no FF',
         parent_port_binding='provider arbitration/response queue, result ingress, shared-owner lease and CP callbacks terminate at gateway; no extra memory port')
    model['allocation_checks']=dict(containment=True,claims_disjoint=True,retained_original_area=True,channels_fit=True)
    model['physical_launch_admitted']=False
    model['next_physical_step']='Harvey/Jason integrate their selected full port abstracts and propagated parent clk_sm/IO constraints; retain 60/25 and input hold checks. No empty wrapper timing qualification.'
    return model


def clock_sdc(ps,clock):
    inp=[p['name'] for p in ps if p['direction']=='input' and p['name'] not in ('clk','por_n')]
    out=[p['name'] for p in ps if p['direction']=='output']
    return '\n'.join([
      '# Candidate bounded parent clk_sm contract. Time ps; capacitance fF (ASAP7 native).',
      '# SS/FF required. Budget loads are analytical; replace with larger actual extracted loads.',
      '# No IO false paths. Root POR recovery/removal must be checked separately.',
      'create_clock -name clk_sm -period %.9f [get_ports clk]'%clock['period_ps'],
      'set_clock_uncertainty -setup 60 [get_clocks clk_sm]',
      'set_clock_uncertainty -hold 25 [get_clocks clk_sm]',
      'set_clock_latency -source 0 [get_clocks clk_sm]',
      'set_clock_latency -early 90 [get_clocks clk_sm]',
      'set_clock_latency -late 100 [get_clocks clk_sm]',
      'set ot_inputs [get_ports {'+' '.join(inp)+'}]',
      'set ot_outputs [get_ports {'+' '.join(out)+'}]',
      'set_input_delay -clock clk_sm -max %.9f $ot_inputs'%clock['input_delay_max_ps'],
      'set_input_delay -clock clk_sm -min 0 $ot_inputs',
      'set_output_delay -clock clk_sm -max %.9f $ot_outputs'%clock['output_delay_max_ps'],
      'set_output_delay -clock clk_sm -min 0 $ot_outputs',
      'set_load %.9f $ot_outputs'%clock['output_capacitance_budget_fF'],
      'set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ot_inputs',
      '# On integrated parent, use propagated clk_sm (remove estimated network latency),',
      '# actual source/receiver arcs and extracted loads; max skew budget10ps is not a waiver.',
      ''])


def export():
    OUT.mkdir(parents=True,exist_ok=True)
    m=F.build(F.variant_arg('service-attn-r1'))
    children=allocations(m)
    attn=U.hbm_existing_attention_allocation_model()
    old=F.build()
    legality=F.legality(m); assert legality['overlaps']==legality['outside']==0
    with contextlib.redirect_stdout(io.StringIO()):
        old_price=P.floor(old); new_price=P.floor(m)
    attn['geometry_wire_projection']=dict(old=old_price,revision=new_price,
             added_DS_die_wire_us=new_price['ds_added_us']-old_price['ds_added_us'],
             measured=False,changed_geometry_uses_old_route_evidence=False)
    # Layout for one tile replicated by the existing scan grid. Use real macro
    # pin OBS: M1-M7 blocked; M8/M9 overmacro remain after retained PG derating.
    leaf=294.782;pitch=leaf+10+43.2
    tile_macros=[dict(name=f'g_g[{4*r+c}].u_g',gid=4*r+c,orientation='R0',
                     relative_bbox_um=[5+c*pitch,5+r*pitch,5+c*pitch+leaf,5+r*pitch+leaf],halo_um=5)
                 for r in range(4) for c in range(4)]
    lef_path='physical/hbm_fmax_attn/ot_attn_hgrp_m6h1/ot_attn_hgrp_m6h1.lef'
    actual_leaf=F.S.real_lef(lef_path)
    assert actual_leaf['w']==actual_leaf['h']==294.782
    assert len(actual_leaf['pins'])==1662
    pin_faces={}
    for name,(layer,r) in actual_leaf['pins'].items():
        distances={'W':r[0],'S':r[1],'E':294.782-r[2],'N':294.782-r[3]}
        key=layer+':'+min(distances,key=distances.get)
        pin_faces[key]=pin_faces.get(key,0)+1
    caps={}
    for corner in ('ss','ff'):
        lib=(ROOT/lef_path.replace('.lef','_'+corner+'.lib')).read_text()
        caps[corner]={n:float(c) for n,c in re.findall(r'pin\("([^"\n]+)"\)\s*\{[^{}]*?capacitance\s*:\s*([\d.]+)',lib)}
    shared=[n for n in caps['ss'] if n not in ('clk','rst_n','VDD','VSS','ov') and not n.startswith(('gid[','oy[','oflt['))]
    assert len(shared)==1618
    attn['macro_pin_contract']=dict(LEF_signal_pins_per_head=1662,LEF_pin_faces=pin_faces,
          pin_rectangles_source=lef_path,SS_clock_cap_per_head_fF=caps['ss']['clk'],
          SS_clock_cap_per_tile_fF=16*caps['ss']['clk'],
          SS_reset_cap_per_tile_fF=16*caps['ss']['rst_n'],
          worst_shared_pin_cap_fF=max(caps['ss'][p] for p in shared),
          worst_unbuffered_16head_shared_load_fF=16*max(caps['ss'][p] for p in shared),
          per_shared_pin_cap_fF={p:max(caps[c][p] for c in caps) for p in shared},
          load_status='actual macro Liberty pin capacitance, excludes unmeasured parent route wire/receiver load',
          buffer_drive='tree leaves each drive one actual macro pin plus extracted wire; x2 count is area proxy, drive sizing not qualified',
          clock_distribution_buffer_cell_budget_um2=256*.10206,
          reset_distribution_buffer_cell_budget_um2=256*.10206,
          PG_retained=True,macro_pin_escape_route_qualified=False,
          input_hold='Leaf IO false paths leave timing arcs unqualified; Lagrange must supply real loaded input hold source/context before tile admission')
    # Conservative corner-to-corner broadcast transport stages, priced in
    # addition to the existing die-level first-access wire composition.
    old_length=6*(math.sqrt(.5e6)+43.2)
    new_length=6*(1349.136+43.2)
    fanout_cycles=math.ceil(new_length/430.56)
    old_fanout_cycles=math.ceil(old_length/430.56)
    attn['internal_fanout_transport']=dict(worst_manhattan_um=new_length,
           stages_budget=fanout_cycles,old_geometry_stages_budget=old_fanout_cycles,
           additional_cycles_per_first_input=fanout_cycles-old_fanout_cycles,
           additional_ns_per_first_input=(fanout_cycles-old_fanout_cycles)/1.2,
           buffers_no_automatic_zero_delay_credit=True,
           stage_installation='source owner must preserve aligned LD/operand/control beats; no cuts implemented by abstract')
    counts=P._ds_counts(json.loads((ROOT/F.MATCHED).read_text()))
    count=counts['attn']
    attn['composed_serial_latency_projection']=dict(
         attention_steps_per_matched_token=count,source=F.MATCHED,
         die_wire_floor_delta_us=new_price['ds_added_us']-old_price['ds_added_us'],
         exposed_internal_fanout_delta_upper_bound_us=count*(fanout_cycles-old_fanout_cycles)/1.2/1000,
         exposed_m6_vs_m4_core_delta_upper_bound_us=count*20/1.2/1000,
         total_increment_upper_bound_us=(new_price['ds_added_us']-old_price['ds_added_us'])+count*(fanout_cycles-old_fanout_cycles+20)/1.2/1000,
         core_delta_basis='Measured leaf62 vs historical leaf42; all20 extra cycles exposed conservatively per step, not measured full-job latency',
         fanout_delta_basis='Prices corner-to-corner stages beyond prior tile geometry; no overlap credit',
         measured=False,source_schedule_alignment_qualified=False)
    parent_text=(ROOT/PARENT).read_text()
    for name in ('u_su_cp','u_w2_sink'):
        assert re.search(name+r'\s*\([^;]*\.clk\(clk_sm\)[^;]*\.por_n\(rst_sm_n\)',parent_text,re.S)
    plan=F.plan_record(m)
    plan.update(revision='service-attn-r1',child_reservations=children,
                attention_macro_reservation=attn,attention_tile_children=tile_macros,
                legality=legality,adopted=False,clock_qualified=False,
                contextual_PNR_admitted=False,
                old_slot_fit=False,
                note='Revision of existing DS r14b; all old route/IR results remain historical and do not qualify this geometry.')
    model=dict(schema='opentallas.hbm-existing-die-revision.v1',children=children,attention=attn,
               die=plan['die'],legality=legality,
               full_token_physical_latency_qualified=False,headline_claim=False)
    # Append the current allocation to the unified record without changing any
    # historical failed slot verdict or its pinned source facts.
    unified_path=ROOT/'results/uarch/hbm_attn_m6h1_replication_20261005/model.json'
    unified=json.loads(unified_path.read_text())
    unified['existing_die_allocation']=dict(revision='service-attn-r1',
           record='results/rtl/hbm_child_contract_20261005/model.json',
           DS_head_macros=1024,Qwen_head_macros=0,
           tile_usable_outline_um=[1349.112,1349.976],die_mm2=plan['die']['mm2'],
           replica_footprint_fits=True,route_qualified=False,input_hold_qualified=False,
           contextual_PNR_admitted=False,
           note='Historical0.5mm2 slot_fit=false preserved; actual reservations now exist in same enlarged DS hub.')
    unified_path.write_text(json.dumps(unified,indent=2)+'\n')
    inputs=[CP,W2,ASSOC,PARENT,'tools/hbm_accel_die_fp.py','tools/uarch_model.py','tools/hbm_die_child_contract.py',
            'tools/chip_assembly/v41_die.py',
            'results/uarch/hbm_cp_balanced_veto_20261005/protected_clock_context_r1.json',
            'results/uarch/hbm_cp_balanced_veto_20261005/parent_functional_r1.json',
            'results/uarch/hbm_w2_publication_20261005/model.json',
            'results/uarch/hbm_attn_m6h1_replication_20261005/model.json',
            'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv',
            'rtl/hdc/ot_qwen_me_array_w12.sv',
            'rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12.sv',
            'results/rtl/hbm_child_contract_20261005/inputs/platform_boundary_constants.json']
    inputs += [str(p.relative_to(ROOT)) for p in (ROOT/'physical/hbm_fmax_attn/ot_attn_hgrp_m6h1').glob('*') if p.suffix in ('.lef','.lib','.json')]
    model['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs}
    for filename,record in [('model.json',model),('floorplan_revision.json',plan),('child_reservations.json',children)]:
        (OUT/filename).write_text(json.dumps(record,indent=2)+'\n')
    for key in ('CP','W2'):
        ps=ports(CP) if key=='CP' else children[key]['ports']
        (OUT/(key.lower()+'_parent_clk_sm.sdc')).write_text(clock_sdc(ps,children['clock']))
    (OUT/'cp_association_parent_clk_sm.sdc').write_text(clock_sdc(ports(ASSOC),children['clock']))
    qdir=OUT/'qwen_a_real'
    if (qdir/'run.log.exit').exists():
        import qwen_rom_fulldie as Q
        result=Q.record_a(qdir)
        result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in qdir.iterdir() if p.name!='result.json'}
        (qdir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('Qwen a_real:',{k:result[k] for k in ('exit','legality','track_assert','pin_access')})
    print('Existing DS die revision:',plan['die'],legality)
    print('Die wire floor us:',old_price['ds_added_us'],'->',new_price['ds_added_us'])
    print('Child signal bits:',children['CP']['external_signal_bits'],children['W2']['external_signal_bits'])


if __name__=='__main__': export()
