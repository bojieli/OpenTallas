#!/usr/bin/env python3
"""DH55-CLAND (DIE-HEAD-55 helper, COORD ruling 11-02 22:54 G1): one-block HEAD plan delta for the count-aligned
clock-landing CONTROL graph of the 0-macro ft/control strips hd_ctl_n, hd_ctl_e and hd_host_n (AUTO-GEOM r2r 1719 x259 /
718 x3 / 1452 x226 on the l48x 3_place dumps).  Existing plan knobs only (clock_landings.py / count_align_bind.py, the
DIE-HEAD-38 R1/R2/W1 keys DIE-HEAD-53 l48z already uses on hd_st_n3_turn / hd_mesh_e); no tool, gate, slot, outline,
pin or data-cycle change:

  landing_reader_start  uniform depth R per type, R registered relays from the origin toward EVERY input ring
                        (count_align_bind: ring K -R, boot +R cycles, steady data cycles 0); origin_rect_um at tstart
  landing_writer_start  depth W on the output buses whose FSTART face flop is > reach from the origin
                        (receiver K +W through the die-top strap ties, boot only)
  landing_status_input_stages  per (agg | local status output, far ring): 1-input status relays on that ring's
                        ready/fault (status observed n cycles later, 0 data cycles)
  landing_status_anchors  agg_1 at the plan point, agg_2.. on the line to the tree output register
  landing_local_resets  same-cycle local copies (depth(raw)+1 == consumer reset depth) for every landing control
                        consumer (origin, FSTART flops, agg/up/sin collects), clustered, raw = a near reset-tree relay
  ft_slots[n_tx_ft].bit_sites_um (hd_ctl_e only)  per-bit s1/s2 sites on the pin rows (mesh_e l48z form), so the
                        E output pins sit ~54 um from s2 (was 288), s1/s2 hops <= 400

Stage sites are computed, not hand-placed: every stage lies on the straight segment between its two end points and
every hop (including the farthest flop of a landing band, half-width + half-height of the plan band) is <= HMAX.
The reset-tree relay table per type (net, depth, xy) is the frozen-tool (703c07481) GEN of the prepared y864 plan
(comments '// raw ... depth D @ (x, y)' of the l48x kit RTL); GEN re-checks every raw and every copy depth and fails
closed (LandingError) on any mismatch.

usage: head_cland_stage_delta.py SRC_DIR OUT_DIR [--ctl-e-geom GEOM_TSV] [--types t1,t2]
  SRC_DIR: a HEAD source dir (source_plan.json + source_sidecar.json [+ s81_head_top.sv]) or a kit-wave prepared dir.
  The die-top count-strap literals (s81_head_top.sv, when present) follow Landings.strap_expected() old vs new.
  --republish ROOT (prepared dirs): regenerate published/<module>.sv of the changed types with ROOT's gen.py
  (bootstrap + alias_patch, exactly head_wave_kit_rtl.py export's check) and refresh wave_prepare.json digests.
"""
import argparse, hashlib, json, math, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HMAX = 370.0          # planned hop (plan reach 405, 35 um left for placement scatter)
COPY_REACH = 370.0    # raw -> local copy and copy -> consumer
TYPES = ("hd_ctl_n", "hd_ctl_e", "hd_host_n", "hd_mesh", "hd_host")
CTL_E_SITE_X = (401.5, 801.0)   # hd_ctl_e n_tx_ft s1/s2 cell centres (hop <= 400 planned, 405 measured reach)

