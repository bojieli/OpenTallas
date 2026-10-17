`timescale 1ns/1ps
// H-NETLIST A2P 2026-10-16: SU cross-quarter RF coherence bench for N_Q quarters (A2P half die: N_Q=2, SW + NW).
// DUT: N_Q REAL ot_hbm_su_static_qcore #(N_Q) (RF replica 64 banks x 4 words + reducer each).  Die model: the RF relay
// network, every reducer -> every replica over RF_RELAY registered stages (the die relay chains of red_rf_v/red_tag/
// red_x -> rf_wv/rf_wa/rf_wd slot w), as ot_hbm_su_static_top's network.
// Stimulus: every quarter's reducer gets random commands (all six ops); RF-writing scalars (tag[8]=1) name RF word
// tag[7:0] in banks owned by that quarter (bank % N_Q == q: no compile-time writer conflict).  The scoreboard records
// the actual scalar at the relay head.  After a quiet window every RF word is read back from EVERY replica (class 0
// broadcast read) and compared with the last scalar written to it; every source must have written.
// Mutants: -GQMUT=256 (qcore: last writer slot ignored), -GDROP=1 (route reducer 1 -> replica 0 missing): must FAIL.
module tb_hbm_su_rf_nq;
 parameter integer N_Q=2, RF_RELAY=4, QMUT=0, DROP=0, NCMD=3000;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [N_Q*54-1:0] rf_rd_cmd=0; reg [N_Q*74-1:0] red_cmd=0; reg [N_Q*128-1:0] sx=0; integer nz=0;
 wire [N_Q-1:0] red_sv,red_rf_v,fault; wire [N_Q*32-1:0] red_tag,red_x; wire [N_Q*128-1:0] bword;
 wire [40:0] rly_out [0:N_Q-1][0:N_Q-1];
 genvar w,d,q;
 for(w=0;w<N_Q;w=w+1)begin:g_src
  wire [40:0] head={red_rf_v[w],red_tag[w*32+:8],red_x[w*32+:32]};
  for(d=0;d<N_Q;d=d+1)begin:g_dst
   reg [40:0] st [0:RF_RELAY-1]; integer k;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)for(k=0;k<RF_RELAY;k=k+1)st[k]<=41'd0;
    else begin st[0]<=head;for(k=1;k<RF_RELAY;k=k+1)st[k]<=st[k-1]; end
   assign rly_out[w][d]={st[RF_RELAY-1][40]&&!(DROP!=0&&w==1&&d==0),st[RF_RELAY-1][39:0]};
  end
 end
 for(q=0;q<N_Q;q=q+1)begin:g_q
  wire [N_Q-1:0] wv; wire [N_Q*8-1:0] wa; wire [N_Q*32-1:0] wd;
  for(w=0;w<N_Q;w=w+1)begin:g_w
   assign wv[w]=rly_out[w][q][40]; assign wa[w*8+:8]=rly_out[w][q][39:32]; assign wd[w*32+:32]=rly_out[w][q][31:0];
  end
  ot_hbm_su_static_qcore #(.MUT(QMUT),.N_Q(N_Q)) u_core(.clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),.rst_n(rst_n),
   .rf_rd_cmd(rf_rd_cmd[q*54+:54]),.red_cmd(red_cmd[q*74+:74]),.rf_drain_cmd(2'b00),.slice_x(sx[q*128+:128]),
   .rf_wv(wv),.rf_wa(wa),.rf_wd(wd),.rf_bword(bword[q*128+:128]),.rf_bcmd(),.rf_dsec(),
   .red_sv(red_sv[q]),.red_tag(red_tag[q*32+:32]),.red_x(red_x[q*32+:32]),.red_rf_v(red_rf_v[q]),
   .rr_wv(1'b0),.rr_wa(5'd0),.rr_wd(256'd0),.sfu_x(32'd0),.fault(fault[q]));
 end
 reg [31:0] model [0:255]; reg written [0:255]; integer writes [0:N_Q-1];
 integer i,j,a,errors=0,checks=0,cycle=0;
 always @(negedge clk) if(rst_n) begin
  cycle=cycle+1;
  for(j=0;j<N_Q;j=j+1)if(red_rf_v[j])begin
   model[red_tag[j*32+:8]]=red_x[j*32+:32]; written[red_tag[j*32+:8]]=1; writes[j]=writes[j]+1; if(red_x[j*32+:32]!=0)nz=nz+1;
  end
 end
 initial begin
  for(i=0;i<256;i=i+1)begin model[i]=0; written[i]=0; end
  for(j=0;j<N_Q;j=j+1)writes[j]=0;
  repeat(4)@(posedge clk); #1 rst_n=1;
  for(i=0;i<NCMD;i=i+1)begin
   @(posedge clk); #1;
   red_cmd=0;
   for(j=0;j<N_Q*4;j=j+1)sx[j*32+:32]={2'b00,6'($urandom%32+16),24'($urandom)};   // finite FP32
   for(j=0;j<N_Q;j=j+1)if(($random&1)==0)begin
    a=($urandom%(64/N_Q))*N_Q+j;                 // bank owned by quarter j
    red_cmd[j*74+73]=1; red_cmd[j*74+70+:3]=$urandom%6; red_cmd[j*74+60+:10]=$urandom%16;
    red_cmd[j*74+50+:10]=$urandom%16; red_cmd[j*74+40+:10]=$urandom%16;
    red_cmd[j*74+8+:32]={23'd0,1'b1,2'($urandom%4),6'(a)};   // tag[8]=1: write RF word {row, bank}
    red_cmd[j*74+7]=0; red_cmd[j*74+0+:7]=$urandom%64;
   end
  end
  @(posedge clk); #1 red_cmd=0;
  repeat(40+RF_RELAY)@(posedge clk);
  for(a=0;a<256;a=a+1)begin
   #1; for(j=0;j<N_Q;j=j+1)rf_rd_cmd[j*54+:9]={1'b1,8'(a)};
   repeat(5)@(posedge clk); #1;
   if(written[a])for(j=0;j<N_Q;j=j+1)begin
    checks=checks+1;
    if(bword[j*128+:32]!==model[a])begin errors=errors+1; if(errors<8)$display("MISMATCH replica%0d word%0d got %h exp %h",j,a,bword[j*128+:32],model[a]); end
   end
  end
  if(nz<100)begin errors=errors+1; $display("too few nonzero scalars %0d",nz); end
  for(j=0;j<N_Q;j=j+1)if(writes[j]==0)begin errors=errors+1; $display("source %0d never wrote",j); end
  $display("SU_RF_NQ N_Q=%0d checks=%0d errors=%0d nonzero_scalars=%0d writes0=%0d writes1=%0d",N_Q,checks,errors,nz,writes[0],writes[1]);
  if(errors||checks==0)$fatal(1,"SU_RF_NQ FAIL errors=%0d",errors);
  $display("SU_RF_NQ PASS N_Q=%0d",N_Q); $finish;
 end
endmodule
