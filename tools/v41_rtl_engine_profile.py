#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM layer die: resource inventory AS THE RTL INSTANTIATES IT (acceptance-ladder rung 1).

Elaborates rtl/chip/ot_chip_v41x_die.sv at FULL_SHAPE=1 (every other parameter at its default) with
Verilator 5.050 `--json-only` (parse, link, parameter resolution and generate unrolling; no synthesis, no
technology mapping, no ABC), then reads the elaborated netlist for:

  * every instantiated module: instance count, specialisation, resolved overridable parameters;
  * every collapsed instance path (generate indices folded to [*]) with its count and region;
  * every behavioural memory array (unpacked array): word bits x words, instances, dynamic-index read and
    write sites as elaborated (the port candidates), constant-index sites, initial-block sites;
  * per-engine MAC lanes per cycle as instantiated, derived from elaborated leaf-multiplier counts and
    parameters;
  * comparison with the analytical ledger (results/floorplan/v41_resource_inventory.json
    analytical_assembly_reference.rows) and with that file's hand-written rtl_instances list;
  * discrepancy D1 (collective engines / package controllers / fabric routers) as a decision PROPOSAL
    built from the committed schedule, sequence, levers and physical records.

The source list is resolved by module-definition closure from the top over rtl/ and the ASAP7 macro views
(never from a hand list), and every file read is pinned by sha256, as are the records D1 cites.

Writes results/floorplan/v41_rtl_engine_profile.json.  `--check` re-derives nothing: it verifies the
committed record's source pins against the working tree.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/floorplan/v41_rtl_engine_profile.json"
TOP = "ot_chip_v41x_die"
TOP_FILE = "rtl/chip/ot_chip_v41x_die.sv"
PARAMS = {"FULL_SHAPE": 1}
INCDIRS = ["rtl/hdc/v41"]
INVENTORY = "results/floorplan/v41_resource_inventory.json"
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools"))
VERILATOR = os.environ.get("OT_VERILATOR", str(TOOLS_ROOT / "verilator-5.050/bin/verilator"))
# warnings are recorded, not gating: the adopted core's sources are linted by their own gates
VFLAGS = ["--json-only", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-MODDUP", "-Wno-TIMESCALEMOD"]
REGIONS = ("ROM_MAC", "VM", "ATTENTION", "HBM_SERVICE", "INDEX", "COLLECTIVE")

# Records the D1 proposal reads (pinned).
D1_RECORDS = {
    "sequence": "results/rtl/v41_tp_layer0_collective_sequence.json",
    "preflight": "results/arch/v41_single_token_schedule_preflight.json",
    "gw4_gate": "results/rtl/v41x_coll_gw4_gate.json",
    "rowsplit_die": "results/rtl/v41_tp_rowsplit_die_collectives.json",
    "levers_campaign": "results/rtl/v41_collective_levers_campaign.json",
    "oneshot_d32": "results/physical_abi3/asap7/rom/ot_rom_oneshot_die_d32/physical.json",
    "pkg_ctrl": "results/physical_abi3/asap7/rom/ot_rom_pkg_ctrl/physical.json",
    "fabric_router": "results/physical_abi3/asap7/rom/ot_rom_fabric_router/physical.json",
    "pkg_link": "results/physical_abi3/asap7/rom_pkg_link/physical.json",
    "die_assembly_tool": "tools/v41_die_assembly.py",
    "utilization_tool": "tools/arch_utilization_v41.py",
}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------
# source closure
MODULE_RE = re.compile(r"^\s*(?:module|package)\s+(\w+)", re.M)
INST_RE = re.compile(r"\b([A-Za-z_]\w*)\s*(?:#\s*\(|\w+\s*\()")
PKG_RE = re.compile(r"\b(\w+)::")
INC_RE = re.compile(r'^\s*`include\s+"([^"]+)"', re.M)


def strip_comments(t: str) -> str:
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))


def module_index() -> dict[str, str]:
    """module/package name -> defining file (behavioural macro models preferred over *_bb.v stubs)."""
    cand = collections.defaultdict(set)
    files = [p for p in (ROOT / "rtl").rglob("*.sv") if "/test/" not in str(p)]
    files += [p for p in (ROOT / "rtl").rglob("*.v") if "/test/" not in str(p)]
    files += list((ROOT / "physical/asap7_memory_macros").rglob("*.v"))
    for p in files:
        for m in MODULE_RE.finditer(strip_comments(p.read_text(errors="ignore"))):
            cand[m.group(1)].add(str(p.relative_to(ROOT)))
    idx = {}
    for k, v in cand.items():
        pref = sorted(x for x in v if not x.endswith("_bb.v")) or sorted(v)
        idx[k] = pref[0]
    return idx


def resolve_sources() -> tuple[list[str], list[str]]:
    idx = module_index()
    seen, todo, files, pkgs, incs = set(), [TOP], [], [], []
    while todo:
        m = todo.pop()
        if m in seen or m not in idx:
            continue
        seen.add(m)
        f = idx[m]
        txt = strip_comments((ROOT / f).read_text(errors="ignore"))
        if f not in files and f not in pkgs:
            (pkgs if re.search(r"^\s*package\s+" + m + r"\b", txt, re.M) else files).append(f)
        for n in set(INST_RE.findall(txt)) | set(PKG_RE.findall(txt)):
            if n in idx and n not in seen:
                todo.append(n)
        for inc in INC_RE.findall(txt):
            for d in INCDIRS + [str(Path(f).parent)]:
                if (ROOT / d / inc).exists() and f"{d}/{inc}" not in incs:
                    incs.append(f"{d}/{inc}")
    return sorted(pkgs) + sorted(files), sorted(incs)


# ---------------------------------------------------------------------------------------------------------
# elaboration
def elaborate(srcs: list[str], work: Path) -> tuple[dict, dict]:
    out = work / "die.json"
    cmd = [VERILATOR, *VFLAGS, "--top-module", TOP, *[f"-G{k}={v}" for k, v in PARAMS.items()],
           *[f"-I{d}" for d in INCDIRS], "--Mdir", str(work), "--json-only-output", str(out), *srcs]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    msgs = [ln for ln in r.stderr.splitlines() if ln.startswith("%")]
    if r.returncode != 0 or not out.exists():
        raise SystemExit("elaboration failed:\n" + "\n".join(msgs[-40:]))
    ver = subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip()
    warn = collections.Counter(re.match(r"%(\w+(?:-\w+)?)", m).group(1) for m in msgs if re.match(r"%\w", m))
    shown = [("<scratch>" if a == str(work) else "<scratch>/die.json" if a == str(out) else a)
             for a in cmd[1:-len(srcs)]]
    info = {"tool": ver, "command": ["verilator", *shown, "<source_files[:-includes] in order>"],
            "json_bytes": out.stat().st_size, "returncode": r.returncode,
            "message_counts": dict(sorted(warn.items())),
            "scope": "Verilator --json-only: parse, link, parameter specialisation and generate unrolling of the "
                     "whole die; no synthesis, no optimisation, no technology mapping"}
    return json.loads(out.read_text()), info


