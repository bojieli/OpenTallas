#!/usr/bin/env python3
"""Minimum SU native control capture; never an arithmetic or token-schedule proof."""
import argparse, csv, hashlib, json, re, subprocess, sys
from pathlib import Path
from collections import defaultdict

PROGRAM='results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/L20_program.hex'
SOURCES=['rtl/hdc/ot_hdc_vstream.sv','rtl/hdc/ot_hdc_vstream_lane.sv','rtl/hdc/ot_hdc_vreduce.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_sfu.sv','tools/hdc_isa.py',PROGRAM,'tools/qwen_rom_finite_vm_schedule.py']
def sha(s): return hashlib.sha256(s).hexdigest()
def run(root,out,mutant=None):
 out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(root/'tools'))
 from hdc_isa import decode
 pins={p:sha((root/p).read_bytes()) for p in SOURCES}
 program=[decode(int(x,16)) for x in (root/PROGRAM).read_text().splitlines()]
 static={p:d for p,d in enumerate(program) if d['unit']==2 and not any(d[k] for k in ('su_d_nin','a_d','b_d','c_d','d_d'))}
 excluded={p:{k:d[k] for k in ('su_d_nin','a_d','b_d','c_d','d_d') if d[k]} for p,d in enumerate(program) if d['unit']==2 and p not in static}
 removed=[];units=[]
 for path in SOURCES[:4]:
  src=(root/path).read_text()
  def remove(m):
   instance=m.group();typ=m[1];body=m[2];removed.append(dict(path=path,sha256=sha(instance.encode()),text=instance))
   if typ in ('ot_hdc_qadd','ot_hdc_qmul'):
    args=body.split(',');return 'assign '+args[-2].strip()+" = 32'd0; assign "+args[-1].strip()+" = 1'b0; // arithmetic unobserved"
   ports=dict(re.findall(r'\.(\w+)\((\w+)\)',body))
   return ' '.join('assign '+ports[k]+" = '0;" for k in ('y','vo','fault'))+' // arithmetic unobserved'
  src=re.sub(r'\b(ot_hdc_qadd|ot_hdc_qmul|ot_hdc_exp_q|ot_hdc_recip_q|ot_hdc_rsqrt_q)\s+\w+\s*\((.*?)\);',remove,src,flags=re.S)
  units.append(src)
 sf=(root/SOURCES[4]).read_text();units.append(sf[sf.index('module ot_hdc_vline #'):sf.index('endmodule',sf.index('module ot_hdc_vline #'))+9])
 control='\n'.join(units)
 mutations={'read_enable':('vb_re <= emit && !bsrc;', 'vb_re <= emit && bsrc;'), 'write_address':('vm_waddr <= o_daddr;', "vm_waddr <= o_daddr + 1'b1;"), 'reducer_address':('o_addr <= st[LV][AW-1:0];', "o_addr <= st[LV][AW-1:0] + 1'b1;")}
 if mutant:
  before,after=mutations[mutant];assert control.count(before)==1;control=control.replace(before,after)
 (out/'control.sv').write_text(control)
 fields={'nout':'su_nout','nin':'su_nin','redsq':'red_sq'}
 for x in 'abcd':
  for y in ('base','so','si'): fields[x+y]=x+'_'+y
 for x in 'abc': fields[x+'src']=x+'_src'
 for y in ('base','so'):fields['r'+y]='r_'+y
 for x in ('ma','mb','ad','sfu','mc','md','dst','red','imm1','imm2'):fields[x]=x
 declarations='\n'.join('reg [31:0] i_'+k+';' for k in fields)
 ports=[f'.i_{k}(i_{k})' for k in fields]
 ports+=['.clk(clk)','.rst_n(rst_n)','.go(go)','.ready(ready)','.idle(idle)','.fault(fault)',".va_q('0)",".vb_q('0)",".vc_q('0)",".crom_q('0)",".wrom_q('0)"]
 for x in ('va','vb','vc'):ports += [f'.{x}_re({x}_re)',f'.{x}_addr({x}_addr)']
 ports+=['.progress(progress)','.progress_rows(progress_rows)','.vm_we(vm_we)','.vm_waddr(vm_addr)','.red_we(red_we)','.red_addr(red_addr)']
 cases='\n'.join(str(p)+': begin '+ ' '.join('i_'+k+"=32'd"+str(d[v])+';' for k,v in fields.items())+' end' for p,d in static.items())
 pcs=','.join(str(p) for p in static)
 bench='''module tb;
reg clk=0,rst_n=0,go=0;
wire [15:0] progress,progress_rows; wire ready,idle,fault,red_we; wire[23:0] red_addr;
wire[63:0] va_re,vb_re,vc_re,vm_we;
wire[64*24-1:0] va_addr,vb_addr,vc_addr,vm_addr;
DECL
 ot_hdc_vstream #(.SW(64),.LV(7),.WR(64),.AW(24),.NW(18)) dut(PORTS);
integer pc,n,count,fd;
initial begin
 fd=$fopen("trace.csv","w");
 $fdisplay(fd,"pc,cycle,ready,idle,va_re,va_addr,vb_re,vb_addr,vc_re,vc_addr,vm_we,vm_addr,red_we,red_addr,progress,progress_rows");
 for(pc=0;pc<PCMAX;pc=pc+1) begin
 case(pc)
 CASES
 default: i_nin=0;
 endcase
 if(i_nin!=0) begin
 rst_n=1;#1;rst_n=0;#1;
 count=i_nout*((i_nin+63)/64)+256;
 for(n=0;n<count;n=n+1) begin
 clk=0;rst_n=n>=4;go=n==5;#5;
 if(n>=4) begin
 if((^{va_re,vb_re,vc_re,vm_we,red_we})===1'bx) $fatal(1,"unknown enable");
 if(fault) $fatal(1,"native control fault");
 $fdisplay(fd,"%0d,%0d,%0d,%0d,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%0d,%0d",pc,n,ready,idle,va_re,va_addr,vb_re,vb_addr,vc_re,vc_addr,vm_we,vm_addr,red_we,red_addr,progress,progress_rows);
 end
 clk=1;#5;
 end
 if(!idle) $fatal(1,"component not drained pc=%0d",pc);
 end
 end
 $fclose(fd);$display("PASS SU native control capture");$finish;
end
endmodule
'''.replace('DECL',declarations).replace('PORTS',','.join(ports)).replace('CASES',cases).replace('PCMAX',str(len(program)))
 (out/'bench.sv').write_text(bench)
 with (out/'build.log').open('w') as f:subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'sim'),str(out/'control.sv'),str(out/'bench.sv')],stdout=f,stderr=f,check=True)
 p=subprocess.run(['vvp',str(out/'sim')],cwd=out,text=True,capture_output=True);(out/'run.log').write_text(p.stdout+p.stderr);p.check_returncode()
 traces=defaultdict(list)
 for r in csv.DictReader((out/'trace.csv').open()):
  e={'cycle':int(r['cycle']),'reads':{},'writes':[],'reducer':None}
  for x in ('va','vb','vc','vm'):
   mask=int(r[x+'_we' if x=='vm' else x+'_re'],16)
   if not mask:continue
   addr=int(r[x+'_addr'],16);items=[[i,(addr>>(24*i))&0xffffff] for i in range(64) if (mask>>i)&1]
   if x=='vm':e['writes']=items
   else:e['reads'][x]=items
  if int(r['red_we'],16): e['reducer']=int(r['red_addr'],16)
  if e['reads'] or e['writes'] or e['reducer'] is not None: traces[int(r['pc'])].append(e)
 summaries=[]
 for pc,d in static.items():
  ev=traces[pc];nv=(d['su_nin']+63)//64
  expected=lambda x:[[[l,d[x+'_base']+o*d[x+'_so']+(v*64+l)*d[x+'_si']] for l in range(min(64,d['su_nin']-v*64))] for o in range(d['su_nout']) for v in range(nv)]
  for x in 'abc':
   got=[e['reads']['v'+x] for e in ev if 'v'+x in e['reads']]
   assert got==([] if d[x+'_src'] else expected(x)),(pc,x,'read-address/mask mismatch')
  assert [e['writes'] for e in ev if e['writes']]==(expected('d') if d['dst']==1 else []),(pc,'write mismatch')
  assert [e['reducer'] for e in ev if e['reducer'] is not None]==([d['r_base']+o*d['r_so'] for o in range(d['su_nout'])] if d['red'] else []),(pc,'reducer mismatch')
  addresses=[];peaks=dict(read=0,write=0,combined=0);witness={};overlaps=0
  for e in ev:
   sets={k:defaultdict(set) for k in peaks};wm=defaultdict(int)
   for items in e['reads'].values():
    for lane,a in items:
     addresses.append(a);word=a>>4;bank=(word^(word>>7))&127;row=word>>7
     sets['read'][bank].add(row);sets['combined'][bank].add(row)
   for lane,a in e['writes']+([] if e['reducer'] is None else [[64,e['reducer']]]):
    addresses.append(a);word=a>>4;bank=(word^(word>>7))&127;row=word>>7
    sets['write'][bank].add(row);sets['combined'][bank].add(row)
    assert not wm[word]&(1<<(a&15)),(pc,e['cycle'],'duplicate simultaneous scalar writer')
    wm[word]|=1<<(a&15)
   e['word_write_masks']=[[w,m] for w,m in sorted(wm.items())]
   if e['writes'] and e['reducer'] is not None:overlaps+=1
   for k,banks in sets.items():
    for b,rows in banks.items():
     if len(rows)>peaks[k]:peaks[k]=len(rows);witness[k]=dict(cycle=e['cycle'],bank=b,rows=sorted(rows))
  summaries.append(dict(pc=pc,parameters=d,first_event_cycle=ev[0]['cycle'],last_event_cycle=ev[-1]['cycle'],read_lane_requests={x:sum(len(e['reads'].get(x,[])) for e in ev) for x in ('va','vb','vc')},su_scalar_writes=sum(len(e['writes']) for e in ev),reducer_scalar_writes=sum(e['reducer'] is not None for e in ev),su_reducer_write_overlap_cycles=overlaps,min_scalar_address=min(addresses),max_scalar_address=max(addresses),bank_distinct_row_peaks=peaks,witness=witness))
 result=dict(schema='opentallas.qwen-su-native-control.v1',source_sha256=pins,arithmetic_instances_removed=removed,generated_sha256={x:sha((out/x).read_bytes()) for x in ('control.sv','bench.sv')},parameters=dict(SW=64,LV=7,AW=24,NW=18,WR=64),excluded_dynamic_instructions=excluded,summaries=summaries,scope='Each static SU instruction starts from reset, go at cycle5. Independent component PRE-edge cycles, not parent issue calendar. Native vstream/lane/reducer tag, enable and address statements unchanged; arithmetic instance outputs are unobserved and tied zero. No numerical check, no fault-injection/protection proof, no VM arbitration, no ME/MX/other parent writers or inter-op overlap. WR64 is immaterial for these SRC_VM-A static operations; production embedding WR and dynamic ops unbound. All operand native read enables counted even when arithmetic opcode does not consume them. Word=(scalar>>4); bank=(word^(word>>7))&127; row=word>>7. Distinct rows measure raw service obligations; simultaneous read/write same row is not a port guarantee. Reducer pair/pass and valid depend only on valid,last,held_v, not arithmetic values.')
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(out/'events.json').write_text(json.dumps(traces,separators=(',',':'))+'\n')
 print(json.dumps(dict(pcs=list(static),excluded=excluded,events=sum(map(len,traces.values())),maxima={k:max(s['bank_distinct_row_peaks'][k] for s in summaries) for k in ('read','write','combined')})))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',choices=['read_enable','write_address','reducer_address']);a=p.parse_args();run(a.root,a.out,a.mutant)
