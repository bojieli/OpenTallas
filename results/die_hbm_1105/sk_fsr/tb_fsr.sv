// DIE-HBM-66 11-05: EQ bench, HBM tail on row Sinkhorn vs the CE tail (arithmetic gold). Same launch data: result and fault of the
// k-th launch must match bit for bit; the only allowed difference is the calendar, printed as measured.
`timescale 1ns/1ps
`ifndef SEED
`define SEED 20261105
`endif
`ifndef NRUN
`define NRUN 60
`endif
module tb;
reg clk=0,rst_n=0,launch=0; always #5 clk=~clk;
reg [767:0] mixes,bases; reg [95:0] scales;
wire gv,dv,gf,df; wire [767:0] gr,dr;
ot_hbm_hc_tail_unit_static_ce_phys gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(gv),.result(gr),.fault(gf));
ot_hbm_hc_tail_unit_static_fsr_phys
`ifdef P_SMUT
 #(.SMUT(`P_SMUT))
`elsif P_MUTSK
 #(.MUT_SK(`P_MUTSK))
`endif
 dut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(dv),.result(dr),.fault(df));
integer seed=`SEED,f,j,k,t0,lg=-1,ld=-1,bad=0,faults=0,nz=0,cg=0,cd=0,ec=0;
reg [767:0] qr[0:4095]; reg qf[0:4095];
reg [31:0] tie[0:7]; initial begin tie[0]=32'h0;tie[1]=32'h80000000;tie[2]=32'h3f800000;tie[3]=32'hbf800000;tie[4]=32'h7fc00000;tie[5]=32'hffc00000;tie[6]=32'h3f800000;tie[7]=32'h40000000; end
function [31:0] rnd(input integer mode); reg [31:0] r; begin r=$random(seed);
  if(mode==0) rnd={r[31],8'(8'd118+($unsigned(r[30:23])%20)),r[22:0]}; else if(mode==2) rnd=tie[r[2:0]];
  else if(mode==3) rnd={r[31],8'(8'd124+($unsigned(r[30:23])%4)),r[22:4],4'd0}; else rnd=r; end endfunction
task randin(input integer mode); begin for(j=0;j<24;j=j+1) begin mixes[j*32+:32]=rnd(mode); bases[j*32+:32]=rnd(mode); end
  for(j=0;j<3;j=j+1) scales[j*32+:32]=rnd(mode); end endtask
integer tl=0,now=0; always @(posedge clk) now<=now+1;
`ifdef DBG
always @(negedge clk) if(rst_n) begin if(dut.ov_i) $display("DBG ov_i now-tl %0d sage %0d sf %b",now-tl,dut.u.sage,dut.sf_i); if(dut.iv_o) $display("DBG iv_o now-tl %0d ird %b",now-tl,dut.ird_i); if(dut.u.capture_q) $display("DBG cap now-tl %0d sage %0d",now-tl,dut.u.sage); end
`endif
always @(negedge clk) if(rst_n) begin
  if(gv) begin if(lg<0) lg=now-tl; qr[cg]=gr; qf[cg]=gf; cg=cg+1; end
  if(dv) begin if(ld<0) ld=now-tl;
    if(cd>=cg) begin bad=bad+1; $display("DUT before gold run %0d",cd); end
    else begin if(qr[cd]!==dr||qf[cd]!==df) begin bad=bad+1; if(bad<6) $display("DIFF run %0d fault g%b d%b t=%0t\n g=%h\n d=%h",cd,qf[cd],df,$time,qr[cd][767:600],dr[767:600]); end end
    if(df) faults=faults+1; if(|dr) nz=nz+1; cd=cd+1; end
end
initial begin randin(0); repeat(6) @(negedge clk); #1 rst_n=1; repeat(4) @(negedge clk); #1;
  for(f=0;f<`NRUN;f=f+1) begin
    `ifdef GOOD
    randin(f%2==1?3:0);
`else
    randin(f%5==4?1:f%5==3?2:f%5==2?3:0);
`endif
 tl=now; launch=1; @(negedge clk); #1 launch=0; randin(1);
    for(k=0;k<1300;k=k+1) begin @(negedge clk); #1; end
  end
  $display("MEASURED gold launch->result_v %0d, dut %0d; dut result+1 emit; runs g %0d d %0d, nonzero %0d, faults %0d, bad %0d, EREADY %0d SKL %0d CAP %0d L %0d",lg,ld,cg,cd,nz,faults,bad,dut.u.u_tail.EREADY,dut.u.SKL,dut.u.CAP,dut.u.L);
  if(bad==0&&cd==`NRUN&&cg==`NRUN&&nz>0) $display("FSR_EQ PASS"); else $display("FSR_EQ FAIL");
  $finish; end
endmodule
