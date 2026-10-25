`timescale 1ns/1ps
module tb;
reg ck=0,rn=0;always #0.5 ck=~ck;
reg[275:0]v=0;wire[275:0]o;wire f;integer ng=0,err=0;
reg[275:0]stim[0:305],gold[0:73];
`ifndef MUT
`define MUT 0
`endif
dsdv_bk_selids #(.MUT(`MUT))dut(ck,rn,v,o,f);
always @(negedge ck)if(rn&&o[0])begin if(ng>=74||o!==gold[ng])err=err+1;ng=ng+1;end
initial begin $readmemh("stim.hex",stim);$readmemh("gold.hex",gold);repeat(4)@(negedge ck);rn=1;for(integer i=0;i<306;i++)begin @(negedge ck);v=stim[i];end @(negedge ck);v=0;repeat(12)@(negedge ck);$display("ENCODER_COSIM words=%0d want=74 errors=%0d fault=%0d",ng,err,f);if(err==0&&ng==74&&!f)$display("PASS");else $display("FAIL");$finish;end
endmodule
