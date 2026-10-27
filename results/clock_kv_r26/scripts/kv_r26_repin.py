#!/usr/bin/env python3
"""CLOCK-KV-R26 (COORD 07:03, KV-CORES-R6 ask): plan delta hm_r25 -> hm_r26.

  (1) e1 + e5 head-eighth clock pins -> the 12.8a centre entry sites that kv_core_slice (KV-CORE-SLICE-1) assigns
      (taken from the KV-CORES-R6 pdR6 views, checked: y = H/2, inside the 8.64-um entry island, same site set as e6).
  (2) e5 sub-core reset pins: r25 sat them on x 107.928..108.216 (108.024 = slice clock site of g_t_10_u_l8) ->
      moved to the e6-analogue reset sites of the same centre row (g_t_10 <-> g_t_12, g_t_11 <-> g_t_13), all off the
      clock sites, >= 2 M5 tracks from every other pin, PG-clear, MX-invariant (y = H/2).
  (3) e5 fMX view rewritten as the exact MX image; D-KV-HEAD-TR(A): every e5 instance on the fMX view at MX goes to
      the canonical e5 view at R0 (same origin; die xy of every pin unchanged by construction).
  Every other pin byte-identical (asserted).  Writes OUT/cores/*_r26.json, OUT/hm_r26.json, report.

    kv_r26_repin.py PD25 PDR6_CORES OUT_PD --report R.json
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kv_island_ports import pg_ok, M5_OFF, M5_PITCH  # noqa: E402

H = W = 216.0
CY = 108.0
ISL_HALF = 4.32
E5_RST = {  # e6-analogue sites (e6_pins_r25: g_t_12_u_stin 107.928, g_t_12_u_stk 108.216, g_t_13_u_stin 107.832, g_t_13_u_stk 108.312)
    "g_t_10_u_stin__rst_n[0]": 107.928, "g_t_10_u_stk__rst_n[0]": 108.216,
    "g_t_11_u_stin__rst_n[0]": 107.832, "g_t_11_u_stk__rst_n[0]": 108.312}
E6MAP = {"g_t_10": "g_t_12", "g_t_11": "g_t_13"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def is_clk(n):
    return n.split("__")[-1].startswith("clk")


def dump(d):
    return (json.dumps(d, indent=1) + "\n").encode()


def row_check(pins, tag):
    row = sorted((p for p in pins if p["layer"] == "M5" and abs(p["y"] - CY) < 1e-6), key=lambda p: p["x"])
    for a, b in zip(row, row[1:]):
        assert b["x"] - a["x"] > 2 * M5_PITCH - 1e-6, (tag, a, b)
    for p in row:
        assert pg_ok(p["x"]), (tag, p)
        k = (p["x"] - M5_OFF) / M5_PITCH
        assert abs(k - round(k)) < 1e-6, (tag, "off track", p)
        assert abs(p["x"] - W / 2) <= ISL_HALF - 0.1, (tag, "outside entry island", p)
    return [(p["name"], p["x"]) for p in row]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pd25")
    ap.add_argument("r6cores")
    ap.add_argument("out")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    pd, r6, out = Path(a.pd25), Path(a.r6cores), Path(a.out)
    rep = dict(schema="opentallas.clock_kv_r26.repin.v1", delta="D-KV-CENTRE-R26 + D-KV-HEAD-TR(A) e5", files={})
    e6 = {p["name"]: p for p in json.loads((pd / "cores/kv3_head_eighth_e6_pins_r25.json").read_text())["pins"]}
    new = {}
    for mod, src in (("e1", "kv3_head_eighth_e1_pins.json"), ("e5", "kv3_head_eighth_e5_pins_r25.json")):
        B = json.loads((pd / "cores" / src).read_text())
        S = {p["name"]: p for p in json.loads((r6 / f"kv3_head_eighth_{mod}_pins.json").read_text())["pins"]}
        assert B["frame"].endswith("outline 216 x 216"), B["frame"]
        N = copy.deepcopy(B)
        moved = []
        for p in N["pins"]:
            if is_clk(p["name"]):
                s = S[p["name"]]
                assert s["layer"] == "M5" and abs(s["y"] - CY) < 1e-6 and abs(s["x"] - W / 2) < ISL_HALF, s
                moved.append(dict(pin=p["name"], from_=[p["x"], p["y"]], to=[s["x"], s["y"]], why="12.8a centre entry"))
                p["x"], p["y"] = s["x"], s["y"]
            elif mod == "e5" and p["name"] in E5_RST:
                x = E5_RST[p["name"]]
                e6n = E6MAP[p["name"][:6]] + p["name"][6:]
                assert e6[e6n]["x"] == x and e6[e6n]["y"] == CY, (e6n, e6[e6n])
                moved.append(dict(pin=p["name"], from_=[p["x"], p["y"]], to=[x, CY], why=f"off clock site; = e6 {e6n} site"))
                p["x"], p["y"] = x, CY
        # every other pin byte-identical
        bo = {p["name"]: p for p in B["pins"]}
        changed = {m["pin"] for m in moved}
        for p in N["pins"]:
            if p["name"] not in changed:
                assert p == bo[p["name"]], p
        assert [p["name"] for p in N["pins"]] == [p["name"] for p in B["pins"]]
        N["source"] = B["source"] + (" | CLOCK-KV-R26 10-27: clock pins -> 12.8a centre entry (kv_core_slice sites)" +
                                     ("; sub-core rst_n -> e6-analogue centre-row sites off the clock sites" if mod == "e5" else ""))
        rowpins = row_check(N["pins"], mod)
        stem = f"kv3_head_eighth_{mod}_pins_r26"
        new[stem] = N
        rep["files"][stem] = dict(base=src, moved=moved, centre_row=rowpins, pins=len(N["pins"]))
    # e5 fMX = exact MX image
    N5 = new["kv3_head_eighth_e5_pins_r26"]
    V = json.loads((pd / "cores/kv3_head_eighth_e5_pins_fMX_r25.json").read_text())
    NV = copy.deepcopy(V)
    NV["pins"] = [dict(p, y=round(H - p["y"], 4)) for p in N5["pins"]]
    NV["source"] = V["source"] + " | CLOCK-KV-R26 10-27: rewritten as the exact MX image of kv3_head_eighth_e5_pins_r26.json (unused by hm_r26: D-KV-HEAD-TR(A))"
    new["kv3_head_eighth_e5_pins_fMX_r26"] = NV
    nimg = sum(1 for p, q in zip(N5["pins"], NV["pins"]) if (q["name"], q["layer"], q["x"], q["y"]) != (p["name"], p["layer"], p["x"], round(H - p["y"], 4)))
    rep["files"]["kv3_head_eighth_e5_pins_fMX_r26"] = dict(non_image_pins=nimg, pins=len(NV["pins"]))
    assert nimg == 0
    # plan delta
    P = json.loads((pd / "hm_r25.json").read_text())
    cnt = dict(e1=0, e5_R0=0, e5_canonMX=0, e5_fMX_to_R0=0)
    for tn, t in P["partition_types"].items():
        for hc in t.get("hard_cores") or []:
            pf = hc["pins_file"]
            if pf == "cores/kv3_head_eighth_e1_pins.json":
                hc["pins_file"] = "cores/kv3_head_eighth_e1_pins_r26.json"; cnt["e1"] += 1
            elif pf == "cores/kv3_head_eighth_e5_pins_r25.json":
                hc["pins_file"] = "cores/kv3_head_eighth_e5_pins_r26.json"
                cnt["e5_R0" if hc["orient"] == "R0" else "e5_canonMX"] += 1
            elif pf == "cores/kv3_head_eighth_e5_pins_fMX_r25.json":
                assert hc["orient"] == "MX", hc
                hc["pins_file"] = "cores/kv3_head_eighth_e5_pins_r26.json"; hc["orient"] = "R0"
                hc["note"] = (hc.get("note") or "") + " | CLOCK-KV-R26 D-KV-HEAD-TR(A): fMX view at MX -> canonical at R0 (same origin)"
                cnt["e5_fMX_to_R0"] += 1
    # type clock taps on the e1/e5 entry pin (R21: one tap per instance on g_t_2/g_t_10 _u_l8__clk[0]) follow the pin;
    # the 24 TR(A) e5 entries (were on the unsigned fMX view, no tap) get the same tap as their canonical siblings
    TAPPIN = {"kv3_head_eighth_e1": "g_t_2_u_l8__clk[0]", "kv3_head_eighth_e5": "g_t_10_u_l8__clk[0]"}
    pv = {"cores/" + k + ".json": {p["name"]: p for p in v["pins"]} for k, v in new.items()}
    tcnt = dict(moved=0, added=0)
    for tn, t in P["partition_types"].items():
        hcs = [h for h in (t.get("hard_cores") or []) if h["module"] in TAPPIN]
        if not hcs:
            continue
        taps = t["clock"]["taps"]
        byname = {tp["name"]: tp for tp in taps}
        for h in hcs:
            pin = TAPPIN[h["module"]]
            p = pv[h["pins_file"]][pin]
            w, hh = h["outline_um"]
            o = h["orient"]
            ox, oy = (a_ + b_ for a_, b_ in zip(h["origin_um"], h.get("track_offset_um") or [0.0, 0.0]))
            u = w - p["x"] if o in ("MY", "R180") else p["x"]
            v = hh - p["y"] if o in ("MX", "R180") else p["y"]
            xy = [round(ox + u, 4), round(oy + v, 4)]
            nm = f"{h['inst']}.{pin}"
            if nm in byname:
                tp = byname[nm]
                tp["xy"] = xy
                tp["note"] = ("CLOCK-KV-R26: tap moved with its pin to the 12.8a centre entry (core (108.024,108)); "
                              "view re-sign on the r26 pins pending (KV-CORES); was: " + tp["note"])
                tcnt["moved"] += 1
            else:
                assert h["module"] == "kv3_head_eighth_e5" and "D-KV-HEAD-TR(A)" in h["note"], (tn, h["inst"])
                taps.append(dict(name=nm, kind="core", xy=xy, insertion_ps=250.0, budget_owner=h["module"],
                                 note="CLOCK-KV-R26: D-KV-HEAD-TR(A) instance on the canonical e5 view: tap on the 12.8a "
                                      "centre-entry clock pin like its canonical siblings; view re-sign pending (KV-CORES)"))
                tcnt["added"] += 1
    rep["taps"] = tcnt
    s = json.dumps(P)
    assert "e1_pins.json" not in s and "e5_pins_r25" not in s and "e5_pins_fMX_r25" not in s
    P["note"] = (P.get("note") or "") + " | hm_r26 (CLOCK-KV-R26 10-27): e1/e5 clock pins at the 12.8a centre entry, e5 rst_n e6-analogue centre-row sites, D-KV-HEAD-TR(A) e5"
    (out / "cores").mkdir(parents=True, exist_ok=True)
    for stem, d in new.items():
        b = dump(d)
        (out / "cores" / f"{stem}.json").write_bytes(b)
        rep["files"][stem]["sha256"] = sha(b)
    pb = (json.dumps(P, indent=1) + "\n").encode()
    (out / "hm_r26.json").write_bytes(pb)
    rep["hard_core_entries"] = cnt
    rep["plan_in_sha256"] = sha((pd / "hm_r25.json").read_bytes())
    rep["plan_out_sha256"] = sha(pb)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(cnt=cnt, plan=rep["plan_out_sha256"][:8], files={k: v.get("sha256", "")[:8] for k, v in rep["files"].items()})))
    for k, v in rep["files"].items():
        for m in v.get("moved", []):
            print(k, m)


if __name__ == "__main__":
    main()
