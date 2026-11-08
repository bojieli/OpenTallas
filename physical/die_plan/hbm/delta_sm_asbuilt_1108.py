"""HBM plan event SM-ASBUILT-1108 (DIE-HBM-92-SU-SM, family (4) q_sm0-3, OPTION 2 as ruled by DIE-HBM-92).

The d44v plan named the q_sm0-3 hard cores after the HNX-SM4P SM (32 hnx_rp3lp3h halves per type, split into
hnx_rp3h_gn/gs/xs/lc/tl by p6/p7).  The as-built native die binds a different SM: sm_N[EW]<q> =
ot_hbm_accel_smh_attn (dissolved), 8 columns x 2 ot_hbm_sm_attn_tile(_seed) + 8 ot_hbm_sm_attn_be(_seed) +
ot_hbm_sm_attn_front_static_nomarker + ot_smh_int8_tile + ot_smh_qs_reg (no hnx module anywhere, different leaf
function: attention-native column, register x-store with 4 SRAMs).  No kit can place a hnx core in the bound netlist,
and the hnx form cannot be made EQ to the as-built (DIE-HBM-92-SU-SM report 11-08).

This event re-plans the four q_sm types onto the AS-BUILT leaves, conservative form (every master <= ~150k ORFS cells
except static_front, ~308k est, under the 400k cap):

  per leaf (32 / type, ot_hbm_sm_attn_leafh)   u_xs  u_bdc  u_tcc.u_h0  u_tcc.u_h1  u_tcc.u_qk  u_tcc.u_merge
  per tile (16 / type)                         u_ptw  u_pte
  per column (8 / type)                        u_be  (CONTROL_DELAY per column -> 6 uniquified wrapper masters)
  front                                        u_front.u_converter  u_front.u_normal  u_front.g_i8w.u_i8w  u_front.u_p

Physical paths are explicit (u_bound.<bound leaf>.<inner path>), masters are the RTL modules at those paths (the BE
leaves take wires-only wrappers ot_hbm_sm_attn_be{,_seed}__cd<N> through asbuilt.substitute_inst so each parameter
set has its own master; the wrapper instantiates the as-built module with the as-built parameters, so the bound
netlist is unchanged up to one hierarchy level).  Each core gets a port-exact pin table (names, widths and
directions from the elaborated bound hierarchy), a centre clock entry on the 4.32 PG lattice, macro sites for its
SRAMs, and a slot in the old tile slots (tile cores) or in the SM driver strip (BE + front).  The 352 hnx cores, their
clock taps / entries / core_conns rows and the q_sm hard reset trees (resets are as built: the tile / leaf reset
relays drive every core reset pin) are removed; compiler_core_delta S2.extra.SM 7 -> 0 (the +7 leaf latency was the
hnx split's; the as-built leaf has none).

Pure functions + a main that writes a hardlinked copy of the plan dir with only the changed files rewritten.
Re-appliable on any plan dir of the chain whose q_sm types still carry the hnx form:

    delta_sm_asbuilt_1108.py event BASE_PLAN_DIR --hier H/hier_{t}.json --bound-rtl RTL --lef-dir LEF --out-dir OUT
    delta_sm_asbuilt_1108.py contained EARLIER_DIR OUT     (every entry of EARLIER is in OUT unchanged, except the
                                                            entries this event owns)
    delta_sm_asbuilt_1108.py wrappers ... / manifest --asbuilt HEAD.json --rules R --out HEAD_sm.json
"""
import argparse
import collections
import copy
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hbm_arch"))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import cores_b2 as CB  # noqa: E402

EVENT = "SM-ASBUILT-1108"
LANE = "DIE-HBM-92-SU-SM"
TAG = "smab1108"
TYPES = ("q_sm0", "q_sm1", "q_sm2", "q_sm3")
G = 8.64
LAT = 4.32
UTIL = 0.5                     # std-cell utilisation the outlines are sized for (ORFS cell estimate)
MACRO_GAP = 8.64
BE_CD = {0: 21, 1: 17, 2: 13, 3: 9, 4: 9, 5: 13, 6: 16, 7: 20}      # as-built CONTROL_DELAY per column (bound RTL)
SEED_BE = (0, 7)

# master key -> (inner path below the bound leaf, cell estimates).  cells_yosys / area: r18g hierarchical yosys ASAP7
# stat (physical/die_plan/hbm/sm_split/inputs/sm_child_cells_r18g.json); cells_orfs: closed-run calibration
# (gen_sm_split.CAL) or yosys x the class ratio; 'basis' says which.
LEAF = [("xs", "u_xs"), ("bdc", "u_bdc"), ("h0", "u_tcc.u_h0"), ("h1", "u_tcc.u_h1"), ("qk", "u_tcc.u_qk"),
        ("merge", "u_tcc.u_merge")]
