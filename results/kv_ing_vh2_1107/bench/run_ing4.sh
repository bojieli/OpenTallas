#!/bin/bash
# KV-ING-8 11-07 vH2 lock-step bench vs the source engine.  usage (repo root as cwd): run_ing4.sh OUT CASE [plusargs]; CASE: form | a mutant name (must FAIL)
set -u
OUT=$(mkdir -p "$1" && cd "$1" && pwd); CASE=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=results/kv_ing_vh2_1107
W=$OUT/src_$CASE; mkdir -p $W
if [ ! -x $OUT/o_$CASE/Vtb ] || [ -z "${REUSE:-}" ]; then
rm -rf $W; mkdir -p $W
cp $D/rtl/*.sv $D/bench/tb_ing4.sv $W/
E=$W/qkd_host_native_engine_ing4.sv; Q=$W/ot_hdc_ingest_fp8q_s.sv; T=$W/qkd_hr_ingest_eng.sv
sub(){ python3 -I - "$1" "$2" "$3" <<'PY' || { echo "SUBST FAIL: $2"; exit 2; }
import sys
p,a,b=sys.argv[1:4]; s=open(p).read(); assert s.count(a)>=1,(p,a); open(p,'w').write(s.replace(a,b))
PY
}
case $CASE in
 form) ;;
 m_lane) sub $E "i0_b <= 4'd9 * qi_t[3:0] + {qi_g, qi_dg};" "i0_b <= 4'd9 * (qi_t[3:0] ^ {3'd0, !qi_v}) + {qi_g, qi_dg};";;
 m_bank) sub $E "rb0 = 4'd9 * t0 + {qo_g, qo_s[1:0], 1'b0}" "rb0 = 4'd9 * t0 + {qo_g, qo_s[1:0], 1'b0} + 4'd1";;
 m_slot) sub $E "wire [255:0] sd_n = qo_slot ? sd0 : sd1;" "wire [255:0] sd_n = qo_slot ? sd1 : sd0;";;
 m_round) sub $Q "up = m[19] && ((|m[18:0]) || m[20]);" "up = m[19] && (|m[18:0]);";;
 m_shstale) sub $E "always @(posedge clk) sh_r <= ra_sh[255:0];" "always @(posedge clk) if (st_go || !st_ok_r && !ap_go) sh_r <= ra_sh[255:0];";;
 m_nowait) sub $E "st_ok_r <= ok0 && st_run && !is_raw && ap_go && !st_go && need_ok;" "st_ok_r <= ok0 && st_run && !is_raw && ap_go && need_ok;";;
 m_ok0) sub $E "st_ok_r <= ok0 && st_run" "st_ok_r <= st_run";;
 m_oh) sub $E "else if (qk_s[gs] && er_s[gs]) oh <= {oh[6:0], oh[7]};" "else if (qk_s[gs] && er_s[gs]) oh <= (gs == 7) ? {oh[3:0], oh[7:4]} : {oh[6:0], oh[7]};";;
 m_qkc) sub $E "qk_s <= {35{fq_ne_n}};" "qk_s <= {35{qk_wv}};";;
 m_rawclr) sub $E "ra_wp <= 3'd0; rawq_v <= 1'b0;" "ra_wp <= 3'd0;";;
 m_rawq) sub $E "rawq_v <= raw_load || (rawq_v && !st_go);" "rawq_v <= raw_load;";;
 m_w1) sub $E "w1 <= ra_w1_n;" "w1 <= ra_rp_n[7:5];";;
 m_off) sub $E "always @(posedge clk) off <= ra_rp[4:0];" "always @(posedge clk) off <= (gy == 3) ? ra_rp[4:0] ^ 5'd1 : ra_rp[4:0];";;
 m_ibq) sub $E "wire [511:0] w_code = ib_all[QB*512 +: 512];" "wire [511:0] w_code = (gb == 13) ? i1_code : ib_all[QB*512 +: 512];";;
 m_ibsel) sub $E "ib_sel1 <= ih_sel1;" "ib_sel1 <= ih_sel0;";;
 m_ihq) sub $E "ib_all <= {ih_all[1023:512], ih_all[1023:512], ih_all[511:0], ih_all[511:0]};" "ib_all <= {ih_all[1023:512], i1_code, ih_all[511:0], ih_all[511:0]};";;
 m_ihlast) sub $E "ih_last <= i1_last;" "ih_last <= i1_last || i1_v;";;
 m_pushq) sub $E "(ra_room && beats_nz && !push_q)" "(ra_room && beats_nz)"; sub $E "ra_room && beats_nz && !push_q;" "ra_room && beats_nz;";;
 m_apskip) sub $E "ap_ok1m <= !ap_inval && st_act && ap_ok1;" "ap_ok1m <= !ap_inval && st_act;";;
 m_last) sub $E "qo_s[1:0] == 2'd3 && t5 == od_thim1" "qo_s[1:0] == 2'd2 && t5 == od_thim1";;
 m_cred) sub $E "wire         q_iss = qo_act && !cred[3];" "wire         q_iss = qo_act && !(cred[3] && cred[0]);";;
 m_kvswap) sub $E "kr <= q_iss && !qo_v; vr <= q_iss && qo_v;" "kr <= q_iss && qo_v; vr <= q_iss && !qo_v;";;
 m_addr) sub $E "{8'd0, fa[22:14], 1'b0, fa[13:0]}" "{8'd0, fa[22:15], 1'b0, fa[14:0]}";;
 m_kvbit) sub $E "od_lay <= sd_n[217] ? sd_n[37:32] : sd_n[36:31];" "od_lay <= sd_n[36:31];";;
 m_take) sub $E "(is_rows ? k_take : ik_low ? 6'd32 : st_ph == 3'd2 ? 6'd4 : 6'd0)" "k_take";;
 m_use) sub $E "q1_use <= {!(i0_fp32 || i0_bf16), !(i0_fp32 || i0_bf16), !i0_fp32};" "q1_use <= {!(i0_fp32 || i0_bf16), !i0_fp32, !i0_fp32};";;
 m_gw) sub $E "wire         g_end = !qf_k2 || qi_g;" "wire         g_end = qi_g;";;
 m_scale) sub $E "(sl_p0[mb] ? sc0[mb*8 +: 8] : sc1[mb*8 +: 8])" "(sl_p0[mb] ? sc1[mb*8 +: 8] : sc0[mb*8 +: 8])";;
 m_bvsel) sub $E "bank_v <= s2_isv ?" "bank_v <= !s2_isv ?";;
 m_kchi) sub $E "wire [28:0]  kc_hi1 = ap_kcode[31:3] + 29'd1;" "wire [28:0]  kc_hi1 = ap_kcode[31:3] + 29'd2;";;
 m_kcsel) sub $E "{kc_lo[3] ? kc_hi1 : ap_kcode[31:3], kc_lo[2:0]}" "{kc_lo[2] ? kc_hi1 : ap_kcode[31:3], kc_lo[2:0]}";;
 # input faces
 m_firdy) sub $E "{2'd0, fi_rdy} <= 3'd2;" "{2'd0, fi_rdy} <= 3'd3;";;
 m_fdrdy) sub $E "{3'd0, dq_rdy} <= 4'd3;" "{3'd0, dq_rdy} <= 4'd4;";;
 m_fiwp) sub $E "if (fi_push) fi_wp <= {fi_wp[1:0], fi_wp[2]};" "if (fi_push) fi_wp <= {fi_wp[1:0], 1'b0} | {2'd0, fi_wp[1]};";;
 m_firp) sub $E "if (fi_pop) fi_rp <= {fi_rp[1:0], fi_rp[2]};" "if (fi_pop) fi_rp <= {fi_rp[0], fi_rp[2:1]};";;
 m_dqwr) sub $E "if (p_d_v) dq_wr <= dq_wr + 2'd1;" "if (p_d_v && !dq_rdy) dq_wr <= dq_wr + 2'd1;";;
 m_invq) sub $T "fc_in_v <= in_acc;" "fc_in_v <= in_v;";;
 m_dvq) sub $T "fc_d_v <= d_acc;" "fc_d_v <= d_v;";;
 m_busyf) sub $T " || fc_in_v || fc_d_v" "";;
 m_busyn) sub $T " || o_v || s_nz" "";;
 # write face
 m_ernp) sub $T " + {2'd0, push}) <= 3'd2" ") <= 3'd2";;
 m_erlim) sub $T "{2'd0, push}) <= 3'd2" "{2'd0, push}) <= 3'd3";;
 m_skeep) sub $T "push && !(ld_o && !s_nz)" "push && !ld_o";;
 m_stake) sub $T "if (s_take) s_rp <= !s_rp;" "if (s_keep) s_rp <= !s_rp;";;
 m_on) sub $T "s_nz ? s_h : e_all" "e_all";;
 m_ldo) sub $T "!o_v || w_rdy" "!o_v || w_rdy || s_n == 2'd2";;
 m_ldo2) sub $T "!o_v || w_rdy" "w_rdy";;
 m_erst) sub $E "er_st <= er_n;" "er_st <= er_m;";;
 m_ers) sub $E "er_s <= {35{er_n}};" "er_s <= {35{er_m}};";;
 # done
 m_idle) sub $T "!o_v && !s_nz" "!s_nz";;
 m_sdblk) sub $E "s_disp = dh_v && !sd_pend &&" "s_disp = dh_v &&";;
 m_qdblk) sub $E "q_disp = dh_v && !sd_pend &&" "q_disp = dh_v &&";;
 m_odn) sub $T "(fire && o_dn[8]) || sd_fire" "sd_fire";;
 m_tg) sub $T "(fire && o_dn[8]) ? o_dn[7:0] : sd_tag" "sd_tag";;
 m_dnfast) sub $T "dn_b <= dn_a; dn_q <= dn_b;" "dn_b <= dn_a; dn_q <= dn_a;";;
 m_dnslow) sub $T "wf_a <= fire; wf_b <= wf_a;" "wf_a <= fire; wf_b <= wf_a; wf_c <= wf_b;"; sub $T "nsec_lo_n = wf_b ?" "nsec_lo_n = wf_c ?"; sub $T "(wf_b && nsec_lf)" "(wf_c && nsec_lf)"; sub $T "if (wf_b) nsec_lf" "if (wf_c) nsec_lf"; sub $T "reg  wf_a, wf_b," "reg  wf_c; reg  wf_a, wf_b,";;
 m_oh2) sub $T "o_h <= ld_o ? o_n[287:0] : o_h;" "o_h <= o_pin;";;
 m_ovp) sub $T "o_vp <= s_nz || push; end" "o_vp <= push; end";;
 m_elast) sub $E "assign       e_last = qk_s[34] && ft[8];" "assign       e_last = ft[8];";;
 # exact cuts
 m_slraw) sub $E "sl_raw <= {34{raw_n}};" "sl_raw <= {34{is_raw}};";;
 m_slsc) sub $E "sl_sc <= {32{sc_n}};" "sl_sc <= {32{is_ikey && ik_sc}};";;
 m_slp0) sub $E "sl_p0 <= {32{st_ph_n[0]}};" "sl_p0 <= {32{st_ph[0]}};";;
 m_mbq) sub $E "mb_q[mb] <= take_n[5] || (5'(mb) < take_n[4:0]);" "mb_q[mb] <= take_r[5] || (5'(mb) < take_r[4:0]);";;
 m_ralo) sub $E "ra_lo <= dh[31:16]; ra_hi" "ra_lo <= {dh[31:17], 1'b0}; ra_hi";;
 m_ralf) sub $E "if (ra_lf) ra_hi <= ra_hi + 16'd1;" ";";;
 m_raflag) sub $E "ra_lf <= dh[31:16] == 16'hffff;" "ra_lf <= 1'b0;";;
 m_rowlf) sub $E "if (row_lf) row_hi <= row_hi + 16'd1;" ";";;
 m_rowfl) sub $E "row_lf <= (dh_mode != M_RAW) && dh[159:144] == 16'hffff;" "row_lf <= 1'b0;";;
 m_rowhi) sub $E "row_hi <= (dh_mode == M_RAW) ? 16'd0 : {8'd0, dh[167:160]};" "row_hi <= 16'd0;";;
 *) echo "unknown $CASE"; exit 2;;
esac
SRC="$W/tb_ing4.sv $E $T $Q rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv tools/qwen_kv_die/spipe6_native_qual_2000/ot_sram_1r1w_32x128_m1.v"
 $V --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --top-module tb --Mdir $OUT/o_$CASE -o Vtb $SRC > $OUT/$CASE.vlog 2>&1 || { echo "$CASE BUILD FAIL"; grep -E "%Error" $OUT/$CASE.vlog | head -12 | cut -c1-200; exit 3; }
fi
$OUT/o_$CASE/Vtb "$@" 2>&1 | grep -vE "^- "