# ---------------------------------------------------------------------------------------------------------
# netlist helpers
CONST_RE = re.compile(r"(\d+)'(s?)([hbdo])([0-9a-fA-F_]+)$")


def cval(c: dict):
    m = CONST_RE.match(c.get("name", ""))
    if not m:
        return c.get("name")
    w, base = int(m.group(1)), {"h": 16, "b": 2, "d": 10, "o": 8}[m.group(3)]
    v = int(m.group(4).replace("_", ""), base)
    if m.group(2) and (v >> (w - 1)) & 1:
        v -= 1 << w
    return v


def children(n: dict):
    for k, v in n.items():
        if isinstance(v, list):
            for x in v:
                if isinstance(x, dict):
                    yield k, x


class Netlist:
    def __init__(self, d: dict):
        self.mods = {m["addr"]: m for m in d["modulesp"]}
        self.top = next(m for m in d["modulesp"] if m["name"] == TOP)
        self.types = {}
        self._reg_types(d)
        self.inst = collections.Counter()          # specialised module name -> instances
        self.paths = collections.Counter()         # collapsed path -> instances
        self.path_mod = {}
        self.path_spec = {}
        self.full_paths = collections.defaultdict(list)   # origName -> example full paths (bounded)
        self.region_of_inst = collections.Counter()      # (region, origName) -> instances
        self.spec_regions = collections.defaultdict(collections.Counter)  # spec name -> region -> count
        self._walk(self.top, "die", 1)

    def _reg_types(self, n):
        stack = [n]
        while stack:
            x = stack.pop()
            if x.get("type", "").endswith("DTYPE"):
                self.types[x["addr"]] = x
            stack.extend(c for _, c in children(x))

    @staticmethod
    def cells(n: dict, prefix=""):
        for _, c in children(n):
            if c["type"] == "CELL":
                yield prefix + c["name"], c
            elif c["type"] == "GENBLOCK" and c.get("name"):
                yield from Netlist.cells(c, prefix + c["name"] + ".")
            elif c["type"] not in ("FUNC", "TASK"):
                yield from Netlist.cells(c, prefix)

    def _walk(self, m: dict, path: str, mult: int):
        self.inst[m["name"]] += 1
        region = region_of(path)
        self.spec_regions[m["name"]][region] += 1
        cp = re.sub(r"\[\d+\]", "[*]", path)
        self.paths[cp] += 1
        self.path_mod[cp] = m["origName"]
        self.path_spec[cp] = m["name"]
        if len(self.full_paths[m["origName"]]) < 3:
            self.full_paths[m["origName"]].append(path)
        for rp, c in self.cells(m):
            self._walk(self.mods[c["modp"]], path + "." + rp, mult)

    def shape(self, addr):
        t = self.types.get(addr)
        if t is None:
            return None
        if t["type"] == "BASICDTYPE":
            if "range" in t:
                a, b = map(int, t["range"].split(":"))
                return abs(a - b) + 1, []
            return {"integer": 32, "int": 32, "byte": 8, "shortint": 16, "longint": 64}.get(t.get("keyword"), 1), []
        if t["type"] == "UNPACKARRAYDTYPE":
            sub = self.shape(t["refDTypep"])
            if sub is None:
                return None
            a, b = map(int, t["declRange"].strip("[]").split(":"))
            return sub[0], [abs(a - b) + 1] + sub[1]
        return None


def gparams(m: dict) -> dict:
    out = {}
    for s in m["stmtsp"]:
        if s["type"] == "VAR" and s.get("isGParam"):
            v = s.get("valuep") or []
            out[s["name"]] = cval(v[0]) if v and v[0]["type"] == "CONST" else None
    return out


def all_params(m: dict) -> dict:
    out = {}
    for s in m["stmtsp"]:
        if s["type"] == "VAR" and s.get("isParam"):
            v = s.get("valuep") or []
            out[s["name"]] = cval(v[0]) if v and v[0]["type"] == "CONST" else None
    return out


# ---------------------------------------------------------------------------------------------------------
# regions (the connectivity owner's IDs; first match on the collapsed instance path)
REGION_RULES = [
    (r"^die\.(u_coll|u_cdma|u_ctrl|u_rtr)\b", "COLLECTIVE"),
    (r"^die\.g_hbm\b", "HBM_SERVICE"),
    (r"^die\.g_packed_kv\.(u_rope|u_rope_region|u_kv_mux)\b", "HBM_SERVICE"),
    (r"^die\.u_tile\.(g_qstream|g_rope_check)\b", "HBM_SERVICE"),
    (r"^die\.g_packed_kv\b", "ATTENTION"),
    (r"^die\.u_tile\.u_core\.(g_att_x|g_packed_window_write)\b", "ATTENTION"),
    (r"^die\.u_tile\.u_core\.g_idx_x\b", "INDEX"),
    (r"^die\.u_tile\.u_kb\b", "INDEX"),
    (r"^die\.u_tile\.u_core\.(g_me_x|u_me|u_qe|g_he_x)\b", "ROM_MAC"),
    (r"^die\.u_tile\.u_qrom_decode\b", "ROM_MAC"),
    (r"^die\.u_tile\.u_core\.(g_su_x|g_xu_x)\b", "VM"),
    (r"^die\.u_tile\b", "VM"),          # tile and core spine: sequencer, VM, buffers (memories re-mapped below)
    (r"^die$", "DIE_TOP_GLUE"),
]
# tile-level behavioural memories: region by role (ROM operands beside their consumers)
TILE_MEMORY_REGION = {"prog": "VM", "wrom": "ROM_MAC", "hrom": "ROM_MAC", "hbank": "ROM_MAC",
                      "mbank": "ROM_MAC", "erom": "VM", "crom": "VM", "qlist": "ROM_MAC", "qwin": "ROM_MAC",
                      "vm": "VM"}


def region_of(path: str) -> str:
    cp = re.sub(r"\[\d+\]", "[*]", path)
    for pat, reg in REGION_RULES:
        if re.search(pat, cp):
            return reg
    return "DIE_TOP_GLUE"


