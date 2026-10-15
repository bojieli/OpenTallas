#!/usr/bin/env python3
import pathlib,subprocess,json,hashlib
R=pathlib.Path(__file__).resolve().parents[3];D=R/'rtl/physical';B=R/'station_gate_build';B.mkdir(exist_ok=True)
s=(D/'ot_hdc_vstream_static_relay_entries.sv').read_text();a=s.index('            (* keep *) reg [GBW-1:0] gb;');b=s.index('\n        end\n',a);body=s[a:b]
ref='''module group_reference(input wire clk,rst_n,input wire[499:0]b_d,input wire[2:0]b_v,output wire[499:0]b_q,output wire[2:0]b_vq);
localparam GBW=500;wire[17:0]v;wire[18:0]fin_th;wire[23:0]rrow,asi,bsi,csi,dsi;wire asrc,bsrc,csrc,mc,md,redsq;wire[1:0]ma,mb,dst,red;wire[2:0]ad,cls,i_sfu;wire[31:0]imm1,imm2;wire[255:0]wrom_q;wire emit,accept,v_last_r;
assign {v,fin_th,rrow,asi,bsi,csi,dsi,asrc,bsrc,csrc,mc,md,redsq,ma,mb,dst,red,ad,cls,i_sfu,imm1,imm2,wrom_q}=b_d;
assign {emit,accept,v_last_r}=b_v;
'''+body+'\nassign b_q=gb;assign b_vq=gv;endmodule\n'
a=s.index('    reg              rd_v,');b=s.index('    wire f_red;',a)
ref+='''module reducer_reference(input wire clk,rst_c,input wire[63:0]l_ov,input wire[127:0]l_red,input wire[63:0]l_redsq,l_last,input wire[1535:0]l_raddr,input wire[2047:0]l_out,output wire[2075:0]q);
localparam AW=24,SW=64;
'''+s[a:b]+'\nassign q={rd_v,rd_mx,rd_sq,rd_last,rd_addr,rd_x};endmodule\n'
(B/'reference.sv').write_text(ref)
files=[D/'ot_qfd_su_octet_station_candidate.sv',R/'tools/qwen_su_glue_1015/base_inventory/tb_station_candidate.sv',B/'reference.sv',R/'tools/qwen_su_glue_1015/base_inventory/ot_hdc_delay.sv']
results=[]
for name,params,expected in [('baseline',{},0),('octet_data',{'DM':1},1),('group_reset',{'RM':1},1),('reducer_data',{'RDM':1},1),('clock_connection',{'CM':1},1)]:
 exe=B/name;cmd=['iverilog','-g2012','-s','tb_station_candidate','-o',str(exe)]+[f'-Ptb_station_candidate.{k}={v}' for k,v in params.items()]+list(map(str,files))
 subprocess.run(cmd,check=True);run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(B/(name+'.log')).write_text(run.stdout+run.stderr)
 assert (run.returncode==0)==(expected==0),(name,run.stdout,run.stderr)
 assert ('PASS station checked=500' in run.stdout) if expected==0 else ('FAIL station' in run.stdout)
 results.append(dict(name=name,exit=run.returncode,expected_failure=bool(expected),log=run.stdout.strip()))
deps=[D/'ot_qfd_sp_su64_station_candidate.sv',D/'ot_hdc_vstream_station_candidate.sv',R/'tools/qwen_su_glue_1015/base_inventory/leaf_boundaries.sv',R/'tools/qwen_su_glue_1015/base_inventory/native_relay_boundary.sv',R/'tools/qwen_su_glue_1015/base_inventory/reset.sv',R/'tools/qwen_su_glue_1015/base_inventory/ot_hdc_vred_pending_guard.sv']
caller=R/'tools/qwen_su_glue_1015/base_inventory/tb_station_caller.sv'
subprocess.run(['iverilog','-g2012','-s','tb_station_caller','-o',str(B/'caller')]+list(map(str,[files[0],files[2],files[3],caller]+deps)),check=True)
run=subprocess.run(['vvp',str(B/'caller')],capture_output=True,text=True);(B/'caller.log').write_text(run.stdout+run.stderr)
assert run.returncode==0 and 'PASS caller checked=128' in run.stdout,(run.stdout,run.stderr)
results.append(dict(name='actual_caller_binding',exit=run.returncode,log=run.stdout.strip(),scope='actual native caller with explicit component-boundary stimuli replacing arithmetic outputs; no arithmetic claim'))
files+=deps+[caller,D/'qfd_sp_su64_sfu_station_candidate.sv']
topdeps=[D/'qfd_sp_su64_sfu_station_candidate.sv',D/'qfd_su_static_copy_entries.sv',R/'tools/qwen_su_glue_1015/base_inventory/qfd_su_vm_pack.sv',R/'tools/qwen_su_glue_1015/base_inventory/copy_core_boundary.sv']
for cut in (0,1):
 run=subprocess.run(['iverilog','-g2012','-s','qfd_sp_su64_sfu_station_candidate','-Pqfd_sp_su64_sfu_station_candidate.EXTERNAL_EMBED=1',f'-Pqfd_sp_su64_sfu_station_candidate.STATION_CUT={cut}','-o',str(B/f'top{cut}')]+list(map(str,[files[0],files[3]]+deps+topdeps)),capture_output=True,text=True)
 (B/f'top{cut}.log').write_text(run.stdout+run.stderr);assert run.returncode==0,(cut,run.stderr)
 results.append(dict(name=f'strict_native_top_elaboration_cut{cut}',exit=run.returncode,log=run.stderr.strip(),scope='no missing-module ignore; exact source boundaries are blackboxes, not functional arithmetic'))
files+=topdeps
print(json.dumps(dict(schema='opentallas.qwen-su-station-component-gate.v1',reference='exact original group/reducer always blocks extracted from immutable source; actual original delay helper used',source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_relative_to(R)},cases=results,scope='station edge/reset/data/clock wiring only; no arithmetic, production caller or physical qualification'),indent=2))
