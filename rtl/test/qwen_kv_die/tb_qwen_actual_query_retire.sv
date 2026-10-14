`timescale 1ns/1ps
// Actual CEXT2 ctl + RPS1/SPLIT1 children, all25 logical child clocks coherent.
module xcache_actual_tile #(parameter integer XLOCAL=0)(
 input wire cc,input wire rst_n,input wire [15:0] tid,input wire go,
 input wire [378:0] ib,input wire [127:0] xl,output wire [3:0] xr,
 output wire [95:0] xa,output wire [20:0] epoch,output wire [511:0] tout,
 output wire tv,output wire fault
);
 wire [69:0] req;wire [2047:0] rqr;wire [3127:0] ld;wire [583:0] lq;
 wire [71:0] le;wire vd,nf;wire [129:0] rm;reg [2659:0] rd=0;
 genvar i;generate for(i=0;i<8;i=i+1) begin assign le[9*i+:9]=lq[73*i+64+:9];end endgenerate
`ifdef XCACHE_TP8
 generate if(XLOCAL==0) begin:choice_ref
 ot_qwen_tile_ctl_tp8_ref ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
 end else begin:choice
 ot_qwen_tile_ctl_tp8 ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
 end endgenerate
`else
 ot_qwen_tile_ctl #(.XLOCAL(XLOCAL)) ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
`endif
 ot_qwen_tile_kids #(.CODE_BANKS(5),.RPS(0),.MCLK(1),.SPLIT(1)) kids(.clk(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),.rst_n(rst_n),.cx_rreq(req),.cx_rq(),.cx_rqr(rqr),.cx_ld(ld),.cx_lq(lq),.cx_td(512'd0),.cx_tvd(vd),.cx_nfault(nf),.n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(tout),.t_vout(tv),.rom_req_m(rm),.rom_rd(rd));
 integer p,l;always @(posedge cc) for(p=0;p<10;p=p+1) if(rm[13*p+12]) begin
  rd[266*p+:266]<=0;
  for(l=0;l<32;l=l+1) rd[266*p+8*l+:8]<=8'(rm[13*p+:12]+32*(p/5)+l+3*tid+1);
 end
