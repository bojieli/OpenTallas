#!/usr/bin/env python3
"""DIE-HBM-97/HBM-TAPS 11-11: cycle-shift equivalence of the +1 input relay stage (face_shell in_stages) for the two
pin-cycle cores, at the face-shell level (the __fcore is the byte-identical signed core, kept as a blackbox and
EVERTED: its input pins become miter outputs, its output pins shared miter inputs).  DO_NOT_COUNT.

  GOLD = signed shell (emit_shell, reproduced byte-identically from the kit face_shell.json) with a +1 register on
         every staged input bus in front of it (= the old core delayed by one cycle on those inputs).
  GATE = the new shell (emit_shell in_stages={bus: 1}).
  PASS  : yosys miter -equiv + sat -tempinduct -prove-asserts -set-init-zero proves GOLD == GATE (every core input pin
          and every shell output pin, every cycle).
  NEG 1 : GATE = in_short mutant (one bit of one staged bus skips the new stage) -> must FAIL.
  NEG 2 : GOLD without the +1 register (plain signed shell) vs GATE -> must FAIL (the stage is really there).

  python3 -I eq_cycles.py REPO_FACE_SHELL_DIR IN_DIR OUT_DIR YOSYS
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

CORES = {"ot_hbm_su_pg_lane_exp_x_core": ("expx_face_shell.json", "expx_fshell.sv"),
         "ot_hidx_s3_q": ("s3q_face_shell.json", "s3q_fshell.sv")}


def load_fs(d):
    spec = importlib.util.spec_from_file_location("fs", Path(d) / "face_shell.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def shell_args(J):
    rr = (J.get("reset_relay") or {}).get("resets") or None
    lk = set((J.get("out_lockup") or {}).get("buses") or ())
    return (J["module"], J["core"], J.get("params") or {}, J["widths"], J["dirs"], J["keep"], set(J["passthrough"]),
            J["clock"]), dict(scalars=set(J["scalars"]), stages=J.get("out_extra_stages") or None, lockup=lk or None,
                              rst_relay=rr)


def core_stub(J):
    """blackbox __fcore with the core port widths (the shell connects keep bits, zero-padded to the core width)."""
    ports = []
    for n, w in J["widths"].items():
        ports.append(f"    {J['dirs'][n]} wire [{int(w) - 1}:0] {n}")
    return f"(* blackbox *)\nmodule {J['core']} (\n" + ",\n".join(ports) + "\n);\nendmodule\n"


def gold_wrap(J, top, inner, staged, delay=True):
    decl, regs, conns = [], [], []
    for n, w in J["widths"].items():
        k = int(J["keep"][n])
        if k == 0:
            continue
        rng = "" if n in J["scalars"] else f"[{k - 1}:0] "
        decl.append(f"    {J['dirs'][n]} wire {rng}{n}")
        if n in staged and delay:
            regs.append(f"    reg {rng}{n}__d; always @(posedge {J['clock']}) {n}__d <= {n};")
            conns.append(f".{n}({n}__d)")
        else:
            conns.append(f".{n}({n})")
    return (f"module {top} (\n" + ",\n".join(decl) + "\n);\n" + "\n".join(regs) +
            f"\n    {inner} u_s ({', '.join(conns)});\nendmodule\n")


def rename(txt, old, new):
    t2, n = re.subn(rf"\bmodule\s+{re.escape(old)}\b", f"module {new}", txt, count=1)
    assert n == 1
    return t2


def prove(fs, out, tag, gold_sv, gate_sv, cells, stub, yosys):
    d = out / tag
    d.mkdir(parents=True, exist_ok=True)
    (d / "cells.sv").write_text(cells)
    (d / "stub.sv").write_text(stub)
    (d / "gold.sv").write_text(gold_sv)
    (d / "gate.sv").write_text(gate_sv)
    ys = f"""
read_verilog -sv {d}/cells.sv {d}/stub.sv {d}/gold.sv {d}/gate.sv
hierarchy -check
proc
setattr -mod -unset keep_hierarchy *
flatten gold_top
flatten gate_top
select -module gold_top
expose -evert t:*__fcore
select -clear
select -module gate_top
expose -evert t:*__fcore
select -clear
opt_clean
async2sync
miter -equiv -flatten -make_assert -ignore_gold_x gold_top gate_top miter
hierarchy -top miter
sat -verify -tempinduct -prove-asserts -set-init-zero -seq 1 -maxsteps 12 -show-ports miter
"""
    (d / "proof.ys").write_text(ys)
    r = subprocess.run([yosys, "-q", "-l", str(d / "yosys.log"), "-s", str(d / "proof.ys")], capture_output=True,
                       text=True, timeout=3600)
    log = (d / "yosys.log").read_text(errors="replace")
    ok = r.returncode == 0 and "SUCCESS!" in log
    return dict(rc=r.returncode, proved=ok, induction=("Induction step proven: SUCCESS!" in log or "SUCCESS!" in log),
                log=str(d / "yosys.log"), tail=(r.stderr or "")[-300:])


def main(fsdir, ind, out, yosys):
    fs = load_fs(fsdir)
    ind, out = Path(ind), Path(out)
    ev = json.loads(Path(sys.argv[5]).read_text())
    res = {}
    for mod, (fj, fsv) in CORES.items():
        J = json.loads((ind / fj).read_text())
        staged = ev["pin_cycles"][mod]["staged_buses"]
        a, kw = shell_args(J)
        old = fs.emit_shell(*a, **kw)
        signed = (ind / fsv).read_text()
        repro = old == signed
        new = fs.emit_shell(*a, **kw, in_stages={b: 1 for b in staged})
        mb = staged[0]
        mut = fs.emit_shell(*a, **kw, in_stages={b: 1 for b in staged},
                            mutant={"kind": "in_short", "bus": mb, "bit": 0})
        assert new.count("u_bimid0_") == len(staged)
        (out / mod).mkdir(parents=True, exist_ok=True)
        (out / mod / f"{mod}__fshell_hbmtaps.sv").write_text(new)
        cells = fs.CELL_SV + fs.NCELL_SV + fs.RCELL_SV
        stub = core_stub(J)
        o_ = rename(old, mod, f"{mod}__old")
        n_ = rename(new, mod, f"{mod}__new")
        m_ = rename(mut, mod, f"{mod}__new")
        g_d = o_ + gold_wrap(J, "gold_top", f"{mod}__old", set(staged), True)
        g_p = o_ + gold_wrap(J, "gold_top", f"{mod}__old", set(staged), False)
        gate = n_ + gold_wrap(J, "gate_top", f"{mod}__new", set(), False)
        gmut = m_ + gold_wrap(J, "gate_top", f"{mod}__new", set(), False)
        r = dict(signed_shell_reproduced=repro, staged_buses=len(staged), mutant_bus=mb,
                 PASS=prove(fs, out / mod, "pass", g_d, gate, cells, stub, yosys),
                 NEG_in_short=prove(fs, out / mod, "neg_in_short", g_d, gmut, cells, stub, yosys),
                 NEG_no_delay=prove(fs, out / mod, "neg_no_delay", g_p, gate, cells, stub, yosys))
        r["verdict"] = ("EQ_CYCLE_SHIFTED" if repro and r["PASS"]["proved"] and not r["NEG_in_short"]["proved"]
                        and not r["NEG_no_delay"]["proved"] else "NOT_PROVEN")
        res[mod] = r
        print(mod, json.dumps({k: (v if not isinstance(v, dict) else {kk: v[kk] for kk in ("rc", "proved")})
                               for k, v in r.items()}), flush=True)
    (out / "eq_cycles.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:5])
