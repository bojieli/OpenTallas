#!/usr/bin/env python3
"""DIE-S81-85 FEED-BAL-2-1111: FEED-BAL-1111 re-based onto the composed POR + PGR1 + SVCPROV-V5-POR plan, with the
tap windows re-measured on the FEED-BAL clock (one plan event, EQ-gated).

Why a re-base: FEED-BAL-1111 (02bc4a0da1, delta_feed_bal_1111.py) and SVCPROV-V5-POR-1111 (S81-SVCRS-3 bbc252fd69a7,
plan_h2_2249_pgr1_v5_ca10ae6afbab2337) are both deltas on PGR1's ebea5f5b8ade.  bbc252 ships a fixed plan file, so
FEED-BAL is the one re-based: BASE = ca10ae6afbab (OWNER 11-10 23:04 approved the v5 die grow).  The two edits touch
disjoint keys and commute (checked: v5 applied after FEED-BAL, da67dc118bd8 -> 5d1555dc7d74, equals ca10ae + the
FEED-BAL keys on every key).

Keys written (everything else byte-identical to BASE, asserted):
  clock.cohort            FEED-BAL's record: DIE-RECHECK-1 feed_bal (19 levels, the 15 PHY partitions on the DS85 sb6
                          parents/taps), feed tap points moved with the v5 grow (svc_split_event_1109.die_grow dy rule:
                          +G_TOTAL at y >= LO_TOP_DIE, as clock.spine.root_um), + TOK-VERIFY-1's landing-phase table
                          (RECORD, not operative; clock.landing_network / latency unchanged).
  clock.tap_window        per_port_ps: per port max(current, measured ebea5f [FEED-BAL], measured 66466e86ebcd
                          [DIE-RECHECK-1 kitwin_auto on the routed FEED-BAL clock]), ceil 1 ps, cap T/4 = 208; ports not
                          raised keep their window, types with no raised port are byte-identical.  Measured ports the
                          base type no longer has (the svc_rs taps v5 removes) are skipped and listed.
  2 types' clock          lk_EN0 / svc_14 landing pins (+ moved edge_clocks tap) set to the loader-separated sites
                          (schema.Plan._separate_landing_pins); the loaded types are identical.

Base: ca10ae6afbab, or 64eb2c89c94c (ca10ae + SVCPROV-PHYSINST-1111; DS85-COMPOSE-1111 BASE_1200 chain).

--svc-as-base: leave the 14 svc_rs types' windows as in BASE also on 64eb2c89 (the ca10ae behaviour, a pure commute
with SVCPROV-PHYSINST): their measured tables (ebea5f / 66466e) are from the pre-v5 svc_rs types, whose clk_c* / clk_t*
port names do not name the same taps after the v5 rebuild (v5 has 32 core taps; 66466e measured clk_c0..c63).

usage: delta_feed_bal2_1111.py [--svc-as-base] PLAN_IN PLAN_OUT [REPORT.json]
       delta_feed_bal2_1111.py --check PLAN_IN PLAN_OUT"""
import copy
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / "tools" / "die_plan")]
import schema as S  # noqa: E402
import gen_phys as GP  # noqa: E402
import svc_split_event_1109 as V1  # noqa: E402
import delta_feed_bal_1111 as FB  # noqa: E402

EVENT = "FEED-BAL-2-1111"
EV1 = HERE / "events" / "feed_bal_1111"
EV2 = HERE / "events" / "feed_bal2_1111"
BASE_SHA = "ca10ae6afbab2337fd8c87e165b2037c37bd3f173f33f99dd34d4228793b3bb9"
# accepted bases: ca10ae (v5) and 64eb2c89 = ca10ae + SVCPROV-PHYSINST-1111 (the 56 physical_inst keys on the svc_rs
# TRX provider boxes).  On 64eb2c89 gen_phys can list the 14 svc_rs types' window ports, so their measured windows
# apply too (on ca10ae they raised and were left as in BASE).
BASES = {BASE_SHA: "ca10ae6afbab PGR1 + SVCPROV-V5-POR",
         "64eb2c89c94c197fee42a5d5c2cb45e36dd03bcfa1f08ca964de7b33c8ac990f":
             "64eb2c89c94c ca10ae + SVCPROV-PHYSINST-1111 (events/svc_prov_v5_por_1111/plan_h2_2249_pgr1_v5pi_64eb2c89c94c197f)"}
