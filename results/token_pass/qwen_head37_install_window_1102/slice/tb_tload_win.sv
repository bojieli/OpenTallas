`timescale 1ns/1fs
// TOK-QW-4 11-02: stage37 HEAD table-install window vs stage36 traffic, MEASURED on the main RTL
// qfd_dv_slice_tload #(HEAD_STAGE37 1) (native C0/LOCAL0/WE34 profile) + qfd_dv_table_rom_loader + the genuine rank0
// HEAD37 table ROMs (48 viamaps), all 12 slices. treq = the registered CALR LOCAL4 lane {v, stage6, user2}.
//  SWEEP: treq{36,u} at E0, treq{37,u'} at E0+d, d = 80..100 (same and cross user) -> min fault-free spacing.
//  BOOT : all 4 users x stages 1..37 back-to-back at the measured spacing -> 0 faults, write counts.
//  COLL : stream table write (s_we) injected at offsets around the stage37 write window -> fault iff inside.
module tb_tload_win;
reg ck=0; always #0.4165 ck=~ck;
reg rst_n=0; reg [8:0] treq=0; reg s_we=0;
localparam integer NS=12;
wire [NS-1:0] we,bz,dn,ft;
genvar g;
generate for(g=0;g<NS;g=g+1)begin:sl
 wire [1:0] k; wire [23:0] a; wire [1023:0] x;
 qfd_dv_slice_tload #(.SLICE(g),.HEAD_STAGE37(1)) t(.ck(ck),.rst_n(rst_n),.treq(treq),.s_we(s_we),.s_kind(2'd1),
   .s_addr(24'd0),.s_data(1024'd0),.tw_we(we[g]),.tw_kind(k),.tw_addr(a),.tw_data(x),.busy(bz[g]),.done(dn[g]),.fault(ft[g]));
end endgenerate
integer cyc=0; always @(posedge ck) cyc<=cyc+1;
integer nw[0:NS-1], fw[0:NS-1], lw[0:NS-1], doneat[0:NS-1]; integer mark=0;
always @(negedge ck) for(int i=0;i<NS;i++) begin
  if(we[i] && cyc>=mark) begin if(fw[i]<0) fw[i]=cyc; lw[i]=cyc; nw[i]=nw[i]+1; end
  if(dn[i] && cyc>=mark && doneat[i]<0) doneat[i]=cyc;
end
task automatic clr(input integer m); mark=m; for(int i=0;i<NS;i++) begin nw[i]=0; fw[i]=-1; lw[i]=-1; doneat[i]=-1; end endtask
task automatic rst(); @(negedge ck); rst_n=0; treq=0; s_we=0; repeat(4) @(negedge ck); rst_n=1; repeat(6) @(negedge ck); endtask
task automatic req(input integer st, input integer u); treq={1'b1,6'(st),2'(u)}; @(negedge ck); treq=0; endtask
// treq goes high at the negedge before posedge 'cyc'; edge E = value of cyc at the sampling posedge
function automatic integer fm(); fm=0; for(int i=0;i<NS;i++) if(ft[i]) fm|=(1<<i); endfunction
integer dmin=1000,d,u2,e0,e1,o,s,uu,tot[0:NS-1],nload;
initial begin
 // ---- SWEEP
 for(u2=0;u2<2;u2++) for(d=80;d<=100;d++) begin
  rst(); e0=cyc+1; req(36,0); repeat(d-1) @(negedge ck); e1=cyc+1; clr(e1); req(37,u2);
  repeat(140) @(negedge ck);
  $display("SWEEP prev 36u0 next 37u%0d d %0d faultmask %03x w37 s0 %0d s11 %0d first %0d last %0d done %0d (rel next)",
           u2,d,fm(),nw[0],nw[11],fw[0]-e1,lw[0]-e1,doneat[0]-e1);
  if(fm()!=0) dmin=1000; else if(dmin==1000) dmin=d;
 end
 // ---- single load occupancy for each stage (busy high span)
 for(s=35;s<=37;s++) begin
  rst(); e0=cyc+1; clr(e0); req(s,1); repeat(140) @(negedge ck);
  $display("SINGLE stage %0d u1 faultmask %03x writes s0 %0d s5 %0d s11 %0d first %0d last %0d done %0d",s,fm(),nw[0],nw[5],nw[11],fw[0]-e0,lw[0]-e0,doneat[0]-e0);
 end
 // ---- COLL: s_we pulse at offset o after the stage37 treq edge (alone, no prior load)
 for(o=0;o<=100;o++) begin
  rst(); e0=cyc+1; clr(e0); req(37,2);
  if(o>1) repeat(o-1) @(negedge ck);
  if(o>0) begin s_we=1; @(negedge ck); s_we=0; end
  else begin end
  repeat(140) @(negedge ck);
  $display("COLL ofs %0d faultmask %03x w37 s0 %0d s11 %0d",o,fm(),nw[0],nw[11]);
 end
 // ---- BOOT: 4 users x stages 1..37 at spacing dmin (from SWEEP) and dmin-1
 for(int sp=dmin-1; sp<=dmin; sp++) begin
  rst(); e0=cyc+1; clr(e0); nload=0;
  for(uu=0;uu<4;uu++) for(s=1;s<=37;s++) begin req(s,uu); nload++; repeat(sp-1) @(negedge ck); end
  repeat(140) @(negedge ck);
  $display("BOOT spacing %0d loads %0d faultmask %03x writes s0 %0d s1 %0d s2 %0d s11 %0d span_last %0d",sp,nload,fm(),nw[0],nw[1],nw[2],nw[11],lw[0]-e0);
 end
 $display("TB_DONE dmin %0d",dmin);
 $finish;
end
endmodule
