#!/usr/bin/env python3
"""PROVISIONAL-VIEW launch of WAIT-DEP types (KW-PROV-1, COORD 2026-11-03 17:50 (C), OWNER "launch the never-launched
tile types").  Self-contained (python3 -I, staged by kit_wave into the item work dir like relay_bay.py): no repo imports.

A type whose child hard cores / contents have no signed view in the plan of record (probe flag planned = no lef/lib,
noview = lef but no lib) waited WAIT-DEP for every child sign-off.  It now builds against a PROVISIONAL abstract of each
such child, so type-level place / route failures surface early.  Still a hard view (macro), never flattened.

  make    --plan P --type T --out D [--src SRC] [--routed D/routed]
          per needed child module M of type T, first passing source wins:
            routed    D/routed/M/c<i>/{M.lef, M_tt.lib, M_ff.lib, meta.json}: the child's latest routed DRC-clean attempt
                      (kit_wave picks DRC 0 sign-off records of the autopilot queue, newest first).  Accepted when the
                      LEF is MACRO M with the plan outline and exactly the plan pin names, and both libs hold cell (M)
                      with the same port base names.  A plan entry that already names a lef (noview) keeps that plan
                      LEF; only the routed lib is taken (port names checked against the plan LEF).
            Optional routed meta: detailed_lef + detailed_receipt staged basenames and explicit detail_bloat_factor
            (0 or 1). The receipt comes from abstract_detail.py splice, adds its actual export bloat_factor, and
            must hash both the captured base and corrected output with matching-export pins/check_ok. The generator
            rechecks exact pins/PG/lower OBS using the selected --src helper. No export or P&R is run here.
            detail_pg_layer: true (explicit, bloat 1 only) details the PG pin layer itself, for a core with PG
            pins on its top OBS layer (nothing above PG to detail); see pg_layer_detail_layers.
            contract  blackbox LEF from the plan outline + pins_file (pin directions: pins_file dir, plan LEF, child
                      RTL header) with OBS M1..obs_max (default M5 = 12.1a ceiling; M7 gave PDN-0006 on M5 PG) less pin windows, VDD/VSS
                      stripes; budget lib (TT/FF) from the plan arrival contracts: both faces registered, IO_BUDGET x T
                      each side (gen_phys.sdc), clock pins carry the plan core-tap insertion as max/min_clock_tree_path.
          writes D/views/M/{M.lef, M_tt.lib, M_ff.lib}, the overlay plan dir D/plan (links to every entry of the plan
          dir + the plan file with ONLY type T's entries of those children bound to the provisional views), and the
          marker D/provisional_views.json (status PROVISIONAL).  Prints 'PROV_JSON {...}'.  Exit 3 when a child has
          neither source (e.g. pin directions unknown): the type FAILs PLAN with that reason.
  resign  --kit K --child M=LEF,TT_LIB,FF_LIB [...] [--image I] [--dry-run]
          STA-only re-sign on the child's SIGNED view, same routed DB (no re-route): checks the signed LEF against the
          kit's provisional LEF (same pin names, centres within 0.05 um, signed OBS top layer <= provisional), copies
          the signed libs over the kit's macro lib names, marks the child final (sha256) and the marker FINAL when all
          children are final, then runs the kit's own signoff.py into K/signoff_resign_<ts>.  Exit 4 = LEF changed:
          RE-ROUTE (the normal late-ECO / stage-resume loop), nothing changed in the kit.

The marker is what keeps a PROVISIONAL result out of the count: the autopilot probe (autopilot.PROBE_CLASSIFY) turns a
SIGNED record of a kit whose provisional_views.json is not FINAL into LOCAL_PASS_NEEDS_PARENT (WAIT-PARENT,
provisional.tsv, never archived / signed.tsv), and kit_wave writes <work>/gen/PROVENANCE.json verdict PROVISIONAL so
release_tree_plan.prov() never versions the kit's own signoff.json.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

SCHEMA = "opentallas.provisional_views.v1"
RULE = ("COORD 2026-11-03 17:50 (C) PROVISIONAL-VIEW launch (KW-PROV-1): built on provisional child abstracts, never "
        "counted; STA-only re-sign on the signed child lib, no re-route")
IO_BUDGET = 0.2                 # = gen_phys.IO_BUDGET: each side of a registered seam
OUT_SLEW_PS = 20.0
IN_CAP_FF = 1.0
PIN_ACCESS_BAND = 0.24  # um: smallest tested form with planar and via access on M4/M5 edge pins
RECT = {"M2": (0.072, 0.018), "M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084), "M6": (0.112, 0.032),
        "M7": (0.032, 0.112), "M8": (0.16, 0.08), "M9": (0.08, 0.16)}
CLOCK_RE = re.compile(r"^(clk|ck|clock|fclk)(_[A-Za-z0-9]+)*$|_(clk|ck)$", re.I)
DIRS = {"in": "INPUT", "input": "INPUT", "out": "OUTPUT", "output": "OUTPUT", "inout": "INOUT"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def is_clock(n):
    """clock pin by name, bit-indexed vector clock ports included (ck[0], clk_core[1])"""
    return bool(CLOCK_RE.search(split_bit(n)[0]))


def split_bit(n):
    m = re.match(r"^(.*)\[(\d+)\]$", n)
    return (m.group(1), int(m.group(2))) if m else (n, None)


# ------------------------------------------------------------------------------------------------------ plan side
def waiting(plan, tn):
    """[(entry, kind)] of EVERY entry of type tn that waits for a view: kind 'noview' (lef, no lib) or 'planned' (hard core, no lef)"""
    t = plan["partition_types"][tn]
    out = []
    hard = t.get("hard_cores") or []
    for c in hard + (t.get("contents") or []):
        if not isinstance(c, dict):
            continue
        kind = "noview" if c.get("lef") and not c.get("lib") else "planned" if (c in hard and not c.get("lef")) else None
        if kind:
            out.append((c, kind))
    return out


def needed(plan, tn):
    """waiting() with one entry per module: the entries a view is built for"""
    out, seen = [], set()
    for c, kind in waiting(plan, tn):
        m = str(c.get("module") or c.get("inst"))
        if m not in seen:
            seen.add(m)
            out.append((c, kind))
    return out


def stamp_views(plan, tn, children):
    """overlay plan: only type tn's waiting entries change (lef when missing, lib = provisional TT view).
    DIE-QC-69 11-04: every instance, not one per module: an unstamped repeat of a module has no site in macro_place.tcl,
    floats to rtl_macro_placer (MPL-0040 on cbf_q0x_s2) and has no physical_inst receipt for OT_RESET_CORE."""
    for c, _kind in waiting(plan, tn):
        v = children[str(c.get("module") or c.get("inst"))]
        if not c.get("lef"):
            c["lef"] = v["lef"]
        c["lib"] = v["tt"]


def resolve(path, roots):
    if not path:
        return None
    if os.path.isabs(path):
        return path if os.path.isfile(path) else None
    for r in roots:
        if r and os.path.isfile(os.path.join(r, path)):
            return os.path.abspath(os.path.join(r, path))
    return None


def plan_pins(entry, plan_dir):
    f = entry.get("pins_file")
    if not f:
        return None
    p = f if os.path.isabs(f) else os.path.join(plan_dir, f)
    if not os.path.isfile(p) and os.path.isfile(p + ".gz"):
        # DIE-HBM-91-KCLS 11-08 (class k1): the plan of record keeps large pin tables only as <pins_file>.gz
        # (d44v cores/ot_pdie_serdes_tx__285.12x207.36__d44v_split.json.gz); read the same table compressed.
        import gzip
        j = json.load(gzip.open(p + ".gz", "rt"))
    else:
        j = json.load(open(p))
    pins = j.get("pins") if isinstance(j, dict) else j
    # PROV-PINS-BUS (DIE-QC-81 11-05): plan pin tables come in two forms, {name,...} rows and {bus, bit,...} rows
    # (clock_entry_pins.pname). Bus/bit rows were dropped, so the QC su_c contract views (red2_leaf, su8_rst3, crh_rp1,
    # s8x_prog, s8x_vmr) carried only VDD/VSS and the parent kits placed against pinless children.
    out = []
    for x in pins:
        if not isinstance(x, dict):
            continue
        if not x.get("name") and x.get("bus"):
            x = dict(x, name=x["bus"] if x.get("bit") is None else f"{x['bus']}[{x['bit']}]")
        if x.get("name"):
            out.append(x)
    return out


def core_insertion(t, inst, pins):
    """{clock pin: (tt_ps, ff_ps)} from the type's core clock taps naming this inst (plan core-tap budgets)"""
    out = {}
    for tp in ((t.get("clock") or {}).get("taps") or []):
        if not isinstance(tp, dict) or tp.get("kind") != "core" or "insertion_ps" not in tp:
            continue
        nm = str(tp.get("name", ""))
        ff = float(tp.get("insertion_ff_ps", tp["insertion_ps"]))
        if nm == inst:
            sel = [p for p in pins if is_clock(p)]
        elif nm.startswith(inst + "."):
            sel = [p for p in (tp.get("merged_clock_ports") or [nm[len(inst) + 1:]]) if p in pins]
        else:
            continue
        for p in sel:
            out[p] = (float(tp["insertion_ps"]), ff)
    return out


