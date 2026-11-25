#!/usr/bin/env python3
"""KV-PC-ABSTRACT: exact M4/M5 OBS for the kvpc hard-core views (qkd_kvs_pcc / qkd_kvs_pcf and the h_head_p variants).

The 11-21 pc_v3 obstruction form (OBS-SYNC-1) wrote M1-M5 as one blanket OBS rect (write_abstract_lef
-bloat_occupied_layers): 94 % (pcf) / 100 % (pcc) of the macro blocked on M4/M5, although the real M4/M5 metal is
2-7 % of the area (kv3_pc kits: GRT overflow 4,096-4,317 over the kvpc column).  Re-exports of a kvpc view keep M1-M3
blanket and take M4/M5 from the same signed ODB (write_abstract_lef -bloat_factor 0, M4 pin-clear cut).

v3 (Fable review 11-25): the pin clearance now removes ONLY the signal pin's own shape from the grown OBS -- never foreign
metal or its spacing (v2 cut a 48 nm zone around every pin, which uncovered real foreign-net metal), and the splice no longer
uses abstract_detail's --pin-clear zone either.  OBS slivers below the layer's minimum width (24 nm on M4/M5; residue of the
pin cuts and of the slab decomposition) are regrown to the minimum width (in place, never over a pin shape or outside the macro) or dropped when it cannot grow; the grown shapes are clipped to the macro outline.

v2 guardrails (COORD 11-25): zero-bloat exact OBS risks DRC against the real internal metal and leaves unusable slivers, so
after the splice every M4/M5 OBS shape is GROWN by max(min spacing, merge gap / 2) per side and the union is merged (gaps
< --merge-gap-um, default 2 x track pitch, close), then the signal pins' own shapes are cut out again so pin access stays open.  PG pins stay PIN, the PG strap metal stays OBS (grown); PIN, PG, SIZE and
all other layers are untouched (abstract_detail check).  --grow-um 0 --merge-gap-um 0 gives the v1 exact form.

  python3 -I kvpc_exact_m45.py --base signed_view.lef --detail exact_b0.lef --out new.lef [--receipt r.json]
      [--min-space-um 0.024] [--pitch-um 0.048] [--merge-gap-um 0.096] [--grow-um X]
"""
import argparse
import bisect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_detail as A

LAYERS = "M4,M5"
MIN_WIDTH_UM = 0.024      # ASAP7 M4/M5 min width
MIN_SPACE_UM = 0.024      # ASAP7 M4/M5 min spacing
PITCH_UM = 0.048          # ASAP7 M4/M5 track pitch
# the published base carries the finalize pin stubs, the raw ODB export does not: this one splice finding is expected
EXPECTED_PROBLEM = "detailed export PIN section != base (different ODB?)"
_RECT = re.compile(r"^\s*RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;")


def splice_args(base, detail, out):
    return ["splice", "--base", str(base), "--detail", str(detail), "--layers", LAYERS, "--bloat-factor", "0", "--out", str(out)]


def _nm(v):
    return int(round(float(v) * 1000))


def union_minus(add, sub):
    """disjoint rects (nm ints) covering union(add) minus union(sub); vertical slabs, coalesced when identical"""
    evs = {}
    for k, rs in ((0, add), (1, sub)):
        for r in rs:
            if r[2] > r[0] and r[3] > r[1]:
                evs.setdefault(r[1], []).append((k, r, 1))
                evs.setdefault(r[3], []).append((k, r, 0))
    act = ([], [])
    out, open_ = [], {}
    ys = sorted(evs)
    for i, y in enumerate(ys):
        for k, r, on in evs[y]:
            lst = act[k]
            if on:
                bisect.insort(lst, (r[0], r[2]))
            else:
                lst.remove((r[0], r[2]))
        cur = _slab(act[0], act[1])
        for iv in [iv for iv in open_ if iv not in cur]:
            out.append((iv[0], open_.pop(iv), iv[1], y))
        for iv in cur:
            open_.setdefault(iv, y)
    return out