# ---------------------------------------------------------------------------------------------------------
# memories
def memories(nl: Netlist) -> list[dict]:
    out = []
    for m in nl.mods.values():
        if m["type"] != "MODULE" or nl.inst[m["name"]] == 0:
            continue
        vars_ = {}

        def find_vars(n, gpath):
            for _, c in children(n):
                if c["type"] == "VAR" and not c.get("isParam") and c.get("lifetime") != "VAUTOMATIC":
                    sh = nl.shape(c["dtypep"])
                    if sh and sh[1]:
                        vars_[c["addr"]] = (c, sh, gpath)
                elif c["type"] == "GENBLOCK":
                    find_vars(c, gpath + [re.sub(r"\[\d+\]", "[*]", c.get("name", ""))])
                elif c["type"] not in ("FUNC", "TASK", "CELL"):
                    find_vars(c, gpath)
        find_vars(m, [])
        if not vars_:
            continue
        sites = {a: collections.Counter() for a in vars_}

        def scan(n, ctx):
            t = n["type"]
            if t in ("INITIAL", "INITIALSTATIC", "FINAL"):
                ctx = ctx | {"init"}
            if t == "LOOP":
                ctx = ctx | {"loop"}
            if t == "ARRAYSEL":
                chain, base = [n], n["fromp"][0] if n.get("fromp") else None
                while base is not None and base["type"] == "ARRAYSEL":
                    chain.append(base)
                    base = base["fromp"][0] if base.get("fromp") else None
                if base is not None and base["type"] == "VARREF" and base.get("varp") in sites:
                    idxs = [b for a in chain for b in a.get("bitp", [])]
                    dyn = not all(b["type"] == "CONST" for b in idxs)
                    acc = "write" if base.get("access") in ("WR", "RW") else "read"
                    key = ("init_" if "init" in ctx else "") + ("dyn_" if dyn else "const_") + acc
                    sites[base["varp"]][key] += 1
                    if "loop" in ctx and dyn and "init" not in ctx:
                        sites[base["varp"]]["in_procedural_loop"] += 1
                    for b in idxs:          # index expressions only: the chain and its base are this one site
                        scan(b, ctx)
                    return
            elif t == "VARREF" and n.get("varp") in sites:
                sites[n["varp"]][("init_" if "init" in ctx else "") + "whole_array_ref"] += 1
            for _, c in children(n):
                if c["type"] not in ("CELL",):
                    scan(c, ctx)
        scan(m, frozenset())
        # instances of a var = module instances x unrolled copies with the same collapsed generate path
        grouped = collections.OrderedDict()
        for a, (v, sh, gp) in vars_.items():
            key = (".".join(gp), v["name"])
            g = grouped.setdefault(key, {"v": v, "sh": sh, "copies": 0, "sites": collections.Counter()})
            g["copies"] += 1
            g["sites"] += sites[a]
        regions = nl.spec_regions[m["name"]]
        for (gp, name), g in grouped.items():
            w, dims = g["sh"]
            words = math.prod(dims)
            s = g["sites"]
            inst = nl.inst[m["name"]] * g["copies"]
            region = dict(regions)
            if m["origName"] == "ot_chip_v41x_tile" and name in TILE_MEMORY_REGION:
                region = {TILE_MEMORY_REGION[name]: nl.inst[m["name"]]}
            written = s["dyn_write"] + s["const_write"] > 0
            out.append({
                "module": m["origName"], "specialisation": m["name"], "generate_scope": gp or None,
                "name": name, "word_bits": w, "dims": dims, "words": words, "bits": w * words,
                "instances": inst, "total_bits": w * words * inst,
                "kind": "rom_or_constant" if not written else "ram_or_register_array",
                "dynamic_read_sites": s["dyn_read"], "dynamic_write_sites": s["dyn_write"],
                "constant_index_read_sites": s["const_read"], "constant_index_write_sites": s["const_write"],
                "dynamic_sites_inside_procedural_loops": s["in_procedural_loop"],
                "initial_block_sites": sum(v for k, v in s.items() if k.startswith("init_")),
                "whole_array_refs": s["whole_array_ref"],
                "regions": {k: v * g["copies"] for k, v in region.items()},
                "class": "memory" if (w * words >= 16384 and s["dyn_read"] + s["dyn_write"] > 0)
                         else "register_array",
            })
    out.sort(key=lambda r: (-r["total_bits"], r["module"], r["name"]))
    return out


# ---------------------------------------------------------------------------------------------------------
# engines: MAC lanes per cycle from elaborated leaf counts
def count_under(nl: Netlist, orig: str, prefix: str) -> int:
    return sum(c for p, c in nl.paths.items() if nl.path_mod[p] == orig and p.startswith(prefix))


LANE_PARAMS = {"G", "L", "M", "MP", "BL", "IL", "W", "NT", "H", "TD", "NL", "S", "N", "LANES", "GW", "DEPTH", "KIND",
               "POOL", "LB", "WW", "XW", "SUN", "SUM", "HHW", "MG", "SW", "XSW", "XSQ", "NC", "PMAX", "OMAX"}


