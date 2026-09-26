#!/usr/bin/env python3
"""Sign-off power, power-grid and clock analysis on routed ASAP7 blocks.

A companion to tools/run_abi3_physical.py.  It works on a routed ORFS work
directory retained with ``run_abi3_physical.py --keep-workdir`` (6_final.odb,
6_final.spef, 6_final.v, 6_final.sdc) and never changes a routed record.

Subcommands
-----------
cell-models   Liberty -> Verilator-friendly behavioural models of the ASAP7
              standard cells (the platform's Verilog models use UDPs, which
              Verilator does not accept), so a routed netlist simulates inside
              the real decode campaign bench.
gl-bench      derive the gate-level variant of a campaign bench: drop the
              parameter override on the DUT and every statement that peeks
              into the DUT's RTL hierarchy.
activity      simulate a bench under Verilator with a VCD streamed through a
              FIFO into tools/signoff/vcd2saif (nothing large reaches the disk)
              and write a SAIF for one scope over a cycle window.
power         OpenROAD/OpenSTA report_power at the routed parasitics with
              switching activity from a SAIF (or a default activity), per
              hierarchy group (instance-name prefix), per corner.
irdrop        OpenROAD PSM static IR drop and electromigration on the routed
              PDN with the per-instance power of `power`.
clock         clock-tree metrics: latency, skew, buffer and sink counts, clock
              power share.
corners       multi-corner STA (ASAP7 SS/TT/FF liberty in the ORFS image) with
              optional on-chip-variation derates: WNS and Fmax per corner.
all           power + irdrop + clock + corners in one container session and
              one results JSON.

Results JSON go under results/physical_abi3/asap7/signoff/ (see
docs/POWER_CLOCK_SIGNOFF.md).  The ORFS image is openroad/orfs:latest, the
one that routed the blocks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "openroad/orfs:latest"
PLATFORM = "/OpenROAD-flow-scripts/flow/platforms/asap7"
SIGNOFF_DIR = ROOT / "results/physical_abi3/asap7/signoff"
VCD2SAIF_SRC = ROOT / "tools/signoff/vcd2saif.cpp"
SCHEMA = "opentallas.signoff.v1"

# ASAP7 corners the ORFS image ships (platforms/asap7/config.mk): liberty
# process tag, supply and temperature exactly as ORFS pairs them.
CORNERS: dict[str, dict[str, Any]] = {
    "SS": {"lib_tag": "SS", "voltage_v": 0.63, "temperature_c": 100.0, "process": "slow"},
    "TT": {"lib_tag": "TT", "voltage_v": 0.70, "temperature_c": 25.0, "process": "typical"},
    "FF": {"lib_tag": "FF", "voltage_v": 0.77, "temperature_c": 0.0, "process": "fast"},
}
# RVT libraries of one corner (file names as the ORFS image ships them).
LIB_TEMPLATES = (
    "asap7sc7p5t_AO_RVT_{c}_nldm_211120.lib.gz",
    "asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz",
    "asap7sc7p5t_OA_RVT_{c}_nldm_211120.lib.gz",
    "asap7sc7p5t_SIMPLE_RVT_{c}_nldm_211120.lib.gz",
    "asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib",
    "asap7sc7p5t_DFFHQNH2V2X_RVT_{c}_nldm_FAKE.lib",
    "asap7sc7p5t_DFFHQNV2X_RVT_{c}_nldm_FAKE.lib",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Liberty -> behavioural Verilog
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"\s*(\(|\)|!|'|\*|\+|\^|&|\||[A-Za-z_][A-Za-z0-9_]*|0|1)")


def liberty_expr_to_verilog(expr: str) -> str:
    """Translate a Liberty boolean function to a Verilog expression.

    Liberty: ! and postfix ' are NOT, * & and juxtaposition are AND, + | OR,
    ^ XOR.  The translation is a precedence-preserving recursive descent, so
    the result is fully parenthesised and does not rely on Verilog precedence.
    """
    toks: list[str] = []
    pos = 0
    s = expr.strip()
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"unparsable liberty function {expr!r} at {pos}")
        toks.append(m.group(1))
        pos = m.end()
        while pos < len(s) and s[pos].isspace():
            pos += 1
    i = 0

    def peek() -> str | None:
        return toks[i] if i < len(toks) else None

    def take() -> str:
        nonlocal i
        i += 1
        return toks[i - 1]

    def primary() -> str:
        t = peek()
        if t == "!":
            take()
            return f"(~{primary()})"
        if t == "(":
            take()
            e = orx()
            if take() != ")":
                raise ValueError(f"unbalanced liberty function {expr!r}")
            v = f"({e})"
        elif t in ("0", "1"):
            take()
            v = f"1'b{t}"
        elif t is not None and re.fullmatch(r"[A-Za-z_]\w*", t):
            v = take()
        else:
            raise ValueError(f"unexpected {t!r} in liberty function {expr!r}")
        while peek() == "'":
            take()
            v = f"(~{v})"
        return v

    def andx() -> str:
        parts = [primary()]
        while True:
            t = peek()
            if t in ("*", "&"):
                take()
                parts.append(primary())
            elif t is not None and (t in ("(", "!", "0", "1") or re.fullmatch(r"[A-Za-z_]\w*", t)):
                parts.append(primary())   # juxtaposition
            else:
                break
        return parts[0] if len(parts) == 1 else "(" + " & ".join(parts) + ")"

    def xorx() -> str:
        parts = [andx()]
        while peek() == "^":
            take()
            parts.append(andx())
        return parts[0] if len(parts) == 1 else "(" + " ^ ".join(parts) + ")"

    def orx() -> str:
        parts = [xorx()]
        while peek() in ("+", "|"):
            take()
            parts.append(xorx())
        return parts[0] if len(parts) == 1 else "(" + " | ".join(parts) + ")"

    out = orx()
    if i != len(toks):
        raise ValueError(f"trailing tokens in liberty function {expr!r}")
    return out


def _groups(text: str, keyword: str) -> Iterable[tuple[str, str]]:
    """Yield (argument, body) of every `keyword (arg) { body }` group at any depth."""
    for m in re.finditer(rf"\b{keyword}\s*\(([^)]*)\)\s*\{{", text):
        depth, j = 1, m.end()
        while depth and j < len(text):
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        yield m.group(1).strip().strip('"'), text[m.end():j - 1]


def _attr(body: str, name: str) -> str | None:
    m = re.search(rf"\b{name}\s*:\s*\"?([^\";]*)\"?\s*;", body)
    return m.group(1).strip() if m else None


def _edge(expr: str) -> tuple[str, str]:
    """A single-literal liberty control ('CLK', '!RESETN') -> (edge, signal)."""
    e = expr.replace(" ", "")
    if re.fullmatch(r"!?\w+", e):
        return ("negedge", e[1:]) if e.startswith("!") else ("posedge", e)
    raise ValueError(f"unsupported sequential control {expr!r}")


def _lvl(expr: str) -> str:
    return liberty_expr_to_verilog(expr)


def cell_model(name: str, body: str) -> str:
    """Behavioural Verilog of one Liberty cell (zero delay, 2-state friendly)."""
    pins: list[tuple[str, str, str | None]] = []
    for pin, pbody in _groups(body, "pin"):
        direction = _attr(pbody, "direction") or "input"
        if direction == "internal":
            continue
        pins.append((pin, direction, _attr(pbody, "function") or _attr(pbody, "state_function")))
    if "statetable" in body:
        # integrated clock gate: IQ latches (ENA | SE) while CLK is low
        if not re.search(r'statetable\s*\(\s*"CLK ENA SE"\s*,\s*"IQ"', body):
            raise ValueError(f"{name}: statetable other than the ICG latch is not modelled")
        ports = ",\n".join(f"    {'output' if d == 'output' else 'input'} wire {p}" for p, d, _ in pins)
        outs = "".join(f"    assign {p} = {_lvl(fn)};\n" for p, d, fn in pins if d == "output")
        return (f"module {name} (\n{ports}\n);\n    reg IQ = 1'b0;\n"
                f"    always @* if (!CLK) IQ = ENA | SE;\n{outs}endmodule\n")
    ffs = list(_groups(body, "ff"))
    latches = list(_groups(body, "latch"))
    lines = [f"module {name} ("]
    lines.append(",\n".join(f"    {'output' if d == 'output' else 'input'} wire {p}" for p, d, _ in pins))
    lines.append(");")
    state_names: list[str] = []
    for arg, gbody in ffs:
        v1, v2 = [a.strip() for a in arg.split(",")]
        state_names += [v1, v2]
        edge, clk = _edge(_attr(gbody, "clocked_on"))
        nxt = _lvl(_attr(gbody, "next_state"))
        clear, preset = _attr(gbody, "clear"), _attr(gbody, "preset")
        both = _attr(gbody, "clear_preset_var1") or "L"
        sens = [f"{edge} {clk}"]
        conds = []
        if clear:
            ce, cs = _edge(clear)
            sens.append(f"{ce} {cs}")
            conds.append((f"{'!' if ce == 'negedge' else ''}{cs}", "1'b0"))
        if preset:
            pe, ps = _edge(preset)
            sens.append(f"{pe} {ps}")
            conds.append((f"{'!' if pe == 'negedge' else ''}{ps}", "1'b1"))
        if clear and preset:
            # both asserted: clear_preset_var1 decides (L -> 0, H -> 1)
            conds.insert(0, (f"({conds[0][0]}) && ({conds[1][0]})", "1'b1" if both == "H" else "1'b0"))
        lines.append(f"    reg {v1} = 1'b0;")
        lines.append(f"    wire {v2} = ~{v1};")
        lines.append(f"    always @({' or '.join(sens)})")
        for k, (c, val) in enumerate(conds):
            lines.append(f"        {'if' if k == 0 else 'else if'} ({c}) {v1} <= {val};")
        lines.append(f"        {'else ' if conds else ''}{v1} <= {nxt};")
    for arg, gbody in latches:
        v1, v2 = [a.strip() for a in arg.split(",")]
        state_names += [v1, v2]
        en = _lvl(_attr(gbody, "enable"))
        din = _lvl(_attr(gbody, "data_in"))
        lines.append(f"    reg {v1} = 1'b0;")
        lines.append(f"    wire {v2} = ~{v1};")
        lines.append(f"    always @* if ({en}) {v1} = {din};")
    for p, d, fn in pins:
        if d == "output":
            if fn is None:
                raise ValueError(f"{name}.{p}: output without a function (statetable cells are not modelled)")
            lines.append(f"    assign {p} = {_lvl(fn)};")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def liberty_cells(paths: Iterable[Path]) -> dict[str, str]:
    cells: dict[str, str] = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        for name, body in _groups(text, "cell"):
            cells[name] = body
    return cells


def netlist_cell_types(netlist: Path) -> set[str]:
    types: set[str] = set()
    pat = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s+[\\A-Za-z_]")
    with open(netlist, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.match(line)
            if m and m.group(1) not in ("wire", "input", "output", "inout", "module", "assign", "reg"):
                types.add(m.group(1))
    return types


def write_cell_models(libs: list[Path], out: Path, only: set[str] | None = None) -> dict[str, Any]:
    cells = liberty_cells(libs)
    chosen = sorted(c for c in cells if only is None or c in only)
    missing = sorted((only or set()) - set(cells))
    text = ["// Generated by tools/signoff_analysis.py cell-models from Liberty; zero-delay behavioural",
            "// models for gate-level activity simulation under Verilator.  Do not edit.",
            "/* verilator lint_off UNOPTFLAT */",
            "// cell internals are not traced: the netlist's own nets carry every toggle",
            "/* verilator tracing_off */"]
    skipped = []
    for c in chosen:
        try:
            text.append(cell_model(c, cells[c]))
        except ValueError as exc:
            skipped.append({"cell": c, "reason": str(exc)})
    out.write_text("\n".join(text), encoding="utf-8")
    return {"models": len(chosen) - len(skipped), "skipped": skipped, "missing": missing}


# ---------------------------------------------------------------------------
# Gate-level bench
# ---------------------------------------------------------------------------
def _stmt_end(lines: list[str], i: int) -> int:
    """Index of the last line of the statement starting at lines[i]."""
    text = lines[i]
    depth_paren = text.count("(") - text.count(")")
    j = i
    stripped = text.strip()
    opens_block = bool(re.search(r"\bbegin\b", stripped))
    if opens_block:
        depth = len(re.findall(r"\bbegin\b", text)) - len(re.findall(r"\bend\b", text))
        while depth > 0:
            j += 1
            depth += len(re.findall(r"\bbegin\b", lines[j])) - len(re.findall(r"\bend\b", lines[j]))
        return j
    while depth_paren > 0 or not lines[j].rstrip().endswith(";"):
        # an `if (...)` header without begin: the body is the next statement
        if depth_paren == 0 and re.match(r"\s*(if|else|always)\b", lines[j]) and not lines[j].rstrip().endswith(";"):
            return _stmt_end(lines, j + 1)
        j += 1
        depth_paren += lines[j].count("(") - lines[j].count(")")
    return j


def gate_level_bench(text: str, dut_module: str, dut_instance: str = "dut") -> tuple[str, list[str]]:
    """Gate-level variant of a campaign bench.

    The routed netlist is flat with its parameters baked in, so the DUT
    instantiation loses its #(...) override, and every statement that reads
    the DUT's RTL hierarchy (``dut.<name>`` -- utilisation counters, traces,
    timeout diagnostics) is removed.  Returns the new text and the removed
    statements (for the record).
    """
    text = re.sub(rf"\b{dut_module}\s*#\s*\((?:[^()]|\([^()]*\))*\)\s*{dut_instance}\b",
                  f"{dut_module} {dut_instance}", text, count=1)
    lines = text.split("\n")
    out: list[str] = []
    removed: list[str] = []
    i = 0
    hier = re.compile(rf"\b{dut_instance}\.[A-Za-z_]")
    while i < len(lines):
        if hier.search(lines[i]):
            # climb to the statement start: a one-line `if (...)` header above
            start = i
            if out and re.match(r"\s*if\s*\(.*\)\s*$", out[-1]) and not out[-1].rstrip().endswith(";"):
                start = i - 1
                out.pop()
            end = _stmt_end(lines, start if start == i else start)
            if start != i:
                end = max(end, _stmt_end(lines, i))
            removed.append("\n".join(lines[start:end + 1]).strip())
            i = end + 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), removed


# ---------------------------------------------------------------------------
# OpenROAD session script
# ---------------------------------------------------------------------------
def corner_libs(corner: str) -> list[str]:
    tag = CORNERS[corner]["lib_tag"]
    return [f"{PLATFORM}/lib/NLDM/{t.format(c=tag)}" for t in LIB_TEMPLATES]


TCL_PRELUDE = r"""
proc emit {key value} { puts "SIGNOFF $key=$value" }
proc sum_list {l} { set s 0.0; foreach x $l { set s [expr {$s + $x}] }; return $s }
"""

TCL_LOAD = r"""
foreach lib $::so_libs { read_liberty $lib }
read_db $::so_odb
read_sdc $::so_sdc
if {$::so_spef ne ""} {
    read_spef $::so_spef
} else {
    # pre-route stage (e.g. 4_cts.odb): placement-estimated wire parasitics
    source $::so_platform/setRC.tcl
    estimate_parasitics -placement
}
set_cmd_units -time ns -power W
"""

TCL_POWER = r"""
# -- activity ---------------------------------------------------------------
if {$::so_saif ne ""} {
    read_saif -scope $::so_saif_scope $::so_saif
}
report_activity_annotation
# -- design totals by OpenSTA group ------------------------------------------
# sta::design_power: {total sequential combinational clock macro pad} x
# {internal switching leakage total}, watts
set dp [sta::design_power [sta::cmd_scene]]
set k 0
foreach grp {total sequential combinational clock macro pad} {
    foreach part {internal switching leakage total} {
        emit power.$grp.${part}_w [lindex $dp $k]
        incr k
    }
}
# -- per hierarchy prefix (flat netlist: instance names keep the RTL path) ----
set prefixes $::so_groups
foreach p $prefixes { set gp($p) {0.0 0.0 0.0 0.0 0} }
set gp(__other__) {0.0 0.0 0.0 0.0 0}
set fh ""
if {$::so_inst_power ne ""} { set fh [open $::so_inst_power w] }
foreach inst [get_cells *] {
    set name [get_full_name $inst]
    set ip [sta::instance_power $inst [sta::cmd_scene]]
    set key __other__
    foreach p $prefixes { if {[string first $p $name] == 0} { set key $p; break } }
    lassign $gp($key) a b c d n
    set gp($key) [list [expr {$a + [lindex $ip 0]}] [expr {$b + [lindex $ip 1]}] \
                     [expr {$c + [lindex $ip 2]}] [expr {$d + [lindex $ip 3]}] [expr {$n + 1}]]
    if {$fh ne ""} { puts $fh "$name [lindex $ip 3]" }
}
if {$fh ne ""} { close $fh }
foreach key [array names gp] {
    lassign $gp($key) a b c d n
    emit hier.$key.internal_w $a
    emit hier.$key.switching_w $b
    emit hier.$key.leakage_w $c
    emit hier.$key.total_w $d
    emit hier.$key.instances $n
}
"""

TCL_CLOCK = r"""
# -- clock tree ----------------------------------------------------------------
set clk [lindex [all_clocks] 0]
emit clock.name [get_name $clk]
emit clock.period_ns [get_property $clk period]
set sinks 0
foreach pin [get_pins -hierarchical */CLK] { incr sinks }
emit clock.register_clock_pins $sinks
set bufs 0
set bufarea 0.0
set block [ord::get_db_block]
foreach inst [$block getInsts] {
    set n [$inst getName]
    if {[string match clkbuf_* $n] || [string match clkload* $n] || [string match *clk_buf* $n]} {
        incr bufs
        set m [$inst getMaster]
        set bufarea [expr {$bufarea + [$m getWidth] * [$m getHeight] / 1.0e6}]
    }
}
emit clock.tree_cells $bufs
emit clock.tree_cell_area_um2 $bufarea
set cnets 0
foreach net [$block getNets] {
    if {[string match clknet_* [$net getName]]} { incr cnets }
}
emit clock.nets $cnets
report_clock_skew -setup -digits 4
report_clock_skew -hold -digits 4
report_clock_latency -digits 4
"""

TCL_TIMING = r"""
# -- timing at this corner -------------------------------------------------
emit timing.setup_wns_s [sta::worst_slack_cmd max]
emit timing.hold_wns_s [sta::worst_slack_cmd min]
emit timing.setup_tns_s [sta::total_negative_slack_cmd max]
emit timing.hold_tns_s [sta::total_negative_slack_cmd min]
report_clock_min_period
if {$::so_derate > 0} {
    set_timing_derate -early [expr {1.0 - $::so_derate}]
    set_timing_derate -late [expr {1.0 + $::so_derate}]
    emit timing_ocv.setup_wns_s [sta::worst_slack_cmd max]
    emit timing_ocv.hold_wns_s [sta::worst_slack_cmd min]
    report_clock_min_period
    unset_timing_derate
}
"""

TCL_IR = r"""
# -- static IR drop (PSM) with the activity-annotated instance power ---------
# PINS : the block's own M6 PDN pins are ideal sources (block-level sign-off:
#        the parent grid is assumed ideal at the block boundary).
# BUMPS: an explicit flip-chip bump array written as a PSM source file
#        (x,y,size,voltage per line): VDD and VSS bumps alternate in a
#        checkerboard of pitch so_bump_pitch um and land on the block's top
#        PDN layer, i.e. no upper redistribution grid (a pessimistic bound).
set_pdnsim_net_voltage -net VDD -voltage $::so_vdd
set_pdnsim_net_voltage -net VSS -voltage 0.0
set die [[ord::get_db_block] getDieArea]
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
set dx0 [expr {[$die xMin] / double($dbu)}]
set dy0 [expr {[$die yMin] / double($dbu)}]
set dx1 [expr {[$die xMax] / double($dbu)}]
set dy1 [expr {[$die yMax] / double($dbu)}]
emit ir.die_um "[expr {$dx1 - $dx0}]x[expr {$dy1 - $dy0}]"
foreach net {VDD VSS} {
    set vf [file join $::so_out ir_${net}.csv]
    set ef [file join $::so_out em_${net}.csv]
    psm::clear_solvers
    if {$::so_source eq "BUMPS"} {
        set src [file join $::so_out bumps_${net}.csv]
        set fh [open $src w]
        set p $::so_bump_pitch
        set nx [expr {max(1, int(floor(($dx1 - $dx0) / $p)))}]
        set ny [expr {max(1, int(floor(($dy1 - $dy0) / $p)))}]
        set ox [expr {$dx0 + (($dx1 - $dx0) - ($nx - 1) * $p) / 2.0}]
        set oy [expr {$dy0 + (($dy1 - $dy0) - ($ny - 1) * $p) / 2.0}]
        set nb 0
        for {set i 0} {$i < $nx} {incr i} {
            for {set j 0} {$j < $ny} {incr j} {
                set is_vdd [expr {(($i + $j) % 2) == 0}]
                if {($net eq "VDD") != $is_vdd && !($nx == 1 && $ny == 1)} { continue }
                set v [expr {$net eq "VDD" ? $::so_vdd : 0.0}]
                puts $fh "[expr {$ox + $i * $p}],[expr {$oy + $j * $p}],$::so_bump_size,$v"
                incr nb
            }
        }
        close $fh
        emit ir.bumps.$net $nb
        analyze_power_grid -net $net -vsrc $src -voltage_file $vf -enable_em -em_outfile $ef
    } else {
        analyze_power_grid -net $net -voltage_file $vf -enable_em -em_outfile $ef
    }
}
"""


# ---------------------------------------------------------------------------
# Running a session in the ORFS image and parsing it
# ---------------------------------------------------------------------------
# ORFS stage -> the database and constraints it leaves; only "final" has a SPEF
STAGE_FILES = {"final": ("6_final.odb", "6_final.sdc", "6_final.spef"),
               "cts": ("4_cts.odb", "4_cts.sdc", None)}


def stage_netlist(workdir: Path) -> Path:
    """The netlist whose flop instance names a mapping uses: the routed one, else
    the synthesised one (placement and CTS add buffers but keep flop names)."""
    try:
        return find_results_dir(workdir, "final") / "6_final.v"
    except FileNotFoundError:
        return find_results_dir(workdir, "cts") / "1_2_yosys.v"


def find_results_dir(path: Path, stage: str = "final") -> Path:
    """The ORFS results directory holding the stage's database under a kept workdir."""
    odb = STAGE_FILES[stage][0]
    path = Path(path)
    if (path / odb).exists():
        return path
    hits = sorted(path.glob(f"**/results/*/*/base/{odb}"))
    if not hits:
        raise FileNotFoundError(f"no {odb} under {path}")
    return hits[0].parent


