#!/usr/bin/env python3
"""Generation-time kit lint (OWNER RULE 12.27 (d), AUTOBUILD-PIPE-4 10-31): a BUILD check, not a sign-off check.

Fails a freshly generated kit before any synth / place allocation on the structural classes the kit wave kept
finding only at synth, place or CTS:

  pins_vs_plan       kit placed pin set == the plan's canonical pin set (kit_contract.pins_canonical, every kit;
                     it was binding on hard-core kits only)
  clock_export_form  a forwarded clock output with a create_generated_clock must use the fwd_buffer export form; the
                     legacy tie text (output BTerm joined onto the source tap net) stops TritonCTS with CTS-0114
  macro_tcl          a kit whose sources instantiate a staged LEF macro must stage MACRO_PLACEMENT_TCL (static sites)
  rtl_check          yosys elaboration with the flow's frontend: hierarchy, undriven and multi-driven nets
                     (`check`, same script as rtl_lint.py, run in the flow image)
  memory_bits        every inferred memory (WIDTH x SIZE after memory_collect) <= SYNTH_MEMORY_MAX_BITS (ORFS
                     default 4096) unless SYNTH_MOCK_LARGE_MEMORIES = 1: ORFS mem_dump.py fails synth otherwise
  src_skew           (kit_wave, on the hub, after gen; COORD 04:0x KIT-WAVE-5 03:47) the kit's source commit vs the
                     queue's: the queue admits a kit with ITS OWN lint (kit_preflight / kit_contract / sdc_lint, the
                     admission bundle), so a kit generated on a source whose copy of those files differs can fail there
                     after place + AUTO-GEOM (S81 t6/t29 'landed-crossing window 416.5 vs 356.5', src 1a34525e751 vs
                     main).  src_skew() lists the QUEUE_LINT_FILES that differ; when sdc_lint.py differs kit_wave runs
                     the queue's own sdc_lint on the kit (exact admission verdict, never a false fail).

The SDC landing window is checked by sdc_lint (kit_preflight sdc_and_ff_binding), which the wave runs right after
this lint; it is not repeated here.

  kit_gen_lint.py KIT [--plan-dir D] [--no-yosys] [--image IMG] [--mem GB]  -> KIT/gen_lint.json, exit 1 on FAIL
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract  # noqa: E402
import rtl_lint  # noqa: E402

ORFS_MEMORY_MAX_BITS = 4096                 # ORFS variables.yaml SYNTH_MEMORY_MAX_BITS default (orfs:asap7lock)
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
TIE_FORM = "$cland_dst connect $cland_net"   # landing_contract.export_tcl legacy tie text


# the queue's admission lint (autopilot stage_admission_tools bundle: kit_preflight + kit_contract + sdc_lint, run by
# signoff_chain) -- a kit whose generating source has a different copy of these is linted by rules it was not made for
QUEUE_LINT_FILES = ("tools/die_plan/kit_preflight.py", "tools/die_plan/kit_contract.py", "tools/die_plan/sdc_lint.py",
                    "tools/autopilot/signoff_chain.py")


def src_skew(src_sha, queue_repo, files=QUEUE_LINT_FILES):
    """-> (errors, info).  errors non-empty = the kit source is not on the queue's lint version (re-GEN on a source at
    or after the queue's commit for these files)."""
    def git(*a):
        return subprocess.run(["git", "-C", str(queue_repo), *a], capture_output=True, text=True)
    if not src_sha:
        return [], dict(applies=False, reason="no source commit in the launch spec")
    head = git("rev-parse", "HEAD")
    if head.returncode:
        return [], dict(applies=False, reason=f"queue repo {queue_repo} is not a git checkout")
    qsha = head.stdout.strip()
    src = git("rev-parse", "--verify", "--quiet", f"{src_sha}^{{commit}}")
    if src.returncode:
        return [], dict(applies=False, reason=f"source {src_sha} unknown to the queue repo (not proven either way)",
                        queue=qsha[:11])
    ssha = src.stdout.strip()
    if ssha == qsha:
        return [], dict(applies=True, src=ssha[:11], queue=qsha[:11], differ=[])
    d = git("diff", "--name-only", ssha, qsha, "--", *files)
    if d.returncode:
        return [f"src_skew: git diff {ssha[:11]}..{qsha[:11]} failed: {d.stderr.strip()[:200]}"], dict(applies=True)
    differ = [x for x in d.stdout.split() if x]
    anc = git("merge-base", "--is-ancestor", ssha, qsha).returncode == 0
    errs = ([f"kit src {ssha[:11]} {'older than' if anc else 'differs from'} the queue lint {qsha[:11]}: "
             f"{', '.join(differ)} differ -> re-GEN on a source >= {qsha[:11]}"] if differ else [])
    return errs, dict(applies=True, src=ssha[:11], queue=qsha[:11], src_is_ancestor=anc, differ=differ)


