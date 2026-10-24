#!/usr/bin/env python3
"""CORE-S81-ENG (10-23): plan of the THREE hard cores that replace the monolithic dsdv_eng_rr (418,942 cells > 400k)
in S81 partition type eng__t1 (die plan v4.7b, claude/s81-p9-1023 2a90fc8c): E (window + lookup engine + head + XQ,
15 macros) and the two Engram hash layer halves H0 / H1 (rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv).
Writes, from this file only:
  inputs/core_pins/<module>.json  pin table (CORE-KS format: module, lef, source, pinhash, pins[name, layer, x, y]),
                                  core frame; M5 pins on N/S at x = 0.012 + k 0.048, M4 pins on E/W at y = 0.012 + k
                                  0.048 (= die tracks under the S81 core track_offset [0.108, 0.012]);
  cores/eng/lef/<module>.lef      abstract stub: SIZE + every signal pin rect + OBS M1-M5 (gen_plan_v4 NONFRAME_HC
                                  reads SIZE from it; replaced by the routed abstract after the gate);
  cores/eng/cores_eng.json        {module, outline_um, pins_file, lef, cells, macros, recipe, placement in eng__t1}.
Geometry: H0 | H1 sit side by side under E's S face (17.28 gap); every H out_res / in_w pin has the SAME x as its E
hx_res / hx_w partner, so the 1,220 half-cycle crossing wires are straight 17-um M5 drops.
usage (repo root): python3 physical/die_plan/s81/cores/eng/gen_eng_cores.py"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S81 = os.path.normpath(os.path.join(HERE, "..", ".."))
REPO = os.path.normpath(os.path.join(S81, "..", "..", ".."))
G = 8.64
TRACK_OFF = [0.108, 0.012]
TP = 0.048                        # M4 / M5 track pitch
EDGE = 4.32
EDGE_KEEP = 4 * 8.64              # gen_plan_v4 HC_EDGE_UM
GAP = 13.8                        # gen_plan_v4 HC_GAP_UM
EW, EH = 345.6, 466.56            # core E
HW, HH = 164.16, 267.84           # cores H0 / H1
HGAP = 17.28                      # H0 | H1 gap and E | H gap (>= 13.8, lattice)

RTL = ["rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv", "rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv",
       "rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv", "rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_rowbank_static_leaf.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_static.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_lookup_static.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_static14.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_lookup_ra512.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra512.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_lookup_ra640.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra640.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32_layer.sv",
       "rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra640_hx.sv",
       "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v",
       "rtl/lib/ot_rst_relay.sv", "rtl/lib/ot_rst_relay_bounded32.sv", "rtl/dsrom_sys/s81_dv/eng/ot_s81eng_reset3n32.sv",
       "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v",
       "physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_bb.v",
       "physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v",
       "rtl/hdc/ot_hdc_delay.sv", "rtl/dsrom_sys/engram/ot_dsrom_engram_token_map.sv", "rtl/hdc/v41/ot_hdc_engram_gather.sv",
       "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_prefix.sv",
       "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv",
       "rtl/dsrom_sys/s81_dv/eng/ot_s81eng_aq_n32.sv", "rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv",
       "rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv"]
HRTL = ["rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32.sv",
        "rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32_layer.sv",
        "rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv"]
DEFINES = ["OT_ENGRAM_CRCMAT", "OT_S81ENG_RR_N32", "OT_S81ENG_RR_MUL_N32"]
MAC = {"ot_rom_4096x72_m8": (38.016, 62.91), "ot_sram_1r1w_512x128_m4_r2c2": (174.096, 29.7),
       "ot_sram_1r1w_64x512_m1_r2c2": (171.288, 77.76), "ot_sram_1r1w_128x256_m1_r2c2": (94.824, 41.064)}
# measured Yosys (ORFS asap7lock synth, flat, TT libs) of each core top: synth_counts.json (from syn/*/synth_stat.txt)
CELLS = json.load(open(os.path.join(HERE, "synth_counts.json")))


def _phase(master):
    """y phase of the macro's M4 pins (first M4 rect centre), as gen_core_kit snaps it"""
    import re
    for d in ("asap7_memory_macros_v2", "asap7_memory_macros"):
        f = os.path.join(REPO, "physical", d, master, master + ".lef")
        if os.path.exists(f):
            mm = re.search(r"LAYER M4 ;\s*RECT\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+([\d.]+)", open(f).read())
            return (float(mm.group(1)) + float(mm.group(2))) / 2
    raise SystemExit(master)