TILE = [("ptw", "u_ptw"), ("pte", "u_pte")]
FRONT = [("kv", "u_front.u_converter"), ("nf", "u_front.u_normal"), ("i8w", "u_front.g_i8w.u_i8w"), ("ps", "u_front.u_p")]
EST = {
    "ot_hbm_accel_smh_xs": dict(yosys=54674, orfs=107190, area=6995.2, dff=14745, basis="MEASURED-SYNTH r18g + CAL smh_xs_p192d (ORFS)"),
    "ot_hbm_accel_smh_bdc": dict(yosys=60410, orfs=60651, area=6926.2, dff=10866, basis="MEASURED-SYNTH r18g + CAL smh_bdc_ref (ORFS)"),
    "ot_hbm_accel_smh_tcl_gu": dict(yosys=48200, orfs=42938, area=5378.7, dff=8577, basis="MEASURED-SYNTH r18g + CAL smh_tcl_gu_ref (ORFS)"),
    "ot_hbm_accel_smh_tct": dict(yosys=65783, orfs=54226, area=7539.0, dff=9000, basis="CAL smh_tct_ref (yosys+ORFS); area = cells x 0.1146 um2 (bdc/tcl mean)"),
    "ot_hbm_sm_pv_merge": dict(yosys=80613, orfs=92030, area=8569.4, dff=12363, basis="MEASURED-SYNTH r18g + CAL smh_pvm_ref_s4a (ORFS)"),
    "ot_hbm_accel_smh_pt_w": dict(yosys=26426, orfs=58063, area=4433.0, dff=13213, basis="MEASURED-SYNTH r18g + CAL smh_pt_w_ref (ORFS)"),
    "ot_hbm_accel_smh_pt_e": dict(yosys=14826, orfs=49933, area=2487.4, dff=7413, basis="MEASURED-SYNTH r18g + CAL smh_pt_e_ref (ORFS)"),
    "ot_hbm_sm_attn_be": dict(yosys=41845, orfs=62768, area=4830.4, dff=8180, basis="MEASURED-SYNTH r18g be_by_hash (max); ORFS = yosys x 1.5 (register class, EST)"),
    "ot_hbm_sm_kv_line": dict(yosys=99977, orfs=119972, area=11200.0, dff=14520, basis="MEASURED-SYNTH r18g (MUT=0 kv_line); ORFS = yosys x 1.2 (EST)"),
    "ot_smh_static_front": dict(yosys=165789, orfs=307707, area=27286.3, dff=79818, basis="MEASURED-SYNTH r18g + gen_sm_split EST_SF (ORFS, fc_* calibrated)"),
    "ot_hbm_sm_i8w_front": dict(yosys=43487, orfs=65231, area=4563.7, dff=8315, basis="MEASURED-SYNTH r18g; ORFS = yosys x 1.5 (EST)"),
    "ot_hbm_sm_attn_pstore": dict(yosys=12000, orfs=18000, area=1400.0, dff=2600, basis="UNMEASURED: front remainder bound (front - static_front - kv_line - i8w = 20k incl. desc/rows/own); EST"),
}


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def snapup(v, g=G):
    return round(math.ceil(v / g - 1e-9) * g, 4)


def snap(v, g=LAT):
    return round(round(v / g) * g, 4)


# ------------------------------------------------------------------------------------------------- hierarchy
class Hier:
    """yosys write_json of the elaborated bound q_sm type (hierarchy + delete p:*): module keys, ports, cells."""

    def __init__(self, path, top):
        self.H = json.loads(Path(path).read_text())["modules"]
        self.top = top

    def resolve(self, path):
        """module key at a dotted instance path below top (yosys cell names keep generate scopes, 'g_lf[0].u_lh')."""
        mod, parts = self.top, path.split(".")
        while parts:
            cells = self.H[mod]["cells"]
            for n in range(len(parts), 0, -1):
                name = ".".join(parts[:n])
                if name in cells:
                    mod, parts = cells[name]["type"], parts[n:]
                    break
            else:
                raise KeyError(f"{path}: {parts[0]!r} not a cell of {mod}")
        return mod

    def ports(self, key):
        out = []
        for name, p in self.H[key]["ports"].items():
            if p.get("offset", 0) or p.get("upto", 0):
                raise ValueError(f"{key}.{name}: offset/upto port not supported")
            out.append((p["direction"], name, len(p["bits"])))
        return out

    def srams(self, key, pre=""):
        out = []
        for name, c in sorted(self.H[key]["cells"].items()):
            t = c["type"]
            if t.startswith("ot_sram_"):
                out.append((pre + name, t))
            elif t in self.H:
                out += self.srams(t, pre + name + ".")
        return out

    @staticmethod
    def base(key):
        """RTL module name of a yosys module key: $paramod$<hash>\\mod or $paramod\\mod\\P=v..."""
        if key.startswith("$paramod$"):
            return key.split("\\", 1)[1]
        if key.startswith("$paramod\\"):
            return key.split("\\")[1]
        return key


def bits(name, w):
    return [name] if w == 1 else [f"{name}[{i}]" for i in range(w)]


# ------------------------------------------------------------------------------------------------- bound RTL
_TILE = re.compile(r"(?m)^[ \t]*// as-built (sm_N[EW]\d)\.g_c\[(\d)\]\.g_p\[(\d)\]\.u_t\s*\n[ \t]*(ot_hbm_sm_attn_tile(?:_seed)?)\b.*?\s(u_u_sm_g_c_\d_g_p_\d_u_t)\s*\(")
_BE = re.compile(r"(?m)^[ \t]*// as-built (sm_N[EW]\d)\.g_c\[(\d)\]\.u_be\s*\n[ \t]*(\w+)\s*#\((.*?)\)\s*(u_u_sm_g_c_\d_u_be)\s*\(")
_FRONT = re.compile(r"(?m)^[ \t]*// as-built (sm_N[EW]\d)\.u_front\s*\n[ \t]*(\w+)\b.*?\s(u_u_sm_u_front)\s*\(")


