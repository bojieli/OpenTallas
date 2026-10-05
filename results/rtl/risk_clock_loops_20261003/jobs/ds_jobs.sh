#!/bin/bash
# DeepSeek-V4.1 ROM control-loop SS clock screens (risk check 2026-10-03), pinned source e156ed54e.
# Parameters: resolved from the runtime die top ot_v41_rt_die_l20_owner_safe with the driver's flags
# (tools/w17_current_fastpp_owner_safe_die_rt.py: -DV41_ATT_CUT -Irtl/hdc/v41 -GROM_PHW=6 -GWINDOW_REFILL_CREDITS=8
#  -GWINDOW_REFILL_OWNER_SAFE=1 -GX_IDX=2 -GX_SEL=1 -GIDX_RING=1 -GSUN=256 -GSUM=64 -GCL_LANES=16 -GCL_DEPTH=512
#  -GCL_RELAY=0) by a Verilator 5.050 --json-only elaboration (per-instance GPARAM values).
# Runner: ../jobs/ds_screen.py (wrapper of tools/risk_clock_loops_screen.py, see its docstring).
# Usage: bash ds_jobs.sh [label ...]   (no args: all jobs, launched concurrently)
cd ~/rcl-20261003/src || exit 1
RUN=../runs/ds; mkdir -p $RUN
LIST=tools/w17_current_fastpp_l20_window_owner_safe_sources.txt
COM="--resolve-from $LIST --define V41_ATT_CUT --include rtl/hdc/v41"
CTL='ctl=(^|\.)(st|state|pst|ph|pc|busy|pend|run|running|rr|cnt|wp|rp|ds|drain|e_mode|rx_st|tx_st|st_rx|st_user|nu_pend|step|stg|stn|ld_run|sm_run|s_ph|a_started|go|issue_unit)(\[|\$|$)'
declare -A J
declare -A G   # expected peak GB for ~/bin/admit.sh (default 4)
declare -A E   # per-job environment (DS_DIE_UM: fixed die for IO-heavy tops)
FSM='fsm=(^|\.)(st|pc)(\[|\$|$)'
ISS='issue=(^|\.)(me_go|su_go|qe_go|xu_go|he_go|coll_go|issue_unit|prog_re|prog_addr|wrel_v)(\[|\$|$)'
IST='istep=(^|\.)(a_istep|a_rstep|p_istep|p_rstep|c_istep|cwp|rp_tot|lst_seq|lst_mark)(\[|\$|$)'
EQC='ctl=(^|\.)(drain|walk\w*|go_\w*|issue\w*|a_ctr|w_\w+|n_\w+)(\[|\$|$)'
P12=0.833; P09=1.111
# 1. core sequencer (units black-boxed)
CORE_P="--param FULL_SHAPE=1 --param KV_HBM=1 --param X_HE=1 --param X_ME=0 --param X_ATT=1 --param X_IDX=2 --param PIKH_HAW=30 --param IDX_RING=1 --param IDX_RING_RSB=64 --param IDX_RING_RTAIL=32 --param X_SEL=1 --param X_SU=1 --param SUN=256 --param SUM=64 --param MBAW=18 --param CKV_SEL=1 --param X_ROM=1 --param ROM_R=128 --param ROM_PHW=6 --param ROM_SAW=16 --param ROM_BST=17 --param NSLOT=1 --param RANK=0"
CORE_BB="--blackbox ot_hdc_v41_matvec --blackbox ot_hdc_v41x_att_adapt --blackbox ot_hdc_v41x_idx_pool_adapt --blackbox ot_hdc_v41x_idx_pool_kwr --blackbox ot_hdc_v41x_su_adapt --blackbox ot_v41_rom_adapt --blackbox ot_v41_spine_w17w10 --blackbox ot_hdc_v41_qe --blackbox ot_hdc_v41x_window_kv_blocks --blackbox ot_hdc_v41x_xu_adapt --blackbox ot_hdc_v41x_he_adapt"
CORE="--top ot_hdc_core_v41x --source rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv $COM $CORE_P $CORE_BB --focus $FSM --focus $ISS"
STUB_CORE="DS_STUB=ot_hdc_v41x_me_adapt,ot_hdc_v41x_idx_adapt,ot_hdc_v41x_idx_kwr,ot_hdc_v41_stream,ot_hdc_v41_xu,ot_hdc_v41_hcproj"
E[ds01_core_1g2]=$STUB_CORE; E[ds01_core_0g9]=$STUB_CORE
J[ds01_core_1g2]="$CORE --period-ns $P12 --domain 1.2GHz-control"
J[ds01_core_0g9]="$CORE --period-ns $P09 --domain 0.9GHz-serial"
# 2. spine (strom/phrom are ROMs in silicon; SAW reduced so Yosys need not build a 65,536x48 flop ROM)
SPINE="--top ot_v41_spine_w17w10 --source rtl/v41die/ot_v41_spine_w17w10.sv $COM --param PHW=6 --param R=128 --param VAW=30 --param VRD=64 --param BST=17 --focus $CTL"
E[ds02_spine_k6144_saw10]="DS_DIE_UM=650"; E[ds02_spine_k512_saw10]="DS_DIE_UM=650"
J[ds02_spine_k6144_saw10]="$SPINE --param SAW=10 --param KMAX=6144 --period-ns $P12 --domain 1.2GHz"
J[ds02_spine_k512_saw10]="$SPINE --param SAW=10 --param KMAX=512 --period-ns $P12 --domain 1.2GHz"
# 3. ROM adapter
J[ds03_rom_adapt]="--top ot_v41_rom_adapt --source rtl/v41die/ot_v41_rom_adapt.sv $COM --param AW=30 --param NW=21 --param W=16 --param IL=8 --param PHW=6 --param VAW=30 --focus $CTL --period-ns $P12 --domain 1.2GHz"
# 4. SU adapter (vector unit black-boxed)
E[ds04_su_adapt]="DS_DIE_UM=3600"
J[ds04_su_adapt]="--top ot_hdc_v41x_su_adapt --source rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv $COM --param N=256 --param M=64 --param LV=7 --param AW=30 --param NW=21 --param CLS_DRAIN=0 --blackbox ot_hdc_v41x_vec --source rtl/hdc/v41x/ot_hdc_v41x_vec.sv --focus $CTL --period-ns $P09 --domain 0.9GHz-serial"
# 5. vector unit (256 lanes, reducer and side unit black-boxed: the pst/issue control remains)
VEC="--top ot_hdc_v41x_vec --source rtl/hdc/v41x/ot_hdc_v41x_vec.sv $COM --param N=256 --param M=64 --param LV=7 --param AW=30 --param NW=21 --focus $CTL --focus $IST"
J[ds05_vec_bbdp]="$VEC --blackbox ot_hdc_v41x_vec_lane --blackbox ot_hdc_v41x_vec_red --blackbox ot_hdc_v41x_vec_side --source rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv --source rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv --source rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv --period-ns $P09 --domain 0.9GHz-serial"
J[ds05_vec_bbdp_n64]="${J[ds05_vec_bbdp]/--param N=256 --param M=64/--param N=64 --param M=16}"; E[ds05_vec_bbdp_n64]="DS_DIE_UM=2000"; G[ds05_vec_bbdp_n64]=12
J[ds05_vec_n16_full]="--top ot_hdc_v41x_vec --source rtl/hdc/v41x/ot_hdc_v41x_vec.sv $COM --param N=16 --param M=8 --param LV=7 --param AW=30 --param NW=21 --focus $CTL --period-ns $P09 --domain 0.9GHz-serial"
# 6. Sinkhorn sequencer (as named; the runtime die instantiates ot_hdc_sinkhorn_mc, see report)
J[ds06_sinkhorn_seq]="--top ot_hdc_sinkhorn_seq --source rtl/hdc/v41/ot_hdc_sinkhorn_seq.sv $COM --focus $CTL --period-ns $P09 --domain 0.9GHz-serial"
# 7. accept/commit (DSpark/MTP; NSLOT=1 in the shipped L20 runtime, screened at NSLOT=8 NW=21)
J[ds07_accept]="--top ot_hdc_accept --source rtl/hdc/ot_hdc_accept.sv $COM --param NSLOT=8 --param NW=21 --focus $CTL --period-ns $P09 --domain 0.9GHz-serial"
# 8. indexer ring port FIFO credit, key-stream ring control
E[ds08_idx_ring_port]="DS_CHPARAM=1"
J[ds08_idx_ring_port]="--top ot_hdc_v41x_idx_ring_port --source rtl/hdc/v41x/ot_hdc_v41x_idx_ring_port.sv $COM --param AW=30 --param RSB=64 --param RTAIL=32 --param WIDE_REC=1 --focus $CTL --period-ns $P12 --domain 1.2GHz"
J[ds08_idx_kctl_ring]="--top ot_hdc_v41x_idx_kctl_ring --source rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv $COM --param NPC=32 --param WB=32 --param GA=24 --param AW=30 --param HW=23 --param TAGW=16 --param LENW=4 --param BEATW=4 --focus $CTL --period-ns $P12 --domain 1.2GHz"
# 9. select (full) and its sel_ctl
J[ds09_sel]="--top ot_hdc_v41x_sel --source rtl/hdc/v41x/ot_hdc_v41x_sel.sv $COM --param Q=4 --param W=16 --param IW=20 --param K=2048 --param AW=8 --param DG=8 --param OD=4 --focus $CTL --period-ns $P12 --domain 1.2GHz"
J[ds09_sel_ctl]="--top ot_hdc_v41x_sel_ctl --source rtl/hdc/v41x/ot_hdc_v41x_sel.sv $COM --param Q=4 --param K=2048 --focus $CTL --period-ns $P12 --domain 1.2GHz"
# 10. collective top-k merge (full shape, as instantiated by ot_w15_coll_dma TOPK=1)
J[ds10_topk_merge]="--top ot_coll_topk_merge --source rtl/chip/ot_coll_topk_merge.sv $COM --param N=4 --param NMAX=2048 --param LW=16 --param LDW=4 --param P=64 --param PF=64 --param DIG=8 --focus $CTL --period-ns $P12 --domain 1.2GHz"
# 11. collective DMA (merge + transpose black-boxed) and one-shot collective engine
E[ds11_coll_dma]="DS_DIE_UM=420"
J[ds11_coll_dma]="--top ot_w15_coll_dma --source rtl/chip/ot_w15_coll_dma.sv $COM --param WA=15 --param FW=512 --param TAGW=32 --param N=4 --param GW=4 --param VM_ALWAYS_READY=1 --param TOPK=1 --blackbox ot_coll_topk_merge --blackbox ot_chip_v41x_coll_transpose --source rtl/chip/ot_coll_topk_merge.sv --source rtl/chip/ot_chip_v41x_coll_transpose.sv --focus $CTL --period-ns $P12 --domain 1.2GHz"
OS="--top ot_w15_rom_oneshot_die_px --source rtl/rom/ot_w15_rom_oneshot_px.sv $COM --param N=4 --param RANK=0 --param LANES=16 --param TAGW=32 --param PKG_DIES=2 --param RELAY=0 --param ADD_LAT=3 --param PAIRWISE=1 --param GW=4 --param OUT_BP=1 --param FIFO_SRAM=0 --focus $CTL"
J[ds11_oneshot_d32]="$OS --param DEPTH=32 --period-ns $P12 --domain 1.2GHz"
# 12. package controller (full MAXU=866 and a reduced-table variant)
PK="--top ot_rom_pkg_ctrl_x --source rtl/rom/ot_rom_pkg_ctrl_x.sv $COM --param PKG_ID=0 --param FLIT=512 --param NW=21 --param AW=30 --param VWA=15 --param USER_W=10 --param KVW=32768 --param XWORDS=1 --param RXWORDS=1 --param RXB=0 --param TXB=0 --param SOURCE=0 --param RESULT_PARTS=1 --param SEND_HIDDEN=0 --param HID_DEST=0 --param SEND_RESULT=0 --param RES_DEST=0 --param COMBINE_IN=0 --param ROW0=0 --param FWD_TOKEN=1 --focus $CTL"
J[ds12_pkg_ctrl_u866]="$PK --param MAXU=866 --period-ns $P12 --domain 1.2GHz"
J[ds12_pkg_ctrl_u64]="$PK --param MAXU=64 --period-ns $P12 --domain 1.2GHz"
# 13. HBM K-port round-robin arbiter
E[ds13_karb]="DS_DIE_UM=1000"
J[ds13_karb]="--top ot_chip_v41x_hbm_karb --source rtl/chip/ot_chip_v41x_hbm_karb.sv $COM --param NPC=32 --param AW=30 --param TAGW=16 --focus $CTL --period-ns $P12 --domain 1.2GHz"
# 14. window refill schedule
J[ds14_refill_sched]="--top ot_chip_v41x_window_refill_schedule --source rtl/chip/ot_chip_v41x_window_refill_schedule.sv $COM --param POS_W=21 --param USER_W=10 --param MAX_CONTEXT=1048576 --param ALLOW_RETAIN=0 --focus $CTL --period-ns $P12 --domain 1.2GHz"
# 15. ROM q element (pair) with its ICG: focus on the ICG ENA pin and the drain/walk control
EQ="--top ot_v41_rom_elem_q_w10 --source rtl/v41rom/ot_v41_rom_elem_q_w10.sv --resolve-from ../jobs/ds_w10_srcs.txt --param NB=2 --param MTP=1 --param EARLY=1 --param FAST=1 --param PP=1 --blackbox ot_rom_4096x274_m8 --blackbox ot_rom_8192x274_m8 --focus icg=u_icg --focus $EQC"
J[ds15_elem_q]="$EQ --period-ns $P12 --domain 1.2GHz"