# reset-tree raw relays (net, depth, x, y, exported) from the frozen 703c07481 GEN of prepared_mesh_y864
# (intel2 codex-head-wave-1101/.../hd_ctl_n, codex-head-wave-1131/.../hd_ctl_e/attempt_3, codex-head-lep-wave-1101/
# .../hd_host_n/attempt_2 gen/<t>/rtl/<module>.sv).  exported = drives a rst_start_raw_* port (writer stages avoid it).
RRL = {
    "hd_ctl_n": [("rst_rl_0", 1, 663.4, 126.8, 1), ("rst_rl_1", 2, 663.4, 126.8, 0), ("rst_rl_2", 3, 663.4, 126.8, 0),
                 ("rst_rl_4", 2, 331.7, 126.8, 0), ("rst_rl_5", 3, 331.7, 126.8, 0), ("rst_rl_7", 3, 82.2, 203.5, 0),
                 ("rst_rl_9", 3, 162.0, 328.5, 0), ("rr_t10", 4, 162.0, 699.8, 0), ("rst_rl_11", 3, 17.3, 189.2, 1),
                 ("rst_rl_13", 2, 304.2, 126.8, 1), ("rst_rl_14", 3, 304.2, 126.8, 0), ("rst_rl_16", 1, 986.1, 105.2, 1),
                 ("rst_rl_17", 2, 986.1, 105.2, 0), ("rst_rl_18", 3, 986.1, 105.2, 0), ("rst_rl_20", 3, 1048.0, 374.9, 0),
                 ("rst_rl_23", 1, 1160.8, 8.6, 1), ("rst_rl_24", 2, 1160.8, 8.6, 0), ("rst_rl_25", 3, 1179.9, 340.4, 0),
                 ("rst_rl_27", 1, 441.2, 8.6, 1), ("rst_rl_28", 2, 441.2, 8.6, 0), ("rst_rl_29", 3, 72.4, 8.6, 0)],
    "hd_ctl_e": [("rst_rl_0", 1, 285.1, 34.1, 1), ("rst_rl_3", 1, 17.3, 21.5, 1), ("rst_rl_5", 1, 470.9, 95.1, 0),
                 ("rr_t4", 2, 713.3, 8.6, 0), ("rst_rl_7", 1, 496.9, 95.1, 0)],
    "hd_host_n": [("rst_rl_0", 1, 510.0, 337.3, 1), ("rst_rl_1", 2, 510.0, 337.3, 0), ("rst_rl_2", 3, 510.0, 337.3, 0),
                  ("rst_rl_4", 2, 764.1, 216.3, 1), ("rst_rl_5", 3, 764.1, 216.3, 0), ("rst_rl_7", 3, 1104.0, 216.3, 0),
                  ("rst_rl_10", 3, 1125.6, 216.3, 1), ("rr_t11", 4, 1434.7, 164.0, 1), ("rst_rl_12", 2, 304.0, 234.0, 1),
                  ("rst_rl_13", 3, 304.0, 234.0, 0), ("rr_t9", 4, 180.0, 8.6, 0), ("rst_rl_17", 2, 541.1, 8.6, 0),
                  ("rst_rl_18", 3, 541.1, 8.6, 0), ("rr_t10", 4, 541.1, 8.6, 1), ("rst_rl_20", 1, 450.8, 639.4, 0),
                  ("rst_rl_21", 2, 450.8, 639.4, 0), ("rst_rl_22", 3, 450.8, 639.4, 0), ("rst_rl_24", 3, 384.0, 328.0, 0),
                  ("rst_rl_27", 1, 891.0, 648.0, 0), ("rst_rl_28", 2, 891.0, 648.0, 0), ("rst_rl_29", 3, 1240.0, 648.0, 0),
                  ("rr_t12", 4, 1434.7, 492.6, 0)],
}
# landing-control reset depth of the type (every ring reset relay u_cland_rst_<b> = rrelay(depth-3 / depth-1 tap) + 1)
CTRL_DEPTH = {"hd_ctl_n": 4, "hd_ctl_e": 2, "hd_host_n": 4, "hd_mesh": 4, "hd_host": 4}
# agg_1 plan point (inside reach of the near rings / face status flops; far rings get status relays)
AGG1 = {"hd_ctl_n": (90.0, 300.0), "hd_ctl_e": (735.0, 74.0), "hd_host_n": (420.0, 290.0)}
# DIE-HEAD-65 l48uc: hd_mesh / hd_host relay table and agg_1 point are read, not typed: --rrl-from T=<wave wrapper .sv> and
# the mid point of the landed rings.
ORIGIN_EXT = 5.0


def rrl_from_rtl(path):
    """(net, depth, x, y, exported) of every raw relay in one GEN wrapper ('// raw ... depth D @ (x, y)' comments)."""
    t = Path(path).read_text()
    out = []
    for m in re.finditer(r"ot_dp_rrelay\s+\w+\s*\(.*?\.q\((\w+)\)\);\s*//\s*raw .*?depth (\d+) @ \(([\d.]+), ([\d.]+)\)", t):
        net = m.group(1)
        exp = int(bool(re.search(r"assign\s+rst_start_raw\w*\s*=\s*" + net + r"\b", t) or
                       re.search(r"\.rst_start_raw\w*\(" + net + r"\)", t)))
        out.append((net, int(m.group(2)), float(m.group(3)), float(m.group(4)), exp))
    if not out:
        raise ValueError(f"no raw relays in {path}")
    return out


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def rnd(p):
    return [round(p[0], 2), round(p[1], 2)]