def tcl_list(items: Iterable[str]) -> str:
    return "{" + " ".join("{" + str(i) + "}" for i in items) + "}"


def session_script(results: str, out: str, corner: str, *, saif: str = "", saif_scope: str = "",
                   groups: list[str] | None = None, inst_power: str = "", derate: float = 0.0,
                   stages: tuple[str, ...] = ("power", "clock", "timing"), ir_sources: tuple[str, ...] = (),
                   bump_pitch_um: float = 140.0, bump_size_um: float = 50.0, spef: bool = True,
                   stage: str = "final") -> str:
    """The OpenROAD Tcl of one analysis session (paths as seen in the container)."""
    c = CORNERS[corner]
    head = [
        f"set ::so_libs {tcl_list(corner_libs(corner))}",
        f"set ::so_odb {results}/{STAGE_FILES[stage][0]}",
        f"set ::so_sdc {results}/{STAGE_FILES[stage][1]}",
        f"set ::so_spef {{{results + '/' + STAGE_FILES[stage][2] if spef and STAGE_FILES[stage][2] else ''}}}",
        f"set ::so_platform {PLATFORM}",
        f"set ::so_saif {{{saif}}}",
        f"set ::so_saif_scope {{{saif_scope}}}",
        f"set ::so_groups {tcl_list(groups or [])}",
        f"set ::so_inst_power {{{inst_power}}}",
        f"set ::so_derate {derate}",
        f"set ::so_vdd {c['voltage_v']}",
        f"set ::so_bump_pitch {int(round(bump_pitch_um))}",
        f"set ::so_bump_size {int(round(bump_size_um))}",
        f"set ::so_out {out}",
        f"file mkdir {out}",
    ]
    body = [TCL_PRELUDE, TCL_LOAD, f"emit corner.name {corner}\n"]
    if "power" in stages:
        body.append(TCL_POWER)
    if "clock" in stages:
        body.append(TCL_CLOCK)
    if "timing" in stages:
        body.append(TCL_TIMING)
    for src in ir_sources:
        body.append(f"set ::so_source {src}\nputs \"IRSOURCE {src}\"\n"
                    + TCL_IR.replace("-allow_reuse", "")
                    .replace("ir_${net}", f"ir_{src}_${{net}}").replace("em_${net}", f"em_{src}_${{net}}"))
    return "\n".join(head) + "\n" + "\n".join(body)


