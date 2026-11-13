#!/usr/bin/env python3
"""QC-REGION-1 (COORD 11-13, HOLD-TAP-1 PLAN step 5; R-CLOCK-6 draft): the REGION FORM of a die clock as one plan delta.

    region_form.py regions PLAN OUT_REGIONS.json
    region_form.py model   PLAN REGIONS.json OUTDIR [--v-ps-mm 290]          -> feed.json, ca.json, crossings.tsv
    region_form.py apply   BASE OUT --sidecar SIDE_IN SIDE_OUT --regions R.json --feed F.json --ca CA.json
                           [--report REPORT.json] [--v-ps-mm 290] [--path-prefix plan_of_record/]
    region_form.py sta     PLAN OUT --sidecar SIDE_IN SIDE_OUT --proof DIR [--report R.json] [--ca-out CA.json]
                           [--v-ps-mm 290]     (follow-on delta: K / DEPTH / sched_lat on the BUILT regional clock)
    exit: 0 applied, 2 usage / input error, 3 CONFLICT (nothing written), 4 post-check failed (outputs written, invalid)

REGIONS = the components of the plan's plain-seam graph: a plan port between two real partitions whose id is NOT a
  count-aligned landed crossing (clock.landing_network.count_aligned_cycles) joins its two partitions.  Region name =
  the lexicographically smallest partition name of the component.  No partition is cut, no landing is added.
FEED = locality.py feed 'fwd' (unchanged code): maximum-bit spanning tree of the region crossing graph, rooted at the
  least-eccentric region; a child hangs from a leaf of its parent's balanced H-tree at the bit-weighted crossing point.
  This is the form die_trial --tree-form link_htree --region-trees REGIONS --feed FEED builds (qcreg.sh).
CA RE-PLAN = locality.py v3 on that feed (shared AOCV + droop model, landed_phase_ocv.analyse) -> count_align_plan.py
  (ADOPTED ring math, unchanged): per crossing DEPTH 4/8 and the schedule latency lat = K_eff + 1 (root count frame).
  WALL-ALIGNED FRAME: the regional clock puts region v's leaves f_v = round(leaf arrival TT / T) whole cycles after the
  root (1..19 on QC s28).  The die's count frame stays wall aligned (as under the balanced die tree, where every f_v
  was equal): sched_w = lat + f_dst - f_src (the bind's K + 1 + a'_dst - a'_src with a'_v = a_v + f_v).  sched_w is
  within one cycle of the skew-free physical latency ceil(L/T + 1) on every crossing, so lane cycles, latency groups
  and the token price keep their meaning.
APPLY (one guarded step, row/type-level guards so it composes after any delta that keeps partitions, ports and the
  landed set):
  CONFLICT (3) when: the plan's spine topology is not htree (already applied / other form); the regions, the feed or
  any CA row derived from BASE differ from the committed files (a partition, port, width or landed crossing changed
  upstream); a sidecar landed crossing is missing, is a start-tree port, or its regions do not match the map; the plan
  count_aligned_cycles / sidecar sched_lat / sidecar ports[].added_cycles of a crossing disagree on input.
  Writes: clock.spine.{topology link_htree, region_map, feed, note}; per crossing sidecar count_aligned.ports
  {depth, sched_lat, K} and ports[].added_cycles, plan count_aligned_cycles; latency.lanes recomputed with
  schema.Plan.lane_latency for every lane already in the table.  K absorbs the latency change with the START tree and
  origins kept (K_new = K + sched_new - sched_in, the HEAD k_replan / reach_relay_plan 'K absorbs' convention); the
  START tree, regions[] (PAD), parts and relays are untouched, so a later START-relay step composes (it moves PAD and K
  relative to what it reads).  A crossing marked output_qreg keeps its +1 inside sched_lat.
  POST-CHECK (4): schema.validate error set not larger than BASE's; count_aligned_cycles == sidecar sched_lat ==
  sidecar ports[].added_cycles; every latency.lanes entry == lane_latency; clock_landings.network_lane_cycles OK.
COUNT STRAPS (apply and sta, same step as K / DEPTH; sync_count_straps): types[].count_straps widths follow the new ring
  DEPTH (strap_ca_k_<bus> = log2(DEPTH) + 4 bits of the type's widest copy, count_align_bind.strap_ties; K tied mod
  2^width), existing bits keep their sites_um, a widened strap gets new strap-lattice sites; listed in the report.
K and the START tree are PLAN values (landing_network.physical_qualified stays false): the built regional clock
(qcreg.sh) re-derives them with count_align_plan --sta-proof before any physical adoption.
STA (follow-on delta on a REGION FORM plan, built clock proof DIR = qcreg reg/proof tap_arrivals_{TT,FF}.json):
  the same locality v3 rows (partition endpoints from the plan ports) hulled with die_sta_related.sta_port_intervals
  (count_align_plan --sta-proof --sta-cppr-lca --sta-clock-cell inv2 --start-tree = the sidecar's START form,
  frame from the plan's clock.spine.feed) ->
  per crossing DEPTH / sched_lat in the count frame; K absorbs (K + sched_new - sched_in, origins kept, same frame).
  CONFLICT unless the plan is link_htree with the sidecar in the plan's frame, and plan / sidecar agree on input.
"""
import argparse
import collections
import contextlib
import copy
import hashlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCHEMA = "opentallas.region_form.v1"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def jdump(o):
    return json.dumps(o, indent=1) + "\n"


