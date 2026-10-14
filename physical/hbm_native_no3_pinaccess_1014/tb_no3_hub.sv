`timescale 1ns/1ps
module tb_no3_hub;
parameter integer MUT=0;
integer i,errors=0;
reg clk_sm;
reg por_n;
reg release_held;
reg in_v;
reg [2:0] out_r;
reg [2:0] ACK_v;
reg [575:0] ACK_owner;
reg [218:0] ACK_frame;
reg release_r;
reg sl4_v_bad;
reg sl4_v_cbad;
reg sl4_v_ce;
reg sl4_v_clean;
reg sl4_v_same;
reg sl4_v_ue;
reg [4:0] sl4_grc_o;
reg [319:0] sl4_q;
reg sl3_v_bad;
reg sl3_v_cbad;
reg sl3_v_ce;
reg sl3_v_clean;
reg sl3_v_same;
reg sl3_v_ue;
reg [7:0] sl3_grc_o;
reg sl2_v_bad;
reg sl2_v_cbad;
reg sl2_v_ce;
reg sl2_v_clean;
reg sl2_v_same;
reg sl2_v_ue;
reg [7:0] sl2_grc_o;
reg sl1_v_bad;
reg sl1_v_cbad;
reg sl1_v_ce;
reg sl1_v_clean;
reg sl1_v_same;
reg sl1_v_ue;
reg [7:0] sl1_grc_o;
reg sl0_v_bad;
reg sl0_v_cbad;
reg sl0_v_ce;
reg sl0_v_clean;
reg sl0_v_same;
reg sl0_v_ue;
reg [7:0] sl0_grc_o;
wire gold_in_r,actual_in_r;
wire [2:0] gold_out_v,actual_out_v;
wire gold_release_v,actual_release_v;
wire [191:0] gold_release_owner,actual_release_owner;
wire [72:0] gold_release_frame,actual_release_frame;
wire gold_fclk_o,actual_fclk_o;
wire gold_drained,actual_drained;
wire gold_paused,actual_paused;
wire gold_fault,actual_fault;
wire gold_sl4_go_check,actual_sl4_go_check;
wire gold_sl4_go_commit,actual_sl4_go_commit;
wire gold_sl4_go_repair,actual_sl4_go_repair;
wire gold_sl4_go_sel,actual_sl4_go_sel;
wire gold_sl4_gr,actual_sl4_gr;
wire gold_sl4_rst_e,actual_sl4_rst_e;
wire gold_sl4_rst_p,actual_sl4_rst_p;
wire [3:0] gold_sl4_ph4,actual_sl4_ph4;
wire gold_sl3_go_check,actual_sl3_go_check;
wire gold_sl3_go_commit,actual_sl3_go_commit;
wire gold_sl3_go_repair,actual_sl3_go_repair;
wire gold_sl3_go_sel,actual_sl3_go_sel;
wire gold_sl3_gr,actual_sl3_gr;
wire gold_sl3_rst_e,actual_sl3_rst_e;
wire gold_sl3_rst_p,actual_sl3_rst_p;
wire [3:0] gold_sl3_ph4,actual_sl3_ph4;
wire gold_sl2_go_check,actual_sl2_go_check;
wire gold_sl2_go_commit,actual_sl2_go_commit;
wire gold_sl2_go_repair,actual_sl2_go_repair;
wire gold_sl2_go_sel,actual_sl2_go_sel;
wire gold_sl2_gr,actual_sl2_gr;
wire gold_sl2_rst_e,actual_sl2_rst_e;
wire gold_sl2_rst_p,actual_sl2_rst_p;
wire [3:0] gold_sl2_ph4,actual_sl2_ph4;
wire gold_sl1_go_check,actual_sl1_go_check;
wire gold_sl1_go_commit,actual_sl1_go_commit;
wire gold_sl1_go_repair,actual_sl1_go_repair;
wire gold_sl1_go_sel,actual_sl1_go_sel;
wire gold_sl1_gr,actual_sl1_gr;
wire gold_sl1_rst_e,actual_sl1_rst_e;
wire gold_sl1_rst_p,actual_sl1_rst_p;
wire [3:0] gold_sl1_ph4,actual_sl1_ph4;
wire gold_sl0_go_check,actual_sl0_go_check;
wire gold_sl0_go_commit,actual_sl0_go_commit;
wire gold_sl0_go_repair,actual_sl0_go_repair;
wire gold_sl0_go_sel,actual_sl0_go_sel;
wire gold_sl0_gr,actual_sl0_gr;
wire gold_sl0_rst_e,actual_sl0_rst_e;
wire gold_sl0_rst_p,actual_sl0_rst_p;
wire [3:0] gold_sl0_ph4,actual_sl0_ph4;
ot_hbm_w2_stn_hub_no3 gold_dut(.clk_sm(clk_sm),.por_n(por_n),.release_held(release_held),.in_v(in_v),.out_r(out_r),.ACK_v(ACK_v),.ACK_owner(ACK_owner),.ACK_frame(ACK_frame),.release_r(release_r),.sl4_v_bad(sl4_v_bad),.sl4_v_cbad(sl4_v_cbad),.sl4_v_ce(sl4_v_ce),.sl4_v_clean(sl4_v_clean),.sl4_v_same(sl4_v_same),.sl4_v_ue(sl4_v_ue),.sl4_grc_o(sl4_grc_o),.sl4_q(sl4_q),.sl3_v_bad(sl3_v_bad),.sl3_v_cbad(sl3_v_cbad),.sl3_v_ce(sl3_v_ce),.sl3_v_clean(sl3_v_clean),.sl3_v_same(sl3_v_same),.sl3_v_ue(sl3_v_ue),.sl3_grc_o(sl3_grc_o),.sl2_v_bad(sl2_v_bad),.sl2_v_cbad(sl2_v_cbad),.sl2_v_ce(sl2_v_ce),.sl2_v_clean(sl2_v_clean),.sl2_v_same(sl2_v_same),.sl2_v_ue(sl2_v_ue),.sl2_grc_o(sl2_grc_o),.sl1_v_bad(sl1_v_bad),.sl1_v_cbad(sl1_v_cbad),.sl1_v_ce(sl1_v_ce),.sl1_v_clean(sl1_v_clean),.sl1_v_same(sl1_v_same),.sl1_v_ue(sl1_v_ue),.sl1_grc_o(sl1_grc_o),.sl0_v_bad(sl0_v_bad),.sl0_v_cbad(sl0_v_cbad),.sl0_v_ce(sl0_v_ce),.sl0_v_clean(sl0_v_clean),.sl0_v_same(sl0_v_same),.sl0_v_ue(sl0_v_ue),.sl0_grc_o(sl0_grc_o),.in_r(gold_in_r),.out_v(gold_out_v),.release_v(gold_release_v),.release_owner(gold_release_owner),.release_frame(gold_release_frame),.fclk_o(gold_fclk_o),.drained(gold_drained),.paused(gold_paused),.fault(gold_fault),.sl4_go_check(gold_sl4_go_check),.sl4_go_commit(gold_sl4_go_commit),.sl4_go_repair(gold_sl4_go_repair),.sl4_go_sel(gold_sl4_go_sel),.sl4_gr(gold_sl4_gr),.sl4_rst_e(gold_sl4_rst_e),.sl4_rst_p(gold_sl4_rst_p),.sl4_ph4(gold_sl4_ph4),.sl3_go_check(gold_sl3_go_check),.sl3_go_commit(gold_sl3_go_commit),.sl3_go_repair(gold_sl3_go_repair),.sl3_go_sel(gold_sl3_go_sel),.sl3_gr(gold_sl3_gr),.sl3_rst_e(gold_sl3_rst_e),.sl3_rst_p(gold_sl3_rst_p),.sl3_ph4(gold_sl3_ph4),.sl2_go_check(gold_sl2_go_check),.sl2_go_commit(gold_sl2_go_commit),.sl2_go_repair(gold_sl2_go_repair),.sl2_go_sel(gold_sl2_go_sel),.sl2_gr(gold_sl2_gr),.sl2_rst_e(gold_sl2_rst_e),.sl2_rst_p(gold_sl2_rst_p),.sl2_ph4(gold_sl2_ph4),.sl1_go_check(gold_sl1_go_check),.sl1_go_commit(gold_sl1_go_commit),.sl1_go_repair(gold_sl1_go_repair),.sl1_go_sel(gold_sl1_go_sel),.sl1_gr(gold_sl1_gr),.sl1_rst_e(gold_sl1_rst_e),.sl1_rst_p(gold_sl1_rst_p),.sl1_ph4(gold_sl1_ph4),.sl0_go_check(gold_sl0_go_check),.sl0_go_commit(gold_sl0_go_commit),.sl0_go_repair(gold_sl0_go_repair),.sl0_go_sel(gold_sl0_go_sel),.sl0_gr(gold_sl0_gr),.sl0_rst_e(gold_sl0_rst_e),.sl0_rst_p(gold_sl0_rst_p),.sl0_ph4(gold_sl0_ph4));
ot_hbm_native_no3_hub_m5_1014 actual_dut(.clk_sm(clk_sm),.por_n(por_n),.release_held(release_held),.in_v(in_v),.out_r(out_r),.ACK_v(ACK_v),.ACK_owner(ACK_owner),.ACK_frame(ACK_frame),.release_r(release_r),.sl4_v_bad(sl4_v_bad),.sl4_v_cbad(sl4_v_cbad),.sl4_v_ce(sl4_v_ce),.sl4_v_clean(sl4_v_clean),.sl4_v_same(sl4_v_same),.sl4_v_ue(sl4_v_ue),.sl4_grc_o(sl4_grc_o),.sl4_q(sl4_q),.sl3_v_bad(sl3_v_bad),.sl3_v_cbad(sl3_v_cbad),.sl3_v_ce(sl3_v_ce),.sl3_v_clean(sl3_v_clean),.sl3_v_same(sl3_v_same),.sl3_v_ue(sl3_v_ue),.sl3_grc_o(sl3_grc_o),.sl2_v_bad(sl2_v_bad),.sl2_v_cbad(sl2_v_cbad),.sl2_v_ce(sl2_v_ce),.sl2_v_clean(sl2_v_clean),.sl2_v_same(sl2_v_same),.sl2_v_ue(sl2_v_ue),.sl2_grc_o(sl2_grc_o),.sl1_v_bad(sl1_v_bad),.sl1_v_cbad(sl1_v_cbad),.sl1_v_ce(sl1_v_ce),.sl1_v_clean(sl1_v_clean),.sl1_v_same(sl1_v_same),.sl1_v_ue(sl1_v_ue),.sl1_grc_o(sl1_grc_o),.sl0_v_bad(sl0_v_bad),.sl0_v_cbad(sl0_v_cbad),.sl0_v_ce(sl0_v_ce),.sl0_v_clean(sl0_v_clean),.sl0_v_same(sl0_v_same),.sl0_v_ue(sl0_v_ue),.sl0_grc_o(sl0_grc_o),.in_r(actual_in_r),.out_v(actual_out_v),.release_v(actual_release_v),.release_owner(actual_release_owner),.release_frame(actual_release_frame),.fclk_o(actual_fclk_o),.drained(actual_drained),.paused(actual_paused),.fault(actual_fault),.sl4_go_check(actual_sl4_go_check),.sl4_go_commit(actual_sl4_go_commit),.sl4_go_repair(actual_sl4_go_repair),.sl4_go_sel(actual_sl4_go_sel),.sl4_gr(actual_sl4_gr),.sl4_rst_e(actual_sl4_rst_e),.sl4_rst_p(actual_sl4_rst_p),.sl4_ph4(actual_sl4_ph4),.sl3_go_check(actual_sl3_go_check),.sl3_go_commit(actual_sl3_go_commit),.sl3_go_repair(actual_sl3_go_repair),.sl3_go_sel(actual_sl3_go_sel),.sl3_gr(actual_sl3_gr),.sl3_rst_e(actual_sl3_rst_e),.sl3_rst_p(actual_sl3_rst_p),.sl3_ph4(actual_sl3_ph4),.sl2_go_check(actual_sl2_go_check),.sl2_go_commit(actual_sl2_go_commit),.sl2_go_repair(actual_sl2_go_repair),.sl2_go_sel(actual_sl2_go_sel),.sl2_gr(actual_sl2_gr),.sl2_rst_e(actual_sl2_rst_e),.sl2_rst_p(actual_sl2_rst_p),.sl2_ph4(actual_sl2_ph4),.sl1_go_check(actual_sl1_go_check),.sl1_go_commit(actual_sl1_go_commit),.sl1_go_repair(actual_sl1_go_repair),.sl1_go_sel(actual_sl1_go_sel),.sl1_gr(actual_sl1_gr),.sl1_rst_e(actual_sl1_rst_e),.sl1_rst_p(actual_sl1_rst_p),.sl1_ph4(actual_sl1_ph4),.sl0_go_check(actual_sl0_go_check),.sl0_go_commit(actual_sl0_go_commit),.sl0_go_repair(actual_sl0_go_repair),.sl0_go_sel(actual_sl0_go_sel),.sl0_gr(actual_sl0_gr),.sl0_rst_e(actual_sl0_rst_e),.sl0_rst_p(actual_sl0_rst_p),.sl0_ph4(actual_sl0_ph4));
initial begin
clk_sm=0; por_n=0;
release_held='0;
in_v='0;
out_r='0;
ACK_v='0;
ACK_owner='0;
ACK_frame='0;
release_r='0;
sl4_v_bad='0;
sl4_v_cbad='0;
sl4_v_ce='0;
sl4_v_clean='0;
sl4_v_same='0;
sl4_v_ue='0;
sl4_grc_o='0;
sl4_q='0;
sl3_v_bad='0;
sl3_v_cbad='0;
sl3_v_ce='0;
sl3_v_clean='0;
sl3_v_same='0;
sl3_v_ue='0;
sl3_grc_o='0;
sl2_v_bad='0;
sl2_v_cbad='0;
sl2_v_ce='0;
sl2_v_clean='0;
sl2_v_same='0;
sl2_v_ue='0;
sl2_grc_o='0;
sl1_v_bad='0;
sl1_v_cbad='0;
sl1_v_ce='0;
sl1_v_clean='0;
sl1_v_same='0;
sl1_v_ue='0;
sl1_grc_o='0;
sl0_v_bad='0;
sl0_v_cbad='0;
sl0_v_ce='0;
sl0_v_clean='0;
sl0_v_same='0;
sl0_v_ue='0;
sl0_grc_o='0;
repeat(4) begin #5 clk_sm=1; #5 clk_sm=0; end
por_n=1;
for(i=0;i<4096;i=i+1) begin
release_held = {$random};
in_v = {$random};
out_r = {$random};
ACK_v = {$random};
ACK_owner = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
ACK_frame = {$random,$random,$random,$random,$random,$random,$random};
release_r = {$random};
sl4_v_bad = {$random};
sl4_v_cbad = {$random};
sl4_v_ce = {$random};
sl4_v_clean = {$random};
sl4_v_same = {$random};
sl4_v_ue = {$random};
sl4_grc_o = {$random};
sl4_q = {$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
sl3_v_bad = {$random};
sl3_v_cbad = {$random};
sl3_v_ce = {$random};
sl3_v_clean = {$random};
sl3_v_same = {$random};
sl3_v_ue = {$random};
sl3_grc_o = {$random};
sl2_v_bad = {$random};
sl2_v_cbad = {$random};
sl2_v_ce = {$random};
sl2_v_clean = {$random};
sl2_v_same = {$random};
sl2_v_ue = {$random};
sl2_grc_o = {$random};
sl1_v_bad = {$random};
sl1_v_cbad = {$random};
sl1_v_ce = {$random};
sl1_v_clean = {$random};
sl1_v_same = {$random};
sl1_v_ue = {$random};
sl1_grc_o = {$random};
sl0_v_bad = {$random};
sl0_v_cbad = {$random};
sl0_v_ce = {$random};
sl0_v_clean = {$random};
sl0_v_same = {$random};
sl0_v_ue = {$random};
sl0_grc_o = {$random};
#5 clk_sm=1; #1;
if(gold_in_r !== actual_in_r) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH in_r cycle=%0d",i);end
if(gold_out_v !== actual_out_v) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH out_v cycle=%0d",i);end
if(gold_release_v !== actual_release_v) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH release_v cycle=%0d",i);end
if(gold_release_owner !== (actual_release_owner ^ MUT)) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH release_owner cycle=%0d",i);end
if(gold_release_frame !== actual_release_frame) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH release_frame cycle=%0d",i);end
if(gold_fclk_o !== actual_fclk_o) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH fclk_o cycle=%0d",i);end
if(gold_drained !== actual_drained) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH drained cycle=%0d",i);end
if(gold_paused !== actual_paused) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH paused cycle=%0d",i);end
if(gold_fault !== actual_fault) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH fault cycle=%0d",i);end
if(gold_sl4_go_check !== actual_sl4_go_check) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_go_check cycle=%0d",i);end
if(gold_sl4_go_commit !== actual_sl4_go_commit) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_go_commit cycle=%0d",i);end
if(gold_sl4_go_repair !== actual_sl4_go_repair) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_go_repair cycle=%0d",i);end
if(gold_sl4_go_sel !== actual_sl4_go_sel) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_go_sel cycle=%0d",i);end
if(gold_sl4_gr !== actual_sl4_gr) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_gr cycle=%0d",i);end
if(gold_sl4_rst_e !== actual_sl4_rst_e) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_rst_e cycle=%0d",i);end
if(gold_sl4_rst_p !== actual_sl4_rst_p) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_rst_p cycle=%0d",i);end
if(gold_sl4_ph4 !== actual_sl4_ph4) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl4_ph4 cycle=%0d",i);end
if(gold_sl3_go_check !== actual_sl3_go_check) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_go_check cycle=%0d",i);end
if(gold_sl3_go_commit !== actual_sl3_go_commit) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_go_commit cycle=%0d",i);end
if(gold_sl3_go_repair !== actual_sl3_go_repair) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_go_repair cycle=%0d",i);end
if(gold_sl3_go_sel !== actual_sl3_go_sel) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_go_sel cycle=%0d",i);end
if(gold_sl3_gr !== actual_sl3_gr) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_gr cycle=%0d",i);end
if(gold_sl3_rst_e !== actual_sl3_rst_e) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_rst_e cycle=%0d",i);end
if(gold_sl3_rst_p !== actual_sl3_rst_p) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_rst_p cycle=%0d",i);end
if(gold_sl3_ph4 !== actual_sl3_ph4) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl3_ph4 cycle=%0d",i);end
if(gold_sl2_go_check !== actual_sl2_go_check) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_go_check cycle=%0d",i);end
if(gold_sl2_go_commit !== actual_sl2_go_commit) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_go_commit cycle=%0d",i);end
if(gold_sl2_go_repair !== actual_sl2_go_repair) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_go_repair cycle=%0d",i);end
if(gold_sl2_go_sel !== actual_sl2_go_sel) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_go_sel cycle=%0d",i);end
if(gold_sl2_gr !== actual_sl2_gr) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_gr cycle=%0d",i);end
if(gold_sl2_rst_e !== actual_sl2_rst_e) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_rst_e cycle=%0d",i);end
if(gold_sl2_rst_p !== actual_sl2_rst_p) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_rst_p cycle=%0d",i);end
if(gold_sl2_ph4 !== actual_sl2_ph4) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl2_ph4 cycle=%0d",i);end
if(gold_sl1_go_check !== actual_sl1_go_check) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_go_check cycle=%0d",i);end
if(gold_sl1_go_commit !== actual_sl1_go_commit) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_go_commit cycle=%0d",i);end
if(gold_sl1_go_repair !== actual_sl1_go_repair) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_go_repair cycle=%0d",i);end
if(gold_sl1_go_sel !== actual_sl1_go_sel) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_go_sel cycle=%0d",i);end
if(gold_sl1_gr !== actual_sl1_gr) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_gr cycle=%0d",i);end
if(gold_sl1_rst_e !== actual_sl1_rst_e) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_rst_e cycle=%0d",i);end
if(gold_sl1_rst_p !== actual_sl1_rst_p) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_rst_p cycle=%0d",i);end
if(gold_sl1_ph4 !== actual_sl1_ph4) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl1_ph4 cycle=%0d",i);end
if(gold_sl0_go_check !== actual_sl0_go_check) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_go_check cycle=%0d",i);end
if(gold_sl0_go_commit !== actual_sl0_go_commit) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_go_commit cycle=%0d",i);end
if(gold_sl0_go_repair !== actual_sl0_go_repair) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_go_repair cycle=%0d",i);end
if(gold_sl0_go_sel !== actual_sl0_go_sel) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_go_sel cycle=%0d",i);end
if(gold_sl0_gr !== actual_sl0_gr) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_gr cycle=%0d",i);end
if(gold_sl0_rst_e !== actual_sl0_rst_e) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_rst_e cycle=%0d",i);end
if(gold_sl0_rst_p !== actual_sl0_rst_p) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_rst_p cycle=%0d",i);end
if(gold_sl0_ph4 !== actual_sl0_ph4) begin errors=errors+1; if(errors<5)$display("NO3_HUB_MISMATCH sl0_ph4 cycle=%0d",i);end
#4 clk_sm=0;
end
if(errors==0)begin $display("NO3_HUB_EXACT PASS cycles=4096 outputs=49");$finish;end
$display("NO3_HUB_EXACT FAIL errors=%0d",errors);$fatal(1,"actual hub mutant mismatch");
end
endmodule