def engines(nl: Netlist) -> list[dict]:
    C = "die.u_tile.u_core."
    tile = next(m for m in nl.mods.values() if m["origName"] == "ot_chip_v41x_tile" and nl.inst[m["name"]])
    tp = all_params(tile)

    by_name = {m["name"]: m for m in nl.mods.values()}

    def spec_of(orig, prefix):
        """resolved parameters of the specialisation(s) of `orig` elaborated under `prefix`."""
        names = sorted({nl.path_spec[p] for p in nl.paths if nl.path_mod[p] == orig and p.startswith(prefix)})
        out = {}
        for n in names:
            ps = all_params(by_name[n])
            out[n] = gparams(by_name[n]) | {k: v for k, v in ps.items() if k in LANE_PARAMS}
        return out

    def e(eid, region, cls, orig_leaf, prefix, per_leaf, basis, top_mod=None, top_prefix=None, dispatched=True,
          analytical=None):
        leaves = count_under(nl, orig_leaf, prefix)
        return {"engine": eid, "region": region, "class": cls, "leaf_module": orig_leaf, "leaf_path_prefix": prefix,
                "leaf_instances": leaves, "macs_per_leaf_per_cycle": per_leaf,
                "mac_lanes_per_cycle_as_instantiated": leaves * per_leaf,
                "engine_parameters": spec_of(top_mod, top_prefix) if top_mod else {},
                "derivation": basis, "dispatched_at_default_configuration": dispatched,
                "analytical_row": analytical}

    rows = [
        e("qe_blockdot", "ROM_MAC", "block_dot_fp8_fp4", "ot_hdc_blockdot", C + "u_qe.",
          32, "BL x MP ot_hdc_blockdot lanes, one exact 32-term block dot per lane per cycle (32 MACs)",
          "ot_hdc_v41_qe", C + "u_qe", analytical="block-dot pool (FP8/FP4 weights + FP4 indexer)"),
        e("idx_blockdot_fp4", "INDEX", "block_dot_fp8_fp4", "ot_hdc_v41x_wgt_bdot", C + "g_idx_x.",
          32, "KIND 0 pooled weight tile: L = 8G lanes, each one 32-term block dot (32 MACs) per cycle, M positions",
          "ot_hdc_v41x_wgt_tile", C + "g_idx_x.", analytical="block-dot pool (FP8/FP4 weights + FP4 indexer)"),
        e("me_bf16", "ROM_MAC", "bf16", "ot_hdc_v41x_wgt_mlane", C + "g_me_x.",
          1, "KIND 1 weight tile: L = 8G BF16 MAC lanes x M positions (one weight per lane per cycle)",
          "ot_hdc_v41x_wgt_tile", C + "g_me_x.", analytical="BF16 pool (BF16 weights, wo_a, attention)"),
        e("attention_products", "ATTENTION", "bf16", "ot_hdc_v41x_attn_bmul", C + "g_att_x.",
          1, "NT = NL x S tiles x H heads x TD products per cycle (q.k: BF16 q x dequantised FP8/FP4 KV; p.v "
             "reuses the tiles)", "ot_hdc_v41x_attn", C + "g_att_x.",
          analytical="BF16 pool (BF16 weights, wo_a, attention)"),
        e("idx_head_weight", "INDEX", "bf16", "ot_hdc_v41x_bmul", C + "g_idx_x.",
          1, "indexer head-sum weight multipliers (keys x heads)", "ot_hdc_v41x_idx_hsum", C + "g_idx_x.",
          analytical="BF16 pool (BF16 weights, wo_a, attention)"),
        e("as_built_matvec_fallback", "ROM_MAC", "bf16", "ot_hdc_bmul", C + "u_me.",
          1, "as-built ot_hdc_v41_matvec G x W BF16 lanes; instantiated, but with X_ME, X_ATT and X_IDX all "
             "non-zero no op class is dispatched to it (ot_hdc_core_v41x me_eng)", "ot_hdc_v41_matvec", C + "u_me",
          dispatched=False, analytical=None),
        e("hcp_fp32", "ROM_MAC", "fp32", "ot_hdc_mul24_rows", C + "g_he_x.u_he.u_hcp.g_grp",
          1, "HC projection: group x lane FP32 multiply lanes (u_om/u_sm scalar multipliers excluded)",
          "ot_hdc_v41x_hcp", C + "g_he_x.", analytical="HC projection (FP32 lanes)"),
        e("vector_light_lanes", "VM", "fp32_vector", "ot_hdc_v41x_vec_lane", C + "g_su_x.",
          1, "X_SU vector lanes (SUN)", "ot_hdc_v41x_vec", C + "g_su_x.", analytical="vector unit, light lanes"),
        e("vector_sfu_lanes", "VM", "sfu", "ot_hdc_v41x_exp", C + "g_su_x.u_su.u_vec.g_lane",
          1, "vector lanes that carry the SFU (g_sfu: exp/div), SUM of SUN", "ot_hdc_v41x_vec", C + "g_su_x.",
          analytical="vector unit, SFU lanes"),
        e("streaming_select", "VM", "select", "ot_hdc_v41x_sel_slice", C + "g_xu_x.",
          tp["XSW"], "XSQ select slices x XSW lanes each", "ot_hdc_v41x_sel_slice", C + "g_xu_x.",
          analytical="streaming select (4 x 16 tselect)"),
    ]
    for r in rows:
        r["mtp_positions_per_weight_read"] = tp.get("ML") if r["engine"] == "me_bf16" else None
    return rows


# ---------------------------------------------------------------------------------------------------------
# analytical comparison
# ledger row -> (RTL module origNames counted as the SAME unit, relation)
UNIT_MAP = {
    "Sinkhorn units (one per verified position)": (["ot_hdc_sinkhorn"], "same_unit"),
    "sqrt(softplus)": (["ot_hdc_v41x_softplus"], "same_function_different_module (record ot_hdc_softplus)"),
    "top-6 select": (["ot_hdc_select"], "related_module (record ot_hdc_select_k6 is not instantiated)"),
    "activation quantiser": (["ot_hdc_actquant"], "same_unit"),
    "FP4 quantise/dequantise": (["ot_hdc_fp4qdq"], "same_unit"),
    "indexer head-sum": (["ot_hdc_v41x_idx_hsum"], "same_unit"),
    "indexer key control": (["ot_hdc_v41x_idx_kctl"], "same_unit"),
    "indexer output tail": (["ot_hdc_v41x_idx_tail"], "same_unit"),
    "KV / key streamer (one per stack)": (["ot_hdc_kv_stream"], "same_unit"),
    "one-shot collective engine (128 lanes)": (["ot_rom_oneshot_die_px"], "successor_module (record d32 is "
                                                                          "ot_rom_oneshot_die LANES16 DEPTH32)"),
    "package controller": (["ot_rom_pkg_ctrl_x"], "superset_module (record ot_rom_pkg_ctrl)"),
    "fabric router": (["ot_rom_fabric_router"], "same_unit"),
    "package link endpoint": (["ot_rom_pkg_link"], "same_unit"),
    "Engram gather slices (spilled table rows)": (["ot_hdc_v41x_egather_slice"], "same_unit"),
    "Engram gather assembler": (["ot_hdc_v41x_egather_asm"], "same_unit"),
    "HBM3E PHY + controller": (["ot_chip_v41x_hbm3e_phy"], "behavioural_timing_model_not_PHY"),
    "UCIe-A modules (package peer)": ([], "no_module: ucie_* ready/valid flit ports only"),
    "112G PAM4 SerDes lanes": ([], "no_module: bl_* ready/valid flit ports only"),
}
LANE_ROWS = {  # ledger row -> (engine ids summed, analytical lanes)
    "block-dot pool (FP8/FP4 weights + FP4 indexer)": ["qe_blockdot", "idx_blockdot_fp4"],
    "BF16 pool (BF16 weights, wo_a, attention)": ["me_bf16", "attention_products", "idx_head_weight"],
    "HC projection (FP32 lanes)": ["hcp_fp32"],
    "vector unit, light lanes": ["vector_light_lanes"],
    "vector unit, SFU lanes": ["vector_sfu_lanes"],
    "streaming select (4 x 16 tselect)": ["streaming_select"],
}
LEDGER_LANES_FROM_BASIS = re.compile(r"^([\d,]+)\s+(?:MACs/cycle|FP32 lanes|lanes)[^x]*x\s*m=(\d)")