# ------------------------------------------------------------------------------------------------------ LEF / lib parse
def lef_info(path):
    """(macro, (w, h) or None, {pin: (dir, use, layer, (cx, cy))}, obs top layer int or 0)"""
    macro, size, pins, cur, obs, in_obs, port = None, None, {}, None, 0, False, False
    for line in open(path, errors="replace"):
        s = line.strip()
        if macro is None:
            m = re.match(r"^MACRO\s+(\S+)", s)
            if m:
                macro = m.group(1)
            continue
        if s.startswith(f"END {macro}"):
            break
        m = re.match(r"^SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", s)
        if m:
            size = (float(m.group(1)), float(m.group(2)))
            continue
        if s == "OBS":
            in_obs = True
            continue
        if in_obs:
            if s == "END":
                in_obs = False
            m = re.match(r"^LAYER\s+M(\d+)", s)
            if m:
                obs = max(obs, int(m.group(1)))
            continue
        if cur is None:
            m = re.match(r"^PIN\s+(\S+)", s)
            if m:
                cur = dict(name=m.group(1), dir=None, use="SIGNAL", layer=None, xy=None)
                port = False
            continue
        if s == f"END {cur['name']}":
            pins[cur["name"]] = (cur["dir"], cur["use"], cur["layer"], cur["xy"])
            cur = None
            continue
        m = re.match(r"^DIRECTION\s+(\w+)", s)
        if m:
            cur["dir"] = m.group(1).upper()
        m = re.match(r"^USE\s+(\w+)", s)
        if m:
            cur["use"] = m.group(1).upper()
        if s.startswith("PORT"):
            port = True
        m = re.match(r"^LAYER\s+(\S+)", s)
        if m and port and cur["layer"] is None:
            cur["layer"] = m.group(1)
        m = re.match(r"^RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", s)
        if m and port and cur["xy"] is None:
            x0, y0, x1, y1 = map(float, m.groups())
            cur["xy"] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return macro, size, pins, obs


def lib_cell_ports(path, cell):
    """port base names of cell (cell) in a liberty file, or None when the cell is missing"""
    txt = open(path, errors="replace").read()
    m = re.search(r"\bcell\s*\(\s*\"?" + re.escape(cell) + r"\"?\s*\)\s*\{", txt)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth and i < len(txt):
        depth += (txt[i] == "{") - (txt[i] == "}")
        i += 1
    body = txt[m.end():i]
    names = set()
    for g in re.finditer(r"\b(pin|bus)\s*\(\s*\"?([^\")]+)\"?\s*\)\s*\{", body):
        names.add(split_bit(g.group(2).strip())[0])
    return names


def signal_bases(pins):
    return {split_bit(n)[0] for n, v in pins.items() if v[1] not in ("POWER", "GROUND")}


def lib_signal_ports(got, pins):
    """lib port names without PG pins: a signed-view lib may list VDD/VSS as pins, also when the LEF has none"""
    return got - ({"VDD", "VSS"} | {split_bit(n)[0] for n, v in pins.items() if v[1] in ("POWER", "GROUND")})


# ------------------------------------------------------------------------------------------------------ RTL directions
_DECL = re.compile(r"\b(input|output|inout)\b([^;()]*?)(?=[;)]|\b(?:input|output|inout)\b)", re.S)


def module_ports(body):
    body = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", body), flags=re.S)
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)            # (* keep *) attributes
    # Packed widths can contain parenthesized parameter arithmetic. Remove
    # ranges before the declaration matcher treats parentheses as boundaries.
    body = re.sub(r"\[[^\]]*\]", " ", body)
    out = {}
    for m in _DECL.finditer(body):
        rest = re.sub(r"\[[^\]]*\]", " ", m.group(2))
        rest = re.sub(r"\b(wire|reg|logic|signed|unsigned|var|bit|tri)\b", " ", rest)
        for tok in rest.split(","):
            mm = re.match(r"^\s*([A-Za-z_]\w*)", tok.split("=")[0])
            if mm:
                out.setdefault(mm.group(1), m.group(1))
    return out


_RTL_CACHE = {}
_RTL_ROOT_INDEX = {}
_MODULE_DECL = re.compile(r"^\s*module\s+([A-Za-z_]\w*)\b")


