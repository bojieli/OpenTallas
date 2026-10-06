`timescale 1ps/1fs
module tb_vm_station_return_bridge;
 reg clk=0,por_n=0,quiesce=0,in_v=0;
 wire in_r,release_pulse,child_drained,child_paused,child_fault;
 reg [2062:0] payload=0;reg [191:0] owner=0;
 wire [2:0] out_v;reg [2:0] out_r=0,child_ACK_v=0;
 wire [3*2063-1:0] out_data;wire [3*192-1:0] out_owner;
 reg [3*192-1:0] child_ACK_owner=0;
 reg [72:0] frame=0;reg ACK_r=0,extra_release=0;
 wire ACK_v,empty,fault;wire [191:0] ACK_owner;wire [72:0] ACK_frame;
 wire forwarded_clk;
 always #416.666 clk=~clk;
 ot_hbm_native_station #(.MODE(1),.ENABLE(1),.W(2063),.IW(2063),.NI(1),.NO(3)) child(
  .fclk_i(clk),.rst_n({4{por_n}}),.i_v(1'b0),.i_d(2063'b0),.fclk_o(forwarded_clk),.o_v(),.o_d(),
  .quiesce(quiesce),.in_v(in_v),.in_r(in_r),.in_data(payload),.in_owner(owner),
  .out_v(out_v),.out_r(out_r),.out_data(out_data),.out_owner(out_owner),
  .ACK_v(child_ACK_v),.ACK_owner(child_ACK_owner),.source_release(release_pulse),
  .drained(child_drained),.paused(child_paused),.fault(child_fault));
 ot_hbm_vm_station_return_bridge #(.ENABLE(1)) dut(
  .clk_sm(clk),.por_n(por_n),.station_release(release_pulse|extra_release),
  .station_owner(out_owner[191:0]),.held_frame(frame),.ACK_v(ACK_v),.ACK_r(ACK_r),
  .ACK_owner(ACK_owner),.ACK_frame(ACK_frame),.empty(empty),.fault(fault));
 integer checks=0,sends=0,receipts=0,events=0;
 task check(input bit ok);begin if(!ok)$fatal(1,"return bridge check%0d",checks);checks++;end endtask
 always @(posedge clk)if(por_n)begin
  for(integer k=0;k<3;k++)if(out_v[k]&&out_r[k])begin
   if(out_data[k*2063+:2063]!==payload||out_owner[k*192+:192]!==owner)$fatal(1,"native child payload/owner");sends++;
  end
  if(release_pulse)events++;
  if(ACK_v&&ACK_r)receipts++;
 end
 task cold;begin
  por_n=0;in_v=0;out_r=0;child_ACK_v=0;ACK_r=0;extra_release=0;quiesce=0;
  repeat(3)@(negedge clk);por_n=1;repeat(2)@(negedge clk);
 end endtask
 task transaction(input bit inject_empty_CE);begin
  in_v=1;do @(posedge clk);while(!in_r);@(negedge clk);in_v=0;
  wait(out_v==3'b111);out_r=7;@(posedge clk);@(negedge clk);out_r=0;
  for(integer k=0;k<3;k++)child_ACK_owner[k*192+:192]=owner;
  child_ACK_v=7;@(posedge clk);@(negedge clk);child_ACK_v=0;quiesce=1;
  wait(release_pulse);@(negedge clk);
  if(inject_empty_CE)dut.on.code[0][0]=~dut.on.code[0][0];
  wait(ACK_v);repeat(3)begin @(negedge clk);
   check(!empty&&!fault&&!child_fault&&ACK_frame===frame&&ACK_owner===owner);
  end
  check(child_drained&&out_v==0);
 end endtask
 initial begin
  frame={20'hfffff,17'h1ffff,4'hb,32'h81abcdef};owner={6{32'hd1fedcba}};payload={64{32'h7f123456}};
  cold;transaction(1);
  check(events==1&&receipts==0&&sends==3);
  ACK_r=1;@(posedge clk);@(negedge clk);ACK_r=0;
  check(empty&&!ACK_v&&!fault&&receipts==1);
  // Real second child completion; uncorrectable receipt must refuse any ACK.
  quiesce=0;transaction(0);
  dut.on.code[1][0]=~dut.on.code[1][0];dut.on.code[1][1]=~dut.on.code[1][1];ACK_r=1;
  repeat(3)begin @(negedge clk);check(fault&&!ACK_v&&!empty&&receipts==1);end
  // Duplicate readyless receipt quarantines already owed identity, never overwrites it.
  cold;transaction(0);extra_release=1;#1;check(fault&&!ACK_v&&!empty);
  @(posedge clk);@(negedge clk);extra_release=0;ACK_r=1;
  check(fault&&!ACK_v&&!empty&&ACK_frame===frame&&ACK_owner===owner);
  $display("PASS_VM_STATION_RETURN_BRIDGE checks=%0d sends=%0d native_events=%0d parent_receipts=%0d NO3=1 emptyCEarrival=1 warmdebt=1 UE_no_ACK=1 collision_quarantined=1",checks,sends,events,receipts);$finish;
 end
endmodule
