#!/usr/bin/env python3
"""Minimum full controller issue-boundary gate; no whole-array simulation."""
from pathlib import Path
import json,subprocess,sys,argparse,hashlib,shutil
import qwen_rom_core_ctx_claude as C
import qwen_core_separate_load as S
import qwen_core_opaque_interfaces as O
import qwen_core_kv_boundary as K
import qwen_core_meif_idle_capture as Q
from qwen_core_kv_bridge_tb import bridge_lines
R=C.ROOT
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--yosys',default='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys');args=ap.parse_args();P=args.out.resolve();P.mkdir(parents=True,exist_ok=False)
C.RETAINED=R/'physical/qwen_core_ctx/retained_screen_synth.ys'
for cand in [0,1,2]:
 dest=P/f'full{cand}';original=C.core_text
 C.core_text=lambda *a,**kw:Q.apply(K.apply(S.apply(original(*a,**kw)))) if cand else K.apply(S.apply(original(*a,**kw)))
 sys.argv=['prepare','--out',str(dest),'--fallback','3','--bound','--amq','--nxreg','--meif','--suif','--pinreg'];C.main();C.core_text=original
 prep=dest/'prepare.ys';lines=prep.read_text().splitlines()
 lines=[x+' -chparam DEC_LA_SEPARATE_LOAD 1'+' -chparam DEC_LA_KV_BANK 1'+(f' -chparam DEC_LA_MEIF_IDLE_CAPTURE {cand}' if cand else '') if x.startswith('hierarchy ') else x for x in lines]
 lines=['proc\nflatten\nopt_clean' if x.startswith('synth ') else x for x in lines]
 prep.write_text('\n'.join(lines)+f'\nwrite_verilog -noattr {dest}/control.v\n')
 O.rewrite(prep)
 with (dest/'yosys.log').open('w') as log:subprocess.run([args.yosys,'-Q','-T','-s',str(prep)],stdout=log,stderr=subprocess.STDOUT,check=True)
 (dest/'opaque_width_gate.json').write_text(json.dumps(O.validate(dest/'specialized_before_blackbox.json'),indent=2)+'\n')
