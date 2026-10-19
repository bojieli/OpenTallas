`timescale 1ns/1ps
module tb_pc_fault_export;
 reg ck=0; always #417 ck=~ck;
 reg rst=0;reg [779:0] di=0; reg [260:0] land_er=0;
 wire chain_fault;wire [287:0] land_es;
 qkd_kv_pc_chain_station_b u_chain(.ck(ck),.rst_n(rst),.pc(5'd0),.cfg_stack(2'd0),.di(di),.dout(),.land_es(land_es),.land_er(land_er),.wes(),.es_context(),.es_expected_valid(),.es_expected_identity(),.es_expected_address(),.es_expected_pc(),.es_expected_stack(),.emb_issue_v(),.emb_token(),.emb_word_index(),.emb_half(),.emb_scale(),.emb_epoch(),.emb_return_slot(),.capture_slot(),.transfer_slot(),.fault(chain_fault));
 reg [287:0] wes=0,hes=0;reg boot_ready=1,issue=0,return_slot=0;reg[260:0] er=0;
 wire merge_fault; wire[287:0] merged;
 qkd_static_kv_pc_es_merge_b u_merge(.ck(ck),.rst_n(rst),.pc(5'd0),.cfg_stack(2'd0),.wes(wes),.emb_boot_ready(boot_ready),.emb_issue_v(issue),.emb_token(18'd0),.emb_word_index(6'd0),.emb_half(1'b0),.emb_scale(1'b0),.emb_epoch(16'd9),.emb_return_slot(return_slot),.hes(hes),.her(),.completion_v(1'b0),.completion_we(1'b0),.hcv(),.hcw(),.es(merged),.er(er),.beat_v(),.beat_data(),.beat_token(),.beat_word(),.beat_half(),.beat_scale(),.beat_epoch(),.corrected(),.emb_outstanding(),.fault(merge_fault));
 reg [281:0] co=0;reg put=0,slot=0;reg[15:0] epoch=0;reg[9:0] sect=0;reg[5:0] layer=0;
 wire [305:0] oldret,newret,offret;wire oldfc,newfc,offfc;
 // Every module is a complete source primitive; the family changes only the fault export equation.
 qkd_static_kv_return_slots_mc_nc u_old(.pll_hbm(ck),.hrst(rst),.ck(ck),.rsi(rst),.pll_hbm_data({4{ck}}),.controller_co(co),.controller_epoch(epoch),.compiled_hbm_put(put),.expected_put(slot),.expected_sector(sect),.expected_epoch(epoch),.expected_layer(layer),.actual_valid(oldret[0]),.actual_sector(oldret[10:1]),.actual_epoch(oldret[26:11]),.actual_layer(oldret[32:27]),.actual_data(oldret[288:33]),.fault_hbm(oldret[289]),.fault_core(oldfc),.idle_hbm(oldret[290]),.idle_core(oldret[291]));
 qkd_static_kv_return_slots_mc_nc_fault_export #(.FAULT_EXPORT(1)) u_new(.extra_core_fault(chain_fault|merge_fault),.pll_hbm(ck),.hrst(rst),.ck(ck),.rsi(rst),.pll_hbm_data({4{ck}}),.controller_co(co),.controller_epoch(epoch),.compiled_hbm_put(put),.expected_put(slot),.expected_sector(sect),.expected_epoch(epoch),.expected_layer(layer),.actual_valid(newret[0]),.actual_sector(newret[10:1]),.actual_epoch(newret[26:11]),.actual_layer(newret[32:27]),.actual_data(newret[288:33]),.fault_hbm(newret[289]),.fault_core(newfc),.idle_hbm(newret[290]),.idle_core(newret[291]));
 qkd_static_kv_return_slots_mc_nc_fault_export u_off(.extra_core_fault(chain_fault|merge_fault),.pll_hbm(ck),.hrst(rst),.ck(ck),.rsi(rst),.pll_hbm_data({4{ck}}),.controller_co(co),.controller_epoch(epoch),.compiled_hbm_put(put),.expected_put(slot),.expected_sector(sect),.expected_epoch(epoch),.expected_layer(layer),.actual_valid(offret[0]),.actual_sector(offret[10:1]),.actual_epoch(offret[26:11]),.actual_layer(offret[32:27]),.actual_data(offret[288:33]),.fault_hbm(offret[289]),.fault_core(offfc),.idle_hbm(offret[290]),.idle_core(offret[291]));
 // Actual unified selected field301 is high9 slice bit5 at qkd_rlys_36.
 wire[304:0] o_grp={3'b0,newfc,301'b0};wire[35:0] relay;
 qkd_rlys_36 u_relay(.ck(ck),.a({27'b0,o_grp[304:296]}),.b(relay));
 wire gf;
 qkd_static_kv_drain_guard4 u_group(.ck(ck),.rst_n(rst),.ctrl_idle_core(4'hf),.ring_idle_core(4'hf),.ctrl_idle_hbm(4'hf),.front_idle_hbm(4'hf),.ring_idle_hbm(4'hf),.ctrl_fault_core(4'b0),.ctrl_completion_fault_core(4'b0),.ctrl_intake_fault_core(4'b0),.ring_fault_core({3'b0,relay[5]}),.ctrl_fault_hbm(4'b0),.ctrl_output_fault_hbm(4'b0),.ctrl_calendar_fault_hbm(4'b0),.ring_fault_hbm(4'b0),.front_fault_overflow_hbm(4'b0),.front_fault_go_hbm(4'b0),.front_hold_hbm(4'b0),.upstream_quiet(1'b1),.upstream_fault(1'b0),.drained(),.fault(gf));
 integer checks=0,cy=0,k,cases=0;reg monitor=0;
 task tick;begin @(posedge ck);#1;cy=cy+1;if(oldret[291:0]!==newret[291:0]||oldret[291:0]!==offret[291:0]||oldfc!==offfc)$fatal(1,"HEALTHY_IDENTITY cycle=%0d",cy);checks=checks+1;@(negedge ck);end endtask
 task reset_all;begin rst=0;di=0;land_er=0;wes=0;hes=0;boot_ready=1;issue=0;return_slot=0;er=0;co=0;put=0;slot=0;epoch=0;sect=0;layer=0;repeat(6)tick;rst=1;repeat(8)tick;if(chain_fault||merge_fault||newfc||gf)$fatal(1,"CLEAR_FAIL");cases=cases+1;end endtask
 task expect_chain_path;begin
  // Called immediately before E0: bad land_er capture; exact initial pipeline is zero.
  tick;if(chain_fault||newfc||gf)$fatal(1,"EARLY_E0");
  land_er=0;tick;if(chain_fault||newfc||gf)$fatal(1,"EARLY_E1");
  tick;if(!chain_fault||newfc||gf)$fatal(1,"CHAIN_E2");
  tick;if(!newfc||gf)$fatal(1,"EXPORT_E3");
  tick;if(!relay[5]||gf)$fatal(1,"RELAY_E4");
  tick;if(gf)$fatal(1,"EARLY_GROUP_E5");
  tick;if(!gf)$fatal(1,"GROUP_E6");
  repeat(8)tick;if(!chain_fault||!newfc||!gf||oldfc)$fatal(1,"STICKY_OR_DEFAULT_FAIL");
 end endtask
 initial begin
  repeat(1)tick;
  // Each predicate is driven through real public pins after a legal reset/release.
  for(k=0;k<3;k=k+1)begin reset_all;case(k)0:land_er[0]=1;1:land_er[259]=1;2:land_er[260]=1;endcase expect_chain_path;end
  // Real boot-counter overflow: eight boot words, no returned credit, no forced state.
  reset_all;di[779]=1;repeat(10)tick;di=0;repeat(8)tick;if(!chain_fault||!newfc||!gf||merge_fault||oldfc)$fatal(1,"BOOT_OVERFLOW_CAUSE");
  // Both lanes targeting this PC is a real source collision, independent of land_er.
  reset_all;di[1:0]=3;tick;di=0;repeat(9)tick;if(!chain_fault||!newfc||!gf)$fatal(1,"DUAL_WRITER_CAUSE");
  // ES merge phase/collision predicates, and child embedding's real fault causes.
  reset_all;boot_ready=0;repeat(3)tick;wes[0]=1;tick;wes=0;repeat(6)tick;if(!merge_fault||!newfc||!gf||chain_fault)$fatal(1,"ES_WRITER_BOOT_CAUSE");
  reset_all;hes[0]=1;repeat(2)tick;hes=0;repeat(6)tick;if(!merge_fault||!newfc||!gf||chain_fault)$fatal(1,"ES_RUN_SLICE_CAUSE");
  reset_all;issue=1;tick;issue=0;tick;issue=1;tick;issue=0;repeat(6)tick;if(!merge_fault||!newfc||!gf||chain_fault)$fatal(1,"EMBED_PENDING_CAUSE");
  reset_all;return_slot=1;tick;return_slot=0;repeat(6)tick;if(!merge_fault||!newfc||!gf||chain_fault)$fatal(1,"EMBED_MISSING_RETURN_CAUSE");
  reset_all;er[260]=1;tick;er=0;repeat(6)tick;if(!merge_fault||!newfc||!gf||chain_fault)$fatal(1,"EMBED_CHILD_FAULT_CAUSE");
  // Nonzero healthy return payload retains exact old word and age, through real ring storage.
  reset_all;epoch=16'h1234;sect=10'h155;layer=6'h2a;co=0;co[281:26]=256'h123456789abcdef00112233445566778899aabbccddeeff00123456789abcde0;co[17:12]=layer;co[11:9]=sect[9:7];co[7:1]=sect[6:0];co[0]=1;put=1;tick;co[0]=0;put=0;repeat(7)tick;slot=1;tick;slot=0;tick;if(!newret[0]||newret[288:33]!=256'h123456789abcdef00112233445566778899aabbccddeeff00123456789abcde0||newfc)$fatal(1,"NONZERO_RETURN_IDENTITY");repeat(8)tick;
  reset_all;repeat(24)tick;
  $display("PC_FAULT_EXPORT_PASS cases=%0d checks=%0d E0_E6=exact nonzero_return=1 default_identity=1",cases,checks);$finish;
 end
endmodule
