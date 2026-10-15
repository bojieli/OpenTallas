`timescale 1ns/1ps
`default_nettype none
module tb_smh_calendar_pair_static;
 parameter integer MUT_PC=0,MUT_DATA=0,MUT_SEAL=0,NSM=32;
 localparam [31:0] SM_MASK=(33'd1<<NSM)-1;
 localparam integer W=291;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg [31:0] cb=0,cc=0,cw=0,start=0;
 reg [15:0] ce[0:31],se[0:31],loops[0:31];
 reg [10:0] ca[0:31],limit[0:31];reg [9:0] base[0:31];reg [255:0] cd[0:31];
 wire [31:0] ack,ready,v,active,done,fault;
 wire [1:0] ak[0:31],ar[0:31];wire[7:0]at[0:31];wire[10:0]aa[0:31];wire[15:0]ae[0:31],re[0:31];
 wire [W-1:0] cal[0:31];wire[31:0]ord[0:31];
 reg [255:0] image0[0:32767],image1[0:32767];reg[W-1:0]expected[0:32767];
 for(genvar sm=0;sm<32;sm++)begin:g_sm
 if(sm<NSM)begin:g_active
  ot_smh_calendar_pair_static #(.W(W),.TARGET(128+sm),.MUT_PC(MUT_PC),.MUT_DATA(MUT_DATA),.MUT_SEAL(MUT_SEAL)) dut(
   .clk(clk),.rst_n(rst_n),.cfg_begin_v(cb[sm]),.cfg_commit_v(cc[sm]),.cfg_we(cw[sm]),.cfg_epoch(ce[sm]),.cfg_addr(ca[sm]),.cfg_data(cd[sm]),
   .cfg_ack_v(ack[sm]),.cfg_ack_kind(ak[sm]),.cfg_ack_target(at[sm]),.cfg_ack_addr(aa[sm]),.cfg_ack_epoch(ae[sm]),.cfg_ack_resp(ar[sm]),
   .ready(ready[sm]),.ready_epoch(re[sm]),.start_v(start[sm]),.start_base(base[sm]),.start_limit(limit[sm]),.start_loops(loops[sm]),.start_epoch(se[sm]),
   .calendar(cal[sm]),.calendar_v(v[sm]),.ordinal(ord[sm]),.active(active[sm]),.done(done[sm]),.fault(fault[sm]));
 end else begin:g_unused
  assign ack[sm]=0;assign ready[sm]=0;assign v[sm]=0;assign active[sm]=0;assign done[sm]=0;assign fault[sm]=0;
  assign ak[sm]=0;assign ar[sm]=0;assign at[sm]=0;assign aa[sm]=0;assign ae[sm]=0;assign re[sm]=0;assign cal[sm]=0;assign ord[sm]=0;
 end
 end
 integer cycle=0,checked=0,caseid=0;
 string dir;
 always @(posedge clk)cycle=cycle+1;
 task automatic cfg(input integer kind,unit,epoch,address,input [255:0]data,input bit error);
  @(negedge clk);cb=0;cc=0;cw=0;ce[unit]=16'(epoch);ca[unit]=11'(address);cd[unit]=data;
  case(kind)0:cw[unit]=1;1:cb[unit]=1;2:cc[unit]=1;endcase
  @(posedge clk);#0.01;
  if(ack!=0)$fatal(1,"NATIVE_PAIR_FAIL prematureACK");
  @(negedge clk);cb=0;cc=0;cw=0;
  @(posedge clk);#0.01;
  if(ack!==(32'b1<<unit)||ak[unit]!==2'(kind)||at[unit]!==8'(128+unit)||aa[unit]!==11'(address)||ae[unit]!==16'(epoch)||ar[unit]!==2'(error?2:0))
   $fatal(1,"NATIVE_PAIR_FAIL ACK mismatch unit%0d kind%0d epoch%0d addr%0d gotack%h kind%0d target%0d addr%0d epoch%0d resp%0d expectederror%0d",unit,kind,epoch,address,ack,ak[unit],at[unit],aa[unit],ae[unit],ar[unit],error);
  if(error&&!fault[unit])$fatal(1,"NATIVE_PAIR_FAIL missingstickyfault");
  if(!error&&fault[unit])$fatal(1,"NATIVE_PAIR_FAIL unexpectedcfgfault");
  @(negedge clk);
 endtask
 task automatic load_images(input integer epoch);
  $readmemh($sformatf("%s/epoch%0d_plane0.hex",dir,epoch),image0);
  $readmemh($sformatf("%s/epoch%0d_plane1.hex",dir,epoch),image1);
  $readmemh($sformatf("%s/epoch%0d_logical.hex",dir,epoch),expected);
 endtask
 task automatic install(input integer unit,epoch);
  cfg(1,unit,epoch,0,0,0);
  if(ready[unit])$fatal(1,"NATIVE_PAIR_FAIL begin didnotinvalidateimage");
  for(integer pc=0;pc<1024;pc++)begin
   cfg(0,unit,epoch,pc,image0[unit*1024+pc],0);
   cfg(0,unit,epoch,1024+pc,image1[unit*1024+pc],0);
  end
  if(ready[unit])$fatal(1,"NATIVE_PAIR_FAIL imagereadybeforecommit");
  cfg(2,unit,epoch,0,0,0);
  if(!ready[unit]||re[unit]!==16'(epoch))$fatal(1,"NATIVE_PAIR_FAIL commitready");
 endtask
 task automatic launch(input integer epoch,first,stop,nloops,input [31:0]mask);
  @(negedge clk);
  for(integer sm=0;sm<32;sm++)begin se[sm]=16'(epoch);base[sm]=10'(first);limit[sm]=11'(stop);loops[sm]=16'(nloops);end
  start=mask;@(posedge clk);#0.01;@(negedge clk);start=0;
 endtask
 task automatic execute(input integer epoch,first,stop,nloops);
  integer launched,total,index,pc;bit ev;
  @(negedge clk);
  for(integer sm=0;sm<32;sm++)begin se[sm]=16'(epoch);base[sm]=10'(first);limit[sm]=11'(stop);loops[sm]=16'(nloops);end
  start=SM_MASK;@(posedge clk);#0.01;launched=cycle;
  @(negedge clk);start=0;total=(stop-first)*nloops;
  for(integer t=0;t<total+7;t++)begin
   @(posedge clk);#0.01;
   if(|fault)$fatal(1,"NATIVE_PAIR_FAIL executionfault mask%h",fault);
   index=cycle-launched-4;ev=index>=0&&index<total;pc=first+(ev?index%(stop-first):0);
   if(v!==({32{ev}}&SM_MASK))$fatal(1,"NATIVE_PAIR_FAIL cycle exactvalid start%0d cycle%0d index%0d mask%h",launched,cycle,index,v);
   for(integer sm=0;sm<NSM;sm++)begin
    if(ev)begin
     if(ord[sm]!==32'(index)||cal[sm]!==expected[sm*1024+pc]||done[sm]!==1'(index==total-1))
      $fatal(1,"NATIVE_PAIR_FAIL payload/PC/seal/order sm%0d pc%0d ordinal%0d got%h want%h",sm,pc,index,cal[sm],expected[sm*1024+pc]);
     checked++;
    end else if(done[sm])$fatal(1,"NATIVE_PAIR_FAIL spuriousdone");
   end
   @(negedge clk);
  end
  if(|active)$fatal(1,"NATIVE_PAIR_FAIL executiondidnotdrain");
 endtask
 initial begin
  if(!$value$plusargs("IMAGES=%s",dir))$fatal(1,"needIMAGES");
  if($value$plusargs("case=%d",caseid))begin end
  for(integer sm=0;sm<32;sm++)begin ce[sm]=0;ca[sm]=0;cd[sm]=0;se[sm]=0;base[sm]=0;limit[sm]=0;loops[sm]=0;end
  repeat(5)@(negedge clk);rst_n=1;
  load_images(1);
  if(caseid!=0)begin
   case(caseid)
    1:begin cfg(1,0,1,0,0,0);cfg(0,0,1,1024,image1[0],1);end
    2:begin cfg(1,0,1,0,0,0);cfg(0,0,1,0,image0[0]^(256'b1<<224),1);end
    3:begin cfg(1,0,1,0,0,0);cfg(0,0,1,0,image0[0]^(256'b1<<215),1);end
    4:begin cfg(1,0,1,0,0,0);cfg(0,0,1,0,image0[0]^(256'b1<<223),1);end
    5:begin cfg(1,0,1,0,0,0);cfg(2,0,1,0,0,1);end
    6:begin cfg(1,0,1,0,0,0);cfg(0,0,2,0,image0[0],1);end
    7:begin cfg(1,0,1,0,0,0);launch(1,0,1024,1,1);repeat(3)@(negedge clk);if(!fault[0]||(|v))$fatal(1,"NATIVE_PAIR_FAIL uncommittedlaunch");end
    8:begin install(0,1);launch(1,0,1024,1,1);repeat(5)@(negedge clk);cfg(0,0,1,0,image0[0],1);end
    9:begin install(0,1);launch(0,0,1024,1,1);repeat(3)@(negedge clk);if(!fault[0]||(|v))$fatal(1,"NATIVE_PAIR_FAIL staleepochlaunch");end
    10:begin install(0,1);cfg(1,0,2,0,0,0);load_images(2);cfg(0,0,2,1024,image1[0],1);end
    11:begin cfg(1,0,1,0,0,0);cfg(0,0,1,0,image0[0]^(256'b1<<240),1);end
    12:begin cfg(1,0,1,0,0,0);cfg(0,0,1,0,image0[0],0);cfg(0,0,1,1024,image1[0]^(256'b1<<214),1);end
    default:$fatal(1,"badcase");
   endcase
   $display("NATIVE_PAIR_NEGATIVE PASS case=%0d",caseid);
  end else begin
   for(integer epoch=1;epoch<=2;epoch++)begin
    load_images(epoch);
    for(integer sm=0;sm<NSM;sm++)install(sm,epoch);
    execute(epoch,0,1024,2);
    execute(epoch,37,1001,1);
   end
   $display("NATIVE_PAIR PASS SMs=%0d actualSRAMs=%0d depth=1024 epochs=2 outputs=%0d start_to_calendar=4 macroread_to_calendar=2 II=1",NSM,NSM*2,checked);
  end
  $finish;
 end
endmodule
`default_nettype wire
