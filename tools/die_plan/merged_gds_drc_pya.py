# KLayout (pya) half of tools/die_plan/merged_gds_drc.py.  Run as: klayout -b -r merged_gds_drc_pya.py -rd mode=... -rd ...
# mode=core   : routed core DEF -> GDS whose top cell is renamed to the core's MASTER name (std cells from the platform GDS).
# mode=parent : routed parent DEF -> three GDS with identical coordinates:
#               merged.gds      parent + every hard core filled with its real GDS (the sign-off geometry)
#               parent_only.gds parent with the hard cores left empty (baseline 1)
#               macros_only.gds only the hard-core instances (baseline 2)
#               Cells matching allow_empty (generated memory macros without GDS) stay empty in all three; their outlines
#               are written to empty_cells.json so the compare step can report markers there as UNCHECKED.
# mode=window : (P-DRC-DECK-BASELINE, flattened windows) clip one of the three GDS to every hard-core instance bbox + margin_um (default 5), flatten each window and write
#               <out_prefix>_<i>.gds; windows.json lists them.  The deck runs on these flat windows; hierarchical full-chip runs no longer gate.
# mode=shorts : (geometric short check, COORD 11-26) per window: on every metal and via layer, parent shapes (win/parent_only_<i>.gds) that overlap core shapes (win/macros_only_<i>.gds)
#               are written to win/shorts_<i>.json as bbox lists per layer, minus the overlap inside the core's own PIN-purpose shapes (datatype 251 of the same layer, written by
#               mode=core from the routed DEF pins: the legal landing of a parent route on a pin; the pin purpose is orientation-correct where a LEF rect would need the placement).
# mode=selftest: build D/{clean,seeded}/{merged,parent_only,macros_only}.gds + parent_cells.json from one real core GDS placed in an empty parent; seeded merged/parent_only get
#               a parent M4 wire overlapping a core M4 wire, a parent M4 box abutting its end with zero gap, a parent M8 shape overlapping a core M8 shape, and a parent V6 via pair 30 nm apart next to a core shape (V6.S).
# mode=compare: merged.lyrdb minus (parent_only.lyrdb + macros_only.lyrdb), matched by (category, marker bbox at 1 dbu);
#               -> compare.json: per category counts, every NEW marker (bbox, category, nearest hard-core instance).
import json
import re

import pya

g = globals()
mode = g.get("mode")


def tech_layout_options(tech_file):
    tech = pya.Technology()
    tech.load(tech_file)
    return tech.load_layout_options


def read_def(def_file, tech_file):
    ly = pya.Layout()
    ly.read(def_file, tech_layout_options(tech_file))
    return ly


def top_cell(ly, name):
    c = ly.cell(name)
    if c is None:
        tops = list(ly.top_cells())
        if len(tops) != 1:
            raise RuntimeError("cannot find top cell %r (tops: %s)" % (name, [t.name for t in tops]))
        c = tops[0]
    return c


def write_top(ly, top, path):
    """write only the tree under top (the DRC deck needs exactly one top cell)"""
    out = pya.Layout()
    out.dbu = ly.dbu
    t = out.create_cell(top.name)
    t.copy_tree(top)
    out.write(path)


SHORT_GROW_DBU = 1     # P-DRC-DECK-BASELINE F1: parent metal within 1 dbu of core metal (zero-gap abutment included) is a short: it merges into one polygon and gives no deck marker


def short_overlap(par, core, pins):
    """Regions (merged): parent shapes grown by SHORT_GROW_DBU that touch or overlap core metal, minus the core's own pin-purpose landing."""
    return (par.merged().sized(SHORT_GROW_DBU) & core.merged()) - pins.merged().sized(SHORT_GROW_DBU)


def nested_empty_cells(cell, allow=None):
    """-> sorted names of cells below `cell` (a filled hard core) with no shapes and no children that are neither VIA_/DEF_FILL nor matched by allow: silently unchecked geometry"""
    out = set()
    for ci in cell.called_cells():
        c = cell.layout().cell(ci)
        if c.is_empty() and not c.name.startswith("VIA_") and not c.name.endswith("_DEF_FILL") and not (allow is not None and allow.match(c.name)):
            out.add(c.name)
    return sorted(out)


