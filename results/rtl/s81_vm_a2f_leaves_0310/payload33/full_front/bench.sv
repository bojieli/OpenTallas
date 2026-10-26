`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;
 reg [52:0] v=0;reg [741:0] row=0;reg [847:0] mask=0;reg [423:0] tag=0;reg [27135:0] data=0;
 wire [127:0] av,fv;wire [1791:0] ar,fr;wire [1023:0] at,ft;wire [511:0] am,fm;wire [16383:0] ad,fd;
 wire [15:0] af,ff;
 s81_a2_controlled ref_a2(
  .ck_header(ck),.ck_payload({4{ck}}),.ck_control({16{ck}}),.ck_meta({16{ck}}),.ck_fault({16{ck}}),.ck_data({128{ck}}),
  .rst_header_n(rst),.rst_payload_n({4{rst}}),.rst_control_n({16{rst}}),.rst_meta_n({16{rst}}),.rst_fault_n({16{rst}}),
  .rst_data_n({128{rst}}),.i_v(v),.i_row(row),.i_tag(tag),.i_mask(mask),.i_data(data),
  .o_slice_v(av),.o_slice_row(ar),.o_slice_tag(at),.o_mask(am),.o_data(ad),.o_fault(af));
 s81_a2f_controlled_split4m_payload33 dut(
  .ck_header(ck),.ck_payload({16{ck}}),.ck_control({4{ck}}),.ck_meta({28{ck}}),.ck_fault({4{ck}}),.ck_data({128{ck}}),
  .rst_header_n(rst),.rst_payload_n({16{rst}}),.rst_control_n({4{rst}}),.rst_meta_n({28{rst}}),.rst_fault_n({4{rst}}),
  .rst_data_n({128{rst}}),.i_v(v),.i_row(row),.i_tag(tag),.i_mask(mask),.i_data(data),
  .o_slice_v(fv),.o_slice_row(fr),.o_slice_tag(ft),.o_mask(fm),.o_data(fd),.o_fault(ff));
 integer cycle,s,b,k,seed,seed0,phase,checked=0,writes=0,faulty=0,nv;
 integer cnt[0:31];reg [2:0] occ[0:31];
 reg [13:0] r;reg [4:0] bank;
 task tick;begin @(posedge ck);#1;end endtask
 task compare;begin
  if(fv!==av)$fatal(1,"MISMATCH_V cycle%0d",cycle);
  if(fr!==ar)$fatal(1,"MISMATCH_ROW cycle%0d",cycle);
  if(ft!==at)$fatal(1,"MISMATCH_TAG cycle%0d",cycle);
  if(fm!==am)$fatal(1,"MISMATCH_MASK cycle%0d",cycle);
  if(fd!==ad)$fatal(1,"MISMATCH_DATA cycle%0d",cycle);
  if(ff!==af)$fatal(1,"MISMATCH_FAULT cycle%0d %h %h",cycle,ff,af);
  checked=checked+1;if(av!==0)nv=nv+1;if(af!==0)faulty=faulty+1;
 end endtask
 task stim(input integer legal);begin
  v=0;row=0;mask=0;tag=0;data=0;
  // legal = lane l (ascending-source prefix count) of a bank drains at t+l: <= 3 per bank and drain edges unique
  for(b=0;b<32;b=b+1)begin cnt[b]=0;occ[b]=occ[b]>>1;end
  for(s=0;s<53;s=s+1)if($random(seed)%4!=0)begin
   r=$random(seed);bank=r[4:0]^{r[7:5],2'b00};
   if(legal && (cnt[bank]>=3 || occ[bank][cnt[bank]]))begin end
   else begin
    if(cnt[bank]<3)occ[bank][cnt[bank]]=1'b1;
    cnt[bank]=cnt[bank]+1;v[s]=1;row[14*s+:14]=r;tag[8*s+:8]=$random(seed);mask[16*s+:16]=$random(seed);
    for(k=0;k<16;k=k+1)data[512*s+32*k+:32]=$random(seed);
    writes=writes+1;
   end
  end
 end endtask
 initial begin
  seed=1;if($value$plusargs("seed=%d",seed))begin end seed0=seed;
  nv=0;cycle=0;for(b=0;b<32;b=b+1)occ[b]=0;
  repeat(7)begin tick();compare();end
  @(negedge ck);rst=1;
  for(cycle=0;cycle<120;cycle=cycle+1)begin @(negedge ck);if(cycle<100)stim(1);else begin v=0; end tick();compare();end
  if(af!==0)$fatal(1,"LEGAL_PHASE_FAULTED %h",af);
  for(cycle=120;cycle<150;cycle=cycle+1)begin @(negedge ck);if(cycle<135)stim(0);else v=0;tick();compare();end
  if(af===0)$fatal(1,"BURST_PHASE_NO_FAULT");
  @(negedge ck);rst=0;v=0;
  for(cycle=150;cycle<160;cycle=cycle+1)begin tick();compare();end
  @(negedge ck);rst=1;for(b=0;b<32;b=b+1)occ[b]=0;
  for(cycle=160;cycle<260;cycle=cycle+1)begin @(negedge ck);if(cycle<240)stim(1);else v=0;tick();compare();end
  if(af!==0)$fatal(1,"RESTART_PHASE_FAULTED %h",af);
  $display("PASS a2f==a2 seed%0d edges%0d writes%0d valid_edges%0d fault_edges%0d",seed0,checked,writes,nv,faulty);
  $finish;
 end
endmodule