class Conflict(Exception):
    pass


# ----------------------------------------------------------------------------------------------------- count straps
STRAP_PITCH_UM = 4.32      # count / ID strap pin lattice (head_count_strap_sites: M5, 4.32 um pitch, 4.32 um halo)


def _strap_lattice_free(raw, plan_path, tn, need, taken, cache=None):
    """`need` free interior strap pin sites of type tn on the strap lattice (4.32 um, M5), nearest (Manhattan) to the
    type's strap anchor (landing_ring_bank reserved site / clock tap / outline centre, as head_count_strap_sites placed
    them).  PLAN-ONLY geometry, so the step gives the same answer on every host and needs no staged view: off every
    placed hard_cores[] / contents[] footprint (origin_um + outline_um, rotated for R90-class orients) + 5.4 um (the
    4.32 um macro halo plus half a pin), off clock reserved sites + 1.08 um, and >= 2.16 um from every declared strap
    site and the clock / reset tap points.  The existing strap bits must pass the same rule (else CONFLICT: the rule
    would disagree with the placement it extends).  plan_path / cache: unused (signature kept for callers)."""
    t = raw["partition_types"][tn]
    w, h = t["outline_um"]
    blocked = []
    for c in (t.get("hard_cores") or []) + (t.get("contents") or []):
        if not (c.get("origin_um") and c.get("outline_um")):
            continue
        (x, y), (mw, mh) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ("R90", "R270", "E", "W", "FE", "FW", "MXR90", "MYR90"):
            mw, mh = mh, mw
        blocked.append((x - 5.4, y - 5.4, x + mw + 5.4, y + mh + 5.4))
    clk = t.get("clock") or {}
    for r in clk.get("reserved_sites_um", []):
        x0, y0, x1, y1 = r["rect_um"]
        blocked.append((x0 - 1.08, y0 - 1.08, x1 + 1.08, y1 + 1.08))

    def inside(x, y):
        return any(a <= x <= c and b <= y <= d for a, b, c, d in blocked)
    bad = [xy for xy in taken if inside(*xy)]
    if bad:
        raise Conflict(f"count strap sites {tn}: {len(bad)} declared strap sites sit on a macro / reserved box "
                       f"under the plan-only rule ({bad[:3]})")
    occ = list(taken) + [tuple(p) for p in (clk.get("tap_um"), (t.get("reset") or {}).get("tap_um")) if p]
    anchors = [((r["rect_um"][0] + r["rect_um"][2]) / 2, (r["rect_um"][1] + r["rect_um"][3]) / 2)
               for r in clk.get("reserved_sites_um", []) if r.get("kind") == "landing_ring_bank"]
    ax, ay = anchors[0] if anchors else clk.get("tap_um", [w / 2, h / 2])
    cand = []
    for ix in range(2, int(w / STRAP_PITCH_UM) - 1):
        x = round(ix * STRAP_PITCH_UM, 4)
        for iy in range(2, int(h / STRAP_PITCH_UM) - 1):
            y = round(iy * STRAP_PITCH_UM, 4)
            if not inside(x, y):
                cand.append((abs(x - ax) + abs(y - ay), x, y))
    out = []
    for _d, x, y in sorted(cand):
        if any(abs(x - a) < 2.16 and abs(y - b) < 2.16 for a, b in occ):
            continue
        out.append([x, y])
        occ.append((x, y))
        if len(out) == need:
            return out
    raise Conflict(f"count strap sites {tn}: no room for {need} more strap pins")


