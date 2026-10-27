#!/usr/bin/env python3
"""tie_audit.py -- what every TIEHI/TIELO cell of a tile drives, sorted into three classes (TILE-FLOW2 10-23).

Why: placed tiles carry thousands of tie cells (ORFS synth.tcl already runs `hilomap -singleton`; floorplan.tcl
repair_tie_fanout then gives every constant LOAD its own tie cell), and the owner rule forbids tied-off functional
inputs.  The count alone says nothing; this tool says what the constants are.

Classes (one per tie-driven sink pin, buffers/inverters followed through to the real load):
  a  harmless, cell-level or parameter constants: unused async SETN/RESETN of DFFASRHQN (ASAP7 has only the
     set+reset async flop), flop D tied (reset relays / static bits), SRAM repair pins (cr_*/rr_*), full-word
     w_mask / always-on r_ce, constant mux selects or other logic-cell inputs.
  b  TIE-OFF (owner rule violation): a user-module INPUT port connected to a literal constant at its instantiation in
     the RTL (`.p(1'b0)`, `.p({143'h0, x})`, `.p('0)`, `.p({8{1'b1}})`, `.p()` open).  Found from the RTL text (the
     netlist is flat, so the hierarchy is gone there); parameter / localparam / generate expressions are NOT literals
     and stay class a.
  c  unused / dead bits: constant top OUTPUT bits (tie -> buf/inv -> port), SRAM data / address / mask bits never
     driven by logic (tie-lo wd/addr/mask, disabled ports), tie cells without load, INPUT ports without any sink.

Two parts:
  1. `tie_audit.py tcl` prints an OpenROAD Tcl dump (env ODB in, OUT dir): tie_sinks.tsv (tie -> buf/inv chain ->
     final sink inst/master/pin or PORT) and ports.tsv (every top port: direction, load/driver count).
     `tie_audit.py remote --host H --odb PATH --tile T` runs it in docker (memory cap, diagnostic probe: never ot-run)
     and pulls the two TSVs back.
  2. `tie_audit.py classify --sinks tie_sinks.tsv[.gz] --ports ports.tsv --tile T [--rtl F..] [--rtl-dir D..] [--top M]`
     writes the opentallas.tie_audit.v1 JSON and a short text summary.  The older hand-probe TSV layout
     (tie_inst tie_master net sink_inst sink_master sink_pin, BUF rows not followed) is accepted too, with an
     optional --const-outputs TSV (port, buffer) for the BUF->PORT hop.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SCHEMA = "opentallas.tie_audit.v1"

# OPT-IN kit setting (spec "orfs_vars"), default OFF so closed kits regenerate byte-identically.  ORFS synth.tcl already
# maps constants with `hilomap -singleton` (one TIEHI + one TIELO per module); the one-tie-cell-per-load count comes from
# floorplan.tcl `repair_tie_fanout`.  SKIP_REPAIR_TIE_FANOUT=1 keeps the shared singleton ties.  Trade-off: the shared
# tie net then fans out to every constant load (18.7k SETN pins in the S81 frame), so repair_design buffers it across
# the tile; use it to measure, not as a default.
TIE_SHARE_ORFS_VARS = {"SKIP_REPAIR_TIE_FANOUT": "1"}

# ----------------------------------------------------------------------------------------------- part 1: OpenROAD dump
TCL = r"""# tie_audit.py dump: tie cell -> (buf/inv chain) -> final sinks; top port load counts.  env: ODB, OUT
read_db $::env(ODB)
set b [ord::get_db_block]
proc is_bufinv {m} { return [regexp {^(BUFx|INVx|HB[0-9]x|CKINVDC|BUFF)} $m] }
proc firstload {net depth} {
  foreach l [$net getITerms] {
    if {[$l isOutputSignal]} continue
    set li [$l getInst]; set lm [[$li getMaster] getName]
    if {[is_bufinv $lm] && $depth < 6} {
      foreach it [$li getITerms] {
        if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { return [firstload [$it getNet] [expr {$depth+1}]] }
      }
    }
    return "$lm.[[$l getMTerm] getName]"
  }
  foreach bt [$net getBTerms] { return "PORT.[$bt getName]" }
  return "-"
}
proc walk {f tie tm net nbuf ninv depth} {
  set n 0
  foreach s [$net getITerms] {
    if {[$s isOutputSignal]} continue
    set si [$s getInst]; set sm [[$si getMaster] getName]
    incr n
    if {[is_bufinv $sm] && $depth < 8} {
      set o ""
      foreach it [$si getITerms] { if {[$it isOutputSignal]} { set o [$it getNet] } }
      if {$o ne "" && $o ne "NULL"} {
        set nb $nbuf; set ni $ninv
        if {[string match "INV*" $sm] || [string match "CKINV*" $sm]} { incr ni } else { incr nb }
        set k [walk $f $tie $tm $o $nb $ni [expr {$depth+1}]]
        if {$k > 0} continue
      }
    }
    set q "-"
    if {[[$s getMTerm] getName] eq "D"} {
      foreach it [$si getITerms] {
        if {![$it isOutputSignal]} continue
        set qn [$it getNet]
        if {$qn eq "NULL"} continue
        set q [firstload $qn 0]
      }
    }
    puts $f "$tie\t$tm\t[$si getName]\t$sm\t[[$s getMTerm] getName]\t$nbuf\t$ninv\t$q"
  }
  foreach bt [$net getBTerms] { incr n; puts $f "$tie\t$tm\tPORT\tPORT\t[$bt getName]\t$nbuf\t$ninv\t-" }
  return $n
}
set f [open $::env(OUT)/tie_sinks.tsv w]
puts $f "tie_inst\ttie_master\tsink_inst\tsink_master\tsink_pin\tnbuf\tninv\tq_load"
foreach i [$b getInsts] {
  set m [[$i getMaster] getName]
  if {![string match "TIE*" $m]} continue
  foreach it [$i getITerms] {
    if {![$it isOutputSignal]} continue
    set n [$it getNet]
    if {$n eq "NULL"} { puts $f "[$i getName]\t$m\t-\tNOSINK\t-\t0\t0\t-"; continue }
    if {[walk $f [$i getName] $m $n 0 0 0] == 0} { puts $f "[$i getName]\t$m\t-\tNOSINK\t-\t0\t0\t-" }
  }
}
close $f
set f [open $::env(OUT)/ports.tsv w]
puts $f "port\tdir\tn_iterms"
foreach bt [$b getBTerms] {
  set n [$bt getNet]
  set c 0
  if {$n ne "NULL"} { set c [llength [$n getITerms]] }
  puts $f "[$bt getName]\t[$bt getIoType]\t$c"
}
close $f
"""

DOCKER_IMAGE = "openroad/orfs:asap7lock"


def run_remote(host: str, odb: str, tile: str, outdir: Path, mem_gb: int = 24,
               remote_root: str = "/srv/opentallas-scratch/claude/tie_audit") -> Path:
    """run the dump in docker on HOST (diagnostic probe: direct docker with a memory cap, never ot-run); pull TSVs"""
    rdir = f"{remote_root}/{tile}"
    odb_dir, odb_name = os.path.split(odb)
    script = (
        f"set -e; mkdir -p {rdir}; cat > {rdir}/tie_dump.tcl; "
        f"docker run --rm --memory={mem_gb}g --memory-swap={mem_gb}g -v {odb_dir}:/in:ro -v {rdir}:/out "
        f"-e ODB=/in/{odb_name} -e OUT=/out {DOCKER_IMAGE} bash -lc "
        + shlex.quote("source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /out/tie_dump.tcl"
                      " > /out/tie_dump.log 2>&1")
        + f"; gzip -f {rdir}/tie_sinks.tsv; ls -la {rdir}")
    subprocess.run(["ssh", host, script], input=TCL, text=True, check=True)
    outdir.mkdir(parents=True, exist_ok=True)
    for name in ("tie_sinks.tsv.gz", "ports.tsv"):
        subprocess.run(["scp", "-q", f"{host}:{rdir}/{name}", str(outdir / name)], check=True)
    return outdir


# ------------------------------------------------------------------------------------- part 2a: netlist classification
STD_RE = re.compile(r"_ASAP7_|^sky130_|^sg13g2_|^gf180")
FLOP_RE = re.compile(r"^(DFF|SDF|DHL|DLL|ASYNC|ICG)")
REPAIR_RE = re.compile(r"^(cr_|rr_)")
DATA_RE = re.compile(r"^(wd|din|d_in|data|wdata)")
ADDR_RE = re.compile(r"(addr|^a_in|^adr)")
MASK_RE = re.compile(r"(mask|bwe|wmask|ben)")
EN_RE = re.compile(r"(_ce|^ce|_en|^en|_we|^we|csb|web)")
BUS_RE = re.compile(r"^(.*?)\[(\d+)\]$")


def bus_base(name: str) -> str:
    m = BUS_RE.match(name)
    return m.group(1) if m else name


def classify_sink(tie_master: str, sink_master: str, pin: str, ninv: int, q_load: str = "-") -> tuple[str, str, int]:
    """-> (class, reason, effective constant value) of one tie-driven final sink.
    q_load (flop D sinks): master.pin of the first load of the flop output, used to tell reset relays from constant
    data registers."""
    val = (1 if "HI" in tie_master.upper() else 0) ^ (int(ninv) & 1)
    pb = bus_base(pin)
    if sink_master == "NOSINK":
        return "c", "tie_without_load", val
    if sink_master == "PORT":
        return "c", "const_output_bit", val
    if not STD_RE.search(sink_master):  # macro (SRAM etc.)
        if REPAIR_RE.match(pb):
            return "a", "macro_repair_pin", val
        if val == 1 and (MASK_RE.search(pb) or EN_RE.search(pb)):
            return "a", "macro_full_word_or_always_on", val
        if val == 0 and DATA_RE.match(pb):
            return "c", "macro_unused_data_bit", val
        if val == 0 and ADDR_RE.search(pb):
            return "c", "macro_unused_addr_bit", val
        if val == 0 and MASK_RE.search(pb):
            return "c", "macro_unused_mask_bit", val
        if val == 0 and EN_RE.search(pb):
            return "c", "macro_disabled_port", val
        return "a", "macro_other_const", val
    if FLOP_RE.match(sink_master):
        if pb in ("SETN", "RESETN", "SN", "RN", "SETB", "RESETB"):
            if val == 1:
                return "a", "flop_unused_async_pin", val
            return "c", "flop_held_in_set_or_reset", val
        if pb in ("D",):
            ql = q_load.rsplit(".", 1)[-1] if q_load not in ("-", "") else ""
            if ql in ("SETN", "RESETN", "SN", "RN") or (val == 1 and "ASR" in sink_master):
                # reset synchroniser / relay stage or a "out of reset" flag: async-reset flop, D tied 1
                return "a", "reset_relay_or_ready_flag", val
            return "c", "const_register_bit", val       # a kept register that always holds one value

        return "a", "flop_other_const", val
    return "a", "logic_const_input", val


def _open(path: Path):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)


def read_sinks(path: Path, const_outputs: Path | None = None) -> list[dict]:
    """rows {tie_master, sink_inst, sink_master, sink_pin, ninv}; legacy hand-probe layout accepted"""
    rows = []
    buf_port = {}
    if const_outputs:
        with open(const_outputs) as f:
            for ln in f:
                p = ln.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] != "port":
                    buf_port[p[1]] = p[0]
    with _open(path) as f:
        hdr = f.readline().rstrip("\n").split("\t")
        ix = {h: i for i, h in enumerate(hdr)}
        legacy = "nbuf" not in ix
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            if len(p) < len(hdr):
                continue
            r = {"tie_inst": p[ix["tie_inst"]], "tie_master": p[ix["tie_master"]], "sink_inst": p[ix["sink_inst"]],
                 "sink_master": p[ix["sink_master"]], "sink_pin": p[ix["sink_pin"]],
                 "ninv": 0 if legacy else int(p[ix["ninv"]]),
                 "q_load": p[ix["q_load"]] if "q_load" in ix else "-"}
            if legacy and r["sink_inst"] in buf_port:   # tie -> BUF -> output port (hand probe 2-hop table)
                r.update(sink_master="PORT", sink_pin=buf_port[r["sink_inst"]], sink_inst="PORT")
            rows.append(r)
    return rows


def read_ports(path: Path | None) -> list[dict]:
    if not path:
        return []
    out = []
    with open(path) as f:
        hdr = f.readline().rstrip("\n").split("\t")
        ix = {h: i for i, h in enumerate(hdr)}
        if "n_iterms" in ix:
            for ln in f:
                p = ln.rstrip("\n").split("\t")
                out.append({"port": p[ix["port"]], "dir": p[ix["dir"]], "n": int(p[ix["n_iterms"]])})
        else:  # hand-probe port_sinks layout: one row per connection, NOSINK rows
            agg = collections.OrderedDict()
            for ln in f:
                p = ln.rstrip("\n").split("\t")
                k = (p[0], p[1])
                agg.setdefault(k, 0)
                if p[4] != "NOSINK" and p[3] != "-":
                    agg[k] += 1
            out = [{"port": k[0], "dir": k[1], "n": v} for k, v in agg.items()]
    return out


def classify_netlist(rows: list[dict], ports: list[dict]) -> dict:
    cls = collections.Counter()
    reasons = collections.Counter()
    by_tie = collections.Counter()
    hist = collections.Counter()
    dead_out = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        c, why, val = classify_sink(r["tie_master"], r["sink_master"], r["sink_pin"], r["ninv"], r["q_load"])
        r["cls"], r["why"], r["val"] = c, why, val
        cls[c] += 1
        reasons[(c, why, "TIEHI" if "HI" in r["tie_master"].upper() else "TIELO")] += 1
        by_tie["TIEHI" if "HI" in r["tie_master"].upper() else "TIELO"] += 1
        hist[(r["sink_master"], bus_base(r["sink_pin"]) if r["sink_master"] != "PORT" else "<output>")] += 1
        if why == "const_output_bit":
            dead_out[bus_base(r["sink_pin"])][str(val)] += 1
    tie_cells = collections.Counter()
    seen = set()
    for r in rows:
        if r["tie_inst"] not in seen:
            seen.add(r["tie_inst"])
            tie_cells["TIEHI" if "HI" in r["tie_master"].upper() else "TIELO"] += 1
    dead_in = collections.Counter()
    for p in ports:
        if p["dir"].upper().startswith("INPUT") and p["n"] == 0:
            dead_in[bus_base(p["port"])] += 1
    return {
        "tie_cells": dict(tie_cells),
        "tie_sinks": dict(by_tie),
        "sinks_by_class": {k: cls.get(k, 0) for k in "abc"},
        "reasons": [{"class": c, "reason": w, "tie": t, "n": n} for (c, w, t), n in sorted(reasons.items())],
        "top_sinks": [{"master": m, "pin": p, "n": n} for (m, p), n in hist.most_common(15)],
        "dead_outputs": {k: dict(v) for k, v in sorted(dead_out.items())},
        "dead_output_bits": sum(sum(v.values()) for v in dead_out.values()),
        "dead_inputs": dict(sorted(dead_in.items())),
        "dead_input_bits": sum(dead_in.values()),
    }


# ----------------------------------------------------------------------------------- part 2b: RTL tie-off scan (class b)
KEYWORDS = set("""module endmodule input output inout wire reg logic assign always always_ff always_comb always_latch
initial begin end if else for while case casez casex endcase default generate endgenerate genvar function endfunction
task endtask parameter localparam integer signed unsigned return posedge negedge or and not typedef struct enum
packed interface endinterface modport import export package endpackage specify endspecify defparam real time bit
byte int shortint longint var automatic static""".split())
CELL_MOD_RE = re.compile(r"(_cell_\d+$|_ASAP7_|^ot_sram_|^fakeram|^sky130_|^sg13g2_|^\$)")
LIT_RE = re.compile(r"^(\d+)?\s*'\s*[sS]?[bBoOdDhH]\s*[0-9a-fA-FxXzZ_?]+$")
UNSIZED_FILL_RE = re.compile(r"^'[01xXzZ]$")
DEC_RE = re.compile(r"^\d+$")


def strip_comments(text: str) -> str:
    """blank // and /* */ comments and strings, keeping every newline (line numbers stay exact)"""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in text[i:j]))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append('"' + " " * max(0, j - i - 1) + '"')
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_paren(s: str, i: int, o: str = "(", c: str = ")") -> int:
    """index of the bracket closing s[i] (== o)"""
    d = 0
    for j in range(i, len(s)):
        if s[j] == o:
            d += 1
        elif s[j] == c:
            d -= 1
            if d == 0:
                return j
    return -1


