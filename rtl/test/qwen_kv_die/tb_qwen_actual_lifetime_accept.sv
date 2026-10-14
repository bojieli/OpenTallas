`timescale 1ns/1ps
// Source-bound actual production post-IREG GO admission. No global seal implied.
module tb_qwen_actual_lifetime_accept;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg step=1;wire hit;wire cc=clk&&step&&hit;
 reg rst_n=0,ack=0,fence=0;wire go;
 wire [378:0] ib;wire [15:0] ctx;wire [31:0] ver;
 reg offer=0,acq_ready=0,flush_ack=0,ack_allowed=0;reg [378:0] offer_ib=0;
 wire ready,acquire,release_v,flush_req,ctrl_fault,begin_banks,held_mode;
 wire actual_callback=(at!=ack)&&ack_allowed;
 wire callback=(MUT==1)?oa:actual_callback;
 wire [127:0] response;reg lv=0;reg [20:0] le=0;reg lm=0;reg [15:0] lc=0;reg [31:0] lver=0;reg [95:0] la=0;wire cache_fault;integer fills=0,callbacks=0,baseedges=0;
 ot_qwen_xdelivery_lifetime_ctrl #(.ENABLE(1),.TILES(768),.BANKS(16)) controller(
 .clk(clk),.rst_n(rst_n),.offer_v(offer),.offer_ready(ready),.offer_ib(offer_ib),.offer_mode(offer_ib[150]),.offer_participants({768{1'b1}}),
 .acquire_v(acquire),.acquire_ready(acq_ready),.acquire_version(32'd101),.held_ib(ib),.held_mode(held_mode),.held_context(ctx),.held_version(ver),.dispatch_v(go),
 .accept_v(callback),.accept_tile(10'd767),.accept_context(actx),.accept_version(aver),.accept_ib((MUT==2)?offer_ib:aib),
 .banks_begin(begin_banks),.bank_drained(16'd0),.source_output_drained(1'b0),.release_v(release_v),.release_ready(1'b0),.flush_req(flush_req),.transport_flush_ack(flush_ack),.fault(ctrl_fault));
 ot_qwen_xcache_context32 cache(.load_clk(clk),.core_clk(cc),.rst_n(rst_n),.clear(1'b0),.live_j_repeat(1'b1),.read_j_repeat(mode),.load_j_repeat(lm),
 .load_v(lv),.load_epoch(le),.read_epoch(epoch),.load_context(lc),.read_context(qctx),.load_version(lver),.read_version(qver),.load_addr(la),.read_addr(xa),
 .load_x({4{32'h3f800000}}),.read_v(xr),.hit(hit),.q_x(response),.fault(cache_fault));
 always @(negedge clk)begin lv=!hit;le=epoch;lm=mode;lc=qctx;lver=qver;la=xa;end
 always @(posedge clk)begin baseedges=baseedges+1;if(rst_n&&lv)fills=fills+1;if(actual_callback)begin callbacks=callbacks+1;ack<=at;end end
 wire [3:0] xr;wire [95:0] xa;wire [20:0] epoch;
 wire [15:0] qctx,actx;wire [31:0] qver,aver;
 wire mode,oa,idle,at,af,last;wire [378:0] aib;wire fault,tv;
 wire [511:0] tout;
 ot_qwen_rom_tile_nkt_tp8_core_ctx dut(
 .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),
 .rst_n(rst_n),.tile_id(16'd767),.ib_go(go),.ib(ib),.x_response(response),
 .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(tout),.t_vout(tv),.fault(fault),
 .cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.op_context(ctx),.vm_version(ver),
 .cx_xjrepeat(mode),.cx_xcontext(qctx),.cx_xversion(qver),.cx_op_accept(oa),
 .cx_accepted_context(actx),.cx_accepted_version(aver),.cx_accepted_ib(aib),.cx_core_idle(idle),
 .accept_ack_toggle(ack),.accept_transport_fence(fence),.cx_accept_toggle(at),.cx_admission_fault(af),.cx_issue_last(last));
 `define LOGIC dut.u_ctl.u_logic
 `define ME dut.u_ctl.u_logic.u_me
 integer accepts=0,queries=0,outputs=0,ccedges=0,pauses=0,checks=0;
 reg old_toggle=0;reg [378:0] expected_ib;reg [15:0] expected_ctx;reg [31:0] expected_ver;
 reg accepted=0;reg actual_accept;
 always @(posedge cc)begin
  ccedges=ccedges+1;
  actual_accept=rst_n&&`ME.go&&`ME.ready;
  if(!rst_n)begin accepted=0;old_toggle=0;end
  else if(actual_accept)begin expected_ib=`LOGIC.ib_i;expected_ctx=`LOGIC.op_meta_i[15:0];expected_ver=`LOGIC.op_meta_i[47:16];accepted=1;end
  #1;
  if(rst_n)begin
   if(oa!==actual_accept)$fatal(1,"actual accepted edge mismatch");
   if(actual_accept)begin accepts=accepts+1;if(at===old_toggle)$fatal(1,"acceptance toggle missing");end
   else if(at!==old_toggle)$fatal(1,"toggle without actual acceptance");
   old_toggle=at;
   if(accepted&&(aib!==expected_ib||actx!==expected_ctx||aver!==expected_ver))$fatal(1,"accepted payload lifetime mismatch");
   if(|xr)begin queries=queries+1;if(qctx!==expected_ctx||qver!==expected_ver)$fatal(1,"query accepted-context mismatch");end
   if(tv)outputs=outputs+1;
   if(af||cache_fault)$fatal(1,"unexpected admission fault");
   checks=checks+1;
  end
 end
 always @(posedge clk)if(!step)begin pauses=pauses+1;#1;if(accepted&&(aib!==expected_ib||actx!==expected_ctx||aver!==expected_ver||at!==old_toggle))$fatal(1,"paused payload or callback changed");end
 function automatic [378:0] descriptor(input integer nout,input integer xjs);
  descriptor={18'(nout),18'd1,18'd1,1'b0,24'd0,24'd8,24'd8,24'd1,24'd4096,24'd1,24'(xjs),24'd1,3'd0,4'd9,24'd0,1'b1,24'd0,24'd8,24'd1,1'b0,1'b1,1'b0,1'b0,24'd0};
 endfunction
 task automatic ticks(input integer n);repeat(n)@(negedge clk);endtask
 initial begin
  ticks(4);rst_n=1;ticks(3);if(!flush_req)$fatal(1,"reset fence missing");flush_ack=1;ticks(2);flush_ack=0;
  wait(ready);offer_ib=descriptor(768,17);offer=1;ticks(4);
  if(!acquire||go||accepts)$fatal(1,"offer published before source acquisition");
  // External next offer must never mutate the controller-held descriptor.
  offer_ib=descriptor(0,0);ticks(11);if(go||accepts)$fatal(1,"unreserved descriptor accepted");
  acq_ready=1;ticks(1);acq_ready=0;
  wait(accepts==1);@(negedge clk);step=0;ticks(17);
  // A held registered op_accept is not a base-domain event.
  if(ctrl_fault)$fatal(1,"held acceptance duplicated into controller");
  ack_allowed=1;ticks(3);if(callbacks!=1)$fatal(1,"actual acceptance callback not durable once");
  step=1;ticks(160);
  if(ctrl_fault)$fatal(1,"actual accepted descriptor differs from held offer");
  if(accepts!=1||callbacks!=1)$fatal(1,"held dispatch reaccepted or callback duplicated");
  if(!go||release_v)$fatal(1,"partial real field accepted as whole-field acceptance");
  if(!idle)$fatal(1,"selected real core did not finish");
  if(!controller.accepted[767]||$countones(controller.accepted)!=1)$fatal(1,"actual recipient multiplicity mismatch");
  if(queries!=8||outputs!=8||fills<1||pauses!=20)$fatal(1,"composition coverage q=%0d o=%0d fill=%0d pause=%0d",queries,outputs,fills,pauses);
  $display("PASS actual709+c86 selected-tile acceptance fullGT3072 participant_count768 accepted_count1 queries=%0d outputs=%0d fills=%0d callbacks=%0d coherent_edges=%0d base_edges=%0d release_blocked=1",queries,outputs,fills,callbacks,ccedges,baseedges);$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
// Bench-only synchronous ROM interface provider, arithmetic is not qualified here.
module ot_rom_4096x266_m8(input wire clk,input wire ce_in,input wire [11:0] addr_in,output reg [265:0] rd_out);
 integer l;always @(posedge clk)if(ce_in)begin rd_out<=0;for(l=0;l<32;l=l+1)rd_out[8*l+:8]<=8'(addr_in+l+1);end
endmodule