_EMIT = re.compile(r"^SIGNOFF (\S+?)=(.*)$")
_MINPER = re.compile(r"^(\S+) period_min = ([0-9.eE+-]+) fmax = ([0-9.eE+-]+)")
_SKEW = re.compile(r"^\s*(-?[0-9.]+) (setup|hold) skew")
_LAT = re.compile(r"^\s*([0-9.]+)\s+([0-9.]+) latency$")
_IR_FIELDS = {
    "Net": "net", "Total power": "total_power_w", "Supply voltage": "supply_v",
    "Worstcase voltage": "worst_voltage_v", "Average voltage": "average_voltage_v",
    "Average IR drop": "average_ir_drop_v", "Worstcase IR drop": "worst_ir_drop_v",
    "Percentage drop": "worst_drop_percent", "Maximum current": "em_max_current_a",
    "Average current": "em_average_current_a", "Number of resistors": "resistors",
}


def _num(v: str) -> Any:
    v = v.strip()
    try:
        return int(v) if re.fullmatch(r"-?\d+", v) else float(v)
    except ValueError:
        return v


def parse_session(text: str) -> dict[str, Any]:
    """Collect the SIGNOFF key=value lines and the text reports of a session."""
    out: dict[str, Any] = {"min_period": [], "skew": {}, "latency": [], "ir": []}
    ir: dict[str, Any] | None = None
    ir_source = None
    for line in text.splitlines():
        m = _EMIT.match(line)
        if m:
            out[m.group(1)] = _num(m.group(2))
            continue
        m = _MINPER.match(line)
        if m:
            out["min_period"].append({"clock": m.group(1), "period_min_ns": float(m.group(2)),
                                      "fmax_mhz": float(m.group(3))})
            continue
        m = _SKEW.match(line)
        if m:
            out["skew"].setdefault(m.group(2), float(m.group(1)))
            continue
        m = _LAT.match(line)
        if m:
            out["latency"].append({"min_ns": float(m.group(1)), "max_ns": float(m.group(2))})
            continue
        if line.startswith("IRSOURCE "):
            ir_source = line.split()[1]
            continue
        if line.startswith("########## IR report"):
            ir = {"source_type": ir_source}
            continue
        if ir is not None and ":" in line and not line.startswith("#"):
            k, v = [x.strip() for x in line.split(":", 1)]
            if k in _IR_FIELDS:
                ir[_IR_FIELDS[k]] = v if k == "Net" else _num(v.split()[0])
            if k == "Number of resistors":
                out["ir"].append(ir)
                ir = None
    return out


def run_session(script: str, mounts: dict[str, str], log: Path, timeout_s: int = 86400,
                gate_min_gb: float | None = None) -> str:
    """Run one OpenROAD session in the ORFS image; returns its stdout+stderr."""
    log.parent.mkdir(parents=True, exist_ok=True)
    tcl = log.with_suffix(".tcl")
    tcl.write_text(script, encoding="utf-8")
    args = ["docker", "run", "--rm", "-v", f"{tcl.parent.resolve()}:/so_session"]
    for host, cont in mounts.items():
        args += ["-v", f"{host}:{cont}"]
    args += [IMAGE, "bash", "-c",
             "trap 'chmod -R a+rwX /so_out >/dev/null 2>&1 || true' EXIT; "
             f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /so_session/{tcl.name}"]
    gate = os.environ.get("OT_SIGNOFF_GATE")
    env = None
    if gate and gate_min_gb:
        # a shared machine's admission gate (slot + memory floor) in front of heavy sessions
        args = [gate, *args]
        env = dict(os.environ, OT_GATE_MIN_GB=str(int(gate_min_gb)))
    t0 = time.time()
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout_s, env=env)
    text = proc.stdout + proc.stderr
    log.write_text(text, encoding="utf-8")
    if proc.returncode != 0 or re.search(r"^Error: ", text, re.M):
        raise RuntimeError(f"OpenROAD session failed (exit {proc.returncode}); see {log}")
    return text + f"\nSIGNOFF session.seconds={time.time() - t0:.1f}\n"


# ---------------------------------------------------------------------------
# IR / EM post-processing
# ---------------------------------------------------------------------------
# Stripe widths of the ORFS ASAP7 grid (platforms/asap7/openRoad/pdn/
# grid_strategy-M1-M2-M5-M6.tcl): M1/M2 follow-pins 0.018 um, M5 0.12 um,
# M6 0.288 um.  ASAP7's technology LEF carries no electromigration rules, so
# current density is reported against a stated assumption, not a PDK limit.
PDN_STRIPE_WIDTH_UM = {"M1": 0.018, "M2": 0.018, "M5": 0.12, "M6": 0.288}
# Assumed DC EM limit for the analysis: 1 mA/um of drawn width at 105 C for
# thin lower copper (the order of magnitude of published 7-10 nm BEOL
# guidance; ASAP7 publishes none).  Recorded as an assumption in every result.
EM_LIMIT_MA_PER_UM = 1.0


def ir_group_stats(csv_path: Path, groups: list[str], net: str) -> dict[str, Any]:
    """Worst and average drop per instance-name prefix from a PSM voltage file."""
    import csv
    acc: dict[str, list[float]] = {}
    supply = None
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            name = row["Instance"]
            v = float(row["Voltage"])
            key = next((g for g in groups if name.startswith(g)), "__other__")
            if name.startswith(("FILLER", "TAP", "PHY_", "DECAP")):
                key = "__physical__"
            acc.setdefault(key, []).append(v)
    out = {}
    for key, vs in acc.items():
        if net == "VDD":
            supply = supply or max(max(x) for x in acc.values())
            drops = [supply - v for v in vs]
        else:
            drops = vs
        out[key] = {"terminals": len(vs), "worst_drop_v": max(drops), "average_drop_v": sum(drops) / len(drops)}
    return out


