#!/usr/bin/env bash
# tok_func_xdie.sh OUTROOT [variant ...]      (TOK-FUNC-HBM-XDIE 2026-10-21; tree TOK.HDS.XDIE + the Qwen TP8 AR leg of TOK.HQ)
#
# ONE command: assemble the HBM COLL quadrant RTL of the release die from source revisions -> run every cross-die
# collective token-pass case on the existing two-die XDIE step vehicle (tb_xdie_hbm_step.sv, compiler
# tools/xdie_hbm_step_compile.py incl. mb_plan/compile_die_mb) and the AR-step vehicle (tb_xdie_hbm_coll.sv) ->
# report JSON (PASS/FAIL, measured cycles vs the composed values of results/rtl/xdie_hbm_1019/record.json).
# Grade of a source assembly: "RTL-functional (source assembly)"; of the gen variant: "die-netlist".
#
# Variants (default: r14_bound r14_lpars128 succ_lpars main_rows256 r14_coll_ar; gen added when XDIE_GEN_NETLIST is set):
#   r14_bound     DIE_REV COLL RTL, hb_coll_NE = ot_hfd_coll_q2_hard_v8g #(NLINK 1, TP 192) at the params the die binds
#                 (contract DIE_CONTRACT: no ROWS/AR_ITER -> ROWS 64, AR_ITER 0). Programmes compiled for 64 rows.
#   r14_lpars128  same DIE_REV RTL at the lp_ars parameters AR_ITER 1 / ROWS 128 (largest ROWS the DIE_REV RTL elaborates).
#   succ_lpars    the SAFE successor parent ot_hfd_coll_n1s0_lpf_ars (flat, AR_ITER 1 / ROWS 128; hard children
#                 issuer_m_r128, fj_n1s0_r128, link_e1 (body link_e2), 16 x reduce_lane) assembled from SUCC_* revs
#                 (3-way merged onto SUCC_BASE), everything else DIE_REV.
#   main_rows256  MAIN256_REV v8g #(AR_ITER 1, ROWS 256) (issuer_m256 / issuer_v7, HBM-COLL256): the only RTL that holds the
#                 218-row RS(144) programme.
#   r14_coll_ar   DIE_REV RTL on the AR-step vehicle (run_xdie_hbm_coll.sh ds+qw: 2-die ALL_REDUCE, golden rank fold).
#   gen           DIE-NETLIST HOOK: XDIE_GEN_NETLIST="<netlist .v files>" (the die GEN netlist of the hb_coll_NE master or
#                 the whole die), XDIE_GEN_TOP=<module of hb_coll_NE>, XDIE_GEN_CELLS="<cell/macro models>",
#                 XDIE_GEN_LINK=<hier path of its link leaf, default hb.u_link0>, XDIE_GEN_XPORTS=<extra port conns, default
#                 qid_rg/qid_wr = QID>, XDIE_GEN_DROP="<flist entries to drop, default the v8g file>", XDIE_GEN_DEFS="<+define+..>",
#                 XDIE_GEN_ROWS (128) -> same cases as r14_lpars128 against the netlist.
#
# Env: REPO (git repo holding every rev; default this script's repo), BENCH_REV (tb + compilers; default HEAD of REPO),
#   DIE_REV (1fe61477b = codex/hbm-die14-release-1021), DIE_CONTRACT (r14 pre_relay contract; masters/params verified),
#   SUCC_BASE fed23480d, SUCC_RL d755fcd4c (hcoll_reduce_lane_u), SUCC_LINK 34f85027d (hcoll_link_e2u, RTL edc9ede07),
#   SUCC_ISS 8827e4001 (issuer_m_r128 v12), MAIN256_REV origin/main,
#   RUN=fleet|local|assemble (assemble: sources + manifests only; fleet: src staged to FLEET_STAGE hosts under FLEET_ROOT, one unpinned ot-run per variant),
#   XDIE_CASES (optional subset, e.g. "qw_ag16:4:ag:16"), FLEET_STAGE "ot-gold1 ot-gold2", FLEET_ROOT /srv/opentallas-scratch/claude/tok-func-hbm-xdie-1021, OT_MEM 48.
# Output: OUTROOT/<variant>/{src.manifest.json,run/*.log}, OUTROOT/report.json (tools/tok_func_hbm_xdie_report.py).
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=${REPO:-$(git -C "$HERE" rev-parse --show-toplevel)}
G="git -C $REPO"
OUTROOT=$(realpath -m "${1:?OUTROOT}"); shift
BENCH_REV=${BENCH_REV:-$($G rev-parse HEAD)}; BENCH_REV=$($G rev-parse "$BENCH_REV")
DIE_REV=${DIE_REV:-1fe61477b}
DIE_CONTRACT=${DIE_CONTRACT:-/home/ubuntu/artifacts/hdie-d4/codex_hbm_r14_release_1021/planB/net/pre_relay_r14.json}
SUCC_BASE=${SUCC_BASE:-fed23480d}; SUCC_RL=${SUCC_RL:-d755fcd4c}; SUCC_LINK=${SUCC_LINK:-34f85027d}; SUCC_ISS=${SUCC_ISS:-8827e4001}
MAIN256_REV=${MAIN256_REV:-origin/main}; MAIN256_REV=$($G rev-parse "$MAIN256_REV")
RUN=${RUN:-fleet}; FLEET_STAGE=${FLEET_STAGE:-"ot-gold1 ot-gold2"}
FLEET_ROOT=${FLEET_ROOT:-/srv/opentallas-scratch/claude/tok-func-hbm-xdie-1021}; OT_MEM=${OT_MEM:-48}
VARIANTS=("$@")
if [ ${#VARIANTS[@]} -eq 0 ]; then
  VARIANTS=(r14_bound r14_lpars128 succ_lpars main_rows256 r14_coll_ar); [ -n "${XDIE_GEN_NETLIST:-}" ] && VARIANTS+=(gen)
fi
mkdir -p "$OUTROOT"
P=rtl/hbm_accel/generic/collective/p2p; X=rtl/hbm_accel/generic/collective/xdie
# the step vehicle file list (run_xdie_hbm_step5.sh; ROWS <= 128), paths relative to the source root
STEP_F="$X/tb_xdie_hbm_step.sv
 $P/ot_hfd_coll_q_hard_v8g.sv $P/ot_hfd_coll_q_hard_v5.sv $P/ot_hgi_coll_ctl_v5.sv $P/ot_hfd_coll_q3_static_host_v4.sv
 $P/ot_hfd_coll_q2_static_host_v4.sv $P/ot_hgi_coll_static_program_target.sv $P/ot_hfd_coll_q_static_v4.sv
 $P/ot_hgi_coll_static_issuer.sv $P/ot_hgi_coll_static_issuer_v5.sv $P/ot_hgi_coll_static_issuer_v6.sv $P/ot_hgi_coll_qslots.sv
 $P/ot_hgi_coll_qslots_capture_pin_v2.sv $P/ot_hgi_coll_pring_static.sv $P/ot_hgi_coll_pring_captured_static.sv
 $P/ot_hgi_coll_pring_static_state_capture.sv $P/ot_hgi_coll_slice_v7.sv $P/ot_hgi_coll_reduce_static.sv
 $P/ot_hgi_coll_argmax_static.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv $P/ot_hgi_coll_static_vmwrite.sv
 $P/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv $P/ot_hgi_coll_static_vmwrite_roots_v6.sv $P/ot_hgi_coll_static_link_capture.sv
 $P/ot_hgi_coll_static_capture_ctl.sv $P/ot_hgi_coll_static_pinreg_ctl.sv $P/ot_hgi_coll_static_pinreg_store.sv
 $P/ot_hgi_coll_static_seq_ctl.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static.sv
 rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_buffer.sv
 $P/ot_hgi_coll_ring_ag.sv $P/ot_hgi_coll_ring_ag_lane.sv $P/ot_hgi_coll_gq.sv $P/ot_hgi_coll_ring_b_stop.sv
 rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv
 physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
 rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static_xcap.sv
 rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
 rtl/hbm_accel/tu/ep_static_20261015/hfd_ep_static.sv rtl/hbm_accel/tu/ep_static_20261015/ot_hep_rx_store.sv
 rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_dec.sv
 rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_ddly.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv
 rtl/dsrom_sys/s81_link/ot_s81_kp4_dout.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
F256="$P/ot_hgi_coll_static_issuer_v7.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v"
# extra files of the AR-step vehicle (run_xdie_hbm_coll.sh)
BENCH_ONLY="$X/tb_xdie_hbm_step.sv $X/tb_xdie_hbm_coll.sv $X/run_xdie_hbm_coll.sh $X/tok_func_xdie_cases.sh tools/xdie_hbm_step_compile.py tools/xdie_hbm_coll_compile.py tools/tok_func_hbm_xdie_report.py tools/hbm_static/leaf_split_latency.py"
COLL_SPEC=results/arch/landed_parent_1018/collq/spec_n1s0_ars.json

blob() { $G rev-parse -q --verify "$1:$2" 2>/dev/null; }
put() {  # rev path dst-root  -> write file; echo blob
  local b; b=$(blob "$1" "$2") || return 1; mkdir -p "$(dirname "$3/$2")"; $G cat-file blob "$b" > "$3/$2"; echo "$b"
}
assemble() {  # variant -> $OUTROOT/$v/src + flist + defines + manifest
  local v=$1 S="$OUTROOT/$1/src" man="$OUTROOT/$1/src.manifest.tsv" f b ovr=$DIE_REV fl defs="" dut="" sp=""
  rm -rf "$S"; mkdir -p "$S"; : > "$man"
  fl="$STEP_F"
  case $v in
    r14_bound|r14_coll_ar) defs="+define+XDIE_AR_ITER=0 +define+XDIE_ROWS=64";;
    r14_lpars128) defs="+define+XDIE_AR_ITER=1 +define+XDIE_ROWS=128";;
    main_rows256) ovr=$MAIN256_REV; fl="$STEP_F $F256"; defs="+define+XDIE_AR_ITER=1 +define+XDIE_ROWS=256";;
    succ_lpars)
      sp=$($G show "$SUCC_RL:$COLL_SPEC" | python3 -c "import json,sys;s=json.load(sys.stdin);print(' '.join(s['sources']+s['child_sources']))")
      fl=$(for f in $STEP_F $sp; do [ "$f" = "$P/ot_hfd_coll_q_hard_v8g.sv" ] || echo "$f"; done | awk '!s[$0]++' | tr '\n' ' ')
      dut=ot_hfd_coll_n1s0_lpf_ars; defs="+define+XDIE_AR_ITER=1 +define+XDIE_ROWS=128 +define+XDIE_DUT_MODULE=$dut";;
    gen)
      local drop=${XDIE_GEN_DROP:-$P/ot_hfd_coll_q_hard_v8g.sv}
      fl=$(for f in $STEP_F; do case " $drop " in *" $f "*) ;; *) echo "$f";; esac; done | tr '\n' ' ')
      dut=${XDIE_GEN_TOP:?XDIE_GEN_TOP}; defs="+define+XDIE_AR_ITER=1 +define+XDIE_ROWS=${XDIE_GEN_ROWS:-128} +define+XDIE_DUT_MODULE=$dut"
      [ -n "${XDIE_GEN_LINK:-}" ] && defs="$defs +define+XDIE_LINK=$XDIE_GEN_LINK"
      [ -n "${XDIE_GEN_XPORTS+x}" ] && defs="$defs +define+XDIE_DUT_XPORTS=$XDIE_GEN_XPORTS"
      defs="$defs ${XDIE_GEN_DEFS:-}";;
  esac
  # 1) bench files (tb, compilers, run scripts) from BENCH_REV; 2) every other source from the variant's RTL rev
  #    (missing there -> BENCH_REV, flagged); the uop layout JSON travels with the RTL.
  for f in $BENCH_ONLY; do b=$(put "$BENCH_REV" "$f" "$S") || { echo "ASSEMBLE FAIL $v: $f not in BENCH_REV"; return 1; }; printf '%s\t%s\t%s\tbench\n' "$f" "$BENCH_REV" "$b" >> "$man"; done
  for f in $fl $P/static_uop_layout_v4.json; do
    case " $BENCH_ONLY " in *" $f "*) continue;; esac
    [ $v = succ_lpars ] && case " $sp " in *" $f "*) continue;; esac   # written by step 3
    if b=$(put "$ovr" "$f" "$S"); then printf '%s\t%s\t%s\tdie\n' "$f" "$ovr" "$b" >> "$man"
    elif b=$(put "$BENCH_REV" "$f" "$S"); then printf '%s\t%s\t%s\tbench-fallback\n' "$f" "$BENCH_REV" "$b" >> "$man"
    else echo "ASSEMBLE FAIL $v: $f in neither $ovr nor BENCH_REV"; return 1; fi
  done
  # include files (*.svh / *.vh) of every source directory, from the same rev as the sources
  local d inc
  for d in $(for f in $fl; do dirname "$f"; done | sort -u); do
    for inc in $($G ls-tree --name-only "$ovr" "$d/" 2>/dev/null | grep -E '\.(svh|vh)$'); do
      [ -e "$S/$inc" ] || { b=$(put "$ovr" "$inc" "$S") && printf '%s\t%s\t%s\tinclude\n' "$inc" "$ovr" "$b" >> "$man"; }
    done
  done
  if [ $v = succ_lpars ]; then  # 3) successor parent + hard leaves: SUCC_RL, 3-way merged with SUCC_LINK and SUCC_ISS onto SUCC_BASE
    local tmp; tmp=$(mktemp -d)
    for f in $sp; do
      local br bb bl bi; br=$(blob $SUCC_RL "$f"); bb=$(blob $SUCC_BASE "$f"); bl=$(blob $SUCC_LINK "$f"); bi=$(blob $SUCC_ISS "$f")
      [ -n "$br$bl$bi" ] || continue
      $G cat-file blob "${br:-${bl:-$bi}}" > "$tmp/cur"; [ -n "$bb" ] && $G cat-file blob "$bb" > "$tmp/base" || : > "$tmp/base"
      local how="succ:$SUCC_RL"; [ -n "$br" ] || how="succ:${bl:+$SUCC_LINK}${bl:-$SUCC_ISS}"
      for side in "$SUCC_LINK:$bl" "$SUCC_ISS:$bi"; do
        local r=${side%%:*} sb=${side#*:}
        [ -n "$sb" ] && [ "$sb" != "$bb" ] && [ "$sb" != "$br" ] || continue
        $G cat-file blob "$sb" > "$tmp/side"
        git merge-file -q "$tmp/cur" "$tmp/base" "$tmp/side" || { echo "ASSEMBLE FAIL $v: merge conflict $f ($r)"; rm -rf "$tmp"; return 1; }
        how="$how+merge:$r"
      done
      mkdir -p "$(dirname "$S/$f")"; cp "$tmp/cur" "$S/$f"
      printf '%s\t%s\t%s\tsuccessor\n' "$f" "$how" "$(git hash-object "$S/$f")" >> "$man"
    done
    rm -rf "$tmp"
  fi
  if [ $v = gen ]; then
    for f in ${XDIE_GEN_NETLIST:?} ${XDIE_GEN_CELLS:-}; do
      mkdir -p "$S/gen"; cp "$f" "$S/gen/"; printf '%s\t%s\t%s\tgen-netlist\n' "gen/$(basename "$f")" "$f" "$(git hash-object "$f")" >> "$man"
      fl="$fl gen/$(basename "$f")"
    done
  fi
  echo "$fl" | tr ' ' '\n' | grep -v '^$' | grep -v "^$X/tb_xdie_hbm_step.sv$" > "$S/xdie_flist.txt"
  echo "$defs" > "$S/xdie_defines.txt"
  [ -n "${XDIE_CASES:-}" ] && echo "$XDIE_CASES" > "$S/xdie_cases.txt"   # optional case subset (name:swd:kind:frames ...)
  python3 - "$OUTROOT/$v" "$v" "$DIE_REV" "$DIE_CONTRACT" "$BENCH_REV" "$ovr" "$dut" <<'EOF'
import json, sys, pathlib, hashlib
o, v, die_rev, contract, bench, ovr, dut = sys.argv[1:8]
rows = [l.rstrip('\n').split('\t') for l in open(f'{o}/src.manifest.tsv')]
m = {'variant': v, 'bench_rev': bench, 'rtl_rev': ovr, 'die_rev': die_rev, 'dut_module': dut or 'ot_hfd_coll_q2_hard_v8g',
     'defines': open(f'{o}/src/xdie_defines.txt').read().split(),
     'files': [{'path': r[0], 'rev': r[1], 'blob': r[2], 'role': r[3]} for r in rows]}
try:
    c = json.load(open(contract)); ins = c['instances']
    it = ins.items() if isinstance(ins, dict) else [(i.get('name'), i) for i in ins]
    m['die_contract'] = {'path': contract, 'sha256': hashlib.sha256(open(contract, 'rb').read()).hexdigest(),
        'coll_instances': {n: {'master': i['master'], 'source': i['source'], 'params': i.get('params', {})}
                           for n, i in it if n and n.startswith('hb_coll_')}}
except Exception as e:
    m['die_contract'] = {'path': contract, 'error': str(e)}
json.dump(m, open(f'{o}/src.manifest.json', 'w'), indent=1)
EOF
  echo "ASSEMBLED $v: $(wc -l < "$man") files ($(grep -c 'bench-fallback' "$man") bench-fallback) -> $S"
}