def sync_count_straps(raw, ca, plan_path=None):
    """COUNT-STRAP WIDTH follows the re-planned ring (QC-REGION-1 11-13, s29 bind: 'declare count strap
    strap_ca_k_bc_i20[7] in types[].count_straps'): a type's strap_ca_k_<bus> is log2(DEPTH)+4 bits of its widest
    copy (count_align_bind.strap_kw; K is tied mod 2^width, count_align_bind.strap_bits), so a DEPTH change of any ring
    choice (4 -> 8, an allowed 16, a retime) changes the declared width clock_landings requires.  In place on raw
    (the plan written by the same step that wrote K / DEPTH into ca = sidecar count_aligned): every
    types[].count_straps entry is set to count_align_bind.strap_ties(ca, raw) widths; existing bits keep their
    sites_um, a widened strap gets new lattice sites (_strap_lattice_free, plan-only geometry), a narrowed one drops
    its top bits.  The kit RTL ports, die_trial free ports, SDC false paths, pin records and parent ties all size from this declaration.
    No-op without count_aligned.strap_form.  -> [dict(type, strap, old, new, sites_added, sites_dropped)]"""
    if not ca.get("strap_form"):
        return []
    import count_align_bind as CAB
    st = CAB.strap_ties(ca, raw)
    plan_types = raw["partition_types"]
    ledger, grow = [], {}
    for tn, info in sorted(st["types"].items()):
        decl = {x["name"]: x for x in plan_types[tn].get("count_straps") or []}
        for sp, w in sorted(info["straps"].items()):
            x = decl.get(sp)
            if x is None:
                raise Conflict(f"count strap {tn}.{sp}: not declared in types[].count_straps on input "
                               f"(plan not composed in the strap form)")
            if int(x["width"]) == int(w):
                continue
            row = dict(type=tn, strap=sp, old=int(x["width"]), new=int(w), sites_added=[], sites_dropped=[])
            if x.get("sites_um") and w < len(x["sites_um"]):
                row["sites_dropped"] = x["sites_um"][w:]
                x["sites_um"] = x["sites_um"][:w]
            elif x.get("sites_um"):
                grow.setdefault(tn, []).append((x, row))
            x["width"] = int(w)
            ledger.append(row)
    for tn, rows in grow.items():
        t = plan_types[tn]
        taken = [tuple(xy) for sp in (t.get("id_straps") or []) + (t.get("count_straps") or [])
                 for xy in sp.get("sites_um") or []]
        need = sum(x["width"] - len(x["sites_um"]) for x, _ in rows)
        new = _strap_lattice_free(raw, plan_path, tn, need, taken)
        for x, row in rows:
            k = x["width"] - len(x["sites_um"])
            row["sites_added"], new = new[:k], new[k:]
            x["sites_um"] = x["sites_um"] + row["sites_added"]
    st2 = CAB.strap_ties(ca, raw)
    for tn, info in st2["types"].items():
        cs = {x["name"]: int(x["width"]) for x in plan_types[tn].get("count_straps") or []}
        bad = [sp for sp, w in info["straps"].items() if cs.get(sp) != int(w)]
        if bad:
            raise Conflict(f"count strap {tn}: widths still differ after sync: {bad[:4]}")
    return ledger


def strap_summary(ledger):
    c = collections.Counter((r["old"], r["new"]) for r in ledger)
    return dict(straps=len(ledger), types=len({r["type"] for r in ledger}),
                widened=sum(r["new"] > r["old"] for r in ledger), narrowed=sum(r["new"] < r["old"] for r in ledger),
                width_change={f"{a}->{b}": n for (a, b), n in sorted(c.items())})


# ----------------------------------------------------------------------------------------------------------- regions
def plain_regions(raw):
    """{partition: region} = plain-seam components; region = min partition name of the component"""
    parts = [p["name"] for p in raw["partitions"]]
    ps = set(parts)
    landed = set(raw["clock"]["landing_network"].get("count_aligned_cycles", {}))
    up = {p: p for p in parts}

    def f(x):
        while up[x] != x:
            up[x] = up[up[x]]
            x = up[x]
        return x
    for pr in raw["ports"]:
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s in ps and d in ps and s != d and pr["id"] not in landed:
            up[f(s)] = f(d)
    comp = collections.defaultdict(list)
    for p in parts:
        comp[f(p)].append(p)
    name = {r: min(m) for r, m in comp.items()}
    return {p: name[f(p)] for p in parts}


def regions_doc(raw, plan_bytes):
    pr = plain_regions(raw)
    sizes = collections.Counter(collections.Counter(pr.values()).values())
    return dict(part_region=pr, schema=SCHEMA + ".regions",
                source="plain-seam components of plan ports not in clock.landing_network.count_aligned_cycles "
                       "(region = min partition name); region_form.py",
                regions=len(set(pr.values())), sizes={str(k): sizes[k] for k in sorted(sizes)},
                landed_ports=len(raw["clock"]["landing_network"].get("count_aligned_cycles", {})),
                plan_sha256_16=sha(plan_bytes)[:16])


