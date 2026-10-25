#!/usr/bin/env python3
"""PATH-HBM/ROOTPACK option R1-302.4 (COORD ruling 2026-10-25 11:31): root E edge +302.4 um (1382.4 -> 1684.8),
4x8 TKM snake, die +302.4 um in x.

    python3 physical/die_plan/hbm_arch/path_hbm_b2p_r1.py --src B2p_base_ids --out B2p_r1 --chain B2p_inputs

Root (type frame 1684.8 x 5356.8, 8.64 lattice), on top of the R3 study (path_hbm_b2p_r3.py):
  * bottom band = the R3 idx/host cluster without the hc row (top = u_host_cp_rxs 976.32); u_hc_eng_hcp_sys1 in the
    band's free E end.
  * root row (y Y0 = band top + TURN): TKM root core at col0; the 6 hc tail cores in one row beside it under cols 1-3.
  * 4x8 snake above it: col0 R0 up tile0..7 (root below tile0), col1 MX down tile8..15, col2 R0 up tile16..23,
    col3 MX down tile24..31 (terminal tile31 at col3 bottom, conv pin facing the root row); cols x 181.44 / 509.76 /
    838.08 / 1166.4; W edge 181.44, E edge 198.72 (each >= 3,625 b at 20.05 b/um).
  * row gaps: L4 corridor after row 3 and L150 corridor after row 6 sized to their bits; the height left over goes to
    the top band (L9/L63 turn to the N windows).
  * die level: every partition with origin x >= the old root E face (all NE_* incl. NE_hub, NE_io) moves +302.4 um;
    the seam-spanning single-instance types (root, vsN0/1/2/4/5/6, PHY_N) grow +302.4 um at their E edge (contents
    unchanged) so every abutment holds; N/S-face port windows, die.io / die.pg rects and die_io.json of moved
    partitions move with them; clock spine root to the new die centre (clock_htree.json NOT regenerated).
Then the R3 sequence: path_hbm_b2p.step_a, conv relay at <= 360 um, non-TKM internal stations with each snake row
group as a blockage, FT slots re-sited (hbm_bit_stations). Corridor needs are MEASURED on the result (max cut over
the routed internal-station + FT-slot polylines per band).
"""
import argparse, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import path_hbm_b2p as PB  # noqa: E402
import path_hbm_b2p_r3 as R3  # noqa: E402

LAT, W_T, H_T = 8.64, 319.68, 345.6
DX = 302.4                       # root E growth = die growth
OLD_W = 1382.4
BPU = R3.BITS_PER_UM             # 20.05 b/um (M5+M7 at 0.55)
COLS = [181.44, 509.76, 838.08, 1166.4]
NROW = 8
L4_AFTER, L150_AFTER = 3, 6      # gap index after row k


def lat_up(v):
    return round(math.ceil(v / LAT - 1e-9) * LAT, 3)


TURN = 34.56                     # band top -> root row
BAND_TOP = 976.32                # u_host_cp_rxs top (544.32 + 432)
NEED = dict(L4=5676, L150=1120, top=2793)   # top: max x-cut of L9x1 (2456) + L63mx1 (336) + conv 1; R3 used 3297
HC_ROW = ["u_hc_eng_tail0_rest", "u_hc_eng_tail0_sk_step0", "u_hc_eng_tail0_sk_steady",
          "u_hc_eng_tail1_rest", "u_hc_eng_tail1_sk_step0", "u_hc_eng_tail1_sk_steady"]
HCP = ("u_hc_eng_hcp_sys1", (1382.4, 34.56))
G = {}


def geometry(turn=TURN, need=NEED):
    yr = lat_up(BAND_TOP + turn)                 # root row
    y0 = round(yr + H_T + LAT, 3)                # snake row 0
    gap = [LAT] * (NROW - 1)
    gap[L4_AFTER], gap[L150_AFTER] = lat_up(need["L4"] / BPU), lat_up(need["L150"] / BPU)
    top = round(5356.8 - (y0 + NROW * H_T + sum(gap)), 3)
    return yr, y0, gap, top