def rtl_module_files(root):
    """Process-local module->files index; one declaration scan per fixed source root."""
    if root in _RTL_ROOT_INDEX:
        return _RTL_ROOT_INDEX[root]
    index = {}
    # KW-FIX-35 11-08 (KW-PROV-1): a single `git grep --untracked` pass found NOTHING in a wave src whose .gitignore
    # is `*` (kw33/src_d95ec, kw35/src_0b72a: staged trees ignore everything; git then skips tracked files too), so
    # every contract child lost its RTL pin directions (QC cbf_q00 a10, slw_su_c a13; HBM q_su01/q_su11 prov_views).
    # Union of: tracked files (the pre-index behaviour), untracked RTL under rtl/ even when ignored, standard untracked.
    passes = (([], ["*.sv", "*.v", "*.svh"]),
              (["--untracked", "--no-exclude-standard"], [":(glob)rtl/**/*.sv", ":(glob)rtl/**/*.v", ":(glob)rtl/**/*.svh"]),
              (["--untracked"], ["*.sv", "*.v", "*.svh"]))
    git_ok = False
    for extra, spec in passes:
        try:
            result = subprocess.run(["git", "-C", root, "grep", *extra, "--null", "-n", "-E",
                                     r"^\s*module\s+[A-Za-z_][A-Za-z_0-9]*", "--", *spec],
                                    capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError):
            continue
        if "not a git repository" in (result.stderr or ""):
            break                                  # a staged non-git root: one probe, then the shallow walk
        if result.returncode not in (0, 1):
            continue
        git_ok = True
        for record in result.stdout.splitlines():
            fields = record.split("\0", 2)  # git grep -z -n: filename, line number, declaration
            if len(fields) != 3:
                continue
            match = _MODULE_DECL.match(fields[2])
            if match:
                files = index.setdefault(match.group(1), [])
                path = os.path.join(root, fields[0])
                if path not in files:
                    files.append(path)
    if git_ok:
        pass
    else:
        for dp, dn, fs in os.walk(root):
            # Preserve the staged, non-git root's shallow walk and exclusions.
            dn[:] = [x for x in dn if x not in (".git", "run", "results", "objects", "logs", "reports", "routed",
                                               "views", "plan", "__pycache__") and dp.count(os.sep) - root.count(os.sep) < 3]
            for filename in fs:
                if not filename.endswith((".sv", ".v")):
                    continue
                path = os.path.join(dp, filename)
                try:
                    with open(path, errors="replace") as source:
                        text = source.read()
                except OSError:
                    continue
                for match in re.finditer(r"\bmodule\s+([A-Za-z_]\w*)\b", text):
                    files = index.setdefault(match.group(1), [])
                    if path not in files:
                        files.append(path)
    _RTL_ROOT_INDEX[root] = index
    return index


def rtl_dirs(module, roots):
    """{port: input|output|inout} of `module` from every RTL file defining it under roots (the kit RTL of the parent
    first when staged, then the source tree / plan dir): the union, first definition wins per port"""
    key = (module, tuple(roots))
    if key in _RTL_CACHE:
        return _RTL_CACHE[key]
    pat = re.compile(r"\bmodule\s+" + re.escape(module) + r"\b")
    files = []
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        files.extend(rtl_module_files(r).get(module, []))
    dirs, first = {}, None
    for f in files:
        try:
            txt = open(f, errors="replace").read()
        except OSError:
            continue
        for m in pat.finditer(txt):
            e = txt.find("endmodule", m.start())
            for n, d in module_ports(txt[m.start():e if e > 0 else None]).items():
                dirs.setdefault(n, d)
            first = first or f
    _RTL_CACHE[key] = (dirs, first)
    return dirs, first


# DIE-HBM-91-KCLS 11-08: hard-core port tables of the core flow (source-relative), for plan modules without RTL of
# their own: the exact cut port table (rows [name, dir, width, lsb]) and the core recipe's RTL top
CORE_PORT_TABLES = ("physical/die_plan/hbm/cores/ports/ports_cut.json",)
CORE_RECIPES = ("physical/die_plan/hbm_arch_cores/recipes_b2.json", "physical/die_plan/hbm/cores/harden/recipes_split.json",
                "physical/die_plan/hbm/cores/harden/recipes_other.json", "physical/die_plan/hbm/cores/harden/recipes.json")


def core_table_dirs(module, roots):
    """{port: input|output|inout}, [sources] of `module` from the core port tables, then the RTL of its recipe top (a
    recipe keyed by the module or '<module>__<outline>'; one distinct top only).  Fills only pins RTL did not."""
    dirs, srcs = {}, []
    for r in roots:
        for rel in CORE_PORT_TABLES:
            f = os.path.join(r or "", rel)
            try:
                j = json.load(open(f))
            except (OSError, ValueError):
                continue
            ent = j.get(module) if isinstance(j, dict) else None
            rows = (ent.get(module) if isinstance(ent, dict) else None) or []
            got = {row[0]: row[1] for row in rows if isinstance(row, list) and len(row) >= 2 and row[1] in DIRS}
            if got:
                for n, d in got.items():
                    dirs.setdefault(n, d)
                srcs.append(f"port table {rel}")
    tops = set()
    pinned = []
    for r in roots:
        for rel in CORE_RECIPES:
            try:
                j = json.load(open(os.path.join(r or "", rel)))
            except (OSError, ValueError):
                continue
            for k, v in (j.items() if isinstance(j, dict) else ()):
                if (k == module or k.startswith(module + "__")) and isinstance(v, dict) and v.get("top"):
                    tops.add(v["top"])
                    for path, rev in v.get("files_at", {}).items():
                        pinned.append((r, v["top"], path, rev))
    if len(tops) == 1:
        top = next(iter(tops))
        rp, rf = rtl_dirs(top, roots)
        if rp:
            for n, d in rp.items():
                dirs.setdefault(n, d)
            srcs.append(f"recipe top {top}")
        # Some recipe RTL is explicitly pinned to an older source commit and
        # absent from the staged working tree. Read that exact module header.
        pat = re.compile(r"\bmodule\s+" + re.escape(top) + r"\b")
        for root, declared_top, path, rev in pinned:
            if declared_top != top:
                continue
            try:
                source = subprocess.run(["git", "-C", root, "show", f"{rev}:{path}"],
                                        capture_output=True, text=True, timeout=30)
            except (OSError, subprocess.SubprocessError):
                continue
            if source.returncode:
                continue
            for match in pat.finditer(source.stdout):
                end = source.stdout.find("endmodule", match.start())
                if end < 0:
                    continue
                got = module_ports(source.stdout[match.start():end])
                if got:
                    for n, d in got.items():
                        dirs.setdefault(n, d)
                    srcs.append(f"recipe file {path} at {rev}")
    return dirs, srcs


# plan-added pins (feedthroughs ft_*_i/_o, face ports) that no RTL header declares: the direction from the name suffix
NAME_DIR = [(re.compile(r"(?:^|_)(?:i|in)(?:_\d+)?$"), "INPUT"), (re.compile(r"(?:^|_)(?:o|out)(?:_\d+)?$"), "OUTPUT"),
            (re.compile(r"^(?:i|in)_"), "INPUT"), (re.compile(r"^(?:o|out)_"), "OUTPUT")]


RESET_RE = re.compile(r"^(?:a|s)?(?:rst|reset)(?:_n|_b|n)?(?:_[A-Za-z0-9]+)*$", re.I)


def name_dir(n):
    b = split_bit(n)[0]
    if is_clock(n) or RESET_RE.match(b):
        return "INPUT"                      # clock / reset entry pins of a core are inputs
    for rx, d in NAME_DIR:
        if rx.search(b):
            return d
    return None


# ------------------------------------------------------------------------------------------------------ writers
CONTRACT_OBS_DEFAULT = "M5"


def contract_obs_top(entry):
    """OBS top layer index of a contract abstract: the plan entry obs_max, else CONTRACT_OBS_DEFAULT (M5)"""
    return int(str(entry.get("obs_max") or CONTRACT_OBS_DEFAULT).lstrip("Mm") or 5)


