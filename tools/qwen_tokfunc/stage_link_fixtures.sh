#!/bin/bash
# TOK-FUNC-QW link stages (10-21): stage the bench FIXTURES of tp8 / ovl4u / ctx4u under RUNROOT/<stage>/fx on the gold hosts.
# Run on the coordinator host (needs the OpenTallas object store; nothing is checked out).  usage:
#   stage_link_fixtures.sh RUNROOT [HOST ...]          (default hosts: ot-gold1 ot-gold2)
# Sources (all committed, named by commit so the fixtures are reproducible):
#   ASM  = c0f8097f3 (RTL-only source assembly): SRAM v2 model + UCIe PHY model (the only modelled leg) + KV programme report
#   OVLB = 967c24eed (codex/sysface-ovl-1019 = claude/qw-sysface3-1019): run_d2d_ovl_mu.sh + tb_d2d_ovl_mu.sv (bench only)
#   RELB = claude/tok-func2-qw-1021 (override RELB=<sha>): run_d2d_ovl_mu_rel.sh + tb_d2d_ovl_mu_rel.sv (ovl4u --release-masters)
#          + macro views d2d_sram_1r1w_64x137_m1_r2c2_p288 (ASM) and ot_sram_1r1w_64x137_m1_r2c2_p192 (SF7V = 545cdd4bc: the
#          sf7 SAFE5/7 store's view, absent from the assembly) -> RUNROOT/ovl4u/fx/rel
#   CTXB = origin/codex/qw-token-pickup-takeover3-1019 (tb f8f2d2f9a): run_mu_context_real_link.sh + sources.f + tb (bench only)
#   MAIN = origin/main: results/rtl/mu_qwen_1018/coll/mu_cal.json (TP8 MU window commands)
#   LANES = the compute GEN coll_lane_latency.json: g5r3 GENs have none yet -> last complete GEN dv2f20g5r2b (ot-epyc6)
set -eu
RUNROOT=${1:?RUNROOT}; shift; HOSTS=("${@:-ot-gold1}"); [ $# -gt 0 ] || HOSTS=(ot-gold1 ot-gold2)
G="git -C /home/ubuntu/OpenTallas"
ASM=c0f8097f3; OVLB=967c24eed; CTXB=origin/codex/qw-token-pickup-takeover3-1019; MAIN=origin/main
RELB=${RELB:-claude/tok-func2-qw-1021}; SF7V=545cdd4bc
FIX=f98fd830f   # claude/tokfunc-qw-link-fix-1021: mu_calendar attn_extra/att_windows consumer (OVL compiler), patch for ovl4u
LANES_HOST=ot-epyc6; LANES=/srv/opentallas-scratch/claude/mu-die-qw/dv2f20g5r2b/out/case/coll_lane_latency.json
PHY=(physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2 physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv)
TMP=$(mktemp -d); trap 'rm -rf $TMP' EXIT
timeout 60 ssh $LANES_HOST cat $LANES > $TMP/g5r2b_coll_lane_latency.json
for h in "${HOSTS[@]}"; do
  ssh $h "mkdir -p $RUNROOT/tp8/fx/lanes $RUNROOT/ovl4u/fx $RUNROOT/ctx4u/fx"
  $G archive $MAIN results/rtl/mu_qwen_1018/coll/mu_cal.json | ssh $h tar -x -C $RUNROOT/tp8/fx
  ssh $h "cat > $RUNROOT/tp8/fx/lanes/coll_lane_latency.json; echo 'dv2f20g5r2b (last complete compute GEN; no g5r3 GEN has a coll_lane_latency.json on 10-21)' > $RUNROOT/tp8/fx/lanes/SOURCE" < $TMP/g5r2b_coll_lane_latency.json
  $G archive $ASM "${PHY[@]}" results/arch/qwen_kv_static_programme_1017/die | ssh $h tar -x -C $RUNROOT/ovl4u/fx
  $G archive $OVLB rtl/test/qwen_split/run_d2d_ovl_mu.sh rtl/test/qwen_split/tb_d2d_ovl_mu.sv | ssh $h tar -x -C $RUNROOT/ovl4u/fx
  ssh $h mkdir -p $RUNROOT/ovl4u/fx/overlay
  $G archive $OVLB rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv | ssh $h tar -x -C $RUNROOT/ovl4u/fx/overlay   # OVL end (DIAG overlay)
  ssh $h mkdir -p $RUNROOT/ovl4u/fx/rel
  $G archive $RELB rtl/test/qwen_split/run_d2d_ovl_mu_rel.sh rtl/test/qwen_split/tb_d2d_ovl_mu_rel.sv | ssh $h tar -x -C $RUNROOT/ovl4u/fx/rel
  $G archive $ASM physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288 | ssh $h tar -x -C $RUNROOT/ovl4u/fx/rel
  $G archive $SF7V physical/asap7_memory_macros_v2/ot_sram_1r1w_64x137_m1_r2c2_p192 | ssh $h tar -x -C $RUNROOT/ovl4u/fx/rel
  $G diff $ASM $FIX -- tools/qwen_static_schedule/mu_calendar.py | ssh $h "cat > $RUNROOT/ovl4u/fx/mu_calendar_attwin.patch"
  $G archive $ASM "${PHY[@]}" | ssh $h tar -x -C $RUNROOT/ctx4u/fx
  $G archive $CTXB rtl/test/qwen_split/run_mu_context_real_link.sh rtl/test/qwen_split/mu_context_real_link_sources.f \
     rtl/test/qwen_split/tb_mu_context_real_link.sv | ssh $h tar -x -C $RUNROOT/ctx4u/fx
  ssh $h "cd $RUNROOT && find tp8/fx ovl4u/fx ctx4u/fx -type f | sort | xargs sha256sum > link_fixtures.sha256; wc -l < link_fixtures.sha256"
done