def stages_needed(a, ea, b, eb, hmax=HMAX):
    """registered stages between end flop groups a (extent ea) and b (extent eb) so every hop <= hmax"""
    return max(0, math.ceil((md(a, b) + ea + eb) / hmax - 1e-9) - 1)


def chain(a, ea, b, eb, n):
    """n stage points on the segment a->b; equal hops H with the end extents charged to the first / last hop"""
    m = md(a, b)
    if n == 0:
        return []
    h = (m + ea + eb) / (n + 1)
    pts = []
    for k in range(n):
        d = min(max(h - ea + k * h, 0.0), m)
        t = d / m if m else 0.0
        pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return pts


def band_geom(rect):
    x0, y0, x1, y1 = rect
    return ((x0 + x1) / 2, (y0 + y1) / 2), (x1 - x0) / 2 + (y1 - y0) / 2


def nearest(rrl, p, depth=None, allow_exported=True):
    c = [r for r in rrl if (depth is None or r[1] == depth) and (allow_exported or not r[4])]
    if not c:
        raise ValueError(f"no reset-tree relay depth {depth}")
    return min(c, key=lambda r: (md((r[2], r[3]), p), r[4], r[0]))


def local_resets(rrl, depth, consumers, prefix="k"):
    """consumers {instance: xy} -> landing_local_resets entries (same-cycle copies, raw depth = depth-1)"""
    copies = []
    for inst, c in sorted(consumers.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[0])):
        r = nearest(rrl, c, depth - 1, allow_exported=False)
        rx = (r[2], r[3])
        if md(rx, c) > 2 * COPY_REACH:
            r = nearest(rrl, c, depth - 1, allow_exported=True); rx = (r[2], r[3])
        d = md(rx, c)
        if d > 2 * COPY_REACH:
            raise ValueError(f"{inst}: nearest depth-{depth - 1} raw {r[0]} is {d:.0f} um away")
        t = 0.0 if d <= COPY_REACH * 0.8 else 0.5
        want = (c[0] + t * (rx[0] - c[0]), c[1] + t * (rx[1] - c[1]))
        for cp in copies:
            if cp["raw"] == r[0] and md(cp["xy"], want) <= 150 and md(cp["xy"], c) <= COPY_REACH \
                    and md(cp["xy"], rx) <= COPY_REACH:
                cp["consumers"].append(inst)
                break
        else:
            copies.append(dict(raw=r[0], xy=want, consumers=[inst]))
    out = []
    for i, cp in enumerate(copies):
        out.append(dict(name=f"{prefix}{i}", raw=cp["raw"], xy_um=rnd(cp["xy"]), consumers=sorted(cp["consumers"])))
    return out


def pins_of(T):
    return {p["name"]: p.get("xy_um") for p in T["clock"]["landing_contract"]["pins"]}


