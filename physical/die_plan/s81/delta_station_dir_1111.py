#!/usr/bin/env python3
"""DIE-S81-85 11-11 STATION-DIR-1111: S81 out-bus station chains written face -> core (COORD S7 class, KV phyrev).

PLAN-ROUTE-1's station lint (tools/die_plan/station_lint.py, claude/plan-route-6-1111 c0550f9c3d05) finds 68 INVERTED
internal_stations chains in 29 S81 types on 64eb2c89 (and the same 68 on BASE_1200 b5faa1bacc5f): the col_h9/h10 r0_p*
frame_int_o0 relay and the dsdv_slice_*_C leafdn_o* / attn_o0 relays (TYPE-SAFE-2 11-08 "relay ... source stations").
Each is an OUT bus (launch = core pin, capture = 'face flop') whose entry has from_um ON the bus face and regs_um listed
face first.  kit_istations sites out-bus stage k (k-th register after the launch) at regs_um[k] (only a 'face bus'
launch is reversed, KW-FIX-27), so stage 0 lands next to the face and the last stage next to the core: the chain runs
core -> face -> ... -> core -> face (zig-zag) instead of core -> ... -> face.

Fix (as DIE-KV-97 phyrev_1111 ccaf9e17): for every listed chain swap from_um / to_um and reverse regs_um.  The same
register sites, the same count, the same cycles; no RTL, pin, bus, cycle or outline change: EQ by construction.
Chains are found by (type, conn 'bus:<name>'), never by index or coordinates, and whatever regs_um the input carries is
reversed, so the delta also runs AFTER a stage that re-sites internal_stations (CPL-S81-SLICE SLICE-C).  A listed chain
that is missing, ambiguous (two entries on one bus) or not in the inverted form (from_um off the bus face, launch at the
face, capture not the face, or regs_um already core -> face) fails the run; --allow-fixed turns the last case into a
SKIP row instead (an upstream stage already wrote that chain in data order).  CHAINS_SUB adds 7 dsdv_slice_*_C chains of
the same form that the lint reports only NONMONOTONE (2-3 stages, below its 25% INVERTED threshold); --listed-only
applies the 68 alone.

DEPENDENCY (native OUT stations): all 29 types are in the S81 asbuilt internal_stations_types (final_1109
asbuilt_b178_coll_h2_2249_final.json, no bus scope), so every reversed entry is a native OUT entry.  main's
tools/die_plan/native_istations.py (md5 a804c119) reverses every face-captured OUT entry unconditionally and would
re-invert them: native_topology digest a44f20aaed4d39e5 -> 614296bd3febae75 (29 of 30 types change -> rebind).  With
the STATION-FIX-HBM direction-aware native_istations.py (7c4c129b340e or later, md5 57a3d8fd, as KW-FIX-43 overlays
for HBM) the digest is unchanged (a44f20aaed4d39e5 before and after) and the native stations are identical.

The plan text is edited in place: the three JSON values of each entry are swapped / their items reordered in their own
text, so the diff is only those values.  Asserted: nothing outside partition_types changes, unlisted types are equal,
in listed types only from_um / to_um / regs_um of the listed entries change, each as an exact swap + reversal.

usage (any cwd):
  delta_station_dir_1111.py PLAN_IN PLAN_OUT --base-sha SHA256[prefix] [--report R.json] [--allow-fixed] [--listed-only]
      [--check]
  --check: compute and verify everything, write nothing; if PLAN_OUT exists it must be byte-equal to the result."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]
from delta_romq_split_1106 import spans  # noqa: E402

EVENT = "STATION-DIR-1111"
EDGE_TOL = 2.0
# type -> buses (conn 'bus:<name>') whose internal_stations chain is inverted: STATION-LINT-1111 S81 INVERTED rows
CHAINS = {
    "col_h10_r0_p1__t1__cl574cc59d": ("frame_int_o0",),
    "col_h10_r0_p1__t1__cl911743eb": ("frame_int_o0",),
    "col_h10_r0_p4__t1": ("frame_int_o0",),
    "col_h9_r0_p1__t1": ("frame_int_o0",),
    "col_h9_r0_p2__t1__cl0045af7b": ("frame_int_o0",),
    "col_h9_r0_p2__t1__cl9f71e63d": ("frame_int_o0",),
    "col_h9_r0_p3__t1__cl0cd90c0e": ("frame_int_o0",),
    "col_h9_r0_p3__t1__cl31d0dc4b": ("frame_int_o0",),
    "col_h9_r0_p3__t1__cl8ce97bcb": ("frame_int_o0",),
    "col_h9_r0_p4__t1__cl8ef405e8": ("frame_int_o0",),
    "col_h9_r0_p4__t1__clcb2fbfe8": ("frame_int_o0",),
    "col_h9_r0_p5__t1": ("frame_int_o0",),
    "col_h9_r0_p6__t1": ("frame_int_o0",),
    "dsdv_slice_c1x_C__t1": ("leafdn_o0", "leafdn_o1"),
    "dsdv_slice_c1x_C__t10": ("leafdn_o3", "leafdn_o4"),
    "dsdv_slice_c1x_C__t3": ("leafdn_o0", "leafdn_o1", "leafdn_o2", "leafdn_o4"),
    "dsdv_slice_c1x_C__t4": ("leafdn_o3",),
    "dsdv_slice_c1x_C__t5": ("leafdn_o0", "leafdn_o1", "leafdn_o2", "leafdn_o4"),
    "dsdv_slice_c1x_C__t6": ("leafdn_o2", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_c1x_C__t7": ("leafdn_o0", "leafdn_o1", "leafdn_o2"),
    "dsdv_slice_c1x_C__t8": ("leafdn_o0", "leafdn_o1", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_c1x_C__t9": ("leafdn_o0", "leafdn_o1", "leafdn_o2", "leafdn_o4"),
    "dsdv_slice_c3x_C__t1": ("attn_o0", "leafdn_o1", "leafdn_o2", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_iq_C__t1": ("leafdn_o2", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_kv512_C__t1": ("leafdn_o2", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_lepe_mu_C__t1": ("leafdn_o1", "leafdn_o2", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_lepe_nh_mus_C__t1": ("leafdn_o0", "leafdn_o1", "leafdn_o2", "leafdn_o3", "leafdn_o4"),
    "dsdv_slice_lepw_mu_C__t1": ("leafdn_o0", "leafdn_o1", "leafdn_o2"),
    "dsdv_slice_lepw_mus_C__t1": ("leafdn_o0", "leafdn_o1", "leafdn_o2", "leafdn_o3", "leafdn_o4"),
}
# the same class below the lint's INVERTED threshold (stage 0 past the last stage by >= 25% of the face-leaf length):
# 2-3 stage dsdv_slice_*_C relays the lint reports NONMONOTONE "stages step back toward the leaf", distances from the
# face growing from stage 0 (e.g. c1x_C__t4 leafdn_o4 [227, 480]); same TYPE-SAFE-2 writer, same face-first order.
# --listed-only leaves them out.
CHAINS_SUB = {
    "dsdv_slice_c1x_C__t4": ("leafdn_o4",),
    "dsdv_slice_c1x_C__t6": ("leafdn_o1",),
    "dsdv_slice_c1x_C__t8": ("leafdn_o2",),
    "dsdv_slice_iq_C__t1": ("leafdn_o1",),
    "dsdv_slice_kv512_C__t1": ("leafdn_o0", "leafdn_o1"),
    "dsdv_slice_lepe_mu_C__t1": ("leafdn_o0",),
}
CHANGED = ("from_um", "to_um", "regs_um")


def chain_set(listed_only=False):
    """[(type, bus, set)] in plan-independent order: set 'LINT-INVERTED' (the 68) or 'SUB-THRESHOLD'."""
    out = [(tn, b, "LINT-INVERTED") for tn, bs in CHAINS.items() for b in bs]
    if not listed_only:
        out += [(tn, b, "SUB-THRESHOLD") for tn, bs in CHAINS_SUB.items() for b in bs]
    assert len(out) == len(set((t, b) for t, b, _ in out))
    return out


def face_dist(face, W, H, p):
    return {"W": p[0], "E": W - p[0], "S": p[1], "N": H - p[1]}[face]


def _l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def classify(tn, t, bus):
    """(index, entry, state) for the one internal_stations entry on bus:<bus>; state INVERTED / FIXED; raises if the
    entry is missing, ambiguous or not an out-bus core -> face chain."""
    conn = "bus:" + bus
    es = [(i, e) for i, e in enumerate(t.get("internal_stations") or []) if e.get("conn") == conn]
    if len(es) != 1:
        raise SystemExit(f"{EVENT}: {tn} {conn}: {len(es)} internal_stations entries (need exactly 1)")
    i, e = es[0]
    b = next((x for x in t.get("buses") or [] if x.get("name") == bus), None)
    W, H = map(float, t["outline_um"])
    bad = []
    if b is None or b.get("dir") != "out" or b.get("face") not in ("N", "S", "E", "W"):
        bad.append(f"bus {bus} is not an out bus with a face ({b and (b.get('dir'), b.get('face'))})")
    L, C = str(e.get("launch", "")), str(e.get("capture", ""))
    if "face" in L or "face" not in C:
        bad.append(f"launch {L!r} / capture {C!r} is not core -> face")
    if any(k in e for k in ("bit_route", "bit_sites_um", "face_bit_sites_um")):
        bad.append("exact-site / bit_route entry")
    regs = e.get("regs_um") or []
    if len(regs) < 1:
        bad.append("no regs_um")
    if bad:
        raise SystemExit(f"{EVENT}: {tn} {conn}: " + "; ".join(bad))
    face = b["face"]
    fd, td = face_dist(face, W, H, e["from_um"]), face_dist(face, W, H, e["to_um"])
    if fd <= EDGE_TOL and td > EDGE_TOL:
        state = "INVERTED"          # from = face end: written face -> core
        F = e["from_um"]
    elif td <= EDGE_TOL and fd > EDGE_TOL:
        state = "FIXED"             # to = face end: already core -> face
        F = e["to_um"]
    else:
        raise SystemExit(f"{EVENT}: {tn} {conn}: neither from_um {e['from_um']} nor to_um {e['to_um']} alone is on "
                         f"face {face}")
    # the register order must agree with the end labels: regs_um[0] nearer the face end when INVERTED
    if len(regs) >= 2:
        first_near = _l1(regs[0], F) < _l1(regs[-1], F)
        if first_near != (state == "INVERTED"):
            raise SystemExit(f"{EVENT}: {tn} {conn}: regs_um order ({regs[0]} .. {regs[-1]}) disagrees with the "
                             f"from/to labels ({state}, face end {F})")
    return i, e, state


def swap_text(tt, sp, i):
    """the type text with internal_stations[i] from_um <-> to_um and regs_um reversed, each in its own text."""
    base = ("internal_stations", i)
    (fa, fb), (ta, tb), (ra, rb) = sp[base + ("from_um",)], sp[base + ("to_um",)], sp[base + ("regs_um",)]
    n = 0
    items = []
    while base + ("regs_um", n) in sp:
        items.append(sp[base + ("regs_um", n)])
        n += 1
    edits = [(fa, fb, tt[ta:tb]), (ta, tb, tt[fa:fb])]
    rev = [tt[a:b] for a, b in items][::-1]
    edits += [(a, b, s) for (a, b), s in zip(items, rev)]
    assert all(ra <= a and b <= rb for a, b, _ in edits[2:])
    for a, b, s in sorted(edits, reverse=True):
        tt = tt[:a] + s + tt[b:]
    return tt


def apply(text, allow_fixed=False, listed_only=False):
    plan = json.loads(text)
    orig = copy.deepcopy(plan)
    rows, todo = [], {}
    for tn, bus, cset in chain_set(listed_only):
        if tn not in plan["partition_types"]:
            raise SystemExit(f"{EVENT}: listed type {tn} missing from the plan")
        t = plan["partition_types"][tn]
        i, e, state = classify(tn, t, bus)
        row = dict(type=tn, conn="bus:" + bus, set=cset, index=i, regs=len(e["regs_um"]), state=state,
                   from_um_in=e["from_um"], to_um_in=e["to_um"], regs_um_in=e["regs_um"])
        if state == "FIXED":
            if not allow_fixed:
                raise SystemExit(f"{EVENT}: {tn} bus:{bus} is already core -> face (use --allow-fixed to skip)")
            row["action"] = "SKIP"
        else:
            e["from_um"], e["to_um"] = e["to_um"], e["from_um"]
            e["regs_um"] = list(reversed(e["regs_um"]))
            row.update(action="REVERSED", from_um_out=e["from_um"], to_um_out=e["to_um"], regs_um_out=e["regs_um"],
                       wire_um_in=round(chain_len(row["from_um_in"], row["regs_um_in"], row["to_um_in"], True), 1),
                       wire_um_out=round(chain_len(e["from_um"], e["regs_um"], e["to_um"], False), 1))
            todo.setdefault(tn, []).append(i)
        rows.append(row)
    # EQ by construction: only the three values of the listed entries move, each by an exact swap + reversal
    for k in plan:
        if k != "partition_types":
            assert plan[k] == orig[k], k
    assert set(plan["partition_types"]) == set(orig["partition_types"])
    for tn, t in plan["partition_types"].items():
        o = orig["partition_types"][tn]
        if tn not in todo:
            assert t == o, tn
            continue
        assert {k: v for k, v in t.items() if k != "internal_stations"} == \
               {k: v for k, v in o.items() if k != "internal_stations"}, tn
        assert len(t["internal_stations"]) == len(o["internal_stations"]), tn
        for j, (e, f) in enumerate(zip(t["internal_stations"], o["internal_stations"])):
            if j not in todo[tn]:
                assert e == f, (tn, j)
                continue
            assert {k: v for k, v in e.items() if k not in CHANGED} == {k: v for k, v in f.items() if k not in CHANGED}
            assert e["from_um"] == f["to_um"] and e["to_um"] == f["from_um"], (tn, j)
            assert e["regs_um"] == f["regs_um"][::-1] and len(e["regs_um"]) == len(f["regs_um"]), (tn, j)
            assert sorted(map(tuple, e["regs_um"])) == sorted(map(tuple, f["regs_um"])), (tn, j)
    # text edit, last type first so earlier offsets stay valid
    out = text
    top = obj_items(out, 0)
    pa, _ = top["partition_types"]
    types = obj_items(out, pa)
    locs = [(types[tn][0], types[tn][1], tn) for tn in todo]
    for a, b, tn in sorted(locs, reverse=True):
        tt = out[a:b]
        sp = spans(tt)
        for i in sorted(todo[tn], reverse=True):
            tt = swap_text(tt, sp, i)
            sp = spans(tt)
        assert json.loads(tt) == plan["partition_types"][tn], tn
        out = out[:a] + tt + out[b:]
    assert json.loads(out) == plan
    return out, rows


def obj_items(text, i):
    """{key: (value start, value end)} of the JSON object starting at text[i] (one level, values skipped at C speed);
    works on one-line and indented plans alike."""
    dec, ws = json.JSONDecoder(), " \t\r\n"

    def skip(i):
        while text[i] in ws:
            i += 1
        return i

    i = skip(i)
    assert text[i] == "{", text[i:i + 20]
    out = {}
    i = skip(i + 1)
    if text[i] == "}":
        return out
    while True:
        assert text[i] == '"'
        k, i = json.decoder.scanstring(text, i + 1)
        i = skip(i)
        assert text[i] == ":"
        s = skip(i + 1)
        _, e = dec.raw_decode(text, s)
        assert k not in out, k
        out[k] = (s, e)
        i = skip(e)
        if text[i] == "}":
            return out
        assert text[i] == ","
        i = skip(i + 1)


def chain_len(frm, regs, to, face_first):
    """Manhattan wire of the chain as kit_istations sites it: launch (core end) -> regs_um[0] -> ... -> face end."""
    core, face = (to, frm) if face_first else (frm, to)
    pts = [core] + list(regs) + [face]
    return sum(_l1(pts[k], pts[k + 1]) for k in range(len(pts) - 1))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--base-sha", required=True, help="sha256 (or a >= 12 hex prefix) PLAN_IN must have")
    ap.add_argument("--report")
    ap.add_argument("--allow-fixed", action="store_true")
    ap.add_argument("--listed-only", action="store_true", help="only the 68 lint INVERTED chains")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    raw = Path(a.plan_in).read_bytes()
    s_in = sha(raw)
    if len(a.base_sha) < 12 or not s_in.startswith(a.base_sha.lower()):
        raise SystemExit(f"{EVENT}: PLAN_IN sha256 {s_in} != --base-sha {a.base_sha}")
    out, rows = apply(raw.decode(), a.allow_fixed, a.listed_only)
    ob = out.encode()
    s_out = sha(ob)
    per_type = {}
    for r in rows:
        if r["action"] == "REVERSED":
            per_type[r["type"]] = per_type.get(r["type"], 0) + 1
    rep = dict(event=EVENT, plan_in=str(a.plan_in), sha_in=s_in, plan_out=str(a.plan_out), sha_out=s_out,
               reversed=sum(per_type.values()),
               reversed_by_set={k: sum(r["action"] == "REVERSED" and r["set"] == k for r in rows)
                                for k in ("LINT-INVERTED", "SUB-THRESHOLD")},
               skipped=sum(r["action"] == "SKIP" for r in rows),
               types=len(per_type), per_type=per_type,
               wire_um_in=round(sum(r.get("wire_um_in", 0) for r in rows), 1),
               wire_um_out=round(sum(r.get("wire_um_out", 0) for r in rows), 1),
               eq="by construction: same regs sites + count per chain, no RTL/pin/bus/cycle/outline key changed",
               chains=rows)
    if a.check:
        p = Path(a.plan_out)
        if p.exists() and sha(p.read_bytes()) != s_out:
            raise SystemExit(f"{EVENT}: --check: {p} sha256 {sha(p.read_bytes())} != recomputed {s_out}")
        print(f"{EVENT} --check OK: {rep['reversed']} chains in {rep['types']} types, skipped {rep['skipped']}, "
              f"sha_in {s_in[:12]} -> {s_out[:12]}" + (" (PLAN_OUT matches)" if p.exists() else ""))
    else:
        Path(a.plan_out).write_bytes(ob)
        print(f"{EVENT}: {rep['reversed']} chains in {rep['types']} types, skipped {rep['skipped']}, "
              f"wire {rep['wire_um_in']} -> {rep['wire_um_out']} um, sha_in {s_in[:12]} -> {s_out[:12]}")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
