`timescale 1ns/1ps
// Exact word bench of the v1.4 head stage leaves: every output word equals the input word one ck edge earlier.
// MUT 1: the bench model expects bit 0 inverted (proves the comparison observes the DUT).
module tb_qkh_head_stages;
  parameter integer WHICH=0, MUT=0, N=20000;
  localparam integer W = WHICH==0 ? 1575 : 34;
  reg ck=0; always #0.5 ck=~ck;
  reg [W-1:0] a=0; wire [W-1:0] b;
  generate if (WHICH==0) begin:g_t
    qkh_head_tstage u (.ck(ck),.ti_a(a[1574:16]),.e_a(a[15:0]),.ti_b(b[1574:16]),.e_b(b[15:0]));
  end else begin:g_s
    qkh_head_sstage u (.ck(ck),.s_a(a),.s_b(b));
  end endgenerate
  integer i,k,errors=0,checks=0;
  initial begin
    for(i=0;i<N+2;i=i+1) begin
      @(negedge ck);
      if(i>=2) begin
        checks=checks+1;
        if(b !== (MUT==1 ? (a ^ {{(W-1){1'b0}},1'b1}) : a)) begin
          if(errors<4) $display("RLY_MISMATCH word=%0d", i); errors=errors+1; end
      end

      for(k=0;k<W;k=k+32) a[k +: 32] = $urandom;
    end
    if(errors==0) $display("QKH_STAGE_BENCH PASS W=%0d 0 errors in %0d words", W, checks);
    else begin $display("QKH_STAGE_BENCH FAIL W=%0d %0d errors in %0d words", W, errors, checks); $fatal(1); end
    $finish;
  end
endmodule
