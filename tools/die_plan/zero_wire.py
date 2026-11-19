#!/usr/bin/env python3
"""CBC rule 3 (COORD 11-19, amends r713): zero-wire logic delay per endpoint, not level count.

Level count does not predict closure (hd_ctl signed at 23 levels; tt_ctlm at 24 used 820 of its 833 ps at zero wire).  The
rule is the FABLE-FIX-S81-GLUE method: OpenSTA on the synthesized ASAP7 netlist with RVT TT NLDM cells, NO wire parasitics
(pin loads only), every net bounded to FANOUT_BOUND cell sinks by a buffer tree first (as placement repair would), ideal
clock.  logic(endpoint) = clk->Q + cells + setup = period - slack.  An endpoint over cbc_rules.LOGIC_PS_MAX (600 ps, leaves
~230 ps for wire + clock) is flagged.  13 levels (DEPTH_LEVELS_MAX) stays only as the cheap pre-screen that picks the
netlists worth timing.

The STA runs with the clock period set to LOGIC_PS_MAX, so OpenSTA's own violation count is the number of endpoints over
the limit and logic = LOGIC_PS_MAX - slack for every reported endpoint.

usage: zero_wire.py NETLIST.v OUT_DIR [--type T] [--top MODULE] [--image IMG] [--no-run] [--report-ends N]
  writes OUT_DIR/zw.v (fanout-bounded copy), OUT_DIR/zw.tcl, runs `sta` in IMG (docker), parses -> OUT_DIR/zw.json
  {type, top, limit_ps, endpoints_over, worst_ps, ends: [[endpoint, logic_ps], ...], buffers_added, nets_bounded}
Row writer / estimator only: nothing here holds a build.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cbc_rules as RULES  # noqa: E402

IMAGE = "opentallas/orfs:asap7lock-grtoff"
BUF = "BUFx4_ASAP7_75t_R"
STD = re.compile(r"_ASAP7_75t_[A-Z]+$")
# ASAP7 standard-cell outputs: Y (logic), Q / QN (flops, latches), CON / SN (full / half adders), GCLK (ICG)
OUT_PINS = {"Y", "Q", "QN", "CON", "SN", "GCLK"}
CELL_HDR = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_$]*)\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\($")
PIN_LINE = re.compile(r"^(\s*)\.([A-Za-z_][A-Za-z0-9_]*)\((.*)\)(,?)\s*$")
MOD_HDR = re.compile(r"^\s*module\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)")
INST_ANY = re.compile(r"^\s*(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(")
KEYWORDS = {"module", "input", "output", "inout", "wire", "reg", "assign", "endmodule", "always", "if", "else", "begin", "end"}


def bound_fanout(text, bound=RULES.FANOUT_BOUND, buf=BUF, strip=True):
    """-> (text, stats): every net with more than `bound` standard-cell input sinks inside one module gets a buffer tree
    (groups of `bound` sinks per buffer, recursively), so no driver sees more than `bound` cell loads.  Sinks that are not
    standard-cell pins (submodule ports, assigns, module outputs) stay on the original net."""
    lines = text.split("\n")
    out, i, stats = [], 0, dict(nets_bounded=0, buffers_added=0, **({"buffers_removed": 0} if strip else {}))
    while i < len(lines):
        m = MOD_HDR.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < len(lines) and not re.match(r"^\s*endmodule\b", lines[j]):
            j += 1
        out += _bound_module(lines[i:j], bound, buf, stats, strip)
        if j < len(lines):
            out.append(lines[j])
        i = j + 1
    return "\n".join(out), stats


BUF_CELL = re.compile(r"^(BUFx\w+|HB\dx\w+)_ASAP7_75t_[A-Z]+$")
PORT_DECL = re.compile(r"^\s*(input|output|inout)\b[^;]*?(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*;")


def _fmt(net):
    return net + " " if net.startswith("\\") else net          # an escaped identifier ends at white space


def _base(e):
    return re.sub(r"\s*\[[^\]]*\]\s*$", "", e.strip()) if not e.strip().startswith("\\") else e.strip().split(" ")[0]


def _cells(L):
    """[(cell, inst, header line, {pin: (line, expr)}, end line)] of the instance blocks of one module"""
    out, cur = [], None
    for k, ln in enumerate(L):
        h = CELL_HDR.match(ln)
        if h and h.group(2) not in KEYWORDS:
            cur = [h.group(2), h.group(3), k, {}, None]
            continue
        if cur is not None:
            p = PIN_LINE.match(ln)
            if p:
                cur[3][p.group(2)] = (k, p.group(3).strip())
                continue
            if ln.strip().startswith(");"):
                cur[4] = k
                out.append(tuple(cur))
                cur = None
    return out


def _strip_buffers(L, stats):
    """the flow removes the synthesis buffers before placement (ORFS remove_buffers) and re-buffers by load: drop every
    standard buffer whose output is no module port and is read only as a whole pin expression, its readers move to its
    input net"""
    ports = {m.group(2) for m in (PORT_DECL.match(ln) for ln in L) if m}
    for ln in L:
        m = re.match(r"^\s*(input|output|inout)\b(.*);", ln)
        if m:
            ports |= {x.strip().split()[-1] for x in m.group(2).split(",") if x.strip()}
    cells = _cells(L)
    whole = defaultdict(int)
    for _c, _i, _h, pins, _e in cells:
        for _p, (_k, e) in pins.items():
            whole[e] += 1
    text = "\n".join(ln for ln in L if not re.match(r"^\s*(wire|reg|input|output|inout)\b", ln))   # uses, not declarations
    alias, drop = {}, set()
    for c, _i, h, pins, e in cells:
        if not BUF_CELL.match(c) or "A" not in pins or "Y" not in pins:
            continue
        a, y = pins["A"][1], pins["Y"][1]
        if not a or not y or re.match(r"^\d+'", a) or _base(y) in ports or y.startswith("{") or a.startswith("{"):
            continue
        n_txt = text.count(y) if y.startswith("\\") else len(re.findall(r"(?<![\w$\\.])" + re.escape(y) + r"(?![\w$\[])", text))
        if n_txt != whole[y]:
            continue                                          # read inside a concatenation / assign: keep the buffer
        alias[y] = a
        drop.update(range(h, e + 1))
    def res(x, d=0):
        return res(alias[x], d + 1) if x in alias and d < 64 else x
    out = []
    for k, ln in enumerate(L):
        if k in drop:
            continue
        p = PIN_LINE.match(ln)
        if p and p.group(3).strip() in alias:
            ln = f"{p.group(1)}.{p.group(2)}({_fmt(res(p.group(3).strip()))}){p.group(4)}"
        out.append(ln)
    stats["buffers_removed"] = stats.get("buffers_removed", 0) + len(alias)
    return out


def _bound_module(L, bound, buf, stats, strip=True):
    if strip:
        L = _strip_buffers(L, stats)
    sinks = defaultdict(list)          # net expr -> [line index of a std-cell input pin reading it]
    cell = None
    for k, ln in enumerate(L):
        h = CELL_HDR.match(ln)
        if h and h.group(2) not in KEYWORDS:
            cell = h.group(2)
            continue
        p = PIN_LINE.match(ln)
        if p and cell:
            if STD.search(cell) and p.group(2) not in OUT_PINS:
                e = p.group(3).strip()
                if e and not re.match(r"^\d+'", e) and not e.startswith("{"):
                    sinks[e].append(k)
            continue
        if ln.strip().startswith(");"):
            cell = None
    edits, decl, bufs, src, n = {}, [], {}, {}, [0]
    for net, ks in sinks.items():
        if len(ks) <= bound:
            continue
        stats["nets_bounded"] += 1
        items = [("pin", k) for k in ks]
        while len(items) > bound:
            nxt = []
            for g in range(0, len(items), bound):
                n[0] += 1
                b = f"zwb_{n[0]}"
                w = f"{b}_y"
                decl.append(f"  wire {w};")
                bufs[b] = w
                for kind, x in items[g:g + bound]:
                    if kind == "pin":
                        m = PIN_LINE.match(L[x])
                        edits[x] = f"{m.group(1)}.{m.group(2)}({w}){m.group(4)}"
                    else:
                        src[x] = w
                nxt.append(("buf", b))
            items = nxt
        for kind, x in items:
            if kind == "buf":
                src[x] = _fmt(net)
    stats["buffers_added"] += len(bufs)
    body = [edits.get(k, ln) for k, ln in enumerate(L)]
    return body + decl + [f"  {buf} {b} (.A({src[b]}), .Y({w}));" for b, w in bufs.items()]


def top_module(text):
    mods = [m.group(1) for m in (MOD_HDR.match(ln) for ln in text.split("\n")) if m]
    used = {m.group(1) for m in (INST_ANY.match(ln) for ln in text.split("\n")) if m and m.group(1) in set(mods)}
    tops = [m for m in mods if m not in used]
    return tops[-1] if tops else (mods[-1] if mods else None)


def sta_tcl(netlist, top, limit_ps, n_ends):
    return f"""foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] {{ read_liberty $f }}