KW2 = ("kitwin_auto_66466e86ebcd.json", "9149770f950a979af32ff08a22f08037ce92490fd9139300d76ecd62e18f4d44")
CAP_PS = 208.0
SVC_V5 = tuple(V1.HI_TYPES) + tuple(V1.LO_TYPES)   # the 14 svc_rs types v5 rebuilds (windows measured pre-grow)
SRC2 = dict(kitwin2="DIE-RECHECK-1 die_sta_related --kit-window-out on proof_auto_66466e86ebcd (routed FEED-BAL clock "
                    "on plan 66466e86ebcd), intel1 /srv/opentallas-scratch2/claude/die-recheck-1/s81/kitwin_auto_66466e86ebcd.json",
            svcprov="S81-SVCRS-3 SVCPROV-V5-POR-1111 bbc252fd69a7 events/svc_prov_v5_por_1111/"
                    "plan_h2_2249_pgr1_v5_ca10ae6afbab2337.json.gz (OWNER 11-10 23:04 approved the die grow)")


def window_ps(v):
    return int(v) if float(v) == int(v) else v


def derive(pin_path, svc_as_base=False):
    text = open(pin_path).read()
    base_sha = hashlib.sha256(text.encode()).hexdigest()
    assert base_sha in BASES, f"base {base_sha[:12]} is not ca10ae6afbab or 64eb2c89c94c"
    assert json.dumps(json.loads(text)) + "\n" == text, "base is not in the compact json.dumps form"
    FB.check_inputs()
    assert FB.sha(EV2 / KW2[0]) == KW2[1], KW2
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(S.load(pin_path), Path(pin_path))
    parts = {p["name"]: p for p in raw["partitions"]}
    rep = dict(event=EVENT, base_plan_sha256=base_sha, base=BASES[base_sha], sources=dict(FB.SRC, **SRC2),
               inputs=dict({f: FB.sha(EV1 / f) for f in FB.INPUTS}, **{KW2[0]: KW2[1]}))

    # ---- tap windows: max(current, m1, m2), cap 208
    m1 = json.loads((EV1 / "kitwin_bal_ebea5f.json").read_text())
    m2 = json.loads((EV2 / KW2[0]).read_text())
    assert m1["plan_sha256"].startswith("ebea5f5b8ade") and m2["plan_sha256"].startswith("66466e86ebcd")
    tw = raw["clock"]["tap_window"]
    ppt = tw["per_port_ps"]
    changed, blocked, skipped, gen_error = {}, {}, {}, {}
    for tn in sorted(set(m1["per_port_ps"]) | set(m2["per_port_ps"])):
        a, b = m1["per_port_ps"].get(tn, {}), m2["per_port_ps"].get(tn, {})
        if svc_as_base and tn in SVC_V5:   # --svc-as-base: the 14 v5 types keep their BASE window (pure commute)
            gen_error[tn] = "--svc-as-base: measured before the v5 rebuild (port names clk_c*/clk_t* not the v5 taps)"
            continue
        try:
            names = GP.window_port_names(P, tn)
        except ValueError as e:      # gen_phys cannot list the type's clock ports: the type is left as in BASE
            assert tn in SVC_V5, (tn, str(e))
            gen_error[tn] = str(e)
            continue
        cur = {n: GP.port_window_ps(P, tn, n) for n in names}
        unk = sorted((set(a) | set(b)) - set(cur))
        if unk:
            assert tn in SVC_V5, (tn, "measured port is not a window port", unk[:5])
            skipped[tn] = unk
        need = {n: max(a.get(n, 0.0), b.get(n, 0.0)) for n in (set(a) | set(b)) & set(cur)}
        over = {n: v for n, v in need.items() if v > CAP_PS}
        if over:
            blocked[tn] = dict(sorted(over.items()))
        up = {n: v for n, v in need.items() if v > cur[n] + 1e-9}
        if not up:
            continue
        tab = dict(ppt[tn]) if ppt.get(tn) else {n: cur[n] for n in names}
        for n, v in up.items():
            tab[n] = window_ps(min(float(math.ceil(v - 1e-9)), CAP_PS))
        tab = {k: window_ps(v) for k, v in sorted(tab.items())}
        ppt[tn] = tab
        changed[tn] = dict(raised={n: [cur[n], tab[n], a.get(n), b.get(n)] for n in sorted(up)},
                           from_66466e=sorted(n for n in up if b.get(n, 0.0) > a.get(n, 0.0)),
                           parts=sorted(p for p in parts if parts[p]["type"] == tn))
    tw["per_port_ps"] = {**{k: ppt[k] for k in orig["clock"]["tap_window"]["per_port_ps"]},
                         **{k: ppt[k] for k in sorted(ppt) if k not in orig["clock"]["tap_window"]["per_port_ps"]}}
    tw["note"] = orig["clock"]["tap_window"]["note"] + (
        f" DIE-S81-85 {EVENT} (COORD 11-10 21:01 (5) + DIE-RECHECK-1 FEED-BAL recheck): per_port_ps of {len(changed)} types "
        "raised to the MEASURED per-port kit window, max over the ebea5f proof_bal table (FEED-BAL-1111) and DIE-RECHECK-1's "
        "kitwin_auto_66466e86ebcd (routed FEED-BAL clock), ceil 1 ps, no margin, cap T/4 = 208; "
        f"{len(blocked)} types have ports above the cap (held: designed DME early-tap delay, S81-PLAN-1); unchanged types "
        "keep their window byte-identical; the 14 svc_rs types were measured before the v5 grow.")
    rep["tap_window"] = dict(rule="max(current, measured ebea5f, measured 66466e), ceil 1 ps, cap 208 (T/4)",
                             types_changed=len(changed), changed=changed,
                             blocked_types=len(blocked), blocked=blocked, skipped_ports_v5=skipped,
                             gen_phys_error_types_left_as_base=gen_error)

    # ---- clock.cohort: FEED-BAL's record, feed taps moved with the v5 grow
    fb = json.loads((EV1 / "feed_bal_h2_2249.json").read_text())
    fs = json.loads((EV1 / "feed_sb6_h2_2249.json").read_text())
    assert set(fb["parent"]) == set(parts)
    for x in FB.PHY:
        assert fb["parent"][x] == fs["parent"][x] and fb["tap"][f"{fb['parent'][x]}->{x}"] == fs["tap"][f"{fs['parent'][x]}->{x}"], x
    feed = copy.deepcopy(fb)
    G, cut = V1.G_TOTAL, V1.LO_TOP_DIE
    moved = 0
    for k, (x, y) in list(feed["tap"].items()):
        if y >= cut - 0.01:
            feed["tap"][k] = [x, round(y + G, 3)]
            moved += 1
    L = FB.tsv(EV1 / "tok_verify_1_landing_ca_rc1_1111_landings.tsv")
    LN = FB.tsv(EV1 / "tok_verify_1_landing_ca_rc1_1111_lanes.tsv")
    eids = {e["id"] for e in raw["clock"]["landing_network"]["edges"] if e["id"].startswith("cland_clk__")}
    assert len(L) == 993 and {"cland_clk__" + r["port"] for r in L} == eids
    lanes = {l["id"]: l for l in raw["lanes"]}
    per_lane = Counter()
    for r in L:
        assert r["port"] in lanes[r["lane"]]["ports"], r["port"]
        per_lane[r["lane"]] += int(r["delta"])
    for r in LN:
        assert per_lane.get(r["lane"], 0) == int(r["delta"]), r["lane"]
    dec = Counter(r["decision"] for r in L)
    assert dec == {"CA": 765, "LEAD": 127, "LAG": 101}, dec

    def iv(s):
        return int(s) if s not in ("", "None") else None
    assert "cohort" not in raw["clock"]
    raw["clock"]["cohort"] = dict(
        id="s81_feed_bal19_1111", authority=FB.SRC["ruling"] + "; DIE-S81-85 FEED-BAL-1111 / " + EVENT,
        source=dict(feed=FB.SRC["feed"], proof=FB.SRC["proof"], landings=FB.SRC["landings"], svcprov=SRC2["svcprov"]),
        status="feed = S81 die clock feed of record (die_trial --feed); landing_phases = RECORD, not operative until the "
               f"bind emits the mixed count-aligned / ring form (clock.landing_network unchanged); feed taps moved with the "
               f"v5 grow (+{G} um at y >= {cut}: {moved} taps); landing phases were measured before the grow",
        phy_parents_kept_ds85=FB.PHY,
        feed=feed,
        landing_phases=dict(
            columns=["decision", "ca_depth", "ca_k", "bind_cycles", "new_cycles"], counts=dict(dec),
            lane_cycle_delta_total=dict(up=sum(v for v in per_lane.values() if v > 0),
                                        down=sum(v for v in per_lane.values() if v < 0)),
            tsv_sha256={f: FB.sha(EV1 / f) for f in ("tok_verify_1_landing_ca_rc1_1111_landings.tsv",
                                                     "tok_verify_1_landing_ca_rc1_1111_lanes.tsv")},
            per_port={r["port"]: [r["decision"], iv(r["ca_depth"]), iv(r["ca_k"]), int(r["bind_cycles"]),
                                  int(r["new_cycles"])] for r in sorted(L, key=lambda r: r["port"])}))
    rep["feed"] = dict(root=fb["root"], depth=19, taps_moved_with_grow=moved, grow_um=G, cut_y_um=cut)
    rep["landing_phases"] = dict(counts=dict(dec), lanes_changed=sum(1 for v in per_lane.values() if v), operative=False)

    # ---- duplicate landing pins: the loader's separated sites
    pin_fix = []
    for q in FB.PINDUP_PARTS:
        tn = parts[q]["type"]
        ck, sk = raw["partition_types"][tn]["clock"], P.types[tn]["clock"]
        sp = {x["name"]: x for x in sk["landing_contract"]["pins"]}
        for x in ck["landing_contract"]["pins"]:
            if x["xy_um"] != sp[x["name"]]["xy_um"]:
                pin_fix.append(dict(part=q, type=tn, pin=x["name"], raw_xy=x["xy_um"], separated_xy=sp[x["name"]]["xy_um"]))
                x["xy_um"] = copy.deepcopy(sp[x["name"]]["xy_um"])
        for i, (x, y) in enumerate(zip(ck.get("edge_clocks") or [], sk.get("edge_clocks") or [])):
            if x != y:
                assert all(x[k] == y[k] for k in x if k != "tap_um") and set(x) == set(y), (tn, i)
                pin_fix.append(dict(part=q, type=tn, edge_clock=x.get("port"), raw_tap_um=x["tap_um"], separated_tap_um=y["tap_um"]))
                ck["edge_clocks"][i] = copy.deepcopy(y)
        assert ck["landing_contract"]["pins"] == sk["landing_contract"]["pins"] and ck.get("edge_clocks") == sk.get("edge_clocks")
    assert sum("pin" in r for r in pin_fix) == 6, pin_fix
    rep["pindup_fix"] = pin_fix

    out_text = json.dumps(raw) + "\n"
    # ---- EQ gate
    for k in raw:
        if k not in ("partition_types", "clock"):
            assert raw[k] == orig[k], k
    for k in set(raw["clock"]) | set(orig["clock"]):
        if k not in ("tap_window", "cohort"):
            assert raw["clock"][k] == orig["clock"][k], k
    for k in raw["clock"]["tap_window"]:
        if k not in ("per_port_ps", "note"):
            assert raw["clock"]["tap_window"][k] == orig["clock"]["tap_window"][k], k
    for tn in orig["clock"]["tap_window"]["per_port_ps"]:
        if tn not in changed:
            assert raw["clock"]["tap_window"]["per_port_ps"][tn] == orig["clock"]["tap_window"]["per_port_ps"][tn], tn
    pin_types = {parts[q]["type"] for q in FB.PINDUP_PARTS}
    for tn in raw["partition_types"]:
        if tn not in pin_types:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
        else:
            for k in raw["partition_types"][tn]:
                if k != "clock":
                    assert raw["partition_types"][tn][k] == orig["partition_types"][tn][k], (tn, k)
    P2 = S.Plan(json.loads(out_text), Path(pin_path))
    for tn in P.types:
        assert P2.types[tn] == P.types[tn], (tn, "loaded type changed")
    rep["eq_gate"] = dict(rtl_change=False, pin_change=False, outline_change=False, cycle_change=False,
                          changed_paths=["clock.cohort (new record)",
                                         f"clock.tap_window.per_port_ps ({len(changed)} types) + note"] +
                                        [f"partition_types.{t}.clock landing pins + edge_clocks tap (raw only; loaded type identical)"
                                         for t in sorted(pin_types)],
                          loaded_types_identical=True, other_keys_identical=True)
    rep["window_types_changed"] = sorted(changed)
    rep["stale_v5_types"] = sorted(t for t in SVC_V5 if t in raw["partition_types"])
    return out_text, rep


def main():
    svc_as_base = "--svc-as-base" in sys.argv
    if svc_as_base:
        sys.argv.remove("--svc-as-base")
    if sys.argv[1] == "--check":
        text, _ = derive(sys.argv[2], svc_as_base)
        assert open(sys.argv[3]).read() == text, "output differs from re-derivation"
        print("CHECK PASS", hashlib.sha256(text.encode()).hexdigest())
        return
    text, rep = derive(sys.argv[1], svc_as_base)
    open(sys.argv[2], "w").write(text)
    rep["output_plan_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(out=rep["output_plan_sha256"], changed=rep["tap_window"]["types_changed"],
                          blocked=rep["tap_window"]["blocked_types"], skipped=rep["tap_window"]["skipped_ports_v5"])))


if __name__ == "__main__":
    main()
