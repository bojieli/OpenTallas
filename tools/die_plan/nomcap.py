#!/usr/bin/env python3
"""nomcap.py (NOMCAP-1118, OWNER ruling r708): nominal input-pin load on clock cells.

r708: sign-off and every timing check use the NOMINAL input-pin capacitance (no rise_capacitance_range /
fall_capacitance_range) on (a) the input pins of the clock buffer / inverter cells and (b) the CLK pin of every
sequential cell (DFF, latch, ICG, scan flop).  Data pins of every other cell keep the range.  The 25 ps hold
uncertainty and the die-level x1.05 clock rule are unchanged.

The ASAP7 RVT INVBUF and SEQ libraries are copied with those range lines removed (nothing else changes) into
tools/die_plan/nomcap_libs/ (gzip, mtime 0: deterministic), with MANIFEST.json listing every stripped pin and the
source / output sha256.  The copies keep the ORFS base names (SEQ gains .gz), so every name-based check
(signoff ot_lib_validate, NATIVE_PDK_LIB, die_sta groups) still classifies them.

Accepted side effect: the clock cells below are ordinary INVBUF masters and are also placed on data nets (hold
buffers BUFx2/HB*, resizer buffers, INVx*).  A liberty file cannot scope a pin attribute to a net, and a renamed
clock-only master would need a new LEF/GDS view and CTS/resizer lists, so data-net instances of these masters read
the nominal load too.  Only the input load changes; drive tables are untouched.

One switch: OT_NOMCAP (default ON; OT_NOMCAP=0 restores the stock libraries everywhere).
  * gen_phys (type kits + die assembly): new kits carry KIT/nomcap/ and config.mk TC/BC/WC_NLDM_LIB_FILES point at
    /work/nomcap (synth, placement, CTS, hold repair, GRT policy, kit STA all read the ORFS LIB_FILES).
  * hold_eco_internal_run / margin_report / parent_core_hold: same /nomcap mount as signoff.py.
  * signoff.py / margin_report / parent_core_hold / timing_libs.tcl (ot_lib_resolve): native INVBUF/SEQ paths are
    replaced by the /nomcap mount (re-sign of DBs built before the switch).
  * die_sta.py corner_libs: native INVBUF/SEQ replaced by the repo copies.

Commands:
  nomcap.py build --src DIR [--out DIR]     regenerate the copies + MANIFEST.json from the ORFS NLDM directory
  nomcap.py check                           verify the repo copies against MANIFEST.json
  nomcap.py stage DEST                      copy the libs into DEST (a kit's nomcap/)
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE / "nomcap_libs"
CONTAINER_DIR = "/nomcap"
CORNERS = ("TT", "FF", "SS")
SOURCES = {"INVBUF": "asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz",
           "SEQ": "asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib"}

# Clock buffer / inverter masters (RVT suffix _R): the BUF family TritonCTS / repair_clock_nets choose from (no CTS_BUF_LIST
# is set, so every BUFx* is a CTS candidate), the CKINVDC clock inverters of the plan-owned clock tools (die_clock, clk_inv_cal,
# clock_components) and INVx4 of the INV-pair trees.  Census of the masters on the clock network of routed DBs (backward walk
# from sequential CLK pins, tools/die_plan/nomcap_clkcells.tcl; nomcap_libs/census.json): S81 serdes H17 BUFx4/6f/10/12/12f/
# 16f/24 + INVx4, HEAD hd_serdes sd9he BUFx4/6f/10/12/12f/16f/24.  Data-only masters keep the range: INVx1/2/3/5/6/8/11/13,
# INVxp33/xp67, HB1-4xp67 (hold pads).
CLOCK_CELLS = (
    "BUFx2", "BUFx3", "BUFx4", "BUFx4f", "BUFx5", "BUFx6f", "BUFx8", "BUFx10", "BUFx12", "BUFx12f", "BUFx16f", "BUFx24",
    "CKINVDCx5p33", "CKINVDCx6p67", "CKINVDCx8", "CKINVDCx9p33", "CKINVDCx10", "CKINVDCx11", "CKINVDCx12",
    "CKINVDCx14", "CKINVDCx16", "CKINVDCx20",
    "INVx4",
)
SEQ_CLOCK_PIN = "CLK"
RANGE_RE = re.compile(r"^\s*(rise|fall)_capacitance_range\b")
CELL_RE = re.compile(r"^\s*cell\s*\(\s*\"?([\w]+)\"?\s*\)\s*\{")
PIN_RE = re.compile(r"^\s*pin\s*\(\s*\"?([\w\[\]]+)\"?\s*\)\s*\{")
DIR_RE = re.compile(r"^\s*direction\s*:\s*\"?(\w+)")


def enabled():
    return os.environ.get("OT_NOMCAP", "1").strip() not in ("0", "off", "OFF", "no", "false")


def out_name(src_name):
    return src_name if src_name.endswith(".gz") else src_name + ".gz"


def strip_lib(text, kind):
    """-> (new text, [(cell, pin, removed line count)]).  Pin blocks are buffered so `direction` may follow the ranges."""
    lines = text.splitlines(keepends=True)
    out, stripped = [], []
    cell, i, n = None, 0, len(lines)
    while i < n:
        line = lines[i]
        mc = CELL_RE.match(line)
        if mc:
            cell = mc.group(1)
        mp = PIN_RE.match(line)
        if not mp:
            out.append(line)
            i += 1
            continue
        depth, j, block = 0, i, []
        while j < n:
            block.append(lines[j])
            depth += lines[j].count("{") - lines[j].count("}")
            j += 1
            if depth <= 0:
                break
        pin = mp.group(1)
        direction = next((m.group(1) for m in (DIR_RE.match(b) for b in block) if m), "")
        base = re.sub(r"_ASAP7_75t_[RLS]$", "", cell or "")
        hit = direction == "input" and ((kind == "INVBUF" and base in CLOCK_CELLS) or (kind == "SEQ" and pin == SEQ_CLOCK_PIN))
        if hit:
            keep = [b for b in block if not RANGE_RE.match(b)]
            if len(keep) != len(block):
                stripped.append((cell, pin, len(block) - len(keep)))
            block = keep
        out.extend(block)
        i = j
    return "".join(out), stripped


def _gz_bytes(text, name):
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as g:
        g.write(text.encode())
    return buf.getvalue()


def _read(p):
    return gzip.open(p, "rt").read() if str(p).endswith(".gz") else Path(p).read_text()


def build(src, out):
    out.mkdir(parents=True, exist_ok=True)
    man = {"ruling": "r708", "switch": "OT_NOMCAP (default 1)", "clock_cells": list(CLOCK_CELLS),
           "seq_clock_pin": SEQ_CLOCK_PIN, "removed_attributes": ["rise_capacitance_range", "fall_capacitance_range"],
           "libraries": []}
    census = out / "census.json"
    if census.is_file():
        man["census"] = json.loads(census.read_text())
    for kind, pat in SOURCES.items():
        for c in CORNERS:
            sp = Path(src) / pat.format(c=c)
            raw = sp.read_bytes()
            text, stripped = strip_lib(_read(sp), kind)
            data = _gz_bytes(text, out_name(sp.name))
            (out / out_name(sp.name)).write_bytes(data)
            cells = sorted({s[0] for s in stripped})
            if kind == "INVBUF":
                missing = sorted(set(CLOCK_CELLS) - {re.sub(r"_ASAP7_75t_[RLS]$", "", x) for x in cells})
                if missing:
                    raise SystemExit(f"nomcap: {sp.name}: clock cells without a range on an input pin: {missing}")
            man["libraries"].append(dict(kind=kind, corner=c, source=sp.name, source_sha256=hashlib.sha256(raw).hexdigest(),
                                         file=out_name(sp.name), sha256=hashlib.sha256(data).hexdigest(),
                                         removed_lines=sum(s[2] for s in stripped),
                                         pins=[f"{s[0]}/{s[1]}" for s in stripped]))
            print(f"nomcap: {out_name(sp.name)} pins {len(stripped)} lines {sum(s[2] for s in stripped)}")
    (out / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man


def manifest(d=LIB_DIR):
    return json.loads((Path(d) / "MANIFEST.json").read_text())


def check(d=LIB_DIR):
    bad = []
    for r in manifest(d)["libraries"]:
        p = Path(d) / r["file"]
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
            bad.append(r["file"])
    return bad


def replacement(name):
    """native ORFS base name -> nomcap file name (None if not replaced)."""
    for kind, pat in SOURCES.items():
        for c in CORNERS:
            if name == pat.format(c=c):
                return out_name(name)
    return None


def map_paths(paths, libdir=None):
    """replace native INVBUF/SEQ RVT liberty paths by the nomcap copies (host paths in libdir, default the repo dir)."""
    if not enabled():
        return list(paths)
    d = Path(libdir) if libdir else LIB_DIR
    res = []
    for p in paths:
        r = replacement(Path(str(p)).name)
        res.append(str(d / r) if r and (d / r).is_file() else str(p))
    return res


def stage(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for r in manifest()["libraries"]:
        shutil.copyfile(LIB_DIR / r["file"], dest / r["file"])
    shutil.copyfile(LIB_DIR / "MANIFEST.json", dest / "MANIFEST.json")
    return dest


def config_mk_lines(kit_dir="/work/nomcap"):
    """ORFS make lines that point the platform NLDM lists at the kit copies (the design config is read before the
    platform config.mk, whose *_NLDM_LIB_FILES are ?= assignments).  The switch is read when the kit is generated."""
    L = ["# NOMCAP-1118 r708: nominal input-pin load on clock cells + sequential CLK pins (tools/die_plan/nomcap.py)"]
    for corner, key in (("FF", "BC"), ("SS", "WC"), ("TT", "TC")):
        files = [f"$(PLATFORM_DIR)/lib/NLDM/asap7sc7p5t_AO_RVT_{corner}_nldm_211120.lib.gz",
                 f"{kit_dir}/{out_name(SOURCES['INVBUF'].format(c=corner))}",
                 f"$(PLATFORM_DIR)/lib/NLDM/asap7sc7p5t_OA_RVT_{corner}_nldm_211120.lib.gz",
                 f"$(PLATFORM_DIR)/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_{corner}_nldm_211120.lib.gz",
                 f"{kit_dir}/{out_name(SOURCES['SEQ'].format(c=corner))}"]
        L.append(f"export {key}_NLDM_LIB_FILES = " + " ".join(files))
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build")
    b.add_argument("--src", required=True)
    b.add_argument("--out", default=str(LIB_DIR))
    sp.add_parser("check")
    s = sp.add_parser("stage")
    s.add_argument("dest")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        build(a.src, Path(a.out))
    elif a.cmd == "check":
        bad = check()
        print("nomcap check", "FAIL " + " ".join(bad) if bad else "PASS")
        return 1 if bad else 0
    elif a.cmd == "stage":
        print(stage(a.dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