def type_delta(tn, T, coll):
    """the full landing-control stage set of one strip type; returns (clock additions, report)"""
    c = T["clock"]
    for k in ("landing_reader_start", "landing_writer_start", "landing_status_input_stages", "landing_status_anchors",
              "landing_local_resets"):
        assert k not in c, (tn, k)
    rrl, depth = RRL[tn], CTRL_DEPTH[tn]
    pins = pins_of(T)
    origin = tuple(c["start_capture_um"])
    bands = {b: band_geom(v["rect_um"]) for b, v in c["landing_contract"]["bands"].items()}
    mask = coll["mask"]
    rings = list(mask["inputs"])
    assert sorted(rings) == sorted(bands), (tn, rings, sorted(bands))
    tree = mask["tree_bus"]
    root_xy = tuple(coll["collector_root_xy"])
    ndep = int(coll["local_registered_depth"])
    rep = dict(type=tn, origin=rnd(origin))
    add, consumers = {}, {}
    # ---- reader START (uniform depth) ----
    R = max(stages_needed(origin, ORIGIN_EXT, *bands[b]) for b in rings)
    if R:
        br = {}
        for b in rings:
            pts = chain(origin, ORIGIN_EXT, bands[b][0], bands[b][1], R)
            br[b] = {"stages": [dict(xy_um=rnd(p), raw_reset=nearest(rrl, p, allow_exported=False)[0]) for p in pts]}
        add["landing_reader_start"] = dict(depth=R, origin_rect_um=[round(origin[0] - 8.64, 2), round(origin[1] - 8.64, 2),
                                                                    round(origin[0] + 8.64, 2), round(origin[1] + 8.64, 2)],
                                           branches=br)
    consumers["u_cland_origin"] = origin
    rep["reader_start_depth"] = R
    rep["ring_K_delta"] = {b: -R for b in rings}
    # ---- writer START on far FSTART face flops ----
    outs = [b for b in mask["outputs"] if f"cland_fstart_out_{b}" in pins]
    need = {b: stages_needed(origin, ORIGIN_EXT, tuple(pins[f"cland_fstart_out_{b}"]), 0.0) for b in outs}
    W = max(need.values()) if need else 0
    far = sorted(b for b, n in need.items() if n)
    if W:
        add["landing_writer_start"] = dict(depth=W, branches={
            b: {"stages": [dict(xy_um=rnd(p), raw_reset=nearest(rrl, p, allow_exported=False)[0])
                           for p in chain(origin, ORIGIN_EXT, tuple(pins[f"cland_fstart_out_{b}"]), 0.0, W)]}
            for b in far})
    for b in outs:
        consumers[f"u_cland_fstart_{b}"] = tuple(pins[f"cland_fstart_out_{b}"])
    rep["writer_start_depth"] = W
    rep["writer_buses_receiver_K_delta"] = {b: +W for b in far}
    # ---- aggregate anchors: agg_1 at the plan point, agg_2.. on the line to the tree output register ----
    a1 = AGG1.get(tn) or tuple(sum(bands[b][0][i] for b in rings) / len(rings) for i in (0, 1))
    anchors = {"u_cland_agg_1": a1}
    for k in range(2, ndep):
        t = (k - 1) / (ndep - 1)
        anchors[f"u_cland_agg_{k}"] = (a1[0] + t * (root_xy[0] - a1[0]), a1[1] + t * (root_xy[1] - a1[1]))
    hop = max(md(a1, root_xy) / (ndep - 1), 0)
    assert hop <= HMAX, (tn, "agg chain hop", hop)
    add["landing_status_anchors"] = {k: rnd(v) for k, v in anchors.items()}
    consumers.update(anchors)
    consumers[f"u_cland_up_{tree}"] = root_xy
    # ---- status input relays: agg_1 and every local status output from each far ring ----
    targets = {"agg": (a1, 0.0)}
    for b in mask["outputs"] + [x for x in mask.get("intra_outputs", []) if x != tree]:
        if b == tree:
            continue
        p = pins.get(f"cland_up_ready_{b}")
        if p:
            targets[b] = (tuple(p), 0.0)
            consumers[f"u_cland_up_{b}"] = tuple(p)
    sis, nsin = {}, 0
    for tgt, (tp, te) in targets.items():
        for r in rings:
            n = stages_needed(bands[r][0], bands[r][1], tp, te)
            if not n:
                continue
            pts = chain(bands[r][0], bands[r][1], tp, te, n)
            sis.setdefault(tgt, {})[r] = [dict(xy_um=rnd(p)) for p in pts]
            for k, p in enumerate(pts):
                consumers[f"u_cland_sin_{tgt}_{r}_{k}"] = p
            nsin += n
    if sis:
        add["landing_status_input_stages"] = sis
    rep["status_input_stages"] = {t: {r: len(v) for r, v in rr.items()} for t, rr in sis.items()}
    rep["status_relays"] = nsin
    # ---- local same-cycle reset copies for every landing control consumer ----
    add["landing_local_resets"] = local_resets(rrl, depth, consumers)
    rep["local_reset_copies"] = len(add["landing_local_resets"])
    rep["boot_extra_cycles"] = R + W
    rep["steady_data_cycles_added"] = 0
    return add, rep


