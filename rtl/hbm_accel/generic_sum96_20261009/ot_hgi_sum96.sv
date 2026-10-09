`timescale 1ns/1ps
// Real96 contributor SUM. Memory is a fixed-latency protected SRAM service:
// accepted writes commit on this edge, accepted reads return exactly MEM_LAT
// edges later. No combinational memory mux or inferred storage in this engine.
module ot_hgi_sum96 #(
 parameter integer MEM_LAT=2, ADD_LAT=7,
 parameter integer MUTANT_TREE=0, MUTANT_DROP=0
)(input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire in_valid, output wire in_ready,
 input wire [6:0] in_rank,input wire [3:0] in_tile,input wire [511:0] in_data,
 output reg out_valid,input wire out_ready, output reg [3:0] out_tile,
 output reg [511:0] out_data,output wire out_last,output reg done,output reg fault,
 output wire rd_en,output wire [6:0] rd_addr,input wire [511:0] rd_data,input wire rd_fault,
 output wire wr_en,output wire [6:0] wr_addr,output wire [511:0] wr_data);
 localparam IDLE=0,LOAD=1,REDUCE=2,FLUSH=3,FINAL=4,OUTPUT=5,FAIL=6;
 reg [2:0] state;
 reg [6:0] rank_next,count,issued,returned;
 reg [3:0] tile;
 reg [7:0] flush;
 reg [MEM_LAT-1:0] rv,rf;
 reg [6:0] ri[0:MEM_LAT-1];
 reg [511:0] lhs;
 wire rsp=rv[MEM_LAT-1];
 wire odd=rsp && !rf[MEM_LAT-1] && ri[MEM_LAT-1][0];
 wire carry=rsp && !rf[MEM_LAT-1] && !ri[MEM_LAT-1][0] && ri[MEM_LAT-1]==count-1;
 wire [511:0] sum;
 wire [15:0] sum_v;
 wire [31:0] sum_err;
 reg [ADD_LAT-1:0] tv,tc;
 reg [6:0] ti[0:ADD_LAT-1];
 reg [511:0] carry_data[0:ADD_LAT-1];
 wire result=tv[ADD_LAT-1];
 wire [511:0] result_data=tc[ADD_LAT-1]?carry_data[ADD_LAT-1]:sum;
 assign cmd_ready=state==IDLE;
 assign in_ready=state==LOAD;
 assign out_last=out_tile==15;
 assign rd_en=(state==REDUCE && issued<count) || (state==FINAL && issued==0);
 wire [6:0] natural_addr=(state==FINAL)?7'd0:issued;
 assign rd_addr=(MUTANT_TREE && count==96 && state==REDUCE)?((natural_addr==95)?7'd0:natural_addr+1'b1):natural_addr;
 wire load_write=in_valid && in_ready && in_rank==rank_next && in_tile==tile;
 assign wr_en=load_write || result;
 assign wr_addr=load_write?rank_next:ti[ADD_LAT-1];
 assign wr_data=load_write?((MUTANT_DROP && rank_next==95)?512'd0:in_data):result_data;
 for(genvar g=0;g<16;g=g+1) begin:g_add
 ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(odd),
 .a(lhs[g*32+:32]),.b(rd_data[g*32+:32]),.y(sum[g*32+:32]),.err(sum_err[g*2+:2]),.valid_out(sum_v[g]));
 end
 integer i;
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin state<=IDLE;rank_next<=0;tile<=0;count<=96;issued<=0;returned<=0;
 rv<=0;rf<=0;tv<=0;tc<=0;out_valid<=0;done<=0;fault<=0;flush<=0; end
 else begin
 done<=0;
 rv[0]<=rd_en; rf[0]<=state==FINAL;ri[0]<=issued;
 for(i=1;i<MEM_LAT;i=i+1) begin rv[i]<=rv[i-1];rf[i]<=rf[i-1];ri[i]<=ri[i-1];end
 tv[0]<=odd||carry;tc[0]<=carry;ti[0]<=ri[MEM_LAT-1]>>1;carry_data[0]<=rd_data;
 for(i=1;i<ADD_LAT;i=i+1) begin tv[i]<=tv[i-1];tc[i]<=tc[i-1];ti[i]<=ti[i-1];carry_data[i]<=carry_data[i-1];end
 if(rsp && !rf[MEM_LAT-1] && !ri[MEM_LAT-1][0]) lhs<=rd_data;
 if(result) returned<=returned+1'b1;
 if(rsp && rd_fault) begin fault<=1;state<=FAIL;end
 else case(state)
 IDLE:if(cmd_valid) begin state<=LOAD;tile<=0;rank_next<=0;fault<=0;count<=96;end
 LOAD:if(in_valid) begin
 if(in_rank!=rank_next || in_tile!=tile) begin fault<=1;state<=FAIL;end
 else if(rank_next==95) begin state<=REDUCE;issued<=0;returned<=0;count<=96;end
 else rank_next<=rank_next+1'b1;
 end
 REDUCE:begin
 if(rd_en) issued<=issued+1'b1;
 if(issued==count && returned==((count+1)>>1)) begin state<=FLUSH;flush<=MEM_LAT+1;end
 end
 FLUSH:if(flush!=0) flush<=flush-1'b1;else begin
 count<=(count+1)>>1;issued<=0;returned<=0;
 if(count<=2) state<=FINAL;else state<=REDUCE;
 end
 FINAL:begin
 if(rd_en) issued<=1;
 if(rsp && rf[MEM_LAT-1]) begin
 for(i=0;i<16;i=i+1) out_data[i*32+:32]<=rd_data[i*32+:32]==32'h80000000?32'd0:rd_data[i*32+:32];
 out_tile<=tile;out_valid<=1;state<=OUTPUT;
 end
 end
 OUTPUT:if(out_ready) begin out_valid<=0;
 if(tile==15) begin done<=1;state<=IDLE;end
 else begin tile<=tile+1'b1;rank_next<=0;state<=LOAD;end
 end
 FAIL:begin rv<=0;tv<=0;done<=1;out_valid<=0;state<=IDLE;end
 endcase
 if(result && !tc[ADD_LAT-1] && |sum_err) begin fault<=1;state<=FAIL;end
 end
 end
`ifndef SYNTHESIS
 initial if(MEM_LAT<1 || ADD_LAT<3) $fatal(1,"invalid local pipeline");
`endif
endmodule