def em_hotspots(csv_path: Path, top: int = 10) -> dict[str, Any]:
    """Per-layer maximum current and the densest stripe segments of a PSM EM file."""
    import csv
    per_layer: dict[str, dict[str, float]] = {}
    hot: list[tuple[float, dict[str, Any]]] = []
    with open(csv_path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("Node0"):
                continue
            l0, x0, y0, l1, x1, y1, cur = row[0], float(row[1]), float(row[2]), row[3], float(row[4]), \
                float(row[5]), abs(float(row[6]))
            key = l0 if l0 == l1 else f"{l0}-{l1}"
            d = per_layer.setdefault(key, {"segments": 0, "max_current_a": 0.0})
            d["segments"] += 1
            d["max_current_a"] = max(d["max_current_a"], cur)
            if l0 == l1 and l0 in PDN_STRIPE_WIDTH_UM:
                dens = cur * 1e3 / PDN_STRIPE_WIDTH_UM[l0]   # mA/um
                if len(hot) < top or dens > hot[-1][0]:
                    hot.append((dens, {"layer": l0, "x_um": x0, "y_um": y0, "x2_um": x1, "y2_um": y1,
                                       "current_a": cur, "ma_per_um": dens}))
                    hot.sort(key=lambda t: -t[0])
                    del hot[top:]
    for key, d in per_layer.items():
        if key in PDN_STRIPE_WIDTH_UM:
            d["max_ma_per_um"] = d["max_current_a"] * 1e3 / PDN_STRIPE_WIDTH_UM[key]
            d["over_assumed_limit"] = d["max_ma_per_um"] > EM_LIMIT_MA_PER_UM
    return {"per_layer": per_layer, "hotspots": [h for _, h in hot],
            "stripe_width_um": PDN_STRIPE_WIDTH_UM,
            "assumed_dc_limit_ma_per_um": EM_LIMIT_MA_PER_UM,
            "limit_basis": "assumption: ASAP7's technology LEF carries no EM rules; 1 mA/um is the order of "
                           "published 7-10 nm lower-metal DC guidance"}


# ---------------------------------------------------------------------------
# analyze: power + clock + corners (+ IR) for one routed block
# ---------------------------------------------------------------------------
def analyze(results_dir: Path, out_dir: Path, *, label: str, record: Path | None, saif: Path | None,
            saif_scope: str, groups: list[str], corners: list[str], derate: float, ir_sources: list[str],
            bump_pitch_um: float, cycles_per_token: dict[str, int] | None, activity_meta: dict | None,
            keep_ir_files: bool = False, stage: str = "final",
            gate_min_gb: float | None = None) -> dict[str, Any]:
    results_dir = find_results_dir(results_dir, stage).resolve()
    odb_name, _, spef_name = STAGE_FILES[stage]
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    mounts = {str(results_dir): "/so_res:ro", str(out_dir): "/so_out"}
    if saif:
        mounts[str(Path(saif).resolve().parent)] = "/so_saif:ro"
    saif_c = f"/so_saif/{Path(saif).name}" if saif else ""
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "label": label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": {"script": "tools/signoff_analysis.py", "sha256": sha256_file(Path(__file__)),
                 "image": IMAGE},
        "routed": {"results_dir": str(results_dir),
                   "stage": stage,
                   "parasitics": "routed SPEF (OpenRCX)" if spef_name else
                                 "placement-estimated (estimate_parasitics -placement, platform setRC.tcl)",
                   "odb_sha256": sha256_file(results_dir / odb_name),
                   "spef_sha256": sha256_file(results_dir / spef_name) if spef_name else None,
                   "netlist_sha256": sha256_file(results_dir / "6_final.v")
                   if (results_dir / "6_final.v").exists() else None},
        "activity": activity_meta or {"source": "vectorless",
                                      "note": "OpenSTA default activity (0.1 at inputs, propagated)"},
        "corners": {},
    }
    if record and Path(record).exists():
        rec = json.loads(Path(record).read_text())
        m = rec.get("place_and_route", {}).get("metrics", {})
        result["record"] = {"path": rel(record), "top": rec["design"]["top"],
                            "clock_period_ns": rec["design"]["clock_period_ns"],
                            "fmax_hz": m.get("fmax_hz"), "closed": rec["design"].get("closed"),
                            "cells": m.get("standard_cell_count"), "area_um2": m.get("standard_cell_area_um2"),
                            "core_area_um2": m.get("core_area_um2"),
                            "orfs_vectorless_power_w": m.get("power_total_w"),
                            "git_commit": rec.get("git", {}).get("commit")}
    for corner in corners:
        stages = ("power", "clock", "timing") if corner == "TT" else ("power", "timing")
        script = session_script("/so_res", f"/so_out/{corner}", corner, saif=saif_c, saif_scope=saif_scope,
                                stage=stage,
                                groups=groups, derate=derate, stages=stages,
                                ir_sources=tuple(ir_sources) if corner == "TT" else (),
                                bump_pitch_um=bump_pitch_um)
        text = run_session(script, mounts, out_dir / f"session_{corner}.log", gate_min_gb=gate_min_gb)
        parsed = parse_session(text)
        c = {"corner": CORNERS[corner], "libraries": corner_libs(corner)}
        c["power_w"] = {g: {p: parsed.get(f"power.{g}.{p}_w") for p in ("internal", "switching", "leakage", "total")}
                        for g in ("total", "sequential", "combinational", "clock", "macro")}
        hier = {}
        for key in groups + ["__other__"]:
            if f"hier.{key}.total_w" in parsed:
                hier[key] = {p: parsed.get(f"hier.{key}.{p}_w") for p in ("internal", "switching", "leakage", "total")}
                hier[key]["instances"] = parsed.get(f"hier.{key}.instances")
        c["power_by_hierarchy_w"] = hier
        c["activity_annotation"] = _annotation(text)
        wns = parsed.get("timing.setup_wns_s")
        c["timing"] = {
            "setup_wns_ns": wns * 1e9 if isinstance(wns, float) else None,
            "hold_wns_ns": _ns(parsed.get("timing.hold_wns_s")),
            "setup_tns_ns": _ns(parsed.get("timing.setup_tns_s")),
            "hold_tns_ns": _ns(parsed.get("timing.hold_tns_s")),
            "min_period": parsed["min_period"][:1],
        }
        if derate:
            c["timing_ocv"] = {"derate": derate,
                               "setup_wns_ns": _ns(parsed.get("timing_ocv.setup_wns_s")),
                               "hold_wns_ns": _ns(parsed.get("timing_ocv.hold_wns_s")),
                               "min_period": parsed["min_period"][1:2]}
        if corner == "TT":
            c["clock_tree"] = {k.split(".", 1)[1]: v for k, v in parsed.items() if k.startswith("clock.")}
            c["clock_tree"]["setup_skew_ns"] = parsed["skew"].get("setup")
            c["clock_tree"]["hold_skew_ns"] = parsed["skew"].get("hold")
            if parsed["latency"]:
                c["clock_tree"]["latency_rise_ns"] = parsed["latency"][0]
            tot = c["power_w"]["total"]["total"] or 0.0
            clk = c["power_w"]["clock"]["total"] or 0.0
            seq_int = c["power_w"]["sequential"]["internal"] or 0.0
            c["clock_tree"]["clock_network_power_share"] = clk / tot if tot else None
            c["clock_tree"]["note"] = ("clock_network_power_share is OpenSTA's Clock group (tree buffers and "
                                       "clock nets) over total; register clock-pin internal power sits in "
                                       "the Sequential group")
            c["ir"] = parsed["ir"]
            c["ir_by_hierarchy"] = {}
            c["em"] = {}
            for src in ir_sources:
                for net in ("VDD", "VSS"):
                    vf = out_dir / corner / f"ir_{src}_{net}.csv"
                    ef = out_dir / corner / f"em_{src}_{net}.csv"
                    if vf.exists():
                        c["ir_by_hierarchy"][f"{src}.{net}"] = ir_group_stats(vf, groups, net)
                    if ef.exists():
                        c["em"][f"{src}.{net}"] = em_hotspots(ef)
                    if not keep_ir_files:
                        for p in (vf, ef):
                            if p.exists():
                                p.unlink()
        c["session_seconds"] = parsed.get("session.seconds")
        result["corners"][corner] = c
    if cycles_per_token:
        result["energy_per_token"] = energy_per_token(result, cycles_per_token)
    return result


def _ns(v: Any) -> Any:
    return v * 1e9 if isinstance(v, (int, float)) else v


def _annotation(text: str) -> dict[str, Any]:
    """Parse report_activity_annotation's summary table."""
    out: dict[str, Any] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(vcd|saif|user|unannotated|annotated|Total|constant|clock|input|internal|"
                     r"default|propagated)\s+(\d+)\s*$", line, re.I)
        if m:
            out[m.group(1).lower()] = int(m.group(2))
    return out


def energy_per_token(result: dict[str, Any], cycles: dict[str, int]) -> dict[str, Any]:
    """Energy of one decode step from the activity-annotated power.

    Dynamic power scales with the clock the activity was annotated at, so the
    dynamic energy per cycle is P_dyn * T_clk; leakage accrues over the
    step's wall time at the operating clock.  Reported at the routed clock
    period (the annotation clock) and at each corner's reg-to-reg Fmax.
    """
    out = {}
    period_ns = result.get("record", {}).get("clock_period_ns")
    for corner, c in result["corners"].items():
        p = c["power_w"]["total"]
        if p["total"] is None or period_ns is None:
            continue
        dyn = (p["internal"] or 0.0) + (p["switching"] or 0.0)
        leak = p["leakage"] or 0.0
        per_cycle_dyn = dyn * period_ns * 1e-9
        e = {}
        for what, n in cycles.items():
            e[what] = {"cycles": n,
                       "dynamic_j": per_cycle_dyn * n,
                       "leakage_j_at_annotation_clock": leak * period_ns * 1e-9 * n,
                       "total_j_at_annotation_clock": (per_cycle_dyn + leak * period_ns * 1e-9) * n}
        out[corner] = {"annotation_clock_period_ns": period_ns, "dynamic_j_per_cycle": per_cycle_dyn,
                       "leakage_w": leak, "per_window": e}
    return out


