`timescale 1ns/1ps
`default_nettype none
// AXI-Lite installation is the elastic host boundary. Native execution below
// this boundary remains compiler fixed-cycle with no runtime ready input.
module host_su_axi_install #(
 parameter integer LINE_BITS=9688,EDGES=7111,
 parameter integer COLS=(LINE_BITS+255)/256,
 parameter integer DICT_ENTRIES[0:COLS-1]='{default:1},
 parameter integer DICT_BANKS[0:COLS-1]='{default:1},
 parameter integer MACROS=((COLS+15)/16)*((EDGES+127)/128)+COLS,
 parameter integer MUT_READY=0
)(input wire clk,rst_n,input wire[MACROS-1:0] clk_macro,
 input wire[11:0] s_awaddr,input wire s_awvalid,output wire s_awready,
 input wire[31:0] s_wdata,input wire[3:0] s_wstrb,input wire s_wvalid,output wire s_wready,
 output reg[1:0] s_bresp,output reg s_bvalid,input wire s_bready,
 input wire[11:0] s_araddr,input wire s_arvalid,output wire s_arready,
 output reg[31:0] s_rdata,output reg[1:0] s_rresp,output reg s_rvalid,input wire s_rready,
 output wire block_ready,busy,valid,done,fault,
 output wire[15:0] edge_index,output wire[LINE_BITS-1:0] command);
 reg aw_pending,w_pending;reg[11:0] awaddr;
 reg[31:0] wdata;reg[3:0] wstrb;
 reg[22:0] selector;reg selector_valid;reg[2:0] chunk;
 reg[255:0] payload;reg[15:0] length;
 wire cfg_ready,cfg_accept;
 wire execute=aw_pending&&w_pending&&!s_bvalid;
 wire full_write=wstrb==4'hf;
 wire config_word=execute&&full_write&&awaddr==12'hf38&&selector_valid;
 wire cfg_v=config_word&&chunk==7;
 wire[255:0] cfg_data={wdata,payload[223:0]};
 wire validate_v=execute&&full_write&&awaddr==12'hf3c&&wdata==1&&!selector_valid&&cfg_ready;
 wire launch_v=execute&&full_write&&awaddr==12'hf44&&wdata==1&&!selector_valid&&block_ready&&length!=0&&length<=EDGES;
 assign s_awready=rst_n&&!aw_pending&&!s_bvalid;
 assign s_wready=rst_n&&!w_pending&&!s_bvalid;
 assign s_arready=rst_n&&!s_rvalid;
 host_su_target #(.LINE_BITS(LINE_BITS),.EDGES(EDGES),.DICT_ENTRIES(DICT_ENTRIES),.DICT_BANKS(DICT_BANKS),.MACROS(MACROS),.MUT_READY(MUT_READY)) target(
  .clk(clk),.rst_n(rst_n),.clk_macro(clk_macro),.cfg_v(cfg_v),.cfg_bank(selector[15:0]),.cfg_row(selector[22:16]),.cfg_data(cfg_data),
  .cfg_ready(cfg_ready),.cfg_accept(cfg_accept),.validate_v(validate_v),.launch_v(launch_v),.length(length),
  .block_ready(block_ready),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   aw_pending<=0;w_pending<=0;awaddr<=0;wdata<=0;wstrb<=0;
   s_bresp<=0;s_bvalid<=0;s_rdata<=0;s_rresp<=0;s_rvalid<=0;
   selector<=0;selector_valid<=0;chunk<=0;payload<=0;length<=0;
  end else begin
   if(s_awvalid&&s_awready)begin aw_pending<=1;awaddr<=s_awaddr;end
   if(s_wvalid&&s_wready)begin w_pending<=1;wdata<=s_wdata;wstrb<=s_wstrb;end
   if(s_bvalid&&s_bready)s_bvalid<=0;
   if(execute)begin
    aw_pending<=0;w_pending<=0;s_bvalid<=1;s_bresp<=2'b10;
    if(full_write)case(awaddr)
     12'hf34:if(cfg_ready&&!selector_valid&&wdata[31:23]==0)begin
      selector<=wdata[22:0];selector_valid<=1;chunk<=0;payload<=0;s_bresp<=0;
     end
     12'hf38:if(selector_valid&&cfg_ready)begin
      if(chunk==7)begin
       chunk<=0;selector_valid<=0;
       if(cfg_accept)s_bresp<=0;
      end else begin payload[chunk*32+:32]<=wdata;chunk<=chunk+1'b1;s_bresp<=0;end
     end
     12'hf3c:if(validate_v)s_bresp<=0;
     12'hf40:if(cfg_ready&&!selector_valid&&wdata>0&&wdata<=EDGES)begin length<=wdata[15:0];s_bresp<=0;end
     12'hf44:if(launch_v)s_bresp<=0;
     default:begin end
    endcase
   end
   if(s_rvalid&&s_rready)s_rvalid<=0;
   if(s_arvalid&&s_arready)begin
    s_rvalid<=1;s_rdata<=0;s_rresp<=0;
    case(s_araddr)
     12'hf34:s_rdata<={9'b0,selector};
     12'hf3c:s_rdata<={24'b0,chunk,selector_valid,cfg_ready,fault,busy,block_ready};
     12'hf40:s_rdata<={16'b0,length};
     12'hf44:s_rdata<=0;
     default:s_rresp<=2'b10;
    endcase
   end
  end
 end
endmodule
`default_nettype wire