def _cfg(kd):
    return rtl_lint.config(kd) if (kd / "config.mk").is_file() else {}


def _sources_text(kd):
    out = []
    for p in rtl_lint._kit_sources(kd):
        if p.is_file() and not re.search(r"_bb\.(?:s?v)$", p.name):
            out.append(p.read_text(errors="replace"))
    return "\n".join(out)


def pins_vs_plan(kd, plan_dir=None):
    if not (kd / "freeze.json").is_file():
        return [], False
    errors, _info = kit_contract.pins_canonical(kd, plan_dir)
    return errors, True


def _generated_clock_ports(sdc):
    ports = set()
    for cmd in re.findall(r"^\s*create_generated_clock\b[^\n]*", sdc, re.M):
        for grp in re.findall(r"get_ports\s+(?:\{([^}]*)\}|\[?list\s+([^\]]*)\]|(\S+?)\])", cmd):
            for s in grp:
                ports.update(x.strip("{}") for x in s.split())
    return {p for p in ports if p}


def clock_export_form(kd):
    le = kd / "landing_exports.tcl"
    if not le.is_file():
        return [], False
    txt = le.read_text(errors="replace")
    if TIE_FORM not in txt:
        return [], True
    sdc = (kd / "constraint.sdc").read_text(errors="replace") if (kd / "constraint.sdc").is_file() else ""
    tied = re.findall(r"OT_CLAND_EXPORT (\S+) <- (\S+)\}", txt)
    gen = _generated_clock_ports(sdc)
    hit = [n for n, _ in tied if n in gen or re.sub(r"\[\d+\]$", "", n) in gen] or ([n for n, _ in tied] if gen else [])
    return [f"forwarded clock output {n} uses the tie export form with a create_generated_clock on the port "
            f"(TritonCTS CTS-0114); regenerate with clock.landing_export_form fwd_buffer (the default)" for n in hit], True


def macro_tcl(kd):
    cfg = kit_contract._mk(kd)
    sizes = kit_contract._lef_sizes(kd, cfg)
    if not sizes:
        return [], False
    text = _sources_text(kd)
    used = sorted(m for m in sizes if re.search(r"(?<![\w$])" + re.escape(m) + r"\s+(?:#\s*\(|[\\A-Za-z_])", text))
    if not used:
        return [], False
    mp = kit_contract._kfile(kd, cfg.get("MACRO_PLACEMENT_TCL", "") or "/")
    if not cfg.get("MACRO_PLACEMENT_TCL") or mp is None or not mp.is_file():
        return [f"{len(used)} instantiated macro master(s) {used[:4]} but no staged MACRO_PLACEMENT_TCL "
                f"({cfg.get('MACRO_PLACEMENT_TCL')!r}): the plan gives no static macro sites"], True
    txt = mp.read_text(errors="replace")
    if not re.search(r"\bplace_macro\b|\bsetLocation\b|\bplace_inst\b|\bforeach\b", txt):
        return [f"{mp.name} places no macro (no place_macro / setLocation)"], True
    return [], True


LINT_TCL = r"""yosys -import
script /work/gen_lint_elab.ys
tee -q -o /work/gen_lint_check.log check
memory_collect
set f [open /work/gen_lint_mem.tsv w]
foreach path [split [string trim [tee -q -s result.string select -list t:\$mem_v2]] "\n"] {
  if {$path eq ""} continue
  set i [string first "/" $path]
  set m [string range $path 0 [expr {$i - 1}]]
  set c [string range $path [expr {$i + 1}] end]
  puts $f "$path\t[rtlil::get_param -uint $m $c WIDTH]\t[rtlil::get_param -uint $m $c SIZE]"
}
close $f
"""


def elab_script(kd):
    """rtl_lint's elaboration (same frontend options, liberties, top params) without its final 'check -assert':
    the tcl driver (LINT_TCL) logs `check`, then memory_collect and one row per $mem_v2 (path, WIDTH, SIZE)."""
    return "\n".join(ln for ln in rtl_lint.script(kd).splitlines() if ln.strip() != "check -assert") + "\n"


def parse_check(log):
    """yosys `check` problems: the Warning lines it reports (undriven, multiple drivers, logic loops)."""
    probs = [ln.strip() for ln in log.splitlines() if re.match(r"\s*Warning:", ln)]
    m = re.search(r"Found and reported (\d+) problems", log)
    if m and int(m.group(1)) and not probs:
        probs = [f"yosys check reported {m.group(1)} problems"]
    return probs