def bound_leaves(text):
    """{'tiles': {(c, p): (module, inst)}, 'be': {c: (module, params text, inst)}, 'front': (module, inst), 'sm': name}"""
    tiles = {(int(m.group(2)), int(m.group(3))): (m.group(4), m.group(5)) for m in _TILE.finditer(text)}
    be = {int(m.group(2)): (m.group(3), m.group(4), m.group(5)) for m in _BE.finditer(text)}
    fr = _FRONT.search(text)
    sms = {m.group(1) for m in _TILE.finditer(text)}
    if len(tiles) != 16 or len(be) != 8 or not fr or len(sms) != 1:
        raise ValueError(f"bound SM leaves: {len(tiles)} tiles, {len(be)} be, front {bool(fr)}, sm {sms}")
    return dict(tiles=tiles, be=be, front=(fr.group(2), fr.group(3)), sm=sms.pop())


def be_wrapper_name(base, cd):
    return f"{base}__cd{cd}"


def be_params(ptext):
    return dict(re.findall(r"\.(\w+)\(([^()]*)\)", ptext))


def be_wrapper_text(base, cd, ports, ptext):
    """wires-only wrapper: same ports as the as-built BE, the as-built module with the as-built parameters inside."""
    name = be_wrapper_name(base, cd)
    hdr = ",\n".join(f"    {d} wire {'[%d:0] ' % (w - 1) if w > 1 else ''}{n}" for d, n, w in ports)
    conn = ", ".join(f".{n}({n})" for _, n, _ in ports)
    return (f"// {EVENT} ({LANE}): parameter-set master of the as-built {base} #({ptext}); wires only.\n"
            f"`default_nettype none\nmodule {name} (\n{hdr}\n);\n    {base} #({ptext}) u_be ({conn});\nendmodule\n"
            "`default_nettype wire\n")


# ------------------------------------------------------------------------------------------------- core geometry
def macro_dims(lef_dir, master):
    txt = (Path(lef_dir) / master / f"{master}.lef").read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt)
    return float(m.group(1)), float(m.group(2))


def macro_rows(macros, dims, w_max):
    """shelf rows of macros (as listed) within width w_max -> ([(name, master, x, y)], used w, used h) from (G, G)."""
    out, x, y, rowh, used = [], G, G, 0.0, 0.0
    for name, master in macros:
        mw, mh = dims[master]
        if x + mw + G > w_max + 1e-6 and x > G:
            x, y, rowh = G, round(y + rowh + MACRO_GAP, 4), 0.0
        out.append((name, master, round(x, 3), round(y, 3)))
        used = max(used, x + mw)
        x = round(x + mw + MACRO_GAP, 4)
        rowh = max(rowh, mh)
    return out, used + G, y + rowh + G


def outline_for(npins, area_std, macros, dims, h_fixed=None, w_fixed=None):
    """smallest 8.64-lattice outline that holds the std cells at UTIL beside the macros and the pins at CB cap."""
    marea = sum(dims[m][0] * dims[m][1] for _, m in macros)
    need = area_std / UTIL + marea * 1.25
    if h_fixed:
        h = h_fixed
        w = snapup(max(need / h, 2 * G))
    elif w_fixed:
        w = w_fixed
        h = snapup(max(need / w, 2 * G))
    else:
        s = math.sqrt(need)
        w = h = snapup(s)
    if macros:
        for _ in range(200):
            _, mw, mh = macro_rows(macros, dims, w)
            if mw <= w + 1e-6 and mh <= h + 1e-6:
                break
            if h_fixed:
                w = snapup(w + G)
            else:
                h = snapup(max(h, mh))
                if mw > w:
                    w = snapup(mw)
    while sum(CB.face_cap(f, w, h) for f in "NSEW") < npins * CB.SLACK:
        if h_fixed:
            w = snapup(w + G)
        elif w_fixed:
            h = snapup(h + G)
        else:
            w, h = snapup(w + G), snapup(h + G)
    return round(w, 4), round(h, 4)


def clock_entry(w, h, rects):
    """centre entry on the 4.32 PG lattice, island +-4.32, clear of macro rects (nearest free lattice point)."""
    cx, cy = snap(w / 2), snap(h / 2)
    cands = sorted(((cx + i * LAT, cy + j * LAT) for i in range(-40, 41) for j in range(-40, 41)),
                   key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p))
    for x, y in cands:
        isl = (x - LAT, y - LAT, x + LAT, y + LAT)
        if isl[0] < G or isl[1] < G or isl[2] > w - G or isl[3] > h - G:
            continue
        if all(isl[2] <= r[0] - 1.0 or isl[0] >= r[2] + 1.0 or isl[3] <= r[1] - 1.0 or isl[1] >= r[3] + 1.0
               for r in rects):
            return round(x, 3), round(y, 3)
    raise ValueError(f"no free clock entry in {w}x{h}")


def pin_table(ports, w, h, clock, entry):
    """port-exact pins: data/control pins spread over the four faces (CB.place_pins, blind faces balanced by width),
    the clock pin at the centre entry (M5, 0.048 x 0.48, as the d44v centre-entry cores)."""
    data = [(d, n, wd) for d, n, wd in ports if n != clock]
    faces = collections.Counter()
    cap = {f: CB.face_cap(f, w, h) for f in "NSEW"}
    groups = []
    for d, n, wd in sorted(data, key=lambda p: -p[2]):
        pref = ("W", "S", "N", "E") if d == "input" else ("E", "N", "S", "W")
        f = min(pref, key=lambda x: (faces[x] + wd) / max(1, cap[x]))
        faces[f] += wd
        groups.append((n, bits(n, wd), f, {f: 0.01}))
    pins, _ = CB.place_pins(groups, w, h)
    dirs = {b: d for d, n, wd in ports for b in bits(n, wd)}
    out = [dict(name=nm, layer=lay, x=round(x, 3), y=round(y, 3), dir=dirs[nm]) for nm, lay, x, y in pins]
    tr = min(CB.tracks(w, True), key=lambda a: abs(a - entry[0]))
    out.append(dict(name=clock, layer="M5", x=round(tr, 3), y=round(entry[1], 3), w=0.048, h=0.48, dir="input"))
    names = [p["name"] for p in out]
    want = sorted(b for _, n, wd in ports for b in bits(n, wd))
    if sorted(names) != want or len(set(names)) != len(names):
        raise ValueError("pin table not port-exact")
    sites = [(p["layer"], p["x"], p["y"]) for p in out]
    if len(set(sites)) != len(sites):
        raise ValueError("coincident pins")
    if any(not (0 <= p["x"] <= w and 0 <= p["y"] <= h) for p in out):
        raise ValueError("pin outside outline")
    return out


