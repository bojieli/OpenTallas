`timescale 1ns/1ps
// ROM ABI opentallas.s81.collective-fixed-edge-rom.v2: CB468/RW564.
// Fixed compiler calendar engine3 endpoint, single stream clock domain.
// ROM consumes one row per edge, never waits for data, credits or completion.
// c_cmd is pin-registered (+1 edge). First matching captured command starts row0; each later pulse must match its named edge.
// Every row carries a valid marker, including idle rows. Empty/missing ROM
// and CYCLES outside1..4096 fail closed; no generic-array or page-size fallback.
// refuses commands. Arrival faults fail-stop; they never retime the calendar.
// All control outputs and c_done are one-edge pin registers from the ROM, priced by the image compiler.
// ROM must be rebuilt for changed physical flight, clock phase or service price.
module s81_static_calendar_controller #(
 parameter ROM_FILE="", parameter integer CYCLES=1,
 parameter integer AW=(CYCLES<2 ? 1:$clog2(CYCLES))
)(
 input wire clk,rst_n,input wire [84:0] c_cmd,
 output reg [8:0] c_done,output wire [1:0] c_st,
 input wire datapath_fault,
 output reg read_slot,
 output reg [13:0] read_row,
 output reg issue_slot,
 output reg [31:0] tag,
 output reg [15:0] seq,
 output reg last,
 output reg [3:0] rankmask,
 output reg commit_slot,
 output reg [31:0] commit_tag,
 output reg [15:0] commit_seq,
 output reg commit_last,
 output reg [3:0] commit_rankmask,
 output reg [59:0] commit_rows,
 output reg tx_beat_slot,
 output reg [1:0] tx_phase,
 output reg tx_frame_slot,
 output reg rx_beat_slot,
 output reg [1:0] rx_phase,
 output reg rx_frame_slot,
 output reg [4:0] channel_tx_slot,
 output reg [9:0] channel_tx_kind,
 output reg [49:0] channel_tx_seq,
 output reg [4:0] channel_tx_last,
 output reg [4:0] channel_rx_slot,
 output reg [9:0] channel_rx_kind,
 output reg [49:0] channel_rx_seq,
 output reg [4:0] channel_rx_last,
 output reg [4:0] channel_tx_beat_slot,
 output reg [4:0] channel_tx_frame_slot,
 output reg [9:0] channel_tx_phase,
 output reg [4:0] channel_rx_beat_slot,
 output reg [4:0] channel_rx_frame_slot,
 output reg [9:0] channel_rx_phase,
 output reg hc_reduce_slot,
 output reg hc_write_slot,
 output reg [3:0] hc_word_index,
 output reg [15:0] hc_expect_seq,
 output reg hc_expect_last,
 output reg hc_emit_slot,
 output reg [31:0] hc_emit_tag,
 output reg commit_gather,
 output reg raw_capture_payload_slot,
 output reg raw_capture_meta_slot,
 output reg raw_rx_write_slot,
 output reg [13:0] raw_rx_payload_row,
 output reg [13:0] raw_rx_meta_row,
 output reg [7:0] raw_rx_tag,
 output reg hc_assemble_slot,
 output wire busy
);
 localparam integer CB=468,RW=564;
 // Physical immutable controlpage: three actual4096x266 macros in width.
 // Macro q is synchronous, one enabled edge; row0 is fetched during idle,
 // overlapping the existing command pin register. Every active edge consumes
 // the previous macro read while fetching the next statically named row.
 // In synthesis the image lives in the ROM macro contents (no file): only the CYCLES range is checked there.
`ifdef SYNTHESIS
 localparam bit CONFIGURED=CYCLES>=1 && CYCLES<=4096;
`else
 localparam bit CONFIGURED=(ROM_FILE!="") && CYCLES>=1 && CYCLES<=4096;
`endif
 wire [797:0] macro_data;
 wire [11:0] macro_addr,macro_addr_n;
 wire macro_enable=rst_n && CONFIGURED;
 genvar bank;
 generate for(bank=0;bank<3;bank=bank+1)begin:ROM_BANK
  ot_rom_4096x266_m8
