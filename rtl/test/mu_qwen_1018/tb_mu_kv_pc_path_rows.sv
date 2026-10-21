`timescale 1ns/1ps
// MU-ADOPT-KV 10-19 (R6 read side through the wired parent): two qkd_static_kv_pc_path_nc (MU 0 = today, MU 1 = the
// per-user KV row) get identical stimulus under the actual compiled die calendar image of one PC (+IMAGE, as
// tb_kvplan_ci_nc_lockstep): LAYERS rounds x 4 users on the SAME layer (stage-interleaved), epoch = {seq14, user2} (the MU epoch convention: user =
// epoch[1:0]); cal_epoch / cal_layer are driven with JUNK right after each go edge (the calendar latches them at go, so
// the stage user must come from the latched per-command epoch).  A PHY model (RL 23) answers the MU 0 path's reads; both
// get the same pi.  Checked every 0.1 ns:
//   * every output except po identical (er, ko, fo, completions, front, return ring, faults, idles, actual_*);
//   * po identical except the row field bits [9:8] (po[18:17]; the row field holds its last ACT value on other edges),
//     which must equal the stage user on every ACT of a KV row, with row[7:0] - 64 = the layer of that go;
//   * per user: >0 ACTs; the (bank, row) sets of the 4 users are pairwise disjoint; inverse row -> {user, layer} exact.
// PASS also needs real traffic (reads, landings, front puts, ring returns) and no fault on either path.
module tb_mu_kv_pc_path_rows;
 integer LAYERS=3, PCN=13;
 reg hck=0, ck=0;
 always #0.4167 hck=~hck;
 initial begin #0.137; forever #0.4167 ck=~ck; end
 reg hrst=0, rsi=0, cal_rst_n=0;
 reg [287:0] es=0; reg [288:0] pi=0; reg [32:0] ki=0; reg fi=0; reg [1:0] cfg_stack=2'd1;
 reg [317:0] es_context=0; reg es_expected_valid=0; reg [60:0] es_expected_identity=0; reg [28:0] es_expected_address=0;
 reg [4:0] es_expected_pc=0; reg [1:0] es_expected_stack=0;
 reg cal_cfg_we=0; reg [4:0] cal_cfg_addr=0; reg [63:0] cal_cfg_data=0; reg cal_seal=0, cal_go=0; reg [15:0] cal_epoch=0; reg [5:0] cal_layer=0;
 reg front_blk_go=0; reg expected_put=0; reg [9:0] expected_sector=0; reg [15:0] expected_epoch=0; reg [5:0] expected_layer=0;
 wire [4:0] pc=5'(PCN);
`define MKV_OUTS(p) \
 wire [260:0] p``er; wire [327:0] p``po; wire [32:0] p``ko; wire p``fo; wire p``ncv; wire [60:0] p``nci; wire [28:0] p``nca; \
 wire p``cv, p``cwe, p``cf, p``ic, p``ih, p``dfc, p``dfh, p``calf, p``cali, p``ff, p``fh, p``fi_, p``ffo, p``ffg; \
 wire [15:0] p``fse; wire [5:0] p``foc; wire p``av; wire [9:0] p``as; wire [15:0] p``ae; wire [5:0] p``al; wire [255:0] p``ad; \
 wire p``rfh, p``rfc, p``rih, p``ric;