ports=json.loads((P/'full0/original.json').read_text())['modules']['ot_qwen_rom_core']['ports']
lines=['`timescale 1ns/1ps','module tb #(parameter NEG=0, STALL=0);','reg clk=0; always #5 clk=~clk; reg rst_n=0,start=0; integer cycle=0,i,j; reg [1023:0] mem[0:64];','`include "ot_hdc_isa.svh"','always @(posedge clk) cycle<=cycle+1;']
outs={};widths={}
for d in [0,1]:
 lines += [f'reg [1023:0] pq{d}=0; integer bm{d}=0,bs{d}=0,nm{d}=0,ns{d}=0,nd{d}=0;']
 con=[]
 for idx,(name,port) in enumerate(ports.items()):
  width=len(port['bits']);signal=f'o{d}_{idx}'
  if port['direction']=='output':
   lines.append(f'wire [{width-1}:0] {signal};');outs[d,name]=signal;widths[name]=width
  else:
   signal=f"{width}'d0"
   special={'clk':'clk','rst_n':'rst_n','start':'start','token':"18'd7",'pos':"18'd8191",'prog_q':f'pq{d}',
    'kv_ok':"1'b1",'kv_write_drained':f'drain{d}','g_vsu.u_su.kv_we':f'kvw_input{d}','w_ok':"1'b1",'emb_ok':"1'b1",'me_mem_ok':"(cycle%17 < 9)",
    'u_me.ready':f'((bm{d}==0) && (!STALL || cycle%7!=0))','u_me.idle':f'(bm{d}==0)',
    'g_vsu.u_su.ready':f'((bs{d}==0) && (!STALL || cycle%11!=0))','g_vsu.u_su.idle':f'(bs{d}==0)',
    'u_me.progress':"16'hffff",'g_vsu.u_su.progress':"16'hffff",'g_vsu.u_su.progress_rows':"16'hffff",
    'u_me.am_idx':"18'd7",'u_me.am_val':"32'h3f800000",'u_me.am_any':"1'b1"}
   signal=special.get(name,signal)
  con.append(f'.\\{name} ({signal})')
 lines.append(f'core{d} d{d}('+',\n'.join(con)+');')
 lines += bridge_lines(d, outs[d,'kv_write_flush'])
 # source graph cells and names unchanged, only top module renamed for the miter
 text=(P/f'full{d}/control.v').read_text().replace('module ot_qwen_rom_core(',f'module core{d}(',1)
 (P/f'core{d}.v').write_text(text)
 for unit,count in [('u_me','nm'),('g_vsu.u_su','ns')]:
  fields=[n for n in outs if n[0]==d and n[1].startswith(unit+'.i_')]
  names=sorted(n for _,n in fields);w=sum(widths[n] for n in names);widths[unit]=w
  lines.append(f'reg [{w-1}:0] {count}events{d}[0:63];')
 me=outs[d,'u_me.go'];su=outs[d,'g_vsu.u_su.go'];re=outs[d,'prog_re'];pa=outs[d,'prog_addr'];done=outs[d,'done']
 lines += [f'always @(posedge clk) begin if({re}) pq{d}<=mem[{pa}%65];',f'if(!rst_n) begin bm{d}<=0;bs{d}<=0;nm{d}=0;ns{d}=0;nd{d}=0;end else begin',f'if(bm{d}>0) bm{d}<=bm{d}-1; if(bs{d}>0) bs{d}<=bs{d}-1;',f'if({done}) nd{d}=nd{d}+1;']
 for unit,count,busy,go in [('u_me','nm','bm',me),('g_vsu.u_su','ns','bs',su)]:
  names=sorted(n for dd,n in outs if dd==d and n.startswith(unit+'.i_'));payload='{'+','.join(outs[d,n] for n in names)+'}'
  accept=go+(f' && d{d}.me_en' if unit=='u_me' else '')
  lines += [f'if({accept}) begin if({busy}{d}!=0) $fatal(1,"duplicate acceptance d={d} unit={unit}");',f'{count}events{d}[{count}{d}]={payload} ^ ((NEG==1 && {d}==1 && {count}{d}==7) ? {widths[unit]}\'d1 : {widths[unit]}\'d0);',f'{count}{d}={count}{d}+1;{busy}{d}<=5+({count}{d}%3);end']
 lines += ['end end']
lines += ['initial begin','for(i=0;i<65;i=i+1) mem[i]=0;','for(i=0;i<64;i=i+1) begin',
 'mem[i][O_UNIT+:W_UNIT]=(i%2)+1;mem[i][O_BARRIER]=i%5==0;mem[i][O_WAIT_ME]=i%7==0;mem[i][O_WAIT_SU]=i%7==0;',
 'mem[i][O_ME_NOUT+:W_ME_NOUT]=1;mem[i][O_ME_TILES+:W_ME_TILES]=1;mem[i][O_ME_K+:W_ME_K]=1;mem[i][O_ME_WBASE+:W_ME_WBASE]=i*17;mem[i][O_ME_AMAX]=1;mem[i][O_ME_AMC]=i!=0;mem[i][O_ME_ROW0+:W_ME_ROW0]=i*17;',
 'mem[i][O_SU_NOUT+:W_SU_NOUT]=1;mem[i][O_SU_NIN+:W_SU_NIN]=1;mem[i][O_DST+:W_DST]=2;end',
 'repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);start=1;@(negedge clk);start=0;',
 'repeat(20) @(negedge clk);rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);start=1;@(negedge clk);start=0;',
 'wait(nd0>0 && nd1>0);wait(drain0 && drain1);repeat(4) @(negedge clk);',
 "if(memory0!=={32{8'h38}} || memory1!=={32{8'h38}}) $fatal(1,\"KV final memory mismatch\");",
 'if(nm0!=32 ||nm1!=32 ||ns0!=32 ||ns1!=32) $fatal(1,"counts ME%0d/%0d SU%0d/%0d",nm0,nm1,ns0,ns1);',
 'for(j=0;j<32;j=j+1) begin if(nmevents0[j]!==nmevents1[j]) $fatal(1,"ME event mismatch %0d",j); if(nsevents0[j]!==nsevents1[j]) $fatal(1,"SU event mismatch %0d",j);end',
 f"if({outs[0,'next_token']}!=={outs[1,'next_token']} || {outs[0,'next_val']}!=={outs[1,'next_val']}) $fatal(1,\"END result mismatch\");",
 f'$display("CYCLES base=%0d candidate=%0d KVwrites=%0d/%0d",{outs[0,"cycles"]},{outs[1,"cycles"]},writes0,writes1);',
 '$display("PASS full controller FB3 BOUND AMQ NXREG MEIF SUIF PINREG: ME32 SU32 fields exact; no duplicate acceptance; reset abort; END");$finish;end',
 'initial begin repeat(10000) @(posedge clk);$display("DBG nm %d/%d ns %d/%d st %d/%d nx %b/%b fault %b/%b kv %b/%b",nm0,nm1,ns0,ns1,d0.st,d1.st,d0.nx_v,d1.nx_v,d0.fault,d1.fault,d0.kv_ok_i,d1.kv_ok_i);$fatal(1,"liveness");end','endmodule']
