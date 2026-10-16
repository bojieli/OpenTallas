`timescale 1ns/1ps
// ot_s81_engram_hash_static == ot_hdc_engram_hash_shipped, every cycle, every column (row and row-offset residue),
// random ids with random sequence starts. +MUT=1 corrupts one residue bit of the candidate compare (must fail).
import ot_hdc_engram_tables_shipped_pkg::*;
module tb_s81_engram_hash_static_equiv;
 localparam integer NC = ENG_LAYERS*ENG_COLS;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0, v=0, f=0; reg [ENG_ID_W-1:0] id=0;
 wire av, bv; wire [ENG_ROW_W*NC-1:0] ar, br; wire [ENG_RES_W*NC-1:0] bs;
 ot_hdc_engram_hash_shipped ref_h(.clk(clk),.rst_n(rst_n),.in_valid(v),.in_first(f),.in_cid(id),.out_valid(av),.out_row(ar));
 ot_s81_engram_hash_static dut(.clk(clk),.clk_columns({6{clk}}),.rst_n(rst_n),.in_valid(v),.in_first(f),.in_cid(id),
   .out_valid(bv),.out_row(br),.out_res(bs));
 integer cyc=0, n=0, c, mut=0;
 reg [ENG_ROW_W-1:0] off, rr;
 initial if($value$plusargs("MUT=%d",mut)) begin end
 always @(negedge clk) begin
  cyc=cyc+1; rst_n = cyc>3;
  v = ($urandom%4)!=0; f = v && ($urandom%16)==0;
  case ($urandom%4) 0: id = $urandom; 1: id = {ENG_ID_W{1'b1}}; 2: id = $urandom%64; default: id = ENG_PAD; endcase
 end
 always @(posedge clk) begin
  #0.1;
  if (rst_n) begin
   if (av!==bv) $fatal(1,"EQUIV valid mismatch cyc%0d",cyc);
   if (av) begin
    for (c=0;c<NC;c=c+1) begin
     off = ENG_OFFSET[ENG_ROW_W*c +: ENG_ROW_W];
     rr = ar[ENG_ROW_W*c +: ENG_ROW_W];
     if (br[ENG_ROW_W*c +: ENG_ROW_W]!==rr) $fatal(1,"EQUIV row mismatch cyc%0d col%0d",cyc,c);
     if ((bs[ENG_RES_W*c +: ENG_RES_W] ^ ((mut==1 && n==77 && c==5) ? 1 : 0)) !== (rr-off)) $fatal(1,"EQUIV residue mismatch cyc%0d col%0d",cyc,c);
    end
    n=n+1;
   end
  end
  if (cyc==200000) begin
   if (n<100000) $fatal(1,"EQUIV coverage n%0d",n);
   $display("EQUIV PASS rows %0d x %0d columns", n, NC); $finish;
  end
 end
endmodule