`define MKV_CONN(p) \
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
`define MKV_REST(p) {p``er, p``ko, p``fo, p``ncv, p``nci, p``nca, p``cv, p``cwe, p``cf, p``ic, p``ih, p``dfc, p``dfh, p``calf, \
 p``cali, p``ff, p``fh, p``fse, p``foc, p``fi_, p``ffo, p``ffg, p``av, p``as, p``ae, p``al, p``ad, p``rfh, p``rfc, p``rih, p``ric}
 `MKV_OUTS(a_)
 `MKV_OUTS(b_)
 qkd_static_kv_pc_path_nc #(.MU(0)) u_a (`MKV_CONN(a_));   // today
 qkd_static_kv_pc_path_nc #(.MU(1)) u_b (`MKV_CONN(b_));   // per-user KV row
 wire [714:0] ra = `MKV_REST(a_), rb = `MKV_REST(b_);
 integer mism=0, pomism=0, checks=0;
 always #0.1 begin
  checks++;
  if (ra !== rb) begin mism++; if (mism <= 5) $display("MISMATCH rest t=%0t diff=%h", $realtime, ra ^ rb); end
 end
 // ---- the stage of each command: user / layer of the go that owns the calendar now (set at the go edge) ----
 integer cur_user=-1, cur_layer=-1, edge_num=0;
 integer acts[0:3]; integer act_bad=0, act_nonkv=0, row_hold=0;
 reg [23:0] seen_key [0:3][$];      // {bank5, row19}
 always @(posedge hck) begin
  edge_num++;
  if (a_po !== b_po) begin
   automatic logic [327:0] d = a_po ^ b_po;
   if (!(a_po[0] && a_po[3:1]==1)) row_hold++;   // the held row field of a non-ACT edge (not a command field)
   if ((d & ~(328'b11 << 17)) != 0) begin
    pomism++; if (pomism <= 5) $display("MISMATCH po t=%0t act=%0b diff=%h", $realtime, a_po[0] && a_po[3:1]==1, d);
   end
  end
  if (b_po[0] && b_po[3:1]==1) begin : act
   automatic integer bank=b_po[8:4]; automatic integer row=b_po[27:9]; automatic integer row0=a_po[27:9];
   if (row0 < 256) begin
    if (cur_user < 0 || (row >> 8) != cur_user || (row & 255) - 64 != cur_layer || row0 != 64 + cur_layer || (row & 255) != row0) begin
     act_bad++; if (act_bad <= 5) $display("BAD ACT t=%0t bank%0d row%0d (mu0 row%0d) user%0d layer%0d", $realtime, bank, row, row0, cur_user, cur_layer);
    end
    acts[cur_user]++; seen_key[cur_user].push_back({5'(bank), 19'(row)});
   end else begin
    act_nonkv++;
    if (row != row0) begin act_bad++; $display("BAD non-KV ACT changed row%0d -> %0d", row0, row); end
   end
  end
 end
 // ---- PHY model (answers the MU 0 path; both get the same pi) ----
 function automatic [71:0] ecc(input [63:0] d);
  reg [71:0] c; integer j; begin c=0; j=0; for (integer p=1;p<=71;p++) if ((p&(p-1))!=0) begin c[p-1]=d[j]; j++; end
  for (integer k=0;k<7;k++) for (integer p=1;p<=71;p++) if ((p&(1<<k))!=0) c[(1<<k)-1]^=c[p-1]; c[71]=^c[70:0]; ecc=c; end
 endfunction
 function automatic [287:0] encode(input [255:0] d); for (integer j=0;j<4;j++) encode[j*72+:72]=ecc(d[j*64+:64]); endfunction
 function automatic [255:0] payload(input integer sector, row);
  for (integer j=0;j<8;j++) payload[j*32+:32]=32'hac100000^32'(sector*311+j*31+row*65537);
 endfunction
 reg [288:0] due [0:400000]; integer last_arrival=0, reads=0, landed=0, fputs=0, rets=0; integer openrow[0:31];
 reg phy_on=0;
 always @(posedge hck) begin
  if (a_po[0] && a_po[3:1]==1) openrow[a_po[8:4]] = a_po[27:9];
  if (phy_on && a_po[28] && !a_po[29]) begin : rd
   automatic integer bank=a_po[34:30], col=a_po[39:35], sec=((bank>>2)<<7)|(col<<2)|(bank&3), arrival=edge_num+23;
   if (arrival<=last_arrival) arrival=last_arrival+1; last_arrival=arrival;
   due[arrival]={encode(payload(sec,openrow[bank])),1'b1}; reads++;
  end
  if (u_a.controller_co[0]) landed++;
 end
 always @(negedge hck) begin pi = due[edge_num+1]; due[edge_num+1] = 0; end
 integer gq [0:65535]; integer gw=0, gr=0, blk_seen=0;
 always @(negedge hck) begin
  front_blk_go <= 0;
  if (landed >= (blk_seen+1)*8) begin gq[gw[15:0]] = edge_num + 20; gw++; blk_seen++; end
  if (gr < gw && edge_num >= gq[gr[15:0]]) begin front_blk_go <= 1; gr++; end
 end
 reg [31:0] rq [0:65535]; real rt [0:65535]; integer rw=0, rr=0;
 always @(posedge hck) if (u_a.front_put) begin
  rq[rw[15:0]] = {u_a.front_epoch, u_a.front_co[17:12], u_a.front_co[11:9], u_a.front_co[7:1]}; rt[rw[15:0]] = $realtime + 4.0; rw++; fputs++;
 end
 always @(negedge ck) begin
  expected_put <= 0;
  if (rr < rw && $realtime >= rt[rr[15:0]]) begin
   expected_put <= 1; {expected_epoch, expected_layer, expected_sector} <= rq[rr[15:0]]; rr++;
  end
 end
 always @(posedge ck) if (a_av) rets++;
 reg [127:0] image [0:15]; string ip; integer seq=0, disjoint_bad=0;
 initial begin
  void'($value$plusargs("LAYERS=%d", LAYERS)); void'($value$plusargs("PC=%d", PCN));
  for (integer j=0;j<=400000;j++) due[j]=0; for (integer j=0;j<32;j++) openrow[j]=-1; for (integer u=0;u<4;u++) acts[u]=0;
  if (!$value$plusargs("IMAGE=%s", ip)) $fatal(1, "FAIL missing +IMAGE");
  $readmemh(ip, image);
  repeat(8) @(negedge hck); hrst=1; rsi=1; cal_rst_n=1;
  repeat(150) @(negedge hck);
  for (integer i=0;i<32;i++) begin cal_cfg_we=1; cal_cfg_addr=5'(i); cal_cfg_data = i<16 ? image[i][63:0] : image[i-16][127:64]; @(negedge hck); end
  cal_cfg_we=0; repeat(3) @(negedge hck); cal_seal=1; @(negedge hck); cal_seal=0; repeat(3) @(negedge hck);
  phy_on=1;
  // users interleaved layer by layer (op-level interleave of 4 users' stages on one PC calendar)
  for (integer l=0;l<LAYERS;l++) for (integer u=0;u<4;u++) begin
   cal_layer=6'(l*7+1); cal_epoch={14'(100+seq), 2'(u)}; seq++; cal_go=1;
   @(posedge hck); cur_user=u; cur_layer=l*7+1;      // the go edge: the calendar latches epoch / layer here
   @(negedge hck); cal_go=0; cal_epoch=16'($urandom); cal_layer=6'($urandom);   // junk: must not matter
   repeat(2500) @(negedge hck);
  end
  repeat(200) @(negedge hck);
  for (integer u=0;u<4;u++) for (integer v=u+1;v<4;v++) foreach (seen_key[u][i]) foreach (seen_key[v][j])
   if (seen_key[u][i] == seen_key[v][j]) disjoint_bad++;
  $display("STATS reads=%0d landed=%0d front_puts=%0d ring_returns=%0d acts=%0d/%0d/%0d/%0d nonkv_acts=%0d row_field_held_edges=%0d act_bad=%0d disjoint_bad=%0d rest_mism=%0d po_mism=%0d checks=%0d faults a:%0b%0b%0b%0b%0b b:%0b%0b%0b%0b%0b",
           reads, landed, fputs, rets, acts[0], acts[1], acts[2], acts[3], act_nonkv, row_hold, act_bad, disjoint_bad, mism, pomism, checks,
           a_fo, a_calf, a_ffo|a_ffg, a_rfh, a_rfc, b_fo, b_calf, b_ffo|b_ffg, b_rfh, b_rfc);
  if (!(reads>0 && landed>0 && fputs>0 && rets>0) || a_fo || a_calf || a_ffo || a_ffg || a_rfh || a_rfc ||
      b_fo || b_calf || b_ffo || b_ffg || b_rfh || b_rfc)
   $display("FAIL not representative / faulted");
  else if (act_bad || disjoint_bad || mism || pomism || acts[0]==0 || acts[1]==0 || acts[2]==0 || acts[3]==0)
   $display("FAIL MU_KV_READ_ROWS act_bad=%0d disjoint_bad=%0d rest_mism=%0d po_mism=%0d", act_bad, disjoint_bad, mism, pomism);
  else
   $display("PASS MU_KV_READ_ROWS users4 layers%0d pc%0d acts %0d/%0d/%0d/%0d row=64+l+256u exact, users disjoint, all other outputs lockstep with MU0",
            LAYERS, PCN, acts[0], acts[1], acts[2], acts[3]);
  $finish;
 end
endmodule
