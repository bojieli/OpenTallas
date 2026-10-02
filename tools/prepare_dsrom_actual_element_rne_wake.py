#!/usr/bin/env python3
"""Full actual q/BF source join only. No HDL compiler/simulator/P&R invocation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='results/rtl/dsrom_actual_element_rne_wake_prepare_20261002'
WAKE='b046de7f0278bae6a28f2bd346303bbc25cc4bac'
COPIES={
 'rtl/v41rom/ot_v41_rom_elem_w10.sv':'rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv',
 'rtl/v41die/ot_v41_pair_w17w10.sv':'rtl/v41die/ot_v41_pair_w17w10_rne_wake_prepare.sv',
 'rtl/v41rom/ot_v41_bf16_lanes2.sv':'rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv'}
EXTRA=['rtl/v41rom/ot_v41_bmul2_rne_prepare.sv','rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv']
BENCH='rtl/test/tb_dsrom_actual_element_rne_wake.sv'
def sha(b):return hashlib.sha256(b).hexdigest()
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
N=mod('pinned_numerical','tools/prepare_dsrom_actual_element_numerical.py')
L=mod('pinned_actual','tools/prepare_dsrom_actual_element_gate.py')
def once(text,old,new):
 if text.count(old)!=1:raise ValueError('source substitution not unique '+old)
 return text.replace(old,new)
def compose_sources():
 rowfix=(ROOT/'rtl/v41rom/ot_v41_rom_elem_w10_rowfix_prepare.sv').read_text()
 elem=subprocess.check_output(['git','show',WAKE+':rtl/v41rom/ot_v41_rom_elem_wake_w10.sv'],cwd=ROOT,text=True)
 elem=once(elem,'module ot_v41_rom_elem_wake_w10','module ot_v41_rom_elem_w10')
 marker="        end else begin                          // 2NSEG+1+s: the row of segment s on the pair's second macro\n"
 decoder=rowfix.split(marker)[1].split('        end\n    end')[0]
 original=elem.split(marker)[1].split('        end\n    end')[0]
 elem=once(elem,original,decoder)
 elem=once(elem,'    parameter INSTANCE = ""','    parameter integer FIX_SECOND_ROW_INDEX = 0, // mandatory row decoder repair, opt-in preparation\n    parameter integer GRADUAL_RNE = 0, // shared reviewed multiplier repair\n    parameter INSTANCE = ""')
 elem=once(elem,'ot_v41_bf16_lanes2 #(.NCHB(NCHB), .TRW(TG), .CUT(CUT))','ot_v41_bf16_lanes2 #(.NCHB(NCHB), .TRW(TG), .CUT(CUT), .GRADUAL_RNE(GRADUAL_RNE))')
 pair=(ROOT/'rtl/v41die/ot_v41_pair_w17w10_rowfix_prepare.sv').read_text()
 pair=once(pair,'    parameter INSTANCE = ""','    parameter integer WAKE_REG = 0, // retained true WAKE1 leaf join, off by default\n    parameter integer GRADUAL_RNE = 0, // shared reviewed multiplier repair\n    parameter INSTANCE = ""')
 pair=once(pair,'.FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX),','.FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX), .WAKE_REG(WAKE_REG), .GRADUAL_RNE(GRADUAL_RNE),')
 lanes=L.load_sources()['rtl/v41rom/ot_v41_bf16_lanes2.sv']
 lanes=once(lanes,'    parameter integer TRW = 2,','    parameter integer GRADUAL_RNE = 0, // shared reviewed multiplier; no stage/port change\n    parameter integer TRW = 2,')
 lanes=once(lanes,'ot_v41_bmul2 u_m','ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(GRADUAL_RNE)) u_m')
 return dict(zip(COPIES.values(),(elem,pair,lanes)))
def compose_bench():
 b=(ROOT/'rtl/test/tb_dsrom_actual_element_numerical.sv').read_text()
 b=b.replace('// NUMERICAL PREPARE ONLY; assertion-only independent exact oracle; opt-in mandatory decoder correction on both namespaces.','// Full actual-element RNE/WAKE1 preparation; unchanged assertion-only numerical oracle.')
 b=b.replace('// No clockgate RTL, arithmetic, geometry, timing qualification, or adoption change.','// Underlying ICG and full geometry unchanged; decoder/RNE/WAKE1 opt-ins selected on both namespaces. No hardware timing credit.')
 b=b.replace('.FIX_SECOND_ROW_INDEX(1),','.FIX_SECOND_ROW_INDEX(1),.GRADUAL_RNE(1),.WAKE_REG(1),')
 b=b.replace('.g_cg.u_cg.en_l','.g_wake.g_leaf[0].u_cg.en_l')
 # Retain every existing oracle/DIFf/score/coverage condition; add source-specific wake guards.
 guards=[]
 for leaf in range(8):
  r=f'ref_dut.u_e.g_wake.g_leaf[{leaf}]';c=f'cand_dut.u_e.g_wake.g_leaf[{leaf}]'
  guards.extend([f'      if({r}.wake !== {c}.wake) $fatal(1,"DIFF wake leaf{leaf}");',
    f'      if({r}.u_cg.en_l !== {c}.u_cg.en_l) $fatal(1,"DIFF enable leaf{leaf}");',
    f'      if(ref_dut.u_e.leaf_clk[{leaf}] !== (clk & {r}.u_cg.en_l)) $fatal(1,"wake gate behavior leaf{leaf}");',
    f'      if(cand_dut.u_e.leaf_clk[{leaf}] !== (clk & {c}.u_cg.en_l)) $fatal(1,"candidate wake gate behavior leaf{leaf}");',
    f'      if(!clk && ({r}.u_cg.en_l !== {r}.wake || {c}.u_cg.en_l !== {c}.wake)) $fatal(1,"low latch settling leaf{leaf}");'])
 b=once(b,'    task compare_all;','    task compare_all;\n'+'\n'.join(guards))
 tick='''    reg wake_next_expected;
    integer wake_assertions=0,root_capture_events=0;
    function automatic phase_is_active(input integer phase_id);
      // Assertion-only class-valid contract of immutable cfg image: phase0 empty, phases1..11 active.
      phase_is_active=(phase_id>=1 && phase_id<=11);
    endfunction
    task capture_wake_contract;
      wake_next_expected=!rst_n || (go && phase_is_active(ph)) || ref_dut.u_e.go_e || ref_dut.u_e.walk_busy || ref_dut.u_e.drain!=0;
    endtask
    task check_wake_contract;
'''
 for leaf in range(8):
  tick+=f'      if(ref_dut.u_e.g_wake.g_leaf[{leaf}].wake !== wake_next_expected || cand_dut.u_e.g_wake.g_leaf[{leaf}].wake !== wake_next_expected) $fatal(1,"independent wake lookahead leaf{leaf}");\n'
 tick+='''      wake_assertions=wake_assertions+16;
      if(rst_n) begin
        if(ref_dut.go_e !== (go && phase_is_active(ph)) || cand_dut.go_e !== (go && phase_is_active(ph))) $fatal(1,"independent pair go qualification");
        if(ref_dut.u_e.go_e !== (go && phase_is_active(ph)) || cand_dut.u_e.go_e !== (go && phase_is_active(ph))) $fatal(1,"independent registered element go");
        if({ref_dut.u_e.g_ir.r_xs_v,ref_dut.u_e.g_ir.r_xb_v} !== {xs_v,xb_v} ||
           {cand_dut.u_e.g_ir.r_xs_v,cand_dut.u_e.g_ir.r_xb_v} !== {xs_v,xb_v}) $fatal(1,"free root input valids");
        if({ref_dut.u_e.g_ir.r_xs_p,ref_dut.u_e.g_ir.r_xs_b,ref_dut.u_e.g_ir.r_xs_sv,ref_dut.u_e.g_ir.r_xs_q0,ref_dut.u_e.g_ir.r_xs_e0,ref_dut.u_e.g_ir.r_xs_q1,ref_dut.u_e.g_ir.r_xs_e1,ref_dut.u_e.g_ir.r_xs_pos,ref_dut.u_e.g_ir.r_xb_pos,ref_dut.u_e.g_ir.r_xb_b,ref_dut.u_e.g_ir.r_xb_sv,ref_dut.u_e.g_ir.r_xb_u,ref_dut.u_e.g_ir.r_xb_d} !==
           {xs_p,xs_b,xs_sv,xs_q0,xs_e0,xs_q1,xs_e1,xs_pos,xb_pos,xb_b,xb_sv,xb_u,xb_d}) $fatal(1,"free root captured operands");
        if({cand_dut.u_e.g_ir.r_xs_p,cand_dut.u_e.g_ir.r_xs_b,cand_dut.u_e.g_ir.r_xs_sv,cand_dut.u_e.g_ir.r_xs_q0,cand_dut.u_e.g_ir.r_xs_e0,cand_dut.u_e.g_ir.r_xs_q1,cand_dut.u_e.g_ir.r_xs_e1,cand_dut.u_e.g_ir.r_xs_pos,cand_dut.u_e.g_ir.r_xb_pos,cand_dut.u_e.g_ir.r_xb_b,cand_dut.u_e.g_ir.r_xb_sv,cand_dut.u_e.g_ir.r_xb_u,cand_dut.u_e.g_ir.r_xb_d} !==
           {xs_p,xs_b,xs_sv,xs_q0,xs_e0,xs_q1,xs_e1,xs_pos,xb_pos,xb_b,xb_sv,xb_u,xb_d}) $fatal(1,"candidate free root captured operands");
        root_capture_events=root_capture_events+1;
      end
    endtask
'''
 b=once(b,'    task tick;',tick+'    task tick;')
 b=once(b,'      compare_all(); #416; clk=1; #1; compare_all();','      compare_all(); capture_wake_contract(); #416; clk=1; #1; compare_all(); check_wake_contract();')
 b=once(b,'      $finish;','      if(wake_assertions!=16*cycles || root_capture_events==0) $fatal(1,"wake coverage");\n      $display("PASS wake-source BF=%0d wake_assertions=%0d root_capture_events=%0d",BF,wake_assertions,root_capture_events);\n      $finish;')
 return b

def package():
 sources=L.load_sources()
 for path,copy in COPIES.items():sources[path]=(ROOT/copy).read_text()
 for path in EXTRA:sources[path]=(ROOT/path).read_text()
 result=L.generate(sources)
 result[Path(BENCH).name]=(ROOT/BENCH).read_text()
 for p in ('rtl/test/dsrom_actual_element_numerical_rom.cpp','rtl/test/dsrom_actual_element_numerical_stimulus.svh','rtl/test/dsrom_actual_element_numerical_expected.svh'):result[Path(p).name]=(ROOT/p).read_text()
 return result

def verify():
 N.verify();mod('primitive_verify','tools/prepare_dsrom_bmul_rne_primitive.py').verify()
 m=json.loads((ROOT/BASE/'model.json').read_text())
 for path,pin in m['preserved_files_sha256'].items():
  data=(ROOT/path).read_bytes()
  if sha(data)!=pin or data!=subprocess.check_output(['git','show',m['preserved_commit']+':'+path],cwd=ROOT):raise ValueError('preserved changed '+path)
 for path,pin in m['new_artifact_pins'].items():
  if sha((ROOT/path).read_bytes())!=pin:raise ValueError('new pin changed '+path)
 for path,text in compose_sources().items():
  if text!=(ROOT/path).read_text():raise ValueError('joined source differs from exact composition '+path)
 if compose_bench()!=(ROOT/BENCH).read_text():raise ValueError('bench composition changed')
 for path,pin in m['authority_pins'].items():
  if sha(subprocess.check_output(['git','show',pin['commit']+':'+path],cwd=ROOT))!=pin['sha256']:raise ValueError('authority changed '+path)
 if {p:sha(t.encode()) for p,t in package().items()}!=m['generated_files_sha256']:raise ValueError('package changed')
 return m

def prepare(out):
 m=verify();out.mkdir(parents=True,exist_ok=False)
 for p,t in package().items():
  with (out/p).open('x') as f:f.write(t)
 receipt=dict(status='PREPARED_NOT_COMPILED',model_sha256=sha((ROOT/BASE/'model.json').read_bytes()),files_sha256=m['generated_files_sha256'],preserved_files_verified=len(m['preserved_files_sha256']),compile_authorized=False,simulate_authorized=False)
 with (out/'preparation.json').open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
 return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
