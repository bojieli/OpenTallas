#!/usr/bin/env python3
"""bind_phases: per-phase wall / CPU of a die bind, with no change to the tree under test (BIND-SPEED-1118).

    python3 -I -B tools/die_plan/bind_phases.py [--phases-out FILE] -- <bind.py arguments>     (cwd = the bind tree)

Runs `tools/die_plan/bind.py` of the CURRENT DIRECTORY tree in-process with a timer on every Binder stage and the module-level
elab / flatten / plan-gate / report writers.  Prints one `PHASE name wall_s cpu_s cpu%` line per stage as it ends and writes
OUT/bind_phases.json (OUT = the --out argument, or --phases-out).  cpu% ~ 100 = single-threaded and CPU-bound; far below 100 on
a long phase = the host was oversubscribed (or the stage waits on a child process: yosys, slang).  Children's CPU is added.
"""
import json
import os
import resource
import sys
import time
from pathlib import Path

PHASES = []


def _cpu():
    s = resource.getrusage(resource.RUSAGE_SELF)
    c = resource.getrusage(resource.RUSAGE_CHILDREN)
    return s.ru_utime + s.ru_stime + c.ru_utime + c.ru_stime


def timed(name, fn):
    def wrap(*a, **k):
        w0, c0 = time.time(), _cpu()
        try:
            return fn(*a, **k)
        finally:
            w, c = time.time() - w0, _cpu() - c0
            PHASES.append(dict(phase=name, wall_s=round(w, 1), cpu_s=round(c, 1), cpu_pct=round(100 * c / w) if w > 0.05 else None))
            print(f"PHASE {name} wall {w:.1f}s cpu {c:.1f}s ({round(100 * c / w) if w > 0.05 else '-'}%)", flush=True)
    import functools
    return functools.wraps(fn)(wrap)


BINDER_STAGES = ("map_cells", "analyse", "build_buses", "align_landings", "uniform_inner", "regen_params", "check_types",
                 "pad_trees", "emit", "report", "bus_groups", "bump_pins", "wavefront_plan")
MODULE_STAGES = ("load_plan", "_plan_gate_pre", "_write_provenance", "cmd_elab", "cmd_bind", "cmd_kit_rtl", "cmd_r8_prepass", "_bind_through_landings")


SAMPLES = {}


def _sampler(main_ident, every):
    """poor man's py-spy (py-spy cannot attach to this interpreter): every `every` s record the main thread's innermost die_plan frames"""
    import threading
    import traceback
    stop = threading.Event()

    def run():
        while not stop.wait(every):
            fr = sys._current_frames().get(main_ident)
            if fr is None:
                continue
            st = traceback.extract_stack(fr)
            mine = [f"{Path(x.filename).name}:{x.name}" for x in st if "/die_plan/" in x.filename or "/tools/" in x.filename]
            if mine:
                for key in {" > ".join(mine[-1:]), " > ".join(mine[-3:])}:
                    SAMPLES[key] = SAMPLES.get(key, 0) + 1
    th = threading.Thread(target=run, daemon=True)
    th.start()
    return stop


def main(argv):
    out = None
    every = float(os.environ.get("OT_BIND_SAMPLE_S", "5"))
    stop = _sampler(__import__("threading").get_ident(), every) if every > 0 else None
    if argv and argv[0] == "--phases-out":
        out, argv = argv[1], argv[2:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    here = Path.cwd() / "tools" / "die_plan"
    sys.path.insert(0, str(here))
    import bind as B
    for n in BINDER_STAGES:
        if hasattr(B.Binder, n):
            setattr(B.Binder, n, timed("Binder." + n, getattr(B.Binder, n)))
    for n in MODULE_STAGES:
        if hasattr(B, n):
            setattr(B, n, timed(n, getattr(B, n)))
    if hasattr(B.E, "flatten"):
        B.E.flatten = timed("elab.flatten", B.E.flatten)
    if hasattr(B.E, "elab"):
        B.E.elab = timed("elab.yosys", B.E.elab)
    w0, c0 = time.time(), _cpu()
    sys.argv = [str(here / "bind.py")] + argv
    rc = 1
    try:
        rc = B.main(argv)
    finally:
        tot = dict(phase="TOTAL", wall_s=round(time.time() - w0, 1), cpu_s=round(_cpu() - c0, 1))
        PHASES.append(tot)
        if stop:
            stop.set()
            top = sorted(SAMPLES.items(), key=lambda kv: -kv[1])[:40]
            PHASES.append(dict(phase="SAMPLES_every_%gs" % every, top=[dict(where=k, samples=v, approx_s=round(v * every)) for k, v in top]))
            for k, v in top[:15]:
                print(f"SAMPLE {v * every:7.0f}s  {k}", flush=True)
        if out is None and "--out" in argv:
            out = argv[argv.index("--out") + 1]
        if out:
            Path(out).mkdir(parents=True, exist_ok=True)
            (Path(out) / "bind_phases.json").write_text(json.dumps(dict(host=os.uname().nodename, loadavg=os.getloadavg(),
                                                                       ncpu=os.cpu_count(), phases=PHASES), indent=1) + "\n")
        print("PHASE TOTAL wall %.1fs cpu %.1fs" % (tot["wall_s"], tot["cpu_s"]), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
