// Model: tools/hbm_sm_program_provider_model.py. Default off, local clock/POR.
// Reads the original 10 uint32 native record words without ISA translation.
// Region ends are sector-aligned, exclusive; padding belongs to installation.
// Real issuer supplies request_tag and full ownership at service boundary.
module ot_hbm_sm_program_word #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire region_valid,input wire[31:0] virtual_base,input wire[32:0] virtual_limit,
 input wire[36:0] physical_base,input wire[15:0] request_tag,
 input wire mem_req_valid,output wire mem_req_ready,input wire[31:0] mem_req_addr,
 output wire mem_rsp_valid,input wire mem_rsp_ready,output wire[31:0] mem_rsp_addr,mem_rsp_data,
 output wire mem_rsp_error,
 output wire service_req_valid,input wire service_req_ready,output wire[36:0] service_req_addr,
 output wire[15:0] service_req_tag,
 input wire service_rsp_valid,output wire service_rsp_ready,input wire service_rsp_we,
 input wire[15:0] service_rsp_tag,input wire[255:0] service_rsp_data,input wire service_fault,
 output wire fault
);
 localparam[3:0] IDLE=4'b0001,SEND=4'b0010,WAIT=4'b0100,OUT=4'b1000;
 (* keep=1 *) reg[3:0] state;
 (* keep=1 *) reg[31:0] saved_addr,saved_data;
 (* keep=1 *) reg[36:0] saved_phys;
 (* keep=1 *) reg[15:0] saved_tag;
 (* keep=1 *) reg parity;
 reg sticky;
 wire[32:0] offset={1'b0,mem_req_addr}-{1'b0,virtual_base};
 wire[37:0] full_phys={1'b0,physical_base}+{{5{1'b0}},offset};
 wire[32:0] region_bytes=virtual_limit-{1'b0,virtual_base};
 wire[37:0] physical_end={1'b0,physical_base}+{{5{1'b0}},region_bytes};
 wire bounds_ok=region_valid && virtual_base[4:0]==0 && virtual_limit[4:0]==0 &&
   physical_base[4:0]==0 && virtual_limit<=33'h100000000 && virtual_limit>{1'b0,virtual_base} &&
   mem_req_addr[1:0]==0 && mem_req_addr>=virtual_base &&
   ({1'b0,mem_req_addr}+33'd4)<=virtual_limit && !full_phys[37] && physical_end<=38'h2000000000;
 wire state_ok=state==IDLE||state==SEND||state==WAIT||state==OUT;
 wire parity_ok=parity==^{saved_addr,saved_phys,saved_tag,saved_data};
 wire protocol_error=(service_rsp_valid && (state!=WAIT || service_rsp_we || service_rsp_tag!=saved_tag));
 wire invalid_request=mem_req_valid && state==IDLE && !bounds_ok;
 wire blocked=sticky || !state_ok || !parity_ok || protocol_error || invalid_request || service_fault;
 assign fault=ENABLE && blocked;
 assign mem_req_ready=ENABLE && state==IDLE && bounds_ok && !blocked;
 assign mem_rsp_valid=ENABLE && state==OUT && !blocked;
 assign mem_rsp_addr=saved_addr;assign mem_rsp_data=saved_data;
 // Fault is a sticky sideband; no poisoned word is published as a completion.
 assign mem_rsp_error=1'b0;
 assign service_req_valid=ENABLE && state==SEND && !blocked;
 assign service_req_addr=saved_phys;assign service_req_tag=saved_tag;
 assign service_rsp_ready=ENABLE && state==WAIT && !blocked;
 wire[31:0] selected_word=service_rsp_data[saved_addr[4:2]*32+:32];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;saved_addr<=0;saved_phys<=0;saved_tag<=0;saved_data<=0;parity<=0;sticky<=0;end
  else if(ENABLE)begin
   if(blocked)sticky<=1;
   else begin
    if(mem_req_valid&&mem_req_ready)begin
     saved_addr<=mem_req_addr;saved_phys<={full_phys[36:5],5'b0};saved_tag<=request_tag;saved_data<=0;
     parity<=^{mem_req_addr,{full_phys[36:5],5'b0},request_tag,32'b0};state<=SEND;
    end
    if(service_req_valid&&service_req_ready)state<=WAIT;
    if(service_rsp_valid&&service_rsp_ready)begin
     saved_data<=selected_word;parity<=^{saved_addr,saved_phys,saved_tag,selected_word};state<=OUT;
    end
    if(mem_rsp_valid&&mem_rsp_ready)state<=IDLE;
   end
  end
 end
endmodule