# ---------------------------------------------------------------------------
# activity: gate-level simulation inside a campaign bench -> SAIF
# ---------------------------------------------------------------------------
def netlist_accepting_params(netlist: Path, out: Path, params: Iterable[str]) -> list[str]:
    """Copy a routed netlist, declaring dummy parameters so the RTL parent's
    #(...) override of the (baked) module elaborates.  The values are ignored:
    the caller checks they equal the routed configuration."""
    params = sorted(set(params))
    done = False
    with open(netlist, encoding="utf-8", errors="replace") as src, open(out, "w", encoding="utf-8") as dst:
        in_header = False
        for line in src:
            dst.write(line)
            if not done and line.lstrip().startswith("module "):
                in_header = True
            if in_header and not done and line.rstrip().endswith(");"):
                for p in params:
                    dst.write(f" parameter integer {p} = 0;\n")
                done = True
                in_header = False
    return params


def rtl_without_modules(path: Path, drop: set[str], dest_dir: Path) -> Path:
    """`path` unchanged if it defines none of `drop`; otherwise a copy under
    dest_dir with those module definitions removed (a file can hold helper
    modules the rest of the design still needs)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    pat = re.compile(r"^\s*module\s+(\w+)\b.*?^\s*endmodule\b[^\n]*\n?", re.S | re.M)
    removed = []

    def repl(m: re.Match) -> str:
        if m.group(1) in drop:
            removed.append(m.group(1))
            return f"// {m.group(1)}: replaced by its routed netlist (tools/signoff_analysis.py)\n"
        return m.group(0)

    new = pat.sub(repl, text)
    if not removed:
        return Path(path)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / Path(path).name
    out.write_text(new, encoding="utf-8")
    return out


def rtl_param_overrides(rtl_files: Iterable[Path], module: str) -> set[str]:
    """Parameter names the RTL passes to `module` in any #(...) override."""
    names: set[str] = set()
    pat = re.compile(rf"\b{module}\s*#\s*\(((?:[^()]|\([^()]*\))*)\)", re.S)
    for f in rtl_files:
        for m in pat.finditer(Path(f).read_text(encoding="utf-8", errors="replace")):
            names.update(re.findall(r"\.(\w+)\s*\(", m.group(1)))
    return names


def verilator_bin() -> str:
    """OT_VERILATOR, else the project's Verilator 5 build, else `verilator` on PATH.

    Verilator 5 elaborates a 0.85 M-cell flat netlist several times faster
    than the distribution's 4.038."""
    env = os.environ.get("OT_VERILATOR")
    if env:
        return env
    v5 = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
    return str(v5) if v5.exists() else "verilator"


def build_vcd2saif(dest: Path) -> Path:
    exe = dest / "vcd2saif"
    if not exe.exists() or exe.stat().st_mtime < VCD2SAIF_SRC.stat().st_mtime:
        subprocess.run(["g++", "-O2", "-o", str(exe), str(VCD2SAIF_SRC)], check=True)
    return exe


def activity(*, work: Path, bench: Path, bench_top: str, dut_module: str, rtl: list[Path],
             netlists: dict[str, Path], include_dirs: list[Path], liberty: list[Path],
             plusargs: list[str], scopes: dict[str, Any], window: tuple[int, ...] | None,
             half_period_ps: int, extra_verilator: list[str] | None = None,
             jobs: int = 8, trace_only_netlists: bool = False, engine: str = "verilator",
             reuse_nets: bool = False) -> dict[str, Any]:
    """Simulate `bench` with some modules replaced by routed netlists and write
    one SAIF per entry of `scopes` (name -> dotted VCD scope).

    * dut_module: module the bench instantiates as `dut`; when it is itself a
      netlist, the bench is converted with gate_level_bench().
    * rtl: RTL sources for everything that is not replaced.
    * netlists: module -> routed 6_final.v.  A netlist whose module the RTL
      instantiates with a parameter override gets dummy parameter slots.
    * window: [begin, end) in clock cycles, optionally [begin, end, every, len]
      to dump only len cycles of every `every` (uniform sampling), or None
      for the whole run.
    """
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    if reuse_nets and (work / "activity_sim.json").exists() and \
            all((work / f"{n}.nets.saif").exists() for n in scopes):
        # the simulation is done; only the mapping onto (new) routed netlists is redone
        return finish_saifs(work, scopes, json.loads((work / "activity_sim.json").read_text()))
    t0 = time.time()
    meta: dict[str, Any] = {"bench": rel(bench), "bench_top": bench_top, "plusargs": plusargs,
                            "window_cycles": list(window) if window else None,
                            "half_period_ps": half_period_ps, "netlists": {}, "rtl": [rel(p) for p in rtl]}
    text = Path(bench).read_text()
    if dut_module in netlists:
        text, removed = gate_level_bench(text, dut_module)
        meta["bench_statements_removed"] = removed
    gl_bench = work / f"{Path(bench).stem}_gl.sv"
    gl_bench.write_text(text)
    sources = [gl_bench]
    types: set[str] = set()
    for mod, net in netlists.items():
        params = rtl_param_overrides(rtl, mod)
        dst = work / f"{mod}_gl.v"
        netlist_accepting_params(net, dst, params)
        types |= netlist_cell_types(dst)
        sources.append(dst)
        meta["netlists"][mod] = {"path": str(net), "sha256": sha256_file(net), "dummy_parameters": sorted(params)}
    cells = work / "cells.v"
    meta["cell_models"] = write_cell_models(liberty, cells, types)
    sources.append(cells)
    for p in rtl:
        sources.append(rtl_without_modules(Path(p), set(netlists), work / "rtl"))
    if trace_only_netlists:
        # the RTL around the replaced modules (and the bench) is not traced:
        # the dump carries only the netlists' nets
        quiet = work / "rtl_untraced"
        quiet.mkdir(parents=True, exist_ok=True)
        netlist_files = {work / f"{m}_gl.v" for m in netlists} | {cells}
        for i, s in enumerate(sources):
            if Path(s) in netlist_files:
                continue
            q = quiet / Path(s).name
            q.write_text("/* verilator tracing_off */\n" + Path(s).read_text(encoding="utf-8", errors="replace"),
                         encoding="utf-8")
            sources[i] = q
        meta["trace_only_netlists"] = True
    meta["engine"] = engine
    if engine == "icarus":
        top = work / "so_icarus_top.sv"
        dump_scopes = ", ".join(
            "bench." + (sp["scope"] if isinstance(sp, dict) else sp).split(".", 2)[2]
            for sp in scopes.values())
        top.write_text((ROOT / "tools/signoff/icarus_top.sv.in").read_text()
                       .replace("@BENCH@", bench_top).replace("@HALF_PS@", str(half_period_ps))
                       .replace("@SCOPES@", dump_scopes))
        exe = work / "sim.vvp"
        cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", "so_icarus_top", "-DSYNTHESIS_SIGNOFF",
               *[f"-I{d}" for d in include_dirs], str(top), *map(str, sources)]
        if not exe.exists():
            b = subprocess.run(cmd, capture_output=True, text=True)
            (work / "build.log").write_text(b.stdout[-200000:] + b.stderr[-200000:])
            if b.returncode != 0:
                raise RuntimeError(f"iverilog build failed; see {work / 'build.log'}")
        run_prefix = ["vvp", "-n", str(exe)]
    else:
        harness = ROOT / "tools/signoff/activity_harness.cpp"
        vtop = f"V{bench_top}"
        obj = work / "obj"
        # a flat netlist verilates to ~1 GB of C++ per 0.85 M cells; -O0 at least
        # keeps the compile finite (RTL benches compile quickly either way)
        opt = "-O0" if netlists else "-O1"
        cmd = [verilator_bin(), "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
               "-Wno-BLKSEQ", "-Wno-UNOPTFLAT", "-Wno-PINMISSING", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN",
               "--trace", "--trace-underscore", "--trace-max-array", "1000000", "--trace-max-width", "1000000",
               "--top-module", bench_top, "-Mdir", str(obj),
               *[f"-I{d}" for d in include_dirs], *(extra_verilator or []),
               *map(str, sources), str(harness),
               "-CFLAGS", f"{opt} -DVTOP={vtop} -DVTOP_H='\"{vtop}.h\"'",
               "-MAKEFLAGS", f"OPT_FAST={opt} OPT_SLOW={opt} OPT_GLOBAL={opt}", "-j", str(jobs)]
        exe = obj / vtop
        if not exe.exists():
            b = subprocess.run(cmd, capture_output=True, text=True)
            (work / "build.log").write_text(b.stdout[-200000:] + b.stderr[-200000:])
            if b.returncode != 0:
                raise RuntimeError(f"verilator build failed; see {work / 'build.log'}")
        run_prefix = [str(exe)]
    meta["build_seconds"] = time.time() - t0
    conv = build_vcd2saif(work)
    fifo = work / "trace.fifo"
    if fifo.exists():
        fifo.unlink()
    os.mkfifo(fifo)
    # Verilator dumps in traced time and Icarus brackets its windows with
    # $dumpoff/$dumpon, so either way the accounting starts at the first
    # timestamp and DURATION is the observed time only
    begin_t, end_t = "auto", None
    # one converter per scope, fed by a tee of the FIFO
    readers = []
    tee_fifos = []
    for name, spec in scopes.items():
        scope = spec["scope"] if isinstance(spec, dict) else spec
        if engine == "icarus":   # TOP.<bench>.<path> -> so_icarus_top.bench.<path>
            scope = "so_icarus_top.bench." + scope.split(".", 2)[2]
        f = work / f"trace_{name}.fifo"
        if f.exists():
            f.unlink()
        os.mkfifo(f)
        tee_fifos.append(f)
        saif = work / f"{name}.nets.saif"
        args = [str(conv), str(f), str(saif), scope, begin_t] + ([str(end_t)] if end_t else [])
        readers.append((name, saif, subprocess.Popen(args, stderr=subprocess.PIPE, text=True)))
    tee = subprocess.Popen(f"cat {fifo} | tee {' '.join(str(f) for f in tee_fifos[1:])} > {tee_fifos[0]}",
                           shell=True)
    sim_args = [*run_prefix, f"+VCD={fifo}", f"+HALF_PS={half_period_ps}", *plusargs]
    if window:
        sim_args += [f"+VCD_BEGIN={window[0]}", f"+VCD_END={window[1]}"]
        if len(window) == 4:
            sim_args += [f"+VCD_EVERY={window[2]}", f"+VCD_LEN={window[3]}"]
    t1 = time.time()
    sim = subprocess.run(sim_args, capture_output=True, text=True)
    # a simulation that died before opening its dump leaves the readers blocked
    # on the FIFO: open and close its write end so they see end-of-file
    try:
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
    except OSError:
        pass
    tee.wait()
    meta["simulation_seconds"] = time.time() - t1
    meta["simulation_stdout_tail"] = sim.stdout.strip().splitlines()[-12:]
    meta["simulation_stderr_tail"] = sim.stderr.strip().splitlines()[-6:]
    errs = {}
    for name, saif, p in readers:
        _, err = p.communicate()
        errs[name] = err.strip()[-400:]
    meta["converter"] = errs
    (work / "activity_sim.json").write_text(json.dumps(meta, indent=2, default=str))
    finish_saifs(work, scopes, meta)
    for f in [fifo, *tee_fifos]:
        f.unlink(missing_ok=True)
    if sim.returncode != 0:
        raise RuntimeError(f"simulation failed ({sim.returncode}): {sim.stderr[-2000:]}")
    return meta


