`timescale 1ns/1ps
// Source-sized L20 index backing, separate from the 0x490000 KV store.
// Original ring writer/read arbiter and all 128 native B pseudo-channels.
module DsromS81IndexHbm #(parameter MEM_WORDS=139520, CLK_PS=833)(
 input wire clk,rst_n,
 input wire[127:0] r_v, output wire[127:0] r_rdy,
 input wire[3839:0] r_addr, input wire[511:0] r_len,
 input wire[2047:0] r_tag,
 output wire[127:0] r_rsp_v,input wire[127:0] r_rsp_rdy,
 output wire[2047:0] r_rsp_tag,output wire[511:0] r_rsp_beat,
 output wire[32767:0] r_rsp_data,
 input wire w_v,output wire w_rdy,input wire[29:0] w_csec,w_ssec,
 input wire[511:0] w_codes,input wire[2:0] w_sslot,input wire[31:0] w_scales,
 output wire busy, output wire fault,
 output reg history_ready=0,output wire[31:0] capacity_words,
 output wire[31:0] dbg_records,dbg_writes,dbg_fifo_highwater,dbg_read_stalls,dbg_writer_stalls,
 output wire[47:0] dbg_migrations,dbg_copied_sectors,
 // Actual backend edges: include migration traffic; caller separates tag bit12.
 output wire[127:0] accepted,accepted_we,returned,committed,
 output wire[511:0] accepted_len,output wire[2047:0] accepted_tag,
 output wire[4095:0] accepted_strb
);
 assign capacity_words=MEM_WORDS;
 reg admitted=0,range_fault=0;
 wire ring_fault,writer_ready;
 wire[127:0] reader_ready;
 assign w_rdy=writer_ready&&history_ready&&!fault;
 assign r_rdy=reader_ready&{128{history_ready&&!fault}};
 assign fault=range_fault|ring_fault;
 wire[127:0] bv,br,bwe,bd,rv,rr,range_ok;
 wire[3839:0] ba;wire[511:0] bl;
 wire[2047:0] bt,rt;
 wire[32767:0] bw,rd;wire[4095:0] bs;
 wire[511:0] rb;
 assign accepted=bv&br;assign accepted_we=bwe;assign accepted_len=bl;
 assign accepted_tag=bt;assign accepted_strb=bs;
 assign returned=rv&rr;assign committed=bd;
 assign r_rsp_tag=rt;assign r_rsp_beat=rb;assign r_rsp_data=rd;
 ot_hdc_v41x_idx_ring_port #(.NPC(32),.AW(30),.TAGW(16),.RSB(64),.RTAIL(32),
 .RFQ(4),.READ_FENCE(1),.WIDE_REC(1)) u_ring(
 .clk(clk),.rst_n(rst_n),.w_v(w_v&&history_ready&&!fault),.w_rdy(writer_ready),
 .w_csec(w_csec),.w_codes(w_codes),.w_ssec(w_ssec),.w_sslot(w_sslot),.w_scales(w_scales),
 .d_v(1'b0),.d_base(23'b0),.d_n(33'b0),.d_key(544'b0),
 .r_v(r_v&{128{history_ready&&!fault}}),.r_rdy(reader_ready),.r_addr(r_addr),.r_len(r_len),.r_tag(r_tag),
 .r_rsp_v(r_rsp_v),.r_rsp_rdy(r_rsp_rdy),
 .h_v(bv),.h_rdy(br),.h_addr(ba),.h_len(bl),.h_tag(bt),.h_we(bwe),.h_wdata(bw),.h_wstrb(bs),
 .h_wr_done(bd),.h_rsp_v(rv),.h_rsp_rdy(rr),.h_rsp_tag(rt),.h_rsp_data(rd),
 .busy(busy),.fault(ring_fault),.dbg_records(dbg_records),.dbg_writes(dbg_writes),
 .dbg_fifo_highwater(dbg_fifo_highwater),.dbg_read_stalls(dbg_read_stalls),
 .dbg_writer_stalls(dbg_writer_stalls),.dbg_migrations(dbg_migrations),.dbg_copied_sectors(dbg_copied_sectors));
 generate for(genvar pc=0;pc<128;pc=pc+1)begin:g_guard
 assign range_ok[pc]=bl[pc*4+:4]!=0 &&
 (64'(ba[pc*30+:30])+64'(bl[pc*4+:4])<=MEM_WORDS);
 end endgenerate
 generate for(genvar st=0;st<4;st=st+1)begin:g_s
 wire[31:0] hv,hr,hwe,hd,mv,mr,ar;
 assign br[st*32+:32]=ar&range_ok[st*32+:32]&{32{!fault}};
 wire[959:0] ha,done_addr;wire[127:0] hl,mb;
 wire[543:0] ht,mt,done_tag;
 wire[8191:0] hw,md;wire[1023:0] hs;
 ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16)) u_arb(
 .clk(clk),.rst_n(rst_n),
 .b_v(bv[st*32+:32]&range_ok[st*32+:32]&{32{!fault}}),
 .b_rdy(ar),.b_addr(ba[st*960+:960]),.b_len(bl[st*128+:128]),
 .b_tag(bt[st*512+:512]),.b_we(bwe[st*32+:32]),.b_wdata(bw[st*8192+:8192]),
 .b_wstrb(bs[st*1024+:1024]),.b_wr_done(bd[st*32+:32]),
 .b_rsp_v(rv[st*32+:32]),.b_rsp_rdy(rr[st*32+:32]),
 .b_rsp_tag(rt[st*512+:512]),.b_rsp_beat(rb[st*128+:128]),.b_rsp_data(rd[st*8192+:8192]),
 .k_v(1'b0),.k_addr(30'b0),.k_len(4'b0),.k_tag(16'b0),.k_we(1'b0),
 .k_wdata(256'b0),.k_wstrb(32'b0),.k_rsp_rdy(1'b0),
 .h_v(hv),.h_rdy(hr),.h_addr(ha),.h_len(hl),.h_tag(ht),.h_we(hwe),
 .h_wdata(hw),.h_wstrb(hs),.h_wr_done(hd),.r_v(mv),.r_rdy(mr),.r_tag(mt),.r_beat(mb),.r_data(md));
 ot_hdc_v41x_idx_hbm_c8 #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),
 .MEM_WORDS(MEM_WORDS),.MEM_MODE(0),.REFPB(3),.QD(64),.RQD(32),.CLK_PS(CLK_PS)) u_mem(
 .clk(clk),.rst_n(rst_n),.req_v(hv),.req_rdy(hr),.req_addr(ha),.req_len(hl),
 .req_tag(ht),.req_we(hwe),.req_wdata(hw),.req_wstrb(hs),.wr_done(hd),
 .wr_done_addr(done_addr),.wr_done_tag(done_tag),.rsp_v(mv),.rsp_rdy(mr),
 .rsp_tag(mt),.rsp_beat(mb),.rsp_data(md));
 end endgenerate
 always @(posedge clk) if(rst_n)begin
 if(w_v||(|r_v))admitted<=1;
 if(|(bv&~range_ok))range_fault<=1;
 // Native ring record names physical region0 and position, NOT logical cfg base.
 if(w_v&&(w_ssec!=0||w_csec>=262144||w_sslot!=0))range_fault<=1;
 end
 export "DPI-C" function s81_index_preload_ring;
 function void s81_index_preload_ring(input string directory);
 integer fd,n,count;reg[63:0] address;reg[255:0] data_word;string path;
 if(rst_n||admitted||history_ready)$fatal(1,"index history reload after admission/reset");
 for(integer st=0;st<4;st=st+1)begin
 path=$sformatf("%s/ikring_s%0d.hex",directory,st);
 fd=$fopen(path,"r");if(!fd)$fatal(1,"missing ring raw image %s",path);
 count=0;
 while(!$feof(fd))begin
 n=$fscanf(fd,"%h %h\n",address,data_word);
 if(n==2)begin
 if(address>=MEM_WORDS)$fatal(1,"ring physical address outside backing");
 case(st)
 0:g_s[0].u_mem.mem[address]=data_word;
 1:g_s[1].u_mem.mem[address]=data_word;
 2:g_s[2].u_mem.mem[address]=data_word;
 3:g_s[3].u_mem.mem[address]=data_word;
 endcase
 count=count+1;
 end else if(!$feof(fd))$fatal(1,"malformed ring ADDRESS DATA image");
 end
 $fclose(fd);if(count==0)$fatal(1,"empty ring source image");
 end
 history_ready=1;
 endfunction
endmodule
