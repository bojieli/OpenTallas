import json
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-kv-hr-2249/cdcpc')
cj=json.load(open('/srv/opentallas-scratch2/claude/kv-host-regen-1/rtl/qkd_hr_cdc_pc/qkd_hr_cdc_pc_core.json'))
d=cj['port_decl'];L=['`timescale 1ns/1ps','module tb;','reg ck=0;always #1 ck=~ck;','integer cyc=0,cmp=0,mut_diffs=0,rx_words=0,tx_words=0;','integer crx=4,ctx=4;','reg[3:0] ret_rx=0,ret_tx=0;']
for n,(dr,hi,lo) in d.items():
 if n=='ck':continue
 w=hi-lo+1
 if dr=='input':L.append(f'reg [{w-1}:0] {n}=0;')
 else:
  for pref in ('gold','dut','mut'):
   pw=528 if pref!='gold' and n=='u_tx__o_d' else w
   L.append(f'wire [{pw-1}:0] {pref}_{n};')
for pref,mod in [('gold','qkd_hr_cdc_pc'),('dut','qkd_hr_cdc_pc_projected'),('mut','qkd_hr_cdc_pc_mutant')]:
 con=['.ck(ck)']
 for n,(dr,*_) in d.items():
  if n=='ck':continue
  con.append('.'+n+'('+(n if dr=='input' else pref+'_'+n)+')')
 L.append(mod+' '+pref+'('+',\n'.join(con)+');')
for stream in ('rx','tx'):
 L.append(f'always @(posedge ck) ret_{stream} <= {{ret_{stream}[2:0],gold_u_{stream}__o_v}};')
L+=['always @(negedge ck)begin','cyc=cyc+1;',"if(cyc==20)begin u_rx__rrst_n=1;u_rx__wrst_n=1;u_tx__rrst_n=1;u_tx__wrst_n=1;end",'if(cyc>35)begin','cmp=cmp+1;']
for n,(dr,*_) in d.items():
 if dr!='output':continue
 g='gold_'+n+('[527:0]' if n=='u_tx__o_d' else '')
 L.append('if('+g+'!==dut_'+n+')$fatal(1,"projection '+n+' cyc%0d",cyc);')
L += ['if(gold_u_tx__o_v)begin tx_words=tx_words+1;if(gold_u_tx__o_d[545:528]!==18\'b0)$fatal(1,"reserved nonzero cyc%0d",cyc);if(gold_u_tx__o_d[527:0]!==mut_u_tx__o_d)mut_diffs=mut_diffs+1;end','if(gold_u_rx__o_v)rx_words=rx_words+1;', 'if(gold_u_rx__w_fault||gold_u_rx__r_fault||gold_u_tx__w_fault||gold_u_tx__r_fault)$fatal(1,"illegal trace fault cyc%0d",cyc);','end']
L+=['if(cyc>40)begin','crx=crx+gold_u_rx__i_cr;ctx=ctx+gold_u_tx__i_cr;',"u_rx__i_v=(crx>0&&cyc<1500&&(cyc%5!=0));u_tx__i_v=(ctx>0&&cyc<1500&&(cyc%7!=0));",'if(u_rx__i_v)crx=crx-1;if(u_tx__i_v)ctx=ctx-1;',"u_rx__i_d={17{32'(cyc*137+329)}};u_tx__i_d={17{32'(cyc*181+437)}};",'u_rx__o_cr=ret_rx[1];u_tx__o_cr=ret_tx[1];','end']
L+=['if(cyc==1800)begin','if(rx_words<50||tx_words<50||mut_diffs<50)$fatal(1,"weak coupon rx%0d tx%0d mut%0d",rx_words,tx_words,mut_diffs);','$display("CDCPC_PROJECTION_PASS cmp=%0d rx_words=%0d tx_words=%0d reserved18_valid_zero=%0d mutant_valid_diffs=%0d added_cycles=0",cmp,rx_words,tx_words,tx_words,mut_diffs);$finish;','end','end','endmodule']
(r/'tb.sv').write_text('\n'.join(L)+'\n')
