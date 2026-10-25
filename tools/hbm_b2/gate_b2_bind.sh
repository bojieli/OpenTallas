#!/usr/bin/env bash
# HBM-BIND (2026-10-24) B2 native-bind gate: every new / parameterised RTL item of the 8-SM B2 die (NW + NE + die
# level of r18h5) with its bench + mutants, then the B2 die top (tools/hbm_b2/b2_top.py over the wiring delta) and the
# strict port-bind check.  Run from a clean checkout of the branch (repo root), on a fleet host:
#   tools/hbm_b2/gate_b2_bind.sh OUT BUNDLE [BASE]
#     BUNDLE = the exact r18h5 source bundle (files.f, rtl/, physical/; die.v) -- needed for the port-bind step
#     BASE   = the pre-change source commit (default d13ff7c78 = origin/main at branch point): the unchanged originals
#              the default-parameter bit-exactness benches compare against.
# Prints one line per item and a final "B2_BIND_GATE PASS|FAIL" line; exit 0 iff PASS.
# The port-bind step reports, but does not fail on, the as-built r18h5 baseline classes (identical on the 16-SM die):
# ot_smh_static_front children without RTL, the ot_hbm3e_phy_rc_e8p5 behavioural box, strap INPUT_TIED.
set -uo pipefail
OUT=$(realpath -m "${1:?out}"); BUNDLE=$(realpath "${2:?bundle}"); BASE=${3:-d13ff7c78}
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT"; mkdir -p "$OUT"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
fail=0; res(){ echo "$1 $2"; [ "$2" = PASS ] || fail=1; }
J=()
# ---- 1 in-band host endpoint (hfd_ep_static_vc2 + hfd_ep_host_vc): MUT 0 PASS, MUT 1..9 FAIL (parallel)
E=rtl/hbm_accel/tu/ep_static_20261015
for m in 0 1 2 3 4 5 6 7 8 9; do bash $E/run_hfd_ep_static_vc2_bench.sh "$ROOT" "$OUT/vc2" $m > "$OUT/vc2_m$m.log" 2>&1 & J+=($!); done
# ---- 2 two-stop VM ring
mkdir -p "$OUT/vmref"
for f in ot_vms_rstop_static.sv ot_vms_hub_static.sv hfd_hgi_vms_static_glue.sv; do
  git show $BASE:rtl/hbm_accel/generic/vm/static/$f > "$OUT/vmref/$f"; done
