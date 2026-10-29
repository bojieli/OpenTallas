`default_nettype none
// Explicit opt-in replacement for the rail seed. Authority is the selected
// static_run_target's registered run_v/base/count/arg, matched to allocated KEY
// descriptors. run_v alone is never interpreted as a KEY start.
module ot_hnx_idxn_key_prefill_source #(
 parameter [7:0] KEY_BASE=0,parameter [8:0] KEY_COUNT=0,
 parameter [7:0] KEY_ARG_MASK=0,KEY_ARG_VALUE=0
)(input wire clk,rst_n,
 input wire cp_run_v,input wire[7:0]cp_run_base,input wire[8:0]cp_run_count,input wire[7:0]cp_run_arg,
 input wire service_running,program_active,
 input wire inject_v,input wire[2:0]physical_lane,input wire[7:0]row,input wire cohort,input wire[1098:0]packet,
 output reg[1111:0]rail,output reg fault);
 initial if(KEY_COUNT==0)$fatal(1,"PREFILL requires explicit allocated descriptor identity");
 reg[15:0]epoch;
 wire key_start=cp_run_v&&cp_run_base==KEY_BASE&&cp_run_count==KEY_COUNT&&
                (cp_run_arg&KEY_ARG_MASK)==(KEY_ARG_VALUE&KEY_ARG_MASK);
 wire[9:0]tag={physical_lane,7'b0}+{2'b0,row};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rail<=0;fault<=0;epoch<=0;end
  else begin
   rail<={inject_v,cohort,row,physical_lane,packet[1087:0],packet[1097:1088],packet[1098]};
   if(key_start)begin
    if(service_running||program_active||inject_v)fault<=1;
    else begin
     // row255/lane7 is reserved control; payload[15:0] cookie,[31:16] epoch.
     rail<={1'b1,1'b0,8'hff,3'd7,1067'd0,16'(epoch+16'd1),16'hc1ea};
     epoch<=epoch+16'd1;
    end
   end
   if(inject_v&&(!packet[1098]||packet[1097:1088]!=tag||row>8'd170))fault<=1;
  end
 end
endmodule

// Decode at the existing receiver face. Normal payload has no added pipeline
// edge; clear shares the same captured rail and is applied to BOTH cohorts.
// New control path/epoch FFs need physical qualification. No frame_start input.
module ot_hnx_idxn_key_prefill_receiver(
 input wire clk,rst_n,input wire[1111:0]rail,
 output wire prefill_clear,output wire data_v,output wire cohort,
 output wire[2:0]physical_lane,output wire[7:0]row,output wire[1098:0]line,
 output reg fault);
 reg[15:0]last_epoch;reg seen;
 wire ctrl=rail[1111]&&rail[1109:1102]==8'hff;
 wire cookie=!rail[1110]&&rail[1101:1099]==3'd7&&rail[15:0]==16'hc1ea;
 wire next_epoch=rail[31:16]==16'(last_epoch+16'd1);
 assign prefill_clear=ctrl&&cookie&&next_epoch;
 assign data_v=rail[1111]&&!ctrl&&seen&&rail[1109:1102]<=8'd170;
 assign cohort=rail[1110];assign row=rail[1109:1102];assign physical_lane=rail[1101:1099];assign line=rail[1098:0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin last_epoch<=0;seen<=0;fault<=0;end
  else if(rail[1111])begin
   if(ctrl)begin
    if(!cookie||!next_epoch)fault<=1;
    else begin last_epoch<=rail[31:16];seen<=1;end
   end else if(!seen||rail[1109:1102]>8'd170)fault<=1;
  end
 end
endmodule
`default_nettype wire
