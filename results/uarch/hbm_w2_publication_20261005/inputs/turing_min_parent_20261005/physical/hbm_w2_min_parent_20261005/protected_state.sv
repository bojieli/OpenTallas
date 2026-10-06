`timescale 1ns/1ps
// Inherited mutable-state protection; selected child RTL remains unchanged.
module ot_hbm_w2_parent_protected_view #(parameter integer WIDTH=32)(
 input wire clk,por_n,we,input wire [WIDTH-1:0] next_data,
 output wire [WIDTH-1:0] data,output wire fault
);
 localparam integer BYTES=(WIDTH+7)/8, PAD=BYTES*8;
 (* keep = 1 *) reg [PAD-1:0] a,b,c;(* keep = 1 *) reg [BYTES-1:0] pa,pb,pc;
 wire [PAD-1:0] vote=(a&b)|(a&c)|(b&c);
 wire [PAD-1:0] padded={{(PAD-WIDTH){1'b0}},next_data};
 wire [BYTES-1:0] bad,parity;
 for(genvar k=0;k<BYTES;k=k+1)begin:byte_check
  wire ea=(^a[k*8+:8])!=pa[k],eb=(^b[k*8+:8])!=pb[k],ec=(^c[k*8+:8])!=pc[k];
  assign bad[k]=(ea&&eb)||(ea&&ec)||(eb&&ec);
  assign parity[k]=^padded[k*8+:8];
 end
 assign data=vote[WIDTH-1:0];assign fault=|bad;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin a<=0;b<=0;c<=0;pa<=0;pb<=0;pc<=0;end
  else if(we&&!fault)begin a<=padded;b<=padded;c<=padded;pa<=parity;pb<=parity;pc<=parity;end
  else if(!fault)begin
   a<=vote;b<=vote;c<=vote;
   for(integer k=0;k<BYTES;k=k+1)begin
    pa[k]<=^vote[k*8+:8];pb[k]<=^vote[k*8+:8];pc[k]<=^vote[k*8+:8];
   end
  end
 end
endmodule
`timescale 1ps/1fs
// Protected coded-word crossing. Pointer rail mismatch refuses transfer; local
// mutable mismatch is sticky. No ECC is removed from the coded payload words.
module ot_hbm_w2_parent_protected_fifo #(parameter W=360,AW=5)(
 input wire wclk,wrst_n,we,input wire[W-1:0] wdata,output wire full,
 output wire[2:0] rd_freed,output wire w_fault,
 input wire rclk,rrst_n,re,output wire[W-1:0] rdata,output wire empty,output wire r_fault);
 localparam D=1<<AW;
 wire[D*W-1:0] mem_bus;
 wire[D-1:0] payload_fault;
 for(genvar bank_idx=0;bank_idx<D;bank_idx=bank_idx+1)begin:bank
  localparam integer IDX=bank_idx;
  wire [W-1:0] bank_data;
  assign mem_bus[IDX*W+:W]=bank_data;
  (* keep_hierarchy = 1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(W)) u_code(
   .clk(wclk),.por_n(wrst_n),.we(we&&!full&&wb[AW-1:0]==IDX),
   .next_data(wdata),.data(bank_data),.fault(payload_fault[IDX]));
 end
 (* keep = 1 *) reg[AW:0] wb,wg,rb,rg,wb_n,wg_n,rb_n,rg_n;
 (* async_reg="true" *) (* keep = 1 *) reg[AW:0] rw1,rw2,rn1,rn2,ww1,ww2,wn1,wn2;
 (* keep = 1 *) reg[AW:0] freed,freed_n;
 (* keep = 1 *) reg wf,rf,wf_n,rf_n;
 wire wbad=(wf!=~wf_n)||(wb!=~wb_n)||(wg!=~wg_n)||(freed!=~freed_n);
 wire rbad=(rf!=~rf_n)||(rb!=~rb_n)||(rg!=~rg_n);
 wire rok=rw2==~rn2,wok=ww2==~wn2;
 assign full=wf||wbad||payload_fault[wb[AW-1:0]]||!rok||(wg=={~rw2[AW:AW-1],rw2[AW-2:0]});
 assign empty=rf||rbad||payload_fault[rb[AW-1:0]]||!wok||(rg==ww2);
 wire[AW:0] bw=wb+(we&&!full),br=rb+(re&&!empty);
 wire[AW:0] gw=bw^(bw>>1),gr=br^(br>>1);
 function automatic[AW:0] graybin(input[AW:0] g);
  for(integer i=AW;i>=0;i=i-1)graybin[i]=(i==AW)?g[i]:graybin[i+1]^g[i];
 endfunction
 wire[AW:0] released=graybin(rw2);
 assign rd_freed=rok&&!wbad&&!wf?3'(released-freed):0;
 assign rdata=mem_bus[rb[AW-1:0]*W+:W];
 assign w_fault=wf||wbad||payload_fault[wb[AW-1:0]];assign r_fault=rf||rbad||payload_fault[rb[AW-1:0]];
 always @(posedge wclk or negedge wrst_n)
  if(!wrst_n)begin wb<=0;wg<=0;wb_n<='1;wg_n<='1;rw1<=0;rw2<=0;rn1<='1;rn2<='1;freed<=0;freed_n<='1;begin wf<=0;wf_n<=~(0);end end
  else begin
   wb<=bw;wg<=gw;wb_n<=~bw;wg_n<=~gw;
   rw1<=rg;rw2<=rw1;rn1<=rg_n;rn2<=rn1;
   if(rok)begin freed<=released;freed_n<=~released;end
   if(wbad)begin wf<=1;wf_n<=~(1);end 
  end
 always @(posedge rclk or negedge rrst_n)
  if(!rrst_n)begin rb<=0;rg<=0;rb_n<='1;rg_n<='1;ww1<=0;ww2<=0;wn1<='1;wn2<='1;begin rf<=0;rf_n<=~(0);end end
  else begin rb<=br;rg<=gr;rb_n<=~br;rg_n<=~gr;ww1<=wg;ww2<=ww1;wn1<=wg_n;wn2<=wn1;if(rbad)begin rf<=1;rf_n<=~(1);end end
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_w2_parent_mreq_cdc: one SM memory client crossing from the SM clock domain into
// the crossbar/L2/HBM-service domain (the GPC <-> XBAR asynchronous boundary
// of a GPU): a request FIFO (we, address, write data, byte enables, tag) and a
// response FIFO (tag, kind, data), both ot_gpu_cdc_fifo at the depth the
// sizing model gives for one entry per cycle across 833 ps <-> 1000 ps
// (tools/gpu_sys/cdc_sizing.py: 8 entries, measured >= 0.99 entries/cycle).
// ENABLE = 0: inert, every output 0.
// ---------------------------------------------------------------------------
module ot_hbm_w2_parent_mreq_cdc #(
    parameter integer ENABLE = 0,
    parameter integer AW     = 3
) (
    input  wire          clk_s,
    input  wire          rst_s_n,
    input  wire          clk_m,
    input  wire          rst_m_n,
    // SM side (clk_s)
    input  wire          s_req_v,
    output wire          s_req_rdy,
    input  wire          s_req_we,
    input  wire [31:0]   s_req_addr,
    input  wire [255:0]  s_req_wdata,
    input  wire [31:0]   s_req_wstrb,
    input  wire [15:0]   s_req_tag,
    output wire          s_rsp_v,
    input  wire          s_rsp_rdy,
    output wire [15:0]   s_rsp_tag,
    output wire          s_rsp_we,
    output wire [255:0]  s_rsp_data,
    // memory side (clk_m)
    output wire          m_req_v,
    input  wire          m_req_rdy,
    output wire          m_req_we,
    output wire [31:0]   m_req_addr,
    output wire [255:0]  m_req_wdata,
    output wire [31:0]   m_req_wstrb,
    output wire [15:0]   m_req_tag,
    input  wire          m_rsp_v,
    output wire          m_rsp_rdy,
    input  wire [15:0]   m_rsp_tag,
    input  wire          m_rsp_we,
    input  wire [255:0]  m_rsp_data,
    output wire          fault
);
generate if (ENABLE == 0) begin : g_off
    assign s_req_rdy = 1'b0; assign s_rsp_v = 1'b0; assign s_rsp_tag = 16'd0; assign s_rsp_we = 1'b0;
    assign s_rsp_data = 256'd0; assign m_req_v = 1'b0; assign m_req_we = 1'b0; assign m_req_addr = 32'd0;
    assign m_req_wdata = 256'd0; assign m_req_wstrb = 32'd0; assign m_req_tag = 16'd0; assign m_rsp_rdy = 1'b0;
    assign fault = 1'b0;
