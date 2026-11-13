`timescale 1ns/1ps
module fq_ref #(
    parameter integer W=553, AW=3, NS=(W+15)/16, MUT=0
)(input wire clk, input wire rst_n,
  input wire [1:0] we, input wire [2*AW-1:0] wa, input wire [W-1:0] wd,
  input wire [2*AW-1:0] ra, output wire [W-1:0] q);
    localparam integer NB=(W+127)/128;
    reg [1:0] wv; reg [AW-1:0] waddr0, waddr1; reg [W-1:0] wdata, prevdata;
    always @(posedge clk or negedge rst_n) if (!rst_n) wv <= 2'b00; else wv <= we;
    always @(posedge clk) begin waddr0 <= wa[0 +: AW]; waddr1 <= wa[AW +: AW]; wdata <= wd; prevdata <= wdata; end
    wire [1:0] chit = {we[1] && wa[AW +: AW] == ra[AW +: AW], we[0] && wa[0 +: AW] == ra[0 +: AW]};
    wire [1:0] phit = {wv[1] && waddr1 == ra[AW +: AW], wv[0] && waddr0 == ra[0 +: AW]};
    wire [NB*128-1:0] padded, raw;
    assign padded={{(NB*128-W){1'b0}},wdata};
    genvar b,s;
    generate for(b=0;b<NB;b=b+1) begin:g_bank
`ifdef OT_SRAM_P192
        ot_sram_1r1w_32x128_m1_p192_rc u_m(.clk(clk),
`else
        ot_sram_1r1w_32x128_m1 u_m(.clk(clk),
`endif
            .r_ce_in(1'b1),.r_addr_in(5'(ra[0 +: AW])),
            .rd_out(raw[b*128+:128]),.w_ce_in(wv[0]),.w_addr_in(5'(waddr0)),
            .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
    end
    for(s=0;s<NS;s=s+1) begin:g_slice
        localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16, H=(s < NS/2) ? 0 : 1;
        (* keep="true" *) reg cur_q, prev_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin cur_q<=1'b0; prev_q<=1'b0; end
            else begin cur_q<=(MUT==1)?1'b0:chit[H]; prev_q<=(MUT==2)?1'b0:phit[H]; end
        assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
    end endgenerate
endmodule
module fq_new #(
    parameter integer W=553, AW=3, NS=(W+15)/16, MUT=0, HLAT=0, HLAT_PREV=0
)(input wire clk, input wire rst_n,
  input wire [1:0] we, input wire [2*AW-1:0] wa, input wire [W-1:0] wd,
  input wire [2*AW-1:0] ra, output wire [W-1:0] q);
    localparam integer NB=(W+127)/128;
    reg [1:0] wv; reg [AW-1:0] waddr0, waddr1; reg [W-1:0] wdata, prevdata;
    always @(posedge clk or negedge rst_n) if (!rst_n) wv <= 2'b00; else wv <= we;
    // Launch-side negative-level lockup; macro writes keep their original sampled edge.
    // Receiving posedges see the same value; forwarding changes only after fall.
    wire [W-1:0] wdata_l, prevdata_l;
    ot_s81ph_hlk #(.W(W), .EN(HLAT)) u_fl_fq_wdata (.clk(clk), .d(wdata), .q(wdata_l));
    ot_s81ph_hlk #(.W(W), .EN(HLAT_PREV)) u_fl_fq_prev (.clk(clk), .d(prevdata), .q(prevdata_l));
    always @(posedge clk) begin waddr0 <= wa[0 +: AW]; waddr1 <= wa[AW +: AW]; wdata <= wd; prevdata <= wdata_l; end
    wire [1:0] chit = {we[1] && wa[AW +: AW] == ra[AW +: AW], we[0] && wa[0 +: AW] == ra[0 +: AW]};
    wire [1:0] phit = {wv[1] && waddr1 == ra[AW +: AW], wv[0] && waddr0 == ra[0 +: AW]};
    wire [NB*128-1:0] padded, raw;
    assign padded={{(NB*128-W){1'b0}},wdata_l};
    genvar b,s;
    generate for(b=0;b<NB;b=b+1) begin:g_bank
`ifdef OT_SRAM_P192
        ot_sram_1r1w_32x128_m1_p192_rc u_m(.clk(clk),
`else
        ot_sram_1r1w_32x128_m1 u_m(.clk(clk),
`endif
            .r_ce_in(1'b1),.r_addr_in(5'(ra[0 +: AW])),
            .rd_out(raw[b*128+:128]),.w_ce_in(wv[0]),.w_addr_in(5'(waddr0)),
            .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
    end
    for(s=0;s<NS;s=s+1) begin:g_slice
        localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16, H=(s < NS/2) ? 0 : 1;
        (* keep="true" *) reg cur_q, prev_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin cur_q<=1'b0; prev_q<=1'b0; end
            else begin cur_q<=(MUT==1)?1'b0:chit[H]; prev_q<=(MUT==2)?1'b0:phit[H]; end
        assign q[LO+:SW]=cur_q ? wdata_l[LO+:SW] : prev_q ? prevdata_l[LO+:SW] : raw[LO+:SW];
    end endgenerate
endmodule
module ot_s81ph_hlk #(parameter integer W = 1, parameter integer EN = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (EN != 0) begin : g_lat
        reg [W-1:0] l;
`ifdef OT_S81PH_HLK_MUT
        always_latch if (clk) l <= d;     // bench mutant: positive-level latch (the hop passes in the high phase)
`else
        `ifdef FQ_STALE_MUT
        always @(posedge clk) l <= d; // causal mutant: extra cycle on the forwarding hop
`else
        always_latch if (!clk) l <= d;
`endif
`endif
        assign q = l;
`ifdef OT_S81PH_HLK_COV
        // bench coverage only: count q changes (each latch must toggle under the layer traffic)
        integer ntog = 0; reg [W-1:0] lq;
        always @(negedge clk) begin #0.001 if (l !== lq) ntog = ntog + 1; lq = l; end
        final $display("HLK_COV %m W %0d toggles %0d", W, ntog);
`endif
    end else begin : g_wire
        assign q = d;
    end endgenerate
endmodule
module ot_sram_1r1w_32x128_m1(input clk,r_ce_in,input[4:0]r_addr_in,output reg[127:0]rd_out,input w_ce_in,input[4:0]w_addr_in,input[127:0]wd_in,w_mask_in);
 reg[127:0]mem[0:31];integer k;initial begin rd_out=0;for(k=0;k<32;k=k+1)mem[k]=0;end
 always @(posedge clk)begin
  if(r_ce_in)rd_out<=mem[r_addr_in];
  if(w_ce_in)for(integer j=0;j<128;j=j+1)if(w_mask_in[j])mem[w_addr_in][j]<=wd_in[j];
 end
endmodule
module tb;
 parameter PREV=0;
 localparam W=137, AW=3;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg[1:0]we=0;reg[2*AW-1:0]wa=0,ra=0;reg[W-1:0]wd=0;
 wire[W-1:0]a,b;
 fq_ref #(.W(W),.AW(AW)) r(clk,rst_n,we,wa,wd,ra,a);
 fq_new #(.W(W),.AW(AW),.HLAT(1),.HLAT_PREV(PREV)) n(clk,rst_n,we,wa,wd,ra,b);
 integer i,j,k,errors=0,checks=0,cur=0,prev=0,raw=0,resets=0,memory_checks=0,write_edges=0;reg[AW-1:0]addr=0,paddr=0;reg[31:0]seed=32'h9812bac1;
 function automatic[31:0]rng(input[31:0]x);reg[31:0]t;begin t=x^(x<<13);t=t^(t>>17);rng=t^(t<<5);end endfunction
 always @(posedge clk)begin
  // This is the actual downstream FF sampling edge, BEFORE source NBA updates.
  if(rst_n && i>5)begin
   checks=checks+1;
   if(a!==b)begin if(errors<4)$display("EDGE_MISMATCH cycle=%0d prevmode=%0d ref=%h new=%h",i,PREV,a,b);errors=errors+1;end
   if(r.g_slice[0].cur_q)cur=cur+1;else if(r.g_slice[0].prev_q)prev=prev+1;else raw=raw+1;
  end
  if(r.wv[0])write_edges=write_edges+1;
  #1;
  if(i>5)for(k=0;k<32;k=k+1)begin
   memory_checks=memory_checks+2;
   if(r.g_bank[0].u_m.mem[k]!==n.g_bank[0].u_m.mem[k])errors=errors+1;
   if(r.g_bank[1].u_m.mem[k]!==n.g_bank[1].u_m.mem[k])errors=errors+1;
  end
  if(i>5 && (r.wdata!==n.wdata || r.prevdata!==n.prevdata))begin errors=errors+1;end
 end
 initial begin
  for(i=0;i<4096;i=i+1)begin
   @(negedge clk);#1;
   rst_n=(i>=3 && i%251!=0);if(!rst_n)resets=resets+1;
   seed=rng(seed);addr=seed[AW-1:0];we={2{seed[4] || seed[5]}};wa={addr,addr};
   case(i%5)
    0:ra={addr,addr};
    1:ra={paddr,paddr};
    default:begin seed=rng(seed);ra={2{seed[AW-1:0]}};end
   endcase
   for(j=0;j<W;j=j+1)begin seed=rng(seed);wd[j]=seed[0];end
   paddr=addr;
   @(posedge clk);#2;
  end
  if(cur==0 || prev==0 || raw==0 || resets<2)$fatal(1,"coverage absent");
`ifdef FQ_STALE_MUT
  if(errors==0)$fatal(1,"stale mutant survived");
  $display("FIFO_HLAT_MUTANT_KILLED prevmode=%0d errors=%0d checks=%0d cur=%0d prev=%0d raw=%0d resets=%0d memory_checks=%0d write_edges=%0d",PREV,errors,checks,cur,prev,raw,resets,memory_checks,write_edges);
`else
  if(errors!=0)$fatal(1,"exact mismatch errors=%0d",errors);
  $display("FIFO_HLAT_EXACT_PASS prevmode=%0d checks=%0d cur=%0d prev=%0d raw=%0d resets=%0d width=%0d memory_checks=%0d write_edges=%0d",PREV,checks,cur,prev,raw,resets,W,memory_checks,write_edges);
`endif
  $finish;
 end
endmodule
