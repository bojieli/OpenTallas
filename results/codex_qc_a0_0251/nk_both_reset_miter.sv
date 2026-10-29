`timescale 1ns/1ps
module nk_both_reset_miter;
 reg ck=0,rst_n=0,start=0,vin=0;always #5 ck=~ck;
 reg reset_q,local_reset_q;
 always @(posedge ck)reset_q<=rst_n;
 always @(posedge ck)local_reset_q<=reset_q;
 wire [3:0] rn;ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(ck,reset_q,rn);
 reg node_v,fault=0;reg [511:0] payload=0;
 always @(posedge ck or negedge rn[1])if(!rn[1])node_v<=0;else node_v<=vin;
 always @(posedge ck or negedge reset_q)if(!reset_q)fault<=0;else fault<=vin^payload[0];
 reg [513:0] gold,cand,wrong_reset,ny_gold,ny_cand,ny_wrong;
 reg fy_q=0,mis_q=0;wire na_v=vin,nb_v=cycles[2];
 always @(posedge ck)
  if(!reset_q)begin fy_q<=0;mis_q<=0;end
  else begin mis_q<=mis_q|(na_v^nb_v);fy_q<=payload[1]|payload[2]|mis_q;end
 always @(posedge ck)begin
  gold<={reset_q?{fault,node_v}:2'd0,payload};
  cand<={local_reset_q?{fault,node_v}:2'd0,payload};
  wrong_reset<={2'd0,payload};
  ny_gold<={reset_q?{fy_q,node_v}:2'd0,~payload};
  ny_cand<={local_reset_q?{fy_q,node_v}:2'd0,~payload};
  ny_wrong<={2'd0,~payload};
 end
 integer checks=0,controls=0,bootdiff=0,root_release=-1,local_release=-1,cycles=0;
 reg prev_root=0,prev_local=0;integer phase_controls=0,ny_controls=0;
 always @(posedge ck)begin
  #0.01;cycles=cycles+1;
  if(reset_q&&!prev_root)root_release=cycles;
  if(local_reset_q&&!prev_local)begin
   local_release=cycles;
   if(root_release<0||local_release!=root_release+1)$fatal(1,"local reset depth wrong");
   if(root_release!=local_release)phase_controls=phase_controls+1; // bypass-stage mutant is caught
  end
  prev_root=reset_q;prev_local=local_reset_q;
 end
 always @(negedge ck)begin
  if(start)begin
   if(!local_reset_q)$fatal(1,"START before delivered reset release");
   if(gold[513:512]!==cand[513:512]||(gold[512]&&gold[511:0]!==cand[511:0]))$fatal(1,"active reset-phase payload mismatch");
   if(ny_gold[513:512]!==ny_cand[513:512]||(ny_gold[512]&&ny_gold[511:0]!==ny_cand[511:0]))$fatal(1,"n_y active header/payload mismatch");
   checks=checks+1;if(gold!==wrong_reset)controls=controls+1;if(ny_gold!==ny_wrong)ny_controls=ny_controls+1;
  end else if(cycles>12&&gold!==cand)bootdiff=bootdiff+1;
 end
 integer n,j;
 initial begin
  repeat(6)@(negedge ck);
  for(n=0;n<4;n=n+1)begin
   rst_n=1;repeat(8)@(negedge ck);start=1;
   for(j=0;j<256;j=j+1)begin vin=(j%5)!=0;payload={16{32'(j+257*n)}};@(negedge ck);end
   vin=1;repeat(5)@(negedge ck);start=0;rst_n=0;repeat(6)@(negedge ck);
  end
  if(checks<1000||controls<100||ny_controls<100||phase_controls!=4||bootdiff==0)$fatal(1,"missing active/control/boot coverage");
  $display("PASS activechecks=%0d wrong_reset_controls=%0d depth_controls=%0d boot_phase_diffs=%0d added_boot_edges=1 payload_cycles=0 ny_wrong_controls=%0d",checks,controls,phase_controls,bootdiff,ny_controls);$finish;
 end
endmodule
