#!/usr/bin/env python3
"""Bind immutable generated H16 to the proven c0 image vehicle; compare old native on every edge."""
import argparse
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--native-dir', required=True)
p.add_argument('--old-native-dir', default='results/rtl/qw_head_safe32_1020/h16y/net_ifg2')
a = p.parse_args()
native = Path(a.native_dir)
old = Path(a.old_native_dir)
out = Path('results/rtl/qw_head_safe32_1020/h16z/qualification')
out.mkdir(parents=True, exist_ok=True)
name = 'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r'
new_text = (native/'native32_1r_param.v').read_text()
old_text = (old/'native32_1r_param.v').read_text()
assert new_text.count('module '+name+' #(') == old_text.count('module '+name+' #(') == 1
new_helpers = (native/'native32_helpers.sv').read_text()
old_helpers = (old/'native32_helpers.sv').read_text()
# Private names keep the independently preserved old generated source separate.
old_modules = re.findall(r'\bmodule\s+(\w+)', old_helpers)
for module in old_modules:
    old_helpers = re.sub(r'\b'+re.escape(module)+r'\b', 'oldref_'+module, old_helpers)
    old_text = re.sub(r'\b'+re.escape(module)+r'\b', 'oldref_'+module, old_text)
(out/'candidate.v').write_text(new_text.replace('module '+name+' #(', 'module h16_candidate #('))
(out/'candidate_helpers.sv').write_text(new_helpers)
(out/'oldref.v').write_text(old_text.replace('module '+name+' #(', 'module h16_oldref #('))
(out/'oldref_helpers.sv').write_text(old_helpers)
decl = re.findall(r'^(input|output) wire (\[[^\]]+\] )?(\w+);', new_text, re.M)
assert decl and len({x[2] for x in decl}) == len(decl)
assert decl == re.findall(r'^(input|output) wire (\[[^\]]+\] )?(\w+);', old_text, re.M)
outputs = [(width, port) for direction, width, port in decl if direction == 'output']
wrapper = ['module '+name+' #(parameter integer STAGE_ME=1, SEGCAL=1) ('+','.join(x[2] for x in decl)+');']
wrapper += [direction+' wire '+width+port+';' for direction, width, port in decl]
wrapper += ['wire '+width+'old_'+port+';' for width, port in outputs]
for module, instance, prefix in [('h16_candidate','u_candidate',''),('h16_oldref','u_oldref','old_')]:
    conns = ['.'+port+'('+((prefix if direction=='output' else '')+port)+')' for direction,width,port in decl]
    wrapper += [module+' #(.STAGE_ME(STAGE_ME),.SEGCAL(SEGCAL)) '+instance+'('+','.join(conns)+');']
for signal in ['fixed_issue','fixed_end','fixed_pc','fixed_unit']:
    m = re.search(r'wire (\[[^\]]+\]) \\u_head\.'+signal+r'\s*;', new_text)
    assert m, signal
    wrapper += ['wire '+m[1]+' \\u_head.'+signal+' ;', 'assign \\u_head.'+signal+' = u_candidate.\\u_head.'+signal+' ;']
wrapper += ['wire head_fault=u_candidate.head_fault;', 'wire relocation_sticky=u_candidate.relocation_sticky;']
wrapper += ['integer diff_edges=0;', 'always @(negedge ck_head) if(rst_n) begin']
for width,port in outputs:
    wrapper += [' if('+port+' !== old_'+port+') $fatal(1,"H16_NATIVE_DIFF '+port+' edge=%0d new=%h old=%h",diff_edges,'+port+',old_'+port+');']
wrapper += [' diff_edges=diff_edges+1;', 'end', 'final $display("H16_NATIVE_DIFF_PASS edges=%0d outputs='+str(len(outputs))+'",diff_edges);', 'endmodule']
(out/'compare_wrapper.sv').write_text('\n'.join(wrapper)+'\n')
parent = Path('rtl/qwen_dv/qfd_tt_ctlm_dv.sv').read_text()
needle = 'ot_qfd_tt_ctlm_static_hr #('
assert parent.count(needle) == 1
clock = '.ck_head(ck), .ck_pm0(ck), .ck_pm1(ck),'
assert parent.count(clock) == 1
parent = parent.replace(needle, name+' #(').replace(clock, '.ck_head(ck),')
Path('rtl/qwen_dv/qfd_tt_ctlm_dv_h16z_qualification.sv').write_text(parent)
sources = Path('rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines()
sources = ['rtl/qwen_dv/qfd_tt_ctlm_dv_h16z_qualification.sv' if f=='rtl/qwen_dv/qfd_tt_ctlm_dv.sv' else f for f in sources]
sources += [str(out/f) for f in ['candidate.v','candidate_helpers.sv','oldref.v','oldref_helpers.sv','compare_wrapper.sv']]
sources += ['physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v']
Path('rtl/test/qwen_dv/tt_ctlm_dv_h16z_qualification_sources.f').write_text('\n'.join(sources)+'\n')
tb = Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv').read_text()
for signal in ['fixed_issue','fixed_end','fixed_pc','fixed_unit']:
    tb = tb.replace('`TB_HEAD.'+signal, 'dut.g_hard_hr.u_hr.\\u_head.'+signal+' ')
Path('rtl/test/qwen_dv/tb_qfd_tt_ctlm_h16z_qualification.sv').write_text(tb)
bench = Path('rtl/test/qwen_dv/tt_ctlm_prog_bench.py').read_text()
bench = bench.replace('tt_ctlm_dv_sources.f','tt_ctlm_dv_h16z_qualification_sources.f').replace("HERE / 'tb_qfd_tt_ctlm_prog.sv'", "HERE / 'tb_qfd_tt_ctlm_h16z_qualification.sv'")
sim_call = "    subprocess.run([str(obj / 'Vtb'),"
assert bench.count(sim_call)==1
bench=bench.replace(sim_call, "    sim = subprocess.run([str(obj / 'Vtb'),")
end_call = '                   capture_output=True)'
assert bench.count(end_call)==1
bench=bench.replace(end_call,end_call+"\n    (work / f'stdout_{tag}.log').write_bytes(sim.stdout)\n    (work / f'stderr_{tag}.log').write_bytes(sim.stderr)")
Path('rtl/test/qwen_dv/tt_ctlm_prog_h16z_qualification.py').write_text(bench)
print('H16_QUAL_PREPARED ports='+str(len(decl))+' outputs='+str(len(outputs)))