def split_top(s: str, sep: str = ",") -> list[str]:
    parts, d, cur = [], 0, []
    for ch in s:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == sep and d == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def eval_int(expr: str, params: dict) -> int | None:
    e = expr.strip()
    if not e:
        return None
    e = re.sub(r"\$clog2\s*\(", "_clog2(", e)
    e = re.sub(r"(\d+)?'\s*[sS]?[dD]\s*(\d+)", r"\2", e)
    e = re.sub(r"(\d+)?'\s*[sS]?[hH]\s*([0-9a-fA-F_]+)", lambda m: str(int(m.group(2).replace("_", ""), 16)), e)
    e = re.sub(r"(\d+)?'\s*[sS]?[bB]\s*([01_]+)", lambda m: str(int(m.group(2).replace("_", ""), 2)), e)
    for _ in range(4):
        e2 = re.sub(r"\b([A-Za-z_]\w*)\b",
                    lambda m: str(params[m.group(1)]) if m.group(1) in params and params[m.group(1)] is not None
                    else m.group(1), e)
        if e2 == e:
            break
        e = e2
    if re.search(r"[A-Za-z_]", e.replace("_clog2", "")):
        return None
    e = e.replace("/", "//")
    if "?" in e:
        return None
    try:
        return int(eval(e, {"__builtins__": {}}, {"_clog2": lambda v: max(0, (int(v) - 1).bit_length())}))
    except Exception:
        return None


