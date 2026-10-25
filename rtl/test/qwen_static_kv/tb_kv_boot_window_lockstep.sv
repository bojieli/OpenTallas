`timescale 1ns/1ps
// KV-TOK B 2026-10-24: lockstep miter of the per-PC static controller path WITH the controller boot window
// (qkd_static_kv_pc_path_nc and children as now in the repo) against the ORIGINAL path without it (the same sources at
// the pre-change commit, every module renamed *_ref by tools/qwen_kv_die/kv_boot_window_gate.sh).  Stimulus and checks
// are those of tb_kvplan_ci_nc_lockstep (EVERY output of both compared every 0.1 ns):
//   phase P (+PRE): random pre-ownership traffic from reset; +PRE_ES=0 keeps es[0] (static words) low in it, +PRE_ES=1
//            sends random static words (the window is open there, so ONLY in that phase the variant may differ: it
//            issues them; reported as mism_pre, informational unless +PRE_STRICT);
//   phase A: the actual compiled die calendar image of one PC, FRAMES layer go's, PHY model, front, return ring;
//   phase B: random stress on every input while the calendar owns the PC (window closed).
// PASS: zero mismatches after the boot reset (phases A, B) and, with +PRE_STRICT, also in phase P; no boot column after
// the boot reset (the window must stay closed once the calendar owns the PC).  +CMP_POST=0 (window-activity run with
// +PRE_ES=1 only): the variant's phase-P static writes leave different write data in non-reset port registers (po wd),
// so the post-reset compare is not meaningful there; that run only reports the phase-P window activity.
module tb_kv_boot_window_lockstep;
 integer FRAMES=4, JIT=0, PRE=0, STRESS=6000, PCN=13, PRE_ES=1, PRE_STRICT=0, CMP_POST=1;
 reg hck=0, ck=0;
 always #0.4167 hck=~hck;
 initial begin #0.137; forever #0.4167 ck=~ck; end   // same frequency, independent phase
 reg hrst=0, rsi=0, cal_rst_n=0;
 reg [287:0] es=0; reg [288:0] pi=0; reg [32:0] ki=0; reg fi=0; reg [1:0] cfg_stack=2'd1;
 reg [317:0] es_context=0; reg es_expected_valid=0; reg [60:0] es_expected_identity=0; reg [28:0] es_expected_address=0;
 reg [4:0] es_expected_pc=0; reg [1:0] es_expected_stack=0;
 reg cal_cfg_we=0; reg [4:0] cal_cfg_addr=0; reg [63:0] cal_cfg_data=0; reg cal_seal=0, cal_go=0; reg [15:0] cal_epoch=100; reg [5:0] cal_layer=0;
 reg front_blk_go=0; reg expected_put=0; reg [9:0] expected_sector=0; reg [15:0] expected_epoch=0; reg [5:0] expected_layer=0;
 wire [4:0] pc=5'(PCN);
`define KVCI_OUTS(p) \
 wire [260:0] p``er; wire [327:0] p``po; wire [32:0] p``ko; wire p``fo; wire p``ncv; wire [60:0] p``nci; wire [28:0] p``nca; \
 wire p``cv, p``cwe, p``cf, p``ic, p``ih, p``dfc, p``dfh, p``calf, p``cali, p``ff, p``fh, p``fi_, p``ffo, p``ffg; \
 wire [15:0] p``fse; wire [5:0] p``foc; wire p``av; wire [9:0] p``as; wire [15:0] p``ae; wire [5:0] p``al; wire [255:0] p``ad; \
 wire p``rfh, p``rfc, p``rih, p``ric;
