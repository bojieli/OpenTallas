#!/usr/bin/env python3
"""QC-TYPES-6 11-07: QC plan event qc52t = plan_qc52n + clock.tap_pair_affinity {} (defaults) on the listed types.

COORD 11-07 (tap-pair ASK 21:42 ruled READY BY INTENT): ONE QC plan event that turns tap_pair_affinity on for the
HOLD-STRUCTURAL rows and the hc/stm SETUP-AT-GRT rows of lanes/HELD-FAIL-CLASSES.md, then one batch relaunch.

The event adds only clock.tap_pair_affinity = {} to each listed type (gen_phys.tap_pair_affinity_exports defaults:
radius = tap radius, group 64, merge 128, pair 60 um, depth 2).  Every other type and every top-level key stays
byte-identical; outlines, pins, hard cores, budgets and the RTL are untouched, so no counted design can change.

    python3 tools/die_plan/qc_tap_pair_event.py BASE_PLAN OUT_PLAN EVENT_JSON

11-07 23:1x: the QC kit wave builds from plan_qc53_candidate_v4.json (kit_wave.json qwen_compute.plan), not from the
count plan plan_qc52n, so the same event is also written as plan_qc53v4t.json (qc53t_tap_pair_event.json).
"""
import hashlib, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

HOLD_STRUCTURAL = [
    "cbf_q00_s2", "cbn_q00__cld7bf7197", "cbn_q00__cldbcda913", "coll_ft__cl78c7b300", "coll_ft__cla4a25d77",
    "coll_s", "sle_hc1__cl22c1ff36", "sle_hc1__cl7d360508", "sle_su_c", "sle_su_l1__clc6d66f5b",
    "slw_st_a_v2__cl9f076a5c", "slw_su_c__cl92142dac"]
SETUP_HC_STM = [
    "sle_hc0__cl929603c0__cl38badc56", "sle_hc1__cl7d360508", "sle_hc2__cl9c4c4509__cl3edce1b8",
    "sle_hc2__cl9c4c4509__clf60c5152", "sle_hc2__clcc5e3e61", "sle_stm_v1__clbe630b9c", "slw_hc0__cl1bc59e1c",
    "slw_hc1__cl3449ea95", "slw_hc1__cl68f9248e__cl144ee7b3", "slw_hc1__cl68f9248e__cle683a076",
    "slw_hc2__cla3497502__cl16607c7a", "slw_hc2__cla3497502__cldc737267", "slw_stm_v1__cle34a73c3",
    "slw_stm_v2__cl1ca9c415"]
TYPES = sorted(set(HOLD_STRUCTURAL) | set(SETUP_HC_STM))


def dumps(p):
    # the QC plan-of-record style: one line, compact separators, trailing newline
    return json.dumps(p, separators=(",", ":")) + "\n"


def apply(P, types=TYPES):
    """-> (new plan, {type: config.mk export lines}); ValueError when a type is missing, has no clock or already has the key"""
    Q = json.loads(json.dumps(P))
    T = Q["partition_types"]
    exports = {}
    for tn in types:
        if tn not in T:
            raise ValueError("type %s not in the plan" % tn)
        ck = T[tn].get("clock")
        if not isinstance(ck, dict):
            raise ValueError("type %s has no clock object" % tn)
        if "tap_pair_affinity" in ck:
            raise ValueError("type %s already has clock.tap_pair_affinity" % tn)
        ck["tap_pair_affinity"] = {}
        exports[tn] = gen_phys.tap_pair_affinity_exports(T[tn])
    for k in P:
        if k != "partition_types" and dumps(P[k]) != dumps(Q[k]):
            raise AssertionError("top-level key %s changed" % k)
    for tn, v in P["partition_types"].items():
        w = json.loads(json.dumps(Q["partition_types"][tn]))
        if tn in types:
            del w["clock"]["tap_pair_affinity"]
        if dumps(v) != dumps(w):
            raise AssertionError("type %s changed beyond the event key" % tn)
    return Q, exports


def main(argv):
    base, out, ev = (pathlib.Path(a) for a in argv[1:4])
    raw = base.read_bytes()
    P = json.loads(raw)
    # keep the base file's own style: compact (plan_qc52n) or json.dumps default (plan_qc53_candidate_v4, the wave plan)
    style = next((f for f in (dumps, lambda p: json.dumps(p) + "\n") if f(P).encode() == raw), None)
    if style is None:
        raise SystemExit("base plan %s is in neither plan-of-record style" % base)
    Q, exports = apply(P, TYPES)
    data = style(Q).encode()
    out.write_bytes(data)
    rec = {
        "schema": "opentallas.qc_por_event.v1",
        "event": "QC tap-pair affinity on the HOLD-STRUCTURAL + hc/stm SETUP-AT-GRT types (COORD 11-07, QC-TYPES-6 ASK 21:42 READY BY INTENT)",
        "base_plan": base.name, "base_plan_sha256": hashlib.sha256(raw).hexdigest(),
        "plan_output": out.name, "plan_output_sha256": hashlib.sha256(data).hexdigest(),
        "change": "partition_types.<type>.clock.tap_pair_affinity = {} (defaults)",
        "flow": "tools/die_plan/tap_pair_affinity.tcl + tap_pair_plan.tcl (TAP-PAIR v3 e756f627c0; v4 SHIFT 797fdbf8a43)",
        "types_hold_structural": HOLD_STRUCTURAL, "types_setup_hc_stm": SETUP_HC_STM, "types": TYPES,
        "exports": exports, "data_cycles": 0, "pin_cycles": 0,
        "preservation": "every other partition type and every top-level key byte-identical (checked by apply())",
    }
    ev.write_text(json.dumps(rec, indent=1) + "\n")
    print("%d types; %s -> %s %s" % (len(TYPES), rec["base_plan_sha256"][:12], out.name, rec["plan_output_sha256"][:12]))


if __name__ == "__main__":
    main(sys.argv)
