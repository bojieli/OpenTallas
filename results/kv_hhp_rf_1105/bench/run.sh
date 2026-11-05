#!/bin/bash
# DIE-KV-71/HHP 11-05 form bench.  usage: run.sh OUT [J]  from repo root.  Lockstep old (git base) vs form; each MUT must FAIL.
set -u
OUT=$(mkdir -p "$1" && cd "$1" && pwd); J=${2:-8}; ROOT=$(pwd); BASE=${BASE:-cb98b2e232}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=results/kv_host_regen_1/rtl_rf3/qkd_kvs_pcc_h_head_p; B=results/kv_hhp_rf_1105/bench
mkdir -p $OUT/old
for f in ot_qkd_static_kv_timing:ot_qkd_static_kv_timing ot_qkd_static_ctrl_pc_emb:ot_qkd_static_ctrl_pc_emb qkd_controller_hbm_calendar:qkd_controller_hbm_calendar qkd_kv_pc_chain_station_b_p:qkd_kv_pc_chain_station_b_p; do
  n=${f%%:*}; git show $BASE:$D/$n.sv | sed "s/^\(\s*\)module $n\b/\1module ${n}_old/" > $OUT/old/$n.sv
done
sed -i 's/^ ot_qkd_static_kv_timing #/ ot_qkd_static_kv_timing_old #/' $OUT/old/ot_qkd_static_ctrl_pc_emb.sv
EXTRA="$D/qkd_static_kv_return_calendar.sv"
one(){ # tag tb src-stem plusargs -- gparams; MUT="old=>new" in env M
  local tag=$1 tb=$2 stem=$3; shift 3; local args=$1; shift
  local w=$OUT/$tag; rm -rf $w; mkdir -p $w; cp $D/$stem.sv $w/$stem.sv
  if [ -n "${M:-}" ]; then python3 -I - "$w/$stem.sv" "$M" <<'PY' || { echo "SUBST_FAIL $tag" | tee $OUT/$tag.res; return; }
import sys
p,m=sys.argv[1:3]; a,b=m.split("=>"); s=open(p).read(); assert s.count(a)>=1,a; open(p,"w").write(s.replace(a,b))
PY
  fi
  local ex=""; [ $stem = qkd_controller_hbm_calendar ] && ex=$EXTRA
  [ $stem = ot_qkd_static_ctrl_pc_emb ] && ex="$D/ot_qkd_static_kv_timing.sv $OUT/old/ot_qkd_static_kv_timing.sv"
  "$V" --binary -j 2 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module $tb "$@" -Mdir $w/o -o Vtb $B/$tb.sv $OUT/old/$stem.sv $w/$stem.sv $ex > $w/build.log 2>&1 || { echo "BUILD_FAIL $tag" | tee $OUT/$tag.res; return; }
  $w/o/Vtb $args > $w/run.log 2>&1; local l=$(grep -E "^(PASS|FAIL)" $w/run.log | head -1 | cut -c1-200)
  if [ -n "${M:-}" ]; then case "$l" in FAIL*) echo "CAUGHT $tag $l";; *) echo "MISSED $tag $l";; esac
  else case "$l" in PASS*) echo "PASS $tag $l";; *) echo "NOPASS $tag $l $(tail -1 $w/run.log | cut -c1-200)";; esac; fi | tee $OUT/$tag.res
  rm -rf $w/o
}
job(){ while [ "$(jobs -rp | wc -l)" -ge "$J" ]; do wait -n; done; ( one "$@" ) & }
for s in 1 2 3; do
  for g in "0 1 1" "0 0 0" "1 1 1"; do set -- $g
    M="" job t_p$1c$2r$3_s$s tb_timing_ls ot_qkd_static_kv_timing "+seed=$s +cycles=1500000" -GPROFILE_P=$1 -GCTX=$2 -GSR=$3
  done
  M="" job e_c1_s$s tb_emb_ls ot_qkd_static_ctrl_pc_emb "+seed=$s +cycles=1500000" -GCTX=1 -GSR=1
  M="" job e_c0_s$s tb_emb_ls ot_qkd_static_ctrl_pc_emb "+seed=$s +cycles=1500000" -GCTX=0 -GSR=0
  M="" job c_s$s tb_cal_ls qkd_controller_hbm_calendar "+seed=$s +cycles=1500000"
  M="" job c_m1_s$s tb_cal_ls qkd_controller_hbm_calendar "+seed=$s +cycles=300000" -GMUTP=1
  M="" job c_m2_s$s tb_cal_ls qkd_controller_hbm_calendar "+seed=$s +cycles=300000" -GMUTP=2
  M="" job h_0_s$s tb_chain_ls qkd_kv_pc_chain_station_b_p "+seed=$s +cycles=1000000" -GPCP=0
  M="" job h_5_s$s tb_chain_ls qkd_kv_pc_chain_station_b_p "+seed=$s +cycles=1000000" -GPCP=5
