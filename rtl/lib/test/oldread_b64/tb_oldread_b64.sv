`timescale 1ns/1ps
// ot_sram_oldread_b64 (bank64, 2 depth halves) against the reference registered-write OLD-read memory
// ot_s81ph_mem1r1w SRAM 0 / WREG 1 (flop array): random write / read enables over a small hot address set that
// straddles the two 256-row halves, so same-cycle writes (OLD), previous-cycle writes (forwarded) and physical
// same-address read/write edges (suppressed macro read) all occur.  Every cycle after the first read compares q.
module tb_oldread_b64;
 localparam integer W=100, AW=9, NS=(W+7)/8, NA=(NS+3)/4;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0; reg we=0, re=0; reg [AW-1:0] wa=0, ra=0; reg [W-1:0] wd=0;
 wire [W-1:0] q_ref, q_dut;
 ot_s81ph_mem1r1w #(.W(W),.DEPTH(512),.SRAM(0),.WREG(1)) u_ref(.clk(clk),.rst_n(rst_n),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),.q(q_ref));
 ot_sram_oldread_b64 #(.W(W),.AW(AW),.SB(8),.GA(4),.GROUP_IO(0)
`ifdef OT_B64_MUT
  ,.MUT(`OT_B64_MUT)
`endif
 ) u_dut(.clk(clk),.rst_n({NS{rst_n}}),.we(we),.wa({NA{wa}}),.wd(wd),.re(re),.ra({NA{ra}}),.q(q_dut),.we_group({NA{1'b0}}),.re_group({NA{1'b0}}));
 reg [31:0] rng=32'h0b64_5eed; integer c=0, err=0, checks=0, coll=0, fwd=0, old=0; reg seen=0;
 function automatic [AW-1:0] pick(input [31:0] r);
  case (r[2:0]) 0: pick=9'd0; 1: pick=9'd1; 2: pick=9'd256; 3: pick=9'd257; 4: pick=9'd255; 5: pick=9'd511; default: pick=r[31:23]; endcase
 endfunction
 always @(negedge clk) begin
  c=c+1;
  if(seen && rst_n) begin checks=checks+1; if(q_ref!==q_dut) begin err=err+1; if(err<6) $display("B64_ERR cycle=%0d ref=%h dut=%h",c,q_ref,q_dut); end end
  if(re && rst_n) seen=1;
  rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
  rst_n = c>4;
  we = rst_n && rng[0]^rng[7]; re = rst_n && (rng[3]|rng[11]);
  wa = pick(rng); rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
  ra = rng[4] ? wa : pick(rng);
  wd = {rng, rng^32'h5a5a5a5a, rng+c, 4'(c)};
  if(we && re && wa==ra) old=old+1;
  if(re && u_dut.wvalid[0] && u_dut.waddr[AW-1:0]==ra) coll=coll+1;
  if(c==60000) begin
   if(err==0 && checks>50000 && coll>1000 && old>1000) $display("B64_ORACLE PASS checks=%0d same_cycle_old=%0d suppressed_physical_collisions=%0d",checks,old,coll);
   else $display("B64_ORACLE FAIL errors=%0d checks=%0d same_cycle_old=%0d collisions=%0d",err,checks,old,coll);
   $finish;
  end
 end
endmodule