# ------------------------------------------------------------------------------------------------------------- model
def model(plan_path, part_region, v=290.0):
    """(feed doc, ca doc, crossing rows) of the link feed on this region map (locality v3 + count_align_plan)."""
    import locality as LO
    import count_align_plan as CAP
    import tempfile
    D = LO.load_plan(plan_path)
    reg = dict(part_region)
    with contextlib.redirect_stderr(io.StringIO()):
        S = LO.score(D, reg, v, "fwd")
        R = S["crossings"]
        summ = LO.cap_reading(R, D["period"])
    rows = LO.cap_corner_rows(R)
    with tempfile.TemporaryDirectory() as td:
        fi, fo = Path(td) / "in.json", Path(td) / "out.json"
        fi.write_text(json.dumps(dict(corners={c: dict(all=rows[c]) for c in rows})))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            CAP.main([str(fi), "--corner", ",".join(rows), "--period", str(D["period"]), "--aperture",
                      str(D["period"] / 8), "--wander-frac", "0.05", "--out", str(fo)])
        cap = json.loads(fo.read_text())
    Tr, _ = LO.arrivals(S["G"], S["F"], v)
    leaf = {r: Tr[r] + LO.ins(S["G"][r], v) for r in Tr}
    frame = {r: int(round(leaf[r] / D["period"])) for r in Tr}
    feed = dict(S["feed"], schema=SCHEMA + ".feed", form="fwd", v_ps_mm=v, frame="wall_aligned",
                frame_offset=dict(sorted(frame.items())),
                leaf_arrival_tt_ps={r: round(x, 1) for r, x in sorted(leaf.items())})
    byp = {x["port"]: x for x in cap["crossings"]}
    ports = {}
    for r in R:
        x = byp[str(r["id"])]
        if not r["depth"]:
            raise Conflict(f"crossing {r['id']} FAILS the CA ring even at DEPTH 8 on the link feed")
        ports[str(r["id"])] = dict(src_region=r["ra"], dst_region=r["rb"], width=r["width"], depth=r["depth"],
                                   lat=r["lat"], phys=r["phys"], sched_w=r["lat"] + frame[r["rb"]] - frame[r["ra"]],
                                   K_model=(x.get("rtl") or {}).get("K"), m_lo=r["m_lo"], m_hi=r["m_hi"],
                                   on_feed=bool(r["on_feed"]), tree_hops=r["tree_hops"])
    sw = collections.Counter(p["sched_w"] for p in ports.values())
    ca = dict(schema=SCHEMA + ".ca", period_ps=D["period"], v_ps_mm=v, feed="fwd", frame="wall_aligned",
              summary=dict({k: summ[k] for k in ("crossings", "depth4", "depth8", "fail", "worst_margin_lo_ps",
                                                 "worst_margin_hi_ps", "lat_hist", "phys_hist", "max_phys", "min_lat")},
                           sched_w_hist={str(k): sw[k] for k in sorted(sw)}, regions=len(Tr),
                           feed_root=S["feed"]["root"], start_tree_edges_clean=cap["summary"].get("tree_edges_clean"),
                           frame_offset_max=max(frame.values())),
              ports=dict(sorted(ports.items())))
    return feed, ca


def ca_key(c):
    return {p: (x["src_region"], x["dst_region"], x["width"], x["depth"], x["sched_w"]) for p, x in c["ports"].items()}


def feed_key(f):
    return (f["root"], f["parent"], f["tap"], f["joined"], f["frame_offset"])


# ------------------------------------------------------------------------------------------------------------- apply
def lane_table(raw, lids):
    import schema as S
    P = S.Plan(raw)
    out = {}
    for lid in lids:
        d = P.lane_latency(lid)
        out[lid] = d
    return out


def merge_lane(old, d):
    n = {k: d[k] for k in ("cycles", "stations", "boundary", "faces", "fixed", "natural", "pad") if k in d}
    for k in ("clock_landing", "beats", "word_cycles"):
        if k in d:
            n[k] = d[k]
    if "param" in old:
        n["param"] = old["param"]
    return n


def validate_errs(raw):
    import schema as S
    return set(S.validate(raw))