def analytical_lanes(row: dict):
    if row.get("lanes"):
        return row["lanes"]
    m = LEDGER_LANES_FROM_BASIS.match(row["basis"])
    if m:
        return int(m.group(1).replace(",", "")) * int(m.group(2))
    m = re.match(r"^(\d+) lanes of", row["basis"])
    return int(m.group(1)) if m else None


def compare(nl: Netlist, eng: list[dict], mems: list[dict], inv: dict) -> tuple[list, list]:
    by_orig = collections.Counter()
    for m in nl.mods.values():
        by_orig[m["origName"]] += nl.inst[m["name"]]
    eng_by = {e["engine"]: e for e in eng}
    rows, gaps = [], []
    macro_insts = {k: v for k, v in by_orig.items() if re.match(r"ot_(rom|sram)_\d|ot_sram_1r|ot_sram_2r|ot_rom_\d", k)
                   and v}
    for r in inv["analytical_assembly_reference"]["rows"]:
        b = r["block"]
        out = {"block": b, "group": r["group"], "analytical_count": r["count"], "analytical_basis": r["basis"],
               "analytical_record": r["record"]}
        if b in LANE_ROWS:
            ids = LANE_ROWS[b]
            rtl = sum(eng_by[i]["mac_lanes_per_cycle_as_instantiated"] for i in ids)
            al = analytical_lanes(r)
            out.update({"comparison": "lanes_per_cycle", "analytical_lanes_per_cycle": al,
                        "rtl_lanes_per_cycle": rtl, "rtl_engines": ids,
                        "rtl_over_analytical": (rtl / al) if al else None})
            out["status"] = "match" if al == rtl else "rtl_narrower" if al and rtl < al else "differs"
        elif b in UNIT_MAP:
            mods, rel = UNIT_MAP[b]
            n = sum(by_orig.get(x, 0) for x in mods)
            out.update({"comparison": "unit_count", "rtl_modules": mods, "relation": rel, "rtl_instances": n})
            if n == 0:
                out["status"] = "gap_no_rtl_instance"
            elif rel.startswith("behavioural"):
                out["status"] = "behavioural_model_only"
            else:
                out["status"] = "match" if n == r["count"] else "count_differs"
        elif r["group"] == "sram" or b.startswith("pool operand"):
            out.update({"comparison": "no_rtl_macro", "rtl_instances": 0,
                        "rtl_macro_instances": macro_insts,
                        "note": "the die RTL instantiates no SRAM/ROM macro view; storage is behavioural arrays "
                                "(see memories) or, for operand muxes, unpartitioned logic"})
            out["status"] = "gap_no_rtl_instance"
        elif r["group"] == "rom":
            rom_bits = sum(m["total_bits"] for m in mems if m["module"] == "ot_chip_v41x_tile"
                           and m["kind"] == "rom_or_constant")
            out.update({"comparison": "capacity", "rtl_behavioural_rom_bytes": rom_bits // 8,
                        "rtl_macro_instances": macro_insts,
                        "note": "behavioural tile ROM arrays at default depths; no ROM macro instances"})
            out["status"] = "gap_no_rtl_instance"
        else:
            out.update({"comparison": "not_rtl", "status": "not_an_rtl_block"})
        rows.append(out)
        if out["status"] in ("gap_no_rtl_instance",):
            reason = out.get("note") or (f"no instance of {out['rtl_modules']}" if out.get("rtl_modules")
                                         else out.get("relation", "no instance"))
            if b.startswith("KV / key streamer"):
                reason += ("; the index keys stream through ot_hdc_v41x_idx_kstream x4 (a different module, "
                           "not substituted)")
            gaps.append({"block": b, "analytical_count": r["count"], "reason": reason})
    return rows, gaps


def cross_check_inventory(nl: Netlist, inv: dict) -> list[dict]:
    out = []
    mapping = {"u_tile.u_core": ("die.u_tile.u_core", "ot_hdc_core_v41x"),
               "g_hbm.u_hbm": ("die.g_hbm[*].u_hbm", "ot_chip_v41x_hbm3e_phy"),
               "g_hbm.u_arb": ("die.g_hbm[*].g_karb.u_arb", "ot_chip_v41x_hbm_karb"),  # KARB_LOCAL=0 arm (claude/w2-karb-local)
               "u_coll": ("die.u_coll", "ot_rom_oneshot_die_px"),
               "u_cdma": ("die.u_cdma", "ot_chip_v41x_coll_dma"),
               "u_ctrl": ("die.u_ctrl", "ot_rom_pkg_ctrl_x"),
               "u_rtr": ("die.u_rtr", "ot_rom_fabric_router"),
               "u_kv": ("die.g_packed_kv.u_kv_mux.u_kv", "ot_chip_v41x_kv_reqmux"),
               "window source and packed staging": ("die.g_packed_kv.g_window_external_attention.u_window",
                                                    "ot_chip_v41x_window_kv_prefetch"),
               "u_tile.u_kb": ("die.u_tile.u_kb", "ot_hdc_v41x_idx_pool_hbm_bridge")}
    for r in inv["rtl_instances"]:
        p, mod = mapping[r["path"]]
        n = nl.paths.get(p, 0)
        got = nl.path_mod.get(p)
        reg = region_of(p.replace("[*]", "[0]"))
        notes = []
        if n != r["count"]:
            notes.append(f"count {r['count']} in inventory, {n} elaborated")
        if got != mod:
            notes.append(f"module {got} elaborated")
        if reg != r["region"]:
            notes.append(f"region {r['region']} in inventory; this profile places the path in {reg}")
        if r["path"] == "u_kv":
            notes.append("inventory path u_kv (ot_chip_v41x_kv_prefetch) exists only in the reduced branch "
                         "g_reduced_kv; at FULL_SHAPE=1 the KV service is g_packed_kv (kv_rope_reqmux -> kv_reqmux "
                         "+ window_kv_prefetch + rope_hbm_cache); ot_chip_v41x_kv_prefetch is not instantiated")
        if r["path"] == "window source and packed staging":
            notes.append("WINDOW_HBM_ATTENTION=0 elaborates g_window_external_attention (window_kv_prefetch), "
                         "not the internal window source")
        if r["path"] == "u_tile.u_core":
            notes.append("inventory files the whole core under ROM_MAC; elaborated core splits across ROM_MAC "
                         "(QE, ME, HCP), ATTENTION, INDEX and VM (SU, XU, sequencer)")
        out.append({"inventory_path": r["path"], "inventory_region": r["region"], "inventory_count": r["count"],
                    "elaborated_path": p, "elaborated_module": got, "elaborated_count": n,
                    "profile_region": reg, "agrees": not notes, "disagreements": notes})
    return out


