#!/bin/bash
# KV-ING-5 11-06: run_ing.sh + lock-step twin (bench/tb_ing3f.sv, OLD=r3 before cut 19 renamed _old) + cut-19 mutants. KV-ING-1 11-05 r3 engine bench (DIE-KV-70/ING 11-04 bench).  usage (repo root as cwd): run_ing.sh OUT CASE [plusargs]; CASE: form | a mutant name (must FAIL)
set -u
OUT=$(mkdir -p "$1" && cd "$1" && pwd); CASE=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=results/kv_ing_rf3_1105
W=$OUT/src_$CASE; rm -rf $W; mkdir -p $W
cp $D/rtl/qkd_hr_ingest_eng/qkd_host_native_engine_ing3.sv $D/rtl/qkd_hr_ingest_eng/ot_hdc_ingest_fp8q_s.sv $D/bench/tb_ing3f.sv $W/
git show 26670d6ef6:$D/rtl/qkd_hr_ingest_eng/qkd_host_native_engine_ing3.sv | sed 's/^module qkd_host_native_engine_ing3 (/module qkd_host_native_engine_ing3_old (/' > $W/old_ing3.sv
E=$W/qkd_host_native_engine_ing3.sv; Q=$W/ot_hdc_ingest_fp8q_s.sv
sub(){ python3 -I - "$1" "$2" "$3" <<'PY' || { echo "SUBST FAIL: $2"; exit 2; }
import sys
p,a,b=sys.argv[1:4]; s=open(p).read(); assert s.count(a)>=1,(p,a); open(p,'w').write(s.replace(a,b))
PY
}
case $CASE in
 form) ;;
 m_kclo) sub $E "wire [3:0]   kc_lo  = {1'b0, ap_kcode[2:0]} + {1'b0, st_ph};" "wire [3:0]   kc_lo  = {1'b0, ap_kcode[2:0]} + {2'b0, st_ph[1:0]};";;
 m_kchi) sub $E "wire [28:0]  kc_hi1 = ap_kcode[31:3] + 29'd1;" "wire [28:0]  kc_hi1 = ap_kcode[31:3] + 29'd2;";;
 m_kcsel) sub $E "{kc_lo[3] ? kc_hi1 : ap_kcode[31:3], kc_lo[2:0]}" "{kc_lo[2] ? kc_hi1 : ap_kcode[31:3], kc_lo[2:0]}";;
 m_kslo) sub $E "+ {3'd0, st_ph == 3'd4};" "+ {3'd0, st_ph == 3'd3};";;
 m_kshi) sub $E "wire [28:0]  ks_hi1 = ap_kscal[31:3] + 29'd1;" "wire [28:0]  ks_hi1 = ap_kscal[31:3];";;
 m_lane) sub $E "i0_b <= 4'd9 * qi_t[3:0] + {qi_g, qi_dg};" "i0_b <= 4'd9 * (qi_t[3:0] ^ {3'd0, !qi_v}) + {qi_g, qi_dg};";;
 m_bank) sub $E "rb0 = 4'd9 * t0 + {qo_g, qo_s[1:0], 1'b0}" "rb0 = 4'd9 * t0 + {qo_g, qo_s[1:0], 1'b0} + 4'd1";;
 m_slot) sub $E "wire [255:0] sd_n = qo_slot ? sd0 : sd1;" "wire [255:0] sd_n = qo_slot ? sd1 : sd0;";;
 m_round) sub $Q "up = m[19] && ((|m[18:0]) || m[20]);" "up = m[19] && (|m[18:0]);";;
 m_shstale) sub $E "always @(posedge clk) sh_r <= ra_sh[255:0];" "always @(posedge clk) if (st_go || !st_ok_r && !ap_go) sh_r <= ra_sh[255:0];";;
 m_nowait) sub $E "st_ok_r <= ok0 && st_run && !is_raw && ap_go && !st_go && need_ok;" "st_ok_r <= ok0 && st_run && !is_raw && ap_go && need_ok;";;
 m_ok0) sub $E "st_ok_r <= ok0 && st_run" "st_ok_r <= st_run";;
 m_oh) sub $E "else if (fq_pop) oh <= {oh[6:0], oh[7]};" "else if (fq_pop) oh <= (gs == 7) ? {oh[3:0], oh[7:4]} : {oh[6:0], oh[7]};";;
 m_qkc) sub $E "qk_s <= {35{fq_ne_n}};" "qk_s <= {35{qk_wv}};";;
 m_rawclr) sub $E "ra_wp <= 3'd0; rawq_v <= 1'b0;" "ra_wp <= 3'd0;";;
 m_rawq) sub $E "rawq_v <= raw_load || (rawq_v && !st_go);" "rawq_v <= raw_load;";;
 m_w1) sub $E "w1 <= ra_w1_n;" "w1 <= ra_rp_n[7:5];";;
 m_off) sub $E "always @(posedge clk) off <= ra_rp[4:0];" "always @(posedge clk) off <= (gy == 3) ? ra_rp[4:0] ^ 5'd1 : ra_rp[4:0];";;
 m_ibq) sub $E "wire [511:0] w_code = ib_all[QB*512 +: 512];" "wire [511:0] w_code = (gb == 13) ? i1_code : ib_all[QB*512 +: 512];";;
 m_ibsel) sub $E "ib_sel1 <= ih_sel1;" "ib_sel1 <= ih_sel0;";;
 m_ihq) sub $E "ib_all <= {ih_all[1023:512], ih_all[1023:512], ih_all[511:0], ih_all[511:0]};" "ib_all <= {ih_all[1023:512], i1_code, ih_all[511:0], ih_all[511:0]};";;
 m_ihv) sub $E "wire qp_busy = i0_v || q1_v || i1_v || ih_v || ib_v" "wire qp_busy = i0_v || q1_v || i1_v || ib_v";;
 m_ihlast) sub $E "ih_last <= i1_last;" "ih_last <= i1_last || i1_v;";;
 m_fiwp) sub $E "if (fi_push) fi_wp <= !fi_wp;" "fi_wp <= 1'b0;";;
 m_fdrp) sub $E "if (fd_pop) fd_rp <= !fd_rp;" "if (fd_push) fd_rp <= !fd_rp;";;
 m_firdy) sub $E "fi_rdy <= fi_n_n != 2'd2;" "fi_rdy <= 1'b1;";;
 m_fdrdy) sub $E "fd_rdy <= fd_n_n != 2'd2;" "fd_rdy <= 1'b1;";;
 m_busyf) sub $E "busy_q <= busy || fi_n != 2'd0 || fd_n != 2'd0 || fi_n_n != 2'd0 || fd_n_n != 2'd0;" "busy_q <= busy || fi_n != 2'd0 || fi_n_n != 2'd0;";;
 m_busyn) sub $E "busy_q <= busy || fi_n != 2'd0 || fd_n != 2'd0 || fi_n_n != 2'd0 || fd_n_n != 2'd0;" "busy_q <= busy || fi_n_n != 2'd0 || fd_n_n != 2'd0;";;
 m_pushq) sub $E "(ra_room && beats_nz && !push_q)" "(ra_room && beats_nz)"; sub $E "ra_room && beats_nz && !push_q;" "ra_room && beats_nz;";;
 m_apskip) sub $E "ap_ok1m <= !ap_inval && st_act && ap_ok1;" "ap_ok1m <= !ap_inval && st_act;";;
 m_last) sub $E "qo_s[1:0] == 2'd3 && t5 == od_thim1" "qo_s[1:0] == 2'd2 && t5 == od_thim1";;
 m_cred) sub $E "wire         q_iss = qo_act && !cred[3];" "wire         q_iss = qo_act && !(cred[3] && cred[0]);";;
 m_kvswap) sub $E "kr <= q_iss && !qo_v; vr <= q_iss && qo_v;" "kr <= q_iss && qo_v; vr <= q_iss && !qo_v;";;
 m_done) sub $E "done_q <= done_r; dtag_q <= dtag_r; wf_q <= w_fire;" "done_q <= done_r; dtag_q <= dtag_r; wf_q <= wf_q2; wf_q2 <= w_fire;"; sub $E "reg          done_r, done_q, wf_q;" "reg          done_r, done_q, wf_q, wf_q2;";;
 m_addr) sub $E "{8'd0, fa[22:14], 1'b0, fa[13:0]}" "{8'd0, fa[22:15], 1'b0, fa[14:0]}";;
 m_kvbit) sub $E "od_lay <= sd_n[217] ? sd_n[37:32] : sd_n[36:31];" "od_lay <= sd_n[36:31];";;
 m_take) sub $E "take_r <= is_rows ? k_take : ik_low ? 6'd32 : st_ph == 3'd2 ? 6'd4 : 6'd0;" "take_r <= k_take;";;
 m_use) sub $E "q1_use <= {!(i0_fp32 || i0_bf16), !(i0_fp32 || i0_bf16), !i0_fp32};" "q1_use <= {!(i0_fp32 || i0_bf16), !i0_fp32, !i0_fp32};";;
 m_gw) sub $E "wire         g_end = !qf_k2 || qi_g;" "wire         g_end = qi_g;";;
 m_scale) sub $E "(st_ph[0] ? sc0 : sc1)" "(st_ph[0] ? sc1 : sc0)";;
 m_bvsel) sub $E "bank_v <= s2_isv ?" "bank_v <= !s2_isv ?";;
 *) echo "unknown $CASE"; exit 2;;
esac
SRC="$W/tb_ing3f.sv $W/old_ing3.sv $E $Q rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv tools/qwen_kv_die/spipe6_native_qual_2000/ot_sram_1r1w_32x128_m1.v"
if [ ! -x $OUT/o_$CASE/Vtb ] || [ -z "${REUSE:-}" ]; then
 $V --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --top-module tb --Mdir $OUT/o_$CASE -o Vtb $SRC > $OUT/$CASE.vlog 2>&1 || { echo "$CASE BUILD FAIL"; grep -E "%Error" $OUT/$CASE.vlog | head -12 | cut -c1-200; exit 3; }
fi
$OUT/o_$CASE/Vtb "$@" 2>&1 | grep -vE "^- " 
