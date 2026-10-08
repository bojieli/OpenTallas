#!/usr/bin/env python3
"""Per-link source-synchronous (forwarded-clock) budget for station blocks (setup-triage 2026-10-07).

A forwarded-clock link: data and its forwarded clock leave the sender together and the receiver captures with the
forwarded clock.  With P = launch-to-capture edge distance of the link (from the clocks' waveforms: half cycle for the
inverted ot_fwd_link_stage, full cycle otherwise), the setup equation is
    S (sender data-pin offset vs forwarded-clock pin) + M (data/clock wire mismatch on the link) + R (receiver
    pin->flop minus forwarded-clock pin->flop, + setup) + unc 60 <= P
so the consistent split gives BOTH sides an external delay of (P - 60 + M) / 2 against the forwarded clock (S = R).
Common-clock (vclk) ports of the same block keep the common-clock consistent split: external T - 60 - 254.7.
Usage: srcsync.py split IN.sdc PMAP.json OUT.sdc   (PMAP: {clock: P_ps} measured by pass 1)
       srcsync.py reps IN.sdc                     (prints clock -> representative port, direction)
"""
import json, re, sys
M = 25.0; UNC = 60.0
LINE = re.compile(r"^(set_(input|output)_delay)\s+(.*)$")
def parse(line):
    m = LINE.match(line.strip())
    if not m: return None
    toks = m[3]
    clk = re.search(r"-clock\s+(?:\[get_clocks \{?)?([^\s\]\}]+)", toks)
    val = re.search(r"(?:^|\s)(-?[\d.]+)(?=\s)", " " + toks)
    ports = re.search(r"\[get_ports \{([^}]*)\}\]", toks) or re.search(r"\[get_ports (\S+?)\]", toks)
    is_min = "-min" in toks.split()
    return dict(kind=m[2], clock=clk[1] if clk else None, value=float(val[1]) if val else None, ports=ports[1].split() if ports else [],
                is_min=is_min, fall="-clock_fall" in toks)
COMMON = re.compile(r"^(ck|clk|clock|core_clk|clk_sm|hbm_clk|ref_clk|wclk|rclk)(\[0\])?$")
def clocks(sdc):
    """forwarded port clocks {name: port} and whether a common port clock exists"""
    fwd, common = {}, False
    for l in open(sdc):
        m = re.match(r"create_clock -name (\S+) .*\[get_ports (?:\{([^}]*)\}|(\S+?))\]", l.strip())
        if m:
            port = (m[2] or m[3]).strip()
            if COMMON.match(port): common = True
            else: fwd[m[1]] = port
    return fwd, common
def retarget(sdc, dst, fo_port):
    """S81-style stations: every IO line references vclk although the block has only a forwarded port clock.
    Re-reference inputs to the forwarded clock and outputs to an inverted generated clock on the forwarded-clock
    output port (ot_fwd_link_stage: capture on the falling edge, fclk_o = ~fclk_i)."""
    fwd, common = clocks(sdc)
    if common or len(fwd) != 1 or not fo_port: return False
    (fc, fp), = fwd.items()
    o = []
    for l in open(sdc):
        o.append(l)
        if l.startswith(f"create_clock -name {fc} "):
            o.append(f"create_generated_clock -name tri_fo -source [get_ports {{{fp}}}] -master_clock {fc} -divide_by 1 -invert [get_ports {{{fo_port}}}]\n")
    out = []
    for l in o:
        p = parse(l)
        if p and p["clock"] == "vclk":
            if p["kind"] == "input": l = l.replace("[get_clocks {vclk}]", f"[get_clocks {{{fc}}}]").replace("-clock vclk", f"-clock {fc}")
            else: l = l.replace("[get_clocks {vclk}]", "[get_clocks {tri_fo}] -clock_fall").replace("-clock vclk", "-clock tri_fo -clock_fall")
        out.append(l)
    open(dst, "w").writelines(out); return True
def reps(sdc):
    out = {}
    for l in open(sdc):
        p = parse(l)
        if p and not p["is_min"] and p["clock"] and p["ports"]:
            out.setdefault((p["kind"], p["clock"]), p["ports"][0])
    return out
def split(sdc, pmap, dst, T=833.333):
    o = []; n = 0
    for l in open(sdc):
        p = parse(l)
        if p and not p["is_min"] and p["clock"] and p["value"] is not None:
            key = f"{p['kind']}:{p['clock']}"
            if key in pmap:                       # forwarded clock: source-synchronous split
                new = (pmap[key] - UNC + M) / 2.0
            elif p["clock"].startswith("vclk"):    # common-clock port: consistent common split
                new = T - UNC - 254.7
            else:
                o.append(l); continue
            l2 = re.sub(r"^(\s*set_(?:input|output)_delay\s+(?:-(?:max|rise|fall|add_delay)\s+)*)(-?[\d.]+)(?=\s)",
                        lambda m: m[1] + f"{new:.3f}", l, count=1)
            if l2 == l:
                l2 = re.sub(r"(\s)(-?[\d.]+)(\s+-clock)", lambda m: m[1] + f"{new:.3f}" + m[3], l, count=1)
            o.append(l2.rstrip("\n") + f"   ;# setup-triage srcsync: was {p['value']}\n"); n += 1
        else:
            o.append(l)
    open(dst, "w").writelines(o)
    print(f"rewrote {n} max IO delays")
if __name__ == "__main__":
    if sys.argv[1] == "retarget":
        print("RETARGET", retarget(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ""))
    elif sys.argv[1] == "reps":
        for (k, c), p in reps(sys.argv[2]).items(): print(k, c, p)
    else:
        split(sys.argv[2], json.load(open(sys.argv[3])), sys.argv[4])