def cross_check_memories(mems: list[dict], inv: dict) -> list[dict]:
    tile = {m["name"]: m for m in mems if m["module"] == "ot_chip_v41x_tile"}
    out = []
    for r in inv["rtl_behavioral_memories"]:
        m = tile.get(r["id"])
        got = None if m is None else {"word_bits": m["word_bits"], "words": m["words"], "bytes": m["bits"] // 8,
                                      "dynamic_read_sites": m["dynamic_read_sites"],
                                      "dynamic_write_sites": m["dynamic_write_sites"]}
        notes = []
        if m is None:
            notes.append("not elaborated in ot_chip_v41x_tile")
        else:
            if m["word_bits"] != r["word_bits"]:
                notes.append(f"word_bits {r['word_bits']} in inventory, {m['word_bits']} elaborated")
            if m["words"] != r["logical_words"]:
                notes.append(f"words {r['logical_words']} in inventory, {m['words']} elaborated")
            kind = "rom" if m["kind"] == "rom_or_constant" else "sram"
            if kind != r["kind"]:
                notes.append(f"kind {r['kind']} in inventory, {m['kind']} elaborated")
        out.append({"id": r["id"], "inventory": {"word_bits": r["word_bits"], "words": r["logical_words"],
                                                 "ports": r["ports"]},
                    "elaborated": got, "agrees": not notes, "disagreements": notes})
    return out


