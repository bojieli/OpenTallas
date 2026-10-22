#!/usr/bin/env python3
"""Extend the exact minimal LOAD caller with actual K-share window producers.

HBM controllers are boundary models using true fixture bytes. KRL1 response
handshakes and asynchronous stream/HBM clocks remain real source obligations.
"""
import json,runpy,sys
from pathlib import Path
vectors=Path(sys.argv[1]);out=Path(sys.argv[2]);age=sys.argv[3]
runpy.run_path(str(Path(__file__).with_name('emit_dma_integrated_1021.py')),run_name='__main__')
s=out.read_text();v=json.loads(vectors.read_text())
s=s.replace('reg [31:0] fv=0;reg [16*12-1:0] fs=0;reg [16*512-1:0] fd=0;','wire [31:0] fv,fbanks;wire [511:0] fepochs;wire [16*12-1:0] fs;wire [16*512-1:0] fd;\n reg hbm_clk=0;always #0.7 hbm_clk=~hbm_clk;reg [29:0] rows=0;reg[7:0] cols=0;reg[255:0] hbm_words[0:2047];wire[7:0] producer_fault;\n for(genvar sm=0;sm<8;sm=sm+1)begin:KP\n dma_boundary_model #(.SM(sm)) producer(.hbm_clk(hbm_clk),.clk(clk),.rst_n(rst),.vm_v(begin_v[sm/4]),.vm_epoch(epoch[(sm/4)*16+:16]),.vm_row(rows[(sm/4)*15+:15]),.vm_col(cols[(sm/4)*4+:4]),.fault(producer_fault[sm]));\n for(genvar l=0;l<4;l=l+1)begin:F\n localparam Q=sm/4,PC=sm*4+l,LANE=l+4*((PC>>2)&1),GROUP=(PC>>3)&1,I=Q*8+LANE;\n assign fv[I*2+GROUP]=producer.fill_v[l];assign fbanks[I*2+GROUP]=producer.fill_bank[l];assign fepochs[I*32+GROUP*16+:16]=producer.fill_epoch[l*16+:16];assign fs[I*12+GROUP*6+:6]=producer.fill_slot[l*6+:6];assign fd[I*512+GROUP*256+:256]=producer.fill_data[l*256+:256];\n end end')
s=s.replace('.fill_bank_i(2\'b0)', '.fill_bank_i(fbanks[I*2+:2])').replace('.fill_epoch_i({2{epoch[q*16+:16]}})', '.fill_epoch_i(fepochs[I*32+:32])')
s=s.replace('if((|srcfault)||' ,'if((|producer_fault))$fatal(1,"WINDOW_PRODUCER_FAULT");\n if((|srcfault)||')
# Replace the manual landing-fill stimulus with the actual vmks command and
# a bounded wait for every landing lane's real full indication.
for w in v['windows']:
 q=w['sourceq'];needle=f" epoch[{q*16}+:16]=16'd{w['epoch']};begin_v=2'd{1<<q};"
 s=s.replace(needle,f" rows[{q*15}+:15]=15'd{w['row']};cols[{q*4}+:4]=4'd{w['col']};"+needle)
 start=s.index(' fv[',s.index(needle))
 end=s.index(' for(integer b=0;b<8;b=b+1)if(!ready',start)
 s=s[:start]+f' begin integer wait_cycles;wait_cycles=0;while((full0[{q*8}+:8]!==8\'hff)&&wait_cycles<2000)begin @(negedge clk);wait_cycles=wait_cycles+1;end if(wait_cycles==2000)$fatal(1,"PRODUCER_TIMEOUT q{q}");end\n repeat(12)@(negedge clk);\n'+s[end:]
init=''
for w in v['windows']:
 for f in w['fills']:
  index=w['sourceq']*1024+f['lane']*128+f['group']*64+f['slot'];init+=f" hbm_words[{index}]=256'h{f['data']};\n"