def ctl_e_bit_sites(T, geom_tsv):
    """hd_ctl_e n_tx_ft (W->E, 3 stations over 855.36 um): s1/s2 per-bit sites on each bit's pin row (mesh_e l48z
    form, ASAP7 site grid X0=Y0=4.32, SW 0.054, RH 0.27, DFF 1.404x0.27): s0 W face flop ~6 -> s1 401.5 -> s2 801.0
    (hops ~395.5 / 399.5) -> E pins 855.36 (~54; was 288).  DH56-CLAND: the 405.0/808.6 sites (hop 403.6) placed at
    3_place r2r 405.8-406.0 on 4 bits (D/Q pin offsets + legalisation, +2.4 um), so the hop target is <= 400."""
    X0 = Y0 = 4.32; SW, RH, CELL = 0.054, 0.27, [1.404, 0.27]
    slot = {s["name"]: s for s in T["ft_slots"]}["n_tx_ft"]
    assert slot["in_face"] == "W" and slot["out_face"] == "E" and slot["stations"] == 3, slot
    pins = {}
    for ln in Path(geom_tsv).read_text().splitlines():
        f = ln.split("\t")
        if f[0] == "P":
            m = re.fullmatch(r"n_tx_ft_o\[(\d+)\]", f[2])
            if m:
                pins[int(m.group(1))] = float(f[7])
    assert sorted(pins) == list(range(slot["width"] + 1)), "n_tx_ft_o pins not 0..width"
    gx = lambda x: round(X0 + math.floor((x - X0) / SW + 1e-9) * SW, 3)
    sites = []
    for xc in CTL_E_SITE_X:
        x = gx(xc - CELL[0] / 2); used = set(); col = []
        for b in range(slot["width"] + 1):
            n0 = round((pins[b] - RH / 2 - Y0) / RH)
            n = next(n0 + d for d in (0, 1, -1, 2, -2) if n0 + d not in used); used.add(n)
            col.append([x, round(Y0 + n * RH, 3)])
        sites.append(col)
    slot["bit_sites_um"] = sites; slot["bit_site_cell_um"] = CELL
    slot["note"] = ("DH55-CLAND l48h: per-bit station sites s1 x~%.1f, s2 x~%.1f on each bit's pin row "
                    "(L*j/3 put s2 288 um from the E pins)" % (sites[0][0][0] + 0.702, sites[1][0][0] + 0.702))
    return "n_tx_ft bit sites s1/s2 (hops <= 400, E pin_reg ~54, was 288)"


def strap_update(out, repo, plan, side, old_k):
    sys.path.insert(0, str(repo / "tools/die_plan"))
    import clock_landings as CL
    new_k = CL.Landings(json.loads(json.dumps(plan)), side).strap_expected()
    top = (out / "s81_head_top.sv").read_text(); ch = []
    for part in sorted(set(old_k) | set(new_k)):
        for sp in sorted(set(old_k.get(part, {})) | set(new_k.get(part, {}))):
            o, n = old_k.get(part, {}).get(sp), new_k.get(part, {}).get(sp)
            if o == n:
                continue
            w, v = n; inst = CL.ident(part)
            m = re.search(r"\n    (\w+)(?:\s*#\(.*?\))?\s+" + re.escape(inst) + r"\s*\((.*?)\n    \);", top, re.S)
            assert m, inst
            body = m.group(2); pm = re.search(r"\." + re.escape(sp) + r"\((\d+)'b([01]+)\)", body)
            assert pm and int(pm.group(2), 2) == o[1], (inst, sp, o, pm and pm.group(0))
            nb = body[:pm.start()] + ".%s(%d'b%s)" % (sp, w, format(v, "0%db" % w)) + body[pm.end():]
            top = top[:m.start(2)] + nb + top[m.end(2):]
            ch.append([inst, sp, o[1], v])
    (out / "s81_head_top.sv").write_text(top)
    return ch


