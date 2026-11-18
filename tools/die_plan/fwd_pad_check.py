"""HEAD-DIE-R 11-17 (COORD, FABLE-PLAN-HEAD-NF15D2 fwdscan): subtree-balance delay pads on forwarded-clock outputs.

subtree_balance.tcl (OT_STB) before 47a7685132a measured a clock branch that ends only in an output port (a forwarded
clock fclk_out_*: no flop sink in the type) as early and padded it to the round cap, 12 BUFx4 per node x 8 rounds: the
signed hd_st_n3_turn view carried 96 delaybuf_otstb_* on each of fclk_out_u1_o / fclk_out_d1_o (~2.1 ns), which made
the die seam nst3_turn->nst4/u1_i hold -2023 ps TT (pads bypassed: +181 TT / +132 FF).  The type STA cannot see it:
the forwarded clock is a generated clock on the port, so its own outputs stay timed.

check(text) walks every fclk_out* output port of the routed netlist back through its single-input drivers (buffers,
inverters, assigns) to the clock root and counts delaybuf_otstb_* cells on that path.  A port with more than
MAX_PADS (env OT_FWD_PAD_MAX, default 10) pads FAILs the sign-off check 'fwd_pads'.

CLI: fwd_pad_check.py NETLIST.v [...] [--max N]   -> one line per netlist, exit 1 when any FAILs."""
import os
import re
import sys

PAD_PREFIX = "delaybuf_otstb_"
PORT_RE = re.compile(r"^fclk_out")
OUT_PINS = ("Y", "Q", "QN", "Z", "ZN", "CON", "SN", "GCLK")
IN_PINS = ("A", "I", "CLK")
_INST = re.compile(r"^\s*(\\?[\w$]+)\s+(\\\S+|[\w$\[\].]+)\s*\((.*?)\)\s*;", re.S | re.M)
_PIN = re.compile(r"\.(\w+)\s*\(\s*([^()]*?)\s*\)")
_ASSIGN = re.compile(r"^\s*assign\s+(\S+)\s*=\s*([^;]+?)\s*;", re.M)
_OUTPUT = re.compile(r"^\s*output\s+(?:wire\s+)?(?:\[[^\]]*\]\s*)?([^;]+);", re.M)
_KEYWORDS = {"module", "input", "output", "inout", "wire", "assign", "endmodule", "reg"}


def max_pads():
    try:
        return int(os.environ.get("OT_FWD_PAD_MAX", "10"))
    except ValueError:
        return 10


def _ports(text):
    out = []
    for m in _OUTPUT.finditer(text):
        for n in m.group(1).split(","):
            n = n.strip()
            if n and PORT_RE.match(n) and n not in out:
                out.append(n)
    # ANSI headers: "output fclk_out_x," inside the module port list
    for m in re.finditer(r"\boutput\s+(?:wire\s+)?(fclk_out\w*)", text):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def check(text, limit=None):
    """-> dict(verdict PASS|FAIL|NOT RUN, max_pads, limit, ports={port: dict(pads, depth, root)}, failing=[ports])"""
    limit = max_pads() if limit is None else limit
    ports = _ports(text)
    if not ports:
        return dict(verdict="PASS", limit=limit, max_pads=0, ports={}, failing=[], note="no fclk_out port")
    drv = {}
    for m in _INST.finditer(text):
        cell, name, body = m.groups()
        if cell in _KEYWORDS:
            continue
        pins = {a: b for a, b in _PIN.findall(body)}
        for a, b in pins.items():
            if a in OUT_PINS:
                drv[b] = (cell, name, pins)
    assigns = {a: b for a, b in _ASSIGN.findall(text)}
    rep = {}
    for p in ports:
        net, pads, depth, seen = p, 0, 0, set()
        while net not in seen and depth < 100000:
            seen.add(net)
            if net in assigns:
                net = assigns[net]
                continue
            if net not in drv:
                break
            cell, name, pins = drv[net]
            nxt = next((pins[k] for k in IN_PINS if k in pins), None)
            ins = [k for k in pins if k not in OUT_PINS]
            if nxt is None or len(ins) != 1:          # a flop / gate with more than one input: the clock root
                break
            depth += 1
            if name.lstrip("\\").startswith(PAD_PREFIX):
                pads += 1
            net = nxt
        rep[p] = dict(pads=pads, depth=depth, root=net)
    failing = sorted(p for p, r in rep.items() if r["pads"] > limit)
    return dict(verdict="FAIL" if failing else "PASS", limit=limit, max_pads=max(r["pads"] for r in rep.values()),
                ports=rep, failing=failing)


def main(argv):
    args, limit = [], None
    i = 0
    while i < len(argv):
        if argv[i] == "--max":
            limit = int(argv[i + 1])
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if not args:
        print(__doc__)
        return 2
    bad = 0
    for f in args:
        with open(f, errors="replace") as fh:
            r = check(fh.read(), limit)
        bad += r["verdict"] == "FAIL"
        worst = ", ".join(f"{p}={r['ports'][p]['pads']}" for p in r["failing"]) or "-"
        print(f"{r['verdict']} {f} fclk_out={len(r['ports'])} max_pads={r['max_pads']} limit={r['limit']} failing {worst}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