def rows():
    y, out = G["y0"], []
    for i in range(NROW):
        out.append(round(y, 3))
        if i < NROW - 1:
            y += H_T + G["gap"][i]
    return out


def placement():
    R = rows()
    t = []
    for c in range(4):
        for j in range(NROW):
            k = c * NROW + j
            r = j if c % 2 == 0 else NROW - 1 - j
            t.append(dict(inst=f"u_tkm_SW_tile{k}", tile_tid=k, origin_um=[COLS[c], R[r]], orient="R0" if c % 2 == 0 else "MX"))
    return dict(root=dict(inst="u_tkm_SW_root", origin_um=[COLS[0], G["yr"]], orient="R0"), tiles=t,
                note="PATH-HBM/ROOTPACK R1-302.4: root core + 4x8 column snake")


def snake_blocks(R):
    out, start = [], 0
    for i in range(NROW):
        if i == NROW - 1 or G["gap"][i] > LAT + 1e-6:
            y0 = R[start] if start else G["yr"]
            y1 = R[i] + H_T
            out.append((COLS[0], y0, COLS[3] + W_T - COLS[0], round(y1 - y0, 3)))
            start = i + 1
    return out


def conv_path(pr, pt, R):
    """root conv pin (root core N face) -> 4.32 um above it, under snake row 0 -> tile31 (col3 row0, MX: conv pin on
    its S face)."""
    rx, ry = COLS[0] + pr["x"], G["yr"] + H_T
    tx, ty = COLS[3] + pt["x"], R[0]
    y = ry + 4.32
    return [[rx, ry], [rx, y], [tx, y], [tx, ty]]


def configure(turn):
    yr, y0, gap, top = geometry(turn)
    G.update(yr=yr, y0=y0, gap=gap, top=top)
    R3.COLS = COLS
    cl = {k: v for k, v in R3.CLUSTER.items() if not k.startswith("u_hc_eng_")}
    for i, n in enumerate(HC_ROW):
        cl[n] = (round(COLS[1] + i * (155.52 + LAT), 3), yr)
    cl[HCP[0]] = HCP[1]
    R3.CLUSTER = cl
    soft = dict(R3.SOFT)
    soft["u_host_status"] = (1365.12, 924.48)          # off the root-row line (was 984.96..1010.88)
    soft["u_vm_status4"] = (1399.68, 924.48)
    R3.SOFT = soft


# ------------------------------------------------------------------------------------------------ die level
def shift_die(plan, log):
    parts = {q["name"]: q for q in plan["partitions"]}
    rt = parts["root"]
    seam = rt["origin_um"][0] + OLD_W
    moved = sorted(n for n, q in parts.items() if q["origin_um"][0] >= seam - 1e-3)
    for n in moved:
        parts[n]["origin_um"][0] = round(parts[n]["origin_um"][0] + DX, 3)
    grown = []
    for n, q in parts.items():
        t = plan["partition_types"][q["type"]]
        x0, x1 = q["origin_um"][0], q["origin_um"][0] + t["outline_um"][0]
        if n not in moved and x0 < seam - 1e-3 < x1 + 1e-3 and x1 >= seam - 1e-3:
            if sum(1 for r in parts.values() if r["type"] == q["type"]) != 1:
                raise SystemExit(f"seam type {q['type']} has >1 instance")
            t["outline_um"][0] = round(t["outline_um"][0] + DX, 3)
            grown.append(n)
    # ports: N/S windows (die x) of moved partitions move; E/W windows are die y (unchanged)
    nport, bad = 0, []
    for p in plan["ports"]:
        ends = [p["src"]["part"], p["dst"]["part"]]
        mv = [e in moved for e in ends if e in parts]
        if p["face"] in ("N", "S") and any(mv):
            if not all(mv):
                bad.append(p["id"])
            p["window_um"] = [round(v + DX, 4) for v in p["window_um"]]
            nport += 1
    nio = 0

    def mv_rect(r):
        return [round(r[0] + DX, 4), r[1], round(r[2] + DX, 4), r[3]]
    for e in plan["die"]["io"]:
        if e.get("part") in moved:
            e["rect_um"] = mv_rect(e["rect_um"]); nio += 1
    iom = {e["name"] for e in plan["die"]["io"] if e.get("part") in moved}
    for d in plan["die"]["pg"].get("domains", []):
        if set(d.get("io", [])) & iom:
            d["rect_um"] = mv_rect(d["rect_um"])
            if "bumps" in d:
                d["bumps"]["rect_um"] = mv_rect(d["bumps"]["rect_um"])
    W0 = plan["die"]["outline_um"][0]
    plan["die"]["outline_um"][0] = round(W0 + DX, 3)
    sp = plan["clock"].get("spine", {})
    if "root_um" in sp:
        sp["root_um"][0] = round(sp["root_um"][0] + DX / 2, 3)
    log.update(seam_x=seam, moved=moved, grown=grown, ports_shifted=nport, ns_ports_one_end_moved=bad, io_shifted=nio,
               die_w=[W0, plan["die"]["outline_um"][0]], die_h=plan["die"]["outline_um"][1],
               die_area_mm2=[round(W0 * plan["die"]["outline_um"][1] / 1e6, 3),
                             round(plan["die"]["outline_um"][0] * plan["die"]["outline_um"][1] / 1e6, 3)],
               clock_spine_root=sp.get("root_um"), note="clock_htree.json NOT regenerated (die H-tree re-run pending)")
    return set(moved)


