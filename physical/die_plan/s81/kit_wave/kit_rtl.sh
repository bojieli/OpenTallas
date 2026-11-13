#!/bin/bash
# Export the exact current bound S81 partition for a kit-wave item.
# env TYPE/OUT/PLAN (kit_wave.py script mode, cwd = wave source checkout) -> $OUT/kit_rtl.f + kit_rtl.json (defines).
# Class types whose instances differ in parameters are kitted only when every differing parameter is an image
# selector of black-box hard cores (image_params.py image proves it; the instance is named, never implicit).
# Never replace an unsigned hard core by a shell.
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be a fresh kit RTL directory}" "${PLAN:?PLAN must name the plan}"
BIND_OUT=${S81_BIND_OUT:-/srv/opentallas-scratch2/claude/die-s81-34/rebind/out}
ASBUILT=${S81_ASBUILT:-physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
python3 -I - "$BIND_OUT" "$PLAN" "$TYPE" <<'PY'
import json, sys
from pathlib import Path
b, plan, typ = sys.argv[1:]
r = json.loads((Path(b) / "bind_report.json").read_text())
e = r["errors"]
assert (len(e) if isinstance(e, list) else e) == 0, "S81_KIT_RTL: strict bind errors"
p = json.loads(Path(plan).read_text())
assert typ in p["partition_types"], "S81_KIT_RTL: unknown plan type"
assert typ in r["types"], "S81_KIT_RTL: type absent from strict bind"
PY
mkdir -p "$OUT"
# bind.f of the strict bind may name a removed worktree: read it through a private overlay (kit-rtl bind.f preference)
OV="${OUT%/}_bindov"
python3 -I "$HERE/image_params.py" overlay "$BIND_OUT" "$PWD" "$OV" > "$OUT/bind_overlay.json"
python3 -I "$HERE/image_params.py" image "$OV" "$PLAN" "$TYPE" > "$OUT/image_params.json"
INST=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["instance"] or "")' "$OUT/image_params.json")
python3 -I tools/die_plan/bind.py kit-rtl "$PLAN" --out "$OV" --asbuilt "$ASBUILT" --type "$TYPE" --kit "$OUT" \
    ${INST:+--instance "$INST"}
# COORD 07:34 (5), S81 svc plan event (delta_svc_band_1104): every svc type closes its native memories to the MEM v2
# macros the plan places (T7 class port + idx fit, tools/die_plan/s81_svc_memory_closure.py); other types do not apply.
# HARD-S81-SVC-1 11-13: the step lives in kit_rtl_post.sh, which kit_rtl mode "bind" runs too (kit_wave.py
# kit_rtl_post_cmd), so a change of kit_rtl mode can no longer drop it.
TYPE="$TYPE" OUT="$OUT" PLAN="$PLAN" bash "$HERE/kit_rtl_post.sh"
# DIE-S81-85 11-10 (KW43-111, class J3): the J3 leaves xs4/rstopt_xo follow the wave source when the frozen as-built
# base still has the pre-fix bytes (KEEP FAIL g_hq[*].h folded constants); kits without them stay byte-identical.
python3 -I "$HERE/j3_leaf_follow.py" "$OUT"
python3 -I - "$OUT" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
f = [Path(x) for x in (p / "kit_rtl.f").read_text().splitlines() if x.strip()]
assert f and all(x.is_file() for x in f), "S81_KIT_RTL: missing source closure"
r = json.loads((p / "kit_rtl.json").read_text())
# DIE-S81-36 / COORD ruling 10-30 (seqhost ASK option b): declared constant spare outputs, exact match only.  seqhost__t1
# unit_o4: lane unit__seqhost__gunit is 267 on all 14 plan records; the as-built seqhost drives 265 bits and gunit reads
# 265, so the 2 top bits stay registered constants (pins unchanged).  Any other / different spare set still fails.
# COORD 11-01 08:2x class ruling (12.28b): spare plan output bits that the kit wrapper drives as literal constants are a
# declared COORD exception as a CLASS (svc_lo/svc_hi dsdv_svc_rs and any later type).  Proof per row, exact: the
# generated wrapper (first kit_rtl.f source) holds exactly one `assign <port>[..] = <bits>'d0;` (or whole-bus) line for
# that port with that bit count.  A spare row without that literal-constant driver still fails.
import re
DECLARED_SPARE_OUT = {"seqhost__t1": [{"port": "unit_o4", "bits": 2}]}
spare = sorted((x["port"], x["bits"]) for x in r.get("spare_out_bits") or [])
if spare != sorted((x["port"], x["bits"]) for x in DECLARED_SPARE_OUT.get(r["plan_type"], [])):
    wrap = f[0].read_text()
    proof = []
    for port, bits in spare:
        hits = re.findall(r"^\s*assign\s+" + re.escape(port) + r"(?:\[[^\]]+\])?\s*=\s*(\d+)'d0\s*;", wrap, re.M)
        assert hits == [str(bits)], \
            f"S81_KIT_RTL: constant spare outputs require a plan fix (or a COORD-declared exception): {port} {bits} not a literal constant"
        proof.append(dict(port=port, bits=bits, driver=f"{bits}'d0"))
    r["spare_out_exception"] = dict(rule="COORD 11-01 class exception (12.28b): constant spare plan output bits", rows=proof)
im = json.loads((p / "image_params.json").read_text())
r["s81_image_params"] = im
(p / "kit_rtl.json").write_text(json.dumps(r, indent=1))
print("S81_KIT_RTL PASS", r["plan_type"], len(f), "sources", "instance", im["instance"] or "-",
      "image_params", len(im["image_params"]), "of", im["instances"], "instances")
PY
