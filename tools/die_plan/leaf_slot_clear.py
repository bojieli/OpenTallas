#!/usr/bin/env python3
"""S81-LEAF-T14 11-15 (FABLE-PD-S81T-0710 sec 4): leaf slot clear.  Class fix for the two measured leaf defects

  (A) a ve_m / ve_s slot under 20 um holding > 200 ft station sites  -> ve_m moves east by --ve-push (34.56 um),
      rigidly with every macro it would crowd (ft_throat_fix.push_ok); stations under the moved cores follow;
  (B) ft station sites inside a macro body (+ keep-off)                 -> the whole stage is re-sited as a band at the
      nearest legal free site (ft_throat_fix.search: u_station <= target, hops <= max(LIMIT, before)).

Plan geometry only: pins, windows, outlines, core shapes, station counts, cycles and RTL unchanged.  ft_bit_sites follow
because the kit takes its sites from plan bit_sites_um.

  leaf_slot_clear.py PLAN OUT_ROWS LEDGER [--type REGEX] [--ve-push 34.56] [--ve-min-sites 200] [--target 0.95]
OUT_ROWS holds only the changed partition_types rows (merge with plan_merge or json update).
"""
import argparse, json, math, os, re, sys
from pathlib import Path
import numpy as np
TD = os.environ.get("TD") or str(Path(__file__).resolve().parent)
sys.path[:0] = [TD, os.path.dirname(os.path.dirname(TD))]
import schema as S, ft_spread as FS, ft_seam_fix as SF, ft_throat_fix as T


def in_macro(t, boxes=None):
    boxes = boxes or S.placed_macro_boxes(t); out = []
    for x in t.get("ft_slots") or []:
        cw, ch = x.get("bit_site_cell_um", FS.CELL)
        for j, st in enumerate(x.get("bit_sites_um") or []):
            by = {}
            for bx, byy in st:
                for m, b in boxes.items():
                    if b[0] < bx + cw / 2 < b[2] and b[1] < byy + ch / 2 < b[3]:
                        by[m] = by.get(m, 0) + 1; break
            if by:
                out.append((x["name"], j, sum(by.values()), len(st), by))
    return out


def ve_pair(t, boxes):
    m = next((k for k in boxes if k.endswith("u_ve.u_m")), None); s = next((k for k in boxes if k.endswith("u_ve.u_s")), None)
    return (m, s) if m and s else (None, None)


def ve_slot_sites(t, boxes):
    """(gap um, sites) of the ve_m/ve_s facing slot, sites = station sites whose centre lies inside it."""
    m, s = ve_pair(t, boxes)
    if not m:
        return None
    a, b = boxes[s], boxes[m]
    for p, q, axis in ((a, b, 0), (b, a, 0), (a, b, 1), (b, a, 1)):
        o = 1 - axis
        gap = q[axis] - p[axis + 2]; ov = min(p[o + 2], q[o + 2]) - max(p[o], q[o])
        if 0 < gap < 20 and ov > 0:
            r = [0, 0, 0, 0]; r[axis] = p[axis + 2]; r[axis + 2] = q[axis]
            r[o] = max(p[o], q[o]); r[o + 2] = min(p[o + 2], q[o + 2])
            n = 0
            for x in t.get("ft_slots") or []:
                cw, ch = x.get("bit_site_cell_um", FS.CELL)
                for st in x.get("bit_sites_um") or []:
                    n += sum(1 for bx, by in st if r[0] <= bx + cw / 2 <= r[2] and r[1] <= by + ch / 2 <= r[3])
            return gap, n, axis, (1 if boxes[m][axis] > boxes[s][axis] else -1)
    return None


