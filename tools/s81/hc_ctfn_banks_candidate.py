#!/usr/bin/env python3
"""Held 4-root straight CTFN component: same data stages and x pins, +1 init reset edge only."""
import hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
C='b875feb3a';P='physical/s81_die_pins/v25_hc_norm_fs_yshift_candidate/ot_s81_hc_ctfn_nt.tcl'
def main():
 raw=subprocess.check_output(['git','show',f'{C}:{P}']).decode();pins={}
 for l in raw.splitlines():
  m=re.search(r'-pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}',l)
  if m:pins[m[1]]=(m[2],float(m[3]),float(m[4]))
 bounds=[0,144.288,288.576,432.864,576.72];groups=[]
 for j in range(4):
  ids=[i for i in range(2920) if bounds[j]<=pins[f'fd_in[{i}]'][1]<bounds[j+1]];vs=[i for i in range(7) if bounds[j]<=pins[f'fv_in[{i}]'][1]<bounds[j+1]]
  assert all(bounds[j]<=pins[f'fdm[{i}]'][1]<bounds[j+1] for i in ids)
  assert all(bounds[j]<=pins[f'fvm[{i}]'][1]<bounds[j+1] for i in vs)
  groups.append(dict(bank=j,x=bounds[j],w=round(bounds[j+1]-bounds[j],3),h=25.92,y=8.64,fd_bits=ids,fv_bits=vs))
 assert sum(len(g['fd_bits']) for g in groups)==2920 and sum(len(g['fv_bits']) for g in groups)==7
 new=R/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctfn_banks_candidate.sv';s=['// HELD COMPONENT ONLY. Logical data/valid latency stays2; local reset release has+1INITedge.','// Parent is wires-only, five real independent clock entries; no native view inheritance.','module ot_s81_hc_ctfn_banks_candidate(input wire [4:0] ck,input wire rst_in,input wire [6:0] fv_in,input wire [2919:0] fd_in,output wire rst_c,output wire [6:0] fvm,output wire [2919:0] fdm);','wire valid_reset;','ot_s81_hc_ctfnq_reset u_reset(.clk(ck[4]),.rst_in(rst_in),.rst_c(rst_c),.valid_reset(valid_reset));']
 def bus(n,bits):return '{'+','.join(f'{n}[{i}]' for i in reversed(bits))+'}'
 for g in groups:
  j=g['bank'];args=[f'.clk(ck[{j}])',f'.fd_in({bus("fd_in",g["fd_bits"])})',f'.fdm({bus("fdm",g["fd_bits"])})']
  if g['fv_bits']:args += ['.rst_in(valid_reset)',f'.fv_in({bus("fv_in",g["fv_bits"])})',f'.fvm({bus("fvm",g["fv_bits"])})']
  s += [f'ot_s81_hc_ctfnq{j} u_q{j}('+','.join(args)+');']
 s+=['endmodule','module ot_s81_hc_ctfnq_reset(input wire clk,input wire rst_in,output wire rst_c,output wire valid_reset);','reg [1:0] rr; always @(posedge clk) rr <= {rr[0],rst_in};','assign rst_c=rr[0];assign valid_reset=rr[1];','endmodule']
 pinroot=R/'physical/s81_die_pins/ctfn_banks_candidate_1015';pinroot.mkdir(parents=True,exist_ok=True)
 def writepins(cell,pp):
  text='\n'.join(f'place_pin -pin_name {{{n}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary' for n,ly,x,y in pp)+'\n';(pinroot/f'{cell}.tcl').write_text(text);return hashlib.sha256(text.encode()).hexdigest()
 for g in groups:
  j=g['bank'];N=len(g['fd_bits']);V=len(g['fv_bits']);cell=f'ot_s81_hc_ctfnq{j}'
  ps=[f'input wire clk',f'input wire [{N-1}:0] fd_in',f'output reg [{N-1}:0] fdm']
  if V:ps += ['input wire rst_in',f'input wire [{V-1}:0] fv_in',f'output reg [{V-1}:0] fvm']
  s += [f'module {cell}('+','.join(ps)+');',f'reg [{N-1}:0] fd;','always @(posedge clk) begin fd <= fd_in; fdm <= fd; end']
  if V:s += ['reg rr;always @(posedge clk) rr <= rst_in;',f'reg [{V-1}:0] fv;','always @(posedge clk or negedge rr) if(!rr) begin fv<=0;fvm<=0;end else begin fv<=fv_in;fvm<=fv;end']
  s += ['endmodule']
  pp=[]
  for pref,glob,bits in [('fd_in','fd_in',g['fd_bits']),('fdm','fdm',g['fd_bits']),('fv_in','fv_in',g['fv_bits']),('fvm','fvm',g['fv_bits'])]:
   for rank,i in enumerate(bits):
    ly,x,y=pins[f'{glob}[{i}]'];pp.append((f'{pref}[{rank}]',ly,round(x-g['x'],3),y))
  cx=round(.012+.048*round((g['w']/2-.012)/.048),3);pp += [('clk','M3',cx,25.878)]
  if V:
   rx=round(.012+.048*round((cx+.144-.012)/.048),3);pp += [('rst_in','M3',rx,25.878)]
  g['clock_local_x']=cx;g['cell']=cell;g['pins_sha256']=writepins(cell,pp);g['max_clock_sinks_logical']=2*N+2*V+bool(V)
 # Tiny reset leaf above the four data banks, all wires in the parent.
 reset=dict(cell='ot_s81_hc_ctfnq_reset',x=280.8,y=0,w=16.416,h=8.64)
 pp=[('clk','M3',7.26,8.598),('rst_in','M3',5.34,8.598),('rst_c','M5',5.484,.042),('valid_reset','M5',7.548,.042)];reset['pins_sha256']=writepins(reset['cell'],pp)
 parentpp=[]
 for n,(ly,x,y) in pins.items():
  if n=='clk':continue
  parentpp.append((n,ly,x,round(y+8.64,3) if y>20 else y))
 for g in groups:parentpp.append((f'ck[{g["bank"]}]','M3',round(g['x']+g['clock_local_x'],3),34.518))
 parentpp.append(('ck[4]','M3',288.06,34.518))
 parentsha=writepins('ot_s81_hc_ctfn_banks_candidate',parentpp)
 new.write_text('\n'.join(s)+'\n')
 old=subprocess.check_output(['git','show',f'{C}:rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv']).decode();old=old[old.index('module ot_s81_hc_ctfn_nt #'):];old=old[:old.index('endmodule')+len('endmodule')];ref=R/'tools/s81_suhc/ctfn_banks_candidate';ref.mkdir(exist_ok=True);(ref/'reference.sv').write_text(old.replace('ot_s81_hc_ctfn_nt','ot_s81_hc_ctfn_nt_reference',1)+'\n')
 d=dict(status='HELD_COMPONENT_STUDY',outline_um=[576.72,34.56],parent_pins_sha256=parentsha,source_pins=dict(commit=C,path=P,sha256=hashlib.sha256(raw.encode()).hexdigest()),source_reference=dict(commit=C,module='ot_s81_hc_ctfn_nt',sha256=hashlib.sha256(old.encode()).hexdigest()),data_stages=2,extra_normal_edges=0,extra_init_edges=1,init_contract='FV must be zero throughout reset and for4edges after rst_in rises; arbitrary FD always passes2edges',added_logical_ff=1,clock_entries=5,groups=groups,reset_leaf=reset,open=['Exact component positive and clock mutants','Actual CTS/native/TT/FF/DRC0 per bank','No parent source/view/physical inheritance','New 5clock ABI and+8.64umFN row/grant, full static schedule and reset init binding','Re-screen40bad FS->FN hops with actual new native arcs'])
 (pinroot/'layout.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps([(g['bank'],len(g['fd_bits']),len(g['fv_bits']),g['w'],g['max_clock_sinks_logical']) for g in groups]))
if __name__=='__main__':main()
