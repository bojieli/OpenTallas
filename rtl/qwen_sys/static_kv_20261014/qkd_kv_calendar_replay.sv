`timescale 1ns/1ps
// Sparse immutable per-domain calendar. Boot roots are actual flops, not an
// inferred SRAM or a DPI memory. No payload/arrival/ready input selects slots.
// Width64 HBM packing: {blk_go, epoch16, reserved_write, reserved_static,
// reserved_rd, static_cmd43}; static_cmd_owner is separately active.
// Width33 CORE packing: {expected_layer6, expected_epoch16, sector10, put}.
// A full perPC/all36 image, physical home/phi-R and cost are NOT established.
module qkd_kv_calendar_replay #(
 parameter integer DEPTH=64, WIDTH=64, MUT=0
)(
 input wire ck,rst_n,
 input wire cfg_we,cfg_seal,input wire[5:0]cfg_addr,
 input wire[31:0]cfg_time,input wire[WIDTH-1:0]cfg_payload,
 input wire start,
 output reg[WIDTH-1:0]payload,
 output reg configured,active,done,fault,
 output reg[31:0]cycle
);
 initial if(DEPTH<1||DEPTH>64||WIDTH<1||WIDTH>64)$error("split calendar into <=64-event/64-bit leaves");
 (* keep = "true" *) reg reset_pin_n;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_pin_n<=0;else reset_pin_n<=1;
 (* keep = "true" *) reg cfg_we_p,cfg_seal_p,start_p;
 (* keep = "true" *) reg[5:0]cfg_addr_p;
 (* keep = "true" *) reg[31:0]cfg_time_p;
 (* keep = "true" *) reg[WIDTH-1:0]cfg_payload_p;
 always @(posedge ck)begin
  cfg_addr_p<=cfg_addr;cfg_time_p<=cfg_time;cfg_payload_p<=cfg_payload;
 end
 always @(posedge ck or negedge reset_pin_n)
  if(!reset_pin_n)begin cfg_we_p<=0;cfg_seal_p<=0;start_p<=0;end
  else begin cfg_we_p<=cfg_we;cfg_seal_p<=cfg_seal;start_p<=start;end
 reg[31:0]times[0:DEPTH-1];reg[WIDTH-1:0]words[0:DEPTH-1];
 reg[6:0]count,head;reg[31:0]last_time,stop_time;
 wire accept_cfg=cfg_we_p&&!cfg_seal_p&&!configured&&!active&&!fault&&
   count<DEPTH&&{1'b0,cfg_addr_p}==count&&(count==0||cfg_time_p>last_time);
 genvar g;
 generate for(g=0;g<DEPTH;g=g+1)begin:boot_flops
  always @(posedge ck)if(accept_cfg&&cfg_addr_p==g)begin
   times[g]<=cfg_time_p;words[g]<=cfg_payload_p;
  end
 end endgenerate
 wire[31:0]next_cycle=cycle+1'b1;
 wire due=head<count&&next_cycle==times[head]+((MUT==1)?32'd1:32'd0);
 always @(posedge ck or negedge reset_pin_n)begin
  if(!reset_pin_n)begin
   count<=0;head<=0;last_time<=0;stop_time<=0;configured<=0;
   active<=0;done<=0;fault<=0;cycle<=0;payload<=0;
  end else begin
   done<=0;payload<=0;
   if(cfg_we_p||cfg_seal_p)begin
    if(cfg_we_p)begin
     if(!accept_cfg)fault<=1;
     else begin count<=count+1'b1;last_time<=cfg_time_p;end
    end else if(configured||active||fault||count==0||cfg_time_p<=last_time)fault<=1;
    else begin configured<=1;stop_time<=cfg_time_p;end
   end
   if(start_p)begin
    if(!configured||active||fault||cfg_we_p||cfg_seal_p)fault<=1;
    else begin
     active<=1;cycle<=0;head<=0;
     if(times[0]==0)begin payload<=words[0]^((MUT==2)?1:0);head<=1;end
    end
   end else if(active)begin
    cycle<=next_cycle;
    if(due)begin payload<=words[head]^((MUT==2)?1:0);head<=head+1'b1;end
    if(next_cycle==stop_time)begin
     active<=0;done<=1;
     if(head!=count)fault<=1;
    end
    if(&cycle)begin active<=0;fault<=1;done<=1;end
   end
  end
 end
endmodule
