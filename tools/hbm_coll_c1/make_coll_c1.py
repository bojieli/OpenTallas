#!/usr/bin/env python3
"""STEWARD-HBMe/SMH 10-23: COLL landed parents (ot_hfd_coll_q3_lp_ars256, ot_hfd_coll_n1s0_lp_ars256) rebuilt
top-down after the coordinator BAD verdict (92/88 children scattered over 1607x1261 / 1270x1261, 5% fill, 26 children
facing away, 5.4k/3.1k pins without a face register).

Method (shared by both parents):
  * children in family ROWS on the kit's 8.64-um child lattice, every row ordered by dataflow measured on the
    flattened netlist (tools/hbm_coll_c1/net_affinity.py on yosys proc+flatten with the children blackboxed):
      S band   link_e1 (phy flits = S pins)              -> qcap row (rx_flit E -> captured)
      qcap row (src W / captured E)                      -> reduce rows above (pub S <- / in_data N)
      reduce lanes x16 (2 rows of 8) + argmax            -> qso row above (dst_d E, captured W, select N)
      qso row                                            -> writer (W face, kq -> W pins), E del_flit, link wr_flit
      uop96 4x4 (MY: d1 E <- issuer W face)              -> control (MY: inst E <- uop d2)
      vmasm16 4x4 at the W face (rd_il <- vm_rr W pins)  -> qcap
      ring_ag_ctl (MX: ag_d/rr_d to the N pins) + 8 state-capture lanes in the N band; fj on the issuer's N face
  * every top pin gets a range on its face centred on the bit-weighted centroid of the children it feeds/reads
    (measured from the netlist), so pins land beside their child / landing register (io_flop_at_pins kept).
  * RTL, landing record, clocks (5 roots), recipe unchanged: placement + outline + pin table only (0 edges).
usage: make_coll_c1.py [--aff q3_aff.json]   (writes physical/ref_tile_specs/hcoll_c1/*.json)"""
import json, os, re, sys, collections, copy
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
L = 8.64
SPECS = os.path.join(ROOT, "physical/ref_tile_specs/hcoll_c1")

def lef_size(view):
    n = view.rstrip("/").split("/")[-1]
    t = open(os.path.join(ROOT, view, n + ".lef")).read()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    return float(m.group(1)), float(m.group(2))

def plan(kind):
    """returns W, H, {inst: (x, y, orient)}"""
    P = {}
    if kind == "q3":
        W, H = 1166.4, 1252.8
        P["u_link0"] = (155.52, 25.92, "R0"); P["u_link1"] = (665.28, 25.92, "R0")
        nqc, qo_x0, issuer_x, up_x, ctl_x, fj_x, rst_x = 10, 285.12, 622.08, 380.16, 250.56, 1028.16, 285.12
        P["u_arg"] = (976.32, 397.44, "R0")
    else:
        W, H = 1105.92, 1252.8
        P["u_link0"] = (285.12, 25.92, "R0")
        nqc, qo_x0, issuer_x, up_x, ctl_x, fj_x, rst_x = 8, 155.52, 561.6, 319.68, 190.08, 967.68, 276.48
    for r in range(4):
        for c in range(4):
            P["u_va%d" % (4 * r + c)] = (25.92 + 60.48 * c, 241.92 + 60.48 * r, "R0")
            P["u_up%d" % (4 * r + c)] = (up_x + 60.48 * c, 734.4 + 60.48 * r, "MY")
    for k in range(nqc):
        P["u_qc%d" % k] = (285.12 + 86.4 * k, 241.92, "R0")      # under reduce lane k (same column)
    for k in range(16):
        P["u_rdl%d" % k] = (285.12 + 86.4 * (k % 8), 397.44 if k < 8 else 483.84, "R0")
    for k in range(18):
        P["u_qo%d" % k] = (qo_x0 + 51.84 * k, 570.24, "R0")
    if kind == "q3":                                   # the 1-bit slot (21.6 um) heads the row beside the writer
        P["u_qo17"] = (198.72, 570.24, "R0")
    P["u_issuer"] = (issuer_x, 699.84, "R0")
    P["u_control"] = (ctl_x, 734.4, "MY")
    P["u_writer"] = (25.92, 570.24, "MY")
    P["u_rctl"] = (25.92, 1097.28, "MX")
    for k in range(8):
        P["u_rst%d" % k] = (rst_x + 86.4 * k, 1157.76, "R0")
    P["u_fj"] = (fj_x, 1157.76, "R0")
    return W, H, P

