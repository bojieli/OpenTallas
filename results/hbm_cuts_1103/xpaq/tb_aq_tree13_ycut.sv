`timescale 1ns/1ps
// DIE-HBM-61/CUTS 11-03: ot_hbm_xp_aq_tree13 YCUT=1 == gold (origin/main tree13, module gold_ot_hbm_xp_aq_tree13) with
// EVERY output (vo, q, e, y, fault) delayed one edge. Random fp4/v per edge (II 1, bubbles), structured + random binary32
// (zero, -0, subnormal, max finite, nonfinite, wide exponent spread), periodic mid-run resets. YMUT != 0 must FAIL.
module tb;
  parameter integer YMUT=0, CYC=200000;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0, v=0, fp4=0; reg [1023:0] x=0;
  wire gv,gf,nv,nf; wire [255:0] gq,nq; wire signed [9:0] ge,ne; wire [511:0] gy,ny;
  gold_ot_hbm_xp_aq_tree13 u_g(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(gv),.q(gq),.e(ge),.y(gy),.fault(gf));
  ot_hbm_xp_aq_tree13 #(.YCUT(1),.YMUT(YMUT)) u_n(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(nv),.q(nq),.e(ne),.y(ny),.fault(nf));
  reg dv,df; reg [255:0] dq; reg signed [9:0] de; reg [511:0] dy;
  always @(posedge clk) begin dv<=gv; df<=gf; dq<=gq; de<=ge; dy<=gy; end
  integer cyc, i, bad=0, nchk=0, nval=0, nfp4=0, nflt=0, hi=0; reg [31:0] b; integer k;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      rst_n = (cyc%20000) >= 8;
      hi = rst_n ? hi+1 : 0;
      v = ($urandom%8)!=0; fp4 = $urandom%2;
      k = $urandom%12;
      for(i=0;i<32;i=i+1) begin
        b = $urandom;
        case(k)
          0: b = ($urandom%4==0) ? 32'h0 : {$urandom%2==0, 8'd1+8'($urandom%20), 23'($urandom)};
          1: b = {1'b1, 31'h0};
          2: b = {$urandom%2==0, 8'd0, 23'($urandom)};                    // subnormal
          3: b = {$urandom%2==0, 8'd254-8'($urandom%4), 23'($urandom)};   // near max finite
          4: b = (($urandom%64)==0) ? {1'b0,8'hff,23'($urandom%3)} : b;   // rare nonfinite
          5: b = {$urandom%2==0, 8'd127+8'($urandom%8)-8'd4, 23'($urandom)};
          6: b = {$urandom%2==0, 8'd100+8'($urandom%40), 23'($urandom)};
          default: b = {$urandom%2==0, 8'($urandom%255), 23'($urandom)};
        endcase
        if(k!=4 && b[30:23]==8'hff) b[30:23]=8'hfe;
        x[32*i+:32]=b;
      end
      if(hi>3) begin
        nchk=nchk+1; nval=nval+nv; nfp4=nfp4+(nv&&fp4); nflt=nflt+nf;
        if({dv,df,dq,de,dy}!=={nv,nf,nq,ne,ny}) begin bad=bad+1;
          if(bad<=5) $display("YCUT_MISMATCH cyc=%0d vo %b/%b fault %b/%b q_eq %b e %0d/%0d y_eq %b",cyc,dv,nv,df,nf,dq==nq,de,ne,dy==ny);
        end
      end
    end
    if(bad==0) $display("YCUT_EQ PASS YMUT=%0d checks=%0d valid=%0d fault_cycles=%0d shift=+1 every output",YMUT,nchk,nval,nflt);
    else $display("YCUT_EQ FAIL YMUT=%0d mismatches=%0d of %0d",YMUT,bad,nchk);
    $finish;
  end
endmodule