`define KVCI_CONN(p) \
 .pll_hbm(hck), .pll_hbm_port(hck), .pll_hbm_ecc(hck), .pll_hbm_cdc(hck), .pll_hbm_obs(hck), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(pc), \
 .es(es), .er(p``er), .po(p``po), .pi(pi), .ki(ki), .ko(p``ko), .fi(fi), .fo(p``fo), .cfg_stack(cfg_stack), .es_context(es_context), \
 .es_expected_valid(es_expected_valid), .es_expected_identity(es_expected_identity), .es_expected_address(es_expected_address), \
 .es_expected_pc(es_expected_pc), .es_expected_stack(es_expected_stack), .native_commit_valid(p``ncv), .native_commit_identity(p``nci), \
 .native_commit_address(p``nca), .completion_v(p``cv), .completion_we(p``cwe), .completion_fault(p``cf), .idle_core(p``ic), .idle_hbm(p``ih), \
 .drain_fault_core(p``dfc), .drain_fault_hbm(p``dfh), .cal_hck(hck), .cal_rst_n(cal_rst_n), .cal_cfg_we(cal_cfg_we), .cal_cfg_addr(cal_cfg_addr), \
 .cal_cfg_data(cal_cfg_data), .cal_seal(cal_seal), .cal_go(cal_go), .cal_epoch(cal_epoch), .cal_layer(cal_layer), .cal_fault_hbm(p``calf), \
 .cal_idle_hbm(p``cali), .front_hck(hck), .front_hbm_data({4{hck}}), .front_blk_go(front_blk_go), .front_blk_freed(p``ff), .front_hold(p``fh), \
 .front_stall_edges(p``fse), .front_occupancy(p``foc), .front_idle_hbm(p``fi_), .front_fault_overflow_hbm(p``ffo), .front_fault_go_hbm(p``ffg), \
 .return_hck(hck), .return_ck(ck), .return_hbm_data({4{hck}}), .expected_put(expected_put), .expected_sector(expected_sector), \
 .expected_epoch(expected_epoch), .expected_layer(expected_layer), .actual_valid(p``av), .actual_sector(p``as), .actual_epoch(p``ae), \
 .actual_layer(p``al), .actual_data(p``ad), .return_fault_hbm(p``rfh), .return_fault_core(p``rfc), .return_idle_hbm(p``rih), .return_idle_core(p``ric)
`define KVCI_VEC(p) {p``er, p``po, p``ko, p``fo, p``ncv, p``nci, p``nca, p``cv, p``cwe, p``cf, p``ic, p``ih, p``dfc, p``dfh, p``calf, \
 p``cali, p``ff, p``fh, p``fse, p``foc, p``fi_, p``ffo, p``ffg, p``av, p``as, p``ae, p``al, p``ad, p``rfh, p``rfc, p``rih, p``ric}
 `KVCI_OUTS(a_)
 `KVCI_OUTS(b_)
 qkd_static_kv_pc_path_nc_ref u_a (`KVCI_CONN(a_));   // original controller path (no boot window)
 qkd_static_kv_pc_path_nc     u_b (`KVCI_CONN(b_));   // with the controller boot window
 wire [1042:0] va = `KVCI_VEC(a_), vb = `KVCI_VEC(b_);
 integer mism=0, checks=0, mism_pre=0, in_pre=0;
 always #0.1 begin
  checks++;
  if (va !== vb) begin
   if (in_pre) mism_pre++; else mism++;
   if (!in_pre && mism <= 5) $display("MISMATCH t=%0t diff=%h", $realtime, va ^ vb);
  end
 end
 // boot-window activity of the variant: static columns issued without a reservation (col_boot), and window state
 integer boot_cols_pre=0, boot_cols_post=0;
 always @(posedge hck) if (u_b.u_ctrl.u_sched.col_boot) begin if (in_pre) boot_cols_pre++; else boot_cols_post++; end
 integer legacy_nz=0;
 // ---- SECDED-coded PHY payload ----
 function automatic [71:0] ecc(input [63:0] d);
  reg [71:0] c; integer j; begin c=0; j=0; for (integer p=1;p<=71;p++) if ((p&(p-1))!=0) begin c[p-1]=d[j]; j++; end
  for (integer k=0;k<7;k++) for (integer p=1;p<=71;p++) if ((p&(1<<k))!=0) c[(1<<k)-1]^=c[p-1]; c[71]=^c[70:0]; ecc=c; end
 endfunction
 function automatic [287:0] encode(input [255:0] d); for (integer j=0;j<4;j++) encode[j*72+:72]=ecc(d[j*64+:64]); endfunction
 function automatic [255:0] payload(input integer sector, row);
  for (integer j=0;j<8;j++) payload[j*32+:32]=32'hac100000^32'(sector*311+j*31+row*65537);
 endfunction
 reg [288:0] due [0:400000]; integer edge_num=0, last_arrival=0, reads=0, landed=0, fputs=0, rets=0; integer openrow[0:31];
 reg phy_on=0, stress=0;
 always @(posedge hck) begin
  edge_num++;
  if (a_po[0] && a_po[3:1]==1) openrow[a_po[8:4]] = a_po[27:9];
  if (phy_on && a_po[28] && !a_po[29]) begin : rd
   automatic integer bank=a_po[34:30], col=a_po[39:35], sec=((bank>>2)<<7)|(col<<2)|(bank&3), arrival=edge_num+23+JIT;
   if (arrival<=last_arrival) arrival=last_arrival+1; last_arrival=arrival;
   due[arrival]={encode(payload(sec,openrow[bank])),1'b1}; reads++;
  end
  if (u_a.controller_co[0]) landed++;
 end
 always @(negedge hck) if (!stress) begin pi = due[edge_num+1]; due[edge_num+1] = 0; end
 // elastic front: release each block a fixed margin after its 8th sector landed
 integer gq [0:65535]; integer gw=0, gr=0, blk_seen=0;
 always @(negedge hck) if (!stress) begin
  front_blk_go <= 0;
  if (landed >= (blk_seen+1)*8) begin gq[gw[15:0]] = edge_num + 20; gw++; blk_seen++; end
  if (gr < gw && edge_num >= gq[gr[15:0]]) begin front_blk_go <= 1; gr++; end
 end
 // return ring: the core slot of each front put, one fixed delay later
 reg [31:0] rq [0:65535]; real rt [0:65535]; integer rw=0, rr=0;
 always @(posedge hck) if (u_a.front_put) begin
  rq[rw[15:0]] = {u_a.front_epoch, u_a.front_co[17:12], u_a.front_co[11:9], u_a.front_co[7:1]}; rt[rw[15:0]] = $realtime + 4.0; rw++; fputs++;
 end
 always @(negedge ck) if (!stress) begin
  expected_put <= 0;
  if (rr < rw && $realtime >= rt[rr[15:0]]) begin
   expected_put <= 1; {expected_epoch, expected_layer, expected_sector} <= rq[rr[15:0]]; rr++;
  end
 end
 always @(posedge ck) if (a_av) rets++;
 // ---- random stress driver ----
 task automatic rnd_cycle(input integer own);
  ki = ($urandom%23==0) ? {$urandom, 1'b1} : {$urandom, 1'b0};
  if (ki[0] && ($urandom%2)) ki[32:31] = 2'd0;
  es = {$urandom, {8{$urandom}}};
  es[0] = ($urandom%17==0) && (own || PRE_ES!=0);
  pi = {{9{$urandom}}, ($urandom%11==0)};
  fi = ($urandom%997==0) ? 1'b1 : fi;
  front_blk_go = ($urandom%41==0);
  expected_put = ($urandom%29==0); expected_sector = 10'($urandom); expected_epoch = 16'($urandom); expected_layer = 6'($urandom);
  es_expected_valid = ($urandom%61==0); es_context[317] = es[0] && ($urandom%3==0);
  if (!own) begin cal_cfg_we = ($urandom%53==0); cal_cfg_addr = 5'($urandom); cal_cfg_data = {$urandom,$urandom}; end
 endtask
 reg [127:0] image [0:15]; string ip;
 initial begin
  void'($value$plusargs("FRAMES=%d", FRAMES)); void'($value$plusargs("JIT=%d", JIT)); void'($value$plusargs("PRE=%d", PRE));
  void'($value$plusargs("STRESS=%d", STRESS)); void'($value$plusargs("PC=%d", PCN));
  void'($value$plusargs("PRE_ES=%d", PRE_ES)); void'($value$plusargs("PRE_STRICT=%d", PRE_STRICT));
  void'($value$plusargs("CMP_POST=%d", CMP_POST));
  for (integer j=0;j<=400000;j++) due[j]=0; for (integer j=0;j<32;j++) openrow[j]=-1;
  if (!$value$plusargs("IMAGE=%s", ip)) $fatal(1, "FAIL missing +IMAGE");
  $readmemh(ip, image);
  repeat(8) @(negedge hck); hrst=1; rsi=1; cal_rst_n=1;
  if (PRE) begin   // random pre-ownership traffic, then a reset of both domains (the boot reset) before the programme
   stress=1; in_pre=1; repeat(PRE) begin @(negedge hck); rnd_cycle(0); end
   ki=0; es=0; pi=0; front_blk_go=0; expected_put=0; cal_cfg_we=0; es_expected_valid=0; es_context=0; fi=0;
   repeat(50) @(negedge hck); hrst=0; rsi=0; cal_rst_n=0; repeat(8) @(negedge hck); in_pre=0; hrst=1; rsi=1; cal_rst_n=1;
   for (integer j=0;j<=400000;j++) due[j]=0; stress=0; reads=0; landed=0; fputs=0; rets=0; rw=0; rr=0; gw=0; gr=0; blk_seen=0;
   legacy_nz=0; repeat(50) @(negedge hck);
  end
  repeat(150) @(negedge hck);
  for (integer i=0;i<32;i++) begin cal_cfg_we=1; cal_cfg_addr=5'(i); cal_cfg_data = i<16 ? image[i][63:0] : image[i-16][127:64]; @(negedge hck); end
  cal_cfg_we=0; repeat(3) @(negedge hck); cal_seal=1; @(negedge hck); cal_seal=0; repeat(3) @(negedge hck);
  phy_on=1;
  for (integer l=0;l<FRAMES;l++) begin
   cal_layer=6'(l); cal_epoch=16'(100+l); cal_go=1; @(negedge hck); cal_go=0; repeat(2500) @(negedge hck);
  end
  repeat(200) @(negedge hck);
  $display("PHASE_A reads=%0d landed=%0d front_puts=%0d ring_returns=%0d fo=%0b cal_fault=%0b front_fault=%0b%0b return_fault=%0b%0b boot_win=%0b",
           reads, landed, fputs, rets, a_fo, a_calf, a_ffo, a_ffg, a_rfh, a_rfc, u_b.u_ctrl.u_sched.boot_win);
  if (!(reads>0 && landed>0 && fputs>0 && rets>0) || a_fo || a_calf || a_ffo || a_ffg || a_rfh || a_rfc) begin
   $display("FAIL phase A not representative / faulted (mismatches=%0d)", mism); $finish; end
  stress=1; phy_on=0; pi=0; front_blk_go=0; expected_put=0;
  // B1: kc chain commands while the calendar owns the controller (must fault f_cmd, identically), nothing else
  repeat(500) begin @(negedge hck); ki = ($urandom%23==0) ? {2'd0, 30'($urandom), 1'b1} : 33'd0; end
  ki=0; repeat(100) @(negedge hck);
  $display("PHASE_B1 fo=%0b", a_fo);
  // B2: random stress on every input
  repeat(STRESS) begin @(negedge hck); rnd_cycle(1); end
  repeat(300) @(negedge hck);
  $display("PHASE_P pre=%0d pre_es=%0d mism_pre=%0d boot_cols_pre=%0d boot_cols_post=%0d", PRE, PRE_ES, mism_pre, boot_cols_pre, boot_cols_post);
  if (CMP_POST == 0) $display("INFO WINDOW_ACTIVITY_ONLY (post-reset compare off: non-reset write-data registers keep the differing phase-P history) mism_post=%0d", mism);
  else if (mism != 0 || (PRE_STRICT != 0 && mism_pre != 0) || boot_cols_post != 0)
   $display("FAIL LOCKSTEP mismatches=%0d mism_pre=%0d boot_cols_post=%0d checks=%0d", mism, mism_pre, boot_cols_post, checks);
  else $display("PASS KV_BOOT_WINDOW_LOCKSTEP checks=%0d frames=%0d jit=%0d pre=%0d pre_es=%0d stress=%0d mism_pre=%0d boot_cols_pre=%0d final_fo=%0b",
                checks, FRAMES, JIT, PRE, PRE_ES, STRESS, mism_pre, boot_cols_pre, a_fo);
  $finish;
 end
endmodule