def shift_die_io_sidecar(out, moved):
    f = out / "die_io.json"
    if not f.exists():
        return 0
    d = json.load(open(f)); n = 0
    for e in d:
        if e.get("part") in moved:
            r = e["rect_um"]; e["rect_um"] = [round(r[0] + DX, 4), r[1], round(r[2] + DX, 4), r[3]]; n += 1
    json.dump(d, open(f, "w"), indent=1)
    return n


def grow_root_ft(T, xmin=1183.68):  # old E edge strip (R3 frame) and the old E face
    """FT slot points in the old E edge strip / on the old E face move with the E face."""
    n = 0
    for s in T["ft_slots"]:
        regs = s["regs_um"]
        for i, q in enumerate(regs):
            if q[0] >= xmin - 1e-6:
                q[0] = round(q[0] + DX, 4); n += 1
                if s.get("bit_sites_um") and i < len(s["bit_sites_um"]):
                    for b in s["bit_sites_um"][i]:
                        b[0] = round(b[0] + DX, 4)
    return n


# ------------------------------------------------------------------------------------------------ measured corridors
def polylines(T):
    for s in T.get("internal_stations", []):
        yield s["conn"], s.get("bits", 1), [s["from_um"]] + s["regs_um"] + [s["to_um"]]
    for s in T.get("ft_slots", []):
        yield "FT:" + s["name"], s["width"], s["regs_um"]


def hcut(T, y0, y1, xs):
    """max over x in xs of bits whose path crosses the vertical line x inside band y0..y1."""
    best, arg, who = 0, None, {}
    for x in xs:
        tot, w = 0, {}
        for nm, b, pts in polylines(T):
            for a, c in zip(pts, pts[1:]):
                if min(a[0], c[0]) < x <= max(a[0], c[0]):
                    yy = a[1] + (c[1] - a[1]) * (x - a[0]) / (c[0] - a[0])
                    if y0 - 1e-6 <= yy <= y1 + 1e-6:
                        tot += b; w[nm] = b
                        break
        if tot > best:
            best, arg, who = tot, x, w
    return best, arg, sorted(who.items(), key=lambda kv: -kv[1])[:6]


def vcut(T, x0, x1, ys):
    best, arg, who = 0, None, {}
    for y in ys:
        tot, w = 0, {}
        for nm, b, pts in polylines(T):
            for a, c in zip(pts, pts[1:]):
                if min(a[1], c[1]) < y <= max(a[1], c[1]):
                    xx = a[0] + (c[0] - a[0]) * (y - a[1]) / (c[1] - a[1])
                    if x0 - 1e-6 <= xx <= x1 + 1e-6:
                        tot += b; w[nm] = b
                        break
        if tot > best:
            best, arg, who = tot, y, w
    return best, arg, sorted(who.items(), key=lambda kv: -kv[1])[:6]