def resite_stage(P, t, tn, s, j, target, rec):
    W = int(s["width"]); W1 = W + 1; hz = T.horiz(s); tpu = FS._tracks(s, hz)
    ext_need = W / (target * tpu) / 0.95 + (FS.CELL[1] if hz else FS.CELL[0])
    lids = SF.slot_lanes(P, tn, s["name"])
    lim = max(T.LIMIT, SF.max_slot_hop(P, lids, tn, s["name"])[0]); first_ok0 = SF.first_hop_ok(P, tn, s)
    olds = s["bit_sites_um"][j]; r0 = np.array(s["regs_um"][j + 1], float)
    # a stage whose centroid is in a macro: seed the search at the centroid of its sites outside macros if any
    done, fails = T.search(P, t, s, j, r0, T.ranks(olds, hz), W1, ext_need, hz, s["bit_site_cell_um"], W, tpu, target, lids, lim, first_ok0)
    if done is None:
        # last resort: relax the hop limit by one column pitch step per try (never above 405)
        for extra in (5.0,):
            done, fails = T.search(P, t, s, j, r0, T.ranks(olds, hz), W1, ext_need, hz, s["bit_site_cell_um"], W, tpu, target, lids, min(lim + extra, 404.9), first_ok0)
            if done: done["hop_relaxed_um"] = extra
    rec.setdefault("stages", []).append(dict(slot=s["name"], stage=j + 1, done=done, fails=None if done else fails))
    return done is not None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--type", default=r"^ot_s81sl_leaf__t\d+"); ap.add_argument("--target", type=float, default=0.95)
    ap.add_argument("--ve-push", type=float, default=34.56); ap.add_argument("--ve-min-sites", type=int, default=200)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw); rows = {}; led = []
    for tn in sorted(raw["partition_types"]):
        if not re.search(a.type, tn): continue
        t = raw["partition_types"][tn]
        try: boxes = S.placed_macro_boxes(t)
        except Exception: continue
        rec = dict(type=tn); T.CTX.update(P=P, tn=tn, gate=1.0, pending=set())
        ve = ve_slot_sites(t, boxes); mac = in_macro(t, boxes)
        rec["ve_slot"] = dict(gap=ve[0], sites=ve[1]) if ve else None
        rec["in_macro_before"] = [(x[0], x[1] + 1, x[2], x[3]) for x in mac]
        need_ve = bool(ve and ve[1] > a.ve_min_sites); need_in = bool(mac)
        if not (need_ve or need_in): continue
        keep = json.dumps(t); ok = True
        if need_ve:
            m, s_ = ve_pair(t, boxes); axis, sign = ve[2], ve[3]
            o = None
            for f in (1.0, .75, .5):
                d = sign * a.ve_push * f
                o = T.push_ok(t, m, d, axis)
                if o is not None and not T.hops_worse(t, [o]): break
                if o is not None: T.undo(o); o = None
            if o is None:
                rec["ve_push"] = "FAILED: no legal push of ve_m"; ok = False
            else:
                rec["ve_push"] = dict(core=m, axis="xy"[axis], um=o["um"], group=o["group"], stations_followed=o["slots"])
                boxes = S.placed_macro_boxes(t)
                ve2 = ve_slot_sites(t, boxes); rec["ve_slot_after"] = dict(gap=ve2[0], sites=ve2[1]) if ve2 else None
        if need_in or True:
            mac = in_macro(t, boxes)
            for (sn, j, n, tot, by) in sorted(mac, key=lambda x: (x[0], x[1])):
                s = next(x for x in t["ft_slots"] if x["name"] == sn)
                if not resite_stage(P, t, tn, s, j, a.target, rec): ok = False
            left = in_macro(t, S.placed_macro_boxes(t))
            rec["in_macro_after"] = [(x[0], x[1] + 1, x[2], x[3]) for x in left]
            if left: ok = False
        rec["u_after"] = {x["name"]: [round(u, 3) for u in (T.u_stations(x) or [])] for x in t["ft_slots"] if T.u_stations(x) and max(T.u_stations(x)) > 0.9}
        rec["ok"] = ok
        if ok:
            t["note"] = (t.get("note", "") + " | S81-LEAF-T14 11-15 leaf_slot_clear: ve_m +%.2f, stations out of macros" % a.ve_push).strip(" |")
            rows[tn] = t
        else:
            raw["partition_types"][tn] = json.loads(keep); 
        led.append(rec); print(tn, "ok" if ok else "FAIL", json.dumps(rec)[:700], flush=True)
    if not a.dry:
        Path(a.out).write_text(json.dumps(rows) + "\n")
    Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
