`timescale 1ns/1ps
`default_nettype none
// Exact launch ordering from tools/gpu_sys/v41_dspark.py expand(). Full native
// widths. Kernel PCs MUST be installed from linked source images; no defaults.
module ot_hbm_native_mtp_operation_backend #(parameter integer ENABLE=0)(
 input wire clk,rst_n,external_fault,backend_quiescent,
 input wire install_v,input wire [3:0] install_kind,input wire [63:0] install_pc,
 input wire [16:0] noise_token,
 input wire cmd_v,output wire cmd_ready,input wire [200:0] cmd,
 input wire [31:0] cmd_job,input wire [3:0] cmd_generation,
 input wire [31:0] cmd_sequence,input wire [7:0] cmd_epoch,
 output wire cpl_v,input wire cpl_ready,output wire [31:0] cpl_job,
 output wire [3:0] cpl_generation,output wire [31:0] cpl_sequence,
 output wire [7:0] cpl_epoch,output wire cpl_fault,
 output reg am_v,output reg [16:0] am_idx,
 output wire [31:0] launch_v,output wire [63:0] launch_pc,
 output wire [33:0] launch_token,output wire [39:0] launch_pos,
 output wire [145:0] launch_owner,
 input wire [31:0] sm_done,sm_fault,res_v,input wire [1023:0] res_data,
 output wire busy,output reg fault,output reg [31:0] st_launches
);
 import ot_gpu_w6_secded_pkg::*;
 localparam IDLE=0,SELECT=1,LOAD0=2,LOAD1=3,DB=4,WAIT=5,CPL=6;
 reg [2:0] state;reg [5:0] cursor,total;
 reg [71:0] template_pc[0:10];reg [10:0] template_valid,template_invalid;
 reg [71:0] request[0:4];wire [329:0] decoded;
 wire [4:0] request_ue;
 genvar r;
 generate for(r=0;r<5;r=r+1)begin:dec
  wire [65:0] d=decode64(request[r]);assign decoded[r*66+:66]=d;assign request_ue[r]=d[65];
 end endgenerate
 wire [319:0] raw={decoded[264+:64],decoded[198+:64],decoded[132+:64],decoded[66+:64],decoded[0+:64]};
 wire [200:0] held=raw[200:0];
 assign cpl_job=raw[232:201];assign cpl_generation=raw[236:233];
 assign cpl_sequence=raw[268:237];assign cpl_epoch=raw[276:269];
 wire [3:0] op=held[3:0];wire [7:0] idx=held[11:4];wire [3:0] ncol=held[15:12];
 wire [31:0] pos=held[47:16];wire [16:0] tok1=held[64:48];wire [135:0] toks=held[200:65];wire [16:0] held_noise=raw[293:277];
 wire [3:0] iop=cmd[3:0];wire [7:0] iidx=cmd[11:4];wire [3:0] inc=cmd[15:12];wire [31:0] ipos=cmd[47:16];
 wire [32:0] vend={1'b0,ipos}+inc;
 wire [32:0] dend={1'b0,ipos}+6;
 wire valid_shape=(iop<=5) && ipos<1048576 &&
  ((iop==0 && iidx<40 && inc>=1 && inc<=6 && vend<=1048576) ||
   ((iop==1 || iop==2) && iidx==0 && inc>=1 && inc<=6 && vend<=1048576) ||
   (iop==3 && iidx<3 && inc==5 && dend<=1048576) ||
   (iop==4 && iidx==0 && inc==5 && dend<=1048576) ||
   (iop==5 && iidx<5 && inc==1));
 assign cmd_ready=ENABLE && state==IDLE && backend_quiescent && !external_fault;
 assign busy=state!=IDLE;assign cpl_v=ENABLE && state==CPL;assign cpl_fault=fault;
 reg [3:0] kind;reg [16:0] token;reg [19:0] position;
 integer column,part,stride,first_group,local_cursor;
 always @* begin
  kind=0;token=0;position=0;column=0;part=0;stride=0;first_group=0;local_cursor=0;
  case(op)
   0:begin
    stride=(idx==0)?4:3;column=cursor/stride;part=cursor%stride;
    if(part==0)begin kind=0;token=column;position=idx;end
    else if(idx==0 && part==1)begin kind=2;token=toks[column*17+:17];position=pos+column;end
    else if(part==stride-1)begin kind=1;token=column;position=pos+column;end
    else begin kind=3;token=toks[column*17+:17];position=pos+column;end
   end
   1:begin column=cursor/2;if(!cursor[0])begin kind=0;token=column;position=63;end
      else begin kind=4;position=pos+column;end end
   2:begin kind=5;token=cursor;position=pos+cursor;end
   3:begin
    stride=(idx==0)?4:3;first_group=5*stride;
    if(cursor<first_group)begin
     column=cursor/stride;part=cursor%stride;
     if(part==0)begin kind=0;token=8+column;position=40+idx;end
     else if(idx==0 && part==1)begin kind=6;token=(column==0)?tok1:held_noise;position=0;end
     else if(part==stride-1)begin kind=1;token=8+column;position=0;end
     else begin kind=7;token=column;position=pos+1+column;end
    end else begin
     local_cursor=cursor-first_group;column=local_cursor/3;part=local_cursor%3;
     if(part==0)begin kind=0;token=8+column;position=40+idx;end
     else if(part==1)begin kind=8;token=column;position=pos+1+column;end
     else begin kind=1;token=8+column;position=0;end
    end
   end
   4:begin column=cursor/2;
     if(!cursor[0])begin kind=0;token=8+column;position=63;end
     else begin kind=9;token=column;position=pos+1+column;end
   end
   5:begin kind=10;token=tok1;position=idx;end
   default:begin kind=0;token=0;position=0;end
  endcase
 end
 wire [65:0] selected_pc=decode64(template_pc[kind]);
 reg [63:0] pc_q;reg [16:0] token_q;reg [19:0] position_q;
 wire [1:0] cp_ready,cp_valid;wire [7:0] cp_status,cp_gen;
 wire [63:0] cp_job;wire [39:0] cp_position;wire [33:0] cp_token;
 wire both_ready=&cp_ready,both_valid=&cp_valid;
 wire owned=cp_job[31:0]==cpl_job && cp_job[63:32]==cpl_job &&
  cp_gen[3:0]==cpl_generation && cp_gen[7:4]==cpl_generation &&
  cp_position[19:0]==position_q && cp_position[39:20]==position_q;
 wire result_kind=kind==4 || kind==10;
 wire good_status=result_kind?(cp_status==0 && cp_token[16:0]==cp_token[33:17]):(cp_status==8'h22);
 generate for(genvar k=0;k<2;k=k+1)begin:cp
  assign launch_owner[k*73+:73]={launch_pos[k*20+:20],launch_token[k*17+:17],cp_gen[k*4+:4],cp_job[k*32+:32]};
  ot_ds_hbm_cmdproc20_protected #(.ENABLE(ENABLE),.NSM(16),.NCMD(2)) core(
   .clk(clk),.rst_n(rst_n && !external_fault),.cmd_we(state==LOAD0 || state==LOAD1),
   .cmd_addr(state==LOAD1),.cmd_wdata(state==LOAD0?{4'd1,16'hffff,12'b0,pc_q[k*32+:32]}:64'h2000000000000000),
   .db_v(state==DB && both_ready),.db_rdy(cp_ready[k]),.db_token(token_q),.db_pos(position_q),
   .db_job(cpl_job),.db_generation(cpl_generation),.cpl_job(cp_job[k*32+:32]),.cpl_generation(cp_gen[k*4+:4]),.cpl_position(cp_position[k*20+:20]),
   .launch_v(launch_v[k*16+:16]),.launch_pc(launch_pc[k*32+:32]),.launch_token(launch_token[k*17+:17]),.launch_pos(launch_pos[k*20+:20]),
   .sm_done(sm_done[k*16+:16]),.sm_fault(sm_fault[k*16+:16]),.res_v(res_v[k*16+:16]),.res_data(res_data[k*512+:512]),
   .cpl_v(cp_valid[k]),.cpl_rdy(state==WAIT && both_valid),.cpl_token(cp_token[k*17+:17]),.cpl_status(cp_status[k*4+:4]),.cpl_cycles(),.st_kernels(),.st_busy());
 end endgenerate
 integer a;
 wire [319:0] incoming={26'b0,noise_token,cmd_epoch,cmd_sequence,cmd_generation,cmd_job,cmd};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;cursor<=0;total<=0;template_valid<=0;template_invalid<=11'h7ff;
   fault<=0;st_launches<=0;am_v<=0;am_idx<=0;pc_q<=0;token_q<=0;position_q<=0;
   for(a=0;a<5;a=a+1)request[a]<=encode64(0);
  end else begin
   am_v<=0;
   if(ENABLE && install_v && state==IDLE && install_kind<11)begin
    template_pc[install_kind]<=encode64(install_pc);template_valid[install_kind]<=1;template_invalid[install_kind]<=0;
   end
   if(ENABLE && cmd_v && cmd_ready)begin
    for(a=0;a<5;a=a+1)request[a]<=encode64(incoming[a*64+:64]);
    cursor<=0;fault<=0;
    total<=(iop==0)?inc*((iidx==0)?4:3):(iop==1)?inc*2:(iop==2)?inc:(iop==3)?((iidx==0)?35:30):(iop==4)?10:1;
    if(!valid_shape || template_valid!=11'h7ff || template_invalid!=0)begin fault<=1;state<=CPL;end
    else state<=SELECT;
   end
   if(state!=IDLE && state!=CPL && |request_ue)begin fault<=1;state<=CPL;end
   else case(state)
    SELECT:if(selected_pc[65] || !template_valid[kind] || template_invalid[kind])begin fault<=1;state<=CPL;end
      else begin pc_q<=selected_pc[63:0];token_q<=token;position_q<=position;state<=LOAD0;end
    LOAD0:if(!both_ready || |cp_valid)begin fault<=1;state<=CPL;end else state<=LOAD1;
    LOAD1:if(!both_ready || |cp_valid)begin fault<=1;state<=CPL;end else state<=DB;
    DB:if(both_ready)begin st_launches<=st_launches+1'b1;state<=WAIT;end
    WAIT:if(both_valid)begin
      if(!owned || !good_status)begin fault<=1;state<=CPL;end
      else begin
       if(result_kind)begin am_v<=1;am_idx<=cp_token[16:0];end
       if(cursor+1==total)state<=CPL;else begin cursor<=cursor+1'b1;state<=SELECT;end
      end
    end
    CPL:if(cpl_ready)state<=IDLE;
    default:begin end
   endcase
   if(external_fault && state!=IDLE)begin fault<=1;state<=CPL;end
  end
 end
endmodule
`default_nettype wire