def snap_up(master, y):
    """lowest y >= y that puts the macro's M4 pins on the core tracks 0.012 + k 0.048 (stack without overlap)"""
    ph = _phase(master)
    return round(0.012 + math.ceil((y + ph - 0.012) / TP - 1e-6) * TP - ph, 4)


def bus(name, w):
    return [name] if w == 1 else ["%s[%d]" % (name, i) for i in range(w)]


def trk(c):
    """nearest core-frame M4/M5 track 0.012 + k 0.048"""
    return round(0.012 + round((c - 0.012) / TP) * TP, 4)


def run(names, x0, step_tracks=5):
    """pins at x0 (snapped), x0 + step, ... (step = step_tracks tracks)"""
    k0 = round((x0 - 0.012) / TP)
    return [(n, round(0.012 + (k0 + step_tracks * i) * TP, 4)) for i, n in enumerate(names)]


def spread(names, L):
    """pins over the whole face [EDGE, L - EDGE], widest track-multiple pitch"""
    step = max(5, int(((L - 2 * EDGE) / max(len(names) - 1, 1)) / TP + 1e-9))
    span = (len(names) - 1) * step * TP
    return run(names, (L - span) / 2, step)


def put(face, lst, W, H):
    lay = "M5" if face in "NS" else "M4"
    out = []
    for n, c in lst:
        x, y = {"N": (c, round(H - 0.096, 4)), "S": (c, 0.096), "E": (round(W - 0.096, 4), c), "W": (0.096, c)}[face]
        assert EDGE - 1e-6 <= c <= (W if face in "NS" else H) - EDGE + 1e-6, (n, c)
        out.append(dict(name=n, layer=lay, x=x, y=y))
    return out


# ---------------------------------------------------------------------------------------------------- core plans
# Macros: every SRAM / ROM has its pins on its W and E edges (M4), so macros are stacked in vertically ABUTTED columns
# (side-by-side abutment would cover pins) with a std-cell channel on both pin edges.
def h_plan(L):
    """hash layer core: N face = out_res[575:0] (+ in_w at the end facing the H0|H1 gap), aligned to E's S face"""
    names_res = bus("out_res", 576)
    names_w = bus("in_w", 68)
    if L == 0:          # H0: out_res from the W end, in_w at the E end (towards the gap / E hx_w)
        lst = run(names_res, EDGE + 0.5) + run(names_w, HW - EDGE - 67 * 5 * TP - 0.3)
    else:               # H1: in_w at the W end, then out_res
        lst = run(names_w, EDGE + 0.5) + run(names_res, EDGE + 0.5 + 68 * 5 * TP + 0.6)
    pins = put("N", lst, HW, HH) + put("W", [("ck", trk(HH / 2))], HW, HH)
    return dict(name="h%d" % L, module="dsdv_eng_rr_h%d" % L, outline_um=[HW, HH], macros=[], pins=pins,
                faces=dict(N=["out_res", "in_w"], W=["ck"]), files=HRTL, util=0.65, half=["in_w"])


