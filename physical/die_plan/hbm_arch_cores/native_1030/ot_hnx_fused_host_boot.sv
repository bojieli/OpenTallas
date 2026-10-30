// Native host target adapter. TARGET0 is deliberately unbound/disabled.
// Payload format is local to this new target; F20/F24/F28/F2c/F30 wire ABI is unchanged.
module ot_hnx_fused_host_boot #(parameter [7:0] TARGET=0)(
 input wire clk,rst_n,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,
 output reg load_v,output reg [7:0] load_addr,output reg [280:0] load_entry,
 output reg cfg_commit,output reg cfg_calendar_bound,output reg [8:0] cfg_count,
 output reg [7:0] cfg_wsc,output reg [5:0] cfg_pk5,output reg cfg_pb5,output reg start,
 input wire provider_armed,provider_busy,provider_done,provider_fault,
 output wire ready,active,output reg fault
);
 reg cv,dv,lv;reg [7:0] target_q;reg [11:0] addr_q,base_q;reg [12:0] limit_q;reg [15:0] loops_q;reg [255:0] data_q;
 always @(posedge clk)begin target_q<=cfg_target;addr_q<=cfg_addr;data_q<=cfg_data;base_q<=desc_base;limit_q<=desc_limit;loops_q<=desc_loops;end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin cv<=0;dv<=0;lv<=0;end else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
 reg [255:0] low_word;reg [9:0] words;reg pending,configured,installed,participating,launched;
 wire hit=(TARGET>=16)&&(target_q==TARGET);
 assign ready=installed&&provider_armed&&!fault&&!provider_fault;
 assign active=provider_busy;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin words<=0;pending<=0;configured<=0;installed<=0;participating<=0;launched<=0;fault<=0;load_v<=0;cfg_commit<=0;start<=0;end
 else begin
 load_v<=0;cfg_commit<=0;start<=0;
 if(provider_done)launched<=0;
 if(provider_fault)begin fault<=1;installed<=0;end
 if((cv||dv)&&hit)begin
  participating<=1;
  if(fault||provider_fault||provider_busy||launched||(cv&&dv)||lv)begin fault<=1;installed<=0;end
  else if(cv)begin
   installed<=0;
   if(addr_q==12'h200)begin
    if(pending||words==0||configured||data_q[255:64]!=0||data_q[63:32]!=32'h46323137||data_q[31:25]!=0||data_q[8:0]==0||data_q[8:0]>256||words!={data_q[8:0],1'b0}||data_q[22:17]>32||!data_q[24])fault<=1;
    else begin cfg_count<=data_q[8:0];cfg_wsc<=data_q[16:9];cfg_pk5<=data_q[22:17];cfg_pb5<=data_q[23];cfg_calendar_bound<=data_q[24];configured<=1;end
   end else if(addr_q>=512||configured||{1'b0,addr_q[8:0]}!=words||words>=512)fault<=1;
   else if(!addr_q[0])begin low_word<=data_q;pending<=1;words<=words+1;end
   else if(!pending||data_q[255:25]!=0)fault<=1;
   else begin load_addr<=addr_q[8:1];load_entry<={data_q[24:0],low_word};load_v<=1;pending<=0;words<=words+1;end
  end else if(dv)begin
   if(!configured||pending||base_q!=0||limit_q!={3'b0,words}||loops_q!=1)begin fault<=1;installed<=0;end
   else begin cfg_commit<=1;installed<=1;end
  end
 end
 if(lv&&participating)begin
  if(fault||provider_fault||!ready||provider_busy||launched||((cv||dv)&&hit))begin fault<=1;installed<=0;end
  else begin start<=1;launched<=1;installed<=0;end
 end
 end end
endmodule