def memory_errors(rows, cfg):
    if (cfg.get("SYNTH_MOCK_LARGE_MEMORIES") or ["0"])[-1] == "1":
        return []
    lim = int((cfg.get("SYNTH_MEMORY_MAX_BITS") or [ORFS_MEMORY_MAX_BITS])[-1])
    out = []
    for path, w, s in rows:
        if w * s > lim:
            out.append(f"memory {path} {s} x {w} = {w * s} bits > SYNTH_MEMORY_MAX_BITS {lim} (ORFS mem_dump fails "
                       f"synth): set the recipe's synth_memory_max_bits or make it a macro")
    return out


def run_yosys(kd, image=IMAGE, mem_gb=8):
    (kd / "gen_lint_elab.ys").write_text(elab_script(kd))
    (kd / "gen_lint.tcl").write_text(LINT_TCL)
    for f in ("gen_lint_check.log", "gen_lint_mem.tsv"):
        (kd / f).unlink(missing_ok=True)
    cmd = ["docker", "run", "--rm", f"--memory={mem_gb}g", f"--memory-swap={mem_gb}g", "-v", f"{kd}:/work",
           "--user", f"{os.getuid()}:{os.getgid()}", image, "bash", "-lc",
           "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -c /work/gen_lint.tcl > /work/gen_lint_yosys.log 2>&1"]
    rc = subprocess.run(cmd, text=True, capture_output=True).returncode
    log = (kd / "gen_lint_yosys.log").read_text(errors="replace") if (kd / "gen_lint_yosys.log").is_file() else ""
    if rc or not (kd / "gen_lint_mem.tsv").is_file():
        errs = re.findall(r"^.*\bERROR:.*$", log, re.M) or [f"yosys elaboration failed rc {rc} (gen_lint_yosys.log)"]
        return errs, None, rc
    chk = (kd / "gen_lint_check.log").read_text(errors="replace") if (kd / "gen_lint_check.log").is_file() else ""
    rows = []
    for ln in (kd / "gen_lint_mem.tsv").read_text().splitlines():
        p, w, s = ln.split("\t")
        rows.append((p, int(w), int(s)))
    return parse_check(chk), rows, 0


def lint(kd, plan_dir=None, yosys=True, image=IMAGE, mem_gb=8):
    kd = Path(kd).resolve()
    checks = {}

    def put(name, fn):
        try:
            errors, applies = fn()
        except Exception as error:          # fail closed: a lint that cannot run is a FAIL
            errors, applies = [f"lint could not run: {type(error).__name__}: {error}"], True
        checks[name] = dict(verdict="FAIL" if errors else ("PASS" if applies else "NA"), errors=errors[:40],
                            n_errors=len(errors))

    put("pins_vs_plan", lambda: pins_vs_plan(kd, plan_dir))
    put("clock_export_form", lambda: clock_export_form(kd))
    put("macro_tcl", lambda: macro_tcl(kd))
    cfg = _cfg(kd)
    if yosys and cfg.get("DESIGN_NAME"):
        res = {}

        def ys():
            res["r"] = run_yosys(kd, image, mem_gb)
            errs, rows, rc = res["r"]
            return errs, True
        put("rtl_check", ys)
        rows = res.get("r", (None, None, 1))[1]
        put("memory_bits", lambda: (memory_errors(rows, cfg), True) if rows is not None
            else (["not measured: yosys elaboration failed (see rtl_check)"], True))
    else:
        checks["rtl_check"] = checks["memory_bits"] = dict(verdict="NA", errors=[], n_errors=0)
    bad = [f"{n}: {e}" for n, row in checks.items() for e in row["errors"]]
    return dict(schema="opentallas.kit_gen_lint.v1", kit=str(kd), verdict="FAIL" if bad else "PASS",
                checks=checks, issues=bad, note="BUILD check (OWNER 12.27 d), not a sign-off check")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit", type=Path)
    ap.add_argument("--plan-dir", type=Path)
    ap.add_argument("--no-yosys", action="store_true", help="static checks only (unit tests / hosts without docker)")
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--mem", type=int, default=8, help="yosys container memory cap, GB")
    a = ap.parse_args(argv)
    rec = lint(a.kit, a.plan_dir, not a.no_yosys, a.image, a.mem)
    (Path(rec["kit"]) / "gen_lint.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("GEN_LINT", rec["verdict"], "issues", len(rec["issues"]),
          " ".join(f"{n}={r['verdict']}" for n, r in rec["checks"].items()))
    for i in rec["issues"][:30]:
        print("  - GEN_LINT FAIL", i)          # FAIL on every issue line: kit_wave.error_lines/classify read them
    return int(rec["verdict"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