def e_plan(h0, h1):
    mac = []
    # ROM token map: two abutted columns of 4 (38.016 x 251.64), channels W / between / E of them
    for col in range(2):
        y = 103.68
        for r in range(4):
            y = snap_up("ot_rom_4096x72_m8", y)
            mac.append(dict(inst="u_win.u_map.m[%d].rom" % (4 * col + r), master="ot_rom_4096x72_m8",
                            at=[17.28 + col * 69.12, y]))
            y += 62.91
    # one abutted column: wait-line + beat-ring 64x512 (x3), history 512x128, row SRAMs 128x256 (x3)
    x = 151.2
    y = 43.2
    for n, m_ in [("u_xq.u_wl", "ot_sram_1r1w_64x512_m1_r2c2"), ("u_xq.u_b0", "ot_sram_1r1w_64x512_m1_r2c2"),
                  ("u_xq.u_b1", "ot_sram_1r1w_64x512_m1_r2c2"), ("u_win.u_h", "ot_sram_1r1w_512x128_m4_r2c2")] + \
                 [("u_lkp.u_e." + r, "ot_sram_1r1w_128x256_m1_r2c2") for r in ("u_row_e", "u_row_o", "u_row_a")]:
        y = snap_up(m_, y)
        mac.append(dict(inst=n, master=m_, at=[x, y]))
        y += MAC[m_][1]
    # S face: hash crossing, every pin at its H partner's x (H0 at E x 0, H1 at E x HW + HGAP)
    s = []
    for p in h0["pins"]:
        if p["name"].startswith("out_res["):
            s.append(("hx_res[%s" % p["name"][8:], p["x"]))
    for p in h1["pins"]:
        if p["name"].startswith("out_res["):
            s.append(("hx_res[%d]" % (576 + int(p["name"][8:-1])), round(p["x"] + HW + HGAP, 4)))
    # hx_w: one E pin per bit (2 loads: H0 + H1 in_w), in the H0|H1 gap between the two in_w groups
    s += run(bus("hx_w", 68), HW + 0.5, 5)
    pins = put("S", s, EW, EH)
    # N face: the V rung + f_ks, in the partition window order (vi_s, vo_s, vo_n | f_ks, vi_n)
    n = [x for g, w in (("vi_s", 276), ("vo_s", 276), ("vo_n", 276), ("f_ks", 53), ("vi_n", 276)) for x in bus(g, w)]
    pins += put("N", run(n, (EW - (len(n) - 1) * 5 * TP) / 2, 5), EW, EH)
    # W face: response / request chain ends + straps + status + clock / reset, spread over the face
    w = [x for g, k in (("st", 4), ("cfg_en", 1), ("cfg_layer", 1), ("cfg_rank", 2), ("rst_n", 1), ("ck", 1),
                        ("rco", 43), ("pci", 268)) for x in bus(g, k)]
    pins += put("W", spread(w, EH), EW, EH)
    return dict(name="e", module="dsdv_eng_rr_e", outline_um=[EW, EH], macros=mac, pins=pins,
                faces=dict(S=["hx_res", "hx_w"], N=["vi_s", "vo_s", "vo_n", "f_ks", "vi_n"],
                           W=["st", "cfg_en", "cfg_layer", "cfg_rank", "rst_n", "ck", "rco", "pci"]), files=RTL,
                util=0.5, half=["hx_res"])


def lef_stub(mod, W, H, pins, dirs):
    o = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "MACRO %s" % mod, "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", "  FOREIGN %s 0 0 ;" % mod, "  SIZE %.3f BY %.3f ;" % (W, H), "  SYMMETRY X Y ;"]
    for p in pins:
        hw = 0.012
        if p["layer"] == "M5":
            r = (p["x"] - hw, (H - 0.192) if p["y"] > H / 2 else 0.0, p["x"] + hw, H if p["y"] > H / 2 else 0.192)
        else:
            r = ((W - 0.192) if p["x"] > W / 2 else 0.0, p["y"] - hw, W if p["x"] > W / 2 else 0.192, p["y"] + hw)
        base = p["name"].split("[")[0]
        o += ["  PIN %s" % p["name"], "    DIRECTION %s ;" % dirs[base], "    USE %s ;" % (
            "CLOCK" if base == "ck" else "SIGNAL"), "    PORT", "      LAYER %s ;" % p["layer"],
              "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", "  END %s" % p["name"]]
    o += ["  OBS"] + ["    LAYER M%d ;\n      RECT 0.000 0.000 %.3f %.3f ;" % (i, W, H) for i in range(1, 6)] + ["  END"]
    o += ["END %s" % mod, "END LIBRARY"]
    return "\n".join(o) + "\n"


DIRS = dict(ck="INPUT", rst_n="INPUT", cfg_en="INPUT", cfg_layer="INPUT", cfg_rank="INPUT", st="OUTPUT", f_ks="INPUT",
            rco="OUTPUT", pci="INPUT", vi_s="INPUT", vo_s="OUTPUT", vi_n="INPUT", vo_n="OUTPUT", hx_w="OUTPUT",
            hx_res="INPUT", in_w="INPUT", out_res="OUTPUT")
