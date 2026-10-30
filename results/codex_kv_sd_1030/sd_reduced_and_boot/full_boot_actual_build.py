import re,json
from pathlib import Path
r=Path(__file__).resolve().parent;src=r/'bind_sd_r6w7_reset_reduced/rtl';o=r/'full_boot_actual';o.mkdir(exist_ok=True)
top=(src/'qwen_kvsys_bound_top.sv').read_text()
wanted=set(re.findall(r'^    (\w+)\s+\w+\s*\(',top,re.M));mods=[];native=set();counts={}
for f in src.glob('*.sv'):
 if f.name=='qwen_kvsys_bound_top.sv':continue
 text=f.read_text()
 for m in re.finditer(r'\bmodule\s+(\w+)\s*(?:#\s*\(.*?\)\s*)?\(.*?\bendmodule',text,re.S):
  if not m[1].startswith('kv3_'):continue
  s=m[0];header=s[:s.index(');')+2];body=s[len(header):-len('endmodule')];body=re.sub(r'\(\*.*?\*\)', '',body,flags=re.S);body=re.sub(r'//[^\n]*','',body);body=re.sub(r'/\*.*?\*/','',body,flags=re.S)
  # All declarations and continuous assignments preserve exact source wiring.
  statements=re.findall(r'^\s*(?:(?:\(\*.*?\*\)\s*)?)(?:wire|reg|localparam|parameter|assign)\s+[^;]*;',body,re.M|re.S)
  insts=[]
  for im in re.finditer(r'\bot_dp_\w+\s+(?:#\s*\([^;]*?\)\s*)?\w+\s*\([^;]*?\);',body,re.S):
   cell=im[0];mod=cell.split()[0]
   if not any(k in mod for k in ('landing','rrelay','rsync','rgate','lockq')):continue
   if mod in ('ot_dp_clk_landing_cas','ot_dp_clk_landing_ca'):
    cell=re.sub(r'\.W\(\d+\)', '.W(1)',cell)
    cell=re.sub(r'\.d\([^)]*\)', ".d(1'b0)",cell);cell=re.sub(r'\.q\([^)]*\)', '.q()',cell)
   native.add(mod);insts.append(cell)
  counts[m[1]]=len(insts);mods.append(header+'\n'+'\n'.join(statements+insts)+'\nendmodule')
(o/'controls.sv').write_text('\n'.join(mods));(o/'top.sv').write_text(top)
ca=json.load(open(r/'bindbase/kv40/eW_sidecar_sd_r6w7_reset_reduced.json'))['count_aligned'];reg=ca['regions'];ids={n:'v'+str(i) for i,n in enumerate(reg) if n.startswith('st:')}
pins=re.findall(r'^\s*(input|output)\s+(?:wire\s+)?(?:\[[^\]]+\]\s*)?(\w+)\s*;',top,re.M)
tb=['`timescale 1ps/1ps','module tb;reg clk=0;always begin #416 clk=1;#417 clk=0;end reg rst=0,mission_start=0,refclk=0;always #5000 refclk=~refclk;integer cycle=0,base=0;always @(posedge clk)cycle<=cycle+1;wire ready,fault;']
# Native real partition outputs feed virtual stage start/raw roots.
for n in reg:
 if not n.startswith('st:'):tb+=['wire rs_'+n+',rraw_'+n+';']
for n,v in ids.items():
 e=reg[n];par=e['parent'];ps=(ids[par]+'_start') if par in ids else 'rs_'+par;pr=(ids[par]+'_raw') if par in ids else 'rraw_'+par
 tb+=['wire '+v+'_start,'+v+'_raw;','ot_die_start_reset_relay #(.EDGE_FALL('+str(int(e.get('edge_fall',False)))+')) r_'+v+'(.clk(clk),.d('+pr+'),.q('+v+'_raw));',
 'ot_dp_landing_origin #(.PAD('+str(e.get('pad',0))+'),.EDGE_FALL('+str(int(e.get('edge_fall',False)))+')) s_'+v+'(.clk(clk),.rst_raw_n('+v+'_raw),.p_start('+ps+'),.start('+v+'_start));']
connections=[]
for direction,n in pins:
 if n=='pad_por_n':v='rst'
 elif n=='start':v='mission_start'
 elif n=='pad_refclk':v='refclk'
 elif n.startswith('clk_'):v='clk'
 elif n.startswith('pst_'):
  real=n[4:];par=reg[real]['parent'];v=ids[par]+'_start' if par in ids else 'rs_'+par
 elif n.startswith(('rs_','rraw_')):v=n
 elif n=='clock_landing_ready':v='ready'
 elif n=='clock_landing_fault':v='fault'
 elif direction=='input':v="'0"
 else:v=''
 connections.append('.'+n+'('+v+')')
tb+=['qwen_kvsys_bound_top die('+','.join(connections)+');','assign ready=die.hub_C.cland_up_ready;assign fault=die.hub_C.cland_up_fault;']
for pn in ['sys_SW','sys_SE','io_W2','io_E6']:
 tb+=['always @(posedge die.'+pn+'.cland_start)$display("PART_START '+pn+' %0d",cycle-base);','always @(posedge die.'+pn+'.cland_up_ready)$display("PART_READY '+pn+' %0d",cycle-base);']
tb+=['always @(posedge ready)$display("ROOT_READY %0d fault=%0b",cycle-base,fault);','initial begin repeat(20)@(negedge clk);base=cycle;rst=1;repeat(392)@(negedge clk);$display("OLD392_READY=%0b fault=%0b",ready,fault);repeat(700)@(negedge clk);$display("COLD_FINAL ready=%0b fault=%0b",ready,fault);rst=0;repeat(80)@(negedge clk);base=cycle;rst=1;repeat(392)@(negedge clk);$display("WARM_OLD392_READY=%0b fault=%0b",ready,fault);repeat(700)@(negedge clk);$display("WARM_FINAL ready=%0b fault=%0b",ready,fault);$finish;end endmodule']
reset=['module ot_die_start_reset_relay #(parameter bit EDGE_FALL=0)(input wire clk,d,output wire q);reg r0,r1;wire x;generate if(EDGE_FALL)begin reg rf;always @(negedge clk)rf<=d;assign x=rf;end else assign x=d;endgenerate always @(posedge clk)begin r0<=x;r1<=r0;end assign q=r1;endmodule']
(o/'tb.sv').write_text('\n'.join(tb+reset));(o/'extraction.json').write_text(json.dumps({'modules':counts,'native':sorted(native),'ports':len(pins),'virtual_stages':len(ids),'reduction':'Only functional ring data W reduced1/d0/qopen. Nativecounttag/status/control/reset/START/collector graph exact. Timing/commonclock diagnostic.'},indent=1))
print(json.dumps({'modules':len(mods),'native':sorted(native),'pins':len(pins),'virtual':len(ids)},indent=1))