read_verilog {netlist}
link_design {top}
set cks [get_ports -quiet {{clk ck clk_* ck_*}}]
create_clock -name zw -period {limit_ps} $cks
set sta_recovery_removal_checks_enabled 0
set ins {{}}
foreach p [all_inputs] {{ if {{![regexp {{^(clk|ck)(_.*)?$}} [get_full_name $p]]}} {{ lappend ins $p }} }}
if {{[llength $ins]}} {{ set_input_delay 0 -clock zw $ins }}
if {{[llength [all_outputs]]}} {{ set_output_delay 0 -clock zw [all_outputs] }}
puts "ZW WNS [sta::time_sta_ui [sta::worst_slack_cmd max]] NV [sta::endpoint_violation_count max]"
report_checks -path_delay max -digits 1 -format end -group_path_count {n_ends} -endpoint_path_count 1 -slack_max 0
report_checks -path_delay max -digits 1 -format full -group_path_count 1
exit
"""


END_ROW = re.compile(r"^(\S+)\s+\(\S+\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\(VIOLATED\)")
END_ROW2 = re.compile(r"^(\S+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\(VIOLATED\)")


def parse(log, limit_ps):
    m = re.search(r"^ZW WNS (\S+) NV (\d+)", log, re.M)
    if not m:
        raise ValueError("no ZW line in the STA log")
    wns, nv = float(m.group(1)), int(m.group(2))
    ends = []
    for ln in log.split("\n"):
        r = END_ROW.match(ln.strip()) or END_ROW2.match(ln.strip())
        if r:
            ends.append([r.group(1), round(limit_ps - float(r.group(4)), 1)])
    return dict(endpoints_over=nv, worst_ps=round(limit_ps - wns, 1), ends=ends)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("netlist")
    ap.add_argument("out")
    ap.add_argument("--type")
    ap.add_argument("--top")
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--report-ends", type=int, default=200)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    text = Path(a.netlist).read_text()
    top = a.top or top_module(text)
    zw, st = bound_fanout(text)
    (out / "zw.v").write_text(zw)
    lim = RULES.LOGIC_PS_MAX
    (out / "zw.tcl").write_text(sta_tcl("/zw/zw.v", top, lim, a.report_ends))
    rec = dict(type=a.type, netlist=a.netlist, top=top, limit_ps=lim, fanout_bound=RULES.FANOUT_BOUND, **st)
    if not a.no_run:
        cmd = ["docker", "run", "--rm", "-v", f"{out.resolve()}:/zw", a.image, "bash", "-lc",
               "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sta -no_init -exit /zw/zw.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out / "sta.log").write_text(p.stdout + p.stderr)
        try:
            rec.update(parse(p.stdout, lim))
        except ValueError as exc:
            rec["error"] = f"{exc} (rc {p.returncode}); see sta.log"
    (out / "zw.json").write_text(json.dumps(rec, indent=1))
    print(f"ZW {a.type or top}: " + (rec.get("error") or f"{rec['endpoints_over']} endpoints over {lim:.0f} ps, worst "
                                      f"{rec['worst_ps']} ps; {st['nets_bounded']} nets bounded, {st['buffers_added']} buffers"))
    return 0 if "error" not in rec else 1


if __name__ == "__main__":
    sys.exit(main())