`ifndef SYNTHESIS
   #(.VIAMAP(ROM_FILE=="" ? "" : {ROM_FILE,(bank==0 ? ".b0.viamap.hex" : bank==1 ? ".b1.viamap.hex" : ".b2.viamap.hex")}))
`endif
   u_rom(.clk(clk),.ce_in(macro_enable),.addr_in(macro_addr),.rd_out(macro_data[bank*266+:266]));
 end endgenerate
 reg rom_valid_q;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)rom_valid_q<=0;else rom_valid_q<=macro_enable;
 end
 reg [84:0] c_cmd_q;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)c_cmd_q<=0;else c_cmd_q<=c_cmd;
 end
 reg active,fault,online;reg [AW-1:0] cursor;
 wire [RW-1:0] entry=macro_data[RW-1:0];
 wire running=active || c_cmd_q[84];
 wire [84:0] expected=entry[CB+:85];
 wire descriptor_bad=c_cmd_q[84] && (c_cmd_q[30:24]!=0 || c_cmd_q[22:7]==0 || c_cmd_q[22:7]>16'd1024);
 // Idle payload bits need not be zero on external pulse buses.
 wire command_bad=(c_cmd_q[84]!=expected[84]) ||
                  (c_cmd_q[84] && c_cmd_q[83:0]!=expected[83:0]);
 wire row_bad=!CONFIGURED || !rom_valid_q || !entry[RW-1] || descriptor_bad || command_bad;
 // Fetch progression depends only on the fixed calendar cursor/final bit;
 // command/data mismatches fault the controller without retiming a read.
 wire [AW-1:0] current_row=active ? cursor:{AW{1'b0}};
 // OT_S81_COLL_CAL_MUT_ROW (negative control): the macro reads the row after the named one.
`ifdef OT_S81_COLL_CAL_MUT_ROW
 assign macro_addr=macro_addr_n+12'd1;
`else
 assign macro_addr=macro_addr_n;
`endif
 assign macro_addr_n=running && !entry[RW-2] && int'(current_row)<CYCLES-1 ?
                   12'(int'(current_row)+1):12'd0;
 wire enabled=rst_n && running && !fault && !datapath_fault && !row_bad;
 assign busy=active;
 assign c_st={online,fault};
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin read_slot<=0;read_row<=0;issue_slot<=0;tag<=0;seq<=0;last<=0;rankmask<=0;commit_slot<=0;commit_tag<=0;commit_seq<=0;commit_last<=0;commit_rankmask<=0;commit_rows<=0;tx_beat_slot<=0;tx_phase<=0;tx_frame_slot<=0;rx_beat_slot<=0;rx_phase<=0;rx_frame_slot<=0;channel_tx_slot<=0;channel_tx_kind<=0;channel_tx_seq<=0;channel_tx_last<=0;channel_rx_slot<=0;channel_rx_kind<=0;channel_rx_seq<=0;channel_rx_last<=0;channel_tx_beat_slot<=0;channel_tx_frame_slot<=0;channel_tx_phase<=0;channel_rx_beat_slot<=0;channel_rx_frame_slot<=0;channel_rx_phase<=0;hc_reduce_slot<=0;hc_write_slot<=0;hc_word_index<=0;hc_expect_seq<=0;hc_expect_last<=0;hc_emit_slot<=0;hc_emit_tag<=0;commit_gather<=0;raw_capture_payload_slot<=0;raw_capture_meta_slot<=0;raw_rx_write_slot<=0;raw_rx_payload_row<=0;raw_rx_meta_row<=0;raw_rx_tag<=0;hc_assemble_slot<=0;active<=0;fault<=0;online<=0;cursor<=0;c_done<=0;end
  else begin
   read_slot<=enabled ? entry[0 +: 1] : 1'd0;
   read_row<=enabled ? entry[1 +: 14] : 14'd0;
   issue_slot<=enabled ? entry[15 +: 1] : 1'd0;
   tag<=enabled ? entry[16 +: 32] : 32'd0;
   seq<=enabled ? entry[48 +: 16] : 16'd0;
   last<=enabled ? entry[64 +: 1] : 1'd0;
   rankmask<=enabled ? entry[65 +: 4] : 4'd0;
   commit_slot<=enabled ? entry[69 +: 1] : 1'd0;
   commit_tag<=enabled ? entry[70 +: 32] : 32'd0;
   commit_seq<=enabled ? entry[102 +: 16] : 16'd0;
   commit_last<=enabled ? entry[118 +: 1] : 1'd0;
   commit_rankmask<=enabled ? entry[119 +: 4] : 4'd0;
   commit_rows<=enabled ? entry[123 +: 60] : 60'd0;
   tx_beat_slot<=enabled ? entry[183 +: 1] : 1'd0;
   tx_phase<=enabled ? entry[184 +: 2] : 2'd0;
   tx_frame_slot<=enabled ? entry[186 +: 1] : 1'd0;
   rx_beat_slot<=enabled ? entry[187 +: 1] : 1'd0;
   rx_phase<=enabled ? entry[188 +: 2] : 2'd0;
   rx_frame_slot<=enabled ? entry[190 +: 1] : 1'd0;
   channel_tx_slot<=enabled ? entry[191 +: 5] : 5'd0;
   channel_tx_kind<=enabled ? entry[196 +: 10] : 10'd0;
   channel_tx_seq<=enabled ? entry[206 +: 50] : 50'd0;
   channel_tx_last<=enabled ? entry[256 +: 5] : 5'd0;
   channel_rx_slot<=enabled ? entry[261 +: 5] : 5'd0;
   channel_rx_kind<=enabled ? entry[266 +: 10] : 10'd0;
   channel_rx_seq<=enabled ? entry[276 +: 50] : 50'd0;
   channel_rx_last<=enabled ? entry[326 +: 5] : 5'd0;
   channel_tx_beat_slot<=enabled ? entry[331 +: 5] : 5'd0;
   channel_tx_frame_slot<=enabled ? entry[336 +: 5] : 5'd0;
   channel_tx_phase<=enabled ? entry[341 +: 10] : 10'd0;
   channel_rx_beat_slot<=enabled ? entry[351 +: 5] : 5'd0;
   channel_rx_frame_slot<=enabled ? entry[356 +: 5] : 5'd0;
   channel_rx_phase<=enabled ? entry[361 +: 10] : 10'd0;
   hc_reduce_slot<=enabled ? entry[371 +: 1] : 1'd0;
   hc_write_slot<=enabled ? entry[372 +: 1] : 1'd0;
   hc_word_index<=enabled ? entry[373 +: 4] : 4'd0;
   hc_expect_seq<=enabled ? entry[377 +: 16] : 16'd0;
   hc_expect_last<=enabled ? entry[393 +: 1] : 1'd0;
   hc_emit_slot<=enabled ? entry[394 +: 1] : 1'd0;
   hc_emit_tag<=enabled ? entry[395 +: 32] : 32'd0;
   commit_gather<=enabled ? entry[427 +: 1] : 1'd0;
   raw_capture_payload_slot<=enabled ? entry[428 +: 1] : 1'd0;
   raw_capture_meta_slot<=enabled ? entry[429 +: 1] : 1'd0;
   raw_rx_write_slot<=enabled ? entry[430 +: 1] : 1'd0;
   raw_rx_payload_row<=enabled ? entry[431 +: 14] : 14'd0;
   raw_rx_meta_row<=enabled ? entry[445 +: 14] : 14'd0;
   raw_rx_tag<=enabled ? entry[459 +: 8] : 8'd0;
   hc_assemble_slot<=enabled ? entry[467 +: 1] : 1'd0;
   online<=CONFIGURED && rom_valid_q && entry[RW-1];
   c_done<=0;
   if(datapath_fault)fault<=1;
   if(running && !fault) begin
    if(row_bad || datapath_fault)begin fault<=1;active<=0;end
    else begin
     c_done<=entry[CB+85+:9];
     if(entry[RW-2])begin active<=0;cursor<=0;end
     else if((active ? int'(cursor):0)==CYCLES-1)begin fault<=1;active<=0;end
     else begin active<=1;cursor<=AW'((active ? int'(cursor):0)+1);end
    end
   end
  end
 end
endmodule