# ---------------------------------------------------------------------------------------------------------
# D1 decision proposal
def d1_proposal(nl: Netlist) -> dict:
    ld = lambda k: json.loads((ROOT / D1_RECORDS[k]).read_text())  # noqa: E731
    seq, pre = ld("sequence"), ld("preflight")
    phys = {k: ld(k)["design"] for k in ("oneshot_d32", "pkg_ctrl", "fabric_router", "pkg_link")}
    area = {k: v["area_um2"] for k, v in phys.items()}
    cases = seq["cases"]
    blocked = sum(c["cycles_blocked_to_all_done"] for c in cases)
    network = sum(c["network_to_first_vm_cycles"] for c in cases)
    stream = sum(c["input_stream_cycles"] for c in cases)
    other = blocked - network - stream
    act = [c for c in cases if re.match(r"L0\.(experts|shared)\.act\d_gather", c["descriptor"]["tag"])]
    act_blocked = sum(c["cycles_blocked_to_all_done"] for c in act)
    act_words = sum(c["descriptor"]["source_words"] for c in act)
    act_net = max(c["network_to_first_vm_cycles"] for c in act)
    act_commit = max(c["commit_cycles_after_last_vm"] for c in act)
    merged = act_net + act_words + act_commit
    stream128 = sum(math.ceil(c["input_stream_cycles"] / 8) for c in cases)
    elab = {"collective_engines": nl.paths.get("die.u_coll", 0), "collective_dma": nl.paths.get("die.u_cdma", 0),
            "package_controllers": nl.paths.get("die.u_ctrl", 0), "fabric_routers": nl.paths.get("die.u_rtr", 0)}
    coll_p = next(all_params(m) for m in nl.mods.values() if m["origName"] == "ot_rom_oneshot_die_px"
                  and nl.inst[m["name"]])
    rtr_p = next(all_params(m) for m in nl.mods.values() if m["origName"] == "ot_rom_fabric_router"
                 and nl.inst[m["name"]])
    unit = area["oneshot_d32"] + area["pkg_ctrl"] + area["fabric_router"]
    return {
        "status": "proposal_awaiting_root_decision",
        "issue": "analytical ledger 8 one-shot collective engines / 2 package controllers / 4 fabric routers / "
                 "4 package link endpoints per die vs RTL " + json.dumps(elab),
        "origin_of_analytical_counts": {
            "ledger_rows": "tools/v41_die_assembly.py side list: ('one-shot collective engine (128 lanes)', "
                           "'rom/ot_rom_oneshot_die_d32', 8), ('package controller', 'rom/ot_rom_pkg_ctrl', 2), "
                           "('fabric router', 'rom/ot_rom_fabric_router', 4), ('package link endpoint', "
                           "'rom_pkg_link', 4); no basis text for any of the four",
            "the_8_is_an_area_multiplier": "tools/arch_utilization_v41.py lever oneshot_128_lanes: "
                                           "area_um2 = 8 * area(rom/ot_rom_oneshot_die_d32), 'the one-shot engine at "
                                           "LANES >= 128 (512 B/cycle)'; 8 = 128 lanes / 16 lanes of the routed unit, "
                                           "i.e. ONE engine eight times wider, not eight engines",
            "one_per_pattern_and_level": "appears only as a comment (rtl/chip/ot_chip_v41x_die.sv header, "
                                         "tools/rtl_chip_v41x_die_smoke.py); no tool derives 8 that way (the levers "
                                         "record has 5 patterns, the floorplan draws 2 levels)",
            "controllers_routers_endpoints": "2 / 4 / 4 carry no derivation in any tool, doc or commit message",
        },
        "schedule_need": {
            "tp_group": "N_TP = 4 ranks = 2 packages x PKG_DIES = 2 (elaboration-checked in the die)",
            "collective_peers_per_die": {"ucie_in_package": 1, "t1_board_partner_package_dies": 2},
            "router_ports_as_elaborated": {"NP": rtr_p.get("NP"), "ports": "0 package controller, 1 UCIe fabric, "
                                                                           "2 board-link (stage hop)"},
            "collectives_per_layer_layer0_rtl": pre["summary"]["collectives"],
            "concurrently_outstanding_collectives": 1,
            "concurrency_evidence": "COLL is blocking (ot_chip_v41x_coll_dma: go while busy is a fault; die "
                                    "$fatal on package-controller VM access during COLL); "
                                    f"{D1_RECORDS['sequence']} per-die windows are back to back; the analytical "
                                    "critical-path DAG has no case needing two engines concurrently",
            "layer0_measured_blocked_cycles": blocked,
            "layer0_decomposition_cycles": {"network_to_first_vm": network, "input_stream": stream,
                                            "startup_and_commit": other},
            "per_collective": [{"tag": c["descriptor"]["tag"], "source_words": c["descriptor"]["source_words"],
                                "blocked_cycles": c["cycles_blocked_to_all_done"],
                                "network_to_first_vm": c["network_to_first_vm_cycles"]} for c in cases],
            "engine_as_elaborated": {k: coll_p.get(k) for k in ("N", "LANES", "DEPTH", "GW", "RELAY", "ADD_LAT",
                                                                "PKG_DIES", "FW")},
            "reading": "latency is dominated by per-collective network latency "
                       f"({network} of {blocked} cycles), which neither more engines nor wider engines remove; "
                       "the payload stream is the only width-dependent part",
        },
        "unit_areas_asap7_um2": {
            "oneshot_die_d32": {"area_um2": area["oneshot_d32"], "closed": phys["oneshot_d32"].get("closed"),
                                "record": D1_RECORDS["oneshot_d32"],
                                "note": "LANES 16 DEPTH 32 predecessor; no physical record for ot_rom_oneshot_die_px "
                                        "(LANES 16 DEPTH 256 GW 4) or ot_chip_v41x_coll_dma"},
            "pkg_ctrl": {"area_um2": area["pkg_ctrl"], "closed": phys["pkg_ctrl"].get("closed"),
                         "record": D1_RECORDS["pkg_ctrl"]},
            "fabric_router": {"area_um2": area["fabric_router"], "closed": phys["fabric_router"].get("closed"),
                              "record": D1_RECORDS["fabric_router"]},
            "pkg_link": {"area_um2": area["pkg_link"], "closed": phys["pkg_link"].get("closed"),
                         "record": D1_RECORDS["pkg_link"]},
        },
        "options": [
            {"id": "A", "counts": {"collective_engines": 1, "package_controllers": 1, "fabric_routers": 1},
             "engine": "as elaborated: LANES 16, DEPTH 256, GW 4, relay_add3",
             "layer0_collective_cycles": blocked, "latency_basis": "measured (" + D1_RECORDS["sequence"] + ")",
             "area_um2": round(unit, 2), "area_basis": "d32 + pkg_ctrl + router routed unit proxies",
             "verdict": "matches the blocking schedule; leaves the stream term and the serial act gathers exposed"},
            {"id": "B", "counts": {"collective_engines": 8, "package_controllers": 2, "fabric_routers": 4},
             "engine": "literal ledger: eight LANES-16 engines",
             "layer0_collective_cycles": blocked,
             "latency_basis": "no gain without a non-blocking COLL ISA/DMA and more VM ports: the program issues "
                              "one COLL at a time, so seven engines idle",
             "area_um2": round(8 * area["oneshot_d32"] + 2 * area["pkg_ctrl"] + 4 * area["fabric_router"], 2),
             "verdict": "reject: area without a schedule that uses it"},
            {"id": "C", "counts": {"collective_engines": 1, "package_controllers": 1, "fabric_routers": 1},
             "engine": "one engine at LANES 128 (512-B words): the ledger's actual area intent",
             "layer0_collective_cycles": {"estimate_low": blocked - stream + stream128, "estimate_high": blocked},
             "latency_basis": "ESTIMATE from the measured decomposition: input stream / 8; the low bound also needs "
                              "8x VM write bandwidth (GW4 already writes 4 words/cycle; preflight VM-write floor "
                              f"{pre['summary']['four_vm_write_port_aggregate_output_floor_cycles']} cycles for "
                              "the layer), otherwise VM writes bind and nothing is saved",
             "area_um2": round(8 * area["oneshot_d32"] + area["pkg_ctrl"] + area["fabric_router"], 2),
             "verdict": "defer to D2/D4 (engine width and VM banking), not a count question"},
            {"id": "D", "counts": {"collective_engines": 1, "package_controllers": 1, "fabric_routers": 1},
             "engine": "as A, with the independent expert-activation gathers issued as one descriptor (or "
                       "pipelined in the one engine)",
             "layer0_collective_cycles": blocked - act_blocked + merged,
             "latency_basis": f"ESTIMATE: the {len(act)} act gathers ({act_words} words, {act_blocked} blocked "
                              f"cycles measured) become one {act_words}-word gather at the measured "
                              f"{act_net}-cycle network latency + {act_words} stream + {act_commit} commit; "
                              "needs contiguous VM placement or a multi-descriptor engine; a merged gather waits for its last "
                              "producer, so the saving holds only while expert compute does not already overlap "
                              "those gathers; must be measured",
             "area_um2": round(unit, 2),
             "verdict": "largest latency lever found at zero engine count change"},
        ],
        "recommendation": {
            "collective_engines": 1, "package_controllers": 1, "fabric_routers": 1,
            "package_link_endpoints": {"count": 4, "status": "gap_no_rtl_instance",
                                       "derivation": "1 UCIe (fabric + collective + relay) + 2 T1 board "
                                                     "(partner-package dies) + 1 board stage-hop port; "
                                                     "ot_rom_pkg_link is outside the die RTL today"},
            "rationale": "the executed schedule has exactly one collective outstanding per die (blocking COLL), "
                         "one core start/done and one VM port for the package controller, and three router "
                         "endpoints; the ledger's 8 is an area stand-in for one 128-lane engine and its 2/4 have "
                         "no derivation. Keep 1/1/1, correct the ledger rows to count 1 (engine area left to the "
                         "D2 width decision), and pursue option D (merge/pipeline the independent expert "
                         "gathers) as the measured-next latency lever",
            "ledger_area_effect_um2": {
                "ledger_8_2_4": round(8 * area["oneshot_d32"] + 2 * area["pkg_ctrl"] + 4 * area["fabric_router"], 2),
                "recommended_1_1_1_at_16_lanes": round(unit, 2),
                "recommended_1_1_1_if_128_lanes": round(8 * area["oneshot_d32"] + area["pkg_ctrl"]
                                                        + area["fabric_router"], 2)},
            "decision_owner": "root (claude-main)",
        },
        "records_sha256": {v: sha(ROOT / v) for v in D1_RECORDS.values()},
    }


