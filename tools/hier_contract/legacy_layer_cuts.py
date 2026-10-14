#!/usr/bin/env python3
"""Die tracks that legacy M6 / M7 tiles block, and the cut windows that changes (die pin audit, owner 2026-10-13).

The die cut rule (results/arch/qwen_tp8_1012/cuts.py, contract v3 layer study): tiles are capped at M5, so over a tile
the die owns M6 (horizontal wires) and M7 (vertical wires) at 75 % besides its own M8 / M9; channels add M4 / M5 at
50 %.  A tile whose CLOSED VIEW has metal on M6 or M7 takes that layer away over its whole outline:

    M6 blocked   0.75 x h / 0.064 horizontal tracks over the tile's width  (view top >= M6)
    M7 blocked   0.75 x w / 0.064 vertical tracks over the tile's height   (view top >= M7)

Per die-placed instance the top layer is, in this order: the MEASURED top layer of the master's published view
(die_pin_audit <die>_masters.json; only a view of the master itself, not a family alias), else what the contract
declares for the slot (max of signal_max_layer / pg_layer), else the contract's default cap (M5: relays and other
die-placed masters without a slot row; the generator abstract's OBS top is recorded but is not a layer plan).  Classes:
  legacy    measured view top >= M6 on a master that is not hard IP (the M5 rule is for these)
  planned   no view yet; the contract plans M6+ over it and the die cut model (cuts.py) does NOT count it as a cluster
  cluster   the cut model's own cluster list (cuts.py CLUSTER: die layer only, already in the die leads' tables)
  hard_ip   memory / PHY macro abstracts (die layer only, as cuts.py HARD_IP)
  m5        top <= M5
Cut scan: every 260-um window (cuts.py FINE) on cut lines every 50 um, bits from the die model's buses (cuts.py Net:
pins projected onto the face toward the peer), capacity three ways: `as_views` (the classes above), `if_legacy_m5`
(legacy tiles re-routed to M5; planned and hard IP unchanged) and `all_m5` (the contract's intent: only hard IP blocks).

    legacy_layer_cuts.py MODEL.json --masters MASTERS.json --contract C.json --out OUT.json [--md OUT.md] [--hot 0.55]
MODEL.json: tools/die_top_lint.py model --die ... (insts, buses, masters_obs_top).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "results/arch/qwen_tp8_1012"))
import cuts as C  # noqa: E402

HARD_RE = re.compile(r"^(ot_hbm3e_phy|ot_pdie_|ot_rom_|ot_qfd_serdes|ot_sram_|qfd_io_serdes$|qfd_io_ucie$|qkd_pll$|qfd_clkrx$)")
DERATE, CH_DERATE = 0.75, 0.50
HOT, LIMIT = 0.55, 0.60


def metal(s):
    m = re.fullmatch(r"M(\d+)", str(s or ""))
    return int(m.group(1)) if m else None


def tops(model, masters, contract):
    """{master: dict(top, source, cls, measured, declared, generator)}"""
    meas = {r["master"]: r for r in masters.get("masters", []) if not r.get("error") and r.get("macro") == r["master"]}
    decl = {}
    for s in contract.get("slots", []):
        if s.get("kind") == "die":
            continue
        d = max([metal(s.get(k)) or 0 for k in ("signal_max_layer", "pg_layer")])
        decl[s["cell"]] = max(decl.get(s["cell"], 0), d)
    cap = metal((contract.get("layer_defaults") or {}).get("layer_cap")) or 5
    out = {}
    for m in sorted({i["m"] for i in model["insts"]}):
        g = model.get("masters_obs_top", {}).get(m)
        r = meas.get(m)
        mt = metal(r["top_layer"]) if r else None
        hard = bool(HARD_RE.search(m)) or bool(r and r.get("hard_ip"))
        top, src = ((mt, "measured view") if mt is not None else (decl[m], "contract") if decl.get(m)
                    else (cap, "contract default cap (no slot row, no view)"))
        cls = ("hard_ip" if hard else "legacy" if (mt or 0) >= 6 else
               "cluster" if mt is None and top >= 6 and m in C.CLUSTER else "planned" if mt is None and top >= 6 else "m5")
        out[m] = dict(top=top, source=src, cls=cls, measured=mt, declared=decl.get(m), generator=g,
                      view=(r or {}).get("view"))
    return out


class Scan:
    def __init__(self, model_path, T):
        self.net = C.Net(model_path)
        I = list(self.net.I.values())
        self.box = np.array([(i["x"], i["y"], i["x"] + i["w"], i["y"] + i["h"]) for i in I]).reshape(-1, 4)
        self.big = np.array([i["w"] * i["h"] > 4e4 for i in I])
        self.top = np.array([T[i["m"]]["top"] for i in I])
        self.cls = np.array([T[i["m"]]["cls"] for i in I])
        self.mst = np.array([i["m"] for i in I])

    def cover(self, ax, cp, edges, sel):
        p0, o0 = (0, 1) if ax == "x" else (1, 0)
        s = sel & (self.box[:, p0] < cp) & (cp < self.box[:, p0 + 2])
        cov = np.zeros(len(edges) - 1)
        for b in self.box[s]:
            cov += np.clip(np.minimum(edges[1:], b[o0 + 2]) - np.maximum(edges[:-1], b[o0]), 0, None)
        return np.minimum(cov, np.diff(edges))

    def caps(self, ax, cp, edges):
        """usable tracks per window: (as_views, if_legacy_m5, all_m5)"""
        hi, lo, lw = ("M8", "M6", "M4") if ax == "x" else ("M9", "M7", "M5")
        L = np.diff(edges)
        lo_n = metal(lo)
        hard = (self.cls == "hard_ip") | (self.cls == "cluster")      # cuts.py: die layer only over hard IP and CLUSTER
        ch = (L - self.cover(ax, cp, edges, self.big)) * CH_DERATE * C.TPU[lw]          # M4 / M5: channels only
        base = DERATE * L * C.TPU[hi] + ch
        blk = {
            "as_views": hard | (self.top >= lo_n),
            "if_legacy_m5": hard | ((self.top >= lo_n) & (self.cls != "legacy")),
            "all_m5": hard,
        }
        return {k: base + (L - self.cover(ax, cp, edges, v)) * DERATE * C.TPU[lo] for k, v in blk.items()}

    def windows(self, hot, step=50.0, top=40):
        res = []
        for ax, span, other in (("x", self.net.W, self.net.H), ("y", self.net.H, self.net.W)):
            edges = np.arange(0, other + C.FINE, C.FINE)
            for cp in np.arange(step, span, step):
                bits = self.net.cut(ax, cp, edges)[0]
                if not bits.any():
                    continue
                cap = self.caps(ax, cp, edges)
                u = bits / cap["as_views"]
                for j in np.nonzero(u >= hot)[0]:
                    res.append((float(u[j]), ax, float(cp), float(edges[j]), int(bits[j]),
                                float(bits[j] / cap["if_legacy_m5"][j]), float(bits[j] / cap["all_m5"][j])))
        res.sort(reverse=True)
        n_hot = len(res)
        n_over = sum(1 for r in res if r[0] > LIMIT)
        n_legacy_over = sum(1 for r in res if r[0] > LIMIT >= r[5])
        n_plan_over = sum(1 for r in res if r[5] > LIMIT >= r[6])
        out = []
        for u, ax, cp, w0, bits, u5, ua in res:
            if any(ax == o["ax"] and abs(cp - o["pos"]) < 400 and abs(w0 - o["win"][0]) < 600 for o in out):
                continue
            p0, o0 = (0, 1) if ax == "x" else (1, 0)
            lo_n = 6 if ax == "x" else 7
            s = (self.box[:, p0] < cp) & (cp < self.box[:, p0 + 2]) & (self.box[:, o0] < w0 + C.FINE) & (self.box[:, o0 + 2] > w0)
            who, plan = collections.Counter(), collections.Counter()
            for i in np.nonzero(s & (self.top >= lo_n) & ((self.cls == "legacy") | (self.cls == "planned")))[0]:
                (who if self.cls[i] == "legacy" else plan)[self.mst[i]] += float(
                    min(w0 + C.FINE, self.box[i, o0 + 2]) - max(w0, self.box[i, o0]))
            out.append(dict(ax=ax, pos=round(cp), win=[round(w0), round(w0 + C.FINE)], bits=bits, util=round(u, 3),
                            util_if_legacy_m5=round(u5, 3), util_all_m5=round(ua, 3),
                            legacy_over_window_um={k: round(v, 1) for k, v in who.most_common(6)},
                            planned_over_window_um={k: round(v, 1) for k, v in plan.most_common(4)}))
            if len(out) >= top:
                break
        return dict(hot_threshold=hot, limit=LIMIT, windows_scanned_hot=n_hot, windows_over_limit=n_over,
                    windows_over_limit_only_because_of_legacy=n_legacy_over,
                    windows_over_limit_only_because_of_planned_m6_m7=n_plan_over, distinct=out)


def table(model, T):
    rows = {}
    for i in model["insts"]:
        t = T[i["m"]]
        if t["cls"] not in ("legacy", "planned"):
            continue
        r = rows.setdefault(i["m"], dict(master=i["m"], cls=t["cls"], instances=0, top=f"M{t['top']}", source=t["source"],
                                         outline=[i["w"], i["h"]], area_mm2=0.0, m6_track_mm=0.0, m7_track_mm=0.0, view=t["view"]))
        r["instances"] += 1
        r["area_mm2"] += i["w"] * i["h"] / 1e6
        if t["top"] >= 6:       # horizontal M6 tracks over the tile: count x length
            r["m6_track_mm"] += DERATE * i["h"] * C.TPU["M6"] * i["w"] / 1e3
        if t["top"] >= 7:
            r["m7_track_mm"] += DERATE * i["w"] * C.TPU["M7"] * i["h"] / 1e3
    out = sorted(rows.values(), key=lambda r: (r["cls"] != "legacy", -(r["m6_track_mm"] + r["m7_track_mm"])))
    for r in out:
        for k in ("area_mm2", "m6_track_mm", "m7_track_mm"):
            r[k] = round(r[k], 3 if k == "area_mm2" else 1)
    return out


def md(rec):
    L = [f"# Legacy M6 / M7 tiles against the die cut model: {rec['die']}", "",
         f"Die model {rec['model']} ({rec['instances']} instances, {rec['buses']} buses). Legacy = measured view top >= M6 on a "
         f"die-placed master that is not hard IP; planned = no view, contract / generator plans M6+.", "",
         f"Legacy: {rec['summary']['legacy_masters']} masters / {rec['summary']['legacy_instances']} instances, "
         f"{rec['summary']['legacy_area_mm2']} mm2, blocking {rec['summary']['legacy_m6_track_mm']} track-mm of die M6 and "
         f"{rec['summary']['legacy_m7_track_mm']} track-mm of die M7. Planned: {rec['summary']['planned_masters']} masters / "
         f"{rec['summary']['planned_instances']} instances.", "",
         "| master | class | inst | top (source) | outline um | area mm2 | die M6 track-mm blocked | die M7 track-mm blocked |",
         "|---|---|---:|---|---|---:|---:|---:|"]
    for r in rec["tiles"]:
        L.append(f"| {r['master']} | {r['cls']} | {r['instances']} | {r['top']} ({r['source']}) | {r['outline'][0]:g} x {r['outline'][1]:g} | "
                 f"{r['area_mm2']} | {r['m6_track_mm']} | {r['m7_track_mm']} |")
    w = rec["cut_windows"]
    L += ["", f"## Cut windows (260 um, util >= {w['hot_threshold']})", "",
          f"{w['windows_scanned_hot']} window positions >= {w['hot_threshold']}, {w['windows_over_limit']} over {w['limit']}; "
          f"{w['windows_over_limit_only_because_of_legacy']} of those are over {w['limit']} ONLY because legacy tiles hold M6 / M7 "
          f"(they drop to <= {w['limit']} with the legacy tiles at M5); {w['windows_over_limit_only_because_of_planned_m6_m7']} "
          f"more are over {w['limit']} only because of tiles the CONTRACT plans on M6 / M7 (clusters): over them the die has its "
          f"own layer only, which a cut table that counts them as M5-capped does not show.", "",
          "| cut | window | bits | util (closed views + contract layers) | util (legacy at M5) | util (all tiles M5) | legacy tiles over the window (um) | planned M6+ tiles over the window (um) |",
          "|---|---|---:|---:|---:|---:|---|---|"]
    for r in w["distinct"]:
        L.append(f"| {r['ax']} = {r['pos']} | {r['win'][0]}..{r['win'][1]} | {r['bits']} | {r['util']} | {r['util_if_legacy_m5']} | "
                 f"{r['util_all_m5']} | " + (", ".join(f"{k} {v:g}" for k, v in r["legacy_over_window_um"].items()) or "-") + " | "
                 + (", ".join(f"{k} {v:g}" for k, v in r["planned_over_window_um"].items()) or "-") + " |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--masters", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md")
    ap.add_argument("--hot", type=float, default=HOT)
    a = ap.parse_args(argv)
    model = json.loads(Path(a.model).read_text())
    T = tops(model, json.loads(Path(a.masters).read_text()), json.loads(Path(a.contract).read_text()))
    tiles = table(model, T)
    sc = Scan(a.model, T)
    leg = [r for r in tiles if r["cls"] == "legacy"]
    pl = [r for r in tiles if r["cls"] == "planned"]
    rec = dict(schema="opentallas.legacy_layer_cuts.v1", die=model.get("die"), model=Path(a.model).name,
               generator_tag=model.get("generator_tag"), instances=len(model["insts"]), buses=len(model["buses"]),
               rule=dict(derate=DERATE, channel_derate=CH_DERATE, pitch_um={k: round(1 / v, 3) for k, v in C.TPU.items()}, fine_um=C.FINE),
               summary=dict(legacy_masters=len(leg), legacy_instances=sum(r["instances"] for r in leg),
                            legacy_area_mm2=round(sum(r["area_mm2"] for r in leg), 3),
                            legacy_m6_track_mm=round(sum(r["m6_track_mm"] for r in leg), 1),
                            legacy_m7_track_mm=round(sum(r["m7_track_mm"] for r in leg), 1),
                            planned_masters=len(pl), planned_instances=sum(r["instances"] for r in pl)),
               tiles=tiles, cut_windows=sc.windows(a.hot),
               master_classes=dict(collections.Counter(t["cls"] for t in T.values())))
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    if a.md:
        Path(a.md).write_text(md(rec))
    print(json.dumps(dict(rec["summary"], **{k: v for k, v in rec["cut_windows"].items() if k != "distinct"})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
