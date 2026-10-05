#!/usr/bin/env python3
"""Literal integrated bank5+76BUF gate, before physical reset/arrival admission."""
import argparse,gzip,hashlib,json
from pathlib import Path
from qwen_rom_bank5_control_gate import ROOT,OUT,OLD,TILE,BENCH,YOSYS,validate_model,miter
from qwen_rom_hold_capture_literal_gate import candidate_logic,formal_view
from qwen_rom_hold_capture_gate_prepare import original_logic
from qwen_rom_kv_finite_window_gate import guarded_process
NEW='rtl/hdc/ot_qwen_rom_tile_context_candidate_r2.sv'
TREE='rtl/physical/ot_qwen_rom_bank5_control_distribution.sv'

def context_logic(raw):
    source=raw.decode()
    assert source.count('parameter integer ROM_CONTROL_DISTRIBUTION = 0,')==2
    assert '.ROM_CONTROL_DISTRIBUTION(ROM_CONTROL_DISTRIBUTION)' in source
    assert '.addr_in(ROM_CONTROL_DISTRIBUTION != 0 ? rom_distributed_addr[12*(p*5+b) +: 12] : rom_addr)' in source
    start=source.index('    reg  [CODE_BANKS-1:0] code_sel_q;');end=source.index('    // -- KV slice',start)
    old,_=candidate_logic((ROOT/OLD).read_bytes())
    header=old.decode().split('    reg  [CODE_BANKS-1:0] code_sel_q;')[0]
    header=header.replace('ROM_HOLD_DIRECT_CAPTURE=0','ROM_HOLD_DIRECT_CAPTURE=0,ROM_BANK5_CONTROL=0,ROM_CONTROL_DISTRIBUTION=0')
    header=header.replace('output wire [11:0] rom_addr);','output wire [11:0] rom_addr,output wire [119:0] rom_distributed_addr);')
    declaration='    wire [CODE_BANKS-1:0] code_rd_bank; // Explicit before primitive-port expression.\n'
    assert source.index(declaration)<source.index('.bank_read_n(~code_rd_bank)')
    return (header+declaration+source[start:end]+'endmodule\n').encode()

