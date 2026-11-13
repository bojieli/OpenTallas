#!/usr/bin/env python3
"""DIE-S81-89 11-13 (GUNIT-CORE-1 handoff section 7): reverse the N-face B-lane order of hard core dsdv_gunit_l1f_bf.

Why: the bf fold (dsdv_seln_fold_cx u_m0) compares A lane i (S face s0a / s0b, from u_alo) with B lane 7-i (N face
s1a / s1b, from u_ahi), while both faces run lanes 0..7 left to right, so the compare pairs sit 48.6 * |7-2i| um apart
(the gf3 l1r -> c1r -96 ps path).  With the N-face lanes in reverse x order every pair is vertically aligned.

What this stage writes (deterministic; nothing else in the plan changes):
  * a new bf pin table (--pins-out, relative to physical/die_plan/s81): s1a / s1b bit 41 i + k takes the (x, y, layer) of
    bit 41 (7 - i) + k, i.e. a permutation of the face's own pin sites: every pin stays on its track, no two pins share
    a site, the pin windows of the face are the same set, outline / shape / every other pin unchanged;
  * a new contract LEF (--lef-out, repo-relative): the same per-pin x shift applied to each s1a / s1b PIN RECT, all
    other bytes identical (OBS windows unchanged, since the site set is unchanged);
  * the plan with every dsdv_gunit_l1f_bf hard core repointed to the two files (text substitution of the pins_file and
    lef values only; origin, outline, orient, track_offset are asserted unchanged on re-read).
  --mode mirror (alternative, see report): mirror EVERY N-face pin (x -> W - x: s1a / s1b lanes reversed AND sv_hi /
    ctl_hi / vf_hi) and flip each front's u_ahi (dsdv_gunit_l1f_ba1) R0 -> MY, so the bf N face stays abutted bit for bit
    to the flipped A_hi band; refused if any pin of bf or ahi leaves its track (pin_track_audit rule).
The report (--report) carries the pin-track audit before / after for every bf (and in mirror mode ahi) instance and the
parent-wiring estimate: per front the bf-top -> ahi-bottom gap, the s1a / s1b nets whose two ends no longer face each
other, their horizontal span, the peak number of nets crossing one x (= horizontal tracks a channel needs) and the
channel height that takes on M4 + M6.  RTL: none (pin positions only; ports and names unchanged).

usage (repo root):
  stage_gunit_bf_nrev.py PLAN_IN PLAN_OUT --pins-out inputs/core_pins/nrev_1113/dsdv_gunit_l1f_bf.json \\
      --lef-out physical/die_plan/s81/cores/legacy/lef/nrev_1113/dsdv_gunit_l1f_bf.lef [--mode lanes|mirror] [--report R.json]
A second run on its own output refuses (the pin table carries the stage id)."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import pin_track_audit as PTA  # noqa: E402

ID = "DIE-S81-89 11-13 bf N-face lane reverse (stage_gunit_bf_nrev.py)"
BF, AHI = "dsdv_gunit_l1f_bf", "dsdv_gunit_l1f_ba1"
EW, NL = 41, 8                         # record width / lanes of s1a / s1b (dsdv_gunit_l1f_bf: [327:0] = 8 x 41)
B_PORTS = ("s1a", "s1b")
N_ONLY = ("sv_hi", "ctl_hi", "vf_hi")  # the other N-face ports (moved only in mirror mode)
UTIL = 0.7                             # usable fraction of channel tracks (estimate)


def pinhash(pins):
    d = {p["name"]: (p["layer"], p["x"], p["y"]) for p in pins}
    return hashlib.sha256(json.dumps(sorted(d.items())).encode()).hexdigest()[:12]


def bit(name):
    m = re.fullmatch(r"(\w+)\[(\d+)\]", name)
    return (m.group(1), int(m.group(2))) if m else (name, None)


def reverse_lanes(pins):
    """s1a / s1b bit 41 i + k -> the site of bit 41 (7 - i) + k; returns (new pins, {name: dx})"""
    by = {p["name"]: p for p in pins}
    out, dx = [], {}
    for p in pins:
        port, b = bit(p["name"])
        q = dict(p)
        if port in B_PORTS:
            assert b is not None and 0 <= b < EW * NL, p["name"]
            i, k = divmod(b, EW)
            src = by[f"{port}[{EW * (NL - 1 - i) + k}]"]
            assert src["layer"] == p["layer"] and src["y"] == p["y"], (p, src)
            q["x"] = src["x"]
            if q["x"] != p["x"]:
                dx[p["name"]] = round(q["x"] - p["x"], 4)
        out.append(q)
    return out, dx


def mirror_nface(pins, width, height):
    """every N-face pin x -> width - x (bf stays abutted to an MY-flipped ahi)"""
    out, dx = [], {}
    for p in pins:
        q = dict(p)
        if p["y"] > height - 1.0:
            port, _ = bit(p["name"])
            assert port in B_PORTS + N_ONLY, p["name"]
            q["x"] = round(width - p["x"], 4)
            if q["x"] != p["x"]:
                dx[p["name"]] = round(q["x"] - p["x"], 4)
        out.append(q)
    return out, dx


def shift_lef(text, dx):
    """shift every RECT x of the PIN blocks named in dx; all other bytes unchanged"""
    done = set()

    def blk(m):
        name = m.group(1)
        if name not in dx:
            return m.group(0)
        d = dx[name]
        done.add(name)

        def rect(r):
            x0, y0, x1, y1 = (float(v) for v in r.group(1, 2, 3, 4))
            return f"RECT {x0 + d:.4f} {r.group(2)} {x1 + d:.4f} {r.group(4)} ;"
        return re.sub(r"RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ;", rect, m.group(0))
    out = re.sub(r"^  PIN (\S+)\n.*?^  END \1$", blk, text, flags=re.S | re.M)
    missing = set(dx) - done
    assert not missing, f"LEF lacks PIN blocks {sorted(missing)[:4]}"
    return out


def audit(pins, hc, orient=None):
    lays = sorted({p["layer"] for p in pins})
    return PTA.audit_pins(pins, hc["origin_um"], hc.get("track_offset_um") or [0, 0], lays, orient or hc.get("orient", "R0"),
                          hc.get("outline_um"))


def offtrack(a):
    return sum(v["offtrack"] for v in a.values())


def channel_estimate(spans):
    """spans [(x0, x1)]: peak overlap = horizontal tracks one channel needs; height on M4 + M6 at UTIL"""
    ev = sorted([(a, 1) for a, b in spans] + [(b, -1) for a, b in spans])
    cur = peak = 0
    for _, s in ev:
        cur += s
        peak = max(peak, cur)
    per_um = (1 / 0.048 + 1 / 0.064) * UTIL       # M4 + M6 horizontal tracks per um of channel
    return peak, round(peak / per_um, 2)


def stage(plan_in, plan_out, pins_out, lef_out, mode="lanes", root=ROOT):
    root = Path(root)
    text = Path(plan_in).read_text()
    plan = json.loads(text)
    cores = [(t, hc) for t, ty in plan["partition_types"].items() for hc in ty.get("hard_cores") or [] if hc["module"] == BF]
    assert cores, f"no {BF} hard core in the plan"
    pf = {hc["pins_file"] for _, hc in cores}
    lf = {hc.get("lef") for _, hc in cores}
    assert len(pf) == 1 and len(lf) == 1, (pf, lf)
    pf, lf = pf.pop(), lf.pop()
    tab = json.loads((root / "physical/die_plan/s81" / pf).read_text())
    assert ID not in (tab.get("source") or ""), "already staged (second run refused)"
    W, H = cores[0][1]["outline_um"]
    assert all(hc["outline_um"] == [W, H] for _, hc in cores)
    if mode == "lanes":
        new, dx = reverse_lanes(tab["pins"])
    elif mode == "mirror":
        new, dx = mirror_nface(tab["pins"], W, H)
    else:
        raise ValueError(mode)
    sites = lambda ps: sorted((p["layer"], p["x"], p["y"]) for p in ps)     # noqa: E731
    assert len({(p["layer"], p["x"], p["y"]) for p in new}) == len(new), "two pins on one site"
    if mode == "lanes":
        assert sites(new) == sites(tab["pins"]), "lane reversal must permute the face's own sites"
    rep = dict(stage=ID, mode=mode, plan_in=str(plan_in), pins_in=pf, lef_in=lf, pins_out=pins_out, lef_out=lef_out,
               moved_pins=len(dx), pinhash_in=tab.get("pinhash"), instances=[], parent=[])
    # ---- pin track audit, every bf instance (and in mirror mode its front's ahi, flipped)
    types = plan["partition_types"]
    flips = []
    for t, hc in cores:
        a0, a1 = audit(tab["pins"], hc), audit(new, hc)
        assert offtrack(a1) <= offtrack(a0), (hc["inst"], a0, a1)
        row = dict(type=t, inst=hc["inst"], origin=hc["origin_um"], orient=hc.get("orient", "R0"),
                   offtrack_before=offtrack(a0), offtrack_after=offtrack(a1))
        front = hc["inst"].rsplit(".", 1)[0]
        ahi = [h for h in types[t]["hard_cores"] if h["module"] == AHI and h["inst"].rsplit(".", 1)[0] == front]
        assert len(ahi) == 1, (hc["inst"], len(ahi))
        ahi = ahi[0]
        apins = json.loads((root / "physical/die_plan/s81" / ahi["pins_file"]).read_text())["pins"]
        gap = round(ahi["origin_um"][1] - (hc["origin_um"][1] + H), 4)
        if mode == "mirror":
            assert ahi.get("orient", "R0") == "R0" and ahi["outline_um"][0] == W and ahi["origin_um"][0] == hc["origin_um"][0]
            aa = audit(apins, ahi, "MY")
            row.update(ahi=ahi["inst"], ahi_offtrack_my=offtrack(aa), ahi_audit_my=aa)
            assert offtrack(aa) == 0, f"{ahi['inst']} MY leaves pins off track: {aa}"
            flips.append(ahi["inst"])
        rep["instances"].append(row)
        # ---- parent estimate: bf N pin vs the ahi S pin it is wired to (u_ahi.qa / qb / sv / ctl / vf)
        ax = {p["name"]: p["x"] for p in apins}
        if mode == "mirror":
            ax = {k: round(W - v, 4) for k, v in ax.items()}
        amap = dict(s1a="qa", s1b="qb", sv_hi="sv", ctl_hi="ctl", vf_hi="vf")
        spans = []
        for p in new:
            port, b = bit(p["name"])
            if port in amap and p["y"] > H - 1.0:
                an = amap[port] + ("" if b is None else f"[{b}]")
                if abs(ax[an] - p["x"]) > 1e-6:
                    spans.append(tuple(sorted((ax[an], p["x"]))))
        peak, ch = channel_estimate(spans) if spans else (0, 0.0)
        rep["parent"].append(dict(front=front, bf_top_to_ahi_gap_um=gap, unaligned_nets=len(spans),
                                  max_jog_um=round(max((b - a for a, b in spans), default=0), 3),
                                  total_jog_um=round(sum(b - a for a, b in spans), 1), peak_crossing_tracks=peak,
                                  channel_um_m4m6=ch,
                                  ahi_west_face_pins_to_east=(sum(1 for p in apins if p["x"] < 1.0) if mode == "mirror" else 0)))
    # ---- write pins + LEF + plan
    tab2 = dict(tab, source=f"{ID} mode {mode}: from {pf} ({tab.get('pinhash')}); {tab.get('source')}", pins=new,
                pinhash=pinhash(new))
    po = root / "physical/die_plan/s81" / pins_out
    po.parent.mkdir(parents=True, exist_ok=True)
    po.write_text(json.dumps(tab2, indent=1) + "\n")
    lo = root / lef_out
    lo.parent.mkdir(parents=True, exist_ok=True)
    lo.write_text(shift_lef((root / lf).read_text(), dx))
    n = len(cores)
    out, k1 = re.subn(r'("pins_file":\s*)"' + re.escape(pf) + '"', lambda m: m.group(1) + json.dumps(pins_out), text)
    out, k2 = re.subn(r'("lef":\s*)"' + re.escape(lf) + '"', lambda m: m.group(1) + json.dumps(lef_out), out)
    assert k1 == n and k2 == n, (k1, k2, n, "pins_file / lef value shared with a non-bf core")
    for inst in flips:
        pat = re.compile(r'("inst":\s*' + re.escape(json.dumps(inst)) + r'.*?"orient":\s*)"R0"', re.S)
        out, k = pat.subn(lambda m: m.group(1) + '"MY"', out, count=1)
        assert k == 1, inst
    chk = json.loads(out)
    for t, ty in plan["partition_types"].items():         # nothing but the named fields moved
        for h0, h1 in zip(ty.get("hard_cores") or [], chk["partition_types"][t].get("hard_cores") or []):
            d = {k for k in set(h0) | set(h1) if h0.get(k) != h1.get(k)}
            allowed = {"pins_file", "lef"} if h0["module"] == BF else ({"orient"} if h0["inst"] in flips else set())
            assert d <= allowed, (h0["inst"], d)
            assert h0["origin_um"] == h1["origin_um"] and h0["outline_um"] == h1["outline_um"]
    Path(plan_out).write_text(out)
    rep["pinhash_out"] = tab2["pinhash"]
    rep["ahi_flipped"] = flips
    rep["plan_out_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--pins-out", required=True, help="relative to physical/die_plan/s81")
    ap.add_argument("--lef-out", required=True, help="repo-relative")
    ap.add_argument("--mode", choices=("lanes", "mirror"), default="lanes")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--report", default=None)
    a = ap.parse_args(argv)
    rep = stage(a.plan_in, a.plan_out, a.pins_out, a.lef_out, a.mode, a.root)
    s = json.dumps(rep, indent=1) + "\n"
    if a.report:
        Path(a.report).write_text(s)
    print(json.dumps(dict(mode=rep["mode"], moved_pins=rep["moved_pins"], pinhash=[rep["pinhash_in"], rep["pinhash_out"]],
                          offtrack=[(r["inst"], r["offtrack_before"], r["offtrack_after"]) for r in rep["instances"]],
                          parent=rep["parent"])))


if __name__ == "__main__":
    main()