def dims_width(dims: str, params: dict) -> int | None:
    w = 1
    for m in re.finditer(r"\[([^\]:]+):([^\]]+)\]", dims or ""):
        a, b = eval_int(m.group(1), params), eval_int(m.group(2), params)
        if a is None or b is None:
            return None
        w *= abs(a - b) + 1
    return w


class Module:
    def __init__(self, name, file, text, start, body_start, end):
        self.name, self.file, self.text = name, file, text
        self.start, self.body_start, self.end = start, body_start, end
        self.ports: dict[str, tuple[str, int | None]] = {}
        self.params: dict[str, int | None] = {}
        self.blackbox = False

    def line(self, pos: int) -> int:
        return self.text.count("\n", 0, pos) + 1


MOD_RE = re.compile(r"(?m)^[ \t]*(?:\(\*[^)]*\*\)\s*)?(module|macromodule)\s+([A-Za-z_]\w*)")


def parse_modules(path: str, text: str | None = None) -> list[Module]:
    raw = text if text is not None else Path(path).read_text(errors="replace")
    t = strip_comments(raw)
    mods = []
    for m in MOD_RE.finditer(t):
        name = m.group(2)
        end = t.find("endmodule", m.end())
        end = len(t) if end < 0 else end
        i = m.end()
        while i < end and t[i].isspace():
            i += 1
        params = {}
        if i < end and t[i] == "#":
            j = t.index("(", i)
            k = match_paren(t, j)
            for item in split_top(t[j + 1:k]):
                pm = re.search(r"([A-Za-z_]\w*)\s*=\s*(.+)$", item.strip(), re.S)
                if pm:
                    params[pm.group(1)] = pm.group(2).strip()
            i = k + 1
            while i < end and t[i].isspace():
                i += 1
        header = ""
        if i < end and t[i] == "(":
            k = match_paren(t, i)
            header = t[i + 1:k]
            i = k + 1
        semi = t.find(";", i)
        mod = Module(name, path, t, m.start(), semi + 1, end)
        body = t[semi + 1:end]
        for pm in re.finditer(r"\b(?:parameter|localparam)\b([^;]*);", body):
            for item in split_top(pm.group(1)):
                q = re.search(r"([A-Za-z_]\w*)\s*=\s*(.+)$", item.strip(), re.S)
                if q:
                    params.setdefault(q.group(1), q.group(2).strip())
        resolved: dict[str, int | None] = {}
        for _ in range(3):
            for k2, v in params.items():
                if resolved.get(k2) is None:
                    resolved[k2] = eval_int(v, resolved)
        mod.params = resolved
        mod.blackbox = bool(re.search(r"\(\*\s*blackbox", t[max(0, m.start() - 40):m.start() + 40])) or \
            not re.search(r"\b(assign|always|always_ff|always_comb)\b|\)\s*;", body)
        cur_dir, cur_w = None, 1
        for item in split_top(header):
            s = item.strip()
            dm = re.match(r"^(input|output|inout)\b\s*((?:wire|reg|logic|var|signed|unsigned|\s)*)((?:\[[^\]]*\]\s*)*)(.*)$",
                          s, re.S)
            if dm:
                cur_dir, cur_w = dm.group(1), dims_width(dm.group(3), resolved)
                s = dm.group(4)
            nm = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\]\s*)*$", s)
            if nm and cur_dir:
                mod.ports[nm.group(1)] = (cur_dir, cur_w)
            elif nm:
                mod.ports.setdefault(nm.group(1), (None, None))
        for dm in re.finditer(r"\b(input|output|inout)\b\s*((?:wire|reg|logic|var|signed|unsigned|\s)*)((?:\[[^\]]*\]\s*)*)([^;]*);",
                              body):
            w = dims_width(dm.group(3), resolved)
            for nm in split_top(dm.group(4)):
                q = re.match(r"\s*([A-Za-z_]\w*)", nm)
                if q:
                    mod.ports[q.group(1)] = (dm.group(1), w)
        mods.append(mod)
    return mods