def apply(base_path, out_path, side_in, side_out, reg_path, feed_path, ca_path, v=290.0, prefix="plan_of_record/",
          report=None):
    btext = Path(base_path).read_bytes()
    raw = json.loads(btext)
    side = json.loads(Path(side_in).read_bytes())
    regd = json.loads(Path(reg_path).read_bytes())
    feedd = json.loads(Path(feed_path).read_bytes())
    cad = json.loads(Path(ca_path).read_bytes())
    bad = []
    sp = raw["clock"].get("spine", {})
    if sp.get("topology", "htree") != "htree":
        raise Conflict(f"clock.spine.topology is {sp.get('topology')!r}, not htree (already applied or another form)")
    net = raw["clock"]["landing_network"]
    if net.get("data_cycles_per_crossing") != "count_aligned" or net.get("count_aligned_mixed"):
        raise Conflict("landing network is not the whole-network count-aligned form")
    pr = plain_regions(raw)
    if pr != regd["part_region"]:
        diff = sorted(p for p in set(pr) | set(regd["part_region"]) if pr.get(p) != regd["part_region"].get(p))
        raise Conflict(f"region map differs from {reg_path} on {len(diff)} partitions: {diff[:6]}")
    feed, ca = model(base_path, pr, v)
    if feed_key(feed) != feed_key(feedd):
        raise Conflict(f"feed derived from the plan differs from {feed_path}")
    k0, k1 = ca_key(ca), ca_key(cad)
    if k0 != k1:
        diff = sorted(p for p in set(k0) | set(k1) if k0.get(p) != k1.get(p))
        raise Conflict(f"CA re-plan derived from the plan differs from {ca_path} on {len(diff)} crossings: "
                       f"{[(p, k1.get(p), k0.get(p)) for p in diff[:4]]}")
    sca = side.get("count_aligned") or {}
    sports = sca.get("ports", {})
    cac = net["count_aligned_cycles"]
    if set(sports) != set(cac) or set(cac) != set(ca["ports"]):
        raise Conflict(f"landed sets differ: sidecar {len(sports)} plan {len(cac)} model {len(ca['ports'])}")
    rows = {r["port"]: r for r in side.get("ports", [])}
    # sidecar regions must group partitions exactly as the map (names may differ)
    s2m = {}
    for r in side.get("ports", []):
        for e, re_ in (("src", "src_region"), ("dst", "dst_region")):
            m = pr.get(r[e])
            if m is None or s2m.setdefault(r[re_], m) != m:
                bad.append(f"sidecar region {r[re_]} ({r[e]}) is not map region {m} / {s2m.get(r[re_])}")
    for p, c in sports.items():
        m = ca["ports"][p]
        if c.get("tree"):
            bad.append(f"{p}: start-tree crossing (tree true) is not re-planned here")
        if int(cac[p]) != int(c["sched_lat"]):
            bad.append(f"{p}: plan count_aligned_cycles {cac[p]} != sidecar sched_lat {c['sched_lat']}")
        r = rows.get(p)
        if r is None or int(r.get("added_cycles", -99)) != int(c["sched_lat"]):
            bad.append(f"{p}: sidecar ports[] added_cycles {None if r is None else r.get('added_cycles')} != sched_lat")
        elif (pr[r["src"]], pr[r["dst"]]) != (m["src_region"], m["dst_region"]):
            bad.append(f"{p}: regions {pr[r['src']]}->{pr[r['dst']]} != model {m['src_region']}->{m['dst_region']}")
    if bad:
        raise Conflict(f"{len(bad)} rows: " + " | ".join(bad[:8]))
    if sca.get("frame"):
        raise Conflict(f"sidecar already carries count frame {sca['frame'].get('frame')}")
    import count_frame as CF
    fr = CF.Frame("wall_aligned", feedd["frame_offset"], regd["part_region"], prefix + Path(feed_path).name,
                  sha(Path(feed_path).read_bytes()), sha(Path(reg_path).read_bytes()))
    # ---- write
    out = copy.deepcopy(raw)
    s2 = copy.deepcopy(side)
    ledger = []
    for p in sorted(sports):
        c = s2["count_aligned"]["ports"][p]
        m = ca["ports"][p]
        new = int(m["sched_w"]) + (1 if c.get("output_qreg") else 0) + (1 if c.get("freg") else 0)
        old = int(c["sched_lat"])
        # K absorbs in the COUNT FRAME (count_frame.py): K + 1 + N'_dst - N'_src = sched_w with N' = N + f and the
        # input origins N kept (input sidecar: balanced tree, every f equal) -> K_new = K + (new - old) - shift
        x = fr.shift(rows[p]["src"], rows[p]["dst"])
        ledger.append(dict(port=p, old=old, new=new, depth_old=int(c["depth"]), depth_new=int(m["depth"]),
                           K_old=int(c["K"]), K_new=int(c["K"]) + new - old - x, frame_shift=x))
        c["K"] = int(c["K"]) + new - old - x
        c["sched_lat"] = new
        c["depth"] = int(m["depth"])
        out["clock"]["landing_network"]["count_aligned_cycles"][p] = new
    for r in s2.get("ports", []):
        if r["port"] in sports:
            r["added_cycles"] = s2["count_aligned"]["ports"][r["port"]]["sched_lat"]
    s2["count_aligned"]["frame"] = fr.meta()
    straps = sync_count_straps(out, s2["count_aligned"], base_path)
    note = (f"QC-REGION-1 REGION FORM: link_htree feed (root {feed['root']}), wall-aligned frame; K / DEPTH / "
            f"sched_lat re-planned on {len(ledger)} crossings (K absorbs, START tree kept)")
    s2["note"] = (s2.get("note", "") + " | " + note).lstrip(" |")
    rsha, fsha = sha(Path(reg_path).read_bytes()), sha(Path(feed_path).read_bytes())
    out["clock"]["spine"] = dict(out["clock"].get("spine", {}), topology="link_htree",
                                 region_map=dict(path=prefix + Path(reg_path).name, sha256=rsha[:16],
                                                 regions=regd.get("regions", len(set(pr.values())))),
                                 feed=dict(path=prefix + Path(feed_path).name, sha256=fsha[:16], root=feed["root"],
                                           form="fwd", frame="wall_aligned"),
                                 note=note + f"; CA table {prefix + Path(ca_path).name} "
                                             f"{sha(Path(ca_path).read_bytes())[:16]}")
    old_tab = raw.get("latency", {}).get("lanes", {})
    before = lane_table(raw, list(old_tab))
    stale_in = sorted(l for l in old_tab if merge_lane(old_tab[l], before[l]) != old_tab[l])
    after = lane_table(out, list(old_tab))
    lanes = []
    for lid in sorted(old_tab):
        n = merge_lane(old_tab[lid], after[lid])
        if n != old_tab[lid]:
            lanes.append(dict(lane=lid, old=old_tab[lid].get("cycles"), new=n["cycles"],
                              old_landing=old_tab[lid].get("clock_landing", 0), new_landing=n.get("clock_landing", 0)))
        out["latency"]["lanes"][lid] = n
    otext = jdump(out)
    stext = jdump(s2)
    Path(out_path).write_text(otext)
    Path(side_out).write_text(stext)
    # ---- post-check
    post = []
    chk = json.loads(otext)
    e0, e1 = validate_errs(raw), validate_errs(chk)
    if e1 - e0:
        post.append(f"schema: {len(e1 - e0)} new errors: {sorted(e1 - e0)[:4]}")
    sc = json.loads(stext)["count_aligned"]["ports"]
    cc = chk["clock"]["landing_network"]["count_aligned_cycles"]
    if any(int(cc[p]) != int(sc[p]["sched_lat"]) for p in sc):
        post.append("count_aligned_cycles != sidecar sched_lat")
    if any(int(r["added_cycles"]) != int(sc[r["port"]]["sched_lat"]) for r in json.loads(stext)["ports"] if r["port"] in sc):
        post.append("sidecar ports[].added_cycles != sched_lat")
    import clock_landings as CL
    try:
        CL.network_lane_cycles(chk)
    except Exception as ex:  # noqa: BLE001
        post.append(f"network_lane_cycles: {ex}")
    re_ = lane_table(chk, list(old_tab))
    if any(merge_lane(chk["latency"]["lanes"][l], re_[l]) != chk["latency"]["lanes"][l] for l in old_tab):
        post.append("latency.lanes not equal to lane_latency")
    if any(chk["latency"]["lanes"][l]["cycles"] < 1 for l in old_tab):
        post.append("lane with cycles < 1")
    dh = collections.Counter(x["new"] - x["old"] for x in ledger)
    summ = dict(crossings=len(ledger), changed=sum(x["new"] != x["old"] for x in ledger),
                cycles_old=sum(x["old"] for x in ledger), cycles_new=sum(x["new"] for x in ledger),
                delta_hist={str(k): dh[k] for k in sorted(dh)},
                depth_new={str(k): v for k, v in sorted(collections.Counter(x["depth_new"] for x in ledger).items())},
                depth_changed=sum(x["depth_new"] != x["depth_old"] for x in ledger),
                lanes_changed=len(lanes), lane_cycles_old=sum(x["old"] for x in lanes),
                lane_cycles_new=sum(x["new"] for x in lanes), lane_table_stale_on_input=len(stale_in),
                count_straps=strap_summary(straps), ca=ca["summary"])
    rep = dict(schema=SCHEMA + ".report", base=dict(path=str(base_path), sha256=sha(btext)),
               out=dict(path=str(out_path), sha256=sha(otext.encode())),
               side_in=sha(Path(side_in).read_bytes()), side_out=sha(stext.encode()),
               regions=rsha, feed=fsha, ca=sha(Path(ca_path).read_bytes()), summary=summ, post_check=post,
               stale_lanes_on_input=stale_in[:50], ports=ledger, lanes=lanes, count_straps=straps)
    if report:
        Path(report).write_text(jdump(rep))
    return rep


