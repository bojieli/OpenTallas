`timescale 1ns/1ps
// Q-FUNC: three qfd_res_ser_static bands feeding the static VM result-face rule (ot_qfd_sp_vector_memory_bv
// STATIC_SCHEDULE=1: at most one valid band beat per cycle, every beat taken, `end` lands one burst). Random bursts
// (random we masks, rows < 2^20, data) at random spacing >= 24 cycles; checks the exact beat sequence (burst, band,
// slot order), each beat's exact cycle (capture edge + 2 + D + 8 b + j), one landing per burst on its fixed cycle, and
// no fault. +SPACING_MIN=23 is the schedule-violation negative (fault MUST rise); MUT=1 swaps slots 0/1 (MUST FAIL).
module tb_res_ser_static;
parameter integer NB=3, D=2, MUT=0, BURSTS=400;
reg ck=0,rst_n=0; always #1 ck=~ck;
reg me_en=1; reg [4424:0] rq [0:NB-1];
wire [550:0] rb [0:NB-1]; wire [NB-1:0] f;
genvar b;
generate for(b=0;b<NB;b=b+1) begin:g
  qfd_res_ser_static #(.BAND(b),.NB(NB),.D(D),.MUT(MUT)) u (.ck(ck),.rst_n(rst_n),.me_en(me_en),.rq(rq[b]),.rb(rb[b]),.fault(f[b]));
end endgenerate
// expected beats: (cycle, row, mask, data, end)
localparam integer MAXE=BURSTS*NB*8+BURSTS;
longint e_cyc[0:MAXE-1]; reg [19:0] e_row[0:MAXE-1]; reg [15:0] e_mask[0:MAXE-1]; reg [511:0] e_data[0:MAXE-1]; reg e_end[0:MAXE-1]; reg e_nul[0:MAXE-1];
integer ne=0, ge=0, errors=0, lands=0, multi=0, spmin=24;
longint cyc=0;
always @(posedge ck) cyc<=cyc+1;
// observe the merged face exactly as the static VM merge does
always @(negedge ck) if(rst_n) begin : mon
  integer n,k; reg [550:0] m; n=0; m=0;
  for(k=0;k<NB;k=k+1) if(rb[k][550]) begin n=n+1; m=m|rb[k]; end
  if(n>1) begin multi=multi+1; errors=errors+1; end
  if(n>=1) begin
    if(ge>=ne) begin errors=errors+1; if(errors<8)$display("EXTRA beat cyc=%0d",cyc); end
    else begin
      if(e_cyc[ge]!=cyc || m[549]!==e_end[ge] || m[548]!==e_nul[ge] || (!e_nul[ge] && (m[547:528]!==e_row[ge] || m[527:512]!==e_mask[ge] || m[511:0]!==e_data[ge]))) begin
        errors=errors+1; if(errors<8)$display("MISMATCH beat %0d cyc=%0d exp_cyc=%0d row=%h exp=%h end=%b exp=%b",ge,cyc,e_cyc[ge],m[547:528],e_row[ge],m[549],e_end[ge]);
      end
      if(m[549]) lands=lands+1;
      ge=ge+1;
    end
  end
end
integer i,k,s,sp; reg [7:0] we; reg [23:0] row; longint capc;
initial begin
  if($value$plusargs("SPACING_MIN=%d",spmin)) $display("SPACING_MIN %0d",spmin);
  for(k=0;k<NB;k=k+1) rq[k]=0;
  repeat(4)@(negedge ck); rst_n=1; repeat(4)@(negedge ck);
  for(i=0;i<BURSTS;i=i+1) begin
    capc=cyc; // the posedge that samples ov is cycle capc -> beats decoded at capc+1+D+8b+j, sampled at capc+2+D+8b+j
    for(k=0;k<NB;k=k+1) begin
      we=$urandom; if(i%17==0) we=0;
      for(s=0;s<8;s=s+1) begin
        row=$urandom%(1<<20);
        rq[k][552*s +: 552]={row, 16'($urandom), {16{32'($urandom)}}};
        if(we[s]) begin
          e_cyc[ne]=capc+2+D+8*k+s; e_row[ne]=row[19:0]; e_mask[ne]=rq[k][552*s+512 +: 16]; e_data[ne]=rq[k][552*s +: 512];
          e_end[ne]=(k==NB-1&&s==7); e_nul[ne]=0; ne=ne+1;
        end else if(k==NB-1&&s==7) begin
          e_cyc[ne]=capc+2+D+8*k+s; e_end[ne]=1; e_nul[ne]=1; ne=ne+1;
        end
      end
      rq[k][4423:4416]=we; rq[k][4424]=1;
    end
    @(negedge ck); for(k=0;k<NB;k=k+1) rq[k][4424]=0;
    sp=spmin+($urandom%17); repeat(sp-1)@(negedge ck);
  end
  repeat(60)@(negedge ck);
  if(spmin<8*NB) begin
    if(|f) $display("PASS res_ser_static_negative schedule fault raised at spacing %0d",spmin);
    else $display("FAIL res_ser_static_negative no fault at spacing %0d",spmin);
  end else begin
    if(|f) begin errors=errors+1; $display("FAULT %b",f); end
    if(ge!=ne) begin errors=errors+1; $display("COUNT got %0d beats expected %0d",ge,ne); end
    if(lands!=BURSTS) begin errors=errors+1; $display("LANDS %0d expected %0d",lands,BURSTS); end
    if(errors) $display("FAIL res_ser_static errors=%0d multi=%0d beats=%0d/%0d lands=%0d",errors,multi,ge,ne,lands);
    else $display("PASS res_ser_static bursts=%0d beats=%0d lands=%0d exact cycles (capture+2+D+8b+j), one band per cycle, no credits",BURSTS,ne,lands);
  end
  $finish;
end
endmodule