s=s.replace('mutate_bank=$test$plusargs("MUTATE_BANK");',init+' mutate_bank=$test$plusargs("MUTATE_BANK");')
s=s.replace('DMA_INTEGRATED_PASS','DMA_PRODUCER_INTEGRATED_PASS')
s+='''
module dma_boundary_model #(parameter SM=0)(input hbm_clk,clk,rst_n,vm_v,input[15:0]vm_epoch,input[14:0]vm_row,input[3:0]vm_col,output fault);
 wire[3:0]kv,krdy;wire[119:0]ka;wire[15:0]kl;wire[67:0]kt;wire[3:0]kw;
 wire mutate_source=$test$plusargs("MUTATE_HBM");reg[3:0] rv=0;reg[67:0]rt=0;reg[15:0]rb=0;reg[1023:0]rd=0;reg[3:0]seen=0;
 wire[3:0]fill_v,fill_bank;wire[23:0]fill_slot;wire[63:0]fill_epoch;wire[1023:0]fill_data;
 ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0),.KRL1(1)) svc(.hbm_clk(hbm_clk),.hbm_rst_n(rst_n),.stream_clk(clk),.stream_rst_n(rst_n),.sm_stream(3'(SM)),.sm_hbm(3'(SM)),
 .g_k_v(4'd0),.g_k_rdy(),.g_k_addr(120'd0),.g_k_len(16'd0),.g_k_tag(68'd0),.g_k_we(4'd0),.g_k_wdata(1024'd0),.g_k_wstrb(128'd0),.g_k_wr_done(),.g_kr_v(),.g_kr_rdy(4'hf),.g_kr_tag(),.g_kr_beat(),.g_kr_data(),
 .c_k_v(kv),.c_k_rdy(4'hf),.c_k_addr(ka),.c_k_len(kl),.c_k_tag(kt),.c_k_we(kw),.c_k_wdata(),.c_k_wstrb(),.c_k_wr_done(4'd0),.c_kr_v(rv),.c_kr_rdy(krdy),.c_kr_tag(rt),.c_kr_beat(rb),.c_kr_data(rd),
 .vm_v(vm_v),.vm_bank(1'b0),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),.wbw_v(1'b0),.wbw_base(30'd0),.wbw_total(12'd0),.w_k_v(4'd0),.w_k_rdy(),.w_k_addr(120'd0),.w_k_wdata(1024'd0),.w_k_wr_done(),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.fault(fault));
 reg[29:0]qa[0:3][0:31];reg[16:0]qt[0:3][0:31];integer head[0:3],tail[0:3],beat[0:3];
 initial for(integer l=0;l<4;l=l+1)begin head[l]=0;tail[l]=0;beat[l]=0;end
 always @(posedge hbm_clk)begin
 seen<=rst_n?krdy:0;
 if(rst_n)for(integer l=0;l<4;l=l+1)begin
 if(rv[l]&&seen[l])begin rv[l]<=0;if(beat[l]==3)begin head[l]=head[l]+1;beat[l]=0;end else beat[l]=beat[l]+1;end
 if(kv[l])begin
 if(ka[l*30+15+:15]!=vm_row||ka[l*30+8+:4]!=vm_col||kw[l]||kl[l*4+:4]!=4||(ka[l*30+:30]&3)!=0||((ka[l*30+2+:5]^ka[l*30+7+:5]^ka[l*30+12+:5])!=5'(SM*4+l)))$fatal(1,"ILLEGAL_WINDOW_K sm%0d lane%0d",SM,l);
 qa[l][tail[l]%32]=ka[l*30+:30];qt[l][tail[l]%32]=kt[l*17+:17];tail[l]=tail[l]+1;
 end
 if((!rv[l]||seen[l])&&head[l]<tail[l])begin
 integer pc,lane,group,slot,index;reg[29:0]a;
 a=qa[l][head[l]%32]+30'(beat[l]);pc=SM*4+l;lane=l+4*((pc>>2)&1);group=(pc>>3)&1;slot=(((a>>7)&1)<<5)|(((a>>12)&7)<<2)|(a&3);index=(SM/4)*1024+lane*128+group*64+slot;
 rv[l]<=1;rt[l*17+:17]<=qt[l][head[l]%32];rb[l*4+:4]<=4'(beat[l]);rd[l*256+:256]<=tb_dma_integrated.hbm_words[index]^(mutate_source?{32{8'h01}}:256'd0);
 end
 end
 end
endmodule
'''
out.write_text(s)