# s29 ring choice (DIE-QC-100 11-13): on a clock START sidecar the sta step retimes unclean START edges (retime flops on
# ancestor tap nodes, lift into mesh regions) so every crossing fits at DEPTH <= 8 (s29reg: 2525/2525, +343 crossing
# cycles) instead of DEPTH-16 rings (2521/2525, +907).  --no-start-retime = the plain clock START tree; the COORD
# DEPTH-16 allow-list stays an opt-in count_align_plan option (--cap-arg=--depth16-allow --cap-arg=FILE).
START_RETIME = ("--start-retime-up", "--start-lift")


def sta(base_path, out_path, side_in, side_out, proof, v=290.0, report=None, ca_out=None, cap_args=(),
        start_retime=True):
    import count_frame as CF
    import locality as LO
    import count_align_plan as CAP
    import tempfile
    btext = Path(base_path).read_bytes()
    raw = json.loads(btext)
    side = json.loads(Path(side_in).read_bytes())
    sp = raw["clock"].get("spine", {})
    if sp.get("topology") != "link_htree":
        raise Conflict(f"clock.spine.topology {sp.get('topology')!r}: apply the REGION FORM first")
    fr = CF.load(raw, base_path)
    sca = side.get("count_aligned") or {}
    try:
        CF.check_same(sca.get("frame"), fr, "sidecar")
    except CF.FrameError as ex:
        raise Conflict(str(ex))
    # the START form of the re-derivation is the sidecar's: a clock START tree is never re-planned on data crossings
    # (a data START tree on the STA hull turns sync-ambiguous tree edges into multi-cycle path ambiguity, s28: 117 fails)
    start_form = sca.get("start_tree") or "data"
    if start_form not in ("data", "clock"):
        raise Conflict(f"sidecar count_aligned.start_tree {start_form!r} not data / clock")
    pr = plain_regions(raw)
    if pr != fr.part_region:
        raise Conflict("plan regions differ from the frame's region map")
    retime = [x for x in START_RETIME if x not in cap_args] if start_retime and start_form == "clock" else []
    D = LO.load_plan(base_path)
    with contextlib.redirect_stderr(io.StringIO()):
        S = LO.score(D, dict(pr), v, "fwd")
    rows = LO.cap_corner_rows(S["crossings"])
    pp = {p["id"]: p for p in raw["ports"]}
    for c in rows:
        for r in rows[c]:
            q = pp[r["port"]]
            r["src_part"], r["dst_part"] = q["src"]["part"], q["dst"]["part"]
    with tempfile.TemporaryDirectory() as td:
        fi, fo = Path(td) / "in.json", Path(td) / "out.json"
        fi.write_text(json.dumps(dict(corners={c: dict(all=rows[c]) for c in rows})))
        so = io.StringIO()
        with contextlib.redirect_stdout(so):
            rc = CAP.main([str(fi), "--corner", ",".join(rows), "--period", str(D["period"]), "--aperture",
                           str(D["period"] / 8), "--wander-frac", "0.05", "--sta-proof", str(proof), "--sta-plan",
                           str(base_path), "--sta-cppr-lca", "--sta-clock-cell", "inv2", "--start-tree", start_form,
                           "--out", str(fo)] + retime + list(cap_args))
        cap = json.loads(fo.read_text())
    if ca_out:
        Path(ca_out).write_text(json.dumps(cap, indent=0) + "\n")
    xs = {o["port"]: o for o in cap["crossings"]}
    cac = raw["clock"]["landing_network"]["count_aligned_cycles"]
    sports = sca["ports"]
    if set(cac) != set(sports) or set(sports) - set(xs):
        raise Conflict(f"landed sets differ: plan {len(cac)} sidecar {len(sports)} sta {len(xs)}")
    fail = sorted(p for p in sports if not xs[p].get("depth"))
    bad = [f"{p}: plan {cac[p]} != sidecar {c['sched_lat']}" for p, c in sports.items() if int(cac[p]) != int(c["sched_lat"])]
    if bad:
        raise Conflict(f"{len(bad)} rows: " + " | ".join(bad[:6]))
    out, s2, ledger = copy.deepcopy(raw), copy.deepcopy(side), []
    for p in sorted(sports):
        c, x = s2["count_aligned"]["ports"][p], xs[p]
        if not x.get("depth"):
            continue
        new = int(x["lat_cycles"]) + (1 if c.get("output_qreg") else 0) + (1 if c.get("freg") else 0)
        old = int(c["sched_lat"])
        ledger.append(dict(port=p, old=old, new=new, depth_old=int(c["depth"]), depth_new=int(x["depth"]),
                           K_old=int(c["K"]), K_new=int(c["K"]) + new - old, frame_shift=x.get("frame_shift"),
                           m_lo=x.get("margin_lo_ps"), m_hi=x.get("margin_hi_ps")))
        c["K"], c["sched_lat"], c["depth"] = int(c["K"]) + new - old, new, int(x["depth"])
        out["clock"]["landing_network"]["count_aligned_cycles"][p] = new
    for r in s2.get("ports", []):
        if r["port"] in sports:
            r["added_cycles"] = s2["count_aligned"]["ports"][r["port"]]["sched_lat"]
    straps = sync_count_straps(out, s2["count_aligned"], base_path)
    note = f"QC-REGION-1 STA: K / DEPTH / sched_lat on the built regional clock proof {proof} ({len(ledger)} crossings)"
    s2["note"] = (s2.get("note", "") + " | " + note).lstrip(" |")
    old_tab = raw.get("latency", {}).get("lanes", {})
    after = lane_table(out, list(old_tab))
    lanes = []
    for lid in sorted(old_tab):
        n = merge_lane(old_tab[lid], after[lid])
        if n != old_tab[lid]:
            lanes.append(dict(lane=lid, old=old_tab[lid].get("cycles"), new=n["cycles"]))
        out["latency"]["lanes"][lid] = n
    otext, stext = jdump(out), jdump(s2)
    post = [f"{len(fail)} crossings FAIL the CA ring on the built clock: {fail[:6]}"] if fail else []
    if rc != 0 and not fail:
        post.append(f"count_align_plan rc {rc} (start tree not spanning / start fail)")
    Path(out_path).write_text(otext)
    Path(side_out).write_text(stext)
    chk = json.loads(otext)
    e0, e1 = validate_errs(raw), validate_errs(chk)
    if e1 - e0:
        post.append(f"schema: {len(e1 - e0)} new errors: {sorted(e1 - e0)[:4]}")
    import clock_landings as CL
    try:
        CL.network_lane_cycles(chk)
    except Exception as ex:  # noqa: BLE001
        post.append(f"network_lane_cycles: {ex}")
    if any(chk["latency"]["lanes"][l]["cycles"] < 1 for l in old_tab):
        post.append("lane with cycles < 1")
    dh = collections.Counter(x["new"] - x["old"] for x in ledger)
    summ = dict(crossings=len(ledger), fail=len(fail), changed=sum(x["new"] != x["old"] for x in ledger),
                K_changed=sum(x["K_new"] != x["K_old"] for x in ledger),
                cycles_old=sum(x["old"] for x in ledger), cycles_new=sum(x["new"] for x in ledger),
                delta_hist={str(k): dh[k] for k in sorted(dh)},
                depth_new={str(k): v for k, v in sorted(collections.Counter(x["depth_new"] for x in ledger).items())},
                depth_changed=sum(x["depth_new"] != x["depth_old"] for x in ledger),
                lanes_changed=len(lanes), lane_cycles_old=sum(x["old"] for x in lanes),
                lane_cycles_new=sum(x["new"] for x in lanes),
                worst_margin_lo_ps=cap["summary"].get("worst_margin_lo_ps"),
                worst_margin_hi_ps=cap["summary"].get("worst_margin_hi_ps"),
                below_100ps=cap["summary"].get("below_100ps"), sta_interval=cap["summary"].get("sta_interval"),
                start_retime=retime, count_straps=strap_summary(straps))
    rep = dict(schema=SCHEMA + ".sta_report", base=dict(path=str(base_path), sha256=sha(btext)),
               out=dict(path=str(out_path), sha256=sha(otext.encode())), side_in=sha(Path(side_in).read_bytes()),
               side_out=sha(stext.encode()), proof=str(proof), summary=summ, post_check=post, ports=ledger,
               lanes=lanes, count_straps=straps)
    if report:
        Path(report).write_text(jdump(rep))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("regions")
    a.add_argument("plan")
    a.add_argument("out")
    m = sub.add_parser("model")
    m.add_argument("plan")
    m.add_argument("regions")
    m.add_argument("outdir")
    m.add_argument("--v-ps-mm", type=float, default=290.0)
    p = sub.add_parser("apply")
    p.add_argument("base")
    p.add_argument("out")
    p.add_argument("--sidecar", nargs=2, required=True, metavar=("SIDE_IN", "SIDE_OUT"))
    p.add_argument("--regions", required=True)
    p.add_argument("--feed", required=True)
    p.add_argument("--ca", required=True)
    p.add_argument("--report")
    p.add_argument("--v-ps-mm", type=float, default=290.0)
    p.add_argument("--path-prefix", default="plan_of_record/")
    t = sub.add_parser("sta")
    t.add_argument("base")
    t.add_argument("out")
    t.add_argument("--sidecar", nargs=2, required=True, metavar=("SIDE_IN", "SIDE_OUT"))
    t.add_argument("--proof", required=True)
    t.add_argument("--report")
    t.add_argument("--ca-out")
    t.add_argument("--cap-arg", action="append", default=[], metavar="ARG",
                   help="extra count_align_plan argument (e.g. --start-retime-up), repeatable")
    t.add_argument("--v-ps-mm", type=float, default=290.0)
    t.add_argument("--no-start-retime", action="store_true",
                   help="clock START sidecar: plain START tree (default: " + " ".join(START_RETIME) + ")")
    a = ap.parse_args(argv)
    if a.cmd == "sta":
        try:
            rep = sta(a.base, a.out, a.sidecar[0], a.sidecar[1], a.proof, a.v_ps_mm, a.report, a.ca_out, a.cap_arg,
                      start_retime=not a.no_start_retime)
        except Conflict as ex:
            print(f"CONFLICT {ex}")
            return 3
        print(json.dumps(dict(out=rep["out"]["sha256"][:12], side=rep["side_out"][:12], **rep["summary"]), default=str))
        if rep["post_check"]:
            print("POST-CHECK FAIL: " + " | ".join(rep["post_check"]))
            return 4
        print("POST-CHECK PASS")
        return 0
    if a.cmd == "regions":
        b = Path(a.plan).read_bytes()
        d = regions_doc(json.loads(b), b)
        Path(a.out).write_text(jdump(d))
        print(f"regions {d['regions']} sizes {d['sizes']} landed {d['landed_ports']} -> {a.out}")
        return 0
    if a.cmd == "model":
        reg = json.loads(Path(a.regions).read_bytes())["part_region"]
        try:
            feed, ca = model(a.plan, reg, a.v_ps_mm)
        except Conflict as ex:
            print(f"FAIL {ex}")
            return 4
        o = Path(a.outdir)
        o.mkdir(parents=True, exist_ok=True)
        (o / "feed.json").write_text(jdump(feed))
        (o / "ca.json").write_text(jdump(ca))
        with open(o / "crossings.tsv", "w") as fh:
            cols = ("src_region", "dst_region", "width", "on_feed", "tree_hops", "depth", "lat", "phys", "sched_w",
                    "K_model", "m_lo", "m_hi")
            fh.write("port\t" + "\t".join(cols) + "\n")
            for pid, x in ca["ports"].items():
                fh.write(pid + "\t" + "\t".join(str(x[c]) for c in cols) + "\n")
        print(json.dumps(ca["summary"]))
        return 0
    try:
        rep = apply(a.base, a.out, a.sidecar[0], a.sidecar[1], a.regions, a.feed, a.ca, a.v_ps_mm, a.path_prefix,
                    a.report)
    except Conflict as ex:
        print(f"CONFLICT {ex}")
        return 3
    print(json.dumps(dict(out=rep["out"]["sha256"][:12], side=rep["side_out"][:12], **{k: rep["summary"][k] for k in (
        "crossings", "changed", "cycles_old", "cycles_new", "depth_new", "lanes_changed", "lane_cycles_old",
        "lane_cycles_new", "lane_table_stale_on_input", "count_straps")})))
    if rep["post_check"]:
        print("POST-CHECK FAIL: " + " | ".join(rep["post_check"]))
        return 4
    print("POST-CHECK PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
