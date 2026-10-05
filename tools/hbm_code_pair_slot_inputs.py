#!/usr/bin/env python3
"""Source-bound isolated CODE-pair inventory, slots, pins and timing budgets.

No RTL, synthesis, STA or P&R. Pauli owns the actual wrapper and physical run;
Erdos/Sagan own any capture cut. This is not a production-parent contract.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('results/uarch/hbm_accel_fulldie_inputs_20261004/code_pair_slot')


def build(root,out):
    refs={}
    def raw(path):
        p=root/path
        b=p.read_bytes() if p.exists() else subprocess.check_output(['git','show','HEAD:'+str(path)],cwd=root)
        refs[str(path)]=hashlib.sha256(b).hexdigest()
        return b.decode()
    def obj(path): return json.loads(raw(Path(path)))
    leaf=obj('results/uarch/qwen_hbm_code_payload_leaf_20261005/model.json')
    for p in ['rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair.sv',
              'rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair_banklocal.sv',
              'rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_read_pipeline.sv',
              'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv']:
        raw(Path(p))
    assert refs['rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair_banklocal.sv']=='8b713f7c9d1af826e3316e5cd18c5e768e1c1b81f7f6225e8d3e1d68bc90a516'
    macros={}
    for typ in ['1024x256_m2','128x256_m1']:
        name='ot_sram_1r1w_'+typ+'_r2c2';base=Path('physical/asap7_memory_macros')/name
        m=obj(base/(name+'.json'));lef=raw(base/(name+'.lef'))
        for suffix in ['_ss.lib','_ff.lib','_bb.v']:raw(base/(name+suffix))
        pins={}
        for match in re.finditer(r'  PIN (\S+)\n(.*?)  END \1',lef,re.S):
            n,s=match.groups()
            if 'USE POWER' in s or 'USE GROUND' in s: continue
            layer=re.search(r'LAYER (\S+)',s)[1]
            rect=[float(v) for v in re.search(r'RECT ([\d. ]+) ;',s)[1].split()]
            pins[n]=dict(layer=layer,xy_um=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2])
        assert len(pins)==m['area']['outline']['signal_pins']
        macros[name]=dict(metadata=m,pins=pins,base=str(base))
    data_name=leaf['data_macro'];check_name=leaf['check_macro']
    area=10*macros[data_name]['metadata']['area']['macro_area_um2']+10*macros[check_name]['metadata']['area']['macro_area_um2']
    assert abs(area-162057.8664)<1e-7
    inventory=[];macro_pins=[]
    for p in range(2):
        x=8.64+p*473.472
        for b in range(5):
            y=8.64+b*96.66
            for name,instance,mx,orientation in [(data_name,'data_store',x,'MY'),(check_name,'check_store',x+278.424,'R0')]:
                m=macros[name];a=m['metadata']['area'];w=a['macro_width_um'];h=a['macro_height_um']
                inst=f'u_leaf.on.column[{p}].bank[{b}].{instance}'
                inventory.append(dict(instance=inst,master=name,orientation=orientation,box_xywh_um=[mx,y,w,h],halo_um=2.16))
                for pin,v in m['pins'].items():
                    px,py=v['xy_um'];px=w-px if orientation=='MY' else px
                    macro_pins.append(dict(instance=inst,pin=pin,layer=v['layer'],xy_um=[round(mx+px,6),round(y+py,6)]))
    # Literal wrapper ABI agreed by Pauli; no boundary data registers added.
    inputs={'clk':1,'por_n':1,'wr_v':1,'wr_owned':465,'wr_span_bound':1,'wr_kind':1,
            'wr_row':13,'wr_column':12,'visible_r':1,'rd_v':2,'rd_span_bound':2,
            'rd_published':2,'rd_row':26,'virtual_bank':6}
    outputs={'wr_r':1,'visible_v':1,'visible_id':192,'visible_tag':12,'visible_beat':5,
             'visible_row':13,'visible_column':12,'rd_r':2,'rd_corrected':2,
             'rd_uncorrectable':2,'rsp_v':2,'rom_rd':2660,'fault':1}
    boundary=[];north=0;east=0
    for direction,ports in [('input',inputs),('output',outputs)]:
        for n,width in ports.items():
            for i in range(width):
                pin=n if width==1 else f'{n}[{i}]'
                if n=='rom_rd':xy=[863.958,40.044+east*.192];layer='M4';east+=1
                else:xy=[26.892+north*.192,673.878];layer='M5';north+=1
                boundary.append(dict(name=pin,direction=direction,layer=layer,xy_um=[round(z,6) for z in xy],
                    constant_zero=(n=='rom_rd' and i%266>=256)))
    assert len(boundary)==3439 and east==2660
    assert len({(p['layer'],tuple(p['xy_um'])) for p in boundary})==3439
    assert all(0<p['xy_um'][0]<864 and 0<p['xy_um'][1]<673.92 for p in boundary)
    # Actual macro obstructions prohibit M1..M4 over their bodies. Open
    # corridors use M3/5/7/9 vertical, M4/6/8 horizontal; reserve half tracks.
    vcap=lambda w:sum(math.floor(math.floor(w/p)/2) for p in [.036,.048,.064,.080])
    hcap=lambda h:sum(math.floor(math.floor(h/p)/2) for p in [.048,.064,.080])
    channels=[]
    for p in range(2):
        channels.append(dict(name=f'column{p}.raw_read_write_mux',box_xywh_um=[183.384+p*473.472,8.64,103.68,457.11],
            vertical_signal_tracks=vcap(103.68),demand_tracks=3392,
            demand_terms=dict(raw_read_outputs=5*2*256,write_data_checks_masks=3*256,
                read_write_row_addresses=23,select_handshake_control=40,clock=1)))
    channels.append(dict(name='pair.context_and_boundary',box_xywh_um=[8.64,492.48,846.72,172.8],
        horizontal_signal_tracks=hcap(172.8),demand_tracks=3334,
        demand_terms=dict(steered_payload=2560,visible_metadata=237,owned_write=465,controls=72)))
    channels.append(dict(name='pair.shared_vertical',box_xywh_um=[381.888,8.64,100.224,457.11],
        vertical_signal_tracks=vcap(100.224),demand_tracks=3334,
        demand_terms=dict(steered_payload=2560,visible_metadata=237,owned_write=465,controls=72)))
    for c in channels:assert c.get('horizontal_signal_tracks',c.get('vertical_signal_tracks'))>=c['demand_tracks']
    assert hcap(70.47)>=829+819
    # Positive gross operator estimates, no synthesis-removal/sharing credit.
    xor=.17496;nand=.08748;mux=4*nand
    data_positions=[i for i in range(1,72) if i&(i-1)]
    enc_xor=sum(max(0,sum(bool(i&(1<<k)) for i in data_positions)-1) for k in range(7))+70
    dec_xor=sum(sum(bool(i&(1<<k)) for i in range(1,72))-1 for k in range(7))+71
    encode_area=enc_xor*xor
    decode_area=dec_xor*xor+72*12*nand+72*mux+20*nand
    cells=dict(protected1008_FF_floor=1008*.2916,
        protected1008_FF_reset_upsize_reserve=1008*(.37908-.2916),
        encode64_10calls_gross=10*encode_area,decode64_14calls_gross=14*decode_area,
        data_and_check_5bank_mux_gross=2*2*256*4*mux,
        check_8way_shift_gross=2*256*3*mux,
        protected_read_hold_mux_gross=576*mux,
        fixed_pipeline2560_payload_steering_proxy=2560*4,
        address_auth_visible_decode_proxy=1024*.2,
        clock_reset_select_write_buffers_reserve=2048*.4374,
        CTS_route_IR_repair_reserve=4096*.4374)
    core_area=846.72*656.64
    halo_area=sum((m['box_xywh_um'][2]+4.32)*(m['box_xywh_um'][3]+4.32)-m['box_xywh_um'][2]*m['box_xywh_um'][3] for m in inventory)
    standard_capacity=(core_area-area-halo_area)*.55
    assert standard_capacity>sum(cells.values())
    dm=macros[data_name]['metadata'];cm=macros[check_name]['metadata']
    remaining=833.333333-60-dm['timing']['ss']['clk_to_q_ps']
    fo4=dm['timing']['ss']['breakdown']['fo4_ps']
    # Three balanced MUX2 levels, each two FO4: conservative analytical proxy,
    # neither a mapped minimum nor a timing measurement. Wire is charged
    # separately; the full source cannot be admitted merely on area/track fit.
    timing=dict(core_period_ps=833.333333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        macro_data_SS_clkQ_ps=dm['timing']['ss']['clk_to_q_ps'],
        macro_check_SS_clkQ_ps=cm['timing']['ss']['clk_to_q_ps'],
        data_macro_to_capture_available_before_setup_wire_skew_ps=remaining,
        existing5bankmux_proxy_ps=3*2*fo4,proxy_basis='3 balanced MUX2 levels at 2 actual SS FO4 each; estimate, not mapped lower bound',
        maximum_bank_to_common_capture_vertical_span_um=228.555,
        local_escape_width_um=103.68,
        positive_wire_and_clock_skew_reserve_ps=20,
        available_for_actual_mux_and_capture_setup_ps=remaining-20,
        existing_schedule_read_edges=2,II_edges=1,read_bytes_per_edge=64,
        latency_ns=2*833.333333/1000,added_edges_against_original_tile_macro=1,
        macro_clock_load_SS_fF=20*dm['timing']['ss']['clk_cap_ff'],
        standard_state_clock_load_TT_proxy_fF=1008*.474736,
        FF_macro_hold_ps=dm['timing']['ff']['hold_ps'],
        SS_macro_min_period_ps=dm['timing']['ss']['min_period_ps'],
        actual_capture_setup_and_mux_delay_measured=False,
        route_admitted=False,
        verdict='EXISTING_CONTEXT_OVER_CONSERVATIVE_TIMING_BUDGET_SOURCE_OWNER_CUT_OR_ACTUAL_MAPPED_PRICE_REQUIRED')
    # Source-owner option only: bank-local capture on the SAME E2 edge.
    cut=dict(selected=True,owners=['Erdos leaf','Sagan tile/tags'],Pauli_scope='physical only',
        read_capture_bits=2*5*288,added_coded_FF_bits=2304,
        held_output_physical_bank_bits_added=6,held_output_bank_coded_FF_added=0,
        held_output_bank_storage='6 payload bits in existing 72-bit protected control, within unused64-bit payload padding',
        read_edges=2,II_edges=1,additional_edges=0,
        required_schedule='Each selected bank captures assembled data/check under old accepted read, bank/check tags at E2. At same E2 store old physical bank into protected output-bank tags; select coded288 after registers then unchanged decode. Virtual-bank pipeline unchanged; consumer drains and retains original MEM_EXTRA/+1 alignment.',
        costs_um2=dict(added_FF_floor=2304*.2916,added_hold_mux=2304*mux,
            additional_bank_local_8way_check_shift=2*4*256*3*mux,
            gross_postcapture5bank288_mux=2*288*4*mux,
            bank_enable_and_output_tag_logic_reserve=256*.2,
            additional_clock_enable_fanout_buffer_reserve=1024*.4374,
            additional_CTS_route_IR_repair_reserve=2048*.4374),
        old_mux_removal_credit_um2=0,additional_standard_clock_load_TT_proxy_fF=2304*.474736,
        data_macro_to_banklocal_capture_distance_target_um=30.24,
        banklocal_check_capture_available_before_setup_wire_ps=833.333333-60-cm['timing']['ss']['clk_to_q_ps'],
        remaining_timing_gates=['data clkQ + capture hold mux + setup + local wire within81.562ps',
            'local check8:1 shift into protectedcapture','postcapture bank mux + unchanged ECC decode +2560 steering',
            'protected metadata/control feedback and all FF25 hold paths'],
        arithmetic_and_ACK_unchanged_required=True,exactness_unmeasured=True)
    # Bind real installed RC and standard-cell pin/cell authorities. The
    # fixed load is a declared isolated receiver equivalent, not a production
    # parent or an SS characterization inferred from TT.
    authority_dir=out/'authorities'
    authority_dir.mkdir(parents=True,exist_ok=True)
    rc_path=Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/setRC.tcl')
    rc_raw=rc_path.read_bytes()
    (authority_dir/'setRC.tcl').write_bytes(rc_raw)
    refs[str(BASE/'authorities/setRC.tcl')]=hashlib.sha256(rc_raw).hexdigest()
    seq_path=Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib')
    buf_path=Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib')
    standard_authority=dict(grade='TT pin/area authority only, not SS timing',
        sources={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [seq_path,buf_path]},
        library_units=dict(time='ps',capacitance='fF',resistance='kohm'),
        DFFHQNx1=dict(area_um2=.2916,D_cap_fF=.558822,CLK_cap_fF=.474736),
        DFFASRHQNx1=dict(area_um2=.37908),BUFx2=dict(area_um2=.0729,A_cap_fF=.534279),
        BUFx24=dict(area_um2=.4374))
    (authority_dir/'standard_cell_pins.json').write_text(json.dumps(standard_authority,indent=2)+'\n')
    refs[str(BASE/'authorities/standard_cell_pins.json')]=hashlib.sha256((authority_dir/'standard_cell_pins.json').read_bytes()).hexdigest()
    # Literal M4/M5 local route:19.44um horizontal+10.8um bit-alignment detour,
    # twoV4+oneV5. Elmore estimate includes macro SS driver resistance and a
    # real DFF D-pin load proxy. Capture-enable mux input/setup require STA.
    cx=.178475*19.44;cy=.164264*10.8
    rx=.0180365*19.44;ry=.0189935*10.8
    via=2*.0118+.0082
    cwire=cx+cy;load=.558822
    wire_delay=dm['timing']['ss']['out_r_kohm']*(cwire+load)+.5*(rx+ry)*cwire+(rx+ry+via)*load
    local_regions=[]
    for p in range(2):
        for b in range(5):
            x=183.384+p*473.472;y=8.64+b*96.66
            local_regions.append(dict(name=f'column{p}.bank{b}.protected_capture',
                box_xywh_um=[x+2.16,y,17.28,51.84],coded_FF_bits=288,
                cell_capacity_um2=17.28*51.84*.55,
                gross_local_cell_budget_um2=288*(.37908+mux)+256*.2+64*.4374+50,
                members='new bank-local288 coded FFs, their hold muxes and bank enable; exact synthesized names owned by Pauli/Erdos'))
            local_regions.append(dict(name=f'column{p}.bank{b}.check_slot_select',
                box_xywh_um=[x+66.96,y,34.56,70.47],
                cell_capacity_um2=34.56*70.47*.55,
                gross_local_cell_budget_um2=256*3*mux+256*.0729+64*.4374,
                members='new bank-local actual8:1 check slot selector; no parity RAM idealization'))
    assert all(r['cell_capacity_um2']>=r['gross_local_cell_budget_um2'] for r in local_regions)
    cut.update(local_placement_regions=local_regions,
        total_coded_state_bits_including_fixed_pipeline=3312,
        total_macro_and_standard_clock_load_proxy_fF=20*8.68376+3312*.474736,
        local_wire_price=dict(horizontal_um=19.44,vertical_um=10.8,wire_cap_fF=cwire,
            wire_resistance_kohm=rx+ry+via,driver_SS_out_r_kohm=dm['timing']['ss']['out_r_kohm'],
            receiver_D_cap_TT_proxy_fF=load,Elmore_delay_ps_ESTIMATE=wire_delay,
            additional_nonideal_wire_coupling_detour_reserve_ps=5,
            clock_skew_reserve_ps=10,zero_wire_credit=False),
        capture_hold_mux_proxy_ps=2*fo4,
        data_capture_available_for_actual_setup_ps=remaining-2*fo4-wire_delay-15,
        check_slot_select_proxy_ps=3*2*fo4,
        check_capture_available_for_actual_setup_wire_ps=833.333333-60-cm['timing']['ss']['clk_to_q_ps']-3*2*fo4-2*fo4-10,
        postcapture_path_estimates=dict(bank5mux_ps=3*2*fo4,
            W6_decode_proxy_ps=(7*2+3+2)*fo4,
            virtual_steering_proxy_ps=2*fo4,
            positive_wire_and_clock_skew_reserve_ps=30,
            available_including_launchclkQ_before_isolated_output_delay_ps=833.333333-60-120,
            measured=False,grade='gross FO4 proxies are not mapped cell minimums; cannot claim SS closure'))
    # The short data path requires BIT locality, not just a rectangular fence.
    # Source owner supplies the new logical FF array mapping after RTL; Pauli
    # resolves actual synthesized cells. No unknown generated names are guessed.
    capture_targets=[]
    for p in range(2):
        for b in range(5):
            x=183.384+p*473.472;y=8.64+b*96.66
            for k in range(4):
                j=0;parity_index=0
                for pos in range(1,73):
                    coded_bit=k*72+pos-1
                    data_bit=None
                    if pos<=71 and pos&(pos-1):
                        data_bit=k*64+j;j+=1
                        source=next(v for v in macro_pins if v['instance']==f'u_leaf.on.column[{p}].bank[{b}].data_store' and v['pin']==f'rd_out[{data_bit}]')
                        dy=round((source['xy_um'][1]-y)/.27)*.27
                        target=[x+2.7+(j%8)*1.08,y+dy]
                    else:
                        # Eight parity positions per64-bit chunk, sourced from
                        # local8:1 check slot selector, not data SRAM pins.
                        source=None;target=[x+12.42+(parity_index%3)*1.08,y+2.7+k*6.21+(parity_index//3)*.27];parity_index+=1
                    capture_targets.append(dict(column=p,bank=b,coded_bit=coded_bit,
                        data_macro_bit=data_bit,source_pin=source,
                        logical_register=f'u_leaf.on.captured_code[{p}][{b}][{coded_bit}]',
                        preferred_capture_D_xy_um=[round(z,6) for z in target],
                        required_data_route_length_um=30.24 if data_bit is not None else 120,
                        synthesized_cell_mapping_required=True))
    assert len(capture_targets)==2880
    assert len({tuple(t['preferred_capture_D_xy_um']) for t in capture_targets})==2880
    unconstrained_v=51.84-1.932
    unconstrained_h=19.452
    cc=.178475*unconstrained_h+.164264*unconstrained_v
    rr=.0180365*unconstrained_h+.0189935*unconstrained_v
    worst=dm['timing']['ss']['out_r_kohm']*(cc+load)+.5*rr*cc+(rr+via)*load
    cut['local_wire_price'].update(bit_locality_targets_required=True,
        unconstrained_region_distance_um=unconstrained_h+unconstrained_v,
        unconstrained_region_Elmore_delay_ps_ESTIMATE=worst,
        data_short_route_is_placement_requirement_not_measured=True)
    # Bound check-slot local escape separately: macro->nearby selector->parity
    # capture may span up to120um. Upper M6/M7 routing remains outside M4 body
    # OBS. No check parity wire is credited free.
    check_c=.187426*80+.162979*40
    check_r=.0118796*80+.0125096*40+3*.0082
    check_delay=cm['timing']['ss']['out_r_kohm']*(check_c+load)+.5*check_r*check_c+check_r*load
    cut['check_slot_wire_price']=dict(horizontal_M6_um=80,vertical_M7_um=40,
        cap_fF=check_c,resistance_kohm=check_r,Elmore_delay_ps_ESTIMATE=check_delay,
        coupling_detour_reserve_ps=10,actual_mapped_delay_measured=False)
    cut['check_capture_available_for_actual_setup_wire_ps']-=check_delay+10
    cut['additional_state_upsize_reserve_um2']=2304*(.37908-.2916)
    cut['costs_um2']['additional_state_upsize_reserve']=cut['additional_state_upsize_reserve_um2']
    # Fault/quarantine cannot bypass the physical output timing budget.
    # Literal UE4->read_bad->leaf fault, pipeline mismatch/control fault,
    # paired response qualification and each1280-bit steer are priced.
    cells['fault_rsp_fanout_buffers_reserve']=128*.4374
    cells['output_bank_select_fanout_buffers_reserve']=256*.4374
    cells['UE_fault_qualification_logic_gross_proxy']=512*.2
    cells['control_encode_decode_feedback_fanout_reserve']=256*.2
    cut['postcapture_path_estimates'].update(
        leaf_UE_to_fault_proxy_ps=6*fo4,
        pipeline_fault_and_rsp_qualification_proxy_ps=5*fo4,
        fault_to1280_per_column_buffer_tree_proxy_ps=2*fo4,
        fault_steering_gate_proxy_ps=2*fo4,
        response_qualifier_fanout_per_column=1280,
        control_decode_on_physical_bank_select_proxy_ps=19*fo4,
        parity_syndrome_terms_source='7 parity checks each up to36inputs plus overall72; nonzero/<=71 and dynamic bit flip preserved',
        independent_required_cones=['protected physicalbankcontrol decode->5mux->payloaddecode',
            'UE->leaf fault->pipeline fault/responsequalifier->1280-bit steering',
            'pipeline protectedcontrol decode->bankcompare/valid->virtualsteer',
            'protectedleafcontrol decode/nextstate/encode feedback',
            'visible metadata4decode/UE->fault + metadata4encode write feedback'])
    near_logic=[]
    for p in range(2):
        near_logic.append(dict(name=f'column{p}.coded_mux_and_W6',
            box_xywh_um=[8.64+p*473.472,177.93,373.248,21.6],
            members='postcapture coded288 5bank mux and4 existingdecode64 including UE output, no replication',
            banklocal_capture_to_mux_vertical_bound_um=249.48,
            horizontal_gap_signal_layers=['M2 local escape only','M4','M6','M8']))
    for b in range(5):
        near_logic.append(dict(name=f'virtual_bank{b}.paired_steering',
            box_xywh_um=[8.64,81.27+b*96.66,846.72,21.87],
            gross_cells_um2=512*4+128*.4374+(2*(288*4*mux+4*decode_area) if b==1 else 0),
            standard_cell_capacity_um2=846.72*21.87*.55,
            members='original paired512payload-bit virtual-bank gating +response/faultbuffer leaves',
            demanded_tracks=576,signal_tracks=817,
            signal_layers=['M2 local escape only','M4','M6','M8']))
    assert all(r.get('gross_cells_um2',0)<=r.get('standard_cell_capacity_um2',1) for r in near_logic)
    cut['postcapture_placement_regions']=near_logic
    # Actual net-length envelopes, not zero postcapture wire. Repeaters are
    # physical same-edge cells, not extra registered stages/latency credits.
    rc_est=lambda l:.5*.00844765*.103962*l*l + .00844765*l*.558822
    cut['postcapture_wire_price']=dict(
        coded_bank_to_mux_path_um=249.48,M8_wire_cap_fF=.103962*249.48,
        unbuffered_bank_mux_Elmore_wire_only_ps_ESTIMATE=rc_est(249.48),
        coded_mux_to_farthest_virtual_steer_path_um=386.64,
        unbuffered_mux_steer_Elmore_wire_only_ps_ESTIMATE=rc_est(386.64),
        steered_payload_to_farthest_east_pin_envelope_um=1026.432,
        long_haul_repeater_segment_target_um=120,
        worst_east_payload_repeater_cells_per_path=math.ceil(1026.432/120)-1,
        maximum1280_fanout_repeater_tree_levels=2,
        via_coupling_driver_delay_not_in_wire_only_estimate=True,
        output_wire_buffer_area_in_positive_reserves=True,
        actual_mapper_clockQ_setup_buffers_and_loaded_delay_required=True)
    cut['postcapture_path_estimates']['positive_wire_and_clock_skew_reserve_ps']=40
    path_prices=[
        dict(name='data_macro_to_localcapture',launch='data_store/rd_out[*]',capture='u_leaf.on.captured_code[p][b][*]/D',
            available_ps=remaining,wire_estimate_ps=wire_delay,hold_mux_proxy_ps=2*fo4,
            detour_coupling_ps=5,skew_ps=10,actual_capture_setup_budget_ps=remaining-2*fo4-wire_delay-15),
        dict(name='check_macro_to_localcapture',launch='check_store/rd_out[*]',capture='u_leaf.on.captured_code[p][b][parity]/D',
            available_ps=833.333333-60-cm['timing']['ss']['clk_to_q_ps'],
            slot_selector_proxy_ps=3*2*fo4,hold_mux_proxy_ps=2*fo4,wire_estimate_ps=check_delay,
            detour_coupling_ps=10,skew_ps=10,actual_capture_setup_budget_ps=cut['check_capture_available_for_actual_setup_wire_ps']),
        dict(name='captured_code_to_payload',launch='u_leaf.on.captured_code[p][b][*]/Q',capture='rom_rd[*] isolatedboundary',
            available_including_launchclkQ_ps=653.333333,
            combinational_proxy_ps=(6+19+2)*fo4,
            positive_wire_skew_proxy_ps=40,receiver_load_fF=.558822),
        dict(name='captured_code_to_UE_quarantine_steer',launch='u_leaf.on.captured_code[p][b][*]/Q',capture='rom_rd[*]/rsp_v/fault isolatedboundary',
            available_including_launchclkQ_ps=653.333333,
            combinational_proxy_ps=(6+19+6+5+2+2)*fo4,
            positive_wire_skew_proxy_ps=40,receiver_load_fF=.558822),
        dict(name='protected_outputbank_to_payload',launch='u_leaf.on.control_code[*]/Q',capture='rom_rd[*] isolatedboundary',
            available_including_launchclkQ_ps=653.333333,
            combinational_proxy_ps=(19+6+19+2)*fo4,
            positive_wire_skew_proxy_ps=40,receiver_load_fF=.558822)]
    cut['required_actual_source_path_prices']=path_prices
    component=obj('results/uarch/qwen_hbm_code_payload_leaf_20261005/banklocal_component/result.json')
    cut['source_component_gate']=component
    cut['selected_source_sha256']=refs['rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair_banklocal.sv']
    selected_cells=sum(cells.values())+sum(cut['costs_um2'].values())
    assert standard_capacity>selected_cells
    model=dict(name='qwen.code_pair',default_enabled=False,actual_fit=False,full_parent_adopted=False,
        wrapper='ot_qwen_hbm_code_pair_context',parameters=dict(ENABLE=1,COLUMN_BASE=0,ROWS=4496),
        source_bindings=refs,die_xyxy_um=[0,0,864,673.92],core_xyxy_um=[8.64,8.64,855.36,665.28],
        macro_count=20,macro_area_um2=area,macro_halo_area_um2=halo_area,
        context_cells_um2=cells,gross_standard_cells_um2=selected_cells,standard_cell_capacity_um2=standard_capacity,
        selected_cut='bank-local protectedcapture before physical bankmux',
        selected_cut_default_enabled=False,selected_cut_source_ready=True,selected_leaf_module='ot_qwen_hbm_code_payload_pair_banklocal',
        context_strip_xywh_um=[8.64,492.48,846.72,172.8],bank_pitch_um=96.66,
        macro_layer_obstructions=['M1','M2','M3','M4 except pin-edge strips'],
        over_macro_routing_layers=['M5','M6','M7','M8','M9'],
        open_channel_layers=dict(horizontal=['M4','M6','M8'],vertical=['M3','M5','M7','M9']),
        signal_track_fraction=.5,reserved_track_fraction=.5,channels=channels,
        per_bank_pin_escape=dict(height_um=70.47,signal_tracks=hcap(70.47),demand_tracks=1648),
        area_and_track_reservation_pass=True,clock_admission=False,timing=timing,bank_local_capture_candidate=cut,
        boundary_contract=dict(scope='isolated interface only; no production-parent timing claim',
            input_drive_cell='BUFx2_ASAP7_75t_R',output_load_fF=.558822,
            load_basis='one literal DFFHQNx1 D pin from installed TT Liberty, declared fixed isolated load, not SS receiver characterization',
            max_input_delay_ps=120,max_output_delay_ps=120,min_input_delay_ps=0,min_output_delay_ps=0,
            output_receiver_and_input_driver_instantiated=False,
            CORE_clk_is_existing_same_domain=True,physical_boundary_acceptance_required_by='Pauli'),
        state_bits=dict(baseline_leaf=936,banklocal_added=2304,selected_leaf=3240,fixed_pipeline=72,total=3312),macro_inventory=inventory,
        next_action='Erdos additive banklocal RTL + Sagan exact pipeline/tags gate; Pauli only selected minimumcontext physical validation, no originalcentral route/fullarray/parent adoption')
    out.mkdir(parents=True,exist_ok=True)
    for fn,v in [('model.json',model),('macro_pins.json',macro_pins),('boundary_pins.json',boundary),('capture_bit_locality.json',capture_targets),('timing_paths.json',path_prices)]:
        (out/fn).write_text(json.dumps(v,indent=2)+'\n')
    (out/'floorplan.tcl').write_text('# Isolated pair only; does not admit clock/parent.\ninitialize_floorplan -die_area {0 0 864 673.92} -core_area {8.64 8.64 855.36 665.28}\n')
    lines=['# Post-link/floorplan macro-placement hook; exact20 masters/hierarchies.',
           'proc ot_code_pair_instance {literal master} {',
           ' set block [ord::get_db_block]',
           ' foreach inst [$block getInsts] {',
           '  if {[string map {\\\\ ""} [$inst getName]] eq $literal} {',
           '   if {[[$inst getMaster] getName] ne $master} {error "Wrong macro master: $literal"}',
           '   return [$inst getName]',
           '  }',
           ' }',
           ' error "Missing actual CODE macro: $literal"','}']
    for m in inventory:
        x,y,_,_=m['box_xywh_um'];lines.append(f"place_macro -macro_name [ot_code_pair_instance {{{m['instance']}}} {m['master']}] -location {{{x:.6f} {y:.6f}}} -orientation {m['orientation']}")
    (out/'macros.tcl').write_text('\n'.join(lines)+'\n')
    lines=['# Exact Pauli wrapper ABI, source after track creation instead of random IO.']
    for p in boundary:
        x,y=p['xy_um'];lines.append(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{x:.6f} {y:.6f}}}")
    (out/'pins.tcl').write_text('\n'.join(lines)+'\n')
    (out/'boundary.sdc').write_text('''# ISOLATED interface contract ONLY; not actual production-parent delays/load.
set_units -time ns -capacitance pF
create_clock -name core -period 0.833333333 [get_ports clk]
set_clock_uncertainty -setup 0.060 [get_clocks core]
set_clock_uncertainty -hold 0.025 [get_clocks core]
set code_inputs [remove_from_collection [all_inputs] [get_ports {clk por_n}]]
set_input_delay -clock core -max 0.120 $code_inputs
set_input_delay -clock core -min 0.000 $code_inputs
set_driving_cell -lib_cell BUFx2_ASAP7_75t_R -pin Y $code_inputs
set_output_delay -clock core -max 0.120 [all_outputs]
set_output_delay -clock core -min 0.000 [all_outputs]
set_load 0.000558822 [all_outputs]
# Cold-reset boundary only. Release before clock; no warm-reset claim.
set_false_path -from [get_ports por_n]
''')
    print(json.dumps(dict(macro_count=20,area=area,context_cells=selected_cells,pins=len(boundary),timing_available_ps=remaining,clock_admission=False)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--out',type=Path)
    a=p.parse_args();build(a.root,a.out or a.root/BASE)