bash rtl/hbm_accel/generic/vm/static/run_vms_ring2_static.sh "$OUT/vm" "$OUT/vmref" > "$OUT/vm.log" 2>&1 & J+=($!)
# ---- 3 vm_status4 NQ 2
git show $BASE:rtl/hbm_accel/generic/vm/static/ot_vms_status4_static.sv | sed 's/\bot_vms_status4_static\b/ot_vms_status4_ref/; s/OT_VMS_STATUS_MUT/OT_VMS_STATUS_MUT_NOT_IN_REF/' > "$OUT/status4_ref.sv"
# (the reference must not see the bench mutant define, or the NQ 4 mutant compares equal to a mutated reference)
bash rtl/hbm_accel/generic/vm/static/run_vms_status_nq.sh "$OUT/st" "$OUT/status4_ref.sv" > "$OUT/status.log" 2>&1 & J+=($!)
# ---- 4 SU scalar tree NLEG + SU programme root PARTS
bash rtl/hbm_accel/generic/adapters/static_su/top/run_stree_nq.sh "$OUT/stree" $BASE > "$OUT/stree.log" 2>&1 & J+=($!)
bash rtl/hbm_accel/generic/adapters/static_su/programme/run_pgroot_nq.sh "$OUT/pg" $BASE > "$OUT/pg.log" 2>&1 & J+=($!)
bash rtl/hbm_accel/generic/adapters/static_su/top/run_qcore_w2.sh "$OUT/qcw2" > "$OUT/qcw2.log" 2>&1 & J+=($!)
# ---- (IDX / argmax and HC root gates are appended here when their RTL lands; see EXTRA_GATES)
for g in ${EXTRA_GATES:-}; do bash $g "$OUT/$(basename $g .sh)" $BASE > "$OUT/$(basename $g .sh).log" 2>&1 & J+=($!); done
for j in "${J[@]}"; do wait $j; done
v=PASS; grep -q "^TB_HFD_EP_STATIC_VC2 MUT=0 .* PASS$" "$OUT/vc2/run_m0.log" 2>/dev/null || v=FAIL
for m in 1 2 3 4 5 6 7 8 9; do grep -q "^TB_HFD_EP_STATIC_VC2 MUT=$m .* FAIL$" "$OUT/vc2/run_m$m.log" 2>/dev/null || v=FAIL; done
res "1 hfd_ep_static_vc2 (MUT0 PASS, MUT1..9 FAIL)" $v
grep -q "VMS_RING2_GATE PASS" "$OUT/vm.log" && res "2 VM ring2" PASS || res "2 VM ring2" FAIL
grep -q "VMS_STATUS_NQ_GATE PASS" "$OUT/status.log" && res "3 vm_status4 NQ" PASS || res "3 vm_status4 NQ" FAIL
grep -q "STREE_NQ_GATE PASS" "$OUT/stree.log" && res "4a SU stree NLEG" PASS || res "4a SU stree NLEG" FAIL
grep -q "SU_PGROOT_NQ_GATE PASS" "$OUT/pg.log" && res "4b SU programme PARTS" PASS || res "4b SU programme PARTS" FAIL
grep -q "QCORE_W2_GATE PASS" "$OUT/qcw2.log" && res "4c SU core 2-writer" PASS || res "4c SU core 2-writer" FAIL
for g in ${EXTRA_GATES:-}; do b=$(basename $g .sh); grep -q "GATE PASS" "$OUT/$b.log" && res "x $b" PASS || res "x $b" FAIL; done
# ---- 5 B2 die top + port bind
T="$OUT/top"; mkdir -p "$T/ovl"
git diff --name-only $BASE HEAD -- rtl | grep -Ev '/(tb_|run_)' | while read f; do [ -f "$f" ] && mkdir -p "$T/ovl/$(dirname $f)" && cp "$f" "$T/ovl/$f"; done
X=""; for f in $(find "$T/ovl" -name '*.sv' -o -name '*.v' | sort); do X="$X --rtl-file $f --prefer $f"; done
while read rel; do if [ -f "$T/ovl/$rel" ]; then echo "$T/ovl/$rel"; else echo "$BUNDLE/$rel"; fi; done < "$BUNDLE/files.f" > "$T/files_abs.f"
python3 tools/hbm_b2/make_wiring.py --die physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz \
  --asbuilt physical/die_plan/hbm/bind/asbuilt.json --out "$T/wiring.json" > "$T/mw.log" 2>&1 || { cat "$T/mw.log"; fail=1; }
cmp -s <(python3 -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1])),sort_keys=True))" "$T/wiring.json") \
       <(python3 -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1])),sort_keys=True))" results/arch/hbm_arch_1024/b2_bind_wiring.json) \
  && res "5a wiring delta reproduces the committed b2_bind_wiring.json" PASS || res "5a wiring delta reproduces the committed b2_bind_wiring.json" FAIL
python3 tools/hbm_b2/b2_top.py --die physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz --asbuilt physical/die_plan/hbm/bind/asbuilt.json \
  --delta "$T/wiring.json" --out "$T/outw" > "$T/b2.log" 2>&1 && res "5b b2_top (no CUT_UNRESOLVED / UNDRIVEN)" PASS || res "5b b2_top (no CUT_UNRESOLVED / UNDRIVEN)" FAIL
python3 tools/die_port_bind.py "$T/outw/die_b2.v" --top hbm_b2_die --rtl-root "$BUNDLE/rtl" --rtl-root "$BUNDLE/physical" \
  -f "$T/files_abs.f" $X --out "$T/pb.json" > "$T/pb.log" 2>&1
# baseline classes: a master whose ONLY fail class is INPUT_TIED (die straps), the PHY behavioural box, smh_fc children
grep -E '^FAIL' "$T/pb.log" | grep -Ev '^FAIL \S+ +x[0-9]+ +INPUT_TIED |ot_hbm3e_phy_rc_e8p5 .*STUB|child ot_hbm_accel_smh_fc_' > "$T/pb_new.txt"
tail -1 "$T/pb.log" | cut -c1-400
[ ! -s "$T/pb_new.txt" ] && res "5c port-bind: no FAIL beyond the r18h5 baseline classes" PASS || { cat "$T/pb_new.txt"; res "5c port-bind: no FAIL beyond the r18h5 baseline classes" FAIL; }
[ $fail = 0 ] && echo "B2_BIND_GATE PASS" || { echo "B2_BIND_GATE FAIL"; exit 1; }
