#!/usr/bin/env python3
"""DIE-QC-63/RED 11-02: the QC RED source/parent event as an explicit plan event (plan_qc52 delta).

OWNER 11-02: "ADOPT the QC RED source event as an explicit plan event, gated on equivalence/simulation PASS; reach
problems fixed with added pipeline stages; tok/s loss accepted".  The su_c parent (433,951 cells, over the 400k
OpenROAD cap) loses the reducer: the as-built leaf u_red (qfd_dv_s5_red2_leaf, flattened glue) becomes the plan variant
qfd_dv_s5_red2p1_leaf (asbuilt substitute_inst, same ports; rtl/qwen_dv/s5/qfd_dv_s5_red2p1_leaf.sv), whose u_core =
qfd_dv_s5_red2_leaf #(HARD_PINREG 1) is placed as the hard core u_red_u_core (276.48 x 276.48, R0) at ORIGIN, the
standalone RED child kit (codex/qc-suc-1101 54f817f966b H1 source; red_grt kit pins.json byte copy as pins_file).
Reach (tools: results/qc_die63_red_1102/reach.py): the core's E pins take lane l0 (E-face stations), its W pins lane l1
(W-face stations, 1226 um apart): worst face->core 1164 um -> IN_STAGES 2 (<= 388 um/hop); core S pins -> the N-face
x_ctl_o / x_sc_o stations: lead <= 1101 um -> OUT_STAGES 3 (<= 367 um/hop); residual: the one red_* net fans out to the two
stations 900 um apart, so its last branch is ~485 um from one driver (1 repeater per branch, <= 450 um rule).
Latency to the model: red_we/red_addr/red_data +5 cycles (IN 2 + OUT 3), red_fault +2, rd_v +0 (exact), busy covers
the original busy and stretches by <= 5 (su8 idle later by <= 5 cycles, never earlier); equivalence bench
results/qc_die63_red_1102/tb_red_event.sv vs the unmodified as-built leaf.
Per su_c type (sle_su_c, slw_su_c__cl92142dac, slw_su_c__cl19bb38ef): contents u_red note + event, contents
u_red_u_core (reuse, reference), hard_cores u_red_u_core, clock.taps core tap u_red_u_core.ck (early core taps; red_grt
post-CTS pin-flop mean TT 268.77 / FF 211.91 ps, placement RC - re-measure on the signed view).  The reset tree /
landing collector are re-derived with the current tools (as delta_ttctlm_1101.py) only if the change moves them; the
paired clock-landing sidecar entries are updated the same way.
usage: delta_red_1102.py PLAN_IN PLAN_OUT [REPORT.json [SIDECAR_IN SIDECAR_OUT [ASBUILT_IN ASBUILT_OUT]]]"""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402

TYPES = ["sle_su_c", "slw_su_c__cl92142dac", "slw_su_c__cl19bb38ef"]
INST = "u_red_u_core"
MOD = "qfd_dv_s5_red2_leaf"
VARIANT = "qfd_dv_s5_red2p1_leaf"
ORIGIN = [743.04, 561.6]   # DIE-QC-64/RED: x 648 -> 743.04 clears the cws2 ft station column (x 637-730; G0C)
OUTLINE = [276.48, 276.48]
PINS = "cores/su/qfd_dv_s5_red2_leaf_pins.json"
CK_PIN = (138.252, 138.24)
TOFF = [0.012, 0.012]
EVENT = dict(id="DIE-QC-63/RED-1102", variant=VARIANT, core=INST, core_module=MOD, core_params=dict(HARD_PINREG=1),
             in_stages=2, out_stages=3,
             latency_cycles=dict(red_we=5, red_addr=5, red_data=5, fault=2, rd_v=0, busy_stretch_max=5),
             residual="red_* fanout to x_ctl_o (x~100) and x_sc_o (x~1000) N-face stations: last branch ~485 um "
                      "from one driver (> 405 plan hop, 1 repeater/branch <= 450 um)",
             equivalence="results/qc_die63_red_1102/tb_red_event.sv (iverilog, as-built leaf vs variant)")
SUB = dict(inst=r"(?:.*\.)?u_sub\.u_red", module=VARIANT,
           reason="DIE-QC-63/RED 11-02 OWNER-adopted RED source/parent event: relay glue (IN 2 / OUT 3) + exact rd_v + "
                  "covering busy around the H1 hard core u_core (plan hard_cores u_red_u_core); sim-equivalent to the "
                  "as-built leaf with red_* +5, fault +2 (results/qc_die63_red_1102)")