G[ds02_spine_k6144_saw10]=45; G[ds02_spine_k512_saw10]=8; G[ds05_vec_n16_full]=12; G[ds10_topk_merge]=10; G[ds15_elem_q]=12; G[ds01_core_1g2]=10; G[ds01_core_0g9]=10; G[ds05_vec_bbdp]=8; G[ds12_pkg_ctrl_u866]=10
# second-period screens of blocks that fail their domain clock (achievable fmax at the other domain)
for L in ds03_rom_adapt ds08_idx_kctl_ring ds09_sel_ctl ds12_pkg_ctrl_u64 ds14_refill_sched ds08_idx_ring_port ds13_karb ds10_topk_merge ds02_spine_k512_saw10 ds11_coll_dma; do
  J[${L}_0g9]="${J[$L]/--period-ns $P12 --domain 1.2GHz/--period-ns $P09 --domain 1.2GHz-at-0.9GHz}"; E[${L}_0g9]="${E[$L]}"; G[${L}_0g9]="${G[$L]}"
done
for L in ds06_sinkhorn_seq ds07_accept ds04_su_adapt ds05_vec_bbdp; do
  J[${L}_1g2]="${J[$L]/--period-ns $P09 --domain 0.9GHz-serial/--period-ns $P12 --domain 0.9GHz-serial-at-1.2GHz}"; E[${L}_1g2]="${E[$L]}"; G[${L}_1g2]="${G[$L]}"
done

launch() {
  local L=$1
  env ${E[$L]} nohup ~/bin/admit.sh ${G[$L]:-4} -- python3 ../jobs/ds_screen.py ${J[$L]} --work $RUN/$L --output $RUN/$L.json --label $L > $RUN/$L.log 2>&1 &
  echo "launched $L pid $!"
}
if [ $# -gt 0 ]; then for L in "$@"; do launch $L; done; else for L in "${!J[@]}"; do launch $L; done; fi
