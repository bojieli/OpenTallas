#!/usr/bin/env python3
"""Directed actual extracted control/broadcast simulation, not engine equivalence."""
import argparse,hashlib,json,pathlib,subprocess,resource,shutil,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
PACK=pathlib.Path('results/uarch/qwen_rom_connected_control_20261003')
ARCH=ROOT/'results/uarch/qwen_rom_issue_lockstep_terminal_20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate(mutant=None):
 plan=json.loads((ROOT/PACK/'frozen-plan-r1.json').read_text())
 for name,want in plan['source_pins'].items():
  if sha(ARCH/name)!=want:raise ValueError('frozen source mismatch '+name)
 raw=(ARCH/'raw/literal.sv').read_text()
 # Remove only the original formal checker, preserving every actual module/instance/connection.
 view=raw.split('reg seen_reset=0;',1)[0]+'endmodule\n'
 if mutant=='ungated_go':view=view.replace('.d(go && ready)','.d(go)')
 if mutant=='KV_PREP':view=view.replace('.LOCAL_KV_PREP(3)','.LOCAL_KV_PREP(2)')
 if mutant=='ib_bit':view=view.replace('ib_q <= tile_ib','ib_q <= tile_ib ^ 379\'d1')
 if mutant=='address':view=view.replace('wrom_addr <= cur;','wrom_addr <= cur + 1;')
 if mutant=='hold':view=view.replace('if (go) begin','if (go || i_round) begin')
 if mutant=='pipeline':view=view.replace('tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0];','tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0] + 1;')
 me=(ARCH/'source-inputs/rtl/hdc/ot_qwen_w12_matvec.sv').read_text()
 operators=me[me.index('module ot_qwen_w12_kadd'):]
 rows=plan['state_inventory'];regs=[];snapshot=[];checks=[]
 phase={'active','pend','pcnt','split_fault','wrom_re','kv_re'}
 pipeline={'pr_a','tsg_a','otsg_a','kc_a','tsh','osh','kpad_a','tstep_r','ot_step','k_r','nb_step','lb_step'}
 inner={'pr_a','tsg_a','otsg_a','kc_a','tsh','osh','kpad_a'}
 for r in rows:
  n,w,count=r['name'],r['width'],r['elements'];h='g_issue_fast.' if n in inner else ''
  for i in range(count):
   tag=n+'_'+str(i);index='['+str(i)+']' if count>1 else '';path=h+n+index
   regs.append('reg [%d:0] ref_%s;'%(w-1,tag));snapshot.append('ref_%s=dut.root.%s;'%(tag,path))
   qual='1' if n in phase else ('dut.tr' if n=='wrom_addr' else ('age>=5' if n in pipeline else 'age>=1'))
   checks.append('if (%s && dut.tile.%s !== ref_%s) $fatal(1,"state %s cycle=%%0d",cycles);'%(qual,path,tag,tag))
 tb='''`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,go=0;reg[378:0]ib=0;reg[127:0]xl=0;
lockstep dut(.clk(clk),.rst_n(rst_n),.go(go),.ib(ib),.xl(xl));
integer cycles=0,age=0,accepted=0,rejected=0,checks=0,reads=0,kvreads=0,pendchecks=0,resets=0;
reg[378:0]ref_ib;reg[127:0]ref_x;reg ref_go,accept_pre,valid_pre;
integer watch=0,index=0;reg[23:0] expected[0:127];
'''+ '\n'.join(regs)+'''
task tick;
begin
 clk=0;#1;
 ref_ib=ib;ref_x=xl;ref_go=rst_n&&go&&dut.ready;accept_pre=ref_go;
 valid_pre=rst_n;
 if(accept_pre) accepted=accepted+1;
 if(rst_n&&go&&!dut.ready)rejected=rejected+1;
'''+ '\n'.join(snapshot)+'''
 clk=1;#1;cycles=cycles+1;
 if(dut.ib_q !== ref_ib || dut.xl_q !== ref_x) $fatal(1,"every-edge ib/x capture cycle=%0d",cycles);
 if(dut.go_q !== ref_go)$fatal(1,"accepted go cycle=%0d",cycles);
 if(!rst_n)begin
  age=0;resets=resets+1;
  if(dut.root_state!==0 || dut.tile_state!==0 || dut.rr || dut.kr || dut.tr || dut.tk)$fatal(1,"reset phase/strobe");
 end else begin
'''+ '\n'.join(checks)+'''
  checks=checks+1;
  if(dut.go_q && !dut.tre)$fatal(1,"accepted go reached nonready tile");
  if(dut.root.pend)pendchecks=pendchecks+1;
  if(dut.rr)begin
   reads=reads+1;
   if(watch)begin
    if(index>=128 || dut.ra !== expected[index])$fatal(1,"independent ROM address index=%0d got=%h expected=%h",index,dut.ra,expected[index]);
    index=index+1;
   end
  end
  if(dut.kr)kvreads=kvreads+1;
  if(accept_pre) age=1;else if(age>0)age=age+1;
 end
 clk=0;#1;
end endtask
// Real379bit field order, including unused-by-control fields. No added input hold contract.
task cmd(input integer kv,input integer nt,input integer kval,input integer split,input[23:0]base,input[23:0]ts,input[23:0]ks,input[23:0]js,input integer jsh);
begin ib={18'd77,nt[17:0],kval[17:0],kv[0],base,ts,ks,js,24'h800,24'h31,24'h9,24'h40,jsh[2:0],split[3:0],24'h12345,1'b0,24'ha00,24'h101,24'h7,1'b0,1'b1,1'b0,1'b0,24'hc00};end endtask
task finish_op;
integer guard;
begin
 guard=0;go=0;
 while(!dut.ready || !dut.tre || dut.go_q)begin tick;guard=guard+1;if(guard>512)$fatal(1,"directed transaction failed to drain");end
 tick;tick;
end endtask
integer t,k,j,n;
initial begin
 tick;tick;rst_n=1;tick;tick;
 // First ROM: independent K/tile/rotation address sequence and24bit modular wrap.
 cmd(0,2,2,6,24'hffffd0,24'h120,24'h31,24'h3,1);
 n=0;for(t=0;t<2;t=t+1)for(k=0;k<2;k=k+1)for(j=0;j<8;j=j+1)begin expected[n]=(24'hffffd0+t*24'h120+k*24'h31+(j/2)*3);n=n+1;end
 watch=1;index=0;go=1;tick;
 // Busy offers are actual refused go; changing payload must not change latched instruction.
 repeat(8)begin cmd(1,1,65,7,24'hbad,24'h17,24'h29,24'h5,0);xl=xl+1;go=1;tick;end
 go=0;finish_op;watch=0;if(index!=32)$fatal(1,"ROM read count got=%0d",index);
 // Idle changes do not launch work, while payload capture remains unconditional.
 repeat(7)begin ib=~ib;xl=~xl;go=0;tick;end
 // KV waits actual3cycles; input changes and offers during pending/active must be refused.
 cmd(1,2,129,6,24'h123,24'h5,24'h11,24'h3,0);go=1;tick;
 repeat(6)begin ib=~ib;go=1;tick;end
 go=0;finish_op;
 if(kvreads!=48)$fatal(1,"KV ceil129/64 *2tiles *8 mismatch got=%0d",kvreads);
 // Next eligible acceptance, zero idle-gap assumption; first-read init after reset.
 cmd(0,1,1,6,24'h555,24'h3,24'h7,24'h9,0);go=1;tick;go=0;finish_op;
 // Async reset in active, immediate reset effects before clock then recovery.
 cmd(0,2,3,6,24'h678,24'h21,24'h9,24'h3,0);go=1;tick;go=0;tick;
 rst_n=0;#1;if(dut.root.active || dut.tile.active || dut.rr || dut.tr || dut.go_q)$fatal(1,"async active reset");tick;rst_n=1;tick;
 cmd(1,2,129,6,24'h222,24'h7,24'h11,24'h5,0);go=1;tick;
 rst_n=0;#1;if(dut.root.pend || dut.tile.pend || dut.go_q)$fatal(1,"async pending reset");tick;rst_n=1;go=0;tick;
 cmd(0,1,1,5,24'h333,24'h3,24'h5,24'h7,0);go=1;tick;go=0;finish_op;
 if(!dut.root.split_fault || !dut.tile.split_fault)$fatal(1,"actual split fault not latched");
 repeat(3)tick;
 rst_n=0;tick;rst_n=1;tick;
 cmd(0,1,1,6,24'h444,24'h3,24'h5,24'h7,0);go=1;tick;go=0;finish_op;
 if(accepted!=8 || rejected<10 || pendchecks<3 || checks<100 || resets<4)$fatal(1,"coverage not met acc=%0d reject=%0d pend=%0d check=%0d reset=%0d",accepted,rejected,pendchecks,checks,resets);
 $display("PASS_QROM_DIRECTED_CONNECTED_CONTROL cycles=%0d accepted=%0d rejected=%0d checks=%0d ROMreads=%0d KVreads=%0d pendchecks=%0d resets=%0d CONTROL_ONLY",cycles,accepted,rejected,checks,reads,kvreads,pendchecks,resets);$finish;
end
endmodule
'''
 return view,operators,tb