INST_RE = re.compile(r"(?<![\w$.`])([A-Za-z_]\w*)\s*(#\s*\()?")


def instances(mod: Module):
    """yield (child_module, inst_name, params_text, conn_text, conn_offset)"""
    t, i, end = mod.text, mod.body_start, mod.end
    while i < end:
        m = INST_RE.search(t, i, end)
        if not m:
            return
        name = m.group(1)
        i = m.end()
        if name in KEYWORDS:
            continue
        ptxt = ""
        j = m.end()
        if m.group(2):
            k = match_paren(t, j - 1)
            if k < 0:
                continue
            ptxt = t[j:k]
            j = k + 1
        im = re.compile(r"\s*([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*\(").match(t, j)
        if not im or im.group(1) in KEYWORDS:
            continue
        lp = im.end() - 1
        rp = match_paren(t, lp)
        if rp < 0 or rp > end:
            continue
        after = t[rp + 1:rp + 40].lstrip()
        if not after.startswith(";") and not after.startswith(","):
            continue
        inner = t[lp + 1:rp]
        if inner.strip() and not inner.lstrip().startswith("."):
            i = rp + 1  # positional or a function call: not checked
            continue
        yield name, im.group(1), ptxt, inner, lp + 1
        i = rp + 1


def literal_bits(expr: str, port_w: int | None, params: dict) -> tuple[int | None, bool, bool]:
    """-> (constant bits, whole expression constant, any literal). Parameters / localparams are not literals."""
    e = expr.strip()
    if e.startswith("{") and e.endswith("}") and match_paren(e, 0, "{", "}") == len(e) - 1:
        inner = e[1:-1].strip()
        rm = re.match(r"^([^{}]+?)\s*(\{.*\})$", inner, re.S)
        if rm and match_paren(rm.group(2), 0, "{", "}") == len(rm.group(2)) - 1:
            n = eval_int(rm.group(1), params)
            b, whole, anylit = literal_bits(rm.group(2), None, params)
            if anylit and whole:
                return (None if n is None or b is None else n * b), True, True
            return 0, False, anylit
        total, whole, anylit = 0, True, False
        for el in split_top(inner):
            b, w, a = literal_bits(el, None, params)
            anylit |= a
            whole &= w
            if a and b is not None and total is not None:
                total += b
            elif a:
                total = None
        return total, whole, anylit
    e2 = e[1:-1].strip() if e.startswith("(") and e.endswith(")") and match_paren(e, 0) == len(e) - 1 else e
    lm = LIT_RE.match(e2)
    if lm:
        return (int(lm.group(1)) if lm.group(1) else (port_w or 32)), True, True
    if UNSIZED_FILL_RE.match(e2) or DEC_RE.match(e2):
        return port_w, True, True
    return 0, False, False