def corridors(T, R, gap, top_um):
    W, H = T["outline_um"]
    xs = [COLS[0] + 8.64 * k for k in range(0, int((COLS[3] + W_T - COLS[0]) / 8.64) + 1)]
    out = {}

    def row(name, y0, y1, need_plan):
        um = round(y1 - y0, 3)
        m, at, who = hcut(T, y0, y1, xs)
        out[name] = dict(y=[round(y0, 3), round(y1, 3)], um=um, capacity_b=round(um * BPU), need_plan_b=need_plan,
                         need_measured_b=m, at_x=at, top=who,
                         ok=round(um * BPU) >= max(m, need_plan or 0))
    row("bottom_turn", BAND_TOP, G["yr"], None)
    row("root_row_to_row0", G["yr"] + 172.8, R[0], None)
    row("L4_r%dr%d" % (L4_AFTER, L4_AFTER + 1), R[L4_AFTER] + H_T, R[L4_AFTER + 1], NEED["L4"])
    row("L150_r%dr%d" % (L150_AFTER, L150_AFTER + 1), R[L150_AFTER] + H_T, R[L150_AFTER + 1], NEED["L150"])
    row("top_band", R[-1] + H_T, H, NEED["top"])
    out["top_band"]["need_r3_b"] = 3297
    ys = [G["yr"] + 8.64 * k for k in range(0, int((H - G["yr"]) / 8.64))]
    for name, x0, x1, need in (("W_edge", 0.0, COLS[0], 3625), ("E_edge", COLS[3] + W_T, W, 3625)):
        m, at, who = vcut(T, x0, x1, ys)
        narrow = x1 - x0
        out[name] = dict(x=[x0, x1], narrowest_um=round(narrow, 3), capacity_b=round(narrow * BPU), need_plan_b=need,
                         need_measured_b=m, at_y=at, top=who, ok=round(narrow * BPU) >= max(m, need))
    out["horizontal_gap_um_total"] = round(sum(gap), 3)
    return out


def fix_core_taps(T, src_T):
    so = {c["inst"]: c for c in src_T["hard_cores"]}
    HC = {c["inst"]: c for c in T["hard_cores"]}
    n = []
    for tp in T["clock"]["taps"]:
        nm = tp["name"]
        if nm.startswith("u_tkm_SW") or nm not in HC or nm not in so:
            continue
        st = next((t for t in src_T["clock"]["taps"] if t["name"] == nm), None)
        if st is None:
            continue
        off = [st["xy"][0] - so[nm]["origin_um"][0], st["xy"][1] - so[nm]["origin_um"][1]]
        tp["xy"] = [round(HC[nm]["origin_um"][0] + off[0], 3), round(HC[nm]["origin_um"][1] + off[1], 3)]
        n.append(nm)
    return n


# ------------------------------------------------------------------------------------------------ pgslice pretree
PRETREE_M = "ot_hbm_su_static_pgslice_lg__pretree"
PRETREE_W = 164.16               # KITS-SPARE-2/W1 DELTA-REQ: ~150-170 x 457.92 (was 440.64; fill 9.4% -> ~27%)


