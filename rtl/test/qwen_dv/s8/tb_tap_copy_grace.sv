`timescale 1ns/1ps
module tap_copy_grace_case #(parameter D=4,K=2)(input ck,rst,output reg done=0);
localparam W=1567,NC=66,AW=$clog2(D);
wire root,regional;wire[2:0]wrst,rrst;
ot_pl_pad #(.W(1),.N(1)) rootpad(ck,rst,root);
ot_pl_pad #(.W(1),.N(8)) regionpad(ck,root,regional);
genvar g;
generate for(g=0;g<3;g=g+1)begin:gr
 ot_pl_land_rst_copy #(.ID(g)) wc(ck,regional,wrst[g]);
 ot_pl_land_rst_copy #(.ID(g+3)) rc(ck,regional,rrst[g]);
end endgenerate
reg[4:0] original=5'b10101;
reg[3:0] copies[0:4];
reg[31:0] lfsr=32'h51e7a902;
reg[W-1:0] backdrop=0;
reg[W-1:0] olddata,newdata;
integer j,k,edgecount=0,checked=0,clears=0,firstvalid=-1;
initial begin
 for(j=0;j<5;j=j+1)copies[j]=(j%2)?4'b0101:4'b1010;
 #1;
 // Causal negative: exposing independent cold Q without the existing landing
 // grace gives a real binary mismatch, even though all copies share future D.
 if(copies[0]=={4{original[0]}})$fatal(1,"cold negative failed to diverge");
 $display("TAP_GRACE_COLD_NEGATIVE D%0d raw_binary_aliases_differ_before_capture",D);
end
always @*begin
 olddata=backdrop;newdata=backdrop;
 for(integer f=0;f<5;f=f+1)for(integer a=0;a<12;a=a+1)begin
  olddata[479+12*f+a]=original[f];
  newdata[479+12*f+a]=copies[f][a/3];
 end
end
always @(posedge ck)begin
 edgecount=edgecount+1;
 lfsr<={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
 original<=lfsr[4:0];
 for(integer f=0;f<5;f=f+1)copies[f]<={4{lfsr[f]}};
 for(integer b=0;b<W;b=b+1)backdrop[b]<=lfsr[b%32];
end
wire[D*W-1:0]ob,nb;wire[D*(AW+1)-1:0]oe,ne;
wire[D*NC-1:0]ov,nv;wire[W-1:0]oo,no;
ot_pl_land_n32_split_w #(.W(W),.D(D)) ow(ck,wrst,olddata,ob,oe,ov);
ot_pl_land_n32_split_w #(.W(W),.D(D)) nw(ck,wrst,newdata,nb,ne,nv);
ot_pl_land_split_r #(.W(W),.D(D),.K(K)) ordr(ck,rrst,ob,oe,ov,oo);
ot_pl_land_split_r #(.W(W),.D(D),.K(K)) nrdr(ck,rrst,nb,ne,nv,no);
always @(posedge ck)begin
 // The existing reset epoch must actually clear reader warmth and writer valid.
 // No claim is made about pre-reset raw hardware state or full-parent startup.
 if(ow.g_chunk[0].u_local.rq===1'b0)clears=clears+1;
 #1;
 if(clears>0)begin
  if(oo!==no)$fatal(1,"TAP_GRACE_EXPOSED D%0d edge%0d",D,edgecount);
  if(ordr.g_chunk[0].u_local.warm===1'b1 && ordr.g_chunk[0].u_local.selected_valid===1'b1)begin
   if(edgecount<2)$fatal(1,"TAP_GRACE_NO_CAPTURE");
   if(firstvalid<0)firstvalid=edgecount;
   checked=checked+1;
  end
 end
 if(edgecount==128)begin
  if(clears<1||checked<30||firstvalid<0)$fatal(1,"TAP_GRACE_MISSING_COVERAGE");
  $display("TAP_GRACE_PASS D%0d K%0d independent_binary_coldcopies full1567 actual_n32_split writer_reader checks%0d resetclears%0d firstvalid%0d",D,K,checked,clears,firstvalid);done=1;
 end
end
endmodule
module tb_tap_copy_grace;
reg ck=0;always #5 ck=~ck;
reg rst=0;integer cyc=0;
// Existing selected parent TB waveform: low until cyc16, no extra quiet interval.
always @(negedge ck)begin cyc=cyc+1;if(cyc==16)rst=1;end
wire a,b;
tap_copy_grace_case #(.D(4),.K(2)) maincase(ck,rst,a);
tap_copy_grace_case #(.D(8),.K(4)) fallbackcase(ck,rst,b);
initial begin wait(a&&b);$display("TAP_COPY_GRACE_BOTH_PASS conditional_existing_parent_reset_only");$finish;end
endmodule
