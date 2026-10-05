`timescale 1ps/1ps
module scratch_connected_tb;
 parameter ENABLE_CLIENT=1;
 reg clk=0,por_n=0,run_enable=1,local_reset=0;
 integer cycle=0,accepted_cycle;
 task step;begin #416;clk=1;#417;clk=0;cycle=cycle+1;#1;end endtask
 task need(input ok,input [767:0] text);begin if(ok!==1'b1)$fatal(1,"%s cycle%0d",text,cycle);end endtask
 reg kv_valid=0,kv_write=0,kv_done_ready=0;reg [9:0] kv_addr=0;reg [511:0] kv_wdata=0;
 wire kv_ready,kv_done;wire [511:0] kv_rdata;
 wire [63:0] route_valid,route_write,route_done_ready;
 wire [639:0] route_addr;wire [32767:0] route_wdata;
 wire route_ready0,route_done0;wire [511:0] route_rdata0;wire router_fault,router_drained;
 ot_gpu_qwen_kv_shared_router #(.ENABLE(1)) router(
  .clk(clk),.por_n(por_n),.run_enable(run_enable),
  .kv_valid(kv_valid),.kv_write(kv_write),.kv_rank(1'b0),.kv_SM(5'd0),.kv_addr(kv_addr),.kv_wdata(kv_wdata),
  .kv_ready(kv_ready),.kv_done(kv_done),.kv_done_ready(kv_done_ready),.kv_rdata(kv_rdata),
  .native_valid(64'b0),.native_write(64'b0),.native_addr(640'b0),.native_wdata(32768'b0),
  .native_ready(),.native_done(),.native_done_ready(64'b0),.native_rdata(),
  .service_valid(route_valid),.service_write(route_write),.service_addr(route_addr),.service_wdata(route_wdata),
  .service_ready({63'b0,route_ready0}),.service_done({63'b0,route_done0}),
  .service_rdata({32256'b0,route_rdata0}),.service_done_ready(route_done_ready),.fault(router_fault),.drained(router_drained));
 reg workspace_valid=0,workspace_exclusive=1,client_valid=0,client_write=0,client_done_ready=0;
 reg [54:0] workspace_owner=55'h10203,client_owner=55'h10203;
 reg [238:0] workspace_tuple=0,client_tuple=0;
 reg [9:0] workspace_base=128,client_addr=128;
 reg [10:0] workspace_length=128;reg [511:0] client_wdata=0;
 wire client_ready,client_done;wire [511:0] client_rdata;
 wire service_valid,service_write,service_done_ready,service_ready,service_done;
 wire [9:0] service_addr;wire [511:0] service_wdata,service_rdata;
 wire busy,drained,fault;
 ot_gpu_qwen_scratch_client_mux #(.ENABLE_CLIENT(ENABLE_CLIENT),.INDEX(0)) mux(
  .clk(clk),.por_n(por_n),.run_enable(run_enable),.local_reset(local_reset),
  .workspace_valid(workspace_valid),.workspace_exclusive(workspace_exclusive),.workspace_owner(workspace_owner),
  .workspace_tuple(workspace_tuple),.workspace_base(workspace_base),.workspace_length(workspace_length),
  .client_valid(client_valid),.client_write(client_write),.client_done_ready(client_done_ready),
  .client_addr(client_addr),.client_wdata(client_wdata),.client_owner(client_owner),.client_tuple(client_tuple),
  .client_ready(client_ready),.client_done(client_done),.client_rdata(client_rdata),
  .route_valid(route_valid[0]),.route_write(route_write[0]),.route_done_ready(route_done_ready[0]),
  .route_addr(route_addr[9:0]),.route_wdata(route_wdata[511:0]),.route_ready(route_ready0),.route_done(route_done0),.route_rdata(route_rdata0),
  .service_valid(service_valid),.service_write(service_write),.service_done_ready(service_done_ready),
  .service_addr(service_addr),.service_wdata(service_wdata),.service_ready(service_ready),.service_done(service_done),.service_rdata(service_rdata),
  .busy(busy),.drained(drained),.fault(fault));
 ot_gpu_scratch_service memory(.clk(clk),.rst_n(por_n),.valid(service_valid),.write(service_write),
  .addr(service_addr),.wdata(service_wdata),.ready(service_ready),.done(service_done),.done_ready(service_done_ready),.rdata(service_rdata));
 task route_store(input [9:0] address,input [511:0] data);begin
  kv_addr=address;kv_wdata=data;kv_write=1;kv_valid=1;#1;need(kv_ready,"actual route request refused");accepted_cycle=cycle;step();kv_valid=0;#1;
  need(kv_done&&cycle-accepted_cycle==1,"write actual completion latency/data route");
  kv_done_ready=1;step();kv_done_ready=0;need(!kv_done&&!router_fault,"route write completion lost");
 end endtask
 task route_load(input [9:0] address,input [511:0] data);begin
  kv_addr=address;kv_write=0;kv_valid=1;#1;need(kv_ready,"actual route read refused");accepted_cycle=cycle;step();kv_valid=0;#1;
  need(!kv_done,"read ACK fabricated before actual SRAM data");step();need(kv_done&&kv_rdata==data&&cycle-accepted_cycle==2,"actual route readback/2edge latency");
  kv_done_ready=1;step();kv_done_ready=0;
 end endtask
 reg [511:0] A,B;reg [238:0] captured;
 initial begin
  A={16{32'h12345678}};B={16{32'hcafef00d}};
  workspace_tuple={64'h10203040,11'd5,64'hfedcba9876543210,64'h100000003,1'b0,5'd0,11'd9,9'd1,10'd2};client_tuple=workspace_tuple;captured=workspace_tuple;
  step();por_n=1;step();
  route_store(3,A);route_load(3,A);
  if(!ENABLE_CLIENT)begin
   workspace_valid=1;client_valid=1;client_write=1;client_addr=3;client_wdata=B;
   route_load(3,A);need(!client_ready&&!client_done&&!fault,"defaultoff client created completion");
   $display("PASS_DEFAULTOFF_ACTUAL_ROUTER_TWO_SRAMS cycles%0d",cycle);$finish;
  end
  // OLD admitted route must finish even if the new workspace is published.
  kv_addr=4;kv_write=1;kv_wdata=A;kv_valid=1;#1;need(kv_ready,"old routed command refused");step();kv_valid=0;workspace_valid=1;#1;
  need(kv_done&&!fault,"workspace grant blocked admitted OLD route");kv_done_ready=1;step();kv_done_ready=0;
  client_valid=1;client_write=1;client_addr=128;client_wdata=B;#1;need(client_ready,"owned client command refused");accepted_cycle=cycle;step();client_valid=0;#1;
  need(client_done&&cycle-accepted_cycle==1&&!kv_done,"client write completion not actual destination");
  // Live offer metadata can change; completion stays with accepted command.
  client_tuple=0;client_owner=0;repeat(2)begin step();need(client_done&&busy&&!route_done0,"held actual client completion lost/retagged");end
  client_done_ready=1;step();client_done_ready=0;need(!busy&&drained,"actual client write handshake didn't retire command");
  client_tuple=captured;client_owner=workspace_owner;client_addr=128;client_write=0;client_valid=1;#1;need(client_ready,"client read refused");accepted_cycle=cycle;step();client_valid=0;
  need(!client_done,"client read fabricated early");step();need(client_done&&client_rdata==B&&cycle-accepted_cycle==2,"actual client SRAM readback/2edge latency");
  local_reset=1;client_done_ready=1;repeat(2)begin step();need(busy&&!client_done&&!service_done_ready,"warm pause erased debt or consumed reply");end
  local_reset=0;#1;need(client_done&&client_rdata==B,"warm resume lost actual held SRAM data");step();client_done_ready=0;
  // Actual router remains usable outside the held exclusive workspace.
  route_load(3,A);
  kv_addr=128;kv_write=0;kv_valid=1;repeat(2)begin #1;need(!kv_ready&&!service_valid,"NEW router command entered owned workspace");step();end kv_valid=0;
  workspace_valid=0;route_load(128,B); // Same real memory, no copied backing store.
  // Lease identity loss while a real write response is held must quarantine.
  workspace_valid=1;client_write=1;client_valid=1;client_addr=129;client_wdata=A;#1;need(client_ready,"last real client write refused");step();client_valid=0;
  workspace_tuple=captured ^ (239'b1<<99);client_done_ready=1;#1;
  need(fault&&busy&&!client_done&&!service_done_ready,"changed native64 generation consumed ACK");step();workspace_tuple=captured;repeat(2)step();
  need(fault&&busy&&service_done&&!client_done&&!client_ready,"sticky lease identity failure erased actual SRAM debt");
  $display("PASS_CONNECTED_ROUTER_OWNED_CLIENT_ACTUAL_64KIB write1 read2 cycles%0d",cycle);$finish;
 end
endmodule