def contract_obs(w, h, pins, obs_top):
    """OBS lines: blanket M1..obs_top, except an edge window PIN_ACCESS_BAND deep and +- that wide around each pin
    on its own layer and the layer above. A blanket on the pin layer leaves no access point at all (DRT-0073 on
    whichever pin of the master comes first), so the parent stops at pin_access. The rest of the edge band stays
    blocked, so a parent cannot run wires over a child that may use those layers. A pin further than the band
    from every edge gets no window."""
    b = PIN_ACCESS_BAND
    open_at = {}  # layer index -> {edge: [(lo, hi)]}
    for p in pins:
        n = int(str(p.get("layer") or "M4").lstrip("Mm"))
        x, y = float(p["x"]), float(p["y"])
        for edge, dist, along in (("W", x, y), ("E", w - x, y), ("S", y, x), ("N", h - y, x)):
            if dist <= b:
                for i in (n, n + 1):
                    open_at.setdefault(i, {}).setdefault(edge, []).append((along - b, along + b))
    out = []
    for i in range(1, obs_top + 1):
        out.append(f"    LAYER M{i} ;")
        edges = open_at.get(i)
        if not edges:
            out.append(f"      RECT 0 0 {w:.4f} {h:.4f} ;")
            continue
        rects = [(b, b, w - b, h - b)]
        for edge, lo, hi in (("S", 0.0, w), ("N", 0.0, w), ("W", b, h - b), ("E", b, h - b)):
            at = lo
            spans = []
            for a, c in sorted(edges.get(edge, [])) + [(hi, hi)]:
                if a > at:
                    spans.append((at, min(a, hi)))
                at = max(at, c)
            for a, c in spans:
                rects.append({"S": (a, 0.0, c, b), "N": (a, h - b, c, h),
                              "W": (0.0, a, b, c), "E": (w - b, a, w, c)}[edge])
        out += ["      RECT " + " ".join(f"{v:.4f}" for v in r) + " ;" for r in rects]
    return out


def merged_clock_pins(t, inst):
    """pins a merged core clock tap of the type names for inst (tap `<inst>.<base>` + merged_clock_ports)"""
    out = set()
    for tp in ((t.get("clock") or {}).get("taps") or []):
        if isinstance(tp, dict) and tp.get("kind") == "core" and str(tp.get("name", "")).startswith(inst + "."):
            out.update(tp.get("merged_clock_ports") or [])
    return out


def contract_lef(module, w, h, pins, dirs, obs_top, clock_pins=()):
    """blackbox LEF: plan pins (centre x/y, layer) with plan directions, OBS M1..obs_top, VDD/VSS M5/M4 stripes.
    DIE-HBM-92-GEN 11-08 (HBM q_b100..q_b103 gen phys "clk_pair[0]: actual LEF input clock required"): the pins of a
    merged core clock tap (clock_pins, merged_clock_pins) are USE CLOCK, as the contract lib already marks them
    clock : true and merged_core_clocks.pins requires; every other pin stays USE SIGNAL (other abstracts unchanged)."""
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {module}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {module} 0 0 ;", f"  SIZE {w:.4f} BY {h:.4f} ;", "  SYMMETRY X Y ;"]
    for p in pins:
        lay = p.get("layer") or "M4"
        rw, rh = RECT.get(lay, (0.024, 0.084))
        x0 = min(max(float(p["x"]) - rw / 2, 0.0), w - rw)
        y0 = min(max(float(p["y"]) - rh / 2, 0.0), h - rh)
        d = dirs.get(p["name"]) or dirs.get(split_bit(p["name"])[0])
        use = "CLOCK" if p["name"] in clock_pins else "SIGNAL"
        L += [f"  PIN {p['name']}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;",
              f"        RECT {x0:.4f} {y0:.4f} {x0 + rw:.4f} {y0 + rh:.4f} ;", "    END", f"  END {p['name']}"]
    # PG: vertical M5 stripes (M4 horizontal when the plan caps the core below M5), 4 per net, inside the outline
    vert = obs_top >= 5
    lay, span = ("M5", w) if vert else ("M4", h)
    sw = 0.288
    for k, (net, use) in enumerate((("VDD", "POWER"), ("VSS", "GROUND"))):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;"]
        for i in range(4):
            c = span * (2 * i + 1 + k) / 9.0
            r = (c - sw / 2, 0.0, c + sw / 2, h) if vert else (0.0, c - sw / 2, w, c + sw / 2)
            L.append("        RECT " + " ".join(f"{v:.4f}" for v in r) + " ;")
        L += ["    END", f"  END {net}"]
    L.append("  OBS")
    L += contract_obs(w, h, pins, obs_top)
    L += ["  END", f"END {module}", "END LIBRARY", ""]
    return "\n".join(L)