done
T=ot_qkd_static_kv_timing; TA="+seed=1 +cycles=1500000"; G="-GPROFILE_P=1 -GCTX=1 -GSR=1"
M="swait >= 8'(S_STARVE - 1)=>swait >= 8'(S_STARVE)" job m_swait tb_timing_ls $T "$TA" $G
M="&& swait >= 8'(S_STARVE - 1);=>;" job m_swait2 tb_timing_ls $T "$TA" $G
M="ref_is1 <= (ref_n == RW'(1))=>ref_is1 <= (ref_n == RW'(2))" job m_ref tb_timing_ls $T "$TA" $G
M=" && !forced_pre;=>;" job m_fp tb_timing_ls $T "$TA" $G
M="!(REF_MODE && ref_due_n && ref_pend) &&=>" job m_refbr tb_timing_ls $T "$TA" $G
M="(rp_sp && |(rd_oh & sb_oh)) || =>" job m_rdrp tb_timing_ls $T "$TA" $G
M=" || (cp_sp && |(rd_oh & c_oh))=>" job m_rdcp tb_timing_ls $T "$TA" $G
# (rp_sp && |(hb_oh & sb_oh)) has no mutant: s_pre_ok needs !h_holdn and the write head is in hold_n, so it cannot fire with wq_ne
M=" || (cp_sp && |(hb_oh & c_oh))=>" job m_wrcp tb_timing_ls $T "+seed=2 +cycles=1500000" -GPROFILE_P=0 -GCTX=1 -GSR=1
M="c_sp <= rp_sp;=>c_sp <= 1'b0;" job m_csp tb_timing_ls $T "$TA" $G
M="ras_zr <= ras_zn[b];=>ras_zr <= (ras == 0);" job m_ras tb_timing_ls $T "$TA" $G
M="&& (!W || (wr_e ? (T_WRR - 1 == 0) : wrr_le1[b]));=>;" job m_rtpw tb_timing_ls $T "$TA" $G
M="(rd_e ? (T_RTP - 1 == 0) : rtp_le1[b])=>rtp_le1[b]" job m_rtpr tb_timing_ls $T "$TA" $G
# form B: production slots.  Each of these must fail against the old core
G0="-GPROFILE_P=0 -GCTX=1 -GSR=1"; TB="+seed=1 +cycles=1500000"
M="wire rd_pin = rd_ok && legal_rd;=>wire rd_pin = rd_ok;" job m_pinrd tb_timing_ls $T "$TB" $G0
M="wire wr_pin = wr_ok && legal_write;=>wire wr_pin = wr_ok;" job m_pinwr tb_timing_ls $T "$TB" $G0
M="wire s_go_pin = s_go && legal_static;=>wire s_go_pin = s_go;" job m_pins tb_timing_ls $T "$TB" $G0
M="(reserved_static_col || (boot_static_col && legal_static))=>(reserved_static_col)" job m_boot tb_timing_ls $T "$TB" $G0
M="(PROFILE == 1) ? legal_write : reserved_write_col=>(PROFILE == 1) ? legal_write : 1'b0" job m_wrslot tb_timing_ls $T "$TB" $G0
M="ctx_sel <= sq_rp[1];=>ctx_sel <= sq_rp[0];" job m_ctxsel tb_timing_ls $T "$TB" $G0
M="ctx_lo <= sq_rp[0] ?=>ctx_lo <= !sq_rp[0] ?" job m_ctxlo tb_timing_ls $T "$TB" $G0
M="ctx_hi <= sq_rp[0] ?=>ctx_hi <= !sq_rp[0] ?" job m_ctxhi tb_timing_ls $T "$TB" $G0
M="!(REF_MODE && (ref_c == RW'(LEAD) || ref_c == RW'(LEAD + 1)) && wq_bank[i] == bsel)=>1'b1" job m_wqref tb_timing_ls $T "$TB" $G0
M="if (sl_act[WQW'(wq_rp + ai)]) begin=>if (sl_act[WQW'(ai)]) begin" job m_wqord tb_timing_ls $T "$TB" $G0
M="wab_oh_n = wq_oh[WQW'(wq_rp + ai)];=>wab_oh_n = wq_oh[WQW'(ai)];" job m_wqoh tb_timing_ls $T "$TB" $G0
M="W && wq_v[i] &&=>W &&" job m_wqv tb_timing_ls $T "$TB" $G0
E=ot_qkd_static_ctrl_pc_emb; EA="+seed=1 +cycles=1000000"
M="live_q<=(count!=4'd1)=>live_q<=(count!=4'd2)" job m_live tb_emb_ls $E "$EA" -GCTX=1 -GSR=1
M="(cmd_q[31:30]==3 && !in_ctx) || =>" job m_mal0 tb_emb_ls $E "$EA" -GCTX=0 -GSR=0
M="first_q>=cmd_q[29:19]=>first_q>cmd_q[29:19]" job m_mal1 tb_emb_ls $E "$EA" -GCTX=1 -GSR=1
M="first_q>128=>first_q>129" job m_mal2 tb_emb_ls $E "$EA" -GCTX=1 -GSR=1
M="cmd_q[27:19]>256=>cmd_q[27:19]>255" job m_mal3 tb_emb_ls $E "$EA" -GCTX=1 -GSR=1
M="head_mal<=mal_fifo[rp_next]=>head_mal<=in_mal" job m_malf tb_emb_ls $E "$EA" -GCTX=1 -GSR=1
C=qkd_controller_hbm_calendar; CA="+seed=1 +cycles=800000"
M="live_r[i]<=(left_q[i]!=10'd1)=>live_r[i]<=(left_q[i]!=10'd0)" job m_left $(echo tb_cal_ls) $C "$CA"
M="wz_r[i]<=(wait_q[i]==16'd1)=>wz_r[i]<=(wait_q[i]==16'd0)" job m_wait tb_cal_ls $C "$CA"
M="(image[i][37:30]==8'd0)=>1'b0" job m_gap tb_cal_ls $C "$CA"
M="burst_q[i]+4'd1;wz_r[i]<=1;=>burst_q[i]+4'd1;wz_r[i]<=0;" job m_burst tb_cal_ls $C "$CA"
M="wz_r[i]<=(16'(image[i][15:0]+16'(MUT==1))==16'd0);=>" job m_load tb_cal_ls $C "$CA"
M="live_r[i]<=(image[i][25:16]!=10'd0);=>live_r[i]<=1'b1;" job m_cnt tb_cal_ls $C "$CA"
H=qkd_kv_pc_chain_station_b_p; HA="+seed=1 +cycles=300000"
M="{bh, bh, c[F_AD +: 29], c[F_D0 +: 256]}=>{bh, 1'b0, c[F_AD +: 29], c[F_D0 +: 256]}" job m_land1 tb_chain_ls $H "$HA"
M="c[F_D0 +: 256]};=>c[F_D1 +: 256]};" job m_land2 tb_chain_ls $H "$HA"
M="c[F_AD +: 29], c[F_D0=>c[F_EAD +: 29], c[F_D0" job m_land3 tb_chain_ls $H "$HA"
wait; cat $OUT/*.res | sort | awk '{print}' > $OUT/summary.txt; grep -cE "^(PASS|CAUGHT)" $OUT/summary.txt; grep -vE "^(PASS|CAUGHT)" $OUT/summary.txt; echo ALLDONE