endmodule
`timescale 1ns/1ps
// Source-bound actual production post-IREG GO admission. No global seal implied.
module tb_qwen_actual_query_retire;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg step=1;wire hit;wire query_credit,read_credit;wire query_output_credit;wire cc=clk&&step&&hit&&query_credit&&read_credit&&query_output_credit;
 reg rst_n=0,ack=0,fence=0;wire go;
 wire [378:0] ib;wire [15:0] ctx;wire [31:0] ver;
 reg offer=0,acq_ready=0,flush_ack=0,ack_allowed=0;reg [378:0] offer_ib=0;
 wire ready,acquire,release_v,flush_req,ctrl_fault,begin_banks,held_mode;
 wire actual_callback=(at!=ack)&&ack_allowed;
 wire callback=actual_callback;
 wire [127:0] response;reg lv=0;reg [20:0] le=0;reg lm=0;reg [15:0] lc=0;reg [31:0] lver=0;reg [95:0] la=0;wire cache_fault;wire [39:0] query_seq;wire query_toggle,query_fault;reg query_ack=0,fill_ack=0,response_ack=0;wire fill_toggle,response_toggle,load_ready;wire [246:0] fill_tuple,response_tuple;wire [47:0] issue_ready;wire bank_drained,bank_fault;integer issues=0;
 wire query_fire=(MUT==1)?(|xr):(query_toggle!=query_ack);
 wire [47:0] issue_valid={query_fire&&ack_allowed,47'd0};
 wire [47:0] no_events=0;wire [47:0] retire_ready;wire query_output_toggle;wire [87:0] query_output_tuple;reg query_output_ack=0,retire_allowed=1;always @(negedge clk)retire_allowed<=(baseedges%13!=3)&&(baseedges%13!=4);wire retire_fire=(query_output_toggle!=query_output_ack)&&retire_allowed;wire [47:0] retire_valid={retire_fire,47'd0};integer retirements=0;
 wire [511:0] reference_output;wire reference_valid,reference_fault;wire [3:0] unused_re;wire [95:0] unused_addr;wire [20:0] unused_epoch;
 xcache_actual_tile #(.XLOCAL(0)) reference_tile(cc,rst_n,16'd767,go&&!accepted,ib,{4{32'h3f800000}},unused_re,unused_addr,unused_epoch,reference_output,reference_valid,reference_fault);
 ot_qwen_xdelivery_ack_vector #(.ENABLE(1),.N(48),.SEQ_W(40),.COUNT_W(7)) bank15(
 .clk(clk),.rst_n(rst_n),.begin_v(begin_banks),.fenced_clear(1'b0),.begin_context(ctx),.begin_version(ver),.participant_mask({48{1'b1}}),
 .issue_v(issue_valid),.issue_ready(issue_ready),.issue_seq({query_seq,1880'd0}),.issue_context({qctx,752'd0}),.issue_version({(MUT==2)?32'd999:qver,1504'd0}),
 .retire_v(retire_valid),.retire_ready(retire_ready),.retire_seq({query_output_tuple[39:0],1880'd0}),.retire_context({query_output_tuple[87:72],752'd0}),.retire_version({query_output_tuple[71:40],1504'd0}),.seal_v(no_events),.seal_context(768'd0),.seal_version(1536'd0),.drained(bank_drained),.fault(bank_fault));integer fills=0,callbacks=0,baseedges=0;
 ot_qwen_xdelivery_lifetime_ctrl #(.ENABLE(1),.TILES(768),.BANKS(16)) controller(
 .clk(clk),.rst_n(rst_n),.offer_v(offer),.offer_ready(ready),.offer_ib(offer_ib),.offer_mode(offer_ib[150]),.offer_participants({768{1'b1}}),
 .acquire_v(acquire),.acquire_ready(acq_ready),.acquire_version(32'd101),.held_ib(ib),.held_mode(held_mode),.held_context(ctx),.held_version(ver),.dispatch_v(go),
 .accept_v(callback),.accept_tile(10'd767),.accept_context(actx),.accept_version(aver),.accept_ib(aib),
 .banks_begin(begin_banks),.bank_drained(16'd0),.source_output_drained(1'b0),.release_v(release_v),.release_ready(1'b0),.flush_req(flush_req),.transport_flush_ack(flush_ack),.fault(ctrl_fault));
 always @(negedge clk)begin lv=(!hit)&&load_ready;le=epoch;lm=mode;lc=qctx;lver=qver;la=xa;end
 always @(posedge clk)begin
  baseedges=baseedges+1;
  if(!rst_n)begin query_ack<=0;fill_ack<=0;response_ack<=0;query_output_ack<=0;end
  else begin
   fill_ack<=fill_toggle;response_ack<=response_toggle;
   if(lv&&load_ready)fills=fills+1;
   if(issue_valid[47]&&issue_ready[47])begin issues=issues+1;query_ack<=query_toggle;end
   if(retire_valid[47]&&retire_ready[47])begin if(!tv||!reference_valid||tout!==reference_output)$fatal(1,"actual tagged output not numerically consumed");retirements=retirements+1;query_output_ack<=query_output_toggle;end
   if(actual_callback)begin callbacks=callbacks+1;ack<=at;end
  end
  #1;if(rst_n&&bank_fault)$fatal(1,"actual query ledger duplicate or stale event issued=%0d retired=%0d outstanding=%0d actualtuple=%h currentctx=%h ver=%h",bank15.recipient[47].issued,bank15.recipient[47].retired,bank15.recipient[47].outstanding,query_output_tuple,ctx,ver);
 end
 wire [3:0] xr;wire [95:0] xa;wire [20:0] epoch;
 wire [15:0] qctx,actx;wire [31:0] qver,aver;
 wire mode,oa,idle,at,af,last;wire [378:0] aib;wire fault,tv;
 wire [511:0] tout;
 ot_qwen_tile_tp8_output_identity dut(
 .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx_group(cc),.clk_rqr({2{cc}}),.clk_cache_response(cc),.clk_cache_load(clk),.clk_local_drain(cc),.clk_node_lifetime(cc),.clk_query_output_identity(cc),
 .drain_ack_toggle(4'd0),.drain_toggle(),.drain_tuple(),.node_context(16'd0),.node_version(32'd0),.node_sequence(40'd0),.producer_seal_v(1'b0),.producer_seal_context(16'd0),.producer_seal_version(32'd0),
 .node_clear_context(1'b0),.node_retire_ack_toggle(1'b0),.node_accept_ack_toggle(1'b0),.node_credit(),.node_accept_credit(),.node_produced_toggle(),.node_accept_toggle(),.node_drained(),.node_produced_tuple(),.node_accept_tuple(),.node_output_tuple(),.node_output_valid(),.node_active_identity(),
 .query_output_ack_toggle(query_output_ack),.query_output_credit(query_output_credit),.query_output_toggle(query_output_toggle),.query_output_tuple(query_output_tuple),
 .rst_n(rst_n),.tile_id(16'd767),.ib_go(go),.ib(ib),.op_context(ctx),.vm_version(ver),
 .cache_clear(1'b0),.load_v(lv),.load_j_repeat(lm),.load_epoch(le),.load_addr(la),.load_context(lc),.load_version(lver),.load_x({4{32'h3f800000}}),
 .load_token(16'd77),.load_root(5'd31),.load_phase(4'd0),.load_recipient(16'd767),.load_query_seq(query_seq),
 .fill_ack_toggle(fill_ack),.response_ack_toggle(response_ack),.load_ready(load_ready),.read_credit(read_credit),.cache_hit(hit),
 .fill_toggle(fill_toggle),.response_toggle(response_toggle),.fill_tuple(fill_tuple),.response_tuple(response_tuple),
 .cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_xjrepeat(mode),.cx_xcontext(qctx),.cx_xversion(qver),
 .query_ack_toggle(query_ack),.cx_query_seq(query_seq),.cx_query_toggle(query_toggle),.cx_query_credit(query_credit),.cx_query_fault(query_fault),
 .accept_ack_toggle(ack),.accept_transport_fence(fence),.cx_accept_toggle(at),.cx_admission_fault(af),.cx_op_accept(oa),.cx_issue_last(last),
 .cx_accepted_context(actx),.cx_accepted_version(aver),.cx_accepted_ib(aib),.cx_core_idle(idle),
 .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(tout),.t_vout(tv),.fault(fault));
 assign cache_fault=0;
 `define LOGIC dut.u_core.u_ctl.u_logic
 `define ME dut.u_core.u_ctl.u_logic.u_me
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
   if(tv)begin outputs=outputs+1;if(!reference_valid||tout!==reference_output)$fatal(1,"actual arithmetic output mismatch");end
   else if(reference_valid)$fatal(1,"actual arithmetic valid mismatch");
   if(af||cache_fault||query_fault)$fatal(1,"unexpected admission fault");
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
  if(issues!=8||bank15.recipient[47].issued!=8||bank15.recipient[47].outstanding!=0||bank15.recipient[47].retired!=8||retirements!=8||bank_drained)$fatal(1,"actual query ledger obligation mismatch");
  if(queries!=8||outputs!=8||fills<1||pauses!=20)$fatal(1,"composition coverage q=%0d o=%0d fill=%0d pause=%0d",queries,outputs,fills,pauses);
  $display("PASS actual output identity+f9 selected-tile query retire ledger fullGT3072 participant_count768 accepted_count1 queries=%0d outputs=%0d fills=%0d callbacks=%0d coherent_edges=%0d base_edges=%0d release_blocked=1",queries,outputs,fills,callbacks,ccedges,baseedges);$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
// Bench-only synchronous ROM interface provider, arithmetic is not qualified here.
module ot_rom_4096x266_m8(input wire clk,input wire ce_in,input wire [11:0] addr_in,output reg [265:0] rd_out);
 integer l;always @(posedge clk)if(ce_in)begin rd_out<=0;for(l=0;l<32;l=l+1)rd_out[8*l+:8]<=8'(addr_in+l+1);end
endmodule