def contract_lib(module, corner, w, h, pins, dirs, clocks, period_ps):
    """budget liberty (time 1 ps): inputs setup IO_BUDGET*T - L / hold 0 vs the clock pin, outputs clock->out
    L + IO_BUDGET*T, clock pins max/min_clock_tree_path L (L = plan core-tap insertion of the corner, else 0)"""
    io = IO_BUDGET * period_ps
    buses = {}
    for p in pins:
        b, bit = split_bit(p["name"])
        buses.setdefault(b, set())
        if bit is not None:
            buses[b].add(bit)
    # clock pins by port (a vector clock port ck[0] is the bus ck: clock + tree path on its bit pins, related_pin "ck")
    lat = {}
    for c, v in clocks.items():
        lat.setdefault(split_bit(c)[0], v[0] if corner == "tt" else v[1])
    rel = sorted(lat, key=lambda c: (bool(buses.get(c)), c))[0] if lat else None
    L0 = lat.get(rel, 0.0) if rel else 0.0
    out = [f"library ({module}_{corner}) {{", "  delay_model : table_lookup;", '  time_unit : "1ps";',
           '  voltage_unit : "1V";', '  current_unit : "1mA";', '  pulling_resistance_unit : "1kohm";',
           "  capacitive_load_unit (1, ff);", "  nom_process : 1;", f"  nom_voltage : {0.77 if corner == 'ff' else 0.7};",
           f"  nom_temperature : {0 if corner == 'ff' else 25};", "  input_threshold_pct_rise : 50;",
           "  input_threshold_pct_fall : 50;", "  output_threshold_pct_rise : 50;", "  output_threshold_pct_fall : 50;",
           "  slew_lower_threshold_pct_rise : 10;", "  slew_upper_threshold_pct_rise : 90;",
           "  slew_lower_threshold_pct_fall : 10;", "  slew_upper_threshold_pct_fall : 90;",
           f"  /* {RULE}; budget view, not a timing model of a built core */"]
    widths = {}
    for b, bits in buses.items():
        if bits:
            widths[(max(bits), min(bits))] = f"bus_{max(bits)}_{min(bits)}"
    for (hi, lo), name in sorted(widths.items()):
        out += [f"  type ({name}) {{", "    base_type : array;", "    data_type : bit;", f"    bit_width : {hi - lo + 1};",
                f"    bit_from : {hi};", f"    bit_to : {lo};", "    downto : true;", "  }"]
    out += [f"  cell ({module}) {{", f"    area : {w * h:.4f};", "    dont_touch : true;", "    dont_use : true;",
            "    is_macro_cell : true;"]

    def sc(k, v):
        return f'        {k} (scalar) {{ values ("{v:.4f}"); }}'

    for b in sorted(buses):
        d = (dirs.get(b) or dirs.get(f"{b}[{min(buses[b])}]" if buses[b] else b) or "INPUT").lower()
        grp = f"    bus ({b}) {{" if buses[b] else f"    pin ({b}) {{"
        body = [grp]
        if buses[b]:
            body.append(f"      bus_type : bus_{max(buses[b])}_{min(buses[b])};")
        body.append(f"      direction : {d};")
        if b in lat and buses[b]:
            # a vector clock port as signed views write it: clock + tree path on each bit's pin group.  cores.lib_clocks
            # reads pin groups only, so a clock on the bus group read as "no clock pins" at gen (bk_sel__t2 ck[0]).
            l = lat[b]
            body.append(f"      capacitance : {IN_CAP_FF};")
            for bit in sorted(buses[b]):
                body += [f'      pin ("{b}[{bit}]") {{', "        direction : input;", "        clock : true;",
                         f"        capacitance : {IN_CAP_FF};"]
                for tt in ("max_clock_tree_path", "min_clock_tree_path"):
                    body += ["        timing () {", f"          timing_type : {tt};",
                             "          timing_sense : positive_unate;", "  " + sc("cell_rise", l),
                             "  " + sc("cell_fall", l), "        }"]
                body.append("      }")
        elif b in lat:
            l = lat[b]
            body += ["      clock : true;", f"      capacitance : {IN_CAP_FF};"]
            for tt in ("max_clock_tree_path", "min_clock_tree_path"):
                body += ["      timing () {", f"        timing_type : {tt};", "        timing_sense : positive_unate;",
                         sc("cell_rise", l), sc("cell_fall", l), "      }"]
        elif d == "input":
            body.append(f"      capacitance : {IN_CAP_FF};")
            if rel:
                for tt, v in (("setup_rising", io - L0), ("hold_rising", 0.0)):
                    body += ["      timing () {", f'        related_pin : "{rel}";', f"        timing_type : {tt};",
                             sc("rise_constraint", v), sc("fall_constraint", v), "      }"]
        elif d == "output":
            body.append("      max_capacitance : 1000;")
            if rel:
                body += ["      timing () {", f'        related_pin : "{rel}";', "        timing_type : rising_edge;",
                         "        timing_sense : non_unate;", sc("cell_rise", L0 + io), sc("cell_fall", L0 + io),
                         sc("rise_transition", OUT_SLEW_PS), sc("fall_transition", OUT_SLEW_PS), "      }"]
        body.append("    }")
        out += body
    out += ["  }", "}", ""]
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------------ make
def routed_detail(cdir, module, meta, source_root):
    """Explicit pre-exported detailed abstract only; no OpenROAD/export or guessed bloat policy here.

    The existing abstract_detail splice receipt pins both files. Recheck its unchanged
    header/pins/PG/lower OBS against the staged base before selecting the detailed LEF.
    """
    keys = ("detailed_lef", "detailed_receipt")
    if not any(meta.get(k) for k in keys):
        return os.path.join(cdir, module + ".lef"), None
    if not all(isinstance(meta.get(k), str) and meta[k] == os.path.basename(meta[k])
               and meta[k] not in (".", "..") for k in keys):
        raise ValueError("detailed abstract needs both staged artifact basenames")
    bloat = meta.get("detail_bloat_factor")
    if type(bloat) is not int or bloat not in (0, 1):
        raise ValueError("detailed abstract needs an explicit bloat factor 0 or 1")
    base = os.path.join(cdir, module + ".lef")
    detail = os.path.join(cdir, meta["detailed_lef"])
    receipt = json.load(open(os.path.join(cdir, meta["detailed_receipt"])))
    if not isinstance(receipt, dict):
        raise ValueError("detailed abstract receipt must be an object")
    if receipt.get("base_sha256") != sha256(base) or receipt.get("out_sha256") != sha256(detail):
        raise ValueError("detailed abstract receipt hashes differ from staged files")
    if receipt.get("pin_clear_um") is not None:
        raise ValueError("detailed abstract pin-clear cuts need a separate explicit model contract")
    if receipt.get("check_ok") is not True or receipt.get("detail_pins_equal_base") is not True:
        raise ValueError("detailed abstract lacks the matching-export pin check")
    if receipt.get("bloat_factor") != bloat or type(receipt.get("bloat_factor")) is not int:
        raise ValueError("detailed abstract bloat policy differs from its receipt")
    if not source_root:
        raise ValueError("detailed abstract needs the selected --src helper cohort")
    import importlib.util
    helper = os.path.join(source_root, "tools", "die_plan", "abstract_detail.py")
    spec = importlib.util.spec_from_file_location("_prov_abstract_detail", helper)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    before = open(base).read().splitlines(keepends=True)
    after = open(detail).read().splitlines(keepends=True)
    layers = tool.default_layers(before)
    pg_layer = meta.get("detail_pg_layer") is True
    if pg_layer:
        layers = pg_layer_detail_layers(tool, before, after, bloat)
    if not layers or receipt.get("layers_detailed") != layers:
        raise ValueError("detailed abstract layers differ from layers above PG pins")
    window = receipt.get("pin_window")        # DIE-QC-97 11-10: pin access windows, rechecked on the base
    if window is not None and not isinstance(window, dict):
        raise ValueError("detailed abstract pin_window must be an object")
    ok, problems = tool.check(before, after, layers, window) if window else tool.check(before, after, layers)
    if not ok:
        raise ValueError("detailed abstract changed protected geometry: " + "; ".join(problems))
    out = dict(base_sha256=receipt["base_sha256"], out_sha256=receipt["out_sha256"],
               bloat_factor=bloat, layers_detailed=layers, check_ok=True,
               detail_pins_equal_base=True, helper_sha256=sha256(helper))
    if pg_layer:
        out["pg_layer_detail"] = True
    if window:
        out["pin_window"] = {k: window.get(k) for k in ("margin_um", "top_layer", "clear_um")}
        out["pin_window"]["pins"] = sorted(window.get("windows") or {})
    return detail, out


def pg_layer_detail_layers(tool, before, after, bloat):
    """DIE-HBM-97 11-09 (COORD 01:4x, DRT-0073 class, ot_hbm_hc_bank128_pair_core): a narrow second form of the detailed
    abstract for a core whose PG pins sit on its TOP OBS layer, so there is no layer above PG for the normal form.  The
    centre clk pin under that layer's blanket OBS has no access point (single-macro probe: DRT-0073 on the base view,
    PA_OK with the same signed ODB's detail on that one layer).  Allowed only when ALL hold, else ValueError:
      - the wave entry opts in explicitly (detail_pg_layer: true); without it nothing here runs;
      - the normal form has nothing to detail (no OBS layer above the highest PG pin layer);
      - exactly that one layer is detailed, it is the highest PG pin layer, and the base has blanket OBS there;
      - bloat factor 1 (one-pitch merge, never the exact-shape 0 form for this case);
      - the detail still carries OBS on that layer (a refinement, not a removal).
    PG pins, all other pins, header and lower OBS stay identical (tool.check, run by the caller)."""
    if tool.default_layers(before):
        raise ValueError("detail_pg_layer only for a core with no OBS layer above its PG pins")
    pg = tool.pg_pin_layers(before)
    order = tool.LAYER_ORDER
    tops = {l for ls in pg.values() for l in ls if l in order}
    if not tops:
        raise ValueError("detail_pg_layer needs PG pins on a routing layer")
    top = max(tops, key=order.index)
    _, bb, _ = tool._split(before)
    _, nb, _ = tool._split(after)
    base_layers = [l for l, _ in tool._obs_by_layer(bb) if l in order]
    if not base_layers or max(base_layers, key=order.index) != top:
        raise ValueError("detail_pg_layer: the PG pin layer is not the base view's top OBS layer")
    if bloat != 1:
        raise ValueError("detail_pg_layer needs bloat factor 1")
    new_geo = [g for l, g in tool._obs_by_layer(nb) if l == top]
    if not any(ln.strip().startswith("RECT") for g in new_geo for ln in g):
        raise ValueError("detail_pg_layer: the detail has no OBS left on the PG pin layer")
    return [top]


