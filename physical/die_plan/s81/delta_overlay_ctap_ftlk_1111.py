#!/usr/bin/env python3
"""DIE-S81-85 OVERLAY-CTAP-FTLK-1111: two per-item overlay plans on the FEED-BAL-2 plan 99f40d35071d (POR + PGR1 +
SVCPROV-V5-POR + FEED-BAL-2) for the relaunch types KW-FIX-43 held back, because 99f40d drops a change they run on.

  ctap  the CORE-CTAP-WIDE set (dsdv_slice_c1x_C t3/t4/t9/t10, lepe_mu_C__t1, lepe_nh_mus_C__t1, lepw_mu_C__t1, eng__t1):
        their partition_types.<t>.clock.taps / clock.core_taps from CORE-CTAP-WIDE plan c839c3235890 (ENG-CTAP-1109 +
        CORE-CTAP-WIDE-1109, delta_core_ctap_wide_1109.py / delta_eng_ctap_1109.py).  Then the FEED-BAL-2 window rule
        (per port max(current, measured ebea5f, measured 66466e), ceil 1 ps, cap 208) on these types; the early core-tap
        ports the measurements do not list keep the type's flat W_t (gen_phys.port_window_ps fallback) and are listed.
  ftlk  the FTLOCK set (slice_station t27/t49): clock.ft_hop_lockup from FTLOCK plan 9c9ac92a70d1 (= b05c29bbaafa +
        clock.ft_hop_lockup only, ft_hop_lockup_item_event.py receipt).  Their partition types and windows are as in 99f40d.

Composition is three-way and fail-closed: ANCESTOR = the wave plan b05c29bbaafa (h2_2249 before PGR1/v5/FEED-BAL; the
FTLOCK input, and on every ctap type byte-identical to the CORE-CTAP-WIDE input type).  A donor key is taken only where
the donor differs from ANCESTOR and 99f40d equals ANCESTOR (no key changed both ways); any other donor difference on the
named types / keys stops the run.  Every other type and key is byte-identical to 99f40d, asserted (and loaded types).

usage: delta_overlay_ctap_ftlk_1111.py MODE BASE_99f40d ANCESTOR_b05c29 DONOR PLAN_OUT [REPORT.json]
       delta_overlay_ctap_ftlk_1111.py --check MODE BASE ANCESTOR DONOR PLAN_OUT"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / "tools" / "die_plan")]
import schema as S  # noqa: E402
import gen_phys as GP  # noqa: E402

EVENT = "OVERLAY-CTAP-FTLK-1111"
EV1 = HERE / "events" / "feed_bal_1111"
EV2 = HERE / "events" / "feed_bal2_1111"
BASE_SHA = "99f40d35071d66bf2edd2b81f4d7046598f297bbf0b1b3884006252e85172eb9"
ANC_SHA = "b05c29bbaafa9842f541802672e6e2ff44963e13286bec6e08f7e50898001c50"
M1 = ("kitwin_bal_ebea5f.json", "dcbe95ea")
M2 = ("kitwin_auto_66466e86ebcd.json", "9149770f950a979af32ff08a22f08037ce92490fd9139300d76ecd62e18f4d44")
CAP_PS = 208.0
MODES = dict(
    ctap=dict(donor_sha="c839c32358909222a4c27e9e9ce9534309a0508a3273d9ac0e5e29539572f9de",
              donor="CORE-CTAP-WIDE-1109 plan c839c3235890 (epyc7 die-s81-85/s81p7/src_ctap2/physical/die_plan/s81/"
                    "plan_h2_2249.json; bind10_ctap)",
              types=["dsdv_slice_c1x_C__t3", "dsdv_slice_c1x_C__t4", "dsdv_slice_c1x_C__t9", "dsdv_slice_c1x_C__t10",
                     "dsdv_slice_lepe_mu_C__t1", "dsdv_slice_lepe_nh_mus_C__t1", "dsdv_slice_lepw_mu_C__t1", "eng__t1"],
              type_clock_keys=("taps", "core_taps"), clock_keys=()),
    ftlk=dict(donor_sha="9c9ac92a70d162a8278c0b5b725122df6033669d537281560ce6e6fd3c6cbc6e",
              donor="FTLOCK-S81 plan 9c9ac92a70d1 (epyc7 die-s81-85/ftlock/s81/plan_ftlk_9c9ac92a70d1.json; bind_ftlk)",
              types=["slice_station__t27", "slice_station__t49"],
              type_clock_keys=(), clock_keys=("ft_hop_lockup",)))
ABSENT = "<absent>"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def window_ps(v):
    return int(v) if float(v) == int(v) else v


def flat(raw):
    """(path tuple) -> value at type-key / type-clock-key / clock-key / top-key granularity."""
    out = {}
    for k, v in raw.items():
        if k == "partition_types":
            for t, tv in v.items():
                for kk, vv in tv.items():
                    if kk == "clock" and isinstance(vv, dict):
                        for c, cv in vv.items():
                            out[("T", t, "clock", c)] = cv
                    else:
                        out[("T", t, kk)] = vv
        elif k == "clock":
            for c, cv in v.items():
                out[("clock", c)] = cv
        else:
            out[(k,)] = v
    return out


def derive(mode, base_p, anc_p, donor_p):
    M = MODES[mode]
    text = open(base_p).read()
    assert hashlib.sha256(text.encode()).hexdigest() == BASE_SHA, "base is not 99f40d35071d (FEED-BAL-2)"
    assert json.dumps(json.loads(text)) + "\n" == text, "base is not in the compact json.dumps form"
    assert sha(anc_p) == ANC_SHA, "ancestor is not b05c29bbaafa"
    assert sha(donor_p) == M["donor_sha"], f"donor is not {M['donor_sha'][:12]}"
    assert sha(EV2 / M2[0]) == M2[1] and sha(EV1 / M1[0]).startswith(M1[1])
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    A = flat(json.load(open(anc_p)))
    D = flat(json.load(open(donor_p)))
    B = flat(raw)
    want = {("T", t, "clock", c) for t in M["types"] for c in M["type_clock_keys"]} | {("clock", c) for c in M["clock_keys"]}
    rep = dict(event=EVENT, mode=mode, base_plan_sha256=BASE_SHA, ancestor_plan_sha256=ANC_SHA,
               donor=M["donor"], donor_plan_sha256=M["donor_sha"], types=M["types"])

    # ---- three-way: donor changes on the named types / keys
    took, same_as_anc, conflicts = [], [], []
    for t in M["types"]:
        tk = {k for k in set(A) | set(D) if k[:2] == ("T", t)}
        for k in sorted(tk):
            a, d, b = A.get(k, ABSENT), D.get(k, ABSENT), B.get(k, ABSENT)
            if d == a:
                continue
            assert k in want, ("donor changes a key outside the overlay", k)
            if b != a:
                conflicts.append(list(k))
        assert all(B.get(k, ABSENT) == A.get(k, ABSENT) for k in tk if k not in want), (t, "99f40d changed this type")
    for k in sorted(want):
        a, d, b = A.get(k, ABSENT), D.get(k, ABSENT), B.get(k, ABSENT)
        if d == a:
            same_as_anc.append(list(k))
            continue
        if b != a and b != d:
            conflicts.append(list(k))
            continue
        took.append(list(k))
        if k[0] == "T":
            ck = raw["partition_types"][k[1]]["clock"]
            if d == ABSENT:
                ck.pop(k[3], None)
            else:
                ck[k[3]] = copy.deepcopy(d)
        else:
            if d == ABSENT:
                raw["clock"].pop(k[1], None)
            else:
                raw["clock"][k[1]] = copy.deepcopy(d)
    assert not conflicts, ("composition conflict", conflicts)
    rep["composition"] = dict(took_from_donor=took, donor_equal_to_ancestor=same_as_anc, conflicts=conflicts)
    if mode == "ctap":
        rep["composition"]["core_taps_added"] = {
            t: [x["name"] for x in raw["partition_types"][t]["clock"].get("taps", [])
                if x.get("kind") == "core" and x not in (A.get(("T", t, "clock", "taps")) or [])]
            for t in M["types"]}
    else:
        rep["composition"]["ft_hop_lockup"] = raw["clock"]["ft_hop_lockup"]

    # ---- windows: FEED-BAL-2 rule on the composed types
    mid = json.dumps(raw) + "\n"
    P = S.Plan(json.loads(mid), Path(base_p))
    m1 = json.loads((EV1 / M1[0]).read_text())
    m2 = json.loads((EV2 / M2[0]).read_text())
    tw = raw["clock"]["tap_window"]
    ppt = tw["per_port_ps"]
    win = {}
    for tn in M["types"]:
        a, b = m1["per_port_ps"].get(tn, {}), m2["per_port_ps"].get(tn, {})
        names = GP.window_port_names(P, tn)
        cur = {n: GP.port_window_ps(P, tn, n) for n in names}
        meas = set(a) | set(b)
        need = {n: max(a.get(n, 0.0), b.get(n, 0.0)) for n in meas & set(cur)}
        up = {n: v for n, v in need.items() if v > cur[n] + 1e-9}
        over = {n: v for n, v in need.items() if v > CAP_PS}
        if up:
            tab = dict(ppt[tn]) if ppt.get(tn) else {n: cur[n] for n in names}
            for n, v in up.items():
                tab[n] = window_ps(min(float(math.ceil(v - 1e-9)), CAP_PS))
            ppt[tn] = {k: window_ps(v) for k, v in sorted(tab.items())}
        win[tn] = dict(window_ports=len(names), raised={n: [cur[n], ppt[tn][n], a.get(n), b.get(n)] for n in sorted(up)},
                       over_cap=dict(sorted(over.items())),
                       unmeasured_ports_on_W_t=sorted(n for n in names if n not in meas),
                       W_t=GP.tap_window_ps(P, tn),
                       measured_ports_not_window=sorted(meas - set(cur)))
    raised = sorted(t for t in win if win[t]["raised"])
    if raised:
        tw["note"] = orig["clock"]["tap_window"]["note"] + (
            f" DIE-S81-85 {EVENT} ({mode}): FEED-BAL-2 rule re-applied on {len(raised)} composed types.")
    rep["tap_window"] = dict(rule="max(current, measured ebea5f, measured 66466e), ceil 1 ps, cap 208 (T/4)",
                             types_raised=raised, per_type=win)

    out_text = json.dumps(raw) + "\n"
    # ---- EQ gate vs 99f40d
    O = flat(raw)
    changed = sorted(list(k) for k in set(O) | set(B) if O.get(k, ABSENT) != B.get(k, ABSENT))
    allowed = {tuple(k) for k in took} | ({("clock", "tap_window")} if raised else set())
    assert {tuple(k) for k in changed} <= allowed, ("unexpected change", changed)
    if raised:
        for k in raw["clock"]["tap_window"]:
            if k not in ("per_port_ps", "note"):
                assert raw["clock"]["tap_window"][k] == orig["clock"]["tap_window"][k], k
        for tn in set(ppt) | set(orig["clock"]["tap_window"]["per_port_ps"]):
            if tn not in raised:
                assert ppt.get(tn) == orig["clock"]["tap_window"]["per_port_ps"].get(tn), tn
    P0 = S.Plan(S.load(base_p), Path(base_p))
    P2 = S.Plan(json.loads(out_text), Path(base_p))
    diff_types = sorted(t for t in P0.types if P2.types[t] != P0.types[t])
    assert set(diff_types) <= set(M["types"]), diff_types
    rep["eq_gate"] = dict(changed_paths=changed, loaded_types_changed=diff_types,
                          every_other_type_and_key_identical_to_99f40d=True,
                          rtl_change=(mode == "ctap" and bool(diff_types)) or mode == "ftlk",
                          note="clock-structure overlay only: no pin, outline, content or cycle change on any type; "
                               "ctap adds early core-tap clock ports (bound RTL of the overlay types changes, as "
                               "bind9 -> bind10_ctap); ftlk adds u_fl_ hop lockup latches in the t27/t49 bound RTL")
    return out_text, rep


def main():
    if sys.argv[1] == "--check":
        text, _ = derive(*sys.argv[2:6])
        assert open(sys.argv[6]).read() == text, "output differs from re-derivation"
        print("CHECK PASS", hashlib.sha256(text.encode()).hexdigest())
        return
    text, rep = derive(*sys.argv[1:5])
    open(sys.argv[5], "w").write(text)
    rep["output_plan_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    if len(sys.argv) > 6:
        Path(sys.argv[6]).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(out=rep["output_plan_sha256"], took=rep["composition"]["took_from_donor"],
                          raised=rep["tap_window"]["types_raised"], loaded_changed=rep["eq_gate"]["loaded_types_changed"])))


if __name__ == "__main__":
    main()
