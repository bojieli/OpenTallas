#!/usr/bin/env python3
"""HEAD-KITS-3 (2026-10-28): ORFS hard-core kit for ot_s81hd_lep_pair (the 4 hd_lep0N PAIR children, DIE-HEAD-9/10/11)
through the shared modern core-kit generator physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py (RTL lint, sdc_lint,
SELRANGE, face_guard, LEC, F1 per-corner vclk, F2 RCX RC, two-mode GRT, pg_connect, corners + signoff bundle).
Die-local driver, no shared-code edit:

  * view = the HEAD plan (physical/die_plan/s81_head/die_plan.json) hard core ot_s81hd_lep_pair 388.8 x 432, pins =
    cores/lep_pair_pins.json (plan pin view, DIE-HEAD-11) + the clock entry pin clk (the pin view excludes clk: "clk
    enters through the core clock entry"): clk = interior M5 clock-size port (0.048 x 0.48, COORD 10-27 shared slice
    rule) on the M5 track two tracks east of the centre rst_n pin (same y);
  * interior entry pins (rst_n, clk; > INTERIOR_TOL_UM from every face) are placed at their exact plan xy (METHODOLOGY
    12.8a, same form as gen_core_kit_kv.io_tcl), never projected onto a face; kit plan_pins.json carries their exact
    centres (= io.tcl), and the kit pin audit is main tools/die_plan/pin_audit.py (interior case), as KV kits do;
  * recipe = rtl/dsrom_sys/s81_head/ot_s81hd_lep_pair.sv (top, CHB 1) + the closure of its two leaves from the
    hd_lep0N plan sources; SRAM macros ot_sram_1r1w2c_256x64_m1 (36) / ot_sram_1r1w2c_32x64_m1 (19) as LEF + TT/FF lib
    at the 55 sites of results/die_head_1028/die_head_9_lep/lep_pair_plan_delta.json child_type.contents
    (place_macro -exact, generator grid snap);
  * defines OT_COLL_NATIVE32 + OT_COLL_NATIVE32_OFF = the qualified HEAD link profile (head_token_sources.py);
  * --face-shell off (lep_pair is a 0-cycle wrapper: no added face cycles), --core-insertion none (plan 250 ps).

    python3 tools/s81_head/head_lep_pair_kit.py --out KITROOT [--plan PLAN] [-- extra gen_core_kit_hbm args]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
import gen_core_kit_hbm as G  # noqa: E402

MODULE = "ot_s81hd_lep_pair"
SV = "rtl/dsrom_sys/s81_head/ot_s81hd_lep_pair.sv"
DELTA = "results/die_head_1028/die_head_9_lep/lep_pair_plan_delta.json"
# closure of ot_s81_mu72_lnland_nst + dsfd_coll_lane_w_safe8_ntf inside the hd_lep0N plan sources
FILES = [SV,
         "physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv",
         "rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv",
         "rtl/common/landed_parent/ot_pl_land.sv",
         "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
         "rtl/common/landed_parent/ot_pl_land_kept_enable.sv",
         "rtl/common/landed_parent/ot_pl_land_reset_forest.sv",
         "rtl/common/ot_link_credit_rx_b64.sv",
         "rtl/common/ot_link_credit_tx_rc.sv",
         "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv",
         "rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv",
         "rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv",
         "rtl/lib/ot_rst_relay.sv",
         "rtl/lib/ot_rst_relay_tree3.sv",
         "rtl/lib/ot_sram_oldread_b64.sv",
         "rtl/lib/ot_sram_showahead_1r1w.sv",
         "rtl/lib/ot_sram_showahead_b64.sv",
         "rtl/link/ot_link_crc32.sv"]
# the qualified HEAD collective-link profile (tools/s81_head/head_token_sources.py, S81 as-built b178_coll): without
# OT_COLL_NATIVE32, ot_s81ph_link_ep_safe4.sv uses nxt_rw2/una_rw2 undeclared (rtl_lint FAIL, first lep_pair run)
DEFINES = ("OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF")
INTERIOR_TOL_UM = 0.5
CLK_PORT_W_UM, CLK_PORT_L_UM = 0.048, 0.48
M5_PITCH, M5_OFF = 0.048, 0.024


def interior(p, w, h):
    return min(p["x"], w - p["x"], p["y"], h - p["y"]) > INTERIOR_TOL_UM


def io_tcl_interior(orig):
    """gen_core_kit_hbm.io_tcl with the 12.8a interior entry case (gen_core_kit_kv form)."""
    def io_tcl(pins, w, h, tag):
        face = [p for p in pins if not interior(p, w, h)]
        out, rows = orig(face, w, h, tag)
        lines = [out.rstrip("\n")]
        for p in pins:
            if not interior(p, w, h):
                continue
            clk = p["name"] == "clk"
            sz = (CLK_PORT_W_UM, CLK_PORT_L_UM) if clk else (G.LAYER_W[p["layer"]], G.PIN_LEN_UM)
            if p["layer"] not in ("M5",):
                raise SystemExit(f"interior pin {p['name']} must be M5 (vertical entry), got {p['layer']}")
            lines.append(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{p['x']:.4f} {p['y']:.4f}}} "
                         f"-pin_size {{{sz[0]:.4f} {sz[1]:.4f}}}   ;# 12.8a interior entry"
                         + (" (clock port >= 0.048x0.48)" if clk else ""))
            b, i = G.split_name(p["name"])
            rows.append(dict(bus=b, bit=i, layer=p["layer"], x=round(p["x"], 4), y=round(p["y"], 4), face="interior",
                             size=[sz[0], sz[1]], clock=clk))
        return "\n".join(lines) + "\n", rows
    return io_tcl


# SRAM sites (kit floorplan; replaces the DIE-HEAD-9 packing estimate, which failed kit_preflight macro_channels (no
# interior channel >= 10.8 um in any column) and put the centre rst_n / clock entry over an SRAM):
#   * pin bands kept free: W face (coll_i/coll_o) x < 30, S face (K side) y < 30;
#   * 36 x 256x64 (34.584 x 41.352) in 6 columns x 6 rows, x pitch 47.52 (channel 12.94), y pitch 56.16 (14.81), three
#     columns W and three E of a 60-um centre channel that holds the core clock / reset entry (194.5, 216);
#   * 19 x 32x64 (31.992 x 17.304): 2 rows of 7 above the 256x64 array (y pitch 30.24, channel 12.94) + 5 in the centre
#     channel well below the entry (y <= 168.5).  All origins on the 4.32 lattice; generator grid snap adds the M4 phase.
COL_X_A = (34.56, 82.08, 129.6, 224.64, 272.16, 319.68)
ROW_Y_A = tuple(round(30.24 + k * 56.16, 2) for k in range(6))
COL_X_B = (34.56, 82.08, 129.6, 177.12, 224.64, 272.16, 319.68)
ROW_Y_B = (367.2, 397.44)
CEN_B = [(177.12, round(30.24 + k * 30.24, 2)) for k in range(5)]


def sram_sites(srams, w, h):
    a = [c["inst"] for c in srams if c["module"].endswith("256x64_m1")]
    b = [c["inst"] for c in srams if c["module"].endswith("32x64_m1")]
    if len(a) != 36 or len(b) != 19 or len(srams) != 55:
        raise SystemExit(f"expected 36 + 19 SRAMs, got {len(a)} + {len(b)} of {len(srams)}")
    sa = [(x, y) for x in COL_X_A for y in ROW_Y_A]
    sb = [(x, y) for y in ROW_Y_B for x in COL_X_B] + CEN_B
    out = dict(zip(a, [list(v) for v in sa]))
    out.update(zip(b, [list(v) for v in sb]))
    return out


def build_inputs(plan_f, work):
    plan = json.loads(plan_f.read_text())
    t = plan["partition_types"]["hd_lep0N"]
    cores = [c for c in t.get("hard_cores", []) if c["module"] == MODULE]
    if len(cores) != 4 or len({tuple(c["outline_um"]) for c in cores}) != 1:
        raise SystemExit("expected 4 ot_s81hd_lep_pair hard cores of one outline in hd_lep0N")
    w, h = cores[0]["outline_um"]
    pv = json.loads((plan_f.parent / cores[0]["pins_file"]).read_text())
    pins = [dict(name=q["name"], layer=q["layer"], x=q["x"], y=q["y"]) for q in pv["pins"]]
    if any(q["name"] == "clk" for q in pins) or pv.get("excluded_clock") != ["clk"]:
        raise SystemExit("plan pin view changed: expected clk excluded (core clock entry)")
    rst = [q for q in pins if q["name"] == "rst_n"]
    if len(rst) != 1 or not interior(rst[0], w, h) or rst[0]["layer"] != "M5":
        raise SystemExit("expected one interior M5 rst_n entry pin")
    cx = round(rst[0]["x"] + 2 * M5_PITCH, 4)
    if abs((cx - M5_OFF) / M5_PITCH - round((cx - M5_OFF) / M5_PITCH)) > 1e-6:
        raise SystemExit(f"clk x {cx} off the M5 track lattice")
    clk = dict(name="clk", layer="M5", x=cx, y=rst[0]["y"])
    pins.append(clk)
    work.mkdir(parents=True, exist_ok=True)
    pf = work / "lep_pair_pins_kit.json"
    pf.write_text(json.dumps(pins, indent=0) + "\n")
    views = dict(plan=str(plan_f.resolve()), view_list=[dict(
        view=f"{MODULE}@kit", module=MODULE, outline_um=[w, h], pins_file=str(pf.resolve()),
        pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), instances=[c["inst"] for c in cores], placed=len(cores),
        recipe_keys=[MODULE])])
    vf = work / "views_lep_pair.json"
    vf.write_text(json.dumps(views, indent=1) + "\n")
    child = json.loads((ROOT / DELTA).read_text())["child_type"]
    if child["module"] != MODULE or [float(v) for v in child["outline_um"]] != [float(w), float(h)]:
        raise SystemExit("plan delta child_type does not match the plan core outline")
    srams = [c for c in child["contents"] if c.get("kind") == "sram"]
    sites = sram_sites(srams, w, h)
    mp = dict(source=f"{DELTA} child_type.contents (instances/masters); sites = head_lep_pair_kit.sram_sites",
              macro_placement=[dict(k=c["inst"], origin_um=sites[c["inst"]], orient="R0", macro=c["module"])
                               for c in srams])
    mf = work / "lep_pair_macros.json"
    mf.write_text(json.dumps(mp, indent=1) + "\n")
    # CHB = 1'b1 is the RTL default (the plan delta's params); no top-param override: the LEC gold frontend (slang)
    # refuses the sized-literal override "CHB=1'b1" (first lep_pair diag run: LEC UNPROVEN, elaboration failed)
    if not re.search(r"parameter\s*\[0:0\]\s*CHB\s*=\s*1'b1", (ROOT / SV).read_text()):
        raise SystemExit("ot_s81hd_lep_pair CHB default is no longer 1'b1: set the parameter explicitly")
    rec = {MODULE: dict(top=MODULE, files=FILES, defines=list(DEFINES), params={},
                        macros=sorted({c["module"] for c in srams}),
                        source="HEAD-KITS-3 head_lep_pair_kit.py: ot_s81hd_lep_pair (DIE-HEAD-9 LEP split child)")}
    return vf, mf, rec, clk, len(srams)


LAND_ARG = 'land=FG.kit_land(kd / "land_slots.json")'


def add_land_decl(text):
    """Append the land= declaration as the last argument of the single FG.guard(...) call in the kit's
    face_guard_core.py, whatever the other keyword arguments are (main d379a4b741c added straps=/dead= on a second line,
    which broke the former exact-string hook).  Fails closed on zero or several calls or an existing land= argument."""
    head = "r = FG.guard("
    if text.count(head) != 1:
        raise SystemExit("core face_guard invocation changed; review landing declaration hook")
    i = text.index(head) + len(head)
    depth, j = 1, i
    while depth:
        if j >= len(text):
            raise SystemExit("core face_guard invocation: unbalanced parentheses")
        depth += {"(": 1, ")": -1}.get(text[j], 0)
        j += 1
    call = text[i:j - 1]
    if re.search(r"\bland\s*=", call):
        raise SystemExit("core face_guard invocation already passes land=; review landing declaration hook")
    return text[:j - 1] + ", " + LAND_ARG + text[j - 1:]


def fix_interior(kd, w, h):
    """plan_pins.json: interior entries at their exact io.tcl centres; freeze pins/kit hashes recomputed; kit pin audit =
    main tools/die_plan/pin_audit.py (interior case)."""
    import shutil
    shutil.copyfile(G.TOOL / "pin_audit.py", kd / "pin_audit_core.py")
    rows = {(r["bus"] if r["bit"] is None else f"{r['bus']}[{r['bit']}]"): r
            for r in json.loads((kd / "pins.json").read_text()) if r["face"] == "interior"}
    pp = json.loads((kd / "plan_pins.json").read_text())
    for p in pp["pins"]:
        if p["name"] in rows:
            p["x"], p["y"] = rows[p["name"]]["x"], rows[p["name"]]["y"]
    pp["rule"] += "; 12.8a interior entry pins (rst_n, clk) at their exact centres (head_lep_pair_kit.py)"
    body = json.dumps(pp, indent=1) + "\n"
    (kd / "plan_pins.json").write_text(body)
    fz = json.loads((kd / "freeze.json").read_text())
    fz["pins_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    fz["pins_canon_sha256"] = G.plan_pins_canon_sha256(dict(pins=pp["pins"]), [w, h])
    fz["head_driver"] = dict(tool="tools/s81_head/head_lep_pair_kit.py", interior_pins=sorted(rows),
                             pin_audit="tools/die_plan/pin_audit.py")
    fz["kit_hash"] = G.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    return sorted(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=str(ROOT / "physical/die_plan/s81_head/die_plan.json"))
    ap.add_argument("rest", nargs="*", help="extra gen_core_kit_hbm.py args (after --)")
    a = ap.parse_args()
    out = Path(a.out)
    vf, mf, rec, clk, nm = build_inputs(Path(a.plan), out / "_inputs")
    G.io_tcl = io_tcl_interior(G.io_tcl)
    sys.argv = ["gen_core_kit_hbm.py", "--views", str(vf), "--view", f"{MODULE}@kit", "--out", str(out),
                "--recipe-key", MODULE, "--face-shell", "off", "--core-insertion", "none",
                "--macro-placement", str(mf), "--macro-inst-fmt", "{k}"] + a.rest
    G.main(recipe_overrides=rec)
    kd = out / re.sub(r"[^A-Za-z0-9_.-]", "_", f"{MODULE}@kit")
    # These four face buses enter the four-slot K->N landing writer.  The
    # decoded binary write count makes the slot write conditions exclusive;
    # face_guard still proves each own-Q hold mux and all four slot flops.
    # Declare the actual replicated boundary rather than adding a face stage.
    (kd / "land_slots.json").write_text(json.dumps({
        "schema": "opentallas.land_slots.v1",
        "buses": {b: {"D": 4, "form": "hold_mux"}
                  for b in ("k_lo_v", "k_lo_d", "k_li_r", "k_rxv")},
    }, indent=1) + "\n")
    # The generic hard-core runner supplies its own pin list directly to
    # guard(), so it must also pass the declaration (the partition CLI loads
    # land_slots.json automatically).  Keep all existing guard inputs intact.
    fg = kd / "face_guard_core.py"
    fg.write_text(add_land_decl(fg.read_text()))
    # Exact original-netlist matching; all nine entries remain untrusted SAT
    # obligations, including the one-to-one kept alias matches.
    from head_collective_lec_hints import collective_lec_hints
    (kd / "lec_hints.json").write_text(json.dumps(collective_lec_hints(), indent=1) + "\n")
    inter = fix_interior(kd, *json.loads((kd / "freeze.json").read_text())["outline_um"])
    print(json.dumps(dict(kit=str(kd), clk=clk, interior=inter, srams=nm)))


if __name__ == "__main__":
    main()