# eng__t1 bus -> (core, port) from the S81 die plan ports + s81_lanes.tsv (svc_14 unit_o1 = etap_15 pco -> pci,
# rco -> etap_15 rci, seqhost engram_f_ks -> f_ks, s_6S vo -> vi_s, vo_s -> s_6S, vo_n -> s_6N, s_6N vo -> vi_n)
BUS_MAP = {"unit_i0": ["e", "pci"], "unit_o0": ["e", "rco"], "unit_i1": ["e", "f_ks"], "xtier_i0": ["e", "vi_s"],
           "xtier_o0": ["e", "vo_s"], "xtier_o1": ["e", "vo_n"], "xtier_i1": ["e", "vi_n"]}
CROSSING = dict(e_to_h=dict(hx_w=68), h0_to_e=dict(hx_res_0_575=576), h1_to_e=dict(hx_res_576_1151=576), bits=1220,
                cycles_added=0, half_cycle=True,
                registered="E hx_w = win_n (ck negedge flop) -> H kept kq17 window copies (posedge); H res_n (column "
                           "negedge flop) -> E res_c (posedge, no logic between) -- the monolith's own core<->hash hops",
                faces="E S face <-> H0 / H1 N faces, 17.28-um gap, partner pins at identical x (straight M5 drops)")


def pinhash(pins):
    return hashlib.sha256(json.dumps(sorted((p["name"], p["layer"], p["x"], p["y"]) for p in pins)).encode()).hexdigest()[:12]


def place(cores, t, PW, PH):
    """E origin on the 8.64 lattice (H0 / H1 hang under it at HGAP); legal (edge keep-off 34.56, gaps >= 13.8),
    NO added ft stations (gen_plan_v4.ft_stations_macro = the plan rule), minimum bit-weighted Manhattan length
    partition bus window -> E port centroid."""
    sys.path.insert(0, S81)
    import gen_plan_v4 as GP
    by = {c["name"]: c for c in cores}
    pins = by["e"]["_pins"]
    cent = {}
    for p in pins:
        cent.setdefault(p["name"].split("[")[0], []).append((p["x"], p["y"]))
    cent = {k: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for k, v in cent.items()}
    win = {}
    for b in t["buses"]:
        m = (b["window_um"][0] + b["window_um"][1]) / 2
        win[b["name"]] = ({"N": (m, PH), "S": (m, 0), "E": (PW, m), "W": (0, m)}[b["face"]], b["width"])
    dx, dy = TRACK_OFF

    def face_pt(face, w_, tt):
        q = w_[0] + tt * (w_[1] - w_[0])
        return {"E": (PW, q), "W": (0.0, q), "N": (q, PH), "S": (q, 0.0)}[face]
    sites = []
    for s in t.get("ft_slots", []):
        for i in range(64):
            tt = (i + 0.5) / 64
            ax_, ay_ = face_pt(s["in_face"], s["in_window_um"], tt)
            bx_, by_ = face_pt(s["out_face"], s["out_window_um"], tt)
            sites += [(ax_ + (bx_ - ax_) * j / s["stations"], ay_ + (by_ - ay_) * j / s["stations"])
                      for j in range(1, s["stations"])]
    best = None
    for i in range(int(EDGE_KEEP / G), int((PW - EDGE_KEEP - EW) / G) + 1):
        ex = i * G
        for j in range(int((EDGE_KEEP + HH + HGAP) / G), int((PH - EDGE_KEEP - EH - dy) / G) + 1):
            ey = j * G
            o = {"e": (ex, ey), "h0": (ex, ey - HGAP - HH), "h1": (ex + HW + HGAP, ey - HGAP - HH)}
            if o["h0"][1] < EDGE_KEEP:
                continue
            cost = 0.0
            for bn, ((wx, wy), w) in win.items():
                px, py = cent[BUS_MAP[bn][1]]
                cost += w * (abs(ex + dx + px - wx) + abs(ey + dy + py - wy))
            if best is not None and cost >= best[0]:
                continue
            cl = [dict(origin_um=list(o[n]), outline_um=by[n]["outline_um"]) for n in ("e", "h0", "h1")]
            if any(GP.ft_stations_macro(s, cl, PW, PH) > s["stations"] for s in t.get("ft_slots", [])):
                continue
            # strict: no planned station site (any bit, any j) inside a core + FT_HALO (stations stay where planned)
            if any(c["origin_um"][0] - GP.FT_HALO <= sx <= c["origin_um"][0] + c["outline_um"][0] + GP.FT_HALO and
                   c["origin_um"][1] - GP.FT_HALO <= sy <= c["origin_um"][1] + c["outline_um"][1] + GP.FT_HALO
                   for sx, sy in sites for c in cl):
                continue
            best = (cost, o)
    if best is None:
        raise SystemExit("no legal placement of E + H0 + H1 in eng__t1")
    for c in cores:
        c["placement"] = dict(type="eng__t1", origin_um=[round(v, 4) for v in best[1][c["name"]]], orient="R0",
                              track_offset_um=TRACK_OFF)
    return round(best[0])