PIN_DATATYPE = 251   # the ASAP7 KLayout tech maps DEF PINS (BTerm shapes) to <layer>/251; the deck reads <layer>/0 only


def pins_to_drawing(ly):
    """BTerm pin shapes are real metal: copy every <layer>/251 shape into <layer>/0 so the DRC deck sees the pin metal (without
    it a parent wire ending inside a core pin looks like a line end 29 nm from the core's via stub: M7.S.2 false errors)"""
    n = 0
    for li in list(ly.layer_indexes()):
        info = ly.get_info(li)
        if info.datatype != PIN_DATATYPE:
            continue
        dst = ly.layer(info.layer, 0)
        for c in ly.each_cell():
            for sh in c.shapes(li).each():
                if sh.is_box() or sh.is_polygon() or sh.is_path():
                    c.shapes(dst).insert(sh)
                    n += 1
    return n


LEF_BBOX = {}     # P-DRC F7: LEF-abstract outline of every cell before it is cleared (an allow-empty macro has no GDS shapes, so its instance bbox would be empty)


def fill_std(ly, top, gds_files):
    """clear every LEF-abstract child cell (keep VIA_ and DEF fill), then read the platform GDS (same names fill them)"""
    for c in ly.each_cell():
        if c.cell_index() != top.cell_index() and not c.name.startswith("VIA_") and not c.name.endswith("_DEF_FILL"):
            if not c.dbbox().empty():
                LEF_BBOX[c.name] = c.dbbox()
            c.clear()
    for f in gds_files:
        ly.read(f)


if mode == "core":
    ly = read_def(in_def, tech_file)  # noqa: F821
    top = top_cell(ly, design_name)  # noqa: F821
    fill_std(ly, top, gds_files.split())  # noqa: F821
    npins = pins_to_drawing(ly)
    out = pya.Layout()
    out.dbu = ly.dbu
    t = out.create_cell(master)  # noqa: F821
    t.copy_tree(top)
    empty = sorted({c.name for c in out.each_cell() if c.is_empty() and c.cell_index() != t.cell_index()})
    out.write(out_file)  # noqa: F821
    json.dump(dict(master=master, empty_cells=empty, dbu=out.dbu, pin_shapes_to_drawing=npins), open(out_file + ".json", "w"), indent=1)  # noqa: F821

elif mode == "parent":
    ly = read_def(in_def, tech_file)  # noqa: F821
    top = top_cell(ly, design_name)  # noqa: F821
    macros = json.loads(open(macro_map).read())  # noqa: F821  {master: core_gds}
    fill_std(ly, top, gds_files.split())  # noqa: F821
    allow = re.compile(allow_empty) if g.get("allow_empty") else None
    filled = {}
    for m, gds in macros.items():
        cell = ly.cell(m)
        if cell is None:
            continue
        src = pya.Layout()
        src.read(gds)
        sc = src.cell(m)
        if sc is None:
            raise RuntimeError("core GDS %s has no cell %s" % (gds, m))
        cell.clear()
        cell.copy_tree(sc)           # children are created anew in ly: no name clash with the parent's own cells
        filled[m] = gds
    nested = {}                      # P-DRC F3: empty cells inside a filled core are real unchecked geometry: they need --allow-empty like top-level ones
    for m in filled:
        ne = nested_empty_cells(ly.cell(m), allow)
        if ne:
            nested[m] = ne
    pins_to_drawing(ly)              # parent BTerms + core pins (also core GDS written before this fix); idempotent overlap
    # instances of the hard cores and of empty cells
    insts, empties, missing = [], [], set()
    for inst in top.each_inst():
        nm = inst.cell.name
        bb = inst.dbbox()
        rec = dict(inst=str(inst.property("name") or ""), master=nm, bbox=[bb.left, bb.bottom, bb.right, bb.top])
        if nm in filled:
            insts.append(rec)
        elif inst.cell.is_empty() and not nm.startswith("VIA_"):
            if allow is not None and allow.match(nm):
                if bb.empty() and nm in LEF_BBOX:
                    lb = inst.dtrans * LEF_BBOX[nm]
                    rec["bbox"] = [lb.left, lb.bottom, lb.right, lb.top]
                empties.append(rec)
            else:
                missing.add(nm)
    for m, ne in nested.items():
        missing.update("%s>%s" % (m, n) for n in ne)
    json.dump(dict(filled=filled, hard_core_insts=insts, empty_allowed=empties, missing=sorted(missing), nested_empty=nested, dbu=ly.dbu),
              open(out_dir + "/parent_cells.json", "w"), indent=1)  # noqa: F821
    if missing:
        raise RuntimeError("cells with neither GDS nor allow_empty: %s" % sorted(missing))
    write_top(ly, top, out_dir + "/merged.gds")  # noqa: F821
    # macros_only: copy of the top with only hard-core instances
    mo = pya.Layout()
    mo.dbu = ly.dbu
    mt = mo.create_cell(top.name)
    mt.copy_tree(top)
    for inst in list(mt.each_inst()):
        if inst.cell.name.split("$")[0] not in filled:
            inst.delete()
    mt.clear_shapes()
    write_top(mo, mt, out_dir + "/macros_only.gds")  # noqa: F821
    mo = None
    # parent_only: hard cores emptied
    for m in filled:
        ly.cell(m).clear()
    write_top(ly, top, out_dir + "/parent_only.gds")  # noqa: F821

