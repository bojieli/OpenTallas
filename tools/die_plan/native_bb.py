#!/usr/bin/env python3
"""Keep native macro metadata parameters through ORFS classic canonicalization.

Liberty blackboxes do not describe content-only VIAMAP/INSTANCE parameters.
Eager native headers replace their port models; deferred logic still specializes
only at actual instance parameters. This does not change hard macro timing.
"""
from pathlib import Path
import argparse
import json
import re
import sys

OLD = "      read_verilog -defer -sv {*}$vIdirsArgs $file"
NEW = """      # OT_NATIVE_BB_METADATA: Liberty omits content-only macro parameters.
      if {[regexp {_bb[.](v|sv)$} $file]} {
        read_verilog -lib -overwrite -sv {*}$vIdirsArgs $file
      } else {
        read_verilog -defer -sv {*}$vIdirsArgs $file
      }"""

def patch(path):
    path = Path(path)
    text = path.read_text()
    if NEW in text:
        return
    if text.count(OLD) != 1:
        raise ValueError("unrecognized synth_preamble.tcl; refusing macro frontend patch")
    path.write_text(text.replace(OLD, NEW))

PHYS_OLD = "write_verilog -nohex -nodec $::env(RESULTS_DIR)/1_2_yosys.v"
PHYS_NEW = """# OT_NATIVE_ROM_PHYSICAL_METADATA: retain all content metadata before serialization.
write_json $::env(RESULTS_DIR)/1_2_yosys_native_metadata.json
# OpenSTA's physical Verilog reader cannot parse string parameter overrides.
# Only ROM content labels are removed; all geometry/numeric parameters remain.
setparam -unset VIAMAP -unset INSTANCE t:ot_rom_*
""" + PHYS_OLD

# STA-0171 class (DIE-QC-59S 11-01): OpenSTA's Verilog reader rejects EVERY '#(...)' instance override, numeric too
# (pinned asap7lock probe: 'ch #(.MIF(32'sb0...)) u0' -> 'Error: 171 ... syntax error').  A signed child kept as a
# black box by its eager *_bb.v metadata header (OT_NATIVE_BB_METADATA) keeps the parent's override in yosys, e.g.
# qfd_dv_s8x_vmr #(.MIF(0)).  After the metadata JSON above, every override on a header master is removed ONLY when it
# equals that header's declared default (the signed parameter identity); any other value stops synth.  The golden RTL,
# the metadata JSON and the LEC RTL side are untouched; kits without *_bb.v headers skip the block in Tcl.
SIGNED_PARAM_TCL = """# OT_SIGNED_PARAM_SERIALIZE (STA-0171): strip only verified header-default overrides on signed black boxes.
set ot_bbh {}
foreach ot_f $::env(VERILOG_FILES) { if {[regexp {_bb[.](v|sv)$} $ot_f]} { lappend ot_bbh $ot_f } }
if {[llength $ot_bbh]} {
  set ot_sp $::env(RESULTS_DIR)/1_2_yosys_signed_params
  set ot_types [exec python3 -I @SELF@ types {*}$ot_bbh]
  set ot_fh [open $ot_sp.tsv w]
  foreach {ot_t ot_ps} $ot_types {
    yosys select -write $ot_sp.sel t:$ot_t
    set ot_in [open $ot_sp.sel]; set ot_cells [split [string trim [read $ot_in]] "\n"]; close $ot_in
    foreach ot_c $ot_cells {
      if {$ot_c eq ""} { continue }
      set ot_i [string first / $ot_c]
      set ot_m [string range $ot_c 0 [expr {$ot_i - 1}]]; set ot_n [string range $ot_c [expr {$ot_i + 1}] end]
      foreach ot_p $ot_ps {
        set ot_has 1
        if {[catch {rtlil::get_param $ot_m $ot_n $ot_p} ot_v]} {
          if {$ot_v ne "parameter missing"} { error "OT_SIGNED_PARAM_SERIALIZE: cannot read $ot_p of $ot_c: $ot_v" }
          set ot_has 0; set ot_v ""
        }
        puts $ot_fh [join [list $ot_t $ot_m $ot_n $ot_p $ot_has $ot_v] "\t"]
      }
    }
  }
  close $ot_fh
  file delete -force $ot_sp.sel
  exec python3 -I @SELF@ plan $ot_sp.tsv $ot_sp.ys $ot_sp.json {*}$ot_bbh >@ stdout 2>@ stderr
  yosys script $ot_sp.ys
}
"""
SIGNED_PARAM_MARK = "# OT_SIGNED_PARAM_SERIALIZE"


def phys_new(self_path=None):
    self_path = str(Path(self_path or __file__).resolve())
    return PHYS_NEW.replace(PHYS_OLD, SIGNED_PARAM_TCL.replace("@SELF@", self_path) + PHYS_OLD)


def patch_physical(path, self_path=None):
    path = Path(path)
    text = path.read_text()
    if SIGNED_PARAM_MARK in text:
        return
    if text.count(PHYS_OLD) != 1:
        raise ValueError("unrecognized synth.tcl; refusing physical metadata patch")
    path.write_text(text.replace(PHYS_OLD, phys_new(self_path)))


# ---- signed-header parameter defaults (the *_bb.v metadata headers read eagerly by OT_NATIVE_BB_METADATA) ----
_LIT = re.compile(r"^(?:(\d+)\s*)?'(s?)([bodh])\s*([0-9a-fA-F_xXzZ?]+)$")


