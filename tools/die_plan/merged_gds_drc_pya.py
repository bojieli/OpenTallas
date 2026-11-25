# KLayout (pya) half of tools/die_plan/merged_gds_drc.py.  Run as: klayout -b -r merged_gds_drc_pya.py -rd mode=... -rd ...
# mode=core   : routed core DEF -> GDS whose top cell is renamed to the core's MASTER name (std cells from the platform GDS).
# mode=parent : routed parent DEF -> three GDS with identical coordinates:
#               merged.gds      parent + every hard core filled with its real GDS (the sign-off geometry)
#               parent_only.gds parent with the hard cores left empty (baseline 1)
#               macros_only.gds only the hard-core instances (baseline 2)
#               Cells matching allow_empty (generated memory macros without GDS) stay empty in all three; their outlines
#               are written to empty_cells.json so the compare step can report markers there as UNCHECKED.
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


def fill_std(ly, top, gds_files):
    """clear every LEF-abstract child cell (keep VIA_ and DEF fill), then read the platform GDS (same names fill them)"""
    for c in ly.each_cell():
        if c.cell_index() != top.cell_index() and not c.name.startswith("VIA_") and not c.name.endswith("_DEF_FILL"):
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
                empties.append(rec)
            else:
                missing.add(nm)
    json.dump(dict(filled=filled, hard_core_insts=insts, empty_allowed=empties, missing=sorted(missing), dbu=ly.dbu),
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
else:
    raise RuntimeError("mode must be core, parent or compare")
