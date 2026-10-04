`timescale 1ns/1ps
// Existing native four-stack K service. No new queue/controller implementation.
// Minimum WINDOW/RoPE participant: indexer B port inactive explicitly.
module DsromS81Hbm #(parameter MEM_WORDS=4784128, CLK_PS=833, WINDOW_STREAM_LA=0, WIN_STACK=0)(
 input wire clk,rst_n,
 input wire[3:0] m_v,m_we, input wire[119:0] m_addr,
 input wire[15:0] m_len, input wire[63:0] m_tag,
 input wire[1023:0] m_wdata, input wire[127:0] m_wstrb,
 output wire[3:0] m_rdy,m_wr_done,s_v, input wire[3:0] s_rdy,
 output wire[63:0] s_tag, output wire[15:0] s_beat,
 output wire[1023:0] s_data, output reg history_ready=0, output reg ckv_history_ready=0,
 output wire[31:0] capacity_words,
 input wire[31:0] wl_req_v, output wire[31:0] wl_req_rdy,
 input wire[959:0] wl_req_addr, input wire[127:0] wl_req_len,
 input wire[415:0] wl_req_tag,
 output wire[31:0] wl_rsp_v, input wire[31:0] wl_rsp_rdy,
 output wire[415:0] wl_rsp_tag, output wire[127:0] wl_rsp_beat,
 output wire[8191:0] wl_rsp_data,
 output wire window_la_enabled, output wire[1:0] window_la_stack,
 output reg fault=0);
 assign capacity_words=MEM_WORDS;
 assign window_la_enabled=(WINDOW_STREAM_LA!=0);
 assign window_la_stack=WIN_STACK;
 initial if(WIN_STACK<0 || WIN_STACK>3)$fatal(1,"WINDOW stack out of range");
 wire[31:0] wide_range_ok;
 wire[3:0] wide_fault;
 generate for(genvar pc=0;pc<32;pc=pc+1)begin:g_range
   assign wide_range_ok[pc]=wl_req_len[pc*4+:4]!=0 &&
     (64'(wl_req_addr[pc*30+:30])+64'(wl_req_len[pc*4+:4])<=MEM_WORDS);
 end endgenerate
 reg admitted=0;
 wire[3:0] range_ok;
 generate for(genvar s=0;s<4;s=s+1) begin:g_s
 wire[31:0] hv,hr,hwe,hd,rv,rr;
 wire[959:0] ha; wire[127:0] hl,rb;
 wire[543:0] ht,rt,done_tag; wire[959:0] done_addr;
 wire[8191:0] hw,rd;wire[1023:0] hs;
 wire[31:0] mv,mr,mwe,md,mrv,mrr;
 wire[959:0] ma;wire[127:0] ml,mrb;
 wire[543:0] mt,mrt;wire[8191:0] mw,mrd;wire[1023:0] ms;
 wire[63:0] wrdy,wrv;wire[831:0] wrtag;
 wire[255:0] wrbeat;wire[16383:0] wrdata;
 localparam WIDE=(WINDOW_STREAM_LA!=0 && s==WIN_STACK);
 wire[31:0] wvalid=WIDE ? (wl_req_v & wide_range_ok &
     {32{history_ready&&!fault}}) : 32'b0;
 if(s==WIN_STACK)begin:g_window
   assign wl_req_rdy=wrdy[31:0]&wide_range_ok&{32{history_ready&&!fault}};
   assign wl_rsp_v=wrv[31:0];assign wl_rsp_tag=wrtag[415:0];
   assign wl_rsp_beat=wrbeat[127:0];assign wl_rsp_data=wrdata[8191:0];
 end
 // Existing bounded read-only wide mux, client0 WINDOW; client1 inactive.
 // Both ports feed the SAME u_mem below. Its hierarchy/preload stays unchanged.
 ot_dsrom_hbm_wmux #(.ENABLE(WIDE),.NPC(32),.AW(30),.TAGW(17),
 .LENW(4),.BEATW(4),.DW(256),.NW(2),.CW(1),.WTAGW(13)) u_wmux(
 .clk(clk),.rst_n(rst_n),
 .a_v(hv),.a_rdy(hr),.a_addr(ha),.a_len(hl),.a_tag(ht),.a_we(hwe),
 .a_wdata(hw),.a_wstrb(hs),.a_wr_done(hd),.a_rsp_v(rv),.a_rsp_rdy(rr),
 .a_rsp_tag(rt),.a_rsp_beat(rb),.a_rsp_data(rd),
 .w_v({32'b0,wvalid}),.w_rdy(wrdy),.w_addr({960'b0,wl_req_addr}),
 .w_len({128'b0,wl_req_len}),.w_tag({416'b0,wl_req_tag}),
 .w_rsp_v(wrv),.w_rsp_rdy({32'b0,(WIDE ? wl_rsp_rdy : 32'b0)}),
 .w_rsp_tag(wrtag),.w_rsp_beat(wrbeat),.w_rsp_data(wrdata),
 .h_v(mv),.h_rdy(mr),.h_addr(ma),.h_len(ml),.h_tag(mt),.h_we(mwe),
 .h_wdata(mw),.h_wstrb(ms),.h_wr_done(md),.r_v(mrv),.r_rdy(mrr),
 .r_tag(mrt),.r_beat(mrb),.r_data(mrd),.fault(wide_fault[s]),
 .w_grants(),.a_held());
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
 .clk(clk),.rst_n(rst_n),.req_v(mv),.req_rdy(mr),.req_addr(ma),.req_len(ml),
 .req_tag(mt),.req_we(mwe),.req_wdata(mw),.req_wstrb(ms),.wr_done(md),
 .wr_done_addr(done_addr),.wr_done_tag(done_tag),
 .rsp_v(mrv),.rsp_rdy(mrr),.rsp_tag(mrt),.rsp_beat(mrb),.rsp_data(mrd));
 end endgenerate
 always @(posedge clk) if(rst_n) begin
   if(|m_v || (WINDOW_STREAM_LA && |wl_req_v)) admitted<=1;
   if(|(m_v&~range_ok) || |wide_fault ||
      (WINDOW_STREAM_LA && |(wl_req_v&~wide_range_ok)))fault<=1;
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
 // Existing CKV source-image format is address/data (not readmemh).
 // Loads retained prior images directly, never current-row/QDQ/golden data.
 export "DPI-C" function s81_hbm_preload_ckv;
 function void s81_hbm_preload_ckv(input string directory);
 integer fd,n,count;reg[63:0] addr;reg[255:0] word_data;string path;
 if(rst_n||admitted||!history_ready||ckv_history_ready)
   $fatal(1,"CKV history init after admission or before base history");
 for(integer s=0;s<4;s=s+1)begin
   path=$sformatf("%s/ckv_s%0d.hex",directory,s);
   fd=$fopen(path,"r");if(!fd)$fatal(1,"missing retained CKV history %s",path);
   count=0;
   while(!$feof(fd))begin
     n=$fscanf(fd,"%h %h\n",addr,word_data);
     if(n==2)begin
       if(addr<4194304||addr>=MEM_WORDS)$fatal(1,"CKV history out of bounds");
       case(s)
       0:g_s[0].u_mem.mem[addr]=word_data;
       1:g_s[1].u_mem.mem[addr]=word_data;
       2:g_s[2].u_mem.mem[addr]=word_data;
       3:g_s[3].u_mem.mem[addr]=word_data;
       endcase
       count=count+1;
     end else if(!$feof(fd))$fatal(1,"malformed CKV source image");
   end
   $fclose(fd);if(count==0)$fatal(1,"empty CKV source image");
 end
 ckv_history_ready=1;
 endfunction
endmodule