def check_routed(cdir, module, entry, ppins, plan_lef, source_root=None, lef_override=None):
    """-> (ok, why) for a routed candidate dir"""
    lef, tt, ff = (os.path.join(cdir, f"{module}{s}") for s in (".lef", "_tt.lib", "_ff.lib"))
    lef = lef_override or lef
    for f in (tt, ff) + (() if plan_lef else (lef,)):
        if not os.path.isfile(f):
            return False, f"missing {os.path.basename(f)}"
    if plan_lef:
        _, _, lp, _ = lef_info(plan_lef)
        want = signal_bases(lp)
    else:
        mac, size, lp, _ = lef_info(lef)
        if mac != module:
            return False, f"LEF macro {mac} != {module}"
        ow = [float(x) for x in entry.get("outline_um") or []]
        if size and len(ow) == 2 and (abs(size[0] - ow[0]) > 0.002 or abs(size[1] - ow[1]) > 0.002):
            return False, f"LEF SIZE {size[0]}x{size[1]} != plan outline {ow[0]}x{ow[1]}"
        if entry.get("physical_ft"):
            try:
                if not source_root:
                    raise ValueError("physical FT needs the explicit selected --src tool cohort")
                helpers = os.path.join(source_root, "tools", "die_plan")
                if not os.path.isfile(os.path.join(helpers, "core_ft_physical.py")):
                    raise ValueError("selected source lacks the matched physical FT helper")
                sys.path.insert(0, helpers)
                import core_ft_physical as CF
                # DIE-QC-97 11-11 ISLAND-VIEW: a repo-relative physical_ft proof resolves against the selected --src
                # cohort (the gen_phys root), not the remote shell cwd
                contract = CF.load(entry, module, lef, tt, ff, root=source_root, ppins=ppins)
                ppins = list(ppins) + [{"name": p["name"]} for p in contract["ports"]]
            except (ValueError, OSError) as exc:
                return False, "physical FT contract: " + str(exc)
        names = {n for n, v in lp.items() if v[1] not in ("POWER", "GROUND")}
        if ppins is not None and names != {p["name"] for p in ppins}:
            a, b = names - {p["name"] for p in ppins}, {p["name"] for p in ppins} - names
            return False, f"LEF pins != plan pins (+{len(a)} -{len(b)}: {sorted(a)[:2]} {sorted(b)[:2]})"
        want = signal_bases(lp)
    for f in (tt, ff):
        got = lib_cell_ports(f, module)
        if got is None:
            return False, f"{os.path.basename(f)}: no cell ({module})"
        got = lib_signal_ports(got, lp)
        if got != want:
            return False, f"{os.path.basename(f)} ports != LEF ports (+{sorted(got - want)[:2]} -{sorted(want - got)[:2]})"
    return True, "ok"


