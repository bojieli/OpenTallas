#!/usr/bin/env python3
"""DIE-S81-85 FEED-BAL-1111: S81 balanced die clock feed + measured tap windows + landing-phase record (one plan event).

COORD ruling 11-10 21:01 (5): DIE-S81-85 adopts DIE-RECHECK-1's balanced feed (19 levels; the 15 SerDes/PHY
partitions keep the DS85 sb6 parents) and sizes each type's tap window to its measured spread; TOK-VERIFY-1 assigns
the landing phases from the new arrivals; S81-PLAN-1 fixes the clock geometry defects.

Base = PGR1-S81-1111 output ebea5f5b8ade (POR b05c29bbaafa + PGR1 rule A coll_lane core taps 405/340, kept).

(1) FEED.  clock.cohort (schema: authoritative die clock cohort record; no build consumer reads it, so no kit input
    changes) records DIE-RECHECK-1's min-depth BFS abutment feed feed_bal_h2_2249.json (root s_3S_L1, depth 19 vs
    sb6 26) byte-for-byte as clock.cohort.feed, plus the 15 PHY partitions whose parent and feed tap equal the DS85 sb6
    feed (asserted).  The die clock tool takes it with die_trial --feed (the sidecar in the event dir is the same JSON).
(2) TAP WINDOWS.  clock.tap_window.per_port_ps: the MEASURED per-port kit window of die_sta_related --kit-window-out
    (kit_port_needs: max over TT/FF and the type's regions of late(q) - early(p) - CPPR credit + declared core-tap
    earliness, ceil 1 ps) on DIE-RECHECK-1's routed balanced clock (proof_bal), run against THIS base plan.  A port's
    window becomes max(its current window, measured), capped at T/4 = 208 ps (gen_phys bound); ports whose measured
    need is <= the current window keep it, and types with no such port are byte-identical (no relaunch).  A type that
    had only a flat per_type_ps / window_ps gets a per-port table over its window ports (unchanged ports = old W).
(3) LANDING PHASES.  clock.cohort.landing_phases records TOK-VERIFY-1's per-landing table on the same clock
    (CA 765 / LEAD 127 / LAG 101 over 993 landings; ca_depth, ca_k, bind -> new cycles).  RECORD ONLY: the operative
    form (clock_landings count-aligned table + latency.lanes cycles) needs the bind-side mixed CA/ring form first, so
    clock.landing_network and latency are byte-identical here (see the report: companion change + per-lane deltas).
(4) DEFECT FIX (local, EQ-safe): the 2 duplicate fclk_in (+ ready/fault) positions of lk_EN0 and svc_14 are already
    separated by the plan loader (schema.Plan._separate_landing_pins, DIE-QC-67 PINDUP), so every kit sees separated
    sites while the raw plan (read by the die clock tool) still has the duplicates.  The raw landing_contract.pins of
    the two types are set to the loader's separated sites: the loaded P.types are asserted identical before/after.

usage: delta_feed_bal_1111.py PLAN_IN PLAN_OUT [REPORT.json]
       delta_feed_bal_1111.py --check PLAN_IN PLAN_OUT        (re-derive, assert byte-identical output)"""
import copy
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / "tools" / "die_plan")]
from delta_romq_split_1106 import spans  # noqa: E402
import schema as S  # noqa: E402
import gen_phys as GP  # noqa: E402

EVENT = "FEED-BAL-1111"
EV = HERE / "events" / "feed_bal_1111"
BASE_SHA = "ebea5f5b8ade"   # full sha checked by prefix; the event report carries the full value
INPUTS = {   # file -> sha256 (fail closed)
    "feed_bal_h2_2249.json": "cc6ea24096507c79a569c7d3fce54968a66989374531535ace9247b74db86450",
    "feed_sb6_h2_2249.json": "fdfa9884427c5157c4d0479725cd9c53c08b967410b69828a3a9e63e37d68c36",
    "kitwin_bal_ebea5f.json": "dcbe95ea9d561abf47bff53cf71337d01d44e66fbb9c6f22ceee41a251d991ae",
    "tok_verify_1_landing_ca_rc1_1111_landings.tsv": "b3971e59d70a37ae62ac72dc0fc62ea1a0ccd5c6e196a42f3793c1f7b01f2f11",
    "tok_verify_1_landing_ca_rc1_1111_lanes.tsv": "c38162e68a4799e10e91a9339172b2e1b6a4b26f03746d9dee127f220dd19ff8",
}
PHY = ["lk_EN0", "lk_EN1", "lk_EN2", "lk_EN3", "lk_ES0", "lk_ES1", "lk_WN0", "lk_WN1", "lk_WN2", "lk_WN3",
       "lk_WS0", "lk_WS1", "lk_WS2", "lk_WS3", "phy_hbm"]