def main():
    plan = json.load(open(os.path.join(S81, "die_plan.json")))
    t = plan["partition_types"]["eng__t1"]
    PW, PH = t["outline_um"]
    h0, h1 = h_plan(0), h_plan(1)
    plans = [e_plan(h0, h1), h0, h1]
    cores = []
    for pl in plans:
        W, H = pl["outline_um"]
        pins = pl["pins"]
        assert len({p["name"] for p in pins}) == len(pins)
        lef = "physical/die_plan/s81/cores/eng/lef/%s.lef" % pl["module"]
        os.makedirs(os.path.join(REPO, os.path.dirname(lef)), exist_ok=True)
        open(os.path.join(REPO, lef), "w").write(lef_stub(pl["module"], W, H, pins, DIRS))
        pf = "inputs/core_pins/%s.json" % pl["module"]
        json.dump(dict(module=pl["module"], lef=lef, pinhash=pinhash(pins),
                       source="CORE-S81-ENG 10-23 planned pins (gen_eng_cores.py): M5 N/S, M4 E/W, core-frame tracks "
                              "0.012 + k 0.048 (die tracks under track_offset %s)" % TRACK_OFF,
                       pins=pins), open(os.path.join(S81, pf), "w"), indent=0)
        cc = CELLS[pl["module"]]
        mac_a = sum(MAC[m["master"]][0] * MAC[m["master"]][1] for m in pl["macros"])
        free = (W - 8.64) * (H - 8.64) - sum((MAC[m["master"]][0] + 8.64) * (MAC[m["master"]][1] + 8.64)
                                             for m in pl["macros"])
        cores.append(dict(name=pl["name"], inst="u_eng.u_" + pl["name"], module=pl["module"], outline_um=[W, H],
                          pins_file=pf, lef=lef, pins=len(pins), cells=cc["cells"], std_area_um2=cc["std_area_um2"],
                          macro_area_um2=round(mac_a, 1), fill_of_free=round(cc["std_area_um2"] / free, 3),
                          macros=pl["macros"], faces=pl["faces"],
                          recipe=dict(files=pl["files"], defines=DEFINES, util=pl["util"], half_cycle_inputs=pl["half"]), _pins=pins))
    cost = place(cores, t, PW, PH)
    for c in cores:
        c.pop("_pins")
    json.dump(dict(schema="opentallas.s81.cores_eng.v1", type="eng__t1", type_outline_um=[PW, PH], bus_map=BUS_MAP,
                   crossing=CROSSING, bit_um_weighted_bus_cost=cost,
                   plan="claude/s81-p9-1023 v4.7b physical/die_plan/s81/die_plan.json sha256 %s" % hashlib.sha256(
                       open(os.path.join(S81, "die_plan.json"), "rb").read()).hexdigest()[:8],
                   rtl="claude/core-s81-eng-1023 rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv (base collb2-engrr "
                       "b8508b4d3)", cores=cores),
              open(os.path.join(HERE, "cores_eng.json"), "w"), indent=1)
    for c in cores:
        print(c["module"], c["outline_um"], "pins", c["pins"], "cells", c["cells"], "fill", c["fill_of_free"],
              "at", c["placement"]["origin_um"])


if __name__ == "__main__":
    main()
