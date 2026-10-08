// Model tools/hbm_sm_weight_x_model.py. Finite exact ordered sector assembly.
module ot_hbm_sm_sector_read #(parameter integer ENABLE=0,N=5)(
 input wire clk,rst_n,input wire in_valid,output wire in_ready,input wire[36:0] in_base,
 input wire[15:0] in_tag,output wire out_valid,input wire out_ready,output wire[N*256-1:0] out_data,
 output wire service_req_valid,input wire service_req_ready,output wire[36:0] service_req_addr,
 output wire[15:0] service_req_tag,input wire service_rsp_valid,output wire service_rsp_ready,
 input wire service_rsp_we,input wire[15:0] service_rsp_tag,input wire[255:0] service_rsp_data,
 input wire service_fault,output wire fault
);
 localparam integer W=37+16+4+N*256;
 localparam[3:0] IDLE=1,SEND=2,WAIT=4,OUT=8;
 (* keep=1 *) reg[W-1:0] q;
 reg[W-1:0] next_q;
 (* keep=1 *) reg parity;
 (* keep=1 *) reg[3:0] state;
 reg sticky;
 wire[36:0] base=q[W-1-:37];wire[15:0] tag=q[N*256+4+:16];wire[3:0] index=q[N*256+:4];
 wire state_ok=state==IDLE||state==SEND||state==WAIT||state==OUT;
 wire bad_input=in_valid&&state==IDLE&&(in_base[4:0]!=0||({1'b0,in_base}+38'(N*32))>38'h2000000000);
 wire blocked=sticky||!state_ok||parity!=(^q)||service_fault||bad_input||
  (service_rsp_valid&&(state!=WAIT||service_rsp_we||service_rsp_tag!=tag));
 assign fault=(ENABLE!=0)&&blocked;
 assign in_ready=(ENABLE!=0)&&state==IDLE&&!blocked;
 assign out_valid=(ENABLE!=0)&&state==OUT&&!blocked;assign out_data=q[N*256-1:0];
 assign service_req_valid=(ENABLE!=0)&&state==SEND&&!blocked;
 assign service_req_addr=base+37'(index)*37'd32;assign service_req_tag=tag;
 assign service_rsp_ready=(ENABLE!=0)&&state==WAIT&&!blocked;
 always @*begin
  next_q=q;
  if(in_valid&&in_ready)next_q={in_base,in_tag,4'b0,{N*256{1'b0}}};
  if(service_rsp_valid&&service_rsp_ready)begin
   next_q[index*256+:256]=service_rsp_data;
   if(index<4'(N-1))next_q[N*256+:4]=index+1'b1;
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin q<=0;parity<=0;state<=IDLE;sticky<=0;end
  else if(ENABLE!=0)begin
   if(blocked)sticky<=1;
   else begin
    q<=next_q;parity<=^next_q;
    if(in_valid&&in_ready)state<=SEND;
    if(service_req_valid&&service_req_ready)state<=WAIT;
    if(service_rsp_valid&&service_rsp_ready)state<=index==4'(N-1)?OUT:SEND;
    if(out_valid&&out_ready)state<=IDLE;
   end
  end
 end
 initial if(N<1||N>15)$fatal(1,"bounded sector count");
endmodule