def clock_port(ports):
    c = [n for d, n, w in ports if d == "input" and w == 1 and re.fullmatch(r"clk|ck|ck_\w+|clk_\w+", n)]
    if len(c) != 1:
        raise ValueError(f"clock port ambiguous: {c}")
    return c[0]


def reset_ports(ports):
    return [n for d, n, w in ports if d == "input" and w == 1 and re.fullmatch(r"rst\w*", n)]


def regional(w, h, sinks):
    """core_clock_regions entry: ~4500 sinks per regional entry on a gx x gy grid."""
    n = max(1, math.ceil(sinks / 4500))
    gx = max(1, round(math.sqrt(n * w / h)))
    gy = max(1, math.ceil(n / gx))
    ents = []
    for j in range(gy):
        for i in range(gx):
            x0, x1, y0, y1 = w * i / gx, w * (i + 1) / gx, h * j / gy, h * (j + 1) / gy
            ents.append(dict(xy_um=[snap((x0 + x1) / 2), snap((y0 + y1) / 2)],
                             region_um=[round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]))
    return dict(sinks=sinks, entries=gx * gy, grid=[gx, gy], sinks_per_entry=math.ceil(sinks / (gx * gy)),
                regional_entries=ents)


# ------------------------------------------------------------------------------------------------- placement
def shelf(items, box):
    """items [(key, w, h)] in box (x0, y0, x1, y1) with G halo; tallest first -> {key: (x, y)} or None."""
    x0, y0, x1, y1 = box
    for order in ("h", "a"):
        key = dict(h=lambda it: (-it[2], -it[1], it[0]), a=lambda it: (-it[1] * it[2], it[0]))[order]
        pos, x, y, rowh, ok = {}, x0 + G, y0 + G, 0.0, True
        for k, w, h in sorted(items, key=key):
            if x + w > x1 - G + 1e-6:
                x, y, rowh = x0 + G, y + rowh + G, 0.0
            if x + w > x1 - G + 1e-6 or y + h > y1 - G + 1e-6:
                ok = False
                break
            pos[k] = (round(x, 4), round(y, 4))
            x = round(x + w + G, 4)
            rowh = max(rowh, h)
        if ok:
            return pos
    return None


def tile_slots(t):
    """old hnx tile slot boxes {(c, p): (x0, y0, x1, y1)} from the plan's u_sm_t<p><c>_{n,s} cores."""
    box = collections.defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
    for hc in t["hard_cores"]:
        m = re.match(r"u_sm_t([01])([0-7])_[ns]__", hc["inst"])
        if not m:
            raise ValueError(f"{hc['inst']}: not a hnx SM core")
        x, y = hc["origin_um"]
        w, h = hc["outline_um"]
        if hc.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        b = box[(int(m.group(2)), int(m.group(1)))]
        b[0], b[1], b[2], b[3] = min(b[0], x), min(b[1], y), max(b[2], x + w), max(b[3], y + h)
    if len(box) != 16:
        raise ValueError(f"{len(box)} tile slots")
    return {k: tuple(round(v, 4) for v in b) for k, b in box.items()}


def strip_box(t, slots):
    """the SM driver strip between the two tile rows, below the plan driver channel."""
    y_lo = max(b[3] for k, b in slots.items() if k[1] == 0)
    y_hi = min(b[1] for k, b in slots.items() if k[1] == 1)
    ch = [c["rect_um"] for c in t.get("channels", []) if c["rect_um"][2] > 0.8 * t["outline_um"][0]]
    if ch:
        y_hi = min(y_hi, ch[0][1])
    return (0.0, y_lo, t["outline_um"][0], y_hi)