launch() {  # variant -> run (fleet or local), logs in $OUTROOT/$v/run
  local v=$1 S="$OUTROOT/$1/src" R="$OUTROOT/$1/run" rid; mkdir -p "$R"
  [ "$RUN" = assemble ] && return 0
  if [ "$RUN" = local ]; then
    bash "$S/$X/tok_func_xdie_cases.sh" "$S" "$R" "$v" > "$R/client.log" 2>&1; return
  fi
  rid=$(basename "$OUTROOT"); local D="$FLEET_ROOT/$rid/$v"
  for h in $FLEET_STAGE; do
    ssh -o ControlPath=none "$h" "mkdir -p $D" && rsync -a --delete -e 'ssh -o ControlPath=none' "$S/" "$h:$D/src/" || echo "stage to $h failed"
  done
  ot-run --mem "$OT_MEM" --threads 16 --dir "$D" -- bash src/$X/tok_func_xdie_cases.sh src run "$v" > "$R/client.log" 2>&1
  local rc=$?; local host; host=$(grep -o 'RAN on [^:]*' "$R/client.log" | tail -1 | cut -d' ' -f3)
  [ -n "$host" ] && rsync -a -e 'ssh -o ControlPath=none' --include='*/' --include='*.log' --include='*.sha256' --include='*.version' \
      --include='*.json' --exclude='*' "$host:$D/run/" "$R/" ; echo "$host" > "$R/host.txt"
  return $rc
}

pids=()
for v in "${VARIANTS[@]}"; do
  assemble "$v" || { echo "{\"variant\":\"$v\",\"assemble\":\"FAIL\"}" > "$OUTROOT/$v.assemble_fail.json"; continue; }
  launch "$v" & pids+=($!)
  echo "LAUNCHED $v pid $!"
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
$G show "$BENCH_REV:results/rtl/xdie_hbm_1019/record.json" > "$OUTROOT/ref_record.json"
$G show "$BENCH_REV:tools/tok_func_hbm_xdie_report.py" > "$OUTROOT/tok_func_hbm_xdie_report.py"
python3 "$OUTROOT/tok_func_hbm_xdie_report.py" "$OUTROOT" --record "$OUTROOT/ref_record.json"

exit "$rc"
