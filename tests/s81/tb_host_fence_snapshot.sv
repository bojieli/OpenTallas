`timescale 1ns/1ps
// Boundary-only stimulus and exact edge comparison with source-pinned legacy
// RTL. The snapshot capture must consume existing req synchronizer slack;
// allowing an extra completion edge would fail this test.
module tb_host_fence_snapshot;
 parameter integer CP=6, HP=6, PHASE=0;
 reg ck=0, ch=0, rst=0;
 always #(CP/2.0) ck=~ck;
 initial begin #(PHASE); forever #(HP/2.0) ch=~ch; end
 reg [7:0] ack=0;
 reg iv=0, cr=0; reg [63:0] id=0;
 wire ic,ov,ft; wire [63:0] od; wire [31:0] landed;
 wire ic0,ov0,ft0; wire [63:0] od0; wire [31:0] landed0;
 ot_s81_ingest_visibility_fence #(.ENABLE(1),.PIPE(2)) dut(
  .rst_n(rst),.ck(ck),.clk_h(ch),.ack_n(ack),.in_v(iv),.in_d(id),
  .in_cr(ic),.out_v(ov),.out_d(od),.out_cr(cr),.fault(ft),.landed_debug(landed));
 ot_s81_ingest_visibility_fence_old #(.ENABLE(1),.PIPE(2)) ref_dut(
  .rst_n(rst),.ck(ck),.clk_h(ch),.ack_n(ack),.in_v(iv),.in_d(id),
  .in_cr(ic0),.out_v(ov0),.out_d(od0),.out_cr(cr),.fault(ft0),.landed_debug(landed0));
 integer cc=0,hc=0,checked=0,words=0;
 initial begin #29 rst=1; end
 always @(negedge ck) if(rst) begin
  cc=cc+1;
  ack=cc%5==0 ? 1+(cc%7) : 0;
 end
 always @(negedge ch) if(rst) begin
  hc=hc+1; iv=0; cr=ov;
  // Alternating ordinary completions and DONE words. DONE is held until the
  // actual source-side ACK count reaches the specified visibility watermark.
  if(hc>30 && hc<3500 && hc%19==0) begin
   iv=1; id=hc%38==0 ? {8'h01,24'd0,32'(hc/3)} : {8'h02,24'(hc),32'(hc*917)};
  end
  if(hc==4200) begin
   if(words<150 || ft || ft0) $fatal(1,"FENCE_SNAPSHOT FAIL traffic/fault words=%0d",words);
   $display("FENCE_SNAPSHOT PASS exact_edges=%0d words=%0d CP=%0d HP=%0d PHASE=%0d",checked,words,CP,HP,PHASE);
   $finish;
  end
 end
 always @(posedge ch) if(rst) begin
  #0.01;
  if(hc>5) begin
   checked=checked+1;
   if({ic,ov,od,ft,landed} !== {ic0,ov0,od0,ft0,landed0})
    $fatal(1,"FENCE_SNAPSHOT FAIL exact timeline edge=%0d actual=%h legacy=%h",hc,{ic,ov,od,ft,landed},{ic0,ov0,od0,ft0,landed0});
   if(ov) words=words+1;
  end
 end
endmodule
