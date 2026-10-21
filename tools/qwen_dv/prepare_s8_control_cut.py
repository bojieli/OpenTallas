#!/usr/bin/env python3
"""Freeze exact old/new production-module cut and source-bound reset dependencies."""
import hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'rtl/test/qwen_dv/s8/control_cut';O.mkdir(parents=True,exist_ok=True)
bound={}
def get(p,ref=None):
 s=subprocess.check_output(['git','-C',str(R),'show',ref+':'+p],text=True) if ref else (R/p).read_text()
 bound[(ref+':' if ref else '')+p]=hashlib.sha256(s.encode()).hexdigest();return s
for name in ['rp1','fdn_arf1']:
 p=f'rtl/qwen_dv/s5/s8/qfd_dv_s8_{name}.sv';s=get(p,'363295685')
 s=s.replace('module qfd_dv_s8_'+name,'module qfd_dv_s8_'+name+'_reference',1)
 (O/f'{name}_reference.sv').write_text(s)
# Small exact production reset modules, no guessed replacement reset model.
def module(s,n):
 a=s.index('module '+n+' ');return s[a:s.index('endmodule',a)+9]
s=get('rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv');a=module(s,'qfd_dv_s6_rst2x4')+'\n'+module(s,'qfd_dv_s6_rk')
s=get('rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv','HEAD');b=module(s,'qfd_dv_s5_rst2')
(O/'reset_dependencies.sv').write_text('`timescale 1ns/1ps\n'+a+'\n'+b+'\n')
p='rtl/qwen_dv/s5/s8/lp/qfd_dv_s8_lp.sv';s=get(p)
helpers='\n\n'.join(module(s,'qfd_dv_s8_lp_flags_mask_'+n) for n in ['local_w','gate'])
(O/'masked_production_helpers.sv').write_text('`timescale 1ns/1ps\n'+helpers+'\n')
# Header-derived pin-complete RP/FDN harness avoids an inferred interface.
lines=['`timescale 1ns/1ps','module s8_guard_cut(input ck,rst,output reg done=0);','integer cycle=0,checks=0,unknown_checks=0;integer mutant=0;','initial if($value$plusargs("mutant=%d",mutant))begin end']
ports={}
for short,name in [('r','rp1'),('f','fdn_arf1')]:
 s=get(f'rtl/qwen_dv/s5/s8/qfd_dv_s8_{name}.sv')
 hdr=re.search(r'module\s+\w+(?:\s*#\([^;]+?\))?\s*\((.*?)\);',s,re.S)[1]
 direction=width=None;ps=[]
 for part in hdr.split(','):
  part=part.strip();m=re.fullmatch(r'(input|output)\s+(?:wire\s*|reg\s*)?(\[[^]]+\])?\s*(\w+)',part)
  if m:direction,width,n=m.groups();width=width or ''
  else:n=part;assert re.fullmatch(r'\w+',n),part
  ps.append((direction,width,n))
 ports[short]=ps
 for d,w,n in ps:
  if n in ['ck','rst_n']:continue
  if d=='input':lines.append(f'reg {w} {short}_{n};')
  else:lines.append(f'wire {w} {short}_old_{n},{short}_new_{n};')
 for old in [True,False]:
  con=[]
  for d,w,n in ps:
   v='ck' if n=='ck' else 'rst' if n=='rst_n' else f'{short}_{n}' if d=='input' else f'{short}_{"old" if old else "new"}_{n}'
   con.append(f'.{n}({v})')
  mod='qfd_dv_s8_'+name+('_reference' if old else '')
  param=' #(.USE_SEL_COPIES(1))' if short=='f' else ''
  lines.append(f'{mod}{param} {short}_{"old" if old else "new"}('+','.join(con)+');')
lines+=['always @(negedge ck)begin','cycle=cycle+1;']
for short,ps in ports.items():
 for d,w,n in ps:
  if d!='input' or n in ['ck','rst_n']:continue
  size=int(re.search(r'\[(\d+):0\]',w)[1])+1 if w else 1
  lines.append(f'for(integer b=0;b<{size};b=b+1){short}_{n}[b]=$random;') if w else lines.append(f'{short}_{n}=$random;')
lines+=['''r_cmd_q=0;f_cmd_i=0;r_chd_q[519:518]=0;
if(cycle%32==10)begin
 r_cmd_q[0]=1;r_cmd_q[3:1]=7;r_cmd_q[7:4]=3;
 f_cmd_i[0]=1;f_cmd_i[3:1]=7;f_cmd_i[7:4]=3;
end
if(cycle%32==12)begin
 r_cmd_q[0]=1;r_cmd_q[115:112]=15;r_cmd_q[5:4]=1;r_cmd_q[15:6]=16;
 f_cmd_i[0]=1;f_cmd_i[115:112]=15;f_cmd_i[5:4]=0;f_cmd_i[22:7]=4;f_cmd_i[54:23]=32'h11223344;
end
if(cycle%32>=14 && cycle%32<=21)begin
 r_chd_q[519:518]=3;r_chd_q[514:512]=3'(cycle%32-14);
 if(cycle%32==17)r_chd_q[519]=1'bx;
 if(cycle%32==18)r_chd_q[518]=1'bz;
 r_chd_q[31:0]=(cycle%2)?32'bz:32'bx;
 f_chu_q[1094]=1;
end
f_chu_ar_sel={46{f_chu_q[1094]}};f_chu_dd_sel={46{f_chu_q[547]}};
if(cycle%32==24)begin f_chu_ar_sel=46'bx;f_chu_dd_sel=46'bz;end
if(cycle%32==25)begin f_chu_q[1094]=1'bx;f_chu_q[547]=1'bz;end
end
always @(posedge ck)begin #1;''']
for short,ps in ports.items():
 for d,w,n in ps:
  if d=='output':lines.append(f'if({short}_old_{n}!=={short}_new_{n})$fatal(1,"GUARD_EQ_MISMATCH {short}.{n} cycle%0d",cycle);')
for sh,names in [('r',['sid_q','sid_ok','rp_arm','rp_base','rp_k']),('f',['arf_sid','arf_sid_ok','arf_arm','arf_tag','arf_wm1','arf_cnt','pq'])]:
 for n in names:lines.append(f'if({sh}_old.{n}!=={sh}_new.{n})$fatal(1,"GUARD_STATE_MISMATCH {sh}.{n} cycle%0d",cycle);')
lines+=['checks=checks+1;if((^r_new_vtw_data)===1\'bx)unknown_checks=unknown_checks+1;', 'if(cycle==255)begin if(checks<250||unknown_checks<4)$fatal(1,"GUARD_COVERAGE");$display("GUARD_EQ_PASS cycles%0d unknown_outputs%0d all_ports_all_state startup_reset_XZ",checks,unknown_checks);done=1;end','end','endmodule']
(O/'guard_cut.sv').write_text('\n'.join(lines)+'\n')
(O/'SOURCE_MANIFEST.json').write_text(json.dumps(bound,indent=2)+'\n')