def parse_value(text):
    """Header default -> ('int', value) | ('str', text) | ('unknown', text)."""
    t = text.strip()
    if re.fullmatch(r"[+-]?\d[\d_]*", t):
        return ("int", int(t.replace("_", "")))
    if re.fullmatch(r'"[^"\\]*"', t):
        return ("str", t[1:-1])
    m = _LIT.match(t.replace(" ", ""))
    if m:
        width, signed, base, digits = m.groups()
        digits = digits.replace("_", "")
        if re.search(r"[xXzZ?]", digits):
            return ("unknown", t)
        v = int(digits, {"b": 2, "o": 8, "d": 10, "h": 16}[base])
        if width and signed and v >> (int(width) - 1):
            v -= 1 << int(width)
        return ("int", v)
    return ("unknown", t)


def _split_top(text):
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _decls(items, params):
    for it in items:
        it = re.sub(r"^\s*(parameter|localparam)\b", "", it).strip()
        if "=" not in it:
            continue
        lhs, rhs = it.split("=", 1)
        name = re.findall(r"[A-Za-z_]\w*", lhs)
        if name:
            params[name[-1]] = parse_value(rhs)


def header_params(text):
    """{module: {param: (kind, value)}} of every module in a *_bb.v header (port-list and body parameters)."""
    text = re.sub(r"/\*.*?\*/", " ", re.sub(r"//[^\n]*", " ", text), flags=re.S)
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    mods = {}
    for m in re.finditer(r"\bmodule\s+([A-Za-z_]\w*)\s*(.*?)\bendmodule\b", text, flags=re.S):
        name, body = m.group(1), m.group(2)
        params = {}
        if body.lstrip().startswith("#"):
            i = body.index("(", body.index("#"))
            depth, j = 0, i
            while j < len(body):
                depth += {"(": 1, ")": -1}.get(body[j], 0)
                if depth == 0:
                    break
                j += 1
            _decls(_split_top(body[i + 1:j]), params)
            body = body[j + 1:]
        for st in re.finditer(r"\bparameter\b([^;]*);", body):
            _decls(_split_top(st.group(1)), params)
        mods[name] = params
    return mods


def headers_params(paths):
    """Never raises on a header it cannot read (canary safety: a kit without overrides must not change); an
    unparsable header contributes no masters, and a parameter declared with different defaults in two headers becomes
    'unknown', so only an actual override of it stops synth."""
    out = {}
    for p in paths:
        try:
            got = header_params(Path(p).read_text(errors="replace"))
        except (OSError, ValueError, IndexError):
            continue
        for mod, ps in got.items():
            if mod in out:
                for k in set(out[mod]) | set(ps):
                    if out[mod].get(k) != ps.get(k):
                        out[mod][k] = ("unknown", "conflicting *_bb.v defaults")
            else:
                out[mod] = dict(ps)
    return out


def numeric_types(paths):
    """Tcl list 'type {params}' of header masters with numeric parameter defaults (the only overrides touched)."""
    hp = headers_params(paths)
    parts = []
    for mod in sorted(hp):
        ps = sorted(p for p, (k, _) in hp[mod].items() if k != "str")
        if ps:
            parts.append(f"{mod} {{{' '.join(ps)}}}")
    return " ".join(parts)


def bits_equal(bits, default):
    """yosys parameter bit string (MSB first) == header integer default (two's complement at the cell width)."""
    if not bits or re.search(r"[^01]", bits):
        return False
    w = len(bits)
    if default < -(1 << (w - 1)) or default >= (1 << w):
        return False
    return int(bits, 2) == default % (1 << w)


def plan(rows, hp):
    """rows: (type, module, cell, param, has, bits).  -> (ys lines, report, errors)."""
    errors, strip = [], {}
    for t, mod, cell, p, has, bits in rows:
        if has != "1":
            continue
        kind, dv = hp.get(t, {}).get(p, ("unknown", None))
        if kind != "int":
            errors.append(f"{t} {mod}/{cell}: .{p}({bits}) has no verifiable numeric header default ({kind} {dv})")
        elif not bits_equal(bits, dv):
            errors.append(f"{t} {mod}/{cell}: .{p}({bits}) != signed header default {dv}")
        else:
            strip.setdefault((t, p), []).append(f"{mod}/{cell}")
    ys = [f"setparam -unset {p} t:{t}" for (t, p) in sorted(strip)]
    report = {"schema": "opentallas.signed-param-serialize.v1", "errors": errors,
              "stripped": [{"type": t, "param": p, "default": hp[t][p][1], "cells": sorted(c)}
                           for (t, p), c in sorted(strip.items())]}
    return ys, report, errors


def main_plan(tsv, ys_out, json_out, headers):
    hp = headers_params(headers)
    rows = [ln.split("\t") for ln in Path(tsv).read_text().splitlines() if ln.strip()]
    rows = [r + [""] * (6 - len(r)) for r in rows]
    ys, report, errors = plan(rows, hp)
    report["headers"] = [str(h) for h in headers]
    Path(json_out).write_text(json.dumps(report, indent=1) + "\n")
    if errors:
        for e in errors:
            print("OT_SIGNED_PARAM_SERIALIZE ERROR: " + e, file=sys.stderr)
        return 2
    Path(ys_out).write_text("".join(ln + "\n" for ln in ys))
    n = sum(len(s["cells"]) for s in report["stripped"])
    print(f"OT_SIGNED_PARAM_SERIALIZE: {n} default override(s) removed on "
          f"{len({s['type'] for s in report['stripped']})} signed header master(s); non-default = hard error")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "types":
        print(numeric_types(sys.argv[2:]))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "plan":
        sys.exit(main_plan(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preamble", type=Path)
    parser.add_argument("--physical-synth", type=Path)
    args = parser.parse_args()
    patch(args.preamble)
    if args.physical_synth:
        patch_physical(args.physical_synth)