PINDUP_PARTS = ["lk_EN0", "svc_14"]
CAP_PS = 208.0
SRC = dict(
    feed="DIE-RECHECK-1 epyc8 /srv/opentallas-scratch2/claude/die-recheck-1/s81/cfg/feed_bal_h2_2249.json "
         "(scripts/feed_bal.py --phy-parents sb6; branch claude/die-recheck-1-1110@0d6c97121e results/die_recheck_1_1110/s81/bal)",
    proof="DIE-RECHECK-1 epyc8 /srv/opentallas-scratch2/claude/die-recheck-1/s81/proof_bal (clock-only die route ck_bal/route_bal "
          "on plan_h2_2249 e596e9588e72, TT+FF, nominal 12.24b, CPPR)",
    kitwin="die_sta_related.py proof_bal --plan ebea5f5b8ade --corner TT --corner FF --core-insertion declared --kit-window-out "
           "(epyc8 /srv/opentallas-scratch2/claude/die-s81-85/feed1111/kitwin_base.json)",
    landings="TOK-VERIFY-1 READY 11-10 21:06, coord/state lanes/TOK-VERIFY-1-landing-ca-rc1-1111-{landings,lanes}.tsv "
             "(landing_ca_select.py --declared-to-ca c8078a53ca, margin 100 ps, on out_bal lps.json 684bdebd)",
    ruling="COORD 11-10 21:01 RULING (5)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_inputs():
    for f, want in INPUTS.items():
        got = sha(EV / f)
        assert got.startswith(want), (f, got, want)


def tsv(p):
    with open(p) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def ind_of(text, a):
    line0 = text.rfind("\n", 0, a) + 1
    return line0, re.match(r" *", text[line0:]).group(0)


def dumps_at(v, ind):
    return json.dumps(v, indent=1).replace("\n", "\n" + ind)


def derive(pin_path):
    text = open(pin_path).read()
    assert hashlib.sha256(text.encode()).hexdigest().startswith(BASE_SHA), "base plan is not ebea5f5b8ade"
    check_inputs()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(S.load(pin_path), Path(pin_path))
    parts = {p["name"]: p for p in raw["partitions"]}
    rep = dict(event=EVENT, base_plan_sha256=hashlib.sha256(text.encode()).hexdigest(), sources=SRC,
               inputs={f: sha(EV / f) for f in INPUTS})

    # ---- (1) feed
    fb = json.loads((EV / "feed_bal_h2_2249.json").read_text())
    fs = json.loads((EV / "feed_sb6_h2_2249.json").read_text())
    assert set(fb["parent"]) == set(parts) and set(fb["leaf_only"]) == set(PHY), "feed / partition set"
    for x in PHY:
        assert fb["parent"][x] == fs["parent"][x], (x, "PHY parent differs from DS85 sb6")
        k = f"{fb['parent'][x]}->{x}"
        assert fb["tap"][k] == fs["tap"][k], (x, "PHY feed tap differs from DS85 sb6")

    def depth(f):
        D = {}

        def d(n):
            if n not in D:
                D[n] = 0 if f["parent"][n] is None else d(f["parent"][n]) + 1
            return D[n]
        return max(d(n) for n in f["parent"])
    dep_b, dep_s = depth(fb), depth(fs)
    assert dep_b == 19 and dep_s == 26, (dep_b, dep_s)
    rep["feed"] = dict(root=fb["root"], depth=dep_b, depth_sb6=dep_s, partitions=len(fb["parent"]),
                       edges=len(fb["tap"]), reparented_vs_sb6=sum(fb["parent"][n] != fs["parent"][n] for n in fb["parent"]),
                       phy_keep_ds85=[dict(part=x, parent=fb["parent"][x], tap=fb["tap"][f"{fb['parent'][x]}->{x}"]) for x in PHY])

    # ---- (2) tap windows
    kw = json.loads((EV / "kitwin_bal_ebea5f.json").read_text())
    assert kw["plan_sha256"].startswith(BASE_SHA), "kit windows not measured against the base plan"
    tw = raw["clock"]["tap_window"]
    ppt = tw.setdefault("per_port_ps", {})
    changed, residual = {}, []
    for tn, meas in sorted(kw["per_port_ps"].items()):
        names = GP.window_port_names(P, tn)
        cur = {n: GP.port_window_ps(P, tn, n) for n in names}
        up = {n: v for n, v in meas.items() if n in cur and v > cur[n] + 1e-9}
        unk = sorted(set(meas) - set(cur))
        assert not unk, (tn, "measured port is not a window port of the type", unk[:5])
        if not up:
            continue
        old_tab = ppt.get(tn)
        new_tab = dict(old_tab) if old_tab else {n: cur[n] for n in names}
        for n, v in up.items():
            nv = min(float(math.ceil(v - 1e-9)), CAP_PS)
            if v > CAP_PS:
                residual.append(dict(type=tn, port=n, need_ps=v, written_ps=CAP_PS, short_ps=round(v - CAP_PS, 1)))
            new_tab[n] = int(nv) if nv == int(nv) else nv
        new_tab = {k: (int(v) if float(v) == int(v) else v) for k, v in sorted(new_tab.items())}
        ppt[tn] = new_tab
        changed[tn] = dict(form="per_port (updated)" if old_tab else "per_port (new; was flat %g)" % GP.tap_window_ps(P, tn),
                           ports=len(new_tab), raised={n: [cur[n], new_tab[n], meas[n]] for n in sorted(up)},
                           max_old=max(cur.values()), max_new=max(float(v) for v in new_tab.values()),
                           parts=sorted(p for p in parts if parts[p]["type"] == tn))
    raw["clock"]["tap_window"]["per_port_ps"] = dict(sorted(ppt.items())) if not orig["clock"]["tap_window"].get(
        "per_port_ps") else {**{k: ppt[k] for k in orig["clock"]["tap_window"]["per_port_ps"]},
                             **{k: ppt[k] for k in sorted(ppt) if k not in orig["clock"]["tap_window"]["per_port_ps"]}}
    tw["note"] = orig["clock"]["tap_window"]["note"] + (
        f" DIE-S81-85 {EVENT} (COORD 11-10 21:01 (5)): per_port_ps of {len(changed)} types raised to the MEASURED per-port "
        "kit window (die_sta_related --kit-window-out on DIE-RECHECK-1's routed balanced-feed die clock proof_bal, TT+FF, "
        f"against plan {BASE_SHA}, ceil 1 ps, no margin): window = max(current, measured), cap T/4 = 208 "
        f"({len(residual)} ports above the cap -> die clock: designed DME delay on those taps); unchanged types keep "
        "their window byte-identical.")
    rep["tap_window"] = dict(types_changed=len(changed), changed=changed, residual_over_cap=residual,
                             rule="max(current port window, measured), ceil 1 ps, cap 208 (T/4)")

    # ---- (3) landing phases (record)
    L = tsv(EV / "tok_verify_1_landing_ca_rc1_1111_landings.tsv")
    LN = tsv(EV / "tok_verify_1_landing_ca_rc1_1111_lanes.tsv")
    eids = {e["id"] for e in raw["clock"]["landing_network"]["edges"] if e["id"].startswith("cland_clk__")}
    ports = {r["port"] for r in L}
    assert len(L) == 993 and {"cland_clk__" + p for p in ports} == eids, "landing set != plan functional landings"
    lanes = {l["id"]: l for l in raw["lanes"]}
    per_lane = {}
    for r in L:
        assert r["lane"] in lanes and r["port"] in lanes[r["lane"]]["ports"], r["port"]
        per_lane[r["lane"]] = per_lane.get(r["lane"], 0) + int(r["delta"])
    for r in LN:
        assert per_lane.get(r["lane"], 0) == int(r["delta"]), r["lane"]
    from collections import Counter
    dec = Counter(r["decision"] for r in L)
    assert dec == {"CA": 765, "LEAD": 127, "LAG": 101}, dec
    raw["clock"]["cohort"] = dict(
        id="s81_feed_bal19_1111", authority=SRC["ruling"] + "; DIE-S81-85 " + EVENT,
        source=dict(feed=SRC["feed"], proof=SRC["proof"], landings=SRC["landings"]),
        status="feed = S81 die clock feed of record (die_trial --feed); landing_phases = RECORD, not operative until the "
               "bind emits the mixed count-aligned / ring form (clock.landing_network unchanged)",
        phy_parents_kept_ds85=PHY,
        feed=fb,
        landing_phases=dict(
            columns=["decision", "ca_depth", "ca_k", "bind_cycles", "new_cycles"],
            counts=dict(dec), lane_cycle_delta_total=dict(up=sum(v for v in per_lane.values() if v > 0),
                                                          down=sum(v for v in per_lane.values() if v < 0)),
            tsv_sha256={f: sha(EV / f) for f in ("tok_verify_1_landing_ca_rc1_1111_landings.tsv",
                                                 "tok_verify_1_landing_ca_rc1_1111_lanes.tsv")},
            per_port={r["port"]: [r["decision"], int(r["ca_depth"]) if r["ca_depth"] not in ("", "None") else None,
                                  int(r["ca_k"]) if r["ca_k"] not in ("", "None") else None,
                                  int(r["bind_cycles"]), int(r["new_cycles"])] for r in sorted(L, key=lambda r: r["port"])}))
    rep["landing_phases"] = dict(counts=dict(dec), lanes=len(LN), lanes_changed=sum(1 for v in per_lane.values() if v),
                                 cycles_up=sum(v for v in per_lane.values() if v > 0),
                                 cycles_down=sum(v for v in per_lane.values() if v < 0),
                                 per_lane_delta={k: v for k, v in sorted(per_lane.items()) if v},
                                 receiver_types=sorted({parts[r["dst"]]["type"] for r in L if r["decision"] == "CA"}),
                                 operative=False)

    # ---- (4) duplicate landing pin positions: materialize the loader's separated sites
    pin_fix = []
    for q in PINDUP_PARTS:
        tn = parts[q]["type"]
        rp = raw["partition_types"][tn]["clock"]["landing_contract"]["pins"]
        sp = {x["name"]: x for x in P.types[tn]["clock"]["landing_contract"]["pins"]}
        for x in rp:
            if x["xy_um"] != sp[x["name"]]["xy_um"]:
                pin_fix.append(dict(part=q, type=tn, pin=x["name"], raw_xy=x["xy_um"], separated_xy=sp[x["name"]]["xy_um"],
                                    die_xy=[round(v, 3) for v in P.to_die(q, sp[x["name"]]["xy_um"])]))
                x["xy_um"] = copy.deepcopy(sp[x["name"]]["xy_um"])
        assert raw["partition_types"][tn]["clock"]["landing_contract"]["pins"] == P.types[tn]["clock"]["landing_contract"]["pins"]
        # the loader moves a separated clock input's edge_clocks tap with it (landing_contract.separate_pins)
        re_ = raw["partition_types"][tn]["clock"].get("edge_clocks")
        for i, (x, y) in enumerate(zip(re_ or [], P.types[tn]["clock"].get("edge_clocks") or [])):
            if x != y:
                assert set(x) == set(y) and all(x[k] == y[k] for k in x if k != "tap_um"), (tn, i)
                pin_fix.append(dict(part=q, type=tn, edge_clock=x.get("port"), raw_tap_um=x["tap_um"], separated_tap_um=y["tap_um"]))
                re_[i] = copy.deepcopy(y)
        assert raw["partition_types"][tn]["clock"].get("edge_clocks") == P.types[tn]["clock"].get("edge_clocks")
    assert sum("pin" in r for r in pin_fix) == 6, pin_fix
    rep["pindup_fix"] = pin_fix

    # ---- text edits (indent-1 style), last span first
    sp = spans(text)
    edits = []
    a, b = sp[("clock", "tap_window", "per_port_ps")]
    edits.append((a, b, dumps_at(raw["clock"]["tap_window"]["per_port_ps"], ind_of(text, a)[1])))
    a, b = sp[("clock", "tap_window", "note")]
    edits.append((a, b, json.dumps(tw["note"])))
    for q in PINDUP_PARTS:
        tn = parts[q]["type"]
        a, b = sp[("partition_types", tn, "clock", "landing_contract", "pins")]
        edits.append((a, b, dumps_at(raw["partition_types"][tn]["clock"]["landing_contract"]["pins"], ind_of(text, a)[1])))
        if raw["partition_types"][tn]["clock"].get("edge_clocks") != orig["partition_types"][tn]["clock"].get("edge_clocks"):
            a, b = sp[("partition_types", tn, "clock", "edge_clocks")]
            edits.append((a, b, dumps_at(raw["partition_types"][tn]["clock"]["edge_clocks"], ind_of(text, a)[1])))
    last = list(orig["clock"])[-1]
    a, b = sp[("clock", last)]
    _l0, ind = ind_of(text, a)
    edits.append((b, b, ",\n" + ind + '"cohort": ' + dumps_at(raw["clock"]["cohort"], ind)))
    for a, b, new in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:a] + new + text[b:]
    out = json.loads(text)
    assert out == raw, "text edit != object edit"

    # ---- EQ gate: every other key byte-identical
    for k in raw:
        if k not in ("partition_types", "clock"):
            assert raw[k] == orig[k], k
    for k in raw["clock"]:
        if k not in ("tap_window", "cohort"):
            assert raw["clock"][k] == orig["clock"][k], k
    for k in raw["clock"]["tap_window"]:
        if k not in ("per_port_ps", "note"):
            assert raw["clock"]["tap_window"][k] == orig["clock"]["tap_window"][k], k
    for tn in raw["clock"]["tap_window"]["per_port_ps"]:
        if tn not in changed:
            assert raw["clock"]["tap_window"]["per_port_ps"][tn] == orig["clock"]["tap_window"]["per_port_ps"][tn], tn
    pin_types = {parts[q]["type"] for q in PINDUP_PARTS}
    for tn in raw["partition_types"]:
        if tn not in pin_types:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    P2 = S.Plan(json.loads(text), Path(pin_path))
    for tn in P.types:
        assert P2.types[tn] == P.types[tn], (tn, "loaded type changed")
    rep["eq_gate"] = dict(
        rtl_change=False, pin_change=False, outline_change=False, cycle_change=False,
        changed_paths=["clock.cohort (new record)", "clock.tap_window.per_port_ps (%d types)" % len(changed),
                       "clock.tap_window.note"] + [f"partition_types.{t}.clock.landing_contract.pins + clock.edge_clocks[].tap_um (raw only; loaded type identical)" for t in sorted(pin_types)],
        loaded_types_identical=True, other_keys_identical=True,
        note="landing_network, latency, lanes, ports, partitions, die, reset and every type key byte-identical; the two "
             "pin-site types load identically (the loader already separated the sites)")
    relaunch = sorted(set(changed))
    rep["relaunch_types"] = relaunch
    rep["relaunch_types_count"] = len(relaunch)
    rep["pin_record_types_no_kit_change"] = sorted(pin_types)
    return text, rep


def main():
    if sys.argv[1] == "--check":
        text, _ = derive(sys.argv[2])
        assert open(sys.argv[3]).read() == text, "output differs from re-derivation"
        print("CHECK PASS", hashlib.sha256(text.encode()).hexdigest())
        return
    text, rep = derive(sys.argv[1])
    open(sys.argv[2], "w").write(text)
    rep["output_plan_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("output_plan_sha256", "relaunch_types_count")}),
          rep["tap_window"]["types_changed"], len(rep["tap_window"]["residual_over_cap"]))


if __name__ == "__main__":
    main()
