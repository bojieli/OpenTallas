`timescale 1ps/1fs
module tb_pdsk_repair;
reg ck=0,rs=0;always #416.5 ck=~ck;
reg[3:0]sid=0;reg[4:0]pv[0:1];reg[159:0]pd[0:1];wire[1:0]fault;wire[1:0]xv;wire[7:0]xi[0:1];wire[31:0]xs[0:1];
for(genvar g=0;g<2;g=g+1)begin:G
 ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(g==0?15'o01234:15'o00234),.QDELAYS(128'd0))u(
 .clk(ck),.rst_n(rs),.sid(sid),.dl_ev(1'b0),.dl_e(1075'd0),.dl_wv(1'b0),.dl_w(1075'd0),.dl_vv(1'b0),.dl_vb(275'd0),
 .lo_v(5'd0),.lo_d(1280'd0),.p_v(pv[g]),.p_d(pd[g]),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),
 .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.x_sv(xv[g]),.x_si(xi[g]),.x_s(xs[g]),.fault(fault[g]));
end
reg[31:0]genuine[0:79];integer cyc=0,phase=0,errors=0,checks=0,cohort=0,counts[0:1],first[0:1],oldactual=0,wrongsel=0,wrongdate=0;
integer dt_old[0:4],dt_new[0:4],depth[0:4],oldarrival[0:4];reg[31:0]captured[0:1][0:4];
always @(posedge ck)begin #2;cyc=cyc+1;
 if(phase)begin
  if(!oldactual&&!wrongsel&&xv[0]!==xv[1])begin errors=errors+1;$display("MISMATCH_VALID cycle%0d",cyc);end
  for(integer g=0;g<2;g=g+1)if(xv[g])begin
   if(first[g]<0)first[g]=cyc;
   if(counts[g]>=5||xi[g]!==8'(counts[g])||xs[g]!==genuine[5*int'(sid)+counts[g]])begin
    errors=errors+1;$display("NX_VALUE actor%0d sid%0d index%0d got%08x want%08x",g,sid,xi[g],xs[g],genuine[5*int'(sid)+counts[g]]);
   end
   if(counts[g]<5)captured[g][counts[g]]=xs[g];counts[g]=counts[g]+1;checks=checks+1;
  end
  if(!oldactual&&!wrongsel&&xv[0]&&xv[1]&&(xi[0]!==xi[1]||xs[0]!==xs[1]))begin errors=errors+1;$display("LOCKSTEP_DATA");end
 end
end
 task tick(input integer n);repeat(n)begin @(posedge ck);#5;end endtask
initial begin
oldactual=$test$plusargs("old_actual_calendar");wrongsel=$test$plusargs("wrong_selector");wrongdate=$test$plusargs("wrong_date");
$readmemh("partial.memh",genuine);depth[0]=4;depth[1]=3;depth[2]=2;depth[3]=1;depth[4]=0;
for(cohort=0;cohort<2;cohort=cohort+1)begin
 phase=0;rs=0;pv[0]=0;pv[1]=0;pd[0]=0;pd[1]=0;sid=cohort==0?4'd0:4'd5;tick(64);rs=1;tick(64);
 counts[0]=0;counts[1]=0;first[0]=-1;first[1]=-1;
 // Legal reference old-deskew schedule and legal selected candidate input
 // schedule align at the same semantic partial-set event100. They are local
 // XR input bookings,not a claim that old tied physical issuer is executable.
 for(integer k=0;k<5;k=k+1)begin dt_old[k]=100-depth[k];dt_new[k]=100-(k==3?0:depth[k]);end
 // Original current native issuer20..24 + actual dn/up + current producer116.
 if(cohort==0)begin oldarrival[0]=147;oldarrival[1]=142;oldarrival[2]=159;oldarrival[3]=161;oldarrival[4]=175;end
 else begin oldarrival[0]=147;oldarrival[1]=142;oldarrival[2]=161;oldarrival[3]=163;oldarrival[4]=175;end
 if(oldactual)for(integer k=0;k<5;k=k+1)dt_old[k]=oldarrival[k];
 if(wrongsel)for(integer k=0;k<5;k=k+1)dt_old[k]=dt_new[k];
 if(wrongdate)dt_new[3]=dt_new[3]+1;
 phase=1;
 for(integer t=0;t<220;t=t+1)begin
  pv[0]=0;pv[1]=0;
  for(integer k=0;k<5;k=k+1)begin
   pd[0][32*k+:32]=genuine[5*int'(sid)+k];pd[1][32*k+:32]=genuine[5*int'(sid)+k];
   if(t==dt_old[k])pv[0][k]=1;if(t==dt_new[k])pv[1][k]=1;
  end
  tick(1);
 end
 pv[0]=0;pv[1]=0;tick(16);
 if(fault||counts[0]!=5||counts[1]!=5)begin errors=errors+1;$display("COLLECTOR_FAULT sid%0d fault%b count%0d/%0d",sid,fault,counts[0],counts[1]);end
 if(!oldactual&&!wrongsel)begin
  for(integer k=0;k<5;k=k+1)if(captured[0][k]!==captured[1][k])errors=errors+1;
  if(first[0]!=first[1])errors=errors+1;
 end
 $display("PDSK_REPAIR sid%0d reference_first%0d candidate_first%0d captured%0d/%0d faults%b",sid,first[0],first[1],counts[0],counts[1],fault);
end
$display("PDSK_REPAIR_%s checks%0d errors%0d clock833 old_actual%0d wrong_selector%0d wrong_date%0d",errors==0?"PASS":"FAIL",checks,errors,oldactual,wrongsel,wrongdate);
if(errors)$fatal(1,"current actual XR collector schedule/selector");$finish;
end
endmodule