# ------------------------------------------------------------------------------------------------- masters
def masters(hier, leaves, lef_dir):
    """{master: dict(ports, clock, resets, srams, est, kind)} and per-type instance rows [(inst, phys, master, role)]."""
    rows, M = [], {}

    def add(inst, phys_rel, role, master_override=None):
        key = hier.resolve(phys_rel)
        base = master_override or hier.base(key)
        ports = hier.ports(key)
        if base in M:
            if M[base]["key"] != key and not master_override:
                raise ValueError(f"{base}: two parameter sets ({M[base]['key'][:40]} / {key[:40]}) - not one design")
            if M[base]["ports"] != ports:
                raise ValueError(f"{base}: port mismatch between instances")
        else:
            est_key = base.split("__cd")[0].replace("_seed", "")
            M[base] = dict(key=key, ports=ports, clock=clock_port(ports), resets=reset_ports(ports),
                           srams=hier.srams(key), est=EST[est_key], role=role)
        rows.append(dict(inst=inst, physical_inst="u_bound." + phys_rel, master=base, role=role))

    for (c, p), (mod, binst) in sorted(leaves["tiles"].items()):
        pre = binst + (".u_seed" if mod.endswith("_seed") else "")
        for j in (0, 1):
            for tag, rel in LEAF:
                add(f"u_sm_c{c}p{p}_l{j}_{tag}", f"{pre}.g_lf[{j}].u_lh.{rel}", "leaf")
        for tag, rel in TILE:
            add(f"u_sm_c{c}p{p}_{tag}", f"{pre}.{rel}", "tile")
    for c, (mod, ptext, binst) in sorted(leaves["be"].items()):
        cd = int(be_params(ptext)["CONTROL_DELAY"])
        if cd != BE_CD[c] or mod.endswith("_seed") != (c in SEED_BE):
            raise ValueError(f"be column {c}: {mod} CONTROL_DELAY {cd} not the as-built pattern {BE_CD}")
        add(f"u_sm_c{c}_be", binst, "be", master_override=be_wrapper_name(mod, cd))
    fmod, finst = leaves["front"]
    for tag, rel in FRONT:
        add(f"u_sm_front_{tag}", f"{finst}.{rel}", "front")
    dims = {}
    for m in M.values():
        for _, s in m["srams"]:
            dims.setdefault(s, macro_dims(lef_dir, s))
    return M, rows, dims


def design_geometry(M, dims, strip_h, slot_w):
    """outline, pins, macro sites, clock entry per master; tile-level (pin-bound) cores take the slot inner width."""
    out = {}
    tile_w = math.floor((slot_w - 2 * G + 1e-6) / G) * G
    for name, m in sorted(M.items()):
        npins = sum(w for _, _, w in m["ports"])
        area = m["est"]["area"] * m["est"]["orfs"] / m["est"]["yosys"]
        hfix = round(strip_h - 2 * G - 1e-9, 4) if m["role"] in ("be", "front") else None
        hfix = snapup(hfix - G) if hfix and snapup(hfix) > hfix else hfix
        if hfix:
            hfix = math.floor(hfix / G) * G
        w, h = outline_for(npins, area, m["srams"], dims, h_fixed=hfix if m["role"] == "front" else None,
                           w_fixed=round(tile_w, 4) if m["role"] == "tile" else None)
        if m["role"] == "be" and h > (hfix or h):
            w, h = outline_for(npins, area, m["srams"], dims, h_fixed=hfix)
        sites, _, _ = macro_rows(m["srams"], dims, w)
        rects = [(x, y, x + dims[s][0], y + dims[s][1]) for _, s, x, y in sites]
        entry = clock_entry(w, h, rects)
        pins = pin_table(m["ports"], w, h, m["clock"], entry)
        marea = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)
        fill = area / max(1e-9, w * h - marea)
        out[name] = dict(w=w, h=h, pins=pins, sites=sites, rects=rects, entry=entry, npins=npins, area=area,
                         fill=round(fill, 4), macro_area=round(marea, 1))
    return out


def place_type(t, rows, geo):
    """origins per inst: leaf + tile cores in their old tile slot, BE + front in the driver strip."""
    slots = tile_slots(t)
    strip = strip_box(t, slots)
    pos = {}
    per = collections.defaultdict(list)
    rest = []
    for r in rows:
        g = geo[r["master"]]
        m = re.match(r"u_sm_c(\d)p(\d)_", r["inst"])
        if m:
            per[(int(m.group(1)), int(m.group(2)))].append((r["inst"], g["w"], g["h"]))
        else:
            rest.append((r["inst"], g["w"], g["h"]))
    for k, items in sorted(per.items()):
        got = shelf(items, slots[k])
        if got is None:
            raise ValueError(f"tile slot c{k[0]}p{k[1]} {slots[k]}: {len(items)} cores do not fit")
        pos.update(got)
    got = shelf(rest, strip)
    if got is None:
        raise ValueError(f"driver strip {strip}: {[(i, w, h) for i, w, h in rest]} do not fit")
    pos.update(got)
    return pos, slots, strip


