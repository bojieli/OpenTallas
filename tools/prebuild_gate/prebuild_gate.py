"""OWNER 11-03 RE-FORM pre-build gate verdict (die-agnostic). ADVISORY (OWNER 07:0x): a report, it never blocks a launch
(exit code 0 unless the tool itself fails). Reads OUT/work written by prebuild_gate.sh and writes
OUT/prebuild_gate.json.  PASS iff ALL of:
  timing  worst TT setup (ideal clocks at the planned insertion latency, placement RC) >= +10% of the period
  cells   std cells after resize <= 150,000
  memory  no inferred memory over SYNTH_MEMORY_MAX_BITS (memories must be generated macros)
  straps  no strap_* port that the kit does not declare (leaked strap)
  face    every data input/output bit has a flop at the face (tools/die_plan/face_guard.py guard(), plain mode:
          clock + reset ports skipped, declared straps/dead inputs exempt) -> pin_unreg == 0
  reset   every reset port lands on <= 8 flop pins (registered relay / synchroniser), not raw async fanout
Also reported (not gated): stage_ps = period - worst r2r slack (> 583 ps = 70% of 833 -> RTL stage cut), counts.
    python3 prebuild_gate.py OUT_DIR
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "die_plan"))
import face_guard as FG  # noqa: E402

CELL_CAP = 150_000
SETUP_FRAC = 0.10
STAGE_FRAC = 0.70
RESET_LANDING_MAX = 8


def cfg_vars(text):
    v = {}
    for m in re.finditer(r"^(?:override\s+)?export\s+(\w+)\s*\??=\s*(.*)$", text, re.M):
        v[m.group(1)] = m.group(2).strip()
    return v


def sta_numbers(log):
    r = {"groups": {}}
    for ln in log.splitlines():
        t = ln.split()
        if not t or t[0] != "GATE":
            continue
        if t[1] == "cells":
            r.update(cells=int(t[2]), macros=int(t[4]), stdcell_area_um2=float(t[6]), sta_stage=t[8])
        elif t[1] == "period":
            r["period"] = float(t[2])
        elif t[1] == "group":
            r["groups"][t[2]] = None if t[3] == "none" else {"slack": float(t[4]), "start": t[6], "end": t[8]}
        elif t[1] == "r2r_endpoints_stage_over_583":
            r["r2r_endpoints_stage_over_583"] = int(t[2])
    sl = [g["slack"] for g in r["groups"].values() if g]
    r["wns"] = min(sl) if sl else None
    m = re.search(r"GATE_WORST_BEGIN\n(.*?)GATE_WORST_END", log, re.S)
    r["worst_path"] = m.group(1)[-6000:] if m else None
    return r


def memories(path, max_bits):
    out = []
    if not path.is_file():
        return out
    try:
        d = json.loads(path.read_text())
    except ValueError:
        return out
    for mod, md in (d.get("modules") or {}).items():
        for name, mm in (md.get("memories") or {}).items():
            bits = int(mm.get("width", 0)) * int(mm.get("size", 0))
            out.append({"module": mod, "memory": name, "bits": bits, "over": bits > max_bits})
    return out


def main(out):
    out = Path(out)
    w = out / "work"
    cfg = cfg_vars((w / "config.mk").read_text())
    top = cfg.get("DESIGN_NAME")
    res = {"schema": "opentallas.prebuild_gate.v1", "kit": (out / "kit_src.txt").read_text().strip(), "design": top}
    st = (w / "gate_flow.status").read_text() if (w / "gate_flow.status").is_file() else ""
    res["flow_status"] = st.split()
    log = (w / "gate_sta.log").read_text() if (w / "gate_sta.log").is_file() else ""
    s = sta_numbers(log)
    res.update({k: s.get(k) for k in ("cells", "macros", "stdcell_area_um2", "sta_stage", "period", "groups", "wns",
                                     "r2r_endpoints_stage_over_583")})
    per = s.get("period") or 833.0
    r2r = (s["groups"].get("r2r") or {}).get("slack")
    res["stage_ps"] = round(per - r2r, 1) if r2r is not None else None
    res["stage_limit_ps"] = round(STAGE_FRAC * per, 1)
    res["setup_limit_ps"] = round(SETUP_FRAC * per, 1)
    checks = {}
    wns = s.get("wns")
    checks["timing"] = {"ok": wns is not None and wns >= SETUP_FRAC * per and s.get("sta_stage") == "place_resized",
                        "wns": wns, "sta_stage": s.get("sta_stage")}
    checks["cells"] = {"ok": s.get("cells") is not None and s["cells"] <= CELL_CAP, "cells": s.get("cells")}
    mx = int(cfg.get("SYNTH_MEMORY_MAX_BITS", "4096"))
    mems = memories(w / "gate_mem.json", mx)
    checks["memory"] = {"ok": not any(m["over"] for m in mems), "max_bits": mx, "largest": max([m["bits"] for m in mems], default=0),
                        "over": [m for m in mems if m["over"]][:10]}
    net = w / "gate_synth.v"
    if net.is_file():
        text = net.read_text()
        fzf = w / "freeze.json"
        fz = json.loads(fzf.read_text()) if fzf.is_file() else {"clocks": ["clk"], "resets": []}
        base = lambda n: re.escape(re.sub(r"\[\d+\]$", "", n))
        clk = [base(n) for n in fz.get("clocks", [])]
        rst = [base(n) for n in fz.get("resets", [])]
        straps = FG.kit_strap_list(w)
        dead = FG.kit_dead_list(w)
        g = FG.guard(text, top, skip_re="^(" + "|".join(clk + rst) + ")$", straps=straps, dead=dead)
        nf = sum(g.get("fail_counts", {}).values())
        checks["face"] = {"ok": nf == 0, "pin_unreg": nf, "checked": g.get("checked"), "fail_counts": g.get("fail_counts"),
                          "fails_head": {k: v[:8] for k, v in g.get("fails", {}).items()}}
        mt = re.search(r"module\s+" + re.escape(top) + r"\b.*?endmodule", text, re.S)
        ports = re.findall(r"\b(?:input|output)\s+(?:wire\s+)?(?:\[[^\]]+\]\s*)?(\w+)", mt.group(0) if mt else "")
        sp = sorted({p for p in ports if p.startswith("strap_")})
        leaked = [p for p in sp if p not in set(re.sub(r"\[\d+\]$", "", x) for x in straps)]
        checks["straps"] = {"ok": not leaked, "strap_ports": sp, "leaked": leaked}
        if rst:
            # registered reset relay = the reset port lands on <= RESET_LANDING_MAX flop pins (a relay flop or an
            # async-assert/sync-deassert synchroniser, the KV-57 reset-spine landing bound), never raw fanout.
            fan = {}
            for r in fz.get("resets", []):
                pat = re.escape(r) if "[" in r else re.escape(r) + r"(?:\[\d+\])?"
                fan[r] = len(re.findall(r"\.\w+\(\s*\\?" + pat + r"\s*\)", mt.group(0) if mt else ""))
            bad = sorted(r for r, n in fan.items() if n == 0 or n > RESET_LANDING_MAX)
            checks["reset"] = {"ok": not bad, "resets": fz.get("resets"), "landing_pins": fan, "unregistered": bad,
                               "max": RESET_LANDING_MAX}
        else:
            checks["reset"] = {"ok": True, "resets": [], "note": "no reset port"}
    else:
        for k in ("face", "straps", "reset"):
            checks[k] = {"ok": False, "why": "no synth netlist"}
    res["checks"] = checks
    res["advisory"] = True
    res["verdict"] = "PASS" if all(c["ok"] for c in checks.values()) else "FAIL"
    res["fails"] = [k for k, c in checks.items() if not c["ok"]]
    res["needs_stage_cut"] = res["stage_ps"] is not None and res["stage_ps"] > res["stage_limit_ps"]
    res["worst_path"] = s.get("worst_path")
    (out / "prebuild_gate.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"PREBUILD_GATE(advisory) {res['verdict']} {top} wns {wns} stage_ps {res['stage_ps']} cells {s.get('cells')} "
          f"pin_unreg {checks['face'].get('pin_unreg')} mem_max {checks['memory']['largest']} fails {res['fails']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