def make(a):
    plan_path = os.path.abspath(a.plan)
    plan_dir = os.path.dirname(plan_path)
    plan = json.load(open(plan_path))
    tn = a.type
    t = plan["partition_types"][tn]
    period = float((plan.get("die") or {}).get("period_ps") or 833.0)
    roots = [r for r in list(a.rtl or []) + [a.src, plan_dir] if r]
    out = os.path.abspath(a.out)
    vroot = os.path.join(out, "views")
    os.makedirs(vroot, exist_ok=True)
    children, errors = {}, []
    for entry, kind in needed(plan, tn):
        m = str(entry.get("module") or entry.get("inst"))
        ppins = plan_pins(entry, plan_dir)
        plan_lef = resolve(entry.get("lef"), roots) if kind == "noview" else None
        if kind == "noview" and not plan_lef:
            errors.append(f"{m}: plan lef {entry.get('lef')} not found")
            continue
        vd = os.path.join(vroot, m)
        os.makedirs(vd, exist_ok=True)
        rec, tried = None, []
        rd = os.path.join(a.routed or "", m)
        for c in sorted(os.listdir(rd)) if a.routed and os.path.isdir(rd) else []:
            cdir = os.path.join(rd, c)
            meta = {}
            try:
                meta = json.load(open(os.path.join(cdir, "meta.json")))
            except (OSError, ValueError):
                pass
            detail = None
            selected_lef = os.path.join(cdir, m + ".lef")
            try:
                if not plan_lef:
                    selected_lef, detail = routed_detail(cdir, m, meta, a.src)
                ok, why = check_routed(cdir, m, entry, ppins, plan_lef, a.src, selected_lef)
            except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
                ok, why = False, "detailed abstract: " + str(exc)
            tried.append(f"{meta.get('job', c)}: {why}")
            if ok:
                for suffix in ("_tt.lib", "_ff.lib"):
                    shutil.copyfile(os.path.join(cdir, m + suffix), os.path.join(vd, m + suffix))
                if not plan_lef:
                    shutil.copyfile(selected_lef, os.path.join(vd, m + ".lef"))
                rec = dict(source="routed", job=meta.get("job"), host=meta.get("host"), signoff=meta.get("signoff"),
                           drc=meta.get("drc"), tt_wns=meta.get("tt_wns"), ff_wns=meta.get("ff_wns"))
                # KW-FIX-35-V 11-08 (COORD: signed child views missing in the wave): a candidate that IS the counted
                # signed view of the child (kit_wave stages counted=True + its export gates.json) is the final view,
                # not a provisional one: the type counts on its own sign-off, no STA re-sign owed.
                sv = signed_view_ok(cdir, m, meta, plan_lef)
                if sv:
                    rec.update(source="signed", counted=sv, final=True)
                    carry_landing_evidence(cdir, vd)
                if detail is not None:
                    rec["abstract_detail"] = detail
                break
        if rec is None and entry.get("physical_ft"):
            errors.append(f"{m}: explicit physical FT requires its exact routed view ({'; '.join(tried)})")
            continue
        if rec is None:
            # plan-contract abstract
            ow = [float(x) for x in entry.get("outline_um") or []]
            if len(ow) != 2 or (ppins is None and not plan_lef):
                errors.append(f"{m}: no routed abstract ({'; '.join(tried) or 'none'}) and no plan outline/pins for a contract")
                continue
            if ppins is not None and not ppins and not plan_lef:
                # a pins_file with no readable signal pin would give a PG-only blackbox: fail closed (PROV-PINS-BUS)
                errors.append(f"{m}: plan pins_file {entry.get('pins_file')} has no signal pin rows for a contract")
                continue
            dirs, dsrc = {}, []
            if plan_lef:
                _, _, lp, _ = lef_info(plan_lef)
                dirs.update({n: v[0] for n, v in lp.items() if v[0]})
                dsrc.append("plan lef")
                if ppins is None:
                    ppins = [dict(name=n, layer=v[2], x=v[3][0], y=v[3][1]) for n, v in lp.items()
                             if v[1] not in ("POWER", "GROUND") and v[3]]
            for p in ppins:
                if p.get("dir") in DIRS:
                    dirs.setdefault(p["name"], DIRS[p["dir"]])
            missing = [p["name"] for p in ppins if p["name"] not in dirs]
            if missing:
                rp, rf = rtl_dirs(m, roots)
                if not rp and "__" in m:
                    rp, rf = rtl_dirs(m.split("__")[0], roots)
                if rf:
                    dsrc.append(f"rtl {os.path.relpath(rf, a.src) if a.src and rf.startswith(a.src) else rf}")
                for n in missing:
                    b = split_bit(n)[0]
                    # a split port '<port>_<lsb>' (wrapper keeps live bit ranges of <port>) has <port>'s direction
                    sp_ = re.match(r"^(.*)_(\d+)$", b)
                    d = rp.get(b) or (rp.get(sp_.group(1)) if sp_ else None)
                    if d:
                        dirs[n] = DIRS[d]
                missing = [p["name"] for p in ppins if p["name"] not in dirs]
            if missing:
                # DIE-HBM-91-KCLS 11-08: a hard-core cut / recipe view whose plan module has no RTL of its own
                # (HBM root ot_hbm_hc_root_static__hcp_sys1, __tailx_sk_fsr): the core flow's exact port tables
                cp, csrc = core_table_dirs(m, roots)
                for n in missing:
                    d = cp.get(split_bit(n)[0])
                    if d:
                        dirs[n] = DIRS[d]
                if csrc and len(missing) != len([p for p in ppins if p["name"] not in dirs]):
                    dsrc += csrc
                missing = [p["name"] for p in ppins if p["name"] not in dirs]
            if missing:
                guessed = {n: name_dir(n) for n in missing if name_dir(n)}
                if guessed:
                    dirs.update(guessed)
                    dsrc.append(f"name suffix ({len(guessed)} pins)")
                    missing = [n for n in missing if n not in guessed]
            if missing:
                errors.append(f"{m}: no routed abstract ({'; '.join(tried) or 'none'}) and contract abstract has "
                              f"{len(missing)} pins without a direction (pins_file dir / plan lef / RTL): {missing[:3]}")
                continue
            # PROV-OBS-M5 (DIE-QC-81 11-05): default OBS top = M5, the 12.1a core ceiling and the default of g2.py /
            # placement_obstacles.py. The contract PG pins are M5 stripes; a blanket M6/M7 OBS over them gave PDN-0006
            # (core_pg_connect M5->M6 has no landing) on every parent that connects child PG (QC coll_core 11-05,
            # = the S81 pgobs class of 11-03). A plan obs_max still overrides; a child signed above it re-routes (resign exit 4).
            obs = contract_obs_top(entry)
            if not plan_lef:
                open(os.path.join(vd, m + ".lef"), "w").write(contract_lef(m, ow[0], ow[1], ppins, dirs, obs,
                                                                             merged_clock_pins(t, entry.get("inst", ""))))
            clocks = core_insertion(t, entry.get("inst", ""), {p["name"] for p in ppins})
            for p in ppins:
                if is_clock(p["name"]) and dirs.get(p["name"]) == "INPUT" and p["name"] not in clocks:
                    clocks[p["name"]] = (0.0, 0.0)
            for corner in ("tt", "ff"):
                open(os.path.join(vd, f"{m}_{corner}.lib"), "w").write(
                    contract_lib(m, corner, ow[0], ow[1], ppins, dirs, clocks, period))
            rec = dict(source="contract", directions=dsrc, clocks=sorted(clocks), routed_tried=tried[:4])
        lef = plan_lef or os.path.join(vd, m + ".lef")
        tt, ff = os.path.join(vd, m + "_tt.lib"), os.path.join(vd, m + "_ff.lib")
        final = bool(rec.get("final"))
        rec.update(kind=kind, inst=entry.get("inst"), lef=lef, lef_from_plan=bool(plan_lef), lef_sha256=sha256(lef),
                   tt=tt, tt_sha256=sha256(tt), ff=ff, ff_sha256=sha256(ff),
                   kit_libs=[os.path.basename(tt), os.path.basename(ff)], final=final)
        if final:   # = resign()'s FINAL record: the kit's macro libs must keep these exact bytes (autopilot classify)
            rec.update(final_lef=lef, final_tt=tt, final_ff=ff,
                       final_sha256={os.path.basename(tt): rec["tt_sha256"], os.path.basename(ff): rec["ff_sha256"]})
        children[m] = rec
    if errors:
        print("PROV_FAIL " + " | ".join(errors))
        print("PROV_JSON " + json.dumps(dict(ok=False, errors=errors, children={k: v["source"] for k, v in children.items()})))
        return 3
    stamp_views(plan, tn, children)
    # the overlay dir links every entry of the plan dir, so plan-relative paths still resolve -- except '../'
    # paths (they would resolve against the overlay's parent): make those absolute
    def absup(o):
        if isinstance(o, dict):
            return {k: absup(v) for k, v in o.items()}
        if isinstance(o, list):
            return [absup(v) for v in o]
        if isinstance(o, str) and o.startswith("../"):
            return os.path.normpath(os.path.join(plan_dir, o))
        return o
    plan = absup(plan)
    pd = os.path.join(out, "plan")
    if os.path.isdir(pd):
        shutil.rmtree(pd)
    os.makedirs(pd)
    base = os.path.basename(plan_path)
    for f in os.listdir(plan_dir):
        if f != base:
            os.symlink(os.path.join(plan_dir, f), os.path.join(pd, f))
    op = os.path.join(pd, base)
    with open(op, "w") as f:
        json.dump(plan, f, indent=1)
    status = "FINAL" if children and all(v.get("final") for v in children.values()) else "PROVISIONAL"
    marker = dict(schema=SCHEMA, status=status, rule=RULE, type=tn, die=(plan.get("die") or {}).get("name"),
                  plan=plan_path, plan_sha256=sha256(plan_path), overlay_plan=op, overlay_sha256=sha256(op),
                  generated=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), children=children)
    with open(os.path.join(out, "provisional_views.json"), "w") as f:
        json.dump(marker, f, indent=1)
    print("PROV_JSON " + json.dumps(dict(ok=True, overlay_plan=op, marker=os.path.join(out, "provisional_views.json"),
                                         status=status, children={k: v["source"] for k, v in children.items()})))
    return 0


# ------------------------------------------------------------------------------------------------------ resign
SIGNED_VERDICTS = ("SIGNED", "LOCAL_PASS_NEEDS_PARENT")


