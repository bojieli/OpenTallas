`timescale 1ns/1ps
// Concrete observer -> existing lifecycle-controller wiring. Acquisition consumes
// the held PHYSICAL record observation at the actual matching command handshake.
// The enclosing top gates cmd_valid/cmd_ready with command_allow; it does not
// manufacture reader ownership from an RPC or tie event_ready to a constant.
module ot_gpu_qwen_kv_metadata_join #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable,
 input wire event_valid, output wire event_ready,
 input wire [2:0] event_kind, input wire [63:0] event_identity, event_producer,
 input wire [19:0] event_key,
 input wire command_valid, controller_command_ready,
 input wire [2:0] command_op, input wire [63:0] command_identity, command_producer,
 input wire [19:0] command_key, output wire command_allow,
 output wire metadata_valid, input wire metadata_ready,
 output wire [63:0] metadata_identity, output wire [19:0] metadata_key,
 output wire metadata_record,
 output wire reader_metadata_valid, input wire reader_metadata_ready,
 output wire [63:0] reader_metadata_identity, output wire [19:0] reader_metadata_key,
 output wire reader_metadata_stage,
 output reg fault
);
 wire active=ENABLE && por_n && run_enable && !fault;
 wire acquire_match=event_kind==2 && event_identity==command_identity &&
     event_key==command_key && event_producer==command_producer;
 assign command_allow=active && (command_op!=4 || (event_valid && acquire_match));
 assign metadata_valid=active && event_valid && event_kind<2;
 assign metadata_identity=event_identity; assign metadata_key=event_key;
 assign metadata_record=event_kind==1;
 assign reader_metadata_valid=active && event_valid && (event_kind==3 || event_kind==4);
 assign reader_metadata_identity=event_identity; assign reader_metadata_key=event_key;
 assign reader_metadata_stage=event_kind==4;
 assign event_ready=active && (event_kind<2 ? metadata_ready :
     event_kind==2 ? command_valid && controller_command_ready && command_op==4 && acquire_match :
     (event_kind==3 || event_kind==4) ? reader_metadata_ready : 1'b0);
 always @(posedge clk or negedge por_n) begin
  if(!por_n) fault<=0;
  else if(active && event_valid) begin
   if(event_kind>4) fault<=1;
   if(command_valid && command_op==4 && event_kind==2 && !acquire_match) fault<=1;
  end
 end
endmodule
