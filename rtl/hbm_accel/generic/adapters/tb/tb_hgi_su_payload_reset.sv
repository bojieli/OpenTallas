`timescale 1ns/1ps
// Minimum four-state reset/valid proof: original and opt-in resetless record payloads.
// Poison every payload while idle, issue the first legal record immediately on reset release,
// and poison again after acceptance. Only valid-qualified words may be consumed.
module tb_hgi_su_payload_reset;
`include "su_sizes.svh"
reg clk=0; always #1 clk=~clk;
reg rst_n=0, rec_v=0, idle=1; reg [2196:0] cur='x;
reg [2196:0] recm[0:NREC-1]; reg [671:0] refs[0:NREC-1];
wire [1:0] rdy, done, fault, halted, opv; wire [669:0] opw[0:1]; wire [1:0] strm[0:1];
`ifdef MUT_IDLE_READ
localparam integer IDLE_READ=1;
`else
localparam integer IDLE_READ=0;
`endif
integer nops=0, ndone=0, wait_idle=0, cycles=0; string dir;
genvar g;
generate for(g=0;g<2;g=g+1) begin: pair
 ot_hgi_su_record #(.LEGACY(0),.PAYLOAD_RESET(g==0),.STREAM_OK(1)) u(
 .clk(clk),.rst_n(rst_n),.hgi_en(1'b1),.rec_v(rec_v),.rec_rdy(rdy[g]),
 .rec_hdr(cur[127:0]),.rec_sut(cur[383:128]),.rec_a(cur[639:384]),.rec_b(cur[895:640]),.rec_c(cur[1151:896]),
 .rec_d(cur[1407:1152]),.rec_o(cur[1663:1408]),.rec_r(cur[1919:1664]),.rec_i(cur[2175:1920]),.rec_n_a(cur[2196:2176]),
 .rec_done(done[g]),.rec_fault(fault[g]),.halted(halted[g]),.op_v(opv[g]),.op_w(opw[g]),.op_strm(strm[g]),
 .op_rdy(1'b1),.su_idle(idle),.su_fault(1'b0),.lg_v(1'b0),.lg_w(670'd0),.lg_rdy(),.drained());
end endgenerate
always @(posedge clk) if(rst_n) begin
 cycles=cycles+1;
 if ({rdy[0],done[0],fault[0],halted[0],opv[0]} !== {rdy[1],done[1],fault[1],halted[1],opv[1]})
  $fatal(1,"PAYLOAD reset control mismatch");
 if (^({rdy,done,fault,halted,opv}) === 1'bx) $fatal(1,"PAYLOAD control X");
 if(opv[1] || IDLE_READ) begin
  if(opw[1] !== opw[0] || opw[1] !== refs[0][669:0] || strm[1] !== strm[0])
   $fatal(1,"PAYLOAD visible op mismatch or X");
 end
 if(opv[1]) begin
  nops=nops+1; idle<=0; wait_idle=7;
 end else if(wait_idle>0) begin wait_idle=wait_idle-1; if(wait_idle==0) idle<=1; end
 if(done[1]) ndone=ndone+1;
end
integer k;
initial begin
 if(!$value$plusargs("DIR=%s",dir)) dir=".";
 $readmemh({dir,"/su_rec.mem"},recm); $readmemh({dir,"/su_ref.mem"},refs);
 for(k=0;k<2;k=k+1) begin
  @(negedge clk); rst_n=0; cur='x; rec_v=0; idle=1; repeat(2) @(negedge clk);
  rst_n=1; cur=recm[0]; rec_v=1; // first edge after release, no warmup allowance
  @(negedge clk); rec_v=0; cur='x;
  repeat(20) @(negedge clk);
 end
 if(nops!=2 || ndone!=2) $fatal(1,"PAYLOAD drop/duplicate: op%0d done%0d",nops,ndone);
 $display("HGI_SU_PAYLOAD_RESET PASS: 2 immediate-release records, idle poison, four-state valid/control exact");
 $finish;
end
endmodule
