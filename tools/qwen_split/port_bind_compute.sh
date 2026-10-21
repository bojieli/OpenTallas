#!/bin/bash
# Owner no-stub gate for the Qwen split COMPUTE die: port-bind DIE_V against real RTL (compute-die lead r3, 2026-10-14).
# usage: tools/qwen_split/port_bind_compute.sh DIE_V OUTDIR     (exit 0 only when the die binds)
#   1. die relays / reset repeaters / the clock receiver of THIS build -> generated RTL (gen_relay_rtl.py)
#   (OT_PORT_BIND_STRAPS=FILE: the plan's own strap manifest, e.g. q_slice_1017/straps_dv2f8.json for the dv face dies)
#   2. tools/die_port_bind.py (full child closure since Q-STUB 10-17: every module under a die master must resolve;
#      memory macros from physical/asap7_memory_macros) with the compute-die RTL (rtl/ tree + the link / clock / reset slots), the hard-macro
#      models allowed as such (UCIe PHY, forwarded-clock bump), the contract straps (straps.json)
set -u
D=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2")
R=$(cd "$(dirname "$0")/../.." && pwd)
python3 $R/tools/qwen_split/gen_relay_rtl.py $D $O/die_glue.sv > $O/die_glue.json || exit 3
# the re-packed 45-entry tile (OT_SPLIT_TILE_GRANT) binds through its die-name wrappers (Q-NETLIST 10-16)
# MU-DIE-QW 10-19: the child closure (S81-LBGAP G6/G7 binder) found 6 modules defined with different interfaces in frozen
# kit copies (physical/ref_tile/*/src/rtl/...) and twice in rtl/ (ot_hdc_qadd): resolve a closed tile's modules from its spec
# sources (the RTL of record of the closed view) -- OT_PORT_BIND_REF_TILE_PREFER=0 restores the plain index.
RTP=; [ "${OT_PORT_BIND_REF_TILE_PREFER:-1}" = 1 ] && RTP=--ref-tile-prefer
T45=; grep -q 'ck_fa0' $D && T45="--rtl-file $R/rtl/physical/qfd_tile_rp2_45_slots.sv --rtl-file $R/rtl/physical/qfd_tile_nk_rp2_45.sv --rtl-file $R/rtl/physical/qfd_tile_nl_rp2_45.sv"
python3 $R/tools/die_port_bind.py $D $T45 --rtl-file $O/die_glue.sv --rtl-file $R/rtl/qwen_split/qfd_link_slots.sv --rtl-file $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv \
  --rtl-file $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
  --rtl-file $R/physical/qwen_missing_phy/tp8_1013/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy_bb.v \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --allow-model qfd_ckbump --allow-model qfd_sigbump --allow-model ot_qkvd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy_model \
  --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qfd_serdes_112g_x12_phy_s597 \
  --lib-root $R/physical/asap7_memory_macros \
  --define OT_QFD_UP4_CK_ENTRIES $RTP --strap-file ${OT_PORT_BIND_STRAPS:-$R/results/arch/qwen_split_compute_1014/straps.json} --out $O/port_bind.json > $O/port_bind.txt 2>&1
rc=$?
tail -1 $O/port_bind.txt
# Q-COLLCAL 10-18: lane audit (one stage count per bus group; landing K straps = the GEN's total E; io_collective LX0..2
# = the SerDes lane cycles TX(peer) + RX(own)).  Part of the strict bind: a die whose bus bits disagree, or whose collective
# calendar misses its lanes, faults its static schedule.  OT_LANE_AUDIT=0 skips it (diagnosis only).
if [ "${OT_LANE_AUDIT:-1}" = 1 ]; then
  python3 $R/tools/qwen_split/lane_latency_audit.py $D --out $O/lane_latency_audit.json > $O/lane_latency_audit.txt 2>&1; la=$?
  tail -1 $O/lane_latency_audit.txt
  [ $la -ne 0 ] && [ $rc -eq 0 ] && rc=4
  # QXF-SEAMC 10-18: record-bundle audit (TOKEN-XDIE-QWEN F5 / LAYERBENCH G-C2): every record bundle of the d2d_rom /
  # native59 / sys_face seams (valid + all fields of one record, selected by endpoint pins) arrives on ONE edge --
  # direct wires included (the lane audit above only sees relay chains, so a direct rx_v beside a landed rx_payload
  # passed it).  tools/qwen_split/record_bundles.py audit.
  python3 $R/tools/qwen_split/record_bundles.py audit $D --out $O/record_bundle_audit.json > $O/record_bundle_audit.txt 2>&1; ra=$?
  tail -1 $O/record_bundle_audit.txt
  [ $ra -ne 0 ] && [ $rc -eq 0 ] && rc=5
fi
# QLB-GEN 10-18 (LAYERBENCH G-C1): fail-closed parameter audit -- every die master whose RTL traps a sentinel-default
# parameter (qfd_tt_ctlm_dv XPF_TRANSPORT_EDGES -1, qfd_d2d_static TXDP 0) must get it from DIE_V.params.json, and the
# values must equal the ones re-derived from this die.v (1 hr reg + hr lane cycles; the production image's D2D_TXDP_C).
# tools/qwen_split/die_params.py audit.  OT_PARAM_AUDIT=0 skips it (diagnosis only).
if [ "${OT_PARAM_AUDIT:-1}" = 1 ]; then
  python3 $R/tools/qwen_split/die_params.py audit $D --port-bind $O/port_bind.json --src $R --out $O/die_param_audit.json > $O/die_param_audit.txt 2>&1; pa=$?
  tail -1 $O/die_param_audit.txt
  [ $pa -ne 0 ] && [ $rc -eq 0 ] && rc=6
fi
# QW-DIEFIX 10-19: hr bus field contract (tt_ctlm ROM command -> slice gi decode, QW-XHEAD XT1: as built go sat on
# hr[73] and no matvec started on the die).  Source layout of producer / pack / consumers + the die's hr chain (one whole
# 453-b net per hop, relays a -> b, slices hr_wi -> hr_eo).  tools/qwen_split/hr_contract.py.  OT_HR_CONTRACT=0 skips.
if [ "${OT_HR_CONTRACT:-1}" = 1 ]; then
  python3 $R/tools/qwen_split/hr_contract.py check --root $R --die-v $D --json $O/hr_contract.json > $O/hr_contract.txt 2>&1; hc=$?
  head -1 $O/hr_contract.txt
  [ $hc -ne 0 ] && [ $rc -eq 0 ] && rc=7
fi
exit $rc
