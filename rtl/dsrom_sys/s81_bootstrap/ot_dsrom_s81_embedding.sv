// Opt-in cold input path. Storage geometry: dedicated embed.weight 2525 pairs,
// four 4096-row physical leaves/pair; 256 payload bits, no ECC.
// One outstanding request. BF16 -> FP32 is wiring, never a host activation.
module ot_dsrom_s81_embedding (
 input wire clk, rst_n,
 input wire start,
 input wire [16:0] token,
 input wire [46:0] identity,
 input wire [18:0] vm_base,
 output wire req_v, input wire req_ready,
 output wire [13:0] req_macro, output wire [11:0] req_row,
 output wire [46:0] req_identity,
 input wire rsp_v, output wire rsp_ready,
 input wire [255:0] rsp_data,
 input wire [13:0] rsp_macro, input wire [11:0] rsp_row,
 input wire [46:0] rsp_identity,
 output wire vm_v, input wire vm_ready,
 output wire [18:0] vm_address, output wire [511:0] vm_data,
 output wire [46:0] vm_identity,
 output wire busy, output reg done, output reg fault
);
 localparam IDLE=0, REQUEST=1, RESPONSE=2, COMMIT=3;
 reg [1:0] state;
 reg [25:0] source_word;
 reg [8:0] row_word;
 reg [1:0] copy_id;
 reg [18:0] base;
 reg [46:0] context_id;
 reg [255:0] payload;
 assign busy=(state!=IDLE);
 assign req_macro={source_word[25:14],source_word[13],source_word[0]};
 assign req_row=source_word[12:1];
 assign req_identity=context_id;
 assign req_v=(state==REQUEST)&&!fault;
 assign rsp_ready=(state==RESPONSE)&&!fault;
 assign vm_v=(state==COMMIT)&&!fault;
 assign vm_address=base + copy_id*19'd5120 + row_word*19'd16;
 assign vm_identity=context_id;
 for(genvar lane=0;lane<16;lane=lane+1) begin: convert
   assign vm_data[lane*32 +:32]={payload[lane*16 +:16],16'b0};
 end
 always @(posedge clk) begin
   if(!rst_n) begin
     state<=IDLE; source_word<=0; row_word<=0;copy_id<=0;
     base<=0;context_id<=0;payload<=0;done<=0;fault<=0;
   end else begin
     done<=0;
     if(start && busy) fault<=1;
     if(!fault) case(state)
       IDLE: if(start) begin
         if(token>=17'd129280 || vm_base>19'd503808) fault<=1;
         else begin
           source_word<=26'(token)*26'd320;
           row_word<=0;copy_id<=0;base<=vm_base;context_id<=identity;
           state<=REQUEST;
         end
       end
       REQUEST: if(req_v && req_ready) state<=RESPONSE;
       RESPONSE: if(rsp_v && rsp_ready) begin
         if(rsp_macro!=req_macro || rsp_row!=req_row || rsp_identity!=context_id) fault<=1;
         else begin payload<=rsp_data;copy_id<=0;state<=COMMIT;end
       end
       COMMIT: if(vm_v && vm_ready) begin
         if(copy_id!=3) copy_id<=copy_id+1'b1;
         else if(row_word==319) begin done<=1;state<=IDLE;end
         else begin
           row_word<=row_word+1'b1;source_word<=source_word+1'b1;
           copy_id<=0;state<=REQUEST;
         end
       end
       default: fault<=1;
     endcase
   end
 end
endmodule