elif mode == "compare":
    def items(path):
        db = pya.ReportDatabase("x")
        db.load(path)
        out = {}
        for it in db.each_item():
            cat = db.category_by_id(it.category_id()).path()
            for v in it.each_value():
                b = None
                if v.is_polygon():
                    b = v.polygon().bbox()
                elif v.is_edge_pair():
                    b = v.edge_pair().bbox()
                elif v.is_box():
                    b = v.box()
                elif v.is_edge():
                    b = v.edge().bbox()
                if b is None:
                    continue
                key = (cat, round(b.left, 4), round(b.bottom, 4), round(b.right, 4), round(b.top, 4))
                out[key] = out.get(key, 0) + 1
        return out
    m, p, q = items(merged), items(parent_only), items(macros_only)  # noqa: F821
    cells = json.load(open(cells_json))  # noqa: F821
    halo = float(g.get("halo_um", "1.0"))

    def where(b):
        for rec in cells["hard_core_insts"]:
            x0, y0, x1, y1 = rec["bbox"]
            if b[0] < x1 + halo and b[2] > x0 - halo and b[1] < y1 + halo and b[3] > y0 - halo:
                return "HARDCORE", rec["master"]
        for rec in cells["empty_allowed"]:
            x0, y0, x1, y1 = rec["bbox"]
            if b[0] < x1 and b[2] > x0 and b[1] < y1 and b[3] > y0:
                return "UNCHECKED", rec["master"]
        return "PARENT", None
    new, per = [], {}
    for k, n in m.items():
        extra = n - p.get(k, 0) - q.get(k, 0)
        if extra <= 0:
            continue
        zone, mst = where(k[1:])
        new.append(dict(category=k[0], bbox=list(k[1:]), count=extra, zone=zone, master=mst))
        per.setdefault(k[0], {}).setdefault(zone, 0)
        per[k[0]][zone] += extra
    tot = lambda d: sum(d.values())
    res = dict(merged_markers=tot(m), parent_only_markers=tot(p), macros_only_markers=tot(q),
               new_markers=sum(x["count"] for x in new),
               new_hardcore=sum(x["count"] for x in new if x["zone"] == "HARDCORE"),
               new_unchecked=sum(x["count"] for x in new if x["zone"] == "UNCHECKED"),
               new_parent=sum(x["count"] for x in new if x["zone"] == "PARENT"),
               per_category=per, new=new[:2000], halo_um=halo)
    json.dump(res, open(out_file, "w"), indent=1)  # noqa: F821
