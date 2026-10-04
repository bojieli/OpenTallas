`timescale 1ns/1ps
// Existing native four-stack K service. No new queue/controller implementation.
// Minimum WINDOW/RoPE participant: indexer B port inactive explicitly.
module DsromS81Hbm #(parameter MEM_WORDS=4194304, CLK_PS=833)(
 input wire clk,rst_n,
 input wire[3:0] m_v,m_we, input wire[119:0] m_addr,
 input wire[15:0] m_len, input wire[63:0] m_tag,
 input wire[1023:0] m_wdata, input wire[127:0] m_wstrb,
 output wire[3:0] m_rdy,m_wr_done,s_v, input wire[3:0] s_rdy,
 output wire[63:0] s_tag, output wire[15:0] s_beat,
 output wire[1023:0] s_data, output reg history_ready=0,
 output reg fault=0);
 reg admitted=0;
 wire[3:0] range_ok;
 generate for(genvar s=0;s<4;s=s+1) begin:g_s
 wire[31:0] hv,hr,hwe,hd,rv,rr;
 wire[959:0] ha; wire[127:0] hl,rb;
 wire[543:0] ht,rt,done_tag; wire[959:0] done_addr;
 wire[8191:0] hw,rd;wire[1023:0] hs;
 assign range_ok[s]=m_len[s*4+:4]!=0 &&
   (64'(m_addr[s*30+:30])+64'(m_len[s*4+:4])<=MEM_WORDS);
 ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16)) u_arb(
 .clk(clk),.rst_n(rst_n),
 .b_v(32'b0),.b_addr(960'b0),.b_len(128'b0),.b_tag(512'b0),.b_we(32'b0),
 .b_wdata(8192'b0),.b_wstrb(1024'b0),.b_rsp_rdy(32'b0),
 .k_v(m_v[s]&&history_ready&&range_ok[s]&&!fault),.k_rdy(m_rdy[s]),
 .k_addr(m_addr[s*30+:30]),.k_len(m_len[s*4+:4]),.k_tag(m_tag[s*16+:16]),
 .k_we(m_we[s]),.k_wdata(m_wdata[s*256+:256]),.k_wstrb(m_wstrb[s*32+:32]),
 .k_wr_done(m_wr_done[s]),.k_rsp_v(s_v[s]),.k_rsp_rdy(s_rdy[s]),
 .k_rsp_tag(s_tag[s*16+:16]),.k_rsp_beat(s_beat[s*4+:4]),.k_rsp_data(s_data[s*256+:256]),
 .h_v(hv),.h_rdy(hr),.h_addr(ha),.h_len(hl),.h_tag(ht),.h_we(hwe),
 .h_wdata(hw),.h_wstrb(hs),.h_wr_done(hd),.r_v(rv),.r_rdy(rr),.r_tag(rt),.r_beat(rb),.r_data(rd));
 ot_hdc_v41x_idx_hbm_c8 #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),
 .MEM_WORDS(MEM_WORDS),.MEM_MODE(0),.REFPB(3),.QD(64),.RQD(32),.CLK_PS(CLK_PS)) u_mem(
 .clk(clk),.rst_n(rst_n),.req_v(hv),.req_rdy(hr),.req_addr(ha),.req_len(hl),
 .req_tag(ht),.req_we(hwe),.req_wdata(hw),.req_wstrb(hs),.wr_done(hd),
 .wr_done_addr(done_addr),.wr_done_tag(done_tag),
 .rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));
 end endgenerate
 always @(posedge clk) if(rst_n) begin
   if(|m_v) admitted<=1;
   if(|(m_v&~range_ok))fault<=1;
 end
 // Literal existing sparse prior-history images, before any admitted service.
 // Current-row writes still run through native request/commit paths.
 export "DPI-C" function s81_hbm_preload;
 function void s81_hbm_preload(input string directory);
 integer fd;string path;
 if(rst_n||admitted||history_ready)$fatal(1,"HBM history reload after service/reset release");
 for(integer s=0;s<4;s=s+1)begin
 path=$sformatf("%s/hbm_s%0d.hex",directory,s);
 fd=$fopen(path,"r");if(!fd)$fatal(1,"missing HBM prior history %s",path);$fclose(fd);
 case(s)
 0:$readmemh(path,g_s[0].u_mem.mem);
 1:$readmemh(path,g_s[1].u_mem.mem);
 2:$readmemh(path,g_s[2].u_mem.mem);
 3:$readmemh(path,g_s[3].u_mem.mem);
 endcase
 end
 history_ready=1;
 endfunction
endmodule