def run(out,mutant=None):
 if out.exists():raise ValueError('exclusive output directory required')
 out.mkdir(parents=True)
 before={str(p):sha(ROOT/p) for p in [PACK/'frozen-plan-r1.json',pathlib.Path('tools/qrom_connected_control_gate.py')]}
 view,ops,tb=generate(mutant)
 for name,text in [('control.sv',view),('operators.sv',ops),('tb.sv',tb)]: (out/name).write_text(text)
 tools={k:pathlib.Path(shutil.which(k)) for k in ['iverilog','vvp']}
 command=[str(tools['iverilog']),'-g2012','-s','tb','-o',str(out/'sim.vvp'),str(out/'control.sv'),str(out/'operators.sv'),str(ARCH/'source-inputs/rtl/hdc/ot_qwen_w12_arith.sv'),str(ARCH/'source-inputs/rtl/hdc/ot_hdc_delay.sv'),str(out/'tb.sv')]
 results=[]
 for name,argv in [('compile',command),('run',[str(tools['vvp']),str(out/'sim.vvp')])]:
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
  results.append({'stage':name,'argv':argv,'rc':r.returncode,'log_sha256':sha(out/(name+'.log'))})
  if r.returncode:break
 passed=len(results)==2 and all(r['rc']==0 for r in results) and 'PASS_QROM_DIRECTED_CONNECTED_CONTROL' in (out/'run.log').read_text()
 after={p:sha(ROOT/p) for p in before}
 if before!=after:passed=False
 terminal={'status':'PASS_DIRECTED_CONTROL_ONLY' if passed else 'FAIL_DIRECTED_CONTROL','mutant':mutant,'results':results,'source_before':before,'source_after':after,'tool_binary_sha256':{k:sha(p) for k,p in tools.items()},'limits':{n:list(resource.getrlimit(v)) for n,v in [('CPU',resource.RLIMIT_CPU),('AS',resource.RLIMIT_AS),('FSIZE',resource.RLIMIT_FSIZE)]},'source_geometry_and_clock_changed':False,'formal':False,'whole_engine':False,'owned_ready':False,'provider_or_ACK':False,'CDC_or_physical':False,'new_numerical_token':False,'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}}
 (out/'terminal.json').write_text(json.dumps(terminal,indent=2,sort_keys=True)+'\n');return terminal
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=pathlib.Path,required=True);parser.add_argument('--mutant',choices=['ungated_go','KV_PREP','ib_bit','address','hold','pipeline']);a=parser.parse_args();result=run(a.out,a.mutant);print(result['status']);raise SystemExit(0 if result['status']=='PASS_DIRECTED_CONTROL_ONLY' else 1)