def lc_of(P, T):
    return P["partition_types"][T]["clock"]["landing_contract"]


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    if all(any(h["inst"] == INST for h in P0["partition_types"][T]["hard_cores"]) for T in TYPES):
        open(pout, "w").write(text)
        print("already applied")
        return
    P = copy.deepcopy(P0)
    rep = dict(event=EVENT, types={})
    trees0 = {T: RT.for_type(S.Plan(P0, pin), T) for T in TYPES}
    for T in TYPES:
        t = P["partition_types"][T]
        assert not any(h["inst"] == INST for h in t["hard_cores"]), T
        red = [c for c in t["contents"] if c["inst"] == "u_red"]
        assert len(red) == 1, T
        red[0]["note"] = red[0]["note"] + f" | {EVENT['id']}: as-built leaf -> plan variant {VARIANT} (relay glue, " \
            f"flattened); its u_core is the hard core {INST}"
        t["contents"].append(dict(inst=INST, module=MOD, status="reuse", outline_um=OUTLINE, origin_um=ORIGIN,
                                  note=f"{EVENT['id']}: RED reducer hard core (HARD_PINREG 1, 352 private pin registers)"))
        t["hard_cores"].append(dict(
            inst=INST, module=MOD, origin_um=ORIGIN, outline_um=OUTLINE, orient="R0", track_offset_um=TOFF,
            pins_file=PINS,
            note=f"{EVENT['id']}: RED child kit view qfd_dv_s5_red2_leaf #(HARD_PINREG 1) (codex/qc-suc-1101 54f817f966b; "
                 "kit epyc2 /srv/opentallas-scratch2/claude/codex-qc-sc-red-1101/red_grt pins.json byte copy); UNSIGNED: "
                 "signed view (lef/lib) binds when the child kit signs off"))
        tap = dict(name=INST + ".ck", kind="core",
                   xy=[round(ORIGIN[0] + TOFF[0] + CK_PIN[0], 3), round(ORIGIN[1] + TOFF[1] + CK_PIN[1], 3)],
                   orient="R0", insertion_ps=268.8, insertion_tol_ps=40, insertion_ff_ps=211.9,
                   budget_owner=f"{EVENT['id']}: red_grt post-CTS pin-flop mean TT 268.77 / FF 211.91 ps (placement RC, "
                                "360 pin regs); re-measure on the signed view")
        t["clock"]["taps"].append(tap)
        rep["types"][T] = dict(hard_core=dict(inst=INST, origin_um=ORIGIN), core_tap=tap["xy"])
    side = None
    # reset tree / landing collector: rewrite only what the change moves
    moved = {}
    for T in TYPES:
        tree1 = RT.for_type(S.Plan(P, pout), T)
        if json.dumps(tree1, sort_keys=True) != json.dumps(trees0[T], sort_keys=True):
            lc = lc_of(P, T)
            moved[T] = dict(old=dict(depth=trees0[T].get("depth"), relays=len(trees0[T].get("relays", []))),
                            new=dict(depth=tree1.get("depth"), relays=len(tree1.get("relays", []))),
                            stored_equal_input=json.dumps(lc["collector_tree"], sort_keys=True) ==
                            json.dumps(trees0[T], sort_keys=True))
            assert RT.consumer_count(tree1) == RT.consumer_count(trees0[T]), f"{T}: consumer count moved"
            lc["collector_tree"] = json.loads(json.dumps(tree1))
        rep["types"][T]["reset_tree_moved"] = T in moved
    rep["reset_tree_moved"] = moved
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep.update(src_sha256=hashlib.sha256(text.encode()).hexdigest(), dst_sha256=hashlib.sha256(out.encode()).hexdigest())
    if len(sys.argv) > 5:
        side_in, side_out = sys.argv[4:6]
        stext = open(side_in).read()
        side = json.loads(stext)
        sst = next((k for k in (1, None) if json.dumps(side, indent=k) + "\n" == stext), 1)
        ch = []
        for T in moved:
            ent = side["collector"]["types"][T]
            ent["tree"] = copy.deepcopy(lc_of(P, T)["collector_tree"])
            ch.append(T)
        sout = json.dumps(side, indent=sst) + "\n"
        open(side_out, "w").write(sout)
        rep["sidecar"] = dict(src_sha256=hashlib.sha256(stext.encode()).hexdigest(),
                              dst_sha256=hashlib.sha256(sout.encode()).hexdigest(), changed_types=ch)
    if len(sys.argv) > 7:
        ab_in, ab_out = sys.argv[6:8]
        atext = open(ab_in).read()
        ab = json.loads(atext)
        ast = next((k for k in (1, None, 2) if json.dumps(ab, indent=k) + "\n" == atext), 1)
        if not any(r.get("module") == VARIANT for r in ab.get("substitute_inst", [])):
            ab.setdefault("substitute_inst", []).append(SUB)
        if len(sys.argv) > 8:
            ab["clock_landing_table"] = sys.argv[8]
        ab["note"] = f"{EVENT['id']}: + substitute_inst u_red -> {VARIANT} | " + ab["note"]
        aout = json.dumps(ab, indent=ast) + "\n"
        open(ab_out, "w").write(aout)
        rep["asbuilt"] = dict(src_sha256=hashlib.sha256(atext.encode()).hexdigest(),
                              dst_sha256=hashlib.sha256(aout.encode()).hexdigest(), substitute_inst=SUB)
    print("RED event:", {T: rep["types"][T] for T in TYPES})
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
