#!/bin/bash
# KV-KITS-19 (2026-10-29): ot_qwen_tp8_pv_join_t R0 + fR180 kits with OUTPUT_LOAD_LOCAL=1 (main b83fce6ef, per-16-bit
# kept lookahead load_q) on top of the KV-KITS-16 one-hot select kits (cc87cab339).
# Root cause (CHECKED, actual routed fR180 13576235cae1 ODB/SPEF probe: all 30 TT setup violators and all 70 endpoints
# below +40 ps are u_leaf.y_hold[*]/y[*] from jrun/jage -> J_OUT NOR decode -> fanout 46/64 buffer cascade; R0
# 82f5e556ae09 worst y_hold[426] -47.98 same cone). Fix: load_q <= nrun && nage==J_OUT, one kept copy per 16 bits
# (16 y_hold + 16 y mux loads), 0 cycles (bench results/kv_kits_19_1029/pvj/pvj_load_eq.sh).
# Changes vs base kit, nothing else:
#   (1) kit leaf module text == release ot_qwen_tp8_pv_join_t (this branch) with the __leaf name (fail closed); kit top
#       instance passes .OUTPUT_LOAD_LOCAL(1);
#   (2) entry-trunk census + the 32 load_q flops (PREDICTED names, like KV-KITS-16 sa/sb), core_infra re-installed;
#   (3) freeze kit_hash / provenance / regen record.  The base kits are already --cts-setup-only / --two-mode-grt.
# usage (intel2, clean checkout of this branch): regen_pvj_load.sh OUTDIR
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
OLD=${OLD:-/srv/opentallas-scratch2/claude/codex-kv-kits-1028/pvj}
O=${1:?OUTDIR}
REL=$REPO/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv
for V in ot_qwen_tp8_pv_join_t__172.8x172.8 ot_qwen_tp8_pv_join_t__172.8x172.8_fR180; do
  K=$OLD/$V; N=$O/$V
  rm -rf "$N"; mkdir -p "$N"
  rsync -a --exclude run --exclude signoff --exclude views --exclude lec --exclude __pycache__ \
    --exclude "autopilot_chain_*" --exclude "preflight_autopilot_*" --exclude preflight.json \
    --exclude 1_synth_odb.v --exclude "synth_odb_v.*" --exclude "face_guard*.json" --exclude "face_guard*.log" \
    --exclude rtl_lint.json --exclude rtl_lint.log --exclude rtl_lint.ys --exclude "selrange.*" \
    --exclude dont_use_check.json --exclude adder_map_dontuse.json --exclude sdc_lint.log --exclude orfs_hold_mm.log \
    --exclude lec_run.log --exclude run_place.log --exclude run_route.log --exclude run_finish.log --exclude signoff.log \
    --exclude pin_audit.json "$K/" "$N/"
  python3 - "$REL" "$N/rtl/ot_qwen_tp8_pv_wide_pair__leaf.sv" "$N/rtl/ot_qwen_tp8_pv_join_t.sv" <<"PY"
import re, sys
from pathlib import Path
rel, leaf, top = (Path(a) for a in sys.argv[1:])
def mod(text, name):
    m = re.search(r"^module %s #.*?^endmodule\n" % re.escape(name), text, re.S | re.M)
    assert m, name
    return m
r = mod(rel.read_text(), "ot_qwen_tp8_pv_join_t").group(0).replace("module ot_qwen_tp8_pv_join_t #", "module ot_qwen_tp8_pv_join_t__leaf #", 1)
s = leaf.read_text(); m = mod(s, "ot_qwen_tp8_pv_join_t__leaf")
leaf.write_text(s[:m.start()] + r + s[m.end():])
t = top.read_text(); old = "ot_qwen_tp8_pv_join_t__leaf #(.J_LAT(7), .MUT(0), .RESET_PIN(1)) u_leaf"
assert t.count(old) == 1, t.count(old)
top.write_text(t.replace(old, "ot_qwen_tp8_pv_join_t__leaf #(.J_LAT(7), .MUT(0), .RESET_PIN(1), .OUTPUT_LOAD_LOCAL(1)) u_leaf"))
print("RTL", leaf.name, "leaf module = release text;", top.name, "OUTPUT_LOAD_LOCAL(1)")
PY
  cmp <(sed -n "/^module ot_qwen_tp8_pv_join_t #/,/^endmodule/p" "$REL") \
      <(sed -n "/^module ot_qwen_tp8_pv_join_t__leaf #/,/^endmodule/p" "$N/rtl/ot_qwen_tp8_pv_wide_pair__leaf.sv" | sed "s/module ot_qwen_tp8_pv_join_t__leaf/module ot_qwen_tp8_pv_join_t/")
  python3 -I "$REPO/tools/die_plan/signoff.py" bundle "$N"
  python3 - "$REPO" "$N" <<"PY"
import json, sys
from pathlib import Path
repo, kd = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(repo / "physical/die_plan/qwen_kvsys/cores/harden"), str(repo / "tools/die_plan")]
import gen_core_kit_kv as GK
import core_infra as CI
import lec as LEC
cen = json.loads((kd / "pv_clock_census.json").read_text())
old_n = len(cen["sinks"])
add = [f"u_leaf.g_output_load_local.g_word\\[{q}\\].load_q$_DFF_PN0_/CLK" for q in range(32)]
assert not set(add) & set(cen["sinks"])
cen["sinks"] = cen["sinks"] + add
cen["kv_kits_19"] = dict(added_predicted=len(add), rule="OUTPUT_LOAD_LOCAL=1 load_q per 16 bits, async reset like js; "
                         "PREDICTED names: re-derive from 1_synth_odb.v before CTS")
(kd / "pv_clock_census.json").write_text(json.dumps(cen, indent=1) + "\n")
sl = json.loads((kd / "pv_trunk_slice.json").read_text())
lf = sl["core_tree"]["leaves"][0]
lf["sinks"], lf["domain_sinks"] = cen["sinks"], len(cen["sinks"])
CI.install(kd, sl)
(kd / "pv_trunk_slice.json").write_text(json.dumps(sl, indent=1) + "\n")
t = (kd / "pv_trunk_install.tcl").read_text().replace(f"sinks{old_n}", "sinks%d" % len(cen["sinks"]))
(kd / "pv_trunk_install.tcl").write_text(t)
fz = json.loads((kd / "freeze.json").read_text())
prov = LEC._repo_provenance(repo)
prev = fz.get("regen")
fz.update(kit_hash=GK.kit_hash(kd), source_commit=prov.get("commit"),
          regen=dict(lane="KV-KITS-19", base_kit=f"codex-kv-kits-1028/pvj/{kd.name}", base_source_commit=fz.get("source_commit"),
                     base_regen=prev, rtl_delta="pv_join OUTPUT_LOAD_LOCAL=1 (main b83fce6ef) on KV-KITS-16 sa/sb (0 cycles)",
                     census_added_predicted=len(add)))
(kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
LEC.write_kit_provenance(kd, repo, provenance=prov)
print("REGEN", kd.name, "kit_hash", fz["kit_hash"], "sinks", len(cen["sinks"]), "src", prov.get("commit"))
PY
done