class RtlIndex:
    def __init__(self, files: list[str], dirs: list[str]):
        self.defs: dict[str, list[Module]] = collections.defaultdict(list)
        self.explicit = set()
        for f in files:
            for mo in parse_modules(f):
                self.defs[mo.name].insert(0, mo)
                self.explicit.add(mo.name)
        self.dir_files = []
        for d in dirs:
            for root, _, fs in os.walk(d):
                self.dir_files += [os.path.join(root, x) for x in fs if x.endswith((".v", ".sv", ".svh", ".vh"))]
        self._grep_cache: dict[str, list[str]] = {}

    def find(self, name: str, near: str = "") -> Module | None:
        if name not in self.defs and name not in self._grep_cache:
            pat = re.compile(r"(?m)^[ \t]*(?:module|macromodule)\s+" + re.escape(name) + r"\b")
            hits = []
            for f in self.dir_files:
                try:
                    with open(f, errors="replace") as fh:
                        if pat.search(fh.read()):
                            hits.append(f)
                except OSError:
                    pass
            self._grep_cache[name] = hits
            for f in hits:
                for mo in parse_modules(f):
                    if mo.name == name:
                        self.defs[name].append(mo)
        cands = self.defs.get(name) or []
        if not cands:
            return None
        if name in self.explicit or len(cands) == 1:
            return cands[0]
        return max(cands, key=lambda mo: len(os.path.commonprefix([mo.file, near])))


