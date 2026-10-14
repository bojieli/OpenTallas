`timescale 1ns/1ps
// Source-bound actual production post-IREG GO admission. No global seal implied.
module tb_qwen_actual_admission;
 reg clk=0;always #5 clk=~clk;
 reg step=1;wire cc=clk&&step;
 reg rst_n=0,go=0,ack=0,fence=0;
 reg [378:0] ib=0;reg [15:0] ctx=1;reg [31:0] ver=101;
 wire [3:0] xr;wire [95:0] xa;wire [20:0] epoch;
 wire [15:0] qctx,actx;wire [31:0] qver,aver;
 wire mode,oa,idle,at,af,last;wire [378:0] aib;wire fault,tv;
 wire [511:0] tout;
 ot_qwen_rom_tile_nkt_tp8_core_ctx dut(
 .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),
 .rst_n(rst_n),.tile_id(16'd767),.ib_go(go),.ib(ib),.x_response({4{32'h3f800000}}),
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
   if(af)$fatal(1,"unexpected admission fault");
   checks=checks+1;
  end
 end
 always @(posedge clk)if(!step)begin pauses=pauses+1;#1;if(accepted&&(aib!==expected_ib||actx!==expected_ctx||aver!==expected_ver||at!==old_toggle))$fatal(1,"paused payload or callback changed");end
 function automatic [378:0] descriptor(input integer nout,input integer xjs);
  descriptor={18'(nout),18'd1,18'd1,1'b0,24'd0,24'd8,24'd8,24'd1,24'd4096,24'd1,24'(xjs),24'd1,3'd0,4'd9,24'd0,1'b1,24'd0,24'd8,24'd1,1'b0,1'b1,1'b0,1'b0,24'd0};
 endfunction
 task automatic ticks(input integer n);repeat(n)@(negedge clk);endtask
 initial begin
  ticks(4);rst_n=1;ticks(8);ib=descriptor(768,17);go=1;
  wait(accepts==1);@(negedge clk);step=0;
  // A new offer reaches pins while old acceptance remains unacknowledged.
  ib=descriptor(0,0);ctx=2;ver=102;ticks(17);
  if(accepts!=1)$fatal(1,"paused callback duplicated");
  step=1;ticks(120);
  if(accepts!=1)$fatal(1,"unacknowledged offer accepted");
  // Loader-domain ACK makes the pending offer eligible on a later actual edge.
  ack=at;ticks(4);if(accepts!=2)$fatal(1,"late ACK lost pending GO");
  ticks(100);if(accepts!=2)$fatal(1,"held GO duplicate accepted before ACK");
  ack=at;ticks(140);if(accepts!=2)$fatal(1,"held GO duplicate accepted after ACK");
  go=0;ticks(100);wait(idle);ticks(4);fence=1;ticks(2);fence=0;ticks(4);
  // Transport fence permits same-identity reuse only with GO low, idle and ACK.
  go=1;ticks(120);if(accepts!=3)$fatal(1,"fenced identity reuse lost or duplicated");
  ack=at;ticks(80);if(accepts!=3)$fatal(1,"post-fence held GO duplicate accepted");
  go=0;ticks(10);
  if(queries<16||outputs<8||pauses!=17||checks<500)$fatal(1,"coverage vacuous q=%0d o=%0d p=%0d c=%0d",queries,outputs,pauses,checks);
  $display("PASS actual709 admission accepts=%0d queries=%0d outputs=%0d coherent_edges=%0d pauses=%0d payload_checks=%0d",accepts,queries,outputs,ccedges,pauses,checks);$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
// Bench-only synchronous ROM interface provider, arithmetic is not qualified here.
module ot_rom_4096x266_m8(input wire clk,input wire ce_in,input wire [11:0] addr_in,output reg [265:0] rd_out);
 integer l;always @(posedge clk)if(ce_in)begin rd_out<=0;for(l=0;l<32;l=l+1)rd_out[8*l+:8]<=8'(addr_in+l+1);end
endmodule