elif mode == "window":
    margin = float(g.get("margin_um", "5"))
    cells = json.load(open(cells_json))  # noqa: F821
    ly = pya.Layout()
    ly.read(in_gds)  # noqa: F821
    top = [ly.cell(i) for i in ly.each_top_cell()][0]
    wins = []
    for n, rec in enumerate(cells["hard_core_insts"]):
        x0, y0, x1, y1 = rec["bbox"]
        w = [round(x0 - margin, 10), round(y0 - margin, 10), round(x1 + margin, 10), round(y1 + margin, 10)]
        box = pya.Box(int(round(w[0] / ly.dbu)), int(round(w[1] / ly.dbu)), int(round(w[2] / ly.dbu)), int(round(w[3] / ly.dbu)))
        ci = ly.clip(top.cell_index(), box)
        c = ly.cell(ci)
        c.name = "WIN%d" % n
        c.flatten(-1, True)
        o = pya.SaveLayoutOptions()
        o.format = "GDS2"
        o.select_all_cells = False
        o.add_this_cell(ci)
        ly.write("%s_%d.gds" % (out_prefix, n), o)  # noqa: F821
        ly.delete_cell_rec(ci)
        wins.append(dict(i=n, master=rec["master"], bbox=w))
    json.dump(wins, open(out_prefix + "_windows.json", "w"), indent=1)  # noqa: F821
elif mode == "shorts":
    LAYERS = dict(M1=19, V1=21, M2=20, V2=25, M3=30, V3=35, M4=40, V4=45, M5=50, V5=55, M6=60, V6=65, M7=70, V7=75, M8=80, V8=85, M9=90, V9=95)
    wins = json.load(open(win_dir + "/merged_windows.json"))  # noqa: F821
    for w in wins:
        i = w["i"]
        regs = {}
        for kind in ("parent_only", "macros_only"):
            ly = pya.Layout()
            ly.read("%s/%s_%d.gds" % (win_dir, kind, i))  # noqa: F821
            top = [ly.cell(j) for j in ly.each_top_cell()][0]
            regs[kind] = (ly, {n: (pya.Region(top.begin_shapes_rec(ly.layer(l, 0))), pya.Region(top.begin_shapes_rec(ly.layer(l, 251)))) for n, l in LAYERS.items()})
        dbu = regs["parent_only"][0].dbu
        out = {}
        for n in LAYERS:
            par = regs["parent_only"][1][n][0]
            core, pins = regs["macros_only"][1][n]
            ov = short_overlap(par, core, pins)
            boxes = [[round(p.bbox().left * dbu, 10), round(p.bbox().bottom * dbu, 10), round(p.bbox().right * dbu, 10), round(p.bbox().top * dbu, 10)] for p in ov.each()]
            if boxes:
                out[n] = boxes
        json.dump(out, open("%s/shorts_%d.json" % (win_dir, i), "w"))  # noqa: F821
