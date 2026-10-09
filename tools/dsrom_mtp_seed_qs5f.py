#!/usr/bin/env python3
"""Four aligned native FP8 subtrees and actual LAT8 FP32 joins; remote only."""
import argparse,json,os,subprocess
from pathlib import Path
import numpy as np
import dsrom_mtp_seed_qelem as B
from dsrom_mtp_seed_qelem import F,I,A,G
B.TB=B.TB.replace('ot_v41_rom_elem_q_qx_w10 #(', 'ot_v41_rom_elem_q_qxpq_w10 #(').replace('.QX(QXV)', '.QX(QXV),.PQ(1),.QW(0),.QM(5),.QS(5)').replace('.go(go),', '.go(go),.go_tag(2\'d0),')
F.QRTL.append(B.ROOT/'rtl/v41rom/ot_v41_elem_pq_tags.sv')

def bench(wrong_three=False,unsafe_pq_start=False):
 s=B.TB.replace('gold[0:1]','gold[0:1],partgold[0:7],roots[0:7],jl[0:1],jr[0:1]').replace('cfg[0:24]','cfg[0:99]')
 s=s.replace('wire busy,fault;', 'wire busy,fault,walking,bank_free,sh_free;').replace('.go_tag(2\'d0),', '.go_tag(2\'d0),.walking(walking),.bank_free(bank_free),.sh_free(sh_free),')
 s=s.replace('if(rst_n && fault)$fatal(1,"element fault");', 'if(rst_n && fault)begin $display("SEED_QS5F_PROVENANCE cyc=%0d pq_fault=%b ffault=%b bk_fault=%b go=%b walking=%b sh_free=%b bank_free=%b",cyc,dut.u_e.pq_fault,dut.u_e.ffault,dut.u_e.bk_fault,go,walking,sh_free,bank_free);$fatal(1,"element fault");end ')
 s=s.replace('integer cyc=0,', '''integer issued=0,issue_streak=0,max_issue_streak=0;
 always @(posedge clk)if(rst_n)begin
 if(dut.u_e.issue)begin issued<=issued+1;issue_streak<=issue_streak+1;if(issue_streak+1>max_issue_streak)max_issue_streak<=issue_streak+1;end else issue_streak<=0;
 end
 integer phase=0,phase_hits=0,join_start=0,join_end=0;reg jv=0;reg[31:0]ja=0,jb=0,jout;wire jvo;wire[31:0]jy;wire[1:0]je;
 ot_v41_fadd joiner(.clk(clk),.rst_n(rst_n),.valid_in(jv),.a(ja),.b(jb),.y(jy),.err(je),.valid_out(jvo));
 task automatic add_join(input[31:0]a,b,output[31:0]y);
 @(negedge clk);ja=a;jb=b;jv=1;@(negedge clk);jv=0;wait(jvo);#0.01;if(je)$fatal(1,"join fault");y=jy;@(negedge clk);endtask
 integer cyc=0,''')
 s=s.replace('pval[j*32+:32]!==gold[j]','pval[j*32+:32]!==partgold[2*phase+j]').replace('gold[j]);','partgold[2*phase+j]);')
 s=s.replace('if(ny==0)first<=cyc;last<=cyc;end','roots[2*phase+j]<=pval[j*32+:32];if(ny==0)first<=cyc;last<=cyc;end')
 s=s.replace('if(|pv)ny<=ny+pv[0]+pv[1];','if(|pv)begin ny<=ny+pv[0]+pv[1];phase_hits<=phase_hits+pv[0]+pv[1];end')
 s=s.replace('$readmemh({dir,"/x.hex"},x);','$readmemh({dir,"/partial.hex"},partgold);$readmemh({dir,"/x.hex"},x);')
 start=s.index(' for(integer k=0;k<25;k++)');stop=s.index(' repeat(512)',start)
 loop=''' for(phase=0;phase<4;phase++)begin
 phase_hits=0;
 for(integer k=0;k<25;k++)begin cfg_v=1;cfg_a=k;cfg_d=cfg[25*phase+k];@(negedge clk);end cfg_v=0;repeat(6)@(negedge clk);go=1;if(phase==0)go_cycle=cyc;@(negedge clk);go=0;repeat(4)@(negedge clk);
 for(integer k=(phase<3 ? phase*128:384);k<(phase<3 ? (phase+1)*128:480);k++)begin
 xs_v=stream[k][0];xs_p=stream[k][8:1];xs_b=stream[k][11:9];xs_sv=stream[k][13:12];
 if(xs_v)begin xs_q0=qb[phase*128+xs_p*16+xs_b];xs_e0=eb[phase*128+xs_p*16+xs_b];xs_q1=qb[phase*128+xs_p*16+8+xs_b];xs_e1=eb[phase*128+xs_p*16+8+xs_b];end
 @(negedge clk);end xs_v=0;wait(phase_hits==2 && !busy);repeat(32)@(negedge clk);end
 join_start=cyc;
 for(integer j=0;j<2;j++)begin
 add_join(roots[j],roots[2+j],jl[j]);add_join(roots[4+j],roots[6+j],jr[j]);add_join(jl[j],jr[j],jout);
 if(jout!==gold[j])$fatal(1,"global root got %h want %h",jout,gold[j]);end
 join_end=cyc;
 if(issued!=480)$fatal(1,"wrong ROM read count %0d",issued);
 $display("SEED_QS5F_READS issues=%0d rowbank_reads=%0d payload_bytes=%0d MACs=%0d max_issue_streak=%0d",issued,2*issued,64*issued,64*issued,max_issue_streak);
'''
 s=s[:start]+loop+s[stop:];s=s.replace('if(ny!=2)','if(ny!=8)')
 if not unsafe_pq_start:
  # PQ's final configuration word starts a 17-word shadow replay. The
  # registered status covers QM5 replay stages; the six-cycle fence covers
  # the input pipeline and the tags' five-cycle SETTLE guard.
  s=s.replace('phase_hits=0;', 'phase_hits=0;wait(bank_free && sh_free);')
  s=s.replace('end cfg_v=0;repeat(6)@(negedge clk);go=1;', 'end cfg_v=0;repeat(6)@(negedge clk);wait(sh_free && !walking);repeat(6)@(negedge clk);go=1;')
 s=s.replace('$display("MTP_SEED PASS K=15360 rows=2 quant_cycles=%0d first_cycles=%0d last_cycles=%0d",quant_end-quant_start+1,first-go_cycle,last-go_cycle);', '$display("MTP_SEED_ALIGNED PASS K=15360 rows=2 phases=4 adds=6 joinLAT=8 quant_cycles=%0d first_cycles=%0d last_cycles=%0d join_cycles=%0d complete_column_cycles=%0d",quant_end-quant_start+1,first-go_cycle,last-go_cycle,join_end-join_start,join_end-quant_start+1);')
 if wrong_three:
  s=s.replace('partgold[0:7]','partgold[0:5]').replace('roots[0:7]','roots[0:5]').replace('cfg[0:99]','cfg[0:74]').replace('phase<4','phase<3')
  s=s.replace('k=(phase<3 ? phase*128:384);k<(phase<3 ? (phase+1)*128:480)', 'k=phase*192;k<(phase+1)*192').replace('phase*128+xs_p','phase*160+xs_p')
  s=s.replace('add_join(roots[j],roots[2+j],jl[j]);add_join(roots[4+j],roots[6+j],jr[j]);add_join(jl[j],jr[j],jout);','add_join(roots[j],roots[2+j],jl[j]);add_join(jl[j],roots[4+j],jout);').replace('if(ny!=8)','if(ny!=6)')
 return s