def check(W, H, kids):
    errs = []
    box = {}
    for c in kids:
        w, h = lef_size(c["view"])
        x, y = c["at"]
        for v in (x, y):
            if abs(v / L - round(v / L)) > 1e-6: errs.append("%s off the %.2f lattice (%.2f)" % (c["inst"], L, v))
        if x < 20 - 1e-6 or y < 20 - 1e-6 or x + w > W - 20 + 1e-6 or y + h > H - 20 + 1e-6:
            errs.append("%s within 20 um of a face" % c["inst"])
        box[c["inst"]] = (x, y, x + w, y + h)
    ks = sorted(box)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            A, B = box[a], box[b]
            gx = max(B[0] - A[2], A[0] - B[2]); gy = max(B[1] - A[3], A[1] - B[3])
            if max(gx, gy) < 20 - 1e-6:
                errs.append("%s / %s channel %.2f < 20" % (a, b, max(gx, gy)))
    return errs, box

def pin_table(spec, box, aff, W, H):
    """range per top port on its face, centred on the bit-weighted centroid of the children it touches."""
    port_kids = collections.defaultdict(collections.Counter)
    for inst, v in aff.items():
        for p, d in v["ports"].items():
            for e, k in d["to"].items():
                if e.startswith("PORT:"): port_kids[e[5:]][inst] += k
    width = spec["_port_width"]
    ranges = {}
    for face, ports in spec["pins"].items():
        horiz = face in ("N", "S"); Lf = W if horiz else H
        items = []
        for p in ports:
            if p.startswith("ck") or p == "clk": continue
            ks = {i: k for i, k in port_kids.get(p, {}).items() if i in box}
            if ks:
                tot = sum(ks.values())
                c = sum(((box[i][0] + box[i][2]) / 2 if horiz else (box[i][1] + box[i][3]) / 2) * k for i, k in ks.items()) / tot
            else:
                c = Lf / 2
            items.append([c, p, width.get(p, 1)])
        bits = sum(i[2] for i in items)
        dens = max(4.0, bits / (Lf - 60.0))          # pins/um, <= ~5 by construction when the face allows it
        items.sort()
        lo_lim, hi_lim = 8.64, Lf - 8.64
        segs = []
        for c, p, b in items:
            ln = max(b / dens, 1.08)
            segs.append([c - ln / 2, ln, p])
        # forward pass: no overlap, keep order; backward pass: inside the face
        cur = lo_lim
        for s in segs:
            s[0] = max(s[0], cur); cur = s[0] + s[1] + 0.432
        cur = hi_lim
        for s in reversed(segs):
            if s[0] + s[1] > cur: s[0] = cur - s[1]
            cur = s[0] - 0.432
        for a, ln, p in segs:
            ranges[p] = [round(a, 3), round(a + ln, 3)]
        spec.setdefault("_face_density", {})[face] = round(dens, 2)
    return ranges

def port_widths(sv, top):
    t = open(sv).read(); m = re.search(r"\bmodule\s+%s\b(.*?)\);" % top, t, re.S)
    w = {}
    for d in re.finditer(r"(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)", m.group(1)):
        w[d.group(3)] = int(d.group(2)) + 1 if d.group(2) else 1
    return w

