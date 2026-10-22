#!/bin/bash
# KV-BIND4-GUARD: Verilator 5.050 lint of the KV die HOST frame roots, MU 0 (qkd_host_root_admission) vs MU 1 (_mu)
set -u; C=$1; B=/srv/opentallas-scratch/claude/kv-bind4-guard-1019; M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
mkdir -p $B; git -C $M fetch -q https://github.com/bojieli/OpenTallas claude/kv-bind4-guard-1019
S=$B/src-$C; [ -d $S ] || git -C $M worktree add -q --detach $S $C; cd $S
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; $V --version
SRCS=$(bash -c 'source physical/ref_tile/qkd_hr_core_guard/kit.env 2>/dev/null; echo $SRCS')
MUF="rtl/qwen_sys/mu_qwen_20261018/qkd_host_root_admission_mu.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_tp8_coordinator_mu.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_peer_coordinator_codec_mu.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_coordinator_services_mu.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_lifecycle_collected_mu.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_post_collector_mu.sv rtl/qwen_sys/mu_qwen_20261018/ot_qwen_tp8_token_cohort_mu.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv"
SRCS=$(echo $SRCS | tr ' ' '\n' | grep -v host_cluster_mu/qkd_hr_core_guard.v | grep -v '_bb.v$' | tr '\n' ' ')
SRCS="$SRCS physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v"
YD=$(for d in $(ls -d physical/asap7_memory_macros/*/) $(ls -d rtl/qwen_sys/*/ rtl/lib rtl/link rtl/physical rtl/hdc/ingest rtl/qwen_split); do echo -n " -y $d"; done)
rc=0
for top in qkd_host_root_admission qkd_host_root_admission_mu; do
  echo "== $top"
  $V --lint-only -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINCONNECTEMPTY -Wno-DECLFILENAME -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
    --top-module $top $YD -DSYNTHESIS $SRCS $MUF > $B/lint_$top.log 2>&1; r=$?
  grep -c '%Warning' $B/lint_$top.log; grep '%Error' $B/lint_$top.log | head -20; echo "rc=$r"; [ $r = 0 ] || rc=1
  grep '%Warning' $B/lint_$top.log | sed 's/:[0-9]*:[0-9]*:/:/' | sort | uniq -c | sort -rn | head -5
done
exit $rc