# ------------------------------------------------------------------------------------------------- the event
def apply(plan, ce, ccr, cm, cc, hrt, ccd, hier_by_type, bounds, lef_dir):
    plan, ce, ccr, cm, cc, hrt, ccd = (copy.deepcopy(x) for x in (plan, ce, ccr, cm, cc, hrt, ccd))
    pts = plan["partition_types"]
    removed_modules = collections.Counter()
    first = None
    Mall, geo, ledger = None, None, dict(types={})
    for tname in TYPES:
        t = pts[tname]
        hier = hier_by_type[tname]
        leaves = bound_leaves(bounds[tname])
        M, rows, dims = masters(hier, leaves, lef_dir)
        if Mall is None:
            strip_h = strip_box(t, tile_slots(t))
            sw = min(b[2] - b[0] for b in tile_slots(t).values())
            Mall, geo = M, design_geometry(M, dims, strip_h[3] - strip_h[1], sw)
            first = (M, dims)
        elif {k: (v["key"], v["ports"]) for k, v in M.items()} != {k: (v["key"], v["ports"]) for k, v in Mall.items()}:
            raise ValueError(f"{tname}: SM leaf masters differ from {TYPES[0]}")
        old = t["hard_cores"]
        if any(not h["module"].startswith("hnx_rp3h_") for h in old):
            raise ValueError(f"{tname}: hard cores are not the hnx form")
        removed_modules.update(h["module"] for h in old)
        old_names = {h["inst"] for h in old}
        pos, slots, strip = place_type(t, rows, geo)
        new = []
        for r in rows:
            g = geo[r["master"]]
            m = Mall[r["master"]]
            e = dict(inst=r["inst"], module=r["master"], origin_um=list(pos[r["inst"]]), outline_um=[g["w"], g["h"]],
                     track_offset_um=[0.0, 0.0], pins_file=f"cores/{r['master']}__{g['w']:g}x{g['h']:g}__{TAG}.json",
                     physical_inst=r["physical_inst"], physical_master=r["master"], obs_max="M5",
                     note=f"{EVENT} ({LANE} 11-08, DIE-HBM-92 option 2): as-built {r['role']} core at "
                          f"{leaves['sm']}.{r['physical_inst'][len('u_bound.u_u_sm_'):]} (bound "
                          f"{r['physical_inst']}); port-exact pins; {m['est']['basis']}")
            if m["resets"]:
                rfm = dict(kind="internal", content="u_sm",
                           source=f"as-built SM reset relays (ot_hbm_sm_attn_tile u_rr / leafh rq / front + be rst_n "
                                  f"from the partition reset as bound): core reset port {m['resets'][0]}, reset as built")
                if m["resets"][0] == "rst_n":
                    rfm["pin"] = "rst_n"
                e["reset_from_master"] = rfm
            new.append(e)
        t["hard_cores"] = new
        for c in t["contents"]:
            if c["inst"] == "u_sm":
                c["module"] = "ot_hbm_accel_smh_attn"
                c["status"] = "reuse"
                c["note"] = (f"{EVENT}: SM slot = the as-built {leaves['sm']} (ot_hbm_accel_smh_attn, dissolved by the "
                             "bind): 16 attention tiles + 8 BE + front + int8 + qs regs; hard cores = its leaf/tile/"
                             "BE/front children (hard_cores[]); was hnx_sm_p3_rp3lp3x_8x2 (never in the as-built die)")
        # clock taps: one centre-entry tap per core (type frame)
        taps = [x for x in t["clock"]["taps"] if x["name"] not in old_names]
        for e in new:
            g = geo[e["module"]]
            taps.append(dict(name=e["inst"], kind="core", xy=[round(e["origin_um"][0] + g["entry"][0], 3),
                                                              round(e["origin_um"][1] + g["entry"][1], 3)],
                             insertion_ps=250.0, insertion_ff_ps=202.5, budget_owner=e["module"],
                             note=f"{EVENT}: plan centre clock entry of the as-built core (12.8a, clock_entries.json)"))
        t["clock"]["taps"] = taps
        t["reset"] = {k: v for k, v in t["reset"].items() if k != "depth"}
        # the hnx form was a pure assembly of hard cores (hard: true, gen skips it); the as-built form keeps
        # ~266k yosys of SM own logic, so the type is an ordinary kit type with hard-core macros
        t["hard"] = False
        soft = soft_estimate()
        t["cells"] = soft["yosys"]
        t["note"] = (f"{EVENT}: soft std cells = the as-built SM own logic outside the {len(new)} hard cores "
                     f"(leafh/native_col/tile own, int8, qs regs, dp stations, top glue) ~{soft['yosys']} yosys "
                     f"(~{soft['orfs']} ORFS est); hard children excluded")
        # clock_entries
        ent = {k: v for k, v in ce.get(tname, {}).items() if k not in old_names}
        for e in new:
            g = geo[e["module"]]
            x, y = g["entry"]
            ent[e["inst"]] = dict(source=f"master plan centre entry on the 4.32 PG lattice (12.8a) | {EVENT}: as-built core",
                                  stack=["M9", "M5"], latency_target_tt_ps=250.0, latency_target_ff_ps=202.5,
                                  xy_um=[x, y], island_um=[round(x - LAT, 3), round(y - LAT, 3), round(x + LAT, 3),
                                                           round(y + LAT, 3)],
                                  port=Mall[e["module"]]["clock"], merged_clock_ports=[], tap=e["inst"],
                                  module=e["module"], native_module=e["module"])
        ce[tname] = ent
        # core_conns: drop the hnx rows; new cores carry their clock tap (other connectivity unmeasured -> blind faces)
        rows_cc = {k: v for k, v in cc.get(tname, {}).items() if k not in old_names}
        for e in new:
            rows_cc[e["inst"]] = {Mall[e["module"]]["clock"]: [f"tap:{e['inst']}"]}
        cc[tname] = rows_cc
        hrt["types"].pop(tname, None)
        ledger["types"][tname] = dict(removed=len(old), added=len(new), sm=leaves["sm"],
                                      slots={f"c{k[0]}p{k[1]}": v for k, v in slots.items()}, strip=strip)
    # module-level side files
    counts = collections.Counter(h["module"] for tn in TYPES for h in pts[tn]["hard_cores"])
    for mod in list(removed_modules):
        cm["cores"].pop(mod, None)
        ccr["modules"].pop(mod, None)
    for mod, g in geo.items():
        m = Mall[mod]
        cm["cores"][mod] = dict(status="KNOWN" if m["srams"] else "NONE", outline_um=[g["w"], g["h"]],
                                macros=[dict(name=_esc(n), master=s, orient="R0",
                                             rect_um=[x, y, round(x + _d(first[1], s)[0], 3), round(y + _d(first[1], s)[1], 3)])
                                        for n, s, x, y in g["sites"]],
                                basis=f"{EVENT}: as-built SRAM paths from the elaborated bound hierarchy; shelf sites")
        r = regional(g["w"], g["h"], m["est"]["dff"])
        r.update(outline_um=[g["w"], g["h"]], instances=counts[mod], kept_signed=False,
                 note=f"{EVENT}: sinks = r18g dff count (EST)")
        ccr["modules"][mod] = r
    extra = ccd["S2"]["extra"]
    old_sm = extra.get("SM")
    extra["SM"] = 0
    ccd["basis"]["SM"] = (f"{EVENT}: as-built SM leaves (no hnx split): leaf result +0 (was {old_sm}: hnx_rp3lp3h "
                          "split LEAF RESULT +7)")
    ledger.update(removed_modules=dict(removed_modules), added_modules=dict(counts), ccd_sm=[old_sm, 0])
    return plan, ce, ccr, cm, cc, hrt, ccd, Mall, geo, ledger