def main():
    aff = json.load(open(sys.argv[sys.argv.index("--aff") + 1])) if "--aff" in sys.argv else {}
    os.makedirs(SPECS, exist_ok=True)
    for kind, base, top, sv in (
            ("q3", "hcoll_q3_lp_safe32", "ot_hfd_coll_q3_lp_ars256", "rtl/hbm_accel/generic/collective/p2p/landed/ot_hfd_coll_q3_lp_ars256.sv"),
            ("n1", "hcoll_n1_lp_safe32", "ot_hfd_coll_n1s0_lp_ars256", "rtl/hbm_accel/generic/collective/p2p/landed/ot_hfd_coll_n1s0_lp_ars256.sv")):
        src = json.load(open(os.path.join(ROOT, "physical/ref_tile", base, "spec.json")))
        W, H, P = plan(kind)
        kids = []
        for c in src["children"]:
            if c["inst"] not in P: raise SystemExit("%s: no plan position for %s" % (kind, c["inst"]))
            x, y, o = P[c["inst"]]
            kids.append(dict(c, at=[round(x, 3), round(y, 3)], orient=o))
        missing = set(P) - {c["inst"] for c in src["children"]}
        missing = {m for m in missing if not (kind == "n1" and re.match(r"u_(link1|arg|qc[89])$", m))}
        if missing: raise SystemExit("%s: planned but absent: %s" % (kind, sorted(missing)))
        errs, box = check(W, H, kids)
        if errs: raise SystemExit("%s CHECK FAIL:\n  " % kind + "\n  ".join(errs))
        hard = sum((b[2] - b[0]) * (b[3] - b[1]) for b in box.values())
        halo = sum((b[2] - b[0] + 10.8) * (b[3] - b[1] + 10.8) for b in box.values())
        chan = sum((b[2] - b[0] + 21.6) * (b[3] - b[1] + 21.6) for b in box.values())
        for tag, fb in (("a", False), ("b", True)):
            s = copy.deepcopy(src)
            s["name"] = "hcoll_%s_lp_c1%s" % (kind, tag)
            s["outline"] = {"w": W, "h": H, "exact": True}
            s["children"] = kids
            s["_port_width"] = port_widths(os.path.join(ROOT, sv), top)
            s["pin_ranges"] = pin_table(s, box, aff, W, H)
            dens = s.pop("_face_density"); s.pop("_port_width")
            s["low_fill_reason"] = ("macro-bound landed parent: %d hard children = %.1f%% of the outline (%.1f%% with 5.4-um halos, "
                                    "%.1f%% with 20-um channels); soft logic is landing/pad registers only (~%s um2 placed)"
                                    % (len(kids), 100 * hard / (W * H), 100 * halo / (W * H), 100 * chan / (W * H),
                                       "65k" if kind == "q3" else "52k"))
            s["structural_change"] = (
                "STEWARD-HBMe/SMH 10-23 c1%s (coordinator BAD 10-23 on %s: children scattered over %.0fx%.0f, 26 facing away, "
                "5.4k/3.1k pins with no face register): same RTL/landing record/5 clock roots; children in dataflow rows on the "
                "8.64 lattice (S link band -> qcap row -> 2 reduce rows -> qso row -> writer W face / E del pins; uop 4x4 between "
                "issuer W face and control; vmasm 4x4 at the W vm_rr pins; ring_ag_ctl MX + 8 state lanes in the N band; fj on "
                "the issuer N face); pin table from the netlist centroid of each port's children (face density %s/um); outline "
                "%.1f x %.1f (%.0f%% of the old)%s"
                % (tag, base, src["outline"]["w"], src["outline"]["h"], json.dumps(dens), W, H,
                   100 * W * H / (src["outline"]["w"] * src["outline"]["h"]),
                   "; FB: TritonCTS on one merged rg+hd root region is NOT possible (5 related roots are RTL ports) -> FB = "
                   "same plan with pin ranges dropped (tool face spread) to separate pin-table risk from row risk" if fb else ""))
            if fb:
                s.pop("pin_ranges", None)
            j = s["job"]
            j.update(owner="Claude:STEWARD-HBMe/SMH", branch="claude/hbme-coll-1023", tag="c1" + tag,
                     purpose="COLL %s landed parent %s re-plan (coordinator BAD 10-23): dataflow rows + content outline + "
                             "netlist pin table; placement render first (GEOM-REVIEW), P&R only after PASS" % (kind, top))
            j["extra_paths"] = sorted(set(j.get("extra_paths", []) + ["tools/hbm_coll_c1"]))
            s["safe_design_checklist"] = {
                "pins": "every top pin ranged beside the child/landing it feeds (netlist centroid); io_flop_at_pins kept",
                "reach": "longest family-to-face distance <= ~600 um (issuer cfg <- fj adjacent; qso -> writer adjacent)",
                "fanout": "RTL unchanged (safe32 census)", "depth": "unchanged", "storage": "children unchanged",
                "floorplan": "regular rows on the 8.64 lattice, >= 20-um channels, no child within 20 um of a face",
                "clock": "5 RTL roots unchanged; each region compact (lk = S band, wr = W column, rg = N band, hd = issuer/fj, sw = rows)",
                "schedule": "static; 0 edges"}
            out = os.path.join(SPECS, s["name"] + ".json")
            json.dump(s, open(out, "w"), indent=1)
            print("%s %.1fx%.1f=%.3f mm2 (old %.3f) hard %.1f%% halo %.1f%% chan %.1f%% dens %s -> %s" % (
                s["name"], W, H, W * H / 1e6, src["outline"]["w"] * src["outline"]["h"] / 1e6,
                100 * hard / (W * H), 100 * halo / (W * H), 100 * chan / (W * H), dens, out))

if __name__ == "__main__":
    main()