def pretree_narrow(plan, out, log):
    """pgslice pretree cores 440.64 -> 164.16 x 457.92: same pins on the same faces (E 1024 ro_x unchanged in y; the
    80 tree_o/tree_cmd W pins now next to the logic; S ro_v/clk/rst spread over the narrow S face); the core keeps its
    E (ro_x) face where it was in the partition, so the freed width opens on the far side."""
    import b2n
    import b2o  # noqa: F401
    rows, types = [], []
    for tn, t in plan["partition_types"].items():
        CT = {c["inst"]: c for c in t.get("contents", [])}
        for c in t.get("hard_cores", []):
            if c["module"] != PRETREE_M:
                continue
            w, h = c["outline_um"]
            pins = json.load(open(out / c["pins_file"]))
            npins = b2n._regrow_pins(pins, w, h, PRETREE_W, h)
            nf = f"cores/{PRETREE_M}__{PRETREE_W:g}x{h:g}__{tn}_{c['inst']}.json"
            json.dump(npins, open(out / nf, "w"))
            o = c.get("orient", "R0")
            ox = c["origin_um"][0] + (w - PRETREE_W if o in ("R0", "MX") else 0.0)
            old = (list(c["origin_um"]), [w, h])
            c["origin_um"] = [round(ox, 3), c["origin_um"][1]]
            c["outline_um"] = [PRETREE_W, h]
            c["pins_file"] = nf
            c["note"] = (c.get("note", "") + f" | B2p_r1 KITS-SPARE-2/W1 DELTA-REQ: pretree {w:g}x{h:g} -> "
                         f"{PRETREE_W:g}x{h:g}, E ro_x face kept in place, pins re-spread per face").strip(" |")
            if c["inst"] in CT and "origin_um" in CT[c["inst"]]:
                CT[c["inst"]]["origin_um"] = list(c["origin_um"]); CT[c["inst"]]["outline_um"] = list(c["outline_um"])
            for tp in t.get("clock", {}).get("taps", []):
                if tp["name"] == c["inst"]:
                    tp["xy"] = [round(c["origin_um"][0] + PRETREE_W / 2, 3), round(c["origin_um"][1] + h / 2, 3)]
            rows.append(dict(type=tn, inst=c["inst"], orient=o, frm=old, to=[c["origin_um"], c["outline_um"]], pins=nf))
            types.append(tn)
    ilog = []
    import b2o as B
    fails = B.internal_stations(plan, out, sorted(set(types)), ilog)
    import hbm_bit_stations as HBS
    try:
        fr = HBS.repair(plan, log=lambda m: None, only_types=sorted(set(types)))
    except HBS.RepairFailure as e:
        fr = e.report
    bad = 0
    for tn in set(types):
        t = plan["partition_types"][tn]
        rects = [(c["origin_um"][0], c["origin_um"][1], c["outline_um"][0], c["outline_um"][1]) for c in t["hard_cores"]]
        pts = [q for s in t.get("internal_stations", []) for q in s["regs_um"]]
        pts += [q for s in t.get("ft_slots", []) for q in s["regs_um"]]
        bad += sum(1 for q in pts if any(r[0] < q[0] < r[0] + r[2] and r[1] < q[1] < r[1] + r[3] for r in rects))
    log.update(cores=rows, internal_stations_unroutable=fails, ft_repair=dict(
        checked=fr.get("checked"), added=len(fr.get("added", [])), type_failures=fr.get("type_failures"),
        unfixed=len(fr.get("unfixed", []))), sites_in_hard_cores=bad)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True); ap.add_argument("--out", required=True); ap.add_argument("--chain", required=True)
    ap.add_argument("--turn", type=float, default=TURN, help="cluster top -> snake bottom gap (um)")
    ap.add_argument("--no-ft-repair", action="store_true")
    ap.add_argument("--pretree-only", action="store_true",
                    help="apply only the pgslice pretree narrowing to an existing --out (R1 already built)")
    a = ap.parse_args(argv)
    if a.pretree_only:
        out = Path(a.out)
        plan = json.load(open(out / "die_plan.json"))
        rep = json.load(open(out / "b2p_r1_report.json"))
        rep["pretree"] = {}
        pretree_narrow(plan, out, rep["pretree"])
        import schema as S  # noqa: E402
        P = S.Plan(plan)
        plan["latency"]["lanes"] = {lid: P.lane_latency(lid) for lid in P.lanes}
        json.dump(plan, open(out / "die_plan.json", "w"), indent=1)
        rep["out_plan_sha256"] = PB.sha(out / "die_plan.json")
        json.dump(rep, open(out / "b2p_r1_report.json", "w"), indent=1)
        print(json.dumps(rep["pretree"], indent=0, default=str)[:3000])
        return
    src, out, chain = Path(a.src), Path(a.out), Path(a.chain)
    configure(a.turn)
    yr, y0, gap, top = G["yr"], G["y0"], G["gap"], G["top"]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    cdir = out / "inputs" / "r1_chain"
    cdir.mkdir(parents=True, exist_ok=True)
    for f in chain.iterdir():
        if f.is_file():
            shutil.copyfile(f, cdir / f.name)
    json.dump(placement(), open(cdir / "tkm_chain_placement.json", "w"), indent=1)
    rp = {q["name"]: q for q in json.load(open(chain / f"{PB.ROOT_M}__repin.json"))}
    tp = {q["name"]: q for q in json.load(open(chain / f"{PB.TERM_M}__repin.json"))}
    R = rows()
    cv = json.load(open(chain / "tkm_conv_tree.json"))
    cv["path"] = conv_path(rp["x_u_u_g_tiles_0_e86_u_tile_conv"], tp["tile_conv"], R)
    cv["note"] = "PATH-HBM/ROOTPACK R1-172.8 conv relay: root N gap -> W edge corridor -> top band -> tile31 N conv pin"
    json.dump(cv, open(cdir / "tkm_conv_tree.json", "w"), indent=1)

    plan = json.load(open(out / "die_plan.json"))
    src_T = json.load(open(src / "die_plan.json"))["partition_types"]["root"]
    log = dict(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), pin_files={}, moved=[], soft_moved=[],
               r1=dict(rows=R, cols=COLS, gaps=gap, root_row_y=yr, y0=y0, turn=a.turn, top_band_um=top, cluster=[]))
    dl = {}
    moved = shift_die(plan, dl)
    dl["die_io_sidecar_shifted"] = shift_die_io_sidecar(out, moved)
    log["r1"]["die"] = dl
    T = plan["partition_types"]["root"]
    assert abs(T["outline_um"][0] - (OLD_W + DX)) < 1e-6, T["outline_um"]
    log["r1"]["ft_points_moved_east"] = grow_root_ft(T)
    R3.place_cluster(T, log["r1"]["cluster"])
    T["clock"]["tap_um"] = [round(COLS[0] + (COLS[3] + W_T - COLS[0]) / 2, 3), round(R[L4_AFTER] + H_T + gap[L4_AFTER] / 2, 3)]
    PB.step_a(plan, out, cdir, log)
    log["r1"]["core_taps_moved"] = fix_core_taps(T, src_T)
    HC = {c["inst"]: c for c in T["hard_cores"]}
    CT = {c["inst"]: c for c in T["contents"]}
    tkc = [c for n, c in HC.items() if n.startswith("u_tkm_SW_")]
    x0 = min(c["origin_um"][0] for c in tkc); yy0 = min(c["origin_um"][1] for c in tkc)
    x1 = max(c["origin_um"][0] + c["outline_um"][0] for c in tkc); y1 = max(c["origin_um"][1] + c["outline_um"][1] for c in tkc)
    CT["u_tkm_SW"]["origin_um"] = [x0, yy0]; CT["u_tkm_SW"]["outline_um"] = [round(x1 - x0, 3), round(y1 - yy0, 3)]
    for s in T["internal_stations"]:
        if s["conn"].startswith("u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv"):
            regs, L, pitch = PB.stations_along(cv["path"], 360.0)
            s["regs_um"] = regs
            s["note"] = (f"B2p_r1 PATH-HBM conv relay root -> tile31 (TOKEN CB21): {L:.1f} um, {len(regs)} stations, "
                         f"pitch {pitch:.1f} um <= 360 (root row -> under snake row 0)")
            hops = [abs(b[0] - a_[0]) + abs(b[1] - a_[1]) for a_, b in zip([s["from_um"]] + regs, regs + [s["to_um"]])]
            log["stations"].update(conv_stations=len(regs), conv_worst_hop_um=round(max(hops), 1))
    import b2o  # noqa: E402
    import cores_b2 as CB  # noqa: E402
    blk = snake_blocks(R)
    _RR, _FP = CB.RelayRouter, CB.free_point

    class RR(_RR):
        def __init__(self, boxes, *a_, **k_):
            super().__init__(list(boxes) + blk, *a_, **k_)
    CB.RelayRouter = RR
    CB.free_point = lambda p, boxes, *a_, **k_: _FP(p, list(boxes) + blk, *a_, **k_)
    keep = [s for s in T["internal_stations"] if s["conn"].startswith("u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv")]
    ilog = []
    fails = b2o.internal_stations(plan, out, ["root"], ilog)
    T = plan["partition_types"]["root"]
    T["internal_stations"] = [s for s in T.get("internal_stations", [])
                              if not s["conn"].startswith("u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv")] + keep
    CB.RelayRouter, CB.free_point = _RR, _FP
    log["r1"]["internal_stations"] = dict(log=ilog, unroutable=fails, conns=len(T["internal_stations"]),
                                          sites=sum(len(s["regs_um"]) for s in T["internal_stations"]))
    if not a.no_ft_repair:
        import hbm_bit_stations as HBS  # noqa: E402
        try:
            fr = HBS.repair(plan, log=lambda m: None, only_types=["root"])
        except HBS.RepairFailure as e:
            fr = e.report
        log["r1"]["ft_repair"] = dict(checked=fr.get("checked"), added=len(fr.get("added", [])),
                                      type_failures=fr.get("type_failures"), unfixed=len(fr.get("unfixed", [])))
    import schema as S  # noqa: E402
    P = S.Plan(plan)
    c0 = plan["latency"]["lanes"]
    newl = {lid: P.lane_latency(lid) for lid in P.lanes}
    log["r1"]["lane_cycle_delta"] = {k: v["cycles"] - c0[k]["cycles"] for k, v in newl.items()
                                     if k in c0 and v["cycles"] != c0[k]["cycles"]}
    plan["latency"]["lanes"] = newl
    log["r1"]["corridors"] = corridors(T, R, gap, top)
    # gate: station / FT sites inside hard cores (strict interior; 8.64 gaps between cores are not cores)
    rects = [(c["inst"], c["origin_um"][0], c["origin_um"][1], c["outline_um"][0], c["outline_um"][1]) for c in T["hard_cores"]]

    def inside(q):
        return [r[0] for r in rects if r[1] < q[0] < r[1] + r[3] and r[2] < q[1] < r[2] + r[4]]
    st_bad = [(s["conn"], q) for s in T["internal_stations"] for q in s["regs_um"] if inside(q)]
    ft_bad = []
    for s in T["ft_slots"]:
        pts = list(s["regs_um"]) + [b for grp in s.get("bit_sites_um", []) for b in grp]
        ft_bad += [(s["name"], q) for q in pts if inside(q)]
    log["r1"]["sites_in_hard_cores"] = dict(stations=len(st_bad), ft=len(ft_bad), st_first=st_bad[:5], ft_first=ft_bad[:5])
    json.dump(plan, open(out / "die_plan.json", "w"), indent=1)
    log["out_plan_sha256"] = PB.sha(out / "die_plan.json")
    json.dump(log, open(out / "b2p_r1_report.json", "w"), indent=1)
    print(json.dumps(dict(root_row=yr, y0=y0, gaps=gap, top_band_um=top, die=dl, lane_cycle_delta=log["r1"]["lane_cycle_delta"],
                          stations=log["stations"], unroutable=fails[:5], ft=log["r1"].get("ft_repair"),
                          corridors=log["r1"]["corridors"], sites=log["r1"]["sites_in_hard_cores"],
                          worst_tap_dist=log["cts_hop_table"]["worst_tap_dist_um"],
                          worst_root_delta=log["cts_hop_table"]["worst_root_delta_um"],
                          plan=log["out_plan_sha256"][:8]), indent=0, default=str))


if __name__ == "__main__":
    main()
