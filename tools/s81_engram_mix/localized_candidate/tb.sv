`timescale 1ns/1ps
// Mechanism-level sequential equivalence of every replaced baseline register.
// Same-phase roots are required by the parent contract; no analog timing claim.
module tb #(parameter MUT=0);
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0;
 reg [19:0] rs_v,c_rqv;reg [10239:0] rs_d;
 reg [279:0] c_rqrow;reg [3:0] c_vtag;
 reg desc_rq;reg [13:0] desc_row;
 reg [19:0] ref_rv,ref_rq;reg [10239:0] ref_rd;reg [279:0] ref_row;
 wire [19:0] rv,rq;wire [10239:0] rd;wire [279:0] row;
 integer q,k,n,checks=0,errors=0,resets=0;
 reg [31:0] rng=32'h106217aa;
 function automatic [31:0] advance(input [31:0] x);
  reg [31:0] v;
  begin v=x^(x<<13);v=v^(v>>17);advance=v^(v<<5);end
 endfunction
 // Literal baseline capture equations from b4ca1edc9.
 always @(posedge clk or negedge rst_n)if(!rst_n)ref_rv<=0;else ref_rv<=rs_v;
 always @(posedge clk)ref_rd<=rs_d;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin ref_rq<=0;ref_row<=0;end else begin
  ref_rq<=c_rqv;ref_row<=c_rqrow;
  for(q=1;q<4;q=q+1)if(c_vtag[q])begin ref_rq[5*q+1]<=0;ref_rq[5*q+2]<=0;end
  if(desc_rq)begin ref_rq[0]<=1'b1;ref_row[0+:14]<=desc_row;end
 end
 genvar l,c;
 generate for(l=0;l<20;l=l+1)begin:ingress
  ot_s81_engram_return_capture cap(.clk((MUT==1&&l==0)?1'b0:clk),.rst_n(rst_n),
   .v_i(rs_v[l]),.d_i(rs_d[512*l+:512]),.v_o(rv[l]),.d_o(rd[512*l+:512]));
 end
 for(c=0;c<4;c=c+1)begin:egress
  ot_s81_engram_request_capture #(.COPY(c)) cap(.clk((MUT==2&&c==0)?1'b0:clk),.rst_n(rst_n),
   .v_i(c_rqv[5*c+:5]),.row_i(c_rqrow[70*c+:70]),.vtag(c_vtag[c]),
   .desc_rq(desc_rq),.desc_row(desc_row),.v_o(rq[5*c+:5]),.row_o(row[70*c+:70]));
 end endgenerate
 initial begin
  rs_v=0;rs_d=0;c_rqv=0;c_rqrow=0;c_vtag=0;desc_rq=0;desc_row=0;
  // Check reset independently from initial register state.
  #0.1;rst_n=1;#0.1;rst_n=0;
  for(n=0;n<1024;n=n+1)begin
   @(negedge clk);
   rst_n=(n%61!=0);if(!rst_n)resets=resets+1;
   rng=advance(rng);rs_v=rng[19:0];c_rqv=rng[31:12];c_vtag=n%16;
   desc_rq=n%3==0;rng=advance(rng);desc_row=rng[13:0];
   for(k=0;k<320;k=k+1)begin rng=advance(rng);rs_d[32*k+:32]=rng;end
   for(k=0;k<280;k=k+1)begin rng=advance(rng);c_rqrow[k]=rng[0];end
   @(posedge clk);#0.1;
   for(k=0;k<20;k=k+1)begin
    checks=checks+513;
    if(rv[k]!==ref_rv[k])errors=errors+1;
    if(rd[512*k+:512]!==ref_rd[512*k+:512])errors=errors+1;
   end
   for(k=0;k<4;k=k+1)begin
    checks=checks+75;
    if(rq[5*k+:5]!==ref_rq[5*k+:5])errors=errors+1;
    if(row[70*k+:70]!==ref_row[70*k+:70])errors=errors+1;
   end
  end
  if(errors)$fatal(1,"LOCAL_CAPTURE_FAIL mutant=%0d samples=1024 bitchecks=%0d resets=%0d mismatched_groups=%0d",MUT,checks,resets,errors);
  $display("LOCAL_CAPTURE_PASS samples=1024 bitchecks=%0d resets=%0d replaced_flops=10560",checks,resets);$finish;
 end
endmodule