def scan_tieoffs(files: list[str], dirs: list[str], top: str | None, repo_root: str | None = None) -> dict:
    idx = RtlIndex(files, dirs)
    if top:
        todo = [top]
    else:
        todo = [n for n in idx.explicit]
    seen, tieoffs, unresolved, ambiguous, unresolved_lits = set(), [], set(), set(), []
    while todo:
        mname = todo.pop()
        if mname in seen:
            continue
        seen.add(mname)
        mod = idx.find(mname)
        if mod is None:
            unresolved.add(mname)
            continue
        if len(idx.defs.get(mname, [])) > 1 and mname not in idx.explicit:
            ambiguous.add(mname)
        for child, inst, ptxt, conns, off in instances(mod):
            if CELL_MOD_RE.search(child):
                continue
            cm = idx.find(child, mod.file)
            if cm is None:
                unresolved.add(child)
            elif not cm.blackbox:
                todo.append(child)  # hard children (blackbox views) are checked at their ports, not descended
            cparams = dict(cm.params) if cm else {}
            for item in split_top(ptxt):
                pm = re.match(r"\s*\.\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$", item, re.S)
                if pm:
                    v = eval_int(pm.group(2), mod.params)
                    if v is not None:
                        cparams[pm.group(1)] = v
            pos = 0
            for item in split_top(conns):
                ipos = conns.find(item, pos)
                pos = ipos + len(item)
                pm = re.match(r"\s*\.\s*([A-Za-z_]\w*)\s*(?:\((.*)\))?\s*$", item, re.S)
                if not pm:
                    continue
                port, expr = pm.group(1), pm.group(2)
                d, w = cm.ports.get(port, (None, None)) if cm else ("unknown", None)
                if d not in ("input", "unknown"):
                    continue
                lineno = mod.line(off + ipos + (len(item) - len(item.lstrip())))
                fpath = os.path.relpath(mod.file, repo_root) if repo_root else mod.file
                if expr is None:
                    continue  # .port implicit name connection
                sink = tieoffs if d == "input" else unresolved_lits
                if not expr.strip():
                    if d != "input":
                        continue
                    tieoffs.append({"file": fpath, "line": lineno, "module": mod.name, "child": child, "instance": inst,
                                    "port": port, "bits": w, "port_width": w, "kind": "open",
                                    "expr": ".%s()" % port})
                    continue
                bits, whole, anylit = literal_bits(expr, w, mod.params)
                if anylit:
                    sink.append({"file": fpath, "line": lineno, "module": mod.name, "child": child, "instance": inst,
                                    "port": port, "bits": bits, "port_width": w,
                                    "kind": "whole" if whole else "partial",
                                    "expr": re.sub(r"\s+", " ", expr.strip())[:160]})
    return {"modules_scanned": len(seen), "tieoffs": tieoffs, "tieoff_bits": sum(t["bits"] or 0 for t in tieoffs),
            "unresolved_modules": sorted(unresolved), "ambiguous_modules": sorted(ambiguous),
            # literals on ports of children without a definition (direction unknown): give their _bb.v to resolve
            "unresolved_literals": unresolved_lits}