def run(work,result):
    if work.exists() or result.exists():raise ValueError('Refusing overwrite')
    model=validate_model();work.mkdir(parents=True)
    d=json.loads((OUT/'distribution_r1.json').read_text())
    assert d['status']=='PASS_EXACT76BUF_SOURCE_AND_OWNERSHIP'
    raw={p:(ROOT/p).read_bytes() for p in [OLD,NEW,TREE,TILE,BENCH,'tools/qwen_rom_control_context_gate.py']}
    for p,digest in d['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
    old,_=candidate_logic(raw[OLD]);new=context_logic(raw[NEW])
    prior=formal_view(old,True).replace('qwen_optin_capture_logic','qwen_prior_capture')
    # Give formal_view its standard interface marker then append new address.
    repaired=formal_view(new.replace(b',output wire [119:0] rom_distributed_addr);',b');'),True)
    repaired=repaired.replace('output wire [4:0] f_q,f_q2,output wire f_s,','output wire [4:0] f_q,f_q2,output wire f_s,output wire [4:0] f_bank,output wire [119:0] rom_distributed_addr,')
    repaired=repaired.replace('endmodule','assign f_bank=code_rd_bank;\nendmodule')
    mit=miter().replace('wire [2559:0] a_cap,b_cap,c_cap;','wire [2559:0] a_cap,b_cap,c_cap;wire [119:0] actual_macro_addr;')
    mit=mit.replace('.ROM_BANK5_CONTROL(1)', '.ROM_BANK5_CONTROL(1),.ROM_CONTROL_DISTRIBUTION(1)').replace('.f_bank(banks));','.f_bank(banks),.rom_distributed_addr(actual_macro_addr));')
    mit=mit.replace('assert(banks=={5{a_s}});','assert(banks=={5{a_s}});assert(actual_macro_addr=={10{a_addr}});')
    (work/'prior.sv').write_text(prior);(work/'miter.sv').write_text(mit)
    # Non-inverting functional model is checked against both source Liberty
    # corners by distribution_r1; transparent model gives no delay/skew credit.
    (work/'BUF_function.sv').write_text('module BUFx4_ASAP7_75t_R(input A,output Y);assign Y=A;endmodule\n')
    (work/'tree.sv').write_bytes(raw[TREE]);steps=[]
    for case,text in [('positive',repaired),('wrong_address_owner',repaired.replace('.low_address(rom_addr)', '.low_address({rom_addr[0],rom_addr[11:1]})'))]:
        source=work/(case+'.sv');source.write_text(text)
        ys=work/(case+'.ys');ys.write_text(f'''read_verilog -formal -sv {work/'BUF_function.sv'} {work/'tree.sv'} {work/'prior.sv'} {source} {work/'miter.sv'}
prep -top bank5_formal -flatten
async2sync
dffunmap
opt_clean
sat -seq 2 -tempinduct -set-assumes -prove-asserts -verify
''')
        rc,out=guarded_process([YOSYS,'-s',str(ys)],work,work/(case+'.log'))
        steps.append(dict(case=case,returncode=rc,output_tail=out[-2500:]))
    (work/'original.sv').write_bytes(original_logic(raw[TILE])[0]);(work/'context_cone.sv').write_bytes(new)
    bench=raw[BENCH].decode().replace('.ROM_HOLD_DIRECT_CAPTURE(1)', '.ROM_HOLD_DIRECT_CAPTURE(1),.ROM_BANK5_CONTROL(1),.ROM_CONTROL_DISTRIBUTION(1)')
    (work/'fourstate.sv').write_text(bench)
    for phase,cmd in [('build',['iverilog','-g2012','-s','tb_qwen_rom_hold_capture_equivalence','-o',str(work/'gate.vvp'),str(work/'BUF_function.sv'),str(work/'tree.sv'),str(work/'original.sv'),str(work/'context_cone.sv'),str(work/'fourstate.sv')]),('run',['vvp',str(work/'gate.vvp')])]:
        rc,out=guarded_process(cmd,work,work/('fourstate_'+phase+'.log'))
        steps.append(dict(case='fourstate_'+phase,returncode=rc,output_tail=out[-2500:]))
        if rc:break
    good=steps[0]['returncode']==0 and 'Induction step proven: SUCCESS!' in steps[0]['output_tail'] and steps[1]['returncode']!=0 and len(steps)==4 and all(s['returncode']==0 for s in steps[2:]) and 'checks=77' in steps[-1]['output_tail']
    stable=all((ROOT/p).read_bytes()==data for p,data in raw.items())
    record=dict(schema='opentallas.qwen-rom-integrated-control-source-gate.v1',status='PASS_INTEGRATED_BANK5_76BUF_LITERAL_AND_FOURSTATE' if good and stable else 'FAIL',
        source_sha256={p:hashlib.sha256(data).hexdigest() for p,data in raw.items()},source_stable=stable,steps=steps,
        model_commit='cdcbe60a34389a5671f9e303c4f5023e83b23710',buffers_connected_to_source_logic_and_macro_address=True,
        buffer_counts=model['fixed_candidate']['buffer_counts'],metadata_FF_modeled=90,metadata_FF_mapped_survival_proven=False,
        actual_issue_producer_instantiated_in_full_source=True,reset_release_root_still_external=True,
        passing_scope='Actual defaultoff new fulltile namespace contains source producer,10ROM,2KV and76BUF bindings. Literal control/capture/address cone proof and functional BUF4state only; complete-tile elaboration/mapping and physical launch/reset/wire/clock proof pending.',
        added_semantic_cycles=0,contextual_STA_admitted=False,tile_PR=False,adoption=False)
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(record['status']);return 0 if good and stable else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workdir',type=Path,required=True);ap.add_argument('--result',type=Path,required=True)
    args=ap.parse_args();raise SystemExit(run(args.workdir,args.result))
