#!/usr/bin/env python3
"""Make full-port, full-production-shape reset/program/recovery equivalence bench."""
import re,sys
from pathlib import Path
base,top,out=sys.argv[1:];s=Path(base).read_text();ports=[]
for d,w,n in re.findall(r'^  (input|output)\s+(\[[^]]+\]\s*)?(\w+);',s,re.M):ports.append((d,w,n))
a=['`timescale 1ns/1ps','module tb;','reg ck=0; always #5 ck=~ck;','integer cyc=0; integer checks=0; integer tx=0; integer aborted=0; reg [19:0] slot_delay=0;']
for d,w,n in ports:
 if n=='ck':continue
 a.append(('reg ' if d=='input' else 'wire ')+w+n+('=0;' if d=='input' else ';'))
 if d=='output':a.append('wire '+w+'ref_'+n+';')
a+= [top+' ref_dut('+','.join('.'+n+'('+('ref_' if d=='output' else '')+n+')' for d,w,n in ports)+');',top+'_reset24 dut('+','.join('.'+n+'('+n+')' for d,w,n in ports)+');']
outs=[n for d,w,n in ports if d=='output'];inputs=[n for d,w,n in ports if d=='input' and n not in ('ck','por_n','rst_n')]
a+=['task check; begin','if ({'+','.join(outs)+'} !== {'+','.join('ref_'+n for n in outs)+'}) begin $display("MISMATCH cycle %0d",cyc); $fatal(1); end','checks=checks+1; if(fdi_tx_v)tx=tx+1;if(epoch_abort)aborted=aborted+1;','end endtask','initial begin','por_n=0;rst_n=0;','for(cyc=0;cyc<6000;cyc=cyc+1) begin','@(negedge ck);']
for d,w,n in ports:
 if n not in inputs:continue
 width=(int(w.split(':')[0][1:])+1) if w else 1
 a.append(n+' = '+('{'+','.join('$random' for _ in range((width+31)//32)))+'};')
a+=['por_n=(cyc>=16 && !(cyc>=3000 && cyc<3020));','rst_n=(cyc>=16 && !(cyc>=1200 && cyc<1220) && !(cyc>=3000 && cyc<3020) && !(cyc>=4500 && cyc<4520));','if(cyc<200 || (cyc>=3100 && cyc<3300)) begin','cfg_tx_we=cyc%2;cfg_rx_we=!(cyc%2);cfg_addr=(cyc/2)%32;cfg_data={(cyc%2 ? 14\'d40 : 14\'d200),1\'b1,3\'d0,4\'d3,5\'d0,5\'d31};','cal_start=0;host_boot_begin=0;host_link_reset_req=0;host_recovery_clear=0;att_tx_v=0;emb_tx_v=0;record_tx_observed_v=0;fdi_rx_v=0;fdi_tx_up=1;end','if(cyc>=200 && cyc<1000) begin','cfg_tx_we=0;cfg_rx_we=0;cal_start=(cyc==260);cal_seg=0;host_boot_begin=(cyc==210);host_link_reset_req=0;host_recovery_clear=0;record_tx_observed_v=0;emb_tx_v=0;fdi_rx_v=0;fdi_tx_up=1;','att_tx_v=slot_delay[19];slot_delay={slot_delay[18:0],att_tx_slot};att_tx_payload={17{32\'h12345678}};','cal_start_rx=(cyc==260);cal_seg_rx=0;cal_user_tx=0;cal_user_rx=0;' if 'cal_start_rx' in [n for d,w,n in ports] else '','end','if(cyc<200) begin '+('cal_start_rx=0;cal_seg_rx=0;cal_user_tx=0;cal_user_rx=0;' if 'cal_start_rx' in [n for d,w,n in ports] else '')+'end','@(posedge ck); #1; if(cyc>=8)check();','end','if(tx<32)$fatal(1,"insufficient production TX activity %0d",tx);','$display("PASS checks=%0d tx=%0d aborted=%0d",checks,tx,aborted);$finish;end','endmodule']
Path(out).write_text('\n'.join(a)+'\n')