def _merge(lst):
    res = []
    for a, b in lst:
        if res and a <= res[-1][1]:
            if b > res[-1][1]:
                res[-1][1] = b
        else:
            res.append([a, b])
    return res


def _slab(add, sub):
    m = _merge(add)
    if not sub or not m:
        return {(a, b) for a, b in m}
    s = _merge(sub)
    res, j = set(), 0
    for a, b in m:
        x = a
        while j < len(s) and s[j][1] <= a:
            j += 1
        k = j
        while k < len(s) and s[k][0] < b:
            if s[k][0] > x:
                res.add((x, s[k][0]))
            x = max(x, s[k][1])
            k += 1
        if x < b:
            res.add((x, b))
    return res


def _parse(text):
    """(lines, obs_start, obs_end, {layer: [rect nm]} of the OBS, {layer: [signal pin rect nm]}, area(um2 SIZE))"""
    lines = text.split("\n")
    pins, cur_pin, sig, lay = {}, None, False, None
    obs_start = None
    obs = {}
    for i, l in enumerate(lines):
        s = l.strip()
        if obs_start is None:
            m = re.match(r"PIN\s+(\S+)", s)
            if m:
                cur_pin = m.group(1)
            elif s.startswith("USE "):
                sig = s.rstrip(" ;").split()[1] == "SIGNAL"
            elif s == "OBS":
                obs_start, lay = i, None
                continue
            m = re.match(r"LAYER\s+(\w+)", s)
            if m:
                lay = m.group(1)
            m = _RECT.match(l)
            if m and cur_pin and sig:
                pins.setdefault(lay, []).append(tuple(_nm(v) for v in m.groups()))
        else:
            m = re.match(r"LAYER\s+(\w+)", s)
            if m:
                lay = m.group(1)
            m = _RECT.match(l)
            if m:
                obs.setdefault(lay, []).append(tuple(_nm(v) for v in m.groups()))
    size = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", text)
    return lines, obs_start, obs, pins, (float(size.group(1)), float(size.group(2)))


def _area(rs):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) / 1e6