def _esc(n):
    return n.replace("[", "\\[").replace("]", "\\]")


def _d(dims, s):
    return dims[s]


def soft_estimate():
    """SM own logic outside the hard cores (r18g yosys): leafh own 4524 x 32, native_col own 1666 x 32, tile own 1208
    x 16, int8 9140, qs regs ~18.8k flops (~25k), dp stations ~3.7k bits (~5k), top 1203, front own ~8k."""
    y = 4524 * 32 + 1666 * 32 + 1208 * 16 + 9140 + 25000 + 5000 + 1203 + 8000
    return dict(yosys=y, orfs=int(y * 1.4))


# ------------------------------------------------------------------------------------------------- io
def _write(path, obj, indent=1):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent) + "\n")
    if path.exists() or path.is_symlink():
        path.unlink()                                # never write through a hardlink into the base plan dir
    os.replace(tmp, path)


def _gz(path):
    path = Path(path)
    gz = path.with_name(path.name + ".gz")
    if gz.exists() or gz.is_symlink():
        gz.unlink()
        with open(path, "rb") as src, open(gz, "wb") as raw, \
                gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as dst:   # deterministic re-apply
            shutil.copyfileobj(src, dst)


SIDE = ("clock_entries.json", "core_clock_regions.json", "core_macros.json", "core_conns.json",
        "hard_reset_trees.json", "compiler_core_delta.json")


def main_event(a):
    src, dst = Path(a.plan_dir).resolve(), Path(a.out_dir)
    if os.path.realpath(a.plan_dir) != str(src) or Path(a.plan_dir).is_symlink():
        raise SystemExit("base must be a real directory path")
    if any(q.is_symlink() for q in src.rglob("*")):
        raise SystemExit("base contains symlinks: the hardlinked copy would share them, refusing")
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    plan = json.loads((src / "die_plan.json").read_text())
    side = [json.loads((src / f).read_text()) for f in SIDE]
    hier = {t: Hier(a.hier.replace("{t}", t), f"hbm_arch_{t}_bound") for t in TYPES}
    bounds = {t: (Path(a.bound_rtl) / f"hbm_arch_{t}.sv").read_text() for t in TYPES}
    new, ce, ccr, cm, cc, hrt, ccd, M, geo, ledger = apply(plan, *side, hier, bounds, a.lef_dir)
    shutil.copytree(src, dst, copy_function=os.link, symlinks=True)
    files_in = {f: fsha(src / f) for f in ("die_plan.json",) + SIDE}
    _write(dst / "die_plan.json", new)
    _gz(dst / "die_plan.json")
    for f, obj in zip(SIDE, (ce, ccr, cm, cc, hrt, ccd)):
        _write(dst / f, obj)
        _gz(dst / f)
    pins = {}
    for mod, g in sorted(geo.items()):
        pf = f"cores/{mod}__{g['w']:g}x{g['h']:g}__{TAG}.json"
        _write(dst / pf, g["pins"], indent=None)
        pins[pf] = dict(sha256=fsha(dst / pf), pins=len(g["pins"]), module=mod, outline_um=[g["w"], g["h"]],
                        fill=g["fill"], macro_area_um2=g["macro_area"], cells_orfs=M[mod]["est"]["orfs"],
                        cells_yosys=M[mod]["est"]["yosys"], basis=M[mod]["est"]["basis"], srams=len(M[mod]["srams"]),
                        clock=M[mod]["clock"], entry_um=list(g["entry"]))
    files_out = {f: fsha(dst / f) for f in files_in}
    a_hier = {t: dict(path=a.hier.replace("{t}", t), sha256=fsha(a.hier.replace("{t}", t))) for t in TYPES}
    receipt = dict(event=EVENT, lane=LANE, ruling="DIE-HBM-92 11-08: q_sm0-3 OPTION 2 (re-plan onto the as-built "
                   "attention leaves), option 1 withdrawn", plan_in=str(src / "die_plan.json"),
                   sha_in=files_in["die_plan.json"], sha_out=files_out["die_plan.json"], files_in=files_in,
                   files_out=files_out, pins_files=pins, hier=a_hier, bound_rtl=a.bound_rtl,
                   bound_sha256={t: fsha(Path(a.bound_rtl) / f"hbm_arch_{t}.sv") for t in TYPES},
                   ledger=ledger, soft=soft_estimate())
    _write(dst / f"{TAG}_event.json", receipt)
    readme = (dst / "README.md").read_text()
    (dst / "README.md").unlink()
    (dst / "README.md").write_text(
        readme + f"\n## {EVENT} ({LANE} {a.date})\n{src.name} ({files_in['die_plan.json'][:12]}) + {EVENT}: q_sm0-3 hard "
        f"cores re-planned onto the as-built SM leaves (DIE-HBM-92 option 2): {sum(v['added'] for v in ledger['types'].values())} "
        f"cores of {len(geo)} masters replace {sum(v['removed'] for v in ledger['types'].values())} hnx cores; port-exact "
        f"pin tables cores/*__{TAG}.json; q_sm hard reset trees dropped (resets as built); compiler_core_delta "
        f"S2.extra.SM {ledger['ccd_sm'][0]} -> 0; die_plan.json sha256 {files_out['die_plan.json'][:12]}. "
        f"Receipt {TAG}_event.json.\n")
    sums = []
    for line in (dst / "SHA256SUMS").read_text().splitlines():
        h, _, name = line.partition("  ")
        p = dst / name
        sums.append(f"{fsha(p) if p.is_file() else h}  {name}")
    for name in list(pins) + [f"{TAG}_event.json"]:
        if not any(s.endswith("  " + name) for s in sums):
            sums.append(f"{fsha(dst / name)}  {name}")
    (dst / "SHA256SUMS").unlink()
    (dst / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"{EVENT}: {files_in['die_plan.json'][:12]} -> {files_out['die_plan.json'][:12]}; masters {len(geo)}; "
          f"{json.dumps({k: (v['removed'], v['added']) for k, v in ledger['types'].items()})}")
    return 0


