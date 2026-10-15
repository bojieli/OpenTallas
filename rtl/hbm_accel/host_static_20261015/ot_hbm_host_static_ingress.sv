`timescale 1ns/1ps
`default_nettype none
// Component successor: host elasticity ends at configuration writes. There is
// no record interpreter, credit dispatch, or readiness input during execution.
// F20 selects {reserved12,addr12,target8}; F24 appends eight little-endian
// 32bit pieces; F28={reserved7,limit13,base12}; F2c=loops16; F30=launch1.
// block_ready must be the actual bound targets' validated, fully installed
// aggregate. It is an input obligation, never synthesized from host promises.
// Existing SU bank16/row7 ABI is intentionally not represented by this collar.
module ot_hbm_host_static_ingress #(parameter integer MUT=0, parameter [255:0] TARGET_MASK=(256'd1<<48))(
 input wire clk,rst_n,
 input wire s_awvalid,output reg s_awready,input wire [11:0] s_awaddr,
 input wire s_wvalid,output reg s_wready,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 output reg s_bvalid,input wire s_bready,output reg [1:0] s_bresp,
 input wire s_arvalid,output reg s_arready,input wire [11:0] s_araddr,
 output reg s_rvalid,input wire s_rready,output reg [31:0] s_rdata,
 input wire block_ready,program_active,program_fault,
 output reg cfg_v,output reg [7:0] cfg_target,output reg [11:0] cfg_addr,
 output reg [255:0] cfg_data,
 output reg desc_v,output reg [11:0] desc_base,output reg [12:0] desc_limit,
 output reg [15:0] desc_loops,output reg launch_v,output reg fault
);
 reg aw_hold,w_hold;reg [11:0] aw;reg [31:0] wd;reg [3:0] ws;
 reg [7:0] target;reg [11:0] pc,base;reg [12:0] lim;
 reg [223:0] assembly;reg [2:0] piece;reg range_valid,selected,end_reached;
 reg [2:0] guard;
 reg block_ready_q,active_q,program_fault_q;
 reg launched,seen_active;
 // Delivered status lands in dedicated pin flops. Host service admission is
 // locked from accepted launch through the actual programme active interval;
 // this lock never gates or delays a running programme's fixed schedule.
 wire execute=aw_hold&&w_hold&&!s_bvalid;
 wire launch_ok=block_ready_q&&!active_q&&!program_fault_q&&!fault&&!launched&&piece==0&&guard==0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   s_awready<=0;s_wready<=0;s_arready<=0;block_ready_q<=0;active_q<=0;program_fault_q<=0;launched<=0;seen_active<=0;
   aw_hold<=0;w_hold<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rdata<=0;
   cfg_v<=0;cfg_target<=0;cfg_addr<=0;cfg_data<=0;desc_v<=0;
   desc_base<=0;desc_limit<=0;desc_loops<=0;launch_v<=0;fault<=0;
   target<=0;pc<=0;base<=0;lim<=0;piece<=0;range_valid<=0;selected<=0;end_reached<=0;guard<=0;
  end else begin
   cfg_v<=0;desc_v<=0;launch_v<=0;
   block_ready_q<=block_ready;active_q<=program_active;program_fault_q<=program_fault;
   s_awready<=!aw_hold&&!s_bvalid;
   s_wready<=!w_hold&&!s_bvalid;
   s_arready<=!s_rvalid;
   if(s_awvalid&&s_awready)s_awready<=0;
   if(s_wvalid&&s_wready)s_wready<=0;
   if(s_arvalid&&s_arready)s_arready<=0;
   if(launched&&active_q)seen_active<=1;
   if(launched&&seen_active&&!active_q)begin launched<=0;seen_active<=0;end
   if(guard!=0)guard<=guard-1'b1;
   if(s_awvalid&&s_awready)begin aw_hold<=1;aw<=s_awaddr;end
   if(s_wvalid&&s_wready)begin w_hold<=1;wd<=s_wdata;ws<=s_wstrb;end
   if(s_bvalid&&s_bready)s_bvalid<=0;
   if(s_rvalid&&s_rready)s_rvalid<=0;
   if(s_arvalid&&s_arready)begin
    s_rvalid<=1;s_rdata<=s_araddr==12'hf30 ? {26'd0,guard!=0,piece!=0,program_fault_q,active_q,block_ready_q,fault}:32'hffffffff;
   end
   if(execute)begin
    aw_hold<=0;w_hold<=0;s_bvalid<=1;s_bresp<=0;
    if(ws!=4'hf || active_q || program_fault_q || launched || fault)begin fault<=1;s_bresp<=2;end
    else case(aw)
     12'hf20:begin
      if(piece!=0 || wd[31:20]!=0 || wd[7:0]<16 || !TARGET_MASK[wd[7:0]])begin fault<=1;s_bresp<=2;end
      else begin target<=wd[7:0];pc<=wd[19:8];selected<=1;end_reached<=0;range_valid<=0;end
     end
     12'hf24:begin
      if(!selected || end_reached)begin fault<=1;s_bresp<=2;end
      else begin
       if(piece<7)assembly[piece*32+:32]<=wd;
       piece<=piece+1'b1;
       if(piece==7)begin
        cfg_v<=1;cfg_target<=target;cfg_addr<=pc;
        cfg_data<={wd,assembly} ^ (MUT==1?256'd1:256'd0);
        if(pc==4095)end_reached<=1;else pc<=pc+1'b1;
        guard<=4;
       end
      end
     end
     12'hf28:begin
      if(!selected || piece!=0 || wd[31:25]!=0 || wd[24:12]<={1'b0,wd[11:0]} || wd[24:12]>4096)begin fault<=1;s_bresp<=2;end
      else begin base<=wd[11:0];lim<=wd[24:12];range_valid<=1;end
     end
     12'hf2c:begin
      if(!range_valid || piece!=0 || wd[31:16]!=0 || wd[15:0]==0)begin fault<=1;s_bresp<=2;end
      else begin cfg_target<=target;desc_base<=base;desc_limit<=lim;desc_loops<=wd[15:0];desc_v<=1;guard<=4;end
     end
     12'hf30:begin
      if(wd!=1 || !(MUT==2?(!active_q&&!program_fault_q&&!fault&&!launched&&guard==0):launch_ok))begin fault<=1;s_bresp<=2;end
      else begin launch_v<=1;guard<=7;launched<=1;seen_active<=0;end
     end
     default:begin fault<=1;s_bresp<=2;end
    endcase
   end
  end
 end
endmodule
`default_nettype wire
