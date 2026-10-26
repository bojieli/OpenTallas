`timescale 1ns/1ps
// tb_bmul_gu (H-SM 2026-10-15): 200,000 BF16 x BF16 products (random, deep-underflow and full-range classes) against
// numpy float32 = IEEE RNE with gradual underflow and +0 zeros (tools/hdc_golden.py mul).  +define+BMUL_CLOSED = the
// closed ot_hbm_accel_smh_bmul as the negative control (faults every product below 2^-133).
module tb_gu;
  localparam integer N=200000, LAT=7;
  reg clk=0; always #0.5 clk=~clk; reg rst_n=0;
  reg [15:0] ma [0:N-1]; reg [15:0] mb [0:N-1]; reg [31:0] my [0:N-1]; reg mf [0:N-1];
  reg v=0; reg [31:0] a=0,b=0; wire [31:0] y; wire fault;
  `ifdef BMUL_CLOSED
  ot_hbm_accel_smh_bmul u(
`else
  ot_hbm_accel_smh_bmul_gu u(
`endif
   .clk(clk),.rst_n(rst_n),.v(v),.kill(1'b0),.a(a),.b(b),.y(y),.fault(fault));
  integer sent=0, got=0, err=0, nsub=0, ok=0;
  integer pidx [0:LAT+1]; reg pv [0:LAT+1]; integer k;
  initial begin string d; if (!$value$plusargs("DIR=%s", d)) d = "."; $readmemh({d,"/a.hex"},ma); $readmemh({d,"/b.hex"},mb); $readmemh({d,"/y.hex"},my); $readmemh({d,"/f.hex"},mf);
    for (k=0;k<=LAT+1;k=k+1) begin pv[k]=0; pidx[k]=0; end
    repeat(3) @(posedge clk); rst_n=1; end
  always @(posedge clk) if (rst_n) begin
    // the output at this edge belongs to the input applied LAT edges ago
    if (pv[LAT]) begin
      if (mf[pidx[LAT]]) ok=ok+1;
      else if (fault || y !== my[pidx[LAT]]) begin err=err+1; if (err<10) $display("ERR i=%0d a=%04h b=%04h y=%08h want=%08h fault=%b",pidx[LAT],ma[pidx[LAT]],mb[pidx[LAT]],y,my[pidx[LAT]],fault); end
      else begin ok=ok+1; if (my[pidx[LAT]][30:23]==0 && my[pidx[LAT]]!=0) nsub=nsub+1; end
      got=got+1;
    end
    for (k=LAT+1;k>0;k=k-1) begin pv[k]<=pv[k-1]; pidx[k]<=pidx[k-1]; end
    if (sent<N) begin v<=1; a<={ma[sent],16'd0}; b<={mb[sent],16'd0}; pv[0]<=1; pidx[0]<=sent; sent<=sent+1; end
    else begin v<=0; pv[0]<=0; end
    if (got==N) begin $display("BMUL_GU %s checked=%0d errors=%0d subnormal_results=%0d", err?"FAIL":"PASS", got, err, nsub); $finish; end
  end
endmodule
