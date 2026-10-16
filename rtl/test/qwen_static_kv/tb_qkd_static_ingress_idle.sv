`timescale 1ns/1ps
// Observation-only source test: busy comes from real pins/registers, never active.
module tb_qkd_static_ingress_idle;
 reg ck=0,rst_n=0;always #0.5 ck=~ck;
 reg [1151:0] we=0;reg [3:0] pv=0;wire gi,gf;
 wire [1151:0] ge;wire [317:0] gc;wire [3:0] gv;wire [60:0] gx;
 wire [28:0] ga;wire [19:0] gp;wire [1:0] gs;
 qkd_static_writer_group #(.NATIVE_FULL_SECTOR(1))g(
 .ck(ck),.rst_n(rst_n),.cfg_stack(2'd0),.cfg_group(3'd0),
 .writer_es(we),.writer_pc(20'd0),.writer_stack(2'd1),.writer_identity(59'd0),.writer_generation(2'd0),
 .programme_valid(pv),.programme_pc(20'd0),.programme_stack(2'd1),.programme_identity(59'd0),.programme_generation(2'd0),.programme_address(29'd0),
 .pc_es(ge),.pc_context(gc),.pc_expected_valid(gv),.pc_expected_identity(gx),.pc_expected_address(ga),.pc_expected_pc(gp),.pc_expected_stack(gs),.fault(gf),.idle(gi));
 reg nv=0,hostv=0;reg [260:0] er=0;reg cv=0;wire mi,mf;
 wire [287:0] oe;wire [317:0] oc;wire ov;wire [60:0] oi;wire [28:0] oa;wire [4:0] op;wire [1:0] os;
 wire [260:0] hr;wire hv,hw;
 qkd_static_writer_pc_mux m(.ck(ck),.rst_n(rst_n),.native_mode(1'b1),.ownership_valid(1'b1),
 .native_es({287'd0,nv}),.native_context({1'b1,61'd0,{256{1'b1}}}),.native_expected_valid(nv),
 .native_expected_identity(61'd0),.native_expected_address(29'd0),.native_expected_pc(5'd0),.native_expected_stack(2'd0),
 .host_es({287'd0,hostv}),.ctrl_er(er),.ctrl_completion_v(cv),.ctrl_completion_we(1'b0),
 .es(oe),.es_context(oc),.es_expected_valid(ov),.es_expected_identity(oi),.es_expected_address(oa),.es_expected_pc(op),.es_expected_stack(os),
 .host_er(hr),.host_completion_v(hv),.host_completion_we(hw),.fault(mf),.idle(mi));
 task tick;begin @(negedge ck);end endtask
 initial begin
  repeat(3)tick();rst_n=1;repeat(5)tick();
  if(!gi||!mi||gf||mf)$fatal(1,"empty actual pipeline not quiet");
  pv=4'hf;we[0]=1;we[288]=1;we[576]=1;we[864]=1;nv=1;tick();
  if(gi||mi)$fatal(1,"real input capture reported quiet");
  pv=0;we=0;nv=0;tick();if(gi||mi)$fatal(1,"captured pending work reported quiet");
  repeat(4)tick();if(!gi||!mi||gf||mf)$fatal(1,"real pipeline flush not observed");
  er[259]=1;tick();if(mi)$fatal(1,"real credit return reported quiet");er=0;repeat(3)tick();
  cv=1;tick();if(mi)$fatal(1,"real completion reported quiet");cv=0;repeat(3)tick();
  // Real diagnostic failure must keep quiet false after the traffic has gone.
  we[0]=1;hostv=1;tick();we=0;hostv=0;repeat(5)tick();
  if(!gf||!mf||gi||mi)$fatal(1,"sticky source fault allowed quiet");
  $display("INGRESS_IDLE PASS raw_capture pending_register flush credit completion stickyfault; observation_only1 data_edges_unchanged");$finish;
 end
endmodule