def needs_parent_view_only(g):
    """KW-FIX-35-CV 11-08 (HBM hcol_h0_ra/rb, sfu_opsa_rest, wbq_root_g0): export_view.py lists the LOCAL_PASS_NEEDS_PARENT
    verdict itself as a view problem, so a counted NEEDS_PARENT view (OWNER 11-03: counts SIGNED) always read
    view_complete false here and never went FINAL.  True when that verdict is the ONLY view problem."""
    pr = g.get("view_problems") or []
    return (str(g.get("signoff") or "").split() or [""])[0] == "LOCAL_PASS_NEEDS_PARENT" and bool(pr) and all(
        "LOCAL_PASS_NEEDS_PARENT" in str(x) and "is not SIGNED" in str(x) for x in pr)


def carry_landing_evidence(cdir, vd):
    """KW-FIX-40 11-08 (QC-TYPES-10 class N): a counted hard-landing child's gen reads landing_evidence/ (or provenance.json,
    needing the original host) beside its selected LEF; the view staged only LEF and libs, so hard_landing.capture failed."""
    src = os.path.join(cdir, "provenance.json")
    if os.path.isfile(src):
        shutil.copyfile(src, os.path.join(vd, "provenance.json"))
    ev = os.path.join(cdir, "landing_evidence")
    if os.path.isdir(ev):
        shutil.copytree(ev, os.path.join(vd, "landing_evidence"), dirs_exist_ok=True)


def signed_view_ok(cdir, module, meta, plan_lef=None):
    """'' unless candidate dir cdir is the COUNTED signed view of module: kit_wave staged it with counted=True (a
    prov_view_sources entry from counted_child_views.py / export_view.py of the counter's own sign-off record) and its
    export gates.json says the module signed (SIGNED / LOCAL_PASS_NEEDS_PARENT, OWNER 11-03) with a complete view.  A
    plan-named LEF (noview child) must be pin/OBS-compatible with the signed LEF.  -> the signed record path."""
    if not meta.get("counted"):
        return ""
    try:
        g = json.load(open(os.path.join(cdir, "gates.json")))
    except (OSError, ValueError):
        return ""
    if g.get("type") not in (None, module) or (str(g.get("signoff") or "").split() or [""])[0] not in SIGNED_VERDICTS:
        return ""
    if g.get("view_complete") is not True and not needs_parent_view_only(g):
        return ""
    if plan_lef:
        sl = os.path.join(cdir, module + ".lef")
        if not os.path.isfile(sl) or lef_compatible(plan_lef, sl, module):
            return ""
    return str(g.get("signoff_record") or meta.get("signoff") or meta.get("job") or "counted")


def lef_compatible(prov_lef, signed_lef, module):
    """[] when the signed LEF can replace the provisional one under the same routed parent (pins, obs)"""
    _, _, pp, po = lef_info(prov_lef)
    mac, _, sp_, so = lef_info(signed_lef)
    bad = []
    if mac != module:
        bad.append(f"signed LEF macro {mac} != {module}")
    a = {n for n, v in pp.items() if v[1] not in ("POWER", "GROUND")}
    b = {n for n, v in sp_.items() if v[1] not in ("POWER", "GROUND")}
    if a != b:
        bad.append(f"pin names differ (+{sorted(b - a)[:2]} -{sorted(a - b)[:2]})")
    moved = [n for n in a & b if pp[n][3] and sp_[n][3] and (abs(pp[n][3][0] - sp_[n][3][0]) > 0.05 or
                                                             abs(pp[n][3][1] - sp_[n][3][1]) > 0.05)]
    if moved:
        bad.append(f"{len(moved)} pins moved > 0.05 um ({sorted(moved)[:2]})")
    if po and so > po:
        bad.append(f"signed OBS up to M{so} > provisional M{po}")
    return bad


def resign(a):
    K = os.path.abspath(a.kit)
    mk = os.path.join(K, "provisional_views.json")
    marker = json.load(open(mk))
    if marker.get("schema") != SCHEMA:
        print(f"PROV_RESIGN FAIL {mk}: not a provisional marker")
        return 2
    want = {}
    for c in a.child:
        m, _, files = c.partition("=")
        lef, tt, ff = files.split(",")
        want[m] = (lef, tt, ff)
    kids = marker.get("children") or {}
    unknown = sorted(set(want) - set(kids))
    if unknown:
        print(f"PROV_RESIGN FAIL children {unknown} not provisional in {mk}")
        return 2
    bad = {}
    for m, (lef, tt, ff) in want.items():
        kl = os.path.join(K, "macros", os.path.basename(kids[m]["lef"]))
        b = lef_compatible(kl if os.path.isfile(kl) else kids[m]["lef"], lef, m)
        for f in (tt, ff):
            if lib_cell_ports(f, m) is None:
                b.append(f"{os.path.basename(f)}: no cell ({m})")
        if b:
            bad[m] = b
    if bad:
        marker["resign"] = dict(status="RE-ROUTE", problems=bad, at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
        if not a.dry_run:
            json.dump(marker, open(mk, "w"), indent=1)
        print("PROV_RESIGN REROUTE " + json.dumps(bad))
        return 4
    if a.dry_run:
        print("PROV_RESIGN DRY ok " + ",".join(sorted(want)))
        return 0
    for m, (lef, tt, ff) in want.items():
        names = kids[m].get("kit_libs") or [f"{m}_tt.lib", f"{m}_ff.lib"]
        for src, name in zip((tt, ff), names):
            dst = os.path.join(K, "macros", name)
            if os.path.isfile(dst) and not os.path.isfile(dst + ".prov"):
                shutil.copyfile(dst, dst + ".prov")
            shutil.copyfile(src, dst)
        kids[m].update(final=True, final_lef=lef, final_tt=tt, final_ff=ff,
                       final_sha256={names[0]: sha256(os.path.join(K, "macros", names[0])),
                                     names[1]: sha256(os.path.join(K, "macros", names[1]))})
    marker["status"] = "FINAL" if all(v.get("final") for v in kids.values()) else "PROVISIONAL"
    marker["resign"] = dict(status="LIBS-FINAL", children=sorted(want),
                            at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
    json.dump(marker, open(mk, "w"), indent=1)
    if marker["status"] != "FINAL":
        print("PROV_RESIGN PARTIAL: other children still provisional; sign-off waits")
        return 0
    so = os.path.join(K, "signoff_resign_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    cmd = [sys.executable, "-I", os.path.join(K, "signoff.py"), "run", "--run-dir", os.path.join(K, "run"), "--kit", K,
           "--out", so, "--corners", "tt,ff"] + (["--image", a.image] if a.image else [])
    print("PROV_RESIGN signoff " + " ".join(cmd), flush=True)
    with open(so + ".log", "w") as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    print(f"PROV_RESIGN rc {rc} {so}")
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--plan", required=True)
    m.add_argument("--type", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--src")
    m.add_argument("--routed")
    m.add_argument("--rtl", action="append", help="RTL dir searched first for child port directions (the parent's kit RTL)")
    r = sub.add_parser("resign")
    r.add_argument("--kit", required=True)
    r.add_argument("--child", action="append", required=True, help="MODULE=LEF,TT_LIB,FF_LIB of the SIGNED child view")
    r.add_argument("--image")
    r.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return make(a) if a.cmd == "make" else resign(a)


if __name__ == "__main__":
    sys.exit(main())