def finish_saifs(work: Path, scopes: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Turn each scope's net SAIF into the pin SAIF OpenSTA reads: expand a
    gate-level dump through its netlist, or map an RTL dump onto routed flops."""
    meta["saif"] = {}
    for name, spec in scopes.items():
        saif = work / f"{name}.nets.saif"
        entry = {"nets_path": str(saif), "scope": spec, "converter": meta.get("converter", {}).get(name),
                 "bytes": saif.stat().st_size if saif.exists() else 0, "path": str(saif)}
        mod = spec.get("netlist") if isinstance(spec, dict) else None
        if mod and saif.exists():
            pins = work / f"{name}.saif"
            entry["expansion"] = expand_saif_to_pins(saif, work / f"{mod}_gl.v", pins,
                                                     top=spec.get("saif_top", "dut"))
            entry["path"] = str(pins)
        rtl_map = spec.get("map_netlist") if isinstance(spec, dict) else None
        if rtl_map and saif.exists():
            pins = work / f"{name}.saif"
            entry["rtl_map"] = map_rtl_saif_to_netlist(saif, Path(rtl_map), pins, top=spec.get("saif_top", "dut"),
                                                       netlist_prefix=spec.get("netlist_prefix", ""))
            entry["path"] = str(pins)
        meta["saif"][name] = entry
    return meta


# ---------------------------------------------------------------------------
# plans and CLI
# ---------------------------------------------------------------------------
def _resolve(p: str | None, base: Path = ROOT) -> Path | None:
    if p is None:
        return None
    q = Path(os.path.expandvars(p))
    return q if q.is_absolute() else base / q


def campaign_sources(spec: str) -> list[Path]:
    """RTL list of a campaign script, e.g. 'tools/rtl_hdc_v41_decode_campaign.py:RTL',
    so a plan simulates exactly the sources the campaign does."""
    import importlib.util
    path, _, names = spec.partition(":")
    mod_spec = importlib.util.spec_from_file_location(Path(path).stem, ROOT / path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    out: list[Path] = []
    for name in names.split("+"):
        val: Any = mod
        for part in name.split("."):
            val = getattr(val, part)
        out += [Path(p) for p in (val if isinstance(val, (list, tuple)) else [val])]
    return out


def run_plan(plan_path: Path, *, only: list[str] | None, output: Path | None, dry_run: bool = False,
             activity_only: bool = False) -> dict:
    """Execute a sign-off plan (configs/signoff/*.json): per block, an optional
    gate-level activity capture and the analysis sessions."""
    plan = json.loads(Path(plan_path).read_text())
    out_path = output or _resolve(plan["output"])
    prior = json.loads(out_path.read_text()) if out_path and out_path.exists() else {}
    result = {"schema": SCHEMA, "plan": rel(plan_path), "architecture": plan.get("architecture"),
              "description": plan.get("description"), "blocks": dict(prior.get("blocks", {}))}
    scratch = _resolve(plan.get("scratch", "${OT_SIGNOFF_SCRATCH}"))
    for name, blk in plan["blocks"].items():
        if only and name not in only:
            continue
        print(f"[signoff] {name}", flush=True)
        if dry_run:
            continue
        work = scratch / name
        act_meta = None
        saifs: dict[str, Path] = {}
        if "activity" in blk:
            a = blk["activity"]
            if a.get("reuse") and all((work / "activity" / f"{s}.saif").exists() for s in a["scopes"]):
                act_meta = json.loads((work / "activity" / "activity.json").read_text())
            else:
                (work / "activity").mkdir(parents=True, exist_ok=True)
                sub = {"work": str(work / "activity"), "root": str(ROOT), "python": sys.executable}
                for step in a.get("prepare", []):
                    subprocess.run([s.format(**sub) for s in step], cwd=ROOT, check=True,
                                   capture_output=True, env=dict(os.environ, **a.get("prepare_env", {})))
                plusargs = [s.format(**sub) for s in a.get("plusargs", [])]
                if a.get("plusargs_file"):
                    plusargs += Path(a["plusargs_file"].format(**sub)).read_text().split()
                a = dict(a, plusargs=plusargs)
                scopes = {}
                for sname, sp in a["scopes"].items():
                    if isinstance(sp, dict) and sp.get("map_netlist"):
                        if activity_only:
                            sp = {k: v for k, v in sp.items() if k != "map_netlist"}
                        else:
                            try:
                                sp = dict(sp, map_netlist=str(stage_netlist(_resolve(sp["map_netlist"]))))
                            except FileNotFoundError as exc:   # not routed yet: its analysis is skipped
                                print(f"[signoff] scope {sname}: no netlist yet ({exc})", flush=True)
                                sp = {k: v for k, v in sp.items() if k != "map_netlist"}
                    scopes[sname] = sp
                a["scopes"] = scopes
                if a.get("rtl_from"):
                    a["rtl"] = [str(p) for p in campaign_sources(a["rtl_from"])] + list(a.get("rtl", []))
                act_meta = activity(
                    work=work / "activity", bench=_resolve(a["bench"]), bench_top=a["bench_top"],
                    dut_module=a["dut_module"], rtl=[_resolve(p) for p in a["rtl"]],
                    netlists={m: find_results_dir(_resolve(d)) / "6_final.v" for m, d in a["netlists"].items()},
                    include_dirs=[_resolve(p) for p in a.get("include_dirs", [])],
                    liberty=[_resolve(p) for p in a["liberty"]], plusargs=a.get("plusargs", []),
                    scopes=a["scopes"], window=tuple(a["window"]) if a.get("window") else None,
                    half_period_ps=a["half_period_ps"], extra_verilator=a.get("verilator_args"),
                    trace_only_netlists=a.get("trace_only_netlists", False),
                    engine=a.get("engine", "verilator"), reuse_nets=True)
                (work / "activity" / "activity.json").write_text(json.dumps(act_meta, indent=2, default=str))
            if activity_only:
                continue
            act_meta = dict(act_meta, source=(
                "gate-level simulation of the routed netlist in the campaign bench" if a.get("netlists") else
                "RTL simulation of the campaign bench, registers mapped by name onto the routed flops; "
                "OpenSTA propagates through the combinational logic"))
            saifs = {s: Path(v["path"]) for s, v in act_meta["saif"].items()}
        analyses = blk["analyses"] if "analyses" in blk else [blk]
        for an in analyses:
            key = an.get("key", name)
            try:
                find_results_dir(_resolve(an["routed"]), an.get("stage", "final"))
            except FileNotFoundError as exc:
                print(f"[signoff] {key}: skipped, {exc}", flush=True)
                continue
            saif = saifs.get(an.get("saif")) if an.get("saif") else None
            r = analyze(_resolve(an["routed"]), work / f"analysis_{key}", label=key,
                        record=_resolve(an.get("record")), saif=saif, saif_scope=an.get("saif_scope", ""),
                        groups=an.get("groups", []), corners=an.get("corners", ["TT", "SS", "FF"]),
                        derate=an.get("derate", 0.05), ir_sources=an.get("ir_sources", []),
                        bump_pitch_um=an.get("bump_pitch_um", 140.0),
                        cycles_per_token=an.get("cycles"), activity_meta=act_meta if saif else None,
                        stage=an.get("stage", "final"), gate_min_gb=an.get("gate_min_gb"))
            r["plan_entry"] = {k: v for k, v in an.items() if k not in ("routed",)}
            result["blocks"][key] = r
            if out_path:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cell-models", help="liberty -> Verilator behavioural cell models")
    c.add_argument("--liberty", action="append", required=True)
    c.add_argument("--netlist", help="only the cells this netlist uses")
    c.add_argument("--output", required=True)
    g = sub.add_parser("gl-bench", help="gate-level variant of a campaign bench")
    g.add_argument("--bench", required=True)
    g.add_argument("--dut-module", required=True)
    g.add_argument("--output", required=True)
    a = sub.add_parser("analyze", help="power/clock/corners/IR of one routed block")
    a.add_argument("--routed", required=True, help="kept workdir or ORFS results dir with 6_final.odb")
    a.add_argument("--record", help="physical.json of that route")
    a.add_argument("--saif")
    a.add_argument("--saif-scope", default="")
    a.add_argument("--group", action="append", default=[], help="instance-name prefix to total separately")
    a.add_argument("--corners", default="TT,SS,FF")
    a.add_argument("--derate", type=float, default=0.05, help="flat OCV derate (0 disables)")
    a.add_argument("--ir-source", action="append", default=[], choices=["PINS", "BUMPS"])
    a.add_argument("--bump-pitch-um", type=float, default=140.0)
    a.add_argument("--label", required=True)
    a.add_argument("--work", required=True)
    a.add_argument("--output", required=True)
    p = sub.add_parser("plan", help="run a configs/signoff/*.json plan")
    p.add_argument("plan")
    p.add_argument("--only", action="append")
    p.add_argument("--output")
    p.add_argument("--dry-run", action="store_true")
    sm = sub.add_parser("summary", help="energy per token per architecture from the sign-off results")
    sm.add_argument("config", nargs="?", default="configs/signoff/energy_per_token.json")
    sm.add_argument("--output", default="results/physical_abi3/asap7/signoff/energy_per_token.json")
    p.add_argument("--activity-only", action="store_true",
                   help="run the simulations only (the routes may not exist yet); a later run reuses them")
    args = ap.parse_args(argv)
    if args.cmd == "cell-models":
        only = netlist_cell_types(Path(args.netlist)) if args.netlist else None
        print(json.dumps(write_cell_models([Path(x) for x in args.liberty], Path(args.output), only)))
    elif args.cmd == "gl-bench":
        text, removed = gate_level_bench(Path(args.bench).read_text(), args.dut_module)
        Path(args.output).write_text(text)
        print(f"removed {len(removed)} statements")
    elif args.cmd == "analyze":
        r = analyze(Path(args.routed), Path(args.work), label=args.label,
                    record=Path(args.record) if args.record else None,
                    saif=Path(args.saif) if args.saif else None, saif_scope=args.saif_scope,
                    groups=args.group, corners=args.corners.split(","), derate=args.derate,
                    ir_sources=args.ir_source, bump_pitch_um=args.bump_pitch_um,
                    cycles_per_token=None, activity_meta=None)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    elif args.cmd == "summary":
        r = summarize(Path(args.config))
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    elif args.cmd == "plan":
        run_plan(Path(args.plan), only=args.only, output=Path(args.output) if args.output else None,
                 dry_run=args.dry_run, activity_only=args.activity_only)
    return 0



# ---------------------------------------------------------------------------
# net-level SAIF -> cell-pin SAIF (what OpenSTA's read_saif annotates)
# ---------------------------------------------------------------------------
# OpenSTA's SAIF reader annotates PINS: a NET record under an INSTANCE is looked
# up as a pin of that instance, so a flat netlist's internal nets must be
# written as the pins of every leaf cell they connect.  Tracing every cell pin
# in the simulator would multiply the dump four-fold; instead the simulator
# traces nets only and this expands them through the routed netlist.
_INST = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(")
_CONN = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(\\\S+\s*(?:\[\d+\])?|[A-Za-z_][A-Za-z0-9_$]*(?:\s*\[\d+\])?|"
                   r"\d+'[bh][0-9a-fA-FxXzZ]+)?\s*\)")


def _netkey(expr: str) -> str:
    """Netlist net reference -> the name vcd2saif writes for that bit."""
    e = expr.strip()
    if e.startswith("\\"):
        e = e[1:]
    return re.sub(r"\s+", "", e)


def _saif_escape(name: str) -> str:
    return "".join(c if (c.isalnum() or c == "_") else "\\" + c for c in name)


def _saif_instance(name: str) -> str:
    """An instance name as OpenSTA's SAIF reader finds it: '.' and '$' raw (an
    escaped '$' or '.' is not matched), brackets escaped."""
    return name.replace("[", "\\[").replace("]", "\\]")


def read_net_saif(path: Path) -> tuple[dict[str, tuple[int, int, int, int]], dict[str, str]]:
    """Net records of a vcd2saif file -> {name: (T0, T1, TX, TC)} plus its header fields."""
    rec = re.compile(r"^\s*\((\S+) \(T0 (\d+)\) \(T1 (\d+)\) \(TX (\d+)\) \(TC (\d+)\)\)")
    nets: dict[str, tuple[int, int, int, int]] = {}
    header: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = rec.match(line)
            if m:
                name = re.sub(r"\\(.)", r"\1", m.group(1)).lstrip("\\")
                nets[name] = (int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
                continue
            h = re.match(r"^\((TIMESCALE|DURATION|DIVIDER|DESIGN) (.*)\)\s*$", line)
            if h:
                header[h.group(1)] = h.group(2)
    return nets, header


def expand_saif_to_pins(net_saif: Path, netlist: Path, out: Path, top: str = "dut") -> dict[str, Any]:
    nets, header = read_net_saif(net_saif)
    stats = {"nets_in_saif": len(nets), "instances": 0, "pins_written": 0, "pins_without_activity": 0,
             "instances_skipped_name": 0, "ports_written": 0}
    ports: list[str] = []
    with open(netlist, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # module ports: every input/output bit that has a record
    for m in re.finditer(r"^\s*(input|output|inout)\s+(?:\[(\d+):(\d+)\]\s+)?(\\\S+|\w+)\s*;", text, re.M):
        name = _netkey(m.group(4))
        if m.group(2) is not None:
            hi, lo = int(m.group(2)), int(m.group(3))
            for i in range(min(hi, lo), max(hi, lo) + 1):
                ports.append(f"{name}[{i}]")
        else:
            ports.append(name)
    with open(out, "w", encoding="utf-8") as o:
        o.write('(SAIFILE\n(SAIFVERSION "2.0")\n(DIRECTION "backward")\n')
        o.write(f'(DESIGN {header.get("DESIGN", chr(34) + top + chr(34))})\n')
        o.write('(PROGRAM_NAME "opentallas signoff_analysis expand")\n(DIVIDER / )\n')
        o.write(f'(TIMESCALE {header.get("TIMESCALE", "1ps")})\n(DURATION {header.get("DURATION", "0")})\n')
        o.write(f"(INSTANCE {top}\n  (NET\n")
        for p in ports:
            r = nets.get(p)
            if r:
                o.write(f"    ({_saif_escape(p)} (T0 {r[0]}) (T1 {r[1]}) (TX {r[2]}) (TC {r[3]}))\n")
                stats["ports_written"] += 1
        o.write("  )\n")
        # instances: a statement runs from the instance header to ");"
        body = text[text.find(");") + 2:]
        for stmt in body.split(";"):
            m = _INST.match(stmt)
            if not m or m.group(1) in ("wire", "input", "output", "inout", "assign", "module", "endmodule"):
                continue
            inst = _netkey(m.group(2))
            if "/" in inst or ":" in inst:
                stats["instances_skipped_name"] += 1
                continue
            conns = _CONN.findall(stmt)
            lines = []
            for pin, expr in conns:
                if not expr or "'" in expr:
                    continue
                r = nets.get(_netkey(expr))
                if r is None:
                    stats["pins_without_activity"] += 1
                    continue
                lines.append(f"      ({pin} (T0 {r[0]}) (T1 {r[1]}) (TX {r[2]}) (TC {r[3]}))\n")
            if not lines:
                continue
            stats["instances"] += 1
            stats["pins_written"] += len(lines)
            o.write(f"  (INSTANCE {_saif_instance(inst)}\n    (NET\n")
            o.writelines(lines)
            o.write("    )\n  )\n")
        o.write(")\n)\n")
    return stats


# ---------------------------------------------------------------------------
# RTL-name matching: register activity of an RTL simulation -> routed flops
# ---------------------------------------------------------------------------
# A flat 0.85 M-cell netlist cannot be simulated gate-level here (Verilator's
# C++ for it does not compile on a loaded machine; Icarus runs ~2 cycles/s).
# Yosys keeps the RTL register path in every flop's instance name
# (`\u_me.g_grp[1].g_lane[6].u_mul.s1_a[2]$_DFF_P_`), so the register toggles
# of the fast RTL simulation of the SAME campaign map one-to-one onto the
# routed flops' outputs; OpenSTA then propagates activity through the
# combinational logic from those annotated registers and the ports.  Its error
# against true gate-level activity is measured on blocks small enough to
# simulate both ways (docs/POWER_CLOCK_SIGNOFF.md).
_FLOP_SUFFIX = re.compile(r"\$_[A-Z0-9_]+_$")


def read_nested_saif(path: Path) -> tuple[dict[str, tuple[int, int, int, int]], dict[str, str]]:
    """A vcd2saif file -> {dotted path below the top instance: (T0, T1, TX, TC)}."""
    rec = re.compile(r"^\s*\((\S+) \(T0 (\d+)\) \(T1 (\d+)\) \(TX (\d+)\) \(TC (\d+)\)\)")
    inst = re.compile(r"^\s*\(INSTANCE (\S+)")
    out: dict[str, tuple[int, int, int, int]] = {}
    header: dict[str, str] = {}
    stack: list[str] = []
    depth_of: list[int] = []   # paren depth at which each INSTANCE opened
    depth = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = rec.match(line)
            if m:
                name = re.sub(r"\\(.)", r"\1", m.group(1))
                prefix = ".".join(stack[1:])
                out[f"{prefix}.{name}" if prefix else name] = (int(m.group(2)), int(m.group(3)), int(m.group(4)),
                                                               int(m.group(5)))
                continue
            m = inst.match(line)
            if m:
                stack.append(re.sub(r"\\(.)", r"\1", m.group(1)))
                depth_of.append(depth)
                depth += line.count("(") - line.count(")")
                continue
            h = re.match(r"^\((TIMESCALE|DURATION|DIVIDER|DESIGN) (.*)\)\s*$", line)
            if h:
                header[h.group(1)] = h.group(2)
                continue
            depth += line.count("(") - line.count(")")
            while depth_of and depth <= depth_of[-1]:
                depth_of.pop()
                stack.pop()
    return out, header


def _rtl_candidates(reg: str) -> list[str]:
    """RTL-record spellings a yosys register name may correspond to."""
    c = [reg]
    # yosys names an unnamed generate scope genblkN where Verilator (and the
    # VCD) has no scope at all
    if ".genblk" in reg:
        c.append(re.sub(r"\.genblk\d+", "", reg))
    # an unpacked array element: yosys `mem[3][5]`, Verilator VCD `mem(3)[5]` or `mem[3][5]`
    m = re.match(r"^(.*)\[(\d+)\]\[(\d+)\]$", reg)
    if m:
        c.append(f"{m.group(1)}({m.group(2)})[{m.group(3)}]")
    # a scalar register: no bit index in the netlist
    return c


def map_rtl_saif_to_netlist(rtl_saif: Path, netlist: Path, out: Path, top: str = "dut",
                            flop_output_pins: tuple[str, ...] = ("QN", "Q"),
                            netlist_prefix: str = "") -> dict[str, Any]:
    """Write a pin SAIF annotating every routed flop's output (and the ports)
    from the RTL register it implements.

    netlist_prefix: map the RTL scope onto the flops of ONE instance of a larger
    routed netlist (e.g. the V4.1 core's matrix engine onto `u_me.` of the
    routed Qwen core, the same module with the same parameters); ports are
    then skipped."""
    rtl, header = read_nested_saif(rtl_saif)
    text = Path(netlist).read_text(encoding="utf-8", errors="replace")
    stats = {"rtl_records": len(rtl), "flops": 0, "flops_matched": 0, "ports": 0, "ports_matched": 0,
             "unmatched_examples": []}
    lines: list[str] = []
    for m in ([] if netlist_prefix else
              re.finditer(r"^\s*(input|output|inout)\s+(?:\[(\d+):(\d+)\]\s+)?(\\\S+|\w+)\s*;", text, re.M)):
        name = _netkey(m.group(4))
        bits = [f"{name}[{i}]" for i in range(min(int(m.group(2)), int(m.group(3))),
                                              max(int(m.group(2)), int(m.group(3))) + 1)] \
            if m.group(2) is not None else [name]
        for b in bits:
            stats["ports"] += 1
            r = rtl.get(b)
            if r:
                stats["ports_matched"] += 1
                lines.append(f"    ({_saif_escape(b)} (T0 {r[0]}) (T1 {r[1]}) (TX {r[2]}) (TC {r[3]}))\n")
    inst_lines: list[str] = []
    for stmt in text.split(";"):
        m = _INST.match(stmt)
        if not m:
            continue
        inst = _netkey(m.group(2))
        if not _FLOP_SUFFIX.search(inst) or not inst.startswith(netlist_prefix):
            continue
        pins = dict(_CONN.findall(stmt))
        out_pin = next((p for p in flop_output_pins if p in pins), None)
        if out_pin is None:
            continue
        stats["flops"] += 1
        reg = _FLOP_SUFFIX.sub("", inst)[len(netlist_prefix):]
        r = next((rtl[c] for c in _rtl_candidates(reg) if c in rtl), None)
        if r is None:
            if len(stats["unmatched_examples"]) < 12:
                stats["unmatched_examples"].append(reg)
            continue
        stats["flops_matched"] += 1
        t0, t1 = (r[1], r[0]) if out_pin == "QN" else (r[0], r[1])
        inst_lines.append(f"  (INSTANCE {_saif_instance(inst)}\n    (NET\n"
                          f"      ({out_pin} (T0 {t0}) (T1 {t1}) (TX {r[2]}) (TC {r[3]}))\n    )\n  )\n")
    with open(out, "w", encoding="utf-8") as o:
        o.write('(SAIFILE\n(SAIFVERSION "2.0")\n(DIRECTION "backward")\n')
        o.write(f'(DESIGN "{top}")\n(PROGRAM_NAME "opentallas signoff_analysis rtl-map")\n(DIVIDER / )\n')
        o.write(f'(TIMESCALE {header.get("TIMESCALE", "1ps")})\n(DURATION {header.get("DURATION", "0")})\n')
        o.write(f"(INSTANCE {top}\n  (NET\n")
        o.writelines(lines)
        o.write("  )\n")
        o.writelines(inst_lines)
        o.write(")\n)\n")
    stats["flop_match_fraction"] = stats["flops_matched"] / stats["flops"] if stats["flops"] else None
    return stats


# ---------------------------------------------------------------------------
# summary: energy per token per architecture, against the analytical model
# ---------------------------------------------------------------------------
TECH = ROOT / "configs/hardware/technology.json"


def saif_port_cycles(saif: Path, ports: Iterable[str], half_period_ps: int) -> dict[str, float]:
    """Cycles each (scalar or vector) top-level port of the SAIF's top instance was
    high: sum over bits of T1 / clock period.  Used for memory-port enables."""
    want = set(ports)
    out: dict[str, float] = {p: 0.0 for p in want}
    seen_instances = 0
    pat = re.compile(r"^\s*\((\S+) \(T0 (\d+)\) \(T1 (\d+)\)")
    with open(saif, encoding="utf-8") as f:
        for line in f:
            if line.lstrip().startswith("(INSTANCE"):
                seen_instances += 1
                if seen_instances > 1:      # vcd2saif writes the top's nets before its children
                    break
                continue
            m = pat.match(line)
            if m:
                base = m.group(1).replace("\\", "").split("[", 1)[0]
                if base in want:
                    out[base] += int(m.group(3)) / (2.0 * half_period_ps)
    return out


def tech_value(*path: str) -> dict[str, Any]:
    node: Any = json.loads(TECH.read_text())
    for p in path:
        node = node[p]
    return {"value": node["value"], "range_low": node.get("range_low"), "range_high": node.get("range_high"),
            "grade": node.get("grade"), "source": f"configs/hardware/technology.json {'.'.join(path)}"}


def _corner_energy(block: dict[str, Any], corner: str, cycles: int, period_ns: float, group: str | None,
                   instances: float) -> dict[str, Any] | None:
    c = block.get("corners", {}).get(corner)
    if not c:
        return None
    p = c["power_by_hierarchy_w"].get(group) if group else c["power_w"]["total"]
    if p is None or p.get("total") is None:
        return None
    t = period_ns * 1e-9 * cycles
    dyn = ((p.get("internal") or 0.0) + (p.get("switching") or 0.0)) * t * instances
    leak = (p.get("leakage") or 0.0) * t * instances
    return {"dynamic_j": dyn, "leakage_j": leak, "total_j": dyn + leak, "power_w": p["total"] * instances}


def summarize(cfg_path: Path) -> dict[str, Any]:
    """Energy per token of each architecture's reduced vehicle, composed from
    the sign-off results (logic, activity-annotated) and the analytical
    model's per-byte memory and link energies (configs/hardware/technology.json)."""
    cfg = json.loads(Path(cfg_path).read_text())
    cache: dict[str, dict] = {}

    def load(path: str) -> dict:
        if path not in cache:
            cache[path] = json.loads((ROOT / path).read_text())
        return cache[path]

    energy = {k: tech_value("energy", k) for k in ("rom_read_j_per_byte", "sram_read_j_per_byte", "hbm_j_per_byte")}
    energy["ucie_j_per_bit"] = {"value": 0.29e-12, "range_low": 0.29e-12, "range_high": 0.29e-12,
                                "grade": "published", "source": "configs/hardware/technology.json "
                                "links.rom_package_ucie.bytes_s note (0.29 pJ/b, UCIe on CoWoS)"}
    out: dict[str, Any] = {"schema": SCHEMA + ".energy_per_token", "config": rel(cfg_path),
                           "generated_at": datetime.now(timezone.utc).isoformat(),
                           "energy_terms": energy, "architectures": {}}
    for name, arch in cfg["architectures"].items():
        a: dict[str, Any] = {"description": arch.get("description"), "token_cycles": arch["token_cycles"],
                             "clock_period_ns": arch["clock_period_ns"], "logic": {}, "memory": {}, "links": {},
                             "static": {}, "missing": list(arch.get("missing", []))}
        cycles, period = arch["token_cycles"], arch["clock_period_ns"]
        token_s = cycles * period * 1e-9
        a["token_time_s"] = token_s
        totals = {c: 0.0 for c in ("TT", "SS", "FF")}
        for item in arch.get("logic", []):
            src = ROOT / item["signoff"]
            if not src.exists():
                a["missing"].append(f"{item['name']}: {item['signoff']} not produced")
                continue
            blk = load(item["signoff"])["blocks"].get(item["key"])
            if blk is None:
                a["missing"].append(f"{item['name']}: block {item['key']} not in {item['signoff']}")
                continue
            row = {"source": f"{item['signoff']}#blocks.{item['key']}", "group": item.get("group"),
                   "instances": item.get("instances", 1), "activity": blk.get("activity", {}).get("source"),
                   "note": item.get("note")}
            for c in totals:
                e = _corner_energy(blk, c, item.get("cycles", cycles), period, item.get("group"),
                                   item.get("instances", 1))
                if e:
                    row[c] = e
                    if not item.get("subtotal_of"):
                        totals[c] += e["total_j"]
            if item.get("subtotal_of"):
                row["subtotal_of"] = item["subtotal_of"]
            a["logic"][item["name"]] = row
        mem_tt = 0.0
        for item in arch.get("memory", []):
            nbytes = item.get("bytes_per_token")
            basis = item.get("basis")
            if nbytes is None and item.get("ports_from_saif"):
                ps = item["ports_from_saif"]
                saif = _resolve(ps["saif"])
                if saif and saif.exists():
                    cyc = saif_port_cycles(saif, ps["ports"].keys(), ps["half_period_ps"])
                    nbytes = sum(cyc[p] * b for p, b in ps["ports"].items())
                    basis = (basis or "") + f" enable-high cycles {dict((p, round(v)) for p, v in cyc.items())}"
            if nbytes is None:
                a["missing"].append(f"memory {item['name']}: no byte count")
                continue
            term = energy[item["energy"]]
            per = term["value"] * (8 if item["energy"].endswith("_bit") else 1)
            lo = (term["range_low"] or term["value"]) * (8 if item["energy"].endswith("_bit") else 1)
            hi = (term["range_high"] or term["value"]) * (8 if item["energy"].endswith("_bit") else 1)
            e = nbytes * per
            mem_tt += e
            a["memory"][item["name"]] = {"bytes_per_token": nbytes, "energy_term": item["energy"],
                                         "energy_j": e, "energy_j_low": nbytes * lo, "energy_j_high": nbytes * hi,
                                         "basis": basis}
        static_j = 0.0
        for item in arch.get("static", []):
            w = tech_value(*item["term"])["value"] * item.get("fraction", 1.0)
            static_j += w * token_s
            a["static"][item["name"]] = {"watts": w, "energy_j": w * token_s, "term": ".".join(item["term"]),
                                         "fraction": item.get("fraction", 1.0), "basis": item.get("basis")}
        a["totals_j"] = {"logic_TT": totals["TT"], "logic_SS": totals["SS"], "logic_FF": totals["FF"],
                         "memory_and_links": mem_tt, "static": static_j,
                         "token_TT": totals["TT"] + mem_tt + static_j}
        # per-MAC projection from the matrix engine
        me = arch.get("mac")
        if me and me.get("macs_per_token") and me.get("logic") in a["logic"] and "TT" in a["logic"][me["logic"]]:
            e_me = a["logic"][me["logic"]]["TT"]
            macs = me["macs_per_token"]
            a["pj_per_mac"] = {
                "matrix_engine_logic_pj_per_mac": e_me["total_j"] / macs * 1e12,
                "matrix_engine_dynamic_pj_per_mac": e_me["dynamic_j"] / macs * 1e12,
                "token_pj_per_mac": a["totals_j"]["token_TT"] / macs * 1e12,
                "macs_per_token": macs, "basis": me.get("basis"),
                "analytical_mac_energy": tech_value("energy", "mac_energy_j_per_op", me.get("format", "bf16")),
            }
        out["architectures"][name] = a
    return out


if __name__ == "__main__":
    raise SystemExit(main())