def fix_slivers(res, clear, minw, bbox):
    """regrow every rect narrower than minw (nm) to minw in place (overlapping its neighbours is fine in a LEF OBS): symmetric,
    else to one side, never over a pin shape in `clear` and never outside bbox; a sliver that cannot grow is dropped (it is
    the residue of a pin cut).  -> (rects, dict(slivers_found, regrown, dropped))"""
    out, found, regrown, dropped = [], 0, 0, 0
    for r in res:
        r = list(r)
        bad = [ax for ax in (0, 1) if r[ax + 2] - r[ax] < minw]
        if not bad:
            out.append(tuple(r))
            continue
        found += 1
        cand = [r]
        for ax in bad:
            e = minw - (r[ax + 2] - r[ax])
            nxt = []
            for c in cand:
                for lo, hi in ((e // 2 + e % 2, e // 2), (e, 0), (0, e)):
                    q = list(c)
                    q[ax] -= lo
                    q[ax + 2] += hi
                    nxt.append(q)
            cand = nxt
        ok = None
        for q in cand:
            if q[0] < bbox[0] or q[1] < bbox[1] or q[2] > bbox[2] or q[3] > bbox[3]:
                continue
            if any(q[0] < p[2] and q[2] > p[0] and q[1] < p[3] and q[3] > p[1] for p in clear):
                continue
            ok = q
            break
        if ok:
            out.append(tuple(ok))
            regrown += 1
        else:
            dropped += 1
    return out, dict(slivers_found=found, regrown=regrown, dropped=dropped)


def grow_merge(lef_in, lef_out, grow_um, layers=("M4", "M5"), min_width_um=MIN_WIDTH_UM):
    """grow the M4/M5 OBS of lef_in by grow_um per side, merge, cut ONLY the signal pins' own shapes, fix slivers -> stats"""
    text = Path(lef_in).read_text()
    lines, obs_start, obs, pins, (W, H) = _parse(text)
    g, mw, stats = _nm(grow_um), _nm(min_width_um), {}
    bbox = (0, 0, _nm(W), _nm(H))
    # drop the old M4/M5 OBS lines (layer header + its rects), keep every other line
    keep, lay, i = [], None, obs_start + 1
    keep = lines[:i]
    end = None
    for j in range(i, len(lines)):
        s = lines[j].strip()
        m = re.match(r"LAYER\s+(\w+)", s)
        if m:
            lay = m.group(1)
        if s == "END" and lines[j].startswith("  END"):
            end = j
            break
        if lay in layers:
            continue
        keep.append(lines[j])
    new_blocks = []
    for L in layers:
        old = obs.get(L, [])
        grown = [(max(0, r[0] - g), max(0, r[1] - g), min(bbox[2], r[2] + g), min(bbox[3], r[3] + g)) for r in old]
        clear = list(pins.get(L, []))
        res, sl = fix_slivers(union_minus(grown, clear), clear, mw, bbox)
        res = sorted(res)
        new_blocks.append(f"    LAYER {L} ;")
        new_blocks += [f"     RECT  {a / 1000:.3f} {b / 1000:.3f} {c / 1000:.3f} {d / 1000:.3f} ;" for a, b, c, d in res]
        stats[L] = dict(rects_before=len(old), rects_after=len(res), obs_area_pct_before=round(100 * _area(old) / (W * H), 2),
                        blocked_area_pct_after=round(100 * _area(res) / (W * H), 2), **sl)
    Path(lef_out).write_text("\n".join(keep + new_blocks + lines[end:]))
    stats["lef_bytes_before"] = Path(lef_in).stat().st_size
    stats["lef_bytes_after"] = Path(lef_out).stat().st_size
    return stats


def run(base, detail, out, receipt=None, grow_um=None, merge_gap_um=None, min_space_um=MIN_SPACE_UM, pitch_um=PITCH_UM):
    """splice + (grow/merge) + check; 0 iff the output differs from base only in the M4/M5 OBS"""
    import contextlib
    import io
    merge_gap_um = 2 * pitch_um if merge_gap_um is None else merge_gap_um
    grow = max(min_space_um, merge_gap_um / 2.0) if grow_um is None else grow_um
    if grow == 0:
        min_space_um = 0.0
    out = Path(out)
    exact = out if grow == 0 else out.with_name(out.name + ".exact.tmp")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = A.main(splice_args(base, detail, exact))
    rec = json.loads(buf.getvalue() or "{}")
    problems = [p for p in rec.get("problems", []) if p != EXPECTED_PROBLEM]
    if (rc not in (0, 1)) or problems:
        return 2
    if grow > 0:
        rec["grow_merge"] = dict(grow_um=grow, merge_gap_um=merge_gap_um, min_space_um=min_space_um,
                                 min_width_um=MIN_WIDTH_UM, stats=grow_merge(exact, out, grow))
        exact.unlink()
    if receipt:
        Path(receipt).write_text(json.dumps(rec, indent=1))
    return A.main(["check", "--base", str(base), "--new", str(out), "--layers", LAYERS])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--detail", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt")
    ap.add_argument("--min-space-um", type=float, default=MIN_SPACE_UM)
    ap.add_argument("--pitch-um", type=float, default=PITCH_UM)
    ap.add_argument("--merge-gap-um", type=float, help="close gaps below this (default 2 x pitch)")
    ap.add_argument("--grow-um", type=float, help="per-side growth (default max(min space, merge gap / 2)); 0 = v1 exact")
    a = ap.parse_args(argv)
    return run(a.base, a.detail, a.out, a.receipt, a.grow_um, a.merge_gap_um, a.min_space_um, a.pitch_um)


if __name__ == "__main__":
    sys.exit(main())