(P/'core_bad.v').write_text((P/'full2/control.v').read_text().replace('module ot_qwen_rom_core(', 'module core1(',1))
lines += ['module ICGx1_ASAP7_75t_R(input CLK,ENA,SE, output GCLK);reg en;always @(*) if(!CLK) en=ENA|SE;assign GCLK=CLK&en;endmodule']
(P/'full_tb.sv').write_text('\n'.join(lines)+'\n')
rows=[]
for stall,neg in [(0,0),(1,0),(0,1),(0,2)]:
 name=f'full_s{stall}_n{neg}';cmd=['iverilog','-g2012','-I'+str(R/'rtl/hdc'),'-s','tb',f'-Ptb.STALL={stall}',f'-Ptb.NEG={neg}','-o',str(P/name),str(P/'core0.v'),str(P/('core_bad.v' if neg==2 else 'core1.v')),str(P/'full_tb.sv'),str(R/'rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv'),str(R/'rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv'),str(R/'rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv')]
 r=subprocess.run(cmd,text=True,capture_output=True);(P/(name+'.compile.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr[-3500:])
 r=subprocess.run(['vvp',str(P/name)],text=True,capture_output=True);(P/(name+'.log')).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout,r.stderr);rows.append(dict(name=name,returncode=r.returncode,negative=bool(neg),passed=(r.returncode!=0 and ('ME event mismatch 7' if neg==1 else 'ME event mismatch') in r.stdout) if neg else (r.returncode==0 and 'PASS full controller' in r.stdout)))

record=dict(schema="qwen.meif_idle_capture.full_interface_gate.v1",status="pass" if all(r["passed"] for r in rows) else "fail",positive_engine_events=128,positive_KV_RMW_bytes=64,measured_cycle_cost=dict(expected_zero=True),rows=rows,source_sha256={(str(f.relative_to(R)) if f.is_relative_to(R) else "tools/"+f.name):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(C.__file__),Path(S.__file__),Path(O.__file__),Path(K.__file__),Path(Q.__file__),Path(__file__),R/"tools/qwen_core_kv_bridge_tb.py",R/"rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv",R/"rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv",R/"rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv"]},lowered_source_sha256={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [P/"full0/core.sv",P/"full1/core.sv",P/"core0.v",P/"core1.v"]},scope="Actual full controller, FB3 BOUND AMQ NXREG MEIF SUIF PINREG, retained shape G6144 SW64 NW18; minimum engine boundaries, no arithmetic or whole-system simulation")
(P/"result.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record,indent=2))
if record["status"]!="pass":raise SystemExit(1)