elif mode == "selftest":
    import os
    core = pya.Layout()
    core.read(core_gds)  # noqa: F821
    ctop = [core.cell(i) for i in core.each_top_cell()][0]
    dbu = core.dbu
    cb = ctop.bbox()
    off = pya.Trans(int(round(50 / dbu)), int(round(50 / dbu)))
    # a long core M4 wire (layer 40/0) to overlap, and any core shape on 40 for the V6 seed position
    m4 = pya.Region(ctop.begin_shapes_rec(core.layer(40, 0)))
    m4.merge()
    m4pins = pya.Region(ctop.begin_shapes_rec(core.layer(40, 251))).merged()
    target = None
    for p_ in m4.each():
        b = p_.bbox()
        if max(b.width(), b.height()) >= 800 and min(b.width(), b.height()) >= 40 and (pya.Region(b) & m4pins.sized(2000)).is_empty():
            target = b
            break
    if target is None:
        for p_ in m4.each():
            b = p_.bbox()
            if max(b.width(), b.height()) >= 800 and (pya.Region(b) & m4pins).is_empty():
                target = b
                break
    if target is None:
        raise RuntimeError("selftest: no core M4 wire away from the pins")
    # collinear sub-box in the middle of the wire (stays inside it: no bend, no new edge on the layer)
    if target.width() >= target.height():
        short_box = pya.Box(target.left + target.width() // 2 - 200, target.bottom, target.left + target.width() // 2 + 200, target.top)
    else:
        short_box = pya.Box(target.left, target.bottom + target.height() // 2 - 200, target.right, target.bottom + target.height() // 2 + 200)
    pl, pad = None, None
    for l_ in (50, 40, 30):
        pr = pya.Region(ctop.begin_shapes_rec(core.layer(l_, 251))).merged()
        for p_ in pr.each():
            b = p_.bbox()
            if b.width() >= 16 and b.height() >= 16:
                pl, pad = l_, pya.Box(b.left + 4, b.bottom + 4, b.right - 4, b.top - 4)
                break
        if pl:
            break
    if pl is None:
        raise RuntimeError("selftest: the core GDS has no PIN-purpose (datatype 251) shape")
    # F1 seed: a parent M4 box that ABUTS the end of the core wire with zero gap (merges into one polygon, no deck marker, no area overlap)
    if target.width() >= target.height():
        abut_box = pya.Box(target.right, target.bottom, target.right + 200, target.top)
    else:
        abut_box = pya.Box(target.left, target.top, target.right, target.top + 200)
    abut_box = abut_box.moved(off.disp)
    short_box = short_box.moved(off.disp)
    # One 32 nm via in each constituent. Only the assembled geometry has a 30 nm gap.
    cx = target.left + off.disp.x + int(round(1 / dbu))
    cy = target.bottom + off.disp.y + int(round(1 / dbu))
    via_width = int(round(0.032 / dbu))
    via_gap = int(round(0.030 / dbu))
    core_via = pya.Box(cx, cy, cx + via_width, cy + via_width)
    parent_via = core_via.moved(via_width + via_gap, 0)
    # F2 seed: core M8 shape and an overlapping parent M8 shape (above the BEOL deck's M7 limit: only the geometric check sees it)
    m8y = cy + int(round(2 / dbu))
    core_m8 = pya.Box(cx, m8y, cx + 800, m8y + 800)
    parent_m8 = pya.Box(cx + 400, m8y, cx + 1200, m8y + 800)
    for variant in ("clean", "seeded"):
        d = os.path.join(out_dir, variant)  # noqa: F821
        os.makedirs(d, exist_ok=True)
        if variant == "seeded":
            seeds = {"SHORT.M4": [[short_box.left, short_box.bottom, short_box.right, short_box.top],
                                  [abut_box.left, abut_box.bottom, abut_box.right, abut_box.top]],
                     "V6.S.1-2-3": [[core_via.right, cy, parent_via.left, cy + via_width]],
                     "SHORT.M8": [[parent_m8.left, m8y, core_m8.right, m8y + 800]]}
            with open(os.path.join(d, "seed_targets.json"), "w") as stream:
                json.dump(seeds, stream)
        for kind in ("merged", "parent_only", "macros_only"):
            ly = pya.Layout()
            ly.dbu = dbu
            top = ly.create_cell("PARENT")
            if kind != "parent_only":
                cc = ly.create_cell(ctop.name)
                cc.copy_tree(ctop)
                top.insert(pya.CellInstArray(cc.cell_index(), off))
            if kind != "macros_only":
                # legal landing: a parent M5 pad inside a core PIN-purpose shape (50/251, else 40/251): overlaps core metal, must NOT flag
                top.shapes(ly.layer(pl, 0)).insert(pad.moved(off.disp))
            if variant == "seeded" and kind != "macros_only":
                top.shapes(ly.layer(40, 0)).insert(short_box)
                top.shapes(ly.layer(40, 0)).insert(abut_box)
            if variant == "seeded":
                if kind != "parent_only":
                    top.shapes(ly.layer(80, 0)).insert(core_m8)
                if kind != "macros_only":
                    top.shapes(ly.layer(80, 0)).insert(parent_m8)
                if kind != "parent_only":
                    top.shapes(ly.layer(65, 0)).insert(core_via)
                if kind != "macros_only":
                    top.shapes(ly.layer(65, 0)).insert(parent_via)
            ly.write(os.path.join(d, kind + ".gds"))
        bb = ctop.bbox()
        x0, y0 = (bb.left + off.disp.x) * dbu, (bb.bottom + off.disp.y) * dbu
        x1, y1 = (bb.right + off.disp.x) * dbu, (bb.top + off.disp.y) * dbu
        json.dump(dict(filled={ctop.name: "core"}, hard_core_insts=[dict(inst="", master=ctop.name, bbox=[x0, y0, x1, y1])], empty_allowed=[], missing=[],
                       dbu=dbu), open(os.path.join(d, "parent_cells.json"), "w"))
else:
    raise RuntimeError("mode must be core, parent, compare, window or selftest")