def main_wrappers(a):
    """BE parameter-set wrappers + the substitute_inst rows for the manifest (from one bound q_sm file)."""
    leaves = bound_leaves((Path(a.bound_rtl) / "hbm_arch_q_sm0.sv").read_text())
    hier = Hier(a.hier.replace("{t}", "q_sm0"), "hbm_arch_q_sm0_bound")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rules, files = [], []
    for c, (mod, ptext, binst) in sorted(leaves["be"].items()):
        cd = int(be_params(ptext)["CONTROL_DELAY"])
        name = be_wrapper_name(mod, cd)
        f = out / f"{name}.sv"
        if str(f) not in files:
            f.write_text(be_wrapper_text(mod, cd, hier.ports(hier.resolve(binst)), ptext))
            files.append(str(f))
        rules.append(dict(inst=rf"sm_N[EW]\d\.g_c\[{c}\]\.u_be", module=name,
                          reason=f"{EVENT}: parameter-set master of the as-built {mod} CONTROL_DELAY {cd} (wires only)"))
    Path(a.rules).write_text(json.dumps(dict(substitute_inst=rules, files=files), indent=1) + "\n")
    print(f"wrappers {len(files)} rules {len(rules)}")
    return 0


def main_manifest(a):
    ab = json.loads(Path(a.asbuilt).read_text())
    r = json.loads(Path(a.rules).read_text())
    out = copy.deepcopy(ab)
    for rule in r["substitute_inst"]:
        if any(x.get("module") == rule["module"] for x in out["substitute_inst"]):
            raise ValueError(f"{rule['module']} already substituted")
    out["substitute_inst"] = out["substitute_inst"] + r["substitute_inst"]
    out["files"] = list(dict.fromkeys(out.get("files", []) + r["files"]))
    out["prefer"] = list(dict.fromkeys(out.get("prefer", []) + r["files"]))
    head = Path(a.asbuilt).stem.replace("asbuilt_", "")
    out["note"] = (f"{LANE} {head}_sm: {head} + {EVENT} BE parameter-set wrappers (substitute_inst) | " + out.get("note", ""))
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"manifest {a.out} substitute_inst {len(ab['substitute_inst'])} -> {len(out['substitute_inst'])}")
    return 0


OWNED_ALLOWED = {"compiler_core_delta.json/basis/SM", "compiler_core_delta.json/S2/extra/SM"}


def contained_diffs(a_dir, b_dir):
    """entries of plan dir A missing or changed in B, skipping what this event owns (q_sm* / hnx_rp3h_* keys and the
    compiler_core_delta SM rows)."""
    bad = []

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in x:
                if str(k).startswith(("q_sm", "hnx_rp3h_")):
                    continue
                if k not in y:
                    bad.append(f"{path}/{k} missing")
                else:
                    walk(x[k], y[k], f"{path}/{k}")
        elif x != y:
            bad.append(path)

    for f in ("die_plan.json",) + SIDE:
        walk(json.loads((a_dir / f).read_text()), json.loads((b_dir / f).read_text()), f)
    bad = [b for b in bad if b not in OWNED_ALLOWED]
    bad += [f"missing file {q.relative_to(a_dir)}" for q in a_dir.rglob("*")
            if q.is_file() and not (b_dir / q.relative_to(a_dir)).exists()]
    return bad


def main_contained(a):
    bad = contained_diffs(Path(a.earlier), Path(a.out))
    print("CONTAINED" if not bad else f"NOT CONTAINED ({len(bad)}): {bad[:20]}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("event")
    e.add_argument("plan_dir")
    e.add_argument("--hier", required=True, help="yosys hierarchy json of the bound type, {t} = type name")
    e.add_argument("--bound-rtl", required=True)
    e.add_argument("--lef-dir", required=True, help="asap7_memory_macros dir")
    e.add_argument("--out-dir", required=True)
    e.add_argument("--date", default="2026-11-08")
    w = sub.add_parser("wrappers")
    w.add_argument("--hier", required=True)
    w.add_argument("--bound-rtl", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--rules", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--asbuilt", required=True)
    m.add_argument("--rules", required=True)
    m.add_argument("--out", required=True)
    c = sub.add_parser("contained")
    c.add_argument("earlier")
    c.add_argument("out")
    a = ap.parse_args(argv)
    return dict(event=main_event, wrappers=main_wrappers, manifest=main_manifest, contained=main_contained)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
