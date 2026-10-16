#!/usr/bin/env python3
"""YB_STAGE=1 delayed equivalence of the four-column return successor (HC-COLUMN 10-16).
Reference = monolithic ot_s81_hc_ctra / ctrb at x(t).  DUT = *_columns YB_STAGE 1 with its fv-domain pins (rst_in, tid,
last, fv, fdx, cs, flags, ctra y beat) at x(t) and the chain-side pins (rv_in, rd_in / rdh_in / rdd_in, hrq) at x(t-1):
in the HC chain those arrive one cycle later because far-tile origination and the bank round trip shift with the engine.
ctrb takes the relayed y beat (ctra yb_rel) at x(t-1).  PASS = every request output equals the reference one cycle
later and every return output (rvm, rdm) two cycles later (+1 column payload stage, +1 y-beat stage).
Runs on ot-run only.  Mutants: unrelayed own y lanes, missing fv pin stage, ctrb relay lane order, hrq lane binding.
"""
import argparse, hashlib, json, re, subprocess, shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[2]; out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
s=(r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv').read_text()
def module(name):
 b=s.index('module '+name+' #(');return s[b:s.index('\nendmodule',b)+len('\nendmodule')]
support=(r/'rtl/hdc/ot_hdc_delay.sv').read_text()
vline=(r/'rtl/hdc/ot_hdc_sfu.sv').read_text(); vb=vline.index('module ot_hdc_vline'); support+='\n'+vline[vb:vline.index('endmodule',vb)+9]
ref=support+'\n'+'\n'.join(module(n) for n in ('ot_s81_hc_ctq','ot_s81_hc_ctrs','ot_s81_hc_ctra','ot_s81_hc_ctrb'))
(out/'reference.sv').write_text(ref)
dut=(r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv').read_text()
tops=[]
for half in ('a','b'):
 name='ot_s81_hc_ctr'+half;t=module(name);head=t[:t.index(');')]
 entries=[]
 for line in head.splitlines():
  m=re.match(r'\s*(input|output)\s+wire\s*(\[[^]]+\])?\s*(.*)',line)
  if m:
   for n in m[3].split('//')[0].strip().rstrip(',').split(','):
    entries.append((m[1],m[2] or '',n.strip()))
 chain={'rv_in','rd_in','rdh_in','rdd_in','hrq_n','hrq_s'}|({'yb_n','yb_s'} if half=='b' else set())
 inp=[(w,n) for d,w,n in entries if d=='input' and n!='clk'];outputs=[(w,n) for d,w,n in entries if d=='output']
 lines=[f'module check_{half};', 'localparam NG=256,D=5120,NCOL=3,GS=8,S_RD=2,S_RT=4,SH=2;', 'localparam O_D=104, P_D=108,WA=1132,WB=1152;', "reg clk=0; reg [31:0] rng=32'h12345678;", 'integer cycle,j; reg active;']
 for w,n in inp:lines += [f'reg {w} {n};']
 for w,n in outputs:lines += [f'wire {w} ref_{n}, dut_{n};',f'reg {w} prev_{n}, prev2_{n};']
 for w,n in inp:
  if n in chain:lines += [f'reg {w} d_{n};']
 params='#(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1))'
 links=[f'.{n}({n})' for _,n in inp]+[f'.{n}(ref_{n})' for _,n in outputs]
 lines += [name+' '+params+' ref_dut(.clk(clk),'+','.join(links)+');']
 links=[f'.{n}(d_{n})' if n in chain else f'.{n}({n})' for _,n in inp]+[f'.{n}(dut_{n})' for _,n in outputs]
 dparams=params[:-1]+',.YB_STAGE(1))'
 extra=',.yb_rel()' if half=='a' else ''
 lines += [name+'_columns '+dparams+' dut(.clk_col({4{clk}}),'+','.join(links)+extra+');','initial begin']
 for _,n in inp:
  if n in chain:lines += [f'd_{n}=0;']
 for _,n in inp:lines += [f'{n}=0;']
 lines += ['for(cycle=0;cycle<2500;cycle=cycle+1) begin','clk=0; #1;']
 for _,n in inp:
  if n=='rst_in':lines += ['rst_in=(cycle>=6 && !(cycle>=1200 && cycle<1204));']
  else:lines += [f'for(j=0;j<$bits({n});j=j+1) begin rng=rng ^ (rng<<13);rng=rng ^ (rng>>17);rng=rng ^ (rng<<5);{n}[j]=rng[0];end'] if n not in ('last','hov_d') else [f'{n}=rng[cycle%32];']
 # Keep all indices within production legal bounds, while alternating every return type.
 lines += ["tid=cycle%64; last=(cycle%31==0);", "fv='0;", "fv[S_RD+1]=(cycle%97==0); fv[S_RD+4]=(cycle%83==0); fv[S_RD+2]=(cycle%7==0); fv[S_RD+3]=(cycle%41==0); fdx[63 +:8]=cycle%5;"]
 # Avoid invalid ybuf indices in unrestricted headers: return vector indices 0..NV-1=4.
 if half=='a':lines += ['for(j=0;j<S_RT;j=j+1) begin rd_in[S_RT+8*j +:8]=(cycle+j)%5;rd_in[S_RT+8*S_RT+16*j +:16]=(cycle+j)%640;end','rd_in[S_RT+24*S_RT +:8]=cycle%5;']
 else: lines += ['for(j=0;j<S_RT;j=j+1) begin rdh_in[S_RT+8*j +:8]=(cycle+j)%5;rdh_in[S_RT+8*S_RT+16*j +:16]=(cycle+j)%640;end','rdh_in[S_RT+24*S_RT +:8]=cycle%5;']
 for _,n in outputs:lines += [f'prev2_{n}=prev_{n};',f'prev_{n}=ref_{n};']
 lines += ['#1;clk=1;']
 # chain-side inputs to the DUT lag the reference by one edge (registered by the bench at the same edge)
 for _,n in inp:
  if n in chain:lines += [f'd_{n}<={n};']
 lines += ['#1;', 'if(cycle>14 && !(cycle>=1200 && cycle<1215)) begin']
 for _,n in outputs:
  expect='prev2_'+n if n in ('rdm','rvm') else 'prev_'+n
  lines += [f'if(dut_{n} !== {expect}) $fatal(1,"{half} {n} mismatch cycle=%0d",cycle);']
 lines += ['end','end',f'$display("PASS {half} 2500 cycles exact delayed return and unchanged requests");$finish;end','endmodule']
 (out/f'check_{half}.sv').write_text('\n'.join(lines));tops.append(half)
# relay bench: ctra yb_rel (the ctrb y-beat source) == {yb_s, yb_n} one cycle late, all 256 bits, random stimulus
(out/'check_rel.sv').write_text("""module check_rel;
reg clk=0; reg [31:0] rng=32'h9e3779b9; integer cycle,j; reg [127:0] yb_n, yb_s; reg [255:0] prev; wire [255:0] yb_rel;
ot_s81_hc_ctra_columns #(.NG(256),.D(5120),.NCOL(3),.GS(8),.S_RD(2),.S_RT(4),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1),.YB_STAGE(1)) dut(
 .clk_col({4{clk}}),.rst_in(1'b1),.tid(8'd0),.last(1'b0),.fv(7'd0),.fdx(104'd0),.rv_in(8'd0),.rd_in(1132'd0),.rvm(),.rdm(),.rq_q(),.hs_run(),.hs_c(),
 .rq_q_c1(),.rq_q_c2(),.rq_q_c3(),.hs_run_c1(),.hs_run_c2(),.hs_run_c3(),.hs_c_c1(),.hs_c_c2(),.hs_c_c3(),.hrq_n(1024'd0),.hrq_s(1024'd0),
 .yb_n(yb_n),.yb_s(yb_s),.cs(128'd0),.nflt_n(8'd0),.nflt_s(8'd0),.hov_d(1'b0),.hnz_n(4'd0),.hnz_s(4'd0),.pflt_n(4'd0),.pflt_s(4'd0),.yb_rel(yb_rel));
initial begin yb_n=0; yb_s=0;
 for(cycle=0;cycle<2500;cycle=cycle+1) begin clk=0; #1;
  for(j=0;j<128;j=j+1) begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);yb_n[j]=rng[0];rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);yb_s[j]=rng[0]; end
  prev={yb_s,yb_n}; #1; clk=1; #1;
  if(cycle>2 && yb_rel!==prev) $fatal(1,"rel mismatch cycle=%0d",cycle);
 end
 $display("PASS rel 2500 cycles yb_rel = y beat one cycle late, 256 bits"); $finish; end
endmodule
""")
results=[]
MUT={'positive':[],
 'unrelayed_own_y':[('assign yb_all[16*n +:16]=yb_r[16*K +:16];','assign yb_all[16*n +:16]=yb_loc[16*K +:16];')],
 'missing_fv_stage':[('assign e_rst=rst_q; assign e_tid=tid_q; assign e_last=last_q; assign e_fv=fv_q;','assign e_rst=rst_q; assign e_tid=tid_q; assign e_last=last_q; assign e_fv=fv;')],
 'relay_lane_order':[('assign yb_rel[16*(c+4*k) +:16]=yb_fwd[16*k +:16];','assign yb_rel[16*(c+4*k) +:16]=yb_fwd[16*(3-k) +:16];')],
 'bad_lane':[('hrq_n[64*SH*(c+4*bank) +:64*SH]','hrq_n[64*SH*((c+1)%4+4*bank) +:64*SH]')]}
HALVES={'positive':('a','b','rel'),'unrelayed_own_y':('a',),'missing_fv_stage':('a',),'relay_lane_order':('rel',),'bad_lane':('a','b')}
for variant,subs in MUT.items():
 x=dut
 for o,n_ in subs:
  assert o in x,(variant,o); x=x.replace(o,n_)
 file=out/f'{variant}.sv';file.write_text(x)
 for half in HALVES[variant]:
  build=out/f'obj_{variant}_{half}';log=out/f'{variant}_{half}.log'
  verilator=shutil.which('verilator') or str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
  cmd=[verilator,'--binary','--timing','-Wno-fatal','--top-module','check_'+half,'--Mdir',str(build),'-j','4',str(out/'reference.sv'),str(file),str(out/f'check_{half}.sv')]
  with log.open('w') as f:
   b=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
   if b.returncode:raise SystemExit('COMPILE FAIL '+str(log))
   run=subprocess.run([str(build/('Vcheck_'+half))],stdout=f,stderr=subprocess.STDOUT)
  okay=(run.returncode==0)==(variant=='positive')
  results.append(dict(variant=variant,half=half,returncode=run.returncode,expected_verdict=okay,log=str(log)))
  if not okay:raise SystemExit('UNEXPECTED VERDICT '+str(log))
receipt={'status':'PASS','scope':'component delayed equivalence of YB_STAGE 1 (reference = monolithic ctra/ctrb); not canonical programme or physical closure','cycles_per_positive':2500,'added_return_cycles':2,'added_request_cycles':1,'yb_stage_added_cycles':1,'source_sha256':hashlib.sha256(dut.encode()).hexdigest(),'results':results}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
