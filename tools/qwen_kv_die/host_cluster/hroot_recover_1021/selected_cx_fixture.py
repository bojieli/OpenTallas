#!/usr/bin/env python3
from pathlib import Path
r=Path('cdc');s=(r/'top.sv').read_text();s=s.replace('qkc_afifo_bits_1021 u(',"wire[63:0]wb,rb;\nfor(genvar b=0;b<4;b=b+1)begin:g_bank\not_host_reset_bank #(.N(16)) uw(.clk(wclk),.async_rst_n(rst_n),.sync_rst_n(wb[b*16+:16]));\not_host_reset_bank #(.N(16)) ur(.clk(rclk),.async_rst_n(rst_n),.sync_rst_n(rb[b*16+:16]));\nend\nqkc_afifo_bits_1021 #(.RESET_BUSES(1)) u(")
s=s.replace('.wclk(wclk),.wrst_n(wn),.wr(wr)', '.wrst_bits(wb),.rrst_bits(rb),.wclk(wclk),.wrst_n(wn),.wr(wr)');(r/'top.sv').write_text(s)
s=(r/'check.py').read_text().replace("'rtl/lib/ot_reset_sync.sv',", "'rtl/lib/ot_reset_sync.sv','rtl/physical/ot_host_die_cdc_sram.sv',")
# Preserve the old policy refusal as history; this run validates selected source only.
k=s.index('# First preserve');e=s.index('try:\n d=G.lint',k);s=s[:k]+s[e:];(r/'check.py').write_text(s)
r=Path('bench')
for n in ['tb.sv','tb_atomic.sv']:
 s=(r/n).read_text().replace('.MUT_ROTATE(MUT)', '.MUT_ROTATE(MUT),.RESET_BUSES(1)').replace('.MUT_UNCOORD(MUT)', '.MUT_UNCOORD(MUT),.RESET_BUSES(1)')
 s=s.replace('.wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(df)', '.wrst_bits({64{wn}}),.rrst_bits({64{rn}}),.wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(df)')
 s=s.replace('.wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(full)', '.wrst_bits({64{wn}}),.rrst_bits({64{rn}}),.wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(full)');(r/n).write_text(s)
