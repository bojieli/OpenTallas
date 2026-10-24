#!/usr/bin/env python3
"""CAL-AUTO 10-23: the post-bind gate.  Run it as the LAST step of every bind (BINDER run scripts):

    bind_post.py --die {qwen_compute,qwen_kvsys,hbm,s81} --bound BIND_DIR [--peer BIND_DIR]
                 [--smoke {submit,print,skip}] [--work SCRATCH] [--expect EXPECT.json]

1. regen_constants.py -> BIND_DIR/regen/constants.json + BIND_DIR/regen/<die>_sched_pkg.sv: every schedule constant
   the compilers / RTL params need, from this bind's landed depths; RTL constants cross-checked against the hook's
   param_regen.json (MISMATCH or ERROR = FAIL).
2. bind_smoke.py (functional smoke: one representative token stage on the bound top with the regenerated constants
   + one mutant that must FAIL; ot-run, honest --mem) -> BIND_DIR/smoke/smoke_report.json.
   --smoke submit runs it now through ot-run (blocking); print = only print the command (bind script runs it later);
   skip = record SKIPPED.
3. BIND_DIR/bind_gate.json (schema opentallas.die_plan.bind_gate.v1) + one line on stdout:
       BIND_GATE <die> PASS|FAIL|INCOMPLETE regen=<PASS|FAIL> smoke=<PASS|FAIL|PENDING|SKIPPED|...>
   INCOMPLETE = regen PASS but the functional smoke has no verdict yet (PENDING vehicle / not run): never PASS.
Exit 0 only on PASS.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regen_constants as RC  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] if Path(p).exists() else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--die", required=True, choices=["qwen_compute", "qwen_kvsys", "hbm", "s81"])
    ap.add_argument("--bound", required=True, type=Path)
    ap.add_argument("--peer", type=Path)
    ap.add_argument("--expect", type=Path)
    ap.add_argument("--smoke", default="print", choices=["submit", "print", "skip"])
    ap.add_argument("--work", type=Path, help="scratch dir for the smoke vehicle (default BIND_DIR/smoke/work)")
    ap.add_argument("--src-rev", help="bind_smoke: git revision of the as-built source tree bind.f refers to (QC)")
    ap.add_argument("--asbuilt", type=Path, help="bind_smoke: the bind as-built recipe JSON (QC; default from README)")
    ap.add_argument("--src-root", type=Path, default=RC.REPO)
    ap.add_argument("--hbm-tools", type=Path)
    ap.add_argument("--kv-boot", type=Path, help="KV: boot run dir of this bind (regen_constants --kv-boot)")
    a = ap.parse_args(argv)
    B = a.bound.resolve()
    rd = B / "regen"
    rd.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rargs = ["--die", a.die, "--bound", str(B), "--out-json", str(rd / "constants.json"),
             "--out-sv", str(rd / f"{a.die}_sched_pkg.sv"), "--src-root", str(a.src_root)]
    if a.peer:
        rargs += ["--peer", str(a.peer)]
    if a.expect:
        rargs += ["--expect", str(a.expect)]
    if a.hbm_tools:
        rargs += ["--hbm-tools", str(a.hbm_tools)]
    if a.kv_boot:
        rargs += ["--kv-boot", str(a.kv_boot)]
    rc = RC.main(rargs)
    doc = json.loads((rd / "constants.json").read_text())
    regen = dict(verdict="PASS" if rc == 0 else "FAIL", counts=doc["verdict"], json=str(rd / "constants.json"),
                 sv=str(rd / f"{a.die}_sched_pkg.sv"), sha=sha(rd / "constants.json"), seconds=round(time.time() - t0, 1),
                 problems={k: v.get("mismatch") or v["formula"] for k, v in doc["constants"].items()
                           if v["status"] in ("ERROR", "MISMATCH")})
    smoke_py = HERE / "bind_smoke.py"
    rep = B / "smoke" / "smoke_report.json"
    cmd = [sys.executable, str(smoke_py), "--die", a.die, "--bound", str(B), "--constants", str(rd / "constants.json"),
           "--work", str(a.work or (B / "smoke" / "work"))]
    if a.src_rev:
        cmd += ["--src-rev", a.src_rev]
    if a.asbuilt:
        cmd += ["--asbuilt", str(a.asbuilt)]
    smoke = dict(command=" ".join(cmd + ["--submit"]))
    if not smoke_py.exists():
        smoke["verdict"] = "PENDING"
        smoke["why"] = "tools/die_plan/bind_smoke.py not on this branch"
    elif a.smoke == "skip":
        smoke["verdict"] = "SKIPPED"
    elif a.smoke == "print":
        smoke["verdict"] = "NOT_RUN"
        print("smoke:", smoke["command"])
    else:
        if regen["verdict"] != "PASS":
            smoke["verdict"] = "NOT_RUN"
            smoke["why"] = "regen FAIL: the smoke would run with inconsistent constants"
        else:
            subprocess.run(cmd + ["--submit"])
            smoke["verdict"] = "NO_REPORT"
    if a.smoke == "submit" and smoke.get("verdict") == "NO_REPORT" and rep.exists():
        r = json.loads(rep.read_text())
        smoke.update(verdict=r.get("verdict", "NO_VERDICT"), report=str(rep),
                     constants_sha_match=r.get("constants_sha") in (None, regen["sha"]) or "stale")
    ok_regen = regen["verdict"] == "PASS"
    sv = smoke["verdict"]
    verdict = "FAIL" if (not ok_regen or sv in ("FAIL", "BUILD_FAIL")) else ("PASS" if sv == "PASS" else "INCOMPLETE")
    gate = dict(schema="opentallas.die_plan.bind_gate.v1", die=a.die, bound=str(B), bound_sha=doc.get("bound_sha"),
                time=time.strftime("%Y-%m-%d %H:%M:%S %Z"), regen=regen, smoke=smoke, verdict=verdict,
                recipes=doc.get("recipes", {}))
    (B / "bind_gate.json").write_text(json.dumps(gate, indent=1) + "\n")
    print(f"BIND_GATE {a.die} {verdict} regen={regen['verdict']} smoke={sv} -> {B / 'bind_gate.json'}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
