`default_nettype none
// Opt-in existing target78 F20 boot publication extension. No new host target.
// F00 header: word_address19, sector_count17, mask8 at bits0,19,36;
// F01: one complete data256 sector. Header address must be aligned to8words.
// Regular namespace only; SID/bank come from actual wordaddress, never rewritten.
// Source pins sample F20 on n; native packet launches n+1 (bank samples n+2).
module ot_vms_f20_boot_publish_r2048 #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire index_active,finish,
 input wire[31:0]legacy_write_valid,
 output wire consume_cfg,
 output wire[281:0]native_wq,
 output wire[4:0]destination,
 output wire collision,
 output reg fault,
 output wire pending
);
 wire take=cfg_v && cfg_target==8'h78 && (cfg_addr==12'hF00 || cfg_addr==12'hF01);
 assign consume_cfg=take;
 reg cv;reg[11:0]ca;reg[255:0]cd;reg active_q;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin cv<=0;active_q<=0;end else begin cv<=take;active_q<=index_active;end
 always @(posedge clk)begin ca<=cfg_addr;cd<=cfg_data;end
 reg[19:0]next_word;reg[16:0]remaining;reg[7:0]mask;
 reg[2:0]drain;
 reg packet_v;reg[16:0]sector;reg[255:0]payload;reg[7:0]packet_mask;
 wire header_bad=(|cd[2:0]) || cd[35:19]==0 || (|cd[255:44]) ||
                 ({2'b0,cd[18:0]}+({4'b0,cd[35:19]}<<3)>21'd524288);
 assign destination={sector[14:13],sector[2:0]};
 wire cl=packet_v && legacy_write_valid[destination];
 assign collision=cl && MUT!=3;
 reg delayed_v;
 always @(posedge clk or negedge rst_n)if(!rst_n)delayed_v<=0;else delayed_v<=packet_v;
 wire allowed=((MUT==4)?delayed_v:packet_v) && !collision && !index_active;
 wire[16:0]mapped_sector=(MUT==1)?{sector[16],1'b0,sector[14:0]}:
                            (MUT==2)?{1'b1,sector[15:0]}:sector;
 assign native_wq={allowed,mapped_sector,payload,packet_mask};
 assign pending=remaining!=0 || cv || packet_v || drain!=0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin next_word<=0;remaining<=0;mask<=0;packet_v<=0;fault<=0;drain<=0;end
  else begin
   packet_v<=0;
   if(allowed)drain<=3'd5;else if(drain!=0)drain<=drain-1'b1;
   if(finish && (pending || take))fault<=1;
   if(cl || (packet_v && index_active))fault<=1;
   if(cv)begin
    if(active_q || index_active || fault)fault<=1;
    else if(ca==12'hF00)begin
     if(header_bad || remaining!=0)fault<=1;
     else begin next_word<={1'b0,cd[18:0]};remaining<=cd[35:19];mask<=cd[43:36];end
    end else begin
     if(remaining==0 || next_word[19])fault<=1;
     else begin packet_v<=1;sector<={1'b0,next_word[18:3]};payload<=cd;packet_mask<=mask;
      next_word<=next_word+20'd8;remaining<=remaining-1'b1;
     end
    end
   end
  end
 end
endmodule
`default_nettype wire
