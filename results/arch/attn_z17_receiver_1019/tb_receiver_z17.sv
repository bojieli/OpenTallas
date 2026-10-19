`timescale 1ns/1ps
module sidecase #(parameter SIDE=0)(output reg done=0);
integer cases=0, checks=0, wf=0, wa=0, z,j,pat,caseid; reg mutate=0; reg [16:0] previous=0; reg [511:0] data; reg [3:0] kind; reg [16:0] good;
reg [0:0] ck;
reg [0:0] rst_n;
reg [0:0] tx_event;
reg [0:0] tx_expected;
reg [3:0] tx_kind;
reg [3:0] tx_expected_kind;
reg [15:0] tx_epoch;
reg [15:0] tx_expected_epoch;
reg [5:0] tx_layer;
reg [5:0] tx_expected_layer;
reg [4:0] tx_beat;
reg [4:0] tx_expected_beat;
reg [511:0] tx_data;
reg [0:0] rx_event;
reg [0:0] rx_expected;
reg [547:0] rx_payload;
reg [3:0] rx_expected_kind;
reg [15:0] rx_expected_epoch;
reg [5:0] rx_expected_layer;
reg [4:0] rx_expected_beat;
reg [16:0] supplied,off_flags;
wire [0:0] ref_tx_valid;
wire [547:0] ref_tx_payload;
wire [0:0] ref_rx_valid;
wire [3:0] ref_rx_kind;
wire [15:0] ref_rx_epoch;
wire [5:0] ref_rx_layer;
wire [4:0] ref_rx_beat;
wire [511:0] ref_rx_data;
wire [0:0] ref_fault;
wire [3:0] ref_fault_cause;
qkd_native_attention_record_ld #(.KV_SIDE(SIDE)) u_ref (
.ck(ck),
.rst_n(rst_n),
.tx_event(tx_event),
.tx_expected(tx_expected),
.tx_kind(tx_kind),
.tx_expected_kind(tx_expected_kind),
.tx_epoch(tx_epoch),
.tx_expected_epoch(tx_expected_epoch),
.tx_layer(tx_layer),
.tx_expected_layer(tx_expected_layer),
.tx_beat(tx_beat),
.tx_expected_beat(tx_expected_beat),
.tx_data(tx_data),
.rx_event(rx_event),
.rx_expected(rx_expected),
.rx_payload(rx_payload),
.rx_expected_kind(rx_expected_kind),
.rx_expected_epoch(rx_expected_epoch),
.rx_expected_layer(rx_expected_layer),
.rx_expected_beat(rx_expected_beat),
.tx_valid(ref_tx_valid),
.tx_payload(ref_tx_payload),
.rx_valid(ref_rx_valid),
.rx_kind(ref_rx_kind),
.rx_epoch(ref_rx_epoch),
.rx_layer(ref_rx_layer),
.rx_beat(ref_rx_beat),
.rx_data(ref_rx_data),
.fault(ref_fault),
.fault_cause(ref_fault_cause));
wire [1097:0] ref_all={ref_tx_valid,ref_tx_payload,ref_rx_valid,ref_rx_kind,ref_rx_epoch,ref_rx_layer,ref_rx_beat,ref_rx_data,ref_fault,ref_fault_cause};
wire [0:0] off_tx_valid;
wire [547:0] off_tx_payload;
wire [0:0] off_rx_valid;
wire [3:0] off_rx_kind;
wire [15:0] off_rx_epoch;
wire [5:0] off_rx_layer;
wire [4:0] off_rx_beat;
wire [511:0] off_rx_data;
wire [0:0] off_fault;
wire [3:0] off_fault_cause;
qkd_native_attention_record_ld_z17 #(.KV_SIDE(SIDE),.RX_ZERO17(0)) u_off (
.ck(ck),
.rst_n(rst_n),
.tx_event(tx_event),
.tx_expected(tx_expected),
.tx_kind(tx_kind),
.tx_expected_kind(tx_expected_kind),
.tx_epoch(tx_epoch),
.tx_expected_epoch(tx_expected_epoch),
.tx_layer(tx_layer),
.tx_expected_layer(tx_expected_layer),
.tx_beat(tx_beat),
.tx_expected_beat(tx_expected_beat),
.tx_data(tx_data),
.rx_event(rx_event),
.rx_expected(rx_expected),
.rx_payload(rx_payload),
.rx_expected_kind(rx_expected_kind),
.rx_expected_epoch(rx_expected_epoch),
.rx_expected_layer(rx_expected_layer),
.rx_expected_beat(rx_expected_beat),
.tx_valid(off_tx_valid),
.tx_payload(off_tx_payload),
.rx_valid(off_rx_valid),
.rx_kind(off_rx_kind),
.rx_epoch(off_rx_epoch),
.rx_layer(off_rx_layer),
.rx_beat(off_rx_beat),
.rx_data(off_rx_data),
.fault(off_fault),
.fault_cause(off_fault_cause),
.rx_zero17(off_flags));
wire [1097:0] off_all={off_tx_valid,off_tx_payload,off_rx_valid,off_rx_kind,off_rx_epoch,off_rx_layer,off_rx_beat,off_rx_data,off_fault,off_fault_cause};
wire [0:0] on_tx_valid;
wire [547:0] on_tx_payload;
wire [0:0] on_rx_valid;
wire [3:0] on_rx_kind;
wire [15:0] on_rx_epoch;
wire [5:0] on_rx_layer;
wire [4:0] on_rx_beat;
wire [511:0] on_rx_data;
wire [0:0] on_fault;
wire [3:0] on_fault_cause;
qkd_native_attention_record_ld_z17 #(.KV_SIDE(SIDE),.RX_ZERO17(1)) u_on (
.ck(ck),
.rst_n(rst_n),
.tx_event(tx_event),
.tx_expected(tx_expected),
.tx_kind(tx_kind),
.tx_expected_kind(tx_expected_kind),
.tx_epoch(tx_epoch),
.tx_expected_epoch(tx_expected_epoch),
.tx_layer(tx_layer),
.tx_expected_layer(tx_expected_layer),
.tx_beat(tx_beat),
.tx_expected_beat(tx_expected_beat),
.tx_data(tx_data),
.rx_event(rx_event),
.rx_expected(rx_expected),
.rx_payload(rx_payload),
.rx_expected_kind(rx_expected_kind),
.rx_expected_epoch(rx_expected_epoch),
.rx_expected_layer(rx_expected_layer),
.rx_expected_beat(rx_expected_beat),
.tx_valid(on_tx_valid),
.tx_payload(on_tx_payload),
.rx_valid(on_rx_valid),
.rx_kind(on_rx_kind),
.rx_epoch(on_rx_epoch),
.rx_layer(on_rx_layer),
.rx_beat(on_rx_beat),
.rx_data(on_rx_data),
.fault(on_fault),
.fault_cause(on_fault_cause),
.rx_zero17(good));
wire [1097:0] on_all={on_tx_valid,on_tx_payload,on_rx_valid,on_rx_kind,on_rx_epoch,on_rx_layer,on_rx_beat,on_rx_data,on_fault,on_fault_cause};
wire [0:0] wrong_tx_valid;
wire [547:0] wrong_tx_payload;
wire [0:0] wrong_rx_valid;
wire [3:0] wrong_rx_kind;
wire [15:0] wrong_rx_epoch;
wire [5:0] wrong_rx_layer;
wire [4:0] wrong_rx_beat;
wire [511:0] wrong_rx_data;
wire [0:0] wrong_fault;
wire [3:0] wrong_fault_cause;
qkd_native_attention_record_ld_z17 #(.KV_SIDE(SIDE),.RX_ZERO17(1)) u_wrong (
.ck(ck),
.rst_n(rst_n),
.tx_event(tx_event),
.tx_expected(tx_expected),
.tx_kind(tx_kind),
.tx_expected_kind(tx_expected_kind),
.tx_epoch(tx_epoch),
.tx_expected_epoch(tx_expected_epoch),
.tx_layer(tx_layer),
.tx_expected_layer(tx_expected_layer),
.tx_beat(tx_beat),
.tx_expected_beat(tx_expected_beat),
.tx_data(tx_data),
.rx_event(rx_event),
.rx_expected(rx_expected),
.rx_payload(rx_payload),
.rx_expected_kind(rx_expected_kind),
.rx_expected_epoch(rx_expected_epoch),
.rx_expected_layer(rx_expected_layer),
.rx_expected_beat(rx_expected_beat),
.tx_valid(wrong_tx_valid),
.tx_payload(wrong_tx_payload),
.rx_valid(wrong_rx_valid),
.rx_kind(wrong_rx_kind),
.rx_epoch(wrong_rx_epoch),
.rx_layer(wrong_rx_layer),
.rx_beat(wrong_rx_beat),
.rx_data(wrong_rx_data),
.fault(wrong_fault),
.fault_cause(wrong_fault_cause),
.rx_zero17(supplied));
wire [1097:0] wrong_all={wrong_tx_valid,wrong_tx_payload,wrong_rx_valid,wrong_rx_kind,wrong_rx_epoch,wrong_rx_layer,wrong_rx_beat,wrong_rx_data,wrong_fault,wrong_fault_cause};
wire [0:0] aged_tx_valid;
wire [547:0] aged_tx_payload;
wire [0:0] aged_rx_valid;
wire [3:0] aged_rx_kind;
wire [15:0] aged_rx_epoch;
wire [5:0] aged_rx_layer;
wire [4:0] aged_rx_beat;
wire [511:0] aged_rx_data;
wire [0:0] aged_fault;
wire [3:0] aged_fault_cause;
qkd_native_attention_record_ld_z17 #(.KV_SIDE(SIDE),.RX_ZERO17(1)) u_aged (
.ck(ck),
.rst_n(rst_n),
.tx_event(tx_event),
.tx_expected(tx_expected),
.tx_kind(tx_kind),
.tx_expected_kind(tx_expected_kind),
.tx_epoch(tx_epoch),
.tx_expected_epoch(tx_expected_epoch),
.tx_layer(tx_layer),
.tx_expected_layer(tx_expected_layer),
.tx_beat(tx_beat),
.tx_expected_beat(tx_expected_beat),
.tx_data(tx_data),
.rx_event(rx_event),
.rx_expected(rx_expected),
.rx_payload(rx_payload),
.rx_expected_kind(rx_expected_kind),
.rx_expected_epoch(rx_expected_epoch),
.rx_expected_layer(rx_expected_layer),
.rx_expected_beat(rx_expected_beat),
.tx_valid(aged_tx_valid),
.tx_payload(aged_tx_payload),
.rx_valid(aged_rx_valid),
.rx_kind(aged_rx_kind),
.rx_epoch(aged_rx_epoch),
.rx_layer(aged_rx_layer),
.rx_beat(aged_rx_beat),
.rx_data(aged_rx_data),
.fault(aged_fault),
.fault_cause(aged_fault_cause),
.rx_zero17(previous));
wire [1097:0] aged_all={aged_tx_valid,aged_tx_payload,aged_rx_valid,aged_rx_kind,aged_rx_epoch,aged_rx_layer,aged_rx_beat,aged_rx_data,aged_fault,aged_fault_cause};

function [16:0] flags(input [511:0] d);
integer i;
begin flags[0]=|d[31:19]; flags[1]=|d[31:5]; for(i=1;i<=15;i=i+1) flags[i+1]=|d[32*i+:32]; end
endfunction
task check;
begin
 #1; checks=checks+1;
 if(ref_all !== off_all) begin $display("FAIL DISABLED side=%0d case=%0d check=%0d ref=%h off=%h",SIDE,caseid,checks,ref_all,off_all); $fatal(1); end
 if(ref_all !== on_all) begin $display("FAIL COHERENT side=%0d case=%0d check=%0d ref=%h on=%h",SIDE,caseid,checks,ref_all,on_all); $fatal(1); end
 if(mutate && ref_all !== wrong_all) begin wf=wf+1; $display("WITNESS WRONGFLAG side=%0d case=%0d ref_fault=%b mut_fault=%b ref_valid=%b mut_valid=%b",SIDE,caseid,ref_fault,wrong_fault,ref_rx_valid,wrong_rx_valid); end
 if(mutate && ref_all !== aged_all) begin wa=wa+1; $display("WITNESS WRONGAGE side=%0d case=%0d ref_fault=%b mut_fault=%b ref_valid=%b mut_valid=%b",SIDE,caseid,ref_fault,aged_fault,ref_rx_valid,aged_rx_valid); end
end endtask
task tick;
begin ck=0; check; ck=1; check; ck=0; check; end endtask
task prepare;
begin
 ck=0;rst_n=0;tx_event=0;tx_expected=0;tx_kind=(SIDE?3:1);tx_expected_kind=tx_kind;tx_epoch=16'h1234;tx_expected_epoch=tx_epoch;tx_layer=2;tx_expected_layer=2;tx_beat=0;tx_expected_beat=0;tx_data=0;
 rx_event=0;rx_expected=0;rx_payload=0;rx_expected_kind=(SIDE?1:4);rx_expected_epoch=16'h1234;rx_expected_layer=2;rx_expected_beat=0;good=flags(0);supplied=0;previous=0;off_flags=17'bxzxzxzxzxzxzxzxzx;tick;rst_n=1;tick;
end endtask
initial begin
 ck=0;rst_n=1;rx_payload=0;good=0;supplied=0;previous=0;off_flags=0;
 for(caseid=0;caseid<256;caseid=caseid+1) begin
  mutate=0;prepare;
  kind=(caseid%8)+1;data=0;
  pat=(caseid/8)%8;
  case(pat)
   0:data=0;
   1:data=512'b1;
   2:data={512{1'b1}};
   3:data[19+(caseid%493)]=1'b1;
   4:data[5+(caseid%507)]=1'bx;
   5:data[5+(caseid%507)]=1'bz;
   6:begin data[0]=1'bx;data[1]=1'bz;end
   7:begin for(j=0;j<512;j=j+1)data[j]=((j+caseid)%7==0);end
  endcase
  rx_payload={5'd0,kind,6'd2,16'h1234,5'd0,data};rx_expected_kind=kind;
  rx_event=1;rx_expected=1;good=flags(data);supplied=good;previous=good;
  case(caseid/64)
   0:begin end
   1:begin rx_payload[532:517]=16'h9876;end
   2:begin rx_payload[538:533]=6'd36;rx_payload[516:512]=5'd3;end
   3:begin rx_expected=0;rx_payload[547:543]=5'd1;end
  endcase
  tx_event=(caseid%3==0);tx_expected=tx_event;
  if(caseid%11==0)tx_expected=!tx_event;
  tick; rx_event=0;rx_expected=0;tick;rst_n=0;check;tick;
  cases=cases+1;
 end
 // Every reserved slice is a causal flag witness. Enabled correct flags reject;
 // zeroed or prior-cycle zero flags accept the same malformed record.
 for(z=0;z<17;z=z+1)begin
  caseid=256+z;mutate=0;prepare;data=0;
  if(z==0)begin kind=1;data[19]=1;end
  else if(z==1)begin kind=4;data[5]=1;end
  else begin kind=(SIDE?1:4);data[32*(z-1)]=1;end
  // Direction must be legal for a visible reserved-bit failure.
  if(SIDE && kind==4)begin kind=1;data=0;data[19]=1;end
  if(!SIDE && kind==1)begin kind=4;data=0;data[19]=1;end
  rx_payload={5'd0,kind,6'd2,16'h1234,5'd0,data};rx_expected_kind=kind;rx_event=1;rx_expected=1;
  good=flags(data);supplied=0;previous=0;mutate=1;tick;mutate=0;
 end
 if(wf==0 || wa==0)$fatal(1,"MUTANT_NOT_CAUGHT side=%0d wf=%0d wa=%0d",SIDE,wf,wa);
 $display("PASS side=%0d cases=%0d checks=%0d all_output_bits=1098 wrongflag=%0d wrongage=%0d",SIDE,cases+17,checks,wf,wa);done=1;
end
endmodule
module tb;
wire d0,d1;sidecase #(.SIDE(0)) s0(d0);sidecase #(.SIDE(1)) s1(d1);
initial begin wait(d0&&d1);$display("PASS RECEIVER_Z17 FOURSTATE ALL OUTPUTS BOTH SIDES");$finish;end
endmodule
