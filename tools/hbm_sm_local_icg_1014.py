#!/usr/bin/env python3
"""Build distinct SM own leaf with local child ICGs and dedicated enable register."""
import copy, hashlib, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'results/arch/hbm_native_1013/sm_own_logic'
OUT=ROOT/'results/arch/hbm_native_1013/sm_local_icg_1014'
OUT.mkdir(parents=True,exist_ok=True)
records=[]
for v in ('eg','wg'):
    design=json.loads((SRC/f'{v}_split.json').read_text())
    old=f'ot_smh_own_{v}'; master=f'ot_smh_own_local_icg_{v}'
    leaf=design['modules'].pop(old);design['modules'][master]=leaf
    for mod in design['modules'].values():
        mod['cells']={n:c for n,c in mod['cells'].items() if c['type']!='$scopeinfo'}
    parent=design['modules'][f'split_{v}'];own=parent['cells']['u_own'];own['type']=master
    ena=leaf['ports']['cut_8870']['bits'][0]
    invs=[(n,c) for n,c in leaf['cells'].items() if c['type'].startswith('INV') and c['connections'].get('Y')==[ena]]
    assert len(invs)==1
    invname,inv=invs[0];qn=inv['connections']['A'][0]
    flops=[(n,c) for n,c in leaf['cells'].items() if c['type'].startswith('DFF') and c['connections'].get('QN')==[qn]]
    assert len(flops)==1
    launchname,launch=flops[0]
    bits=[b for c in leaf['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int)]
    nxt=max(bits)+1
    gate_d=launch['connections']['D'][0]
    nand_name,nand=next((n,c) for n,c in leaf['cells'].items() if c['connections'].get('Y')==[gate_d])
    assert nand['type'].startswith('NAND5')
    cgi_bit=leaf['ports']['cut_4']['bits'][0]
    nor_name,nor=next((n,c) for n,c in leaf['cells'].items() if c['type'].startswith('NOR4') and cgi_bit in c['connections'].get('D',[]) and c['connections']['Y'] in nand['connections'].values())
    local_cgi=nxt;local_nor=nxt+1;local_next=nxt+2;nxt+=3
    leaf['ports']['local_cgi']={'direction':'input','bits':[local_cgi]}
    own['port_directions']['local_cgi']='input';own['connections']['local_cgi']=own['connections']['cut_4'][:]
    local_nor_cell=copy.deepcopy(nor);local_nor_cell['connections']['D']=[local_cgi];local_nor_cell['connections']['Y']=[local_nor];leaf['cells']['u_local_enable_nor']=local_nor_cell
    product_n=nxt;product=nxt+1;nxt+=2
    leaf['cells']['u_local_enable_nand4']={'hide_name':0,'type':'NAND4xp75_ASAP7_75t_R','parameters':{},'attributes':{},'port_directions':{'A':'input','B':'input','C':'input','D':'input','Y':'output'},'connections':{**{p:nand['connections'][p][:] for p in ('A','B','C','D')},'Y':[product_n]}}
    leaf['cells']['u_local_enable_product_inv']={'hide_name':0,'type':'INVx1_ASAP7_75t_R','parameters':{},'attributes':{},'port_directions':{'A':'input','Y':'output'},'connections':{'A':[product_n],'Y':[product]}}
    leaf['cells']['u_local_enable_nand']={'hide_name':0,'type':'NAND2x2_ASAP7_75t_R','parameters':{},'attributes':{},'port_directions':{'A':'input','B':'input','Y':'output'},'connections':{'A':[product],'B':[local_nor],'Y':[local_next]}}
    dedicated_qn=nxt; dedicated_ena=nxt+1;nxt+=2
    commit=nxt;nxt+=1
    leaf['ports']['local_enable_commit']={'direction':'input','bits':[commit]}
    leaf['netnames']['local_enable_commit']={'hide_name':0,'bits':[commit],'attributes':{}}
    own['port_directions']['local_enable_commit']='input';own['connections']['local_enable_commit']=own['connections']['cut_2'][:]
    mirror=copy.deepcopy(launch);mirror['connections']['CLK']=[commit];mirror['connections']['D']=[local_next];mirror['connections']['QN']=[dedicated_qn];mirror['attributes']={'keep':'1','dont_touch':'1'}
    leaf['cells']['u_enable_mirror']=mirror
    direct=copy.deepcopy(inv);direct['type']='INVx4_ASAP7_75t_R';direct['connections']={'A':[dedicated_qn],'Y':[dedicated_ena]};direct['attributes']={'keep':'1','dont_touch':'1'}
    leaf['cells']['u_enable_local_inv']=direct
    leaf['netnames']['local_enable']={'hide_name':0,'bits':[dedicated_ena],'attributes':{'keep':'1'}}
    aux_commit=nxt;aux_qn=nxt+1;aux_ena=nxt+2;nxt+=3
    leaf['ports']['local_enable_commit_aux']={'direction':'input','bits':[aux_commit]}
    own['port_directions']['local_enable_commit_aux']='input';own['connections']['local_enable_commit_aux']=own['connections']['cut_2'][:]
    aux_clock=aux_commit
    for stage in range(6):
        delayed=nxt;nxt+=1
        leaf['cells'][f'u_enable_aux_clock_delay_{stage}']={'hide_name':0,'type':'BUFx6f_ASAP7_75t_R','parameters':{},'attributes':{'keep':'1','dont_touch':'1'},'port_directions':{'A':'input','Y':'output'},'connections':{'A':[aux_clock],'Y':[delayed]}}
        aux_clock=delayed
    aux=copy.deepcopy(mirror);aux['connections']['CLK']=[aux_clock];aux['connections']['QN']=[aux_qn];leaf['cells']['u_enable_aux_mirror']=aux
    auxinv=copy.deepcopy(direct);auxinv['connections']={'A':[aux_qn],'Y':[aux_ena]};leaf['cells']['u_enable_aux_inv']=auxinv
    leaf['netnames']['local_enable_aux']={'hide_name':0,'bits':[aux_ena],'attributes':{'keep':'1'}}
    clockports=[]
    for i in range(12):
        name=f'u_child_icg_{i}';gate=parent['cells'].pop(name)
        raw=f'local_raw_{i}';gated=f'local_gclk_{i}'
        rawbit=nxt;gatedbit=nxt+1;nxt+=2
        for port,direction,local,external in [(raw,'input',rawbit,gate['connections']['CLK'][0]),(gated,'output',gatedbit,gate['connections']['GCLK'][0])]:
            leaf['ports'][port]={'direction':direction,'bits':[local]}
            leaf['netnames'][port]={'hide_name':0,'bits':[local],'attributes':{}}
            own['port_directions'][port]=direction;own['connections'][port]=[external]
        gate['connections']={'CLK':[rawbit],'ENA':[dedicated_ena if i in (4,9,10,11) else aux_ena],'SE':['0'],'GCLK':[gatedbit]}
        gate['attributes']={'keep':'1','dont_touch':'1'};leaf['cells'][name]=gate
        child_name,child=next((cn,cc) for cn,cc in parent['cells'].items() if cc['type'].startswith('ot_hbm_accel_smh_') and cc['connections'].get('clk')==own['connections'][gated])
        clockports.append({'raw':raw,'gclk':gated,'gate':name,'parent_clock_port':f'clk_child_{i}','original_gated_clock_bit':7768,'child_instance':child_name,'child_master':child['type'],'reset_parent_bits':child['connections'].get('rst_n',[])})
    (OUT/f'{v}_split.json').write_text(json.dumps(design)+'\n')
    mapped=copy.deepcopy(design);mapped['modules'].pop(f'split_{v}')
    (OUT/f'{v}_leaf.json').write_text(json.dumps(mapped)+'\n')
    mutant=copy.deepcopy(design);mutant['modules'][master]['cells']['u_enable_mirror']['connections']['D']=['0'];mutant['modules'][master]['cells']['u_enable_aux_mirror']['connections']['D']=['0']
    (OUT/f'{v}_mut.json').write_text(json.dumps(mutant)+'\n')
    for name in [f'{v}_gold.json',f'{v}_surrogates.sv',f'{v}_tb.sv','retention_cell_models.sv']:
        shutil.copy2(SRC/name,OUT/name)
    with (OUT/'retention_cell_models.sv').open('a') as f: f.write('\nmodule INVx4_ASAP7_75t_R(input A, output Y); assign Y=~A; endmodule\nmodule BUFx6f_ASAP7_75t_R(input A, output Y); assign Y=A; endmodule\nmodule NAND4xp75_ASAP7_75t_R(input A,B,C,D, output Y); assign Y=~(A&B&C&D); endmodule\nmodule NAND2x2_ASAP7_75t_R(input A,B, output Y); assign Y=~(A&B); endmodule\n')
    gold=json.loads((OUT/f'{v}_gold.json').read_text())
    for mod in gold['modules'].values():
        mod['cells']={n:c for n,c in mod['cells'].items() if c['type']!='$scopeinfo'}
    (OUT/f'{v}_gold.json').write_text(json.dumps(gold)+'\n')
    script=(SRC/f'{v}_run.sh').read_text();(OUT/f'{v}_run.sh').write_text(script)
    spec=json.loads((SRC/f'{v}_physical_spec.json').read_text())
    spec.update(name=f'smh_own_local_icg_{v}_ref',top=master,sources=[str((OUT/f'{v}_leaf.sv').relative_to(ROOT))],std_area_um2=spec['std_area_um2']+8.0)
    spec['outline']={'w':84.24,'h':73.44}
    spec['pins']['W']+=['local_cgi']
    spec['pins']['N']+=['local_enable_commit','local_enable_commit_aux']
    spec['post_synth_tcl']=str((OUT/'local_clock_preserve.tcl').relative_to(ROOT))
    spec['pre_cts_extra']=[str((OUT/'local_clock_preserve.tcl').relative_to(ROOT))]
    spec['pins']['N']+=sum(([p['raw'],p['gclk']] for p in clockports),[])
    spec['sdc_extra']=[str((OUT/'local_generated_clocks.sdc').relative_to(ROOT))]
    spec['structural_change']='Factor mirror NAND5 into NAND2x2(AND4(originalA..D),NOR4(original busy/cgi)) to remove weak high-fanout decode driver, no Boolean or edge change. Duplicate original NOR4/NAND5 enable decode on dedicated local_cgi normal data pin (same original bit4 parent source), isolating mirror path from original late-register input hold buffers while retaining all original cut4 constraints. Six retained BUFx6f stages on auxiliary mirror clock branch; real generated GCLK exported at clock ports. Split mirrored original ENA into four critical XS/PT_E/PT_W gates and eight auxiliary gates with independent small commit clock roots, INVx4 direct local distribution. Move twelve original parent real ICGs inside distinct own master; mirror original ENA DFF and inverter on identical D/RAW clock to drive local gates without exported ordinary-data hold chain. Preserve all995 original logical registers and ordinary cut8870 data constraint; no cycle/phase relaxation.'
    spec['slot_change_request']={'kind':'local_clock_entry','parent':'native SM compact tile','outline_um':[84.24,73.44],'additional_clock_pins':26,'additional_data_pin':{'local_cgi':'Original bit4 same parent source; separate normal IO constraints, registered ENA capture after duplicated original two-gate decode; original cut4 ordinary-data hold branch retained'},'enable_commit_clock':{'logical_source':'original raw bit2','delivered_phase':'phi-Rown, same tap as own raw input','critical_group_indices':[4,9,10,11],'critical_insertion_max_ps':20,'auxiliary_insertion_min_ps':55,'auxiliary_group_indices':[0,1,2,3,5,6,7,8],'auxiliary_insertion_target_ps':80,'required_gate':'Measured mirror launch CLK arrival and D setup/hold from original own state + all original cgi/reset/pause source pins; no zero-wire or zero-slew assumption'},'status':'PENDING_REAL_MULTICLOCK_CTS_GATING_PULSE_AND_DIE_REACH','source':str((OUT/'manifest.json').relative_to(ROOT))}
    spec['job'].update(branch='codex/sm-gate-structural-1014',owner='Codex:sm_gate_structural',tag='localicg1',purpose=spec['structural_change'],extra_paths=[str(OUT.relative_to(ROOT))])
    for b in spec['job']['benches']:b['cmd']=b['cmd'].replace('sm_own_logic/','sm_local_icg_1014/')
    spec['job']['benches'] += [{'name':'local_icg_functional_phase_ss','cmd':f'bash {OUT.relative_to(ROOT)}/phase_run.sh split ss','expect':'pass','pass_regex':'LOCAL_ICG_PHASE_ss checked=4096 enable_checks=4096 pulses=[1-9]','threads':4,'peak_ram_gb':4},{'name':'local_icg_mirror_mutant','cmd':f'bash {OUT.relative_to(ROOT)}/phase_run.sh mut ss','expect':'fail','fail_regex':'enable mirror state differs from original8870','threads':4,'peak_ram_gb':4}]
    spec['reroute_reason']={'kind':'rtl_change'}
    (OUT/f'{v}_physical_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    records.append({'variant':v,'master':master,'original_enable_bit':8870,'original_gated_bit':7768,'launch_cell':launchname,'launch_D_bits':launch['connections']['D'],'raw_clock_bits':launch['connections']['CLK'],'mirror_type':mirror['type'],'mirror_count':2,'original_decode_cells':[nor_name,nand_name],'local_decode_cgi_parent_bit':own['connections']['local_cgi'],'local_decode_D_bits':[local_next],'inverter_type':'INVx4_ASAP7_75t_R','critical_indices':[4,9,10,11],'local_gate_count':12,'ports':clockports,'source_split_sha256':hashlib.sha256((SRC/f'{v}_split.json').read_bytes()).hexdigest(),'reset_driver_ABI':{'parent_port':'rst_n','original_parent_bit':3,'own_port':'cut_3','polarity':'active_low','original_child_connections':'unchanged, see each child reset_parent_bits'},'logical_phase_and_latency':'UNCHANGED; all clocks common in exact functional bench; physical phi-R checks required separately'})
plan=json.loads((OUT/'clock_baseline/plan.json').read_text())
sdc=(SRC/'own_generated_clock.sdc').read_text()
sdc+='set local_icg_corner tt\nforeach local_lib [get_libs *] {set local_ln [get_property $local_lib name]; if {[regexp {(^|_)SS($|_)} $local_ln]} {set local_icg_corner ss}; if {[regexp {(^|_)FF($|_)} $local_ln]} {set local_icg_corner ff}}\n'
for i,row in enumerate(plan['child_instances']):
    caps=row['corners']
    sdc+=f'set local_clock_cap_{i}(tt) {caps["tt"]["child_clock_cap_fF"]}\nset local_clock_cap_{i}(ff) {caps["ff"]["child_clock_cap_fF"]}\nset local_clock_cap_{i}(ss) {caps["ss"]["child_clock_cap_fF"]}\nset_load $local_clock_cap_{i}($local_icg_corner) [get_ports local_gclk_{i}]\n'
sdc+='set local_icg_period [get_property [get_clocks core_clk] period]\ncreate_clock -name enable_commit -period $local_icg_period [get_ports local_enable_commit]\ncreate_clock -name enable_commit_aux -period $local_icg_period [get_ports local_enable_commit_aux]\nunset_input_delay [get_ports {local_enable_commit local_enable_commit_aux local_raw_*}]\n'
for i in range(12):
    sdc+=f'unset_output_delay [get_ports local_gclk_{i}]\n'
for i in range(12):
    sdc+=f'create_clock -name child_raw_{i} -period $local_icg_period [get_ports local_raw_{i}]\ncreate_generated_clock -name child_gclk_{i} -master_clock child_raw_{i} -source [get_ports local_raw_{i}] -divide_by 1 [get_ports local_gclk_{i}]\n'
(OUT/'local_generated_clocks.sdc').write_text(sdc)
(OUT/'manifest.json').write_text(json.dumps({'status':'RTL_CANDIDATE_NOT_PHYSICALLY_QUALIFIED','records':records,'original_states_preserved':995,'added_mirror_flops':2,'gating_data_exceptions':[],'required_physical_checks':['actual phi-R every gate RAW and child clock','gating setup+hold all3corners','real conditional pulse width','source slew recalibration','ordinary data TT FF DRC and registered seams','native pause/epoch/reset bit7768 semantics']},indent=2)+'\n')