def writable(root):
    """kit-wave prepared dirs keep read-only subdirs (assets, core_pins, ...): the OUT copy is ours to edit"""
    for p in [root, *root.rglob("*")]:
        if not p.is_symlink():
            p.chmod(p.stat().st_mode | 0o200)


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def republish(out, root, types, sidecar):
    """prepared dir: published wrapper = alias_patch(GEN bootstrap) of the new plan (head_wave_kit_rtl export check)"""
    sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
    from head_start_reset_aliases import patch_rtl as alias_patch
    plan = json.loads((out / "source_plan.json").read_text())
    rec = json.loads((out / "wave_prepare.json").read_text())
    for t in types:
        T = plan["partition_types"][t]
        with tempfile.TemporaryDirectory() as td:
            cmd = [sys.executable, str(root / "tools/die_plan/gen.py"), "phys", str(out / "source_plan.json"),
                   "--clock-landing", str(sidecar), "--types", t, "--out", td, "--rtl-root", str(root), "--trial"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            (out / f"republish_{t}.log").write_text(r.stdout + r.stderr)
            if r.returncode:
                raise SystemExit(f"{t}: bootstrap GEN failed rc={r.returncode} (see republish_{t}.log)")
            w = Path(td) / "_rtl" / (T["module"] + ".sv")
            text = alias_patch(w.read_text(), T.get("reset_start_raw_exports", []))
        (out / "published" / w.name).write_text(text)
        rec["published_wrappers"][t] = dict(module=T["module"], sha256=digest(out / "published" / w.name))
    rec["prepared_plan_sha256"] = digest(out / "source_plan.json")
    rec["sidecar_sha256"] = digest(out / "source_sidecar.json")
    (out / "wave_prepare.json").write_text(json.dumps(rec, indent=1) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--types", default=",".join(TYPES))
    ap.add_argument("--ctl-e-geom", type=Path, help="hd_ctl_e l48x geom.tsv (n_tx_ft_o pin rows) for the bit sites")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2],
                    help="tools root for Landings.strap_expected (die-top straps)")
    ap.add_argument("--knobs-from", type=Path, help="a HEAD source dir (no landing_contract in its plan): compute the "
                    "knobs on this prepared dir's plan and add the same clock keys to SRC (die-top straps follow)")
    ap.add_argument("--rrl-from", action="append", default=[], help="T=wrapper.sv: reset relay table of T read from GEN RTL")
    ap.add_argument("--republish", type=Path, help="prepared dir: tools root whose gen.py regenerates published/")
    a = ap.parse_args(argv)
    types = a.types.split(",")
    for x in a.rrl_from:
        tn, p = x.split("=", 1)
        RRL[tn] = rrl_from_rtl(p)
    assert set(types) <= set(TYPES), types
    plan = json.loads((a.src / "source_plan.json").read_text())
    side = json.loads((a.src / "source_sidecar.json").read_text())
    has_top = (a.src / "s81_head_top.sv").exists()
    old_k = None
    if has_top:
        sys.path.insert(0, str(a.repo / "tools/die_plan"))
        import clock_landings as CL
        old_k = CL.Landings(json.loads(json.dumps(plan)), side).strap_expected()
    rep = {}
    kplan = json.loads((a.knobs_from / "source_plan.json").read_text()) if a.knobs_from else plan
    kside = json.loads((a.knobs_from / "source_sidecar.json").read_text()) if a.knobs_from else side
    for tn in types:
        T = plan["partition_types"][tn]
        KT = json.loads(json.dumps(kplan["partition_types"][tn]))
        add, r = type_delta(tn, KT, kside["collector"]["types"][tn])
        if a.knobs_from:
            assert T.get("buses") == KT.get("buses") and T.get("ft_slots") == kplan["partition_types"][tn].get("ft_slots"), tn
        T["clock"].update(add)
        if tn == "hd_ctl_e" and a.ctl_e_geom:
            r["ft_bit_sites"] = ctl_e_bit_sites(T, a.ctl_e_geom)
            if a.knobs_from:
                ctl_e_bit_sites(KT, a.ctl_e_geom)
                assert T["ft_slots"] == KT["ft_slots"]
        rep[tn] = r
    if a.out.exists():
        writable(a.out)
        shutil.rmtree(a.out)
    shutil.copytree(a.src, a.out, symlinks=True)
    writable(a.out)
    (a.out / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    ch = strap_update(a.out, a.repo, plan, side, old_k) if has_top else None
    if a.republish:
        republish(a.out, a.republish.resolve(), types, a.out / "source_sidecar.json")
    report = dict(event="l48h-cland", tool="tools/s81_head/head_cland_stage_delta.py", hmax_um=HMAX, types=rep,
                  strap_changes=ch, sidecar_changed=False, data_cycles_added=0)
    (a.out / "cland_report.json").write_text(json.dumps(report, indent=1) + "\n")
    for tn, r in rep.items():
        print(tn, "R", r["reader_start_depth"], "W", r["writer_start_depth"], "sin", r["status_relays"],
              "lrst", r["local_reset_copies"], r.get("ft_bit_sites", ""))
    if ch is not None:
        print("strap changes", len(ch))
        for c in ch:
            print("  ", c)


if __name__ == "__main__":
    main()
