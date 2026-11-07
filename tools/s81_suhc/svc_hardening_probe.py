#!/usr/bin/env python3
"""Prepare one native SML child-only size/ABI vehicle from a retained RS kit.
No parent elaboration target, extra pin registers, P&R or plan activation.
"""
import argparse,hashlib,json,pathlib,re,shutil
P=[('input','ck',1),('input','rst',1),('input','sk_en',1),('input','i_cv',1),('input','i_nv',7),('input','i_scale',32),('input','i_sink',32),('input','i_sv',1),('input','i_s',32),('input','i_mv',1),('input','i_nmb',32),('output','o_mxv',1),('output','o_mx',32),('output','o_ev',1),('output','o_es',1),('output','o_el',1),('output','o_e',32)]
def prepare(donor,out):
 donor=pathlib.Path(donor).resolve();out=pathlib.Path(out).resolve()
 if out.exists():raise ValueError('output must be new; preserve previous attempts')
 out.mkdir(parents=True);(out/'.keep').touch();(out/'rtl').mkdir()
 cfg=(donor/'config.mk').read_text();line=next(x for x in cfg.splitlines()if x.startswith('export VERILOG_FILES = '));paths=line.split('=',1)[1].split()
 hashes={}
 for s in paths:
  p=donor/s.removeprefix('/work/');target=out/s.removeprefix('/work/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 defs=next(x for x in cfg.splitlines()if x.startswith('export VERILOG_DEFINES = '))
 if(donor/'adder_map_dontuse.v').exists():shutil.copyfile(donor/'adder_map_dontuse.v',out/'adder_map_dontuse.v')
 decl=',\n'.join(f"    {d} wire {'['+str(w-1)+':0] 'if w>1 else ''}{n}"for d,n,w in P)
 binds=',\n'.join('        .'+n+'('+ ("(MUT ? 1'b0 : i_sv)" if n=='i_sv' else n)+')' for _,n,_ in P)
 wrapper='module codex_svc_sml_native #(parameter integer MUT=0) (\n'+decl+'\n);\n    dsfd_su_t_sml u_native (\n'+binds+'\n    );\nendmodule\n'
 (out/'rtl/codex_svc_sml_native.sv').write_text(wrapper)
 srcs=' '.join(paths+['/work/rtl/codex_svc_sml_native.sv'])
 config=f'''export DESIGN_NAME = codex_svc_sml_native
export PLATFORM = asap7
export RESULTS_DIR = /work/run/results/asap7/codex_svc_sml_native/base
export REPORTS_DIR = /work/run/reports/asap7/codex_svc_sml_native/base
export LOG_DIR = /work/run/logs/asap7/codex_svc_sml_native/base
export OBJECTS_DIR = /work/run/objects/asap7/codex_svc_sml_native/base
export VERILOG_FILES = {srcs}
{defs}
export SDC_FILE = /work/constraint.sdc
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_MEMORY_MAX_BITS = 16384
export DIE_AREA = 0 0 174.96 174.96
export CORE_AREA = 4.32 4.32 170.64 170.64
export PLACE_DENSITY = 0.40
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M6
export ADDER_MAP_FILE = /work/adder_map_dontuse.v
'''
 (out/'config.mk').write_text(config)
 (out/'constraint.sdc').write_text('''# Child-only synthesis budget. Not a propagated-clock STA qualification.
create_clock -name clk -period 833 [get_ports ck]
create_clock -name vclk -period 833
set_clock_latency -source 250 [get_clocks vclk]
set_clock_uncertainty -setup 0 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max 133.2 -clock vclk [all_inputs -no_clocks]
set_input_delay -min -40 -clock vclk [all_inputs -no_clocks]
set_output_delay -max 166.6 -clock vclk [all_outputs]
set_output_delay -min 180 -clock vclk [all_outputs]
''')
 bench='''`timescale 1ns/1ps
module tb;
reg ck=0;always #0.5 ck=~ck;
reg rst=0,i_cv=0,i_sv=0,i_mv=0;reg[31:0]i_s=0;
wire sk_en=0;wire[6:0]i_nv=9;wire[31:0]i_scale=32'h3f800000,i_sink=0,i_nmb=32'hbf800000;
'''
 for tag,typ,params in [('g','dsfd_su_t_sml',''),('c','codex_svc_sml_native',''),('m','codex_svc_sml_native','#(.MUT(1))')]:
  for d,n,w in P:
   if d=='output':bench+=f"wire {'['+str(w-1)+':0] 'if w>1 else ''}{tag}_{n};\n"
  binds=','.join(f'.{n}({tag+"_"+n if d=="output"else n})'for d,n,w in P)
  bench+=f'{typ} {params} u_{tag}({binds});\n'
 bench+='''integer checks=0,bad=0,mutdiff=0,validwords=0,lane,v;
always @(negedge ck) if(rst) begin
 checks=checks+1;
 if({g_o_mxv,g_o_ev,g_o_es,g_o_el} !== {c_o_mxv,c_o_ev,c_o_es,c_o_el})bad=bad+1;
 if(g_o_mxv && g_o_mx!==c_o_mx)bad=bad+1;
 if(g_o_ev && g_o_e!==c_o_e)bad=bad+1;
 if(g_o_ev)validwords=validwords+1;
 if({g_o_mxv,g_o_ev,g_o_es,g_o_el} !== {m_o_mxv,m_o_ev,m_o_es,m_o_el})mutdiff=mutdiff+1;
end
initial begin
 repeat(8)@(negedge ck);rst=1;repeat(8)@(negedge ck);
 for(lane=0;lane<16;lane=lane+1)begin
  i_cv=1;@(negedge ck);i_cv=0;repeat(4)@(negedge ck);
  for(v=0;v<9;v=v+1)begin i_sv=1;i_s=(v==8&&lane>4)?32'hff800000:32'h3f800000+(lane<<10)+(v<<16);@(negedge ck);end
  i_sv=0;wait(g_o_mxv);@(negedge ck);i_mv=1;@(negedge ck);i_mv=0;repeat(130)@(negedge ck);
 end
 $display("SML_NATIVE_BOUNDARY checks=%0d validwords=%0d bad=%0d mutantdiff=%0d cycles_added=0",checks,validwords,bad,mutdiff);
 if(bad || validwords<144 || mutdiff==0)$fatal(1,"SML_NATIVE_BOUNDARY FAIL");
 $display("SML_NATIVE_BOUNDARY PASS");$finish;
end
initial begin #20000;$fatal(1,"protocol did not complete within native component schedule");end
endmodule
'''
 (out/'tb.sv').write_text(bench)
 rec=dict(schema='opentallas.svc.native_sml_probe.v1',donor=str(donor),input_sha256=hashes,top='codex_svc_sml_native',native='dsfd_su_t_sml',port_bits=sum(w for d,n,w in P),ports=P,added_pin_cycles=0,added_reset_cycles=0,qualification='NOT_RUN',parent_plan='PRIVATE_ONLY; no macro or POR activation',outline_um=[174.96,174.96],legacy_sizing_only=dict(area_um2=10949,source='s81su_sml_tail133_current_ref',warning='legacy recipe3 has +2 wrapper edges; no timing/source qualification reuse'))
 (out/'PREPARE.json').write_text(json.dumps(rec,indent=2));print(out)
 return rec
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--donor',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();prepare(a.donor,a.out)
