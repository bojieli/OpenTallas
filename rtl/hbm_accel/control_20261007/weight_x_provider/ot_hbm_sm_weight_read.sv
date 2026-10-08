// One reserved request permission, exact production REQCR=1 ready latency2.
module ot_hbm_sm_weight_read #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire installed_valid,input wire[31:0] installed_line_base,
 input wire[32:0] installed_line_limit,
 input wire req_v,output wire req_ready,input wire[31:0] req_addr,input wire[9:0] req_tag,
 output wire rsp_v,output wire[9:0] rsp_tag,output wire[1087:0] rsp_data,
 input wire[15:0] issuer_tag,
 output wire service_req_valid,input wire service_req_ready,output wire[36:0] service_req_addr,
 output wire[15:0] service_req_tag,input wire service_rsp_valid,output wire service_rsp_ready,
 input wire service_rsp_we,input wire[15:0] service_rsp_tag,input wire[255:0] service_rsp_data,
 input wire service_fault,output wire fault
);
 localparam[4:0] GRANT=1,FLIGHT=2,LAND=4,SEND=8,WAIT=16;
 (* keep=1 *)reg[4:0] state;(* keep=1 *)reg[41:0] q;(* keep=1 *)reg parity;reg sticky;
 wire[39:0] byte_address=40'(req_addr)*40'd160;
 wire legal=installed_valid&&req_addr>=installed_line_base&&{1'b0,req_addr}<installed_line_limit&&
  installed_line_limit<=33'h100000000&&byte_address+40'd160<=40'h2000000000;
 wire av,ar,ov,af;wire[1279:0] assembled;
 wire blocked=sticky||af||parity!=(^q)||!(state==GRANT||state==FLIGHT||state==LAND||state==SEND||state==WAIT)||
 (req_v&&(state!=LAND||!legal))||(ov&&assembled[1279:1088]!=0);
 assign fault=(ENABLE!=0)&&blocked;
 assign req_ready=(ENABLE!=0)&&state==GRANT&&installed_valid&&!blocked;
 assign av=(ENABLE!=0)&&state==SEND&&!blocked;
 assign rsp_v=(ENABLE!=0)&&state==WAIT&&ov&&!blocked;
 assign rsp_tag=q[9:0];assign rsp_data=assembled[1087:0];
 ot_hbm_sm_sector_read #(.ENABLE(ENABLE),.N(5)) sectors(
 .clk(clk),.rst_n(rst_n),.in_valid(av),.in_ready(ar),.in_base(37'(q[41:10])*37'd160),.in_tag(issuer_tag),
 .out_valid(ov),.out_ready(rsp_v),.out_data(assembled),.fault(af),.*);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=GRANT;q<=0;parity<=0;sticky<=0;end
  else if(ENABLE!=0)begin
   if(blocked)sticky<=1;
   else case(state)
    GRANT:if(req_ready)state<=FLIGHT;
    FLIGHT:state<=LAND;
    LAND:if(req_v)begin q<={req_addr,req_tag};parity<=^{req_addr,req_tag};state<=SEND;end else state<=GRANT;
    SEND:if(ar)state<=WAIT;
    WAIT:if(rsp_v)state<=GRANT;
    default:sticky<=1;
   endcase
  end
 end
endmodule