def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--ref',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--jobs',type=int,default=12);p.add_argument('--wrong-three',action='store_true');p.add_argument('--unsafe-pq-start',action='store_true');a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
 G.set_arith('chunk8');ck=A.Ckpt(a.snapshot)
 def mean(h):return G.to_bf16(G.mul(G.seqsum([h[j] for j in range(4)]),G.F(.25)))
 x=np.concatenate([mean(np.load(a.ref/f'ctx1048576_L{l}.npz')['h_in']) for l in (37,38,39)])
 m=A.Mat(ck,'mtp.0.main_proj','fp8',2,15360);acc,_,xq,xe=A.golden_rows(m,x);fld=I.Field(1,1,0,pp=True,fast=True);partials=[];phases=[]
 for offset,k in ([(0,5120),(5120,5120),(10240,5120)] if a.wrong_three else [(0,4096),(4096,4096),(8192,4096),(12288,3072)]):
  part=A.Mat(ck,'mtp.0.main_proj','fp8',2,k,k0=offset);part.s81_segments=[[0,k]];part.s81_place=[(0,0,0)];phases.append(I.add_phase(fld,[part],(True,True),0));partials.extend(A.golden_rows(part,x[offset:offset+k])[0])
 assert [p['nbeat'] for p in phases]==([192,192,192] if a.wrong_three else [128,128,128,96])
 for mb in range(2):
  for parity in (0,1):
   f=a.work/f'seed{"b" if mb else ""}_{parity}.viamap.hex';A.viamap({k//2:v for k,v in fld.words[mb].items() if k%2==parity},f);f.write_text(''.join(f.read_text().splitlines(keepends=True)[:512]))
 def hx(n,vs,w):(a.work/n).write_text(''.join(f'{int(v):0{w}x}\n' for v in vs))
 codes=A.x_codes(xq);hx('x.hex',G.bits(x),8);hx('gold.hex',acc,8);hx('partial.hex',partials,8);hx('cfg.hex',[v for cfg in fld.cfg for v in cfg[0]],12);hx('stream.hex',fld.stream,12);hx('q.hex',[int.from_bytes(codes[k:k+32].tobytes(),'little') for k in range(0,15360,32)],64);hx('e.hex',xe.astype(int)&1023,3)
 tb=a.work/'tb.sv';tb.write_text(bench(a.wrong_three,a.unsafe_pq_start).replace('QXV','10').replace('NBTS',str(len(fld.stream))))
 (a.work/'plan.json').write_text(json.dumps(dict(source='four aligned segment subtrees; no engine RTL change',phases=phases,seed_model_function='uarch_model.dsrom_mtp_seed_qs5f_candidate',selected_native_source='fa27bd60819f9bf61483d5605a02837fe6a34088',selected_native_master='ot_v41_rom_elem_q_qxpq_w10',params=dict(QX=10,PQ=1,QW=0,QM=5,QS=5),native_physical_closed=False,collector='one actual ot_v41_fadd LAT8;6 serialized operations for2 rows',whole_field_qualified=False),indent=1)+'\n')
 sources=list(dict.fromkeys(F.RTL+F.QRTL+F.ROMS));run=subprocess.run([os.environ.get('OT_VERILATOR',F.VERILATOR),'--binary','--timing','-Wno-fatal','--top-module','tb_mtp_seed','--Mdir',str(a.work/'obj'),'-j',str(a.jobs),str(tb)]+list(map(str,sources)),text=True,capture_output=True);(a.work/'build.log').write_text(run.stdout+run.stderr)
 if run.returncode:raise RuntimeError('build failed')
 run=subprocess.run([str(a.work/'obj/Vtb_mtp_seed'),f'+DATA={a.work}',f'+OT_ROM_DIR={a.work}'],text=True,capture_output=True);(a.work/'sim.log').write_text(run.stdout+run.stderr);print(run.stdout)
 if a.unsafe_pq_start:
  if run.returncode and 'pq_fault=1' in run.stdout:print('MTP_SEED_PQ_START FAIL_AS_REQUIRED');return
  raise RuntimeError('unsafe PQ start did not expose the actual PQ fault')
 if a.wrong_three:
  if run.returncode and 'global root got' in run.stdout:print('MTP_SEED_WRONG3 FAIL_AS_REQUIRED');return
  raise RuntimeError('wrong-three negative did not expose changed tree')
 if run.returncode or 'MTP_SEED_ALIGNED PASS' not in run.stdout:raise RuntimeError('aligned seed failed')
if __name__=='__main__':main()