# ---------------------------------------------------------------------------------------------------------
def build(keep_json: Path | None = None) -> dict:
    srcs, incs = resolve_sources()
    work = Path(tempfile.mkdtemp(prefix="v41prof_"))
    try:
        d, info = elaborate(srcs, work)
        if keep_json:
            shutil.copy(work / "die.json", keep_json)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    nl = Netlist(d)
    del d
    by_orig = collections.Counter()
    specs = collections.defaultdict(list)
    for m in nl.mods.values():
        if m["type"] == "MODULE" and nl.inst[m["name"]]:
            by_orig[m["origName"]] += nl.inst[m["name"]]
            specs[m["origName"]].append({"specialisation": m["name"], "instances": nl.inst[m["name"]],
                                         "regions": dict(nl.spec_regions[m["name"]]),
                                         "parameters": gparams(m)})
    idx = module_index()
    modules = [{"module": k, "instances": by_orig[k], "source": idx.get(k), "specialisations": specs[k]}
               for k in sorted(by_orig, key=lambda x: (-by_orig[x], x))]
    mems = memories(nl)
    eng = engines(nl)
    inv = json.loads((ROOT / INVENTORY).read_text())
    ledger, gaps = compare(nl, eng, mems, inv)
    # memories by region
    mem_reg = collections.defaultdict(lambda: collections.Counter())
    for m in mems:
        for r, c in m["regions"].items():
            mem_reg[r]["bits"] += m["bits"] * c
            mem_reg[r]["arrays"] += c
    inst_reg = collections.defaultdict(collections.Counter)
    for p, c in nl.paths.items():
        inst_reg[region_of(p.replace("[*]", "[0]"))][nl.path_mod[p]] += c
    regions = {}
    for r in list(REGIONS) + ["DIE_TOP_GLUE"]:
        regions[r] = {"instances": sum(inst_reg[r].values()),
                      "top_modules": dict(inst_reg[r].most_common(12)),
                      "engines": [e["engine"] for e in eng if e["region"] == r],
                      "memory_arrays": mem_reg[r]["arrays"], "memory_bits": mem_reg[r]["bits"],
                      "memory_bytes": mem_reg[r]["bits"] // 8}
    tile = next(m for m in nl.mods.values() if m["origName"] == "ot_chip_v41x_tile" and nl.inst[m["name"]])
    top_p = gparams(nl.top)
    src_all = srcs + incs
    rec = {
        "schema": "opentallas.v41.rtl_engine_profile.v1",
        "status": "resource_inventory_as_instantiated_not_area_timing_or_throughput_proof",
        "acceptance_rung": 1,
        "top": TOP, "top_file": TOP_FILE, "parameter_overrides": PARAMS,
        "top_parameters_resolved": top_p,
        "tile_parameters_resolved": {k: v for k, v in all_params(tile).items()
                                     if k in {"SW", "HS", "MG", "MBAW", "HHW", "HBAW", "SUN", "SUM", "XSQ", "XSW",
                                              "X_HE", "X_ME", "X_ATT", "X_IDX", "X_SEL", "X_EG", "X_SU", "W_HBM",
                                              "KV_HBM", "IDX_SHARDED", "W", "G", "BL", "QLB", "ML", "AW", "NW",
                                              "INSTR_BITS", "VM_AW", "PROG_AW", "WROM_AW", "HROM_AW", "EROM_AW",
                                              "CROM_AW", "LWIN", "LAW", "NPC_W"}},
        "elaboration": info,
        "source_files": src_all,
        "source_sha256": {p: sha(ROOT / p) for p in src_all} | {
            "tools/v41_rtl_engine_profile.py": sha(Path(__file__)), INVENTORY: sha(ROOT / INVENTORY)},
        "source_resolution": "module/package definition closure from the top over rtl/ (excluding rtl/test) and "
                             "physical/asap7_memory_macros (behavioural .v preferred over *_bb.v); includes via "
                             + ",".join(INCDIRS),
        "summary": {
            "instances_total": sum(by_orig.values()),
            "distinct_modules": len(by_orig), "specialisations": sum(len(v) for v in specs.values()),
            "collapsed_instance_paths": len(nl.paths),
            "memory_arrays": len(mems), "memory_arrays_class_memory": sum(1 for m in mems if m["class"] == "memory"),
            "behavioural_memory_bytes_total": sum(m["total_bits"] for m in mems) // 8,
            "sram_or_rom_macro_instances": sum(v for k, v in by_orig.items() if re.match(r"ot_(sram|rom)_\d|ot_sram_[12]r", k)),
            "mac_lanes_per_cycle": {e["engine"]: e["mac_lanes_per_cycle_as_instantiated"] for e in eng},
            "block_dot_macs_per_cycle_dispatched": sum(e["mac_lanes_per_cycle_as_instantiated"] for e in eng
                                                       if e["class"] == "block_dot_fp8_fp4"),
            "bf16_macs_per_cycle_dispatched": sum(e["mac_lanes_per_cycle_as_instantiated"] for e in eng
                                                  if e["class"] == "bf16" and e["dispatched_at_default_configuration"]),
            "collective_engines": nl.paths.get("die.u_coll", 0), "package_controllers": nl.paths.get("die.u_ctrl", 0),
            "fabric_routers": nl.paths.get("die.u_rtr", 0), "hbm_stack_endpoints": nl.paths.get("die.g_hbm[*].u_hbm", 0),
            "me_class_issue": "one ME-class op at a time: ot_hdc_core_v41x serialises the QE/ME/attention/indexer "
                              "slot (an op issues only when every other engine of the slot is idle)",
        },
        "regions": regions,
        "engines": eng,
        "modules": modules,
        "instance_paths": [{"path": p, "module": nl.path_mod[p], "instances": c,
                            "region": region_of(p.replace("[*]", "[0]"))} for p, c in sorted(nl.paths.items())],
        "memories": mems,
        "memory_port_semantics": "dynamic_*_sites are elaborated ARRAYSEL sites with a non-constant index outside "
                                 "initial blocks: an upper bound on ports (mutually exclusive branches are not "
                                 "merged; a site inside a procedural loop counts once and is also counted in "
                                 "dynamic_sites_inside_procedural_loops, where the true port count may be "
                                 "the loop trip count)",
        "analytical_comparison": ledger,
        "gaps_analytical_without_rtl_instance": gaps,
        "inventory_rtl_instances_cross_check": cross_check_inventory(nl, inv),
        "inventory_memories_cross_check": cross_check_memories(mems, inv),
        "d1_decision_proposal": d1_proposal(nl),
        "claim_boundary": "counts and widths the die RTL elaborates at FULL_SHAPE=1 with default parameters; no "
                          "area, frequency, throughput or token-rate claim; D1 latency figures marked ESTIMATE are "
                          "derived from measured decompositions and are not measurements",
    }
    return rec


def check(path: Path = OUT) -> list[str]:
    rec = json.loads(path.read_text())
    bad = [p for p, h in rec["source_sha256"].items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    bad += [p for p, h in rec["d1_decision_proposal"]["records_sha256"].items()
            if not (ROOT / p).exists() or sha(ROOT / p) != h]
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify the committed record's pins only")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--keep-json", type=Path, default=None, help="also keep the elaborated netlist JSON here")
    a = ap.parse_args()
    if a.check:
        bad = check(a.out)
        print("stale pins:" if bad else "pins current", *bad, sep="\n  ")
        sys.exit(1 if bad else 0)
    rec = build(a.keep_json)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    s = rec["summary"]
    print(f"wrote {a.out.relative_to(ROOT) if a.out.is_relative_to(ROOT) else a.out}: {s['instances_total']} "
          f"instances, {s['distinct_modules']} modules, {s['memory_arrays']} arrays")
    print(json.dumps(s["mac_lanes_per_cycle"]))


if __name__ == "__main__":
    main()