end else begin : g_on
    wire f0,f1,rf0,rf1;wire full0,empty0,full1,empty1;
    assign s_req_rdy=!full0;assign m_req_v=!empty0;
    assign m_rsp_rdy=!full1;assign s_rsp_v=!empty1;
    ot_hbm_w2_parent_protected_fifo #( .W(1 + 32 + 256 + 32 + 16), .AW(AW)) u_req (
        .wclk(clk_s), .wrst_n(rst_s_n), .we(s_req_v&&!full0), .full(full0),.rd_freed(),.w_fault(f0),
        .wdata({s_req_we, s_req_addr, s_req_wdata, s_req_wstrb, s_req_tag}),
        .rclk(clk_m), .rrst_n(rst_m_n), .empty(empty0),.re(m_req_rdy&&!empty0),.r_fault(rf0),
        .rdata({m_req_we, m_req_addr, m_req_wdata, m_req_wstrb, m_req_tag}));
    ot_hbm_w2_parent_protected_fifo #( .W(16 + 1 + 256), .AW(AW)) u_rsp (
        .wclk(clk_m), .wrst_n(rst_m_n), .we(m_rsp_v&&!full1), .full(full1),.rd_freed(),.w_fault(f1), .wdata({m_rsp_tag, m_rsp_we, m_rsp_data}),
        .rclk(clk_s), .rrst_n(rst_s_n), .empty(empty1),.re(s_rsp_rdy&&!empty1),.r_fault(rf1), .rdata({s_rsp_tag, s_rsp_we, s_rsp_data}));
    assign fault = f0 | f1 | rf0 | rf1;
end endgenerate
endmodule
