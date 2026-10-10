// L1 source-ID workgroup metadata and tagged result steering. No arithmetic,
// packed-weight conversion, or expert reduction. Default off until integration.
module ot_hbm_expert_workgroup #(parameter ENABLE=0)(
 input wire clk,rst_n,
 input wire launch_v, output wire launch_ready,
 input wire [53:0] expert_ids, input wire [6:0] die,
 input wire [7:0] layer, input wire [31:0] job,
 output wire desc_v, input wire desc_ready,
 output wire [4:0] desc_sm, output wire [2:0] desc_slot,
 output wire [8:0] desc_expert, output wire desc_matrix,
 output wire [11:0] desc_row, output wire [31:0] desc_base,
 output wire [8:0] desc_lines, output wire [7:0] desc_layer,
 output wire [31:0] desc_job,
 input wire ret_v, output wire ret_ready, input wire [4:0] ret_sm,
 input wire [8:0] ret_expert, input wire ret_matrix,
 input wire [11:0] ret_row, input wire [31:0] ret_job,
 input wire [7:0] ret_layer, input wire [31:0] ret_bits,
 output wire out_v, input wire out_ready, output wire [31:0] out_bits,
 output wire [2:0] out_slot, output wire out_matrix,
 output wire [11:0] out_row, output wire [31:0] out_job,
 output wire [7:0] out_layer,
 output reg done, output reg fault, output wire busy
);
 reg active; reg [53:0] ids; reg [6:0] d;
 reg [7:0] l; reg [31:0] j; reg [4:0] issued;
 reg [8:0] returned; reg [3:0] row_count[0:23];
 integer k; reg ids_ok;
 always @* begin
   ids_ok=(die<96);
   for(integer n=0;n<6;n=n+1) begin
     if(expert_ids[n*9+:9]>=384) ids_ok=0;
     if(n>0 && expert_ids[(n-1)*9+:9]>=expert_ids[n*9+:9]) ids_ok=0;
   end
 end
 assign launch_ready=ENABLE && !active && !fault;
 assign busy=active;
 assign desc_v=ENABLE && active && !fault && issued<24;
 assign desc_sm=issued;
 assign desc_slot=issued[4:2];
 assign desc_expert=(issued<24)?ids[issued[4:2]*9+:9]:9'b0;
 assign desc_matrix=issued[1];
 assign desc_row=d*24+issued[0]*12;
 assign desc_base=issued*288;
 assign desc_lines=288;
 assign desc_layer=l; assign desc_job=j;
 wire ret_ok=active && ret_sm<24 && ret_sm<issued &&
   ret_job==j && ret_layer==l && ret_matrix==ret_sm[1] &&
   ret_expert==ids[ret_sm[4:2]*9+:9] &&
   row_count[ret_sm]<12 && ret_row==d*24+ret_sm[0]*12+row_count[ret_sm];
 reg ov; reg [31:0] ob,oj; reg [2:0] os;
 reg om; reg [11:0] orow; reg [7:0] ol;
 assign ret_ready=ENABLE && !fault && (ret_ok?(!ov || out_ready):1'b1);
 assign out_v=ENABLE && !fault && ov;
 assign out_bits=ob; assign out_slot=os; assign out_matrix=om;
 assign out_row=orow; assign out_job=oj; assign out_layer=ol;
 always @(posedge clk) begin
   if(!rst_n) begin
     active<=0; ids<=0; d<=0; l<=0; j<=0; issued<=0;
     returned<=0; done<=0; fault<=0;
     ov<=0; ob<=0; oj<=0; os<=0; om<=0; orow<=0; ol<=0;
     for(k=0;k<24;k=k+1) row_count[k]<=0;
   end else begin
     done<=0;
     if(out_v && out_ready) ov<=0;
     if(active && returned==288 && (!ov || out_ready)) begin done<=1; active<=0; end
     if(launch_v && launch_ready) begin
       if(!ids_ok) fault<=1;
       else begin
         active<=1; ids<=expert_ids; d<=die; l<=layer; j<=job;
         issued<=0; returned<=0;
         for(k=0;k<24;k=k+1) row_count[k]<=0;
       end
     end
     if(desc_v && desc_ready) issued<=issued+1;
     if(ret_v && ret_ready) begin
       if(!ret_ok) begin fault<=1; active<=0; end
       else begin
         ov<=1; ob<=ret_bits; oj<=ret_job; os<=ret_sm[4:2];
         om<=ret_matrix; orow<=ret_row; ol<=ret_layer;
         row_count[ret_sm]<=row_count[ret_sm]+1;
         returned<=returned+1;
       end
     end
   end
 end
endmodule