# ------------------------------------------------------------------------------------------------------------- report
def build_report(tile: str, net: dict, rtl: dict | None, source: dict) -> dict:
    counts = dict(net["sinks_by_class"])
    if rtl is not None:
        counts["b"] = len(rtl["tieoffs"])
    return {
        "schema": SCHEMA, "tile": tile, "source": source,
        "tie_cells": net["tie_cells"], "tie_sinks": net["tie_sinks"],
        "counts": {"a_sinks": counts.get("a", 0), "b_tieoffs": counts.get("b", 0) if rtl is not None else None,
                   "b_tieoff_bits": rtl["tieoff_bits"] if rtl is not None else None,
                   "c_sinks": counts.get("c", 0), "b_netlist_sinks": net["sinks_by_class"].get("b", 0)},
        "reasons": net["reasons"], "top_sinks": net["top_sinks"],
        "tieoffs": rtl["tieoffs"] if rtl is not None else None,
        "rtl_scan": {k: v for k, v in (rtl or {}).items() if k != "tieoffs"} or None,
        "dead_outputs": net["dead_outputs"], "dead_output_bits": net["dead_output_bits"],
        "dead_inputs": net["dead_inputs"], "dead_input_bits": net["dead_input_bits"],
    }


def text_summary(rep: dict) -> str:
    c = rep["counts"]
    tc = rep["tie_cells"]
    L = [f"tie_audit {rep['tile']}: TIEHI {tc.get('TIEHI', 0):,} / TIELO {tc.get('TIELO', 0):,} cells; sinks "
         f"a {c['a_sinks']:,}  c {c['c_sinks']:,}  b(RTL tie-offs) "
         + ("not scanned" if c["b_tieoffs"] is None else f"{c['b_tieoffs']} ({c['b_tieoff_bits'] or 0} bits)")]
    for r in rep["reasons"]:
        L.append(f"  {r['class']} {r['tie']:5s} {r['n']:7,}  {r['reason']}")
    L.append("  top sinks: " + ", ".join(f"{t['master']}.{t['pin']} {t['n']:,}" for t in rep["top_sinks"][:6]))
    if rep["dead_outputs"]:
        L.append(f"  dead output bits {rep['dead_output_bits']:,} on {len(rep['dead_outputs'])} ports: " + ", ".join(
            f"{k}({sum(v.values())})" for k, v in sorted(rep['dead_outputs'].items(), key=lambda kv: -sum(kv[1].values()))[:8]))
    if rep["dead_inputs"]:
        L.append(f"  input bits without sink {rep['dead_input_bits']:,}: " + ", ".join(
            f"{k}({v})" for k, v in sorted(rep["dead_inputs"].items(), key=lambda kv: -kv[1])[:8]))
    for t in rep["tieoffs"] or []:
        L.append(f"  TIE-OFF {t['file']}:{t['line']} {t['child']}.{t['port']} ({t['instance']} in {t['module']}) "
                 f"{'?' if t['bits'] is None else t['bits']} bits [{t['kind']}] {t['expr']}")
    for t in (rep.get("rtl_scan") or {}).get("unresolved_literals") or []:
        L.append(f"  literal on undefined child {t['file']}:{t['line']} {t['child']}.{t['port']} ({t['instance']}) "
                 f"{t['expr']}")
    if rep.get("rtl_scan") and rep["rtl_scan"].get("unresolved_modules"):
        L.append("  unresolved modules (not scanned): " + ", ".join(rep["rtl_scan"]["unresolved_modules"][:10]))
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tcl", help="print the OpenROAD dump script (env ODB, OUT)")
    r = sub.add_parser("remote", help="run the dump in docker on a fleet host and pull the TSVs")
    r.add_argument("--host", required=True)
    r.add_argument("--odb", required=True)
    r.add_argument("--tile", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--mem-gb", type=int, default=24)
    c = sub.add_parser("classify")
    c.add_argument("--tile", required=True)
    c.add_argument("--sinks", required=True)
    c.add_argument("--ports")
    c.add_argument("--const-outputs", help="legacy hand-probe table port<TAB>buffer (tie->BUF->port)")
    c.add_argument("--rtl", nargs="*", default=[], help="RTL files (definitions here win)")
    c.add_argument("--rtl-dir", nargs="*", default=[], help="search dirs for other module definitions")
    c.add_argument("--top", help="scan only the hierarchy below this module")
    c.add_argument("--repo-root", help="report RTL paths relative to this root")
    c.add_argument("--source", default="", help="free text: which ODB / revision")
    c.add_argument("--json")
    c.add_argument("--txt")
    a = ap.parse_args(argv)
    if a.cmd == "tcl":
        sys.stdout.write(TCL)
        return 0
    if a.cmd == "remote":
        run_remote(a.host, a.odb, a.tile, Path(a.out), a.mem_gb)
        return 0
    rows = read_sinks(Path(a.sinks), Path(a.const_outputs) if a.const_outputs else None)
    net = classify_netlist(rows, read_ports(Path(a.ports) if a.ports else None))
    rtl = scan_tieoffs(a.rtl, a.rtl_dir, a.top, a.repo_root) if (a.rtl or a.rtl_dir) else None
    rep = build_report(a.tile, net, rtl, {"odb": a.source, "rtl_top": a.top, "rtl": a.rtl})
    txt = text_summary(rep)
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    if a.txt:
        Path(a.txt).write_text(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
