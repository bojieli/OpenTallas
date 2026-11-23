#!/usr/bin/env python3
"""Generation-time kit lint (OWNER RULE 12.27 (d), AUTOBUILD-PIPE-4 10-31): a BUILD check, not a sign-off check.

Fails a freshly generated kit before any synth / place allocation on the structural classes the kit wave kept
finding only at synth, place or CTS:

  pins_vs_plan       kit placed pin set == the plan's canonical pin set (kit_contract.pins_canonical, every kit;
                     it was binding on hard-core kits only)
  clock_export_form  a forwarded clock output with a create_generated_clock must use the fwd_buffer export form; the
                     legacy tie text (output BTerm joined onto the source tap net) stops TritonCTS with CTS-0114
  macro_tcl          a kit whose sources instantiate a staged LEF macro must stage MACRO_PLACEMENT_TCL (static sites)
  macro_site_count   (MACRO-SITES-GEN-1122, COORD 20:1x) a kit whose MACRO_PLACEMENT_TCL is the KV static site form
                     (cores/macro_sites/macro_sites.py) lists exactly as many sites per master as the ELABORATED design has
                     instances of it (yosys flatten + select t:<master>); 2 sites for a 4-SRAM core (KV ectl q1/q2) failed
                     only at floorplan.  Kits without that form are NA.
  kit_rtl_paths      (COORD r107) every source the kit-rtl filelist names lies in the kit's own source tree (gen --rtl-root),
                     the bind out dir or the kit-rtl dir; a path in another tree (B6gsl/src beside the kit's src_rel2 copy) is
                     a stale-source kit.  Kits without kit_rtl_paths.json (no --kit-rtl) are NA.
  rtl_check          yosys elaboration with the flow's frontend: hierarchy, undriven and multi-driven nets
                     (`check`, same script as rtl_lint.py, run in the flow image)
  memory_bits        every inferred memory (WIDTH x SIZE after memory_collect; with OT_LANDING_FF = 1 after the same
                     landing-ring flip-flop map synth applies) <= SYNTH_MEMORY_MAX_BITS (ORFS
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
LINT_MEMORY_MAX_BITS = 65536                # default for OT_LINT_MEMORY_MAX_BITS (die item_env)
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
TIE_FORM = "$cland_dst connect $cland_net"   # landing_contract.export_tcl legacy tie text


# the queue's admission lint (autopilot stage_admission_tools bundle: kit_preflight + kit_contract + sdc_lint, run by
# signoff_chain) -- a kit whose generating source has a different copy of these is linted by rules it was not made for
QUEUE_LINT_FILES = ("tools/die_plan/kit_preflight.py", "tools/die_plan/kit_contract.py", "tools/die_plan/sdc_lint.py",
                    "tools/autopilot/signoff_chain.py")


def _no_lazy_env():
    return dict(os.environ, GIT_NO_LAZY_FETCH="1")


def src_skew(src_sha, queue_repo, files=QUEUE_LINT_FILES):
    """-> (errors, info).  errors non-empty = the kit source is not on the queue's lint version (re-GEN on a source at
    or after the queue's commit for these files)."""
    def git(*a):
        # KW-FIX-41: every git call here runs with lazy fetch off.  A partial-clone checkout never downloads a pack for a lint.
        return subprocess.run(["git", "-C", str(queue_repo), *a], capture_output=True, text=True, env=_no_lazy_env())
    if not src_sha:
        return [], dict(applies=False, reason="no source commit in the launch spec")
    head = git("rev-parse", "HEAD")
    if head.returncode:
        return [], dict(applies=False, reason=f"queue repo {queue_repo} is not a git checkout")
    qsha = head.stdout.strip()
    # KW-FIX-40 11-08 (COORD: hub scratch2 at 0 GB): an existence check must not lazy-fetch in a partial clone; every run-item
    # fetched the full 747k-object pack (27 x 7.4 GB).  A commit the repo lacks takes the "not proven either way" path below.
    src = git("rev-parse", "--verify", "--quiet", f"{src_sha}^{{commit}}")
    if src.returncode:
        print(f"KW_SRC_SKEW_ERROR commit {src_sha} is not in {queue_repo}: no lazy fetch, skew not judged", flush=True)
        return [], dict(applies=False, reason=f"source {src_sha} unknown to the queue repo (not proven either way)",
                        queue=qsha[:11])
    ssha = src.stdout.strip()
    if ssha == qsha:
        return [], dict(applies=True, src=ssha[:11], queue=qsha[:11], differ=[])
    d = git("diff", "--no-renames", "--name-only", ssha, qsha, "--", *files)
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
@LANDING_FF@memory_collect
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

# MACRO-SITES-GEN-1122: per-master instance count of the elaborated design (flattened copy; the census above is unchanged)
# COUNT-LIVE-1122 (COORD 21:1x, FABLE-KV-DIE q0k/q3k): count LIVE instances only -- flatten + opt_clean -purge drops dead branches
# (q0 u_leaf.u_b g_macro[0..1], outputs unused) exactly as synth does: elaborated 4, opt_clean 2 = the synth netlist 1_2_yosys.v
MACRO_COUNT_TCL = r"""design -save ot_gl
flatten
opt_clean -purge
set f [open /work/gen_lint_macros.tsv w]
foreach m {@MASTERS@} {
  set s [string trim [tee -q -s result.string select -list t:$m]]
  puts $f "$m\t[expr {$s eq "" ? 0 : [llength [split $s "\n"]]}]"
}
close $f
design -load ot_gl
"""
KV_SITES_HEAD = "# GENERATED by physical/die_plan/qwen_kvsys/cores/macro_sites/macro_sites.py"


def kv_site_counts(kd):
    """{master: n sites} of a kit whose MACRO_PLACEMENT_TCL is the KV static site form, else None"""
    cfg = kit_contract._mk(kd)
    mp = kit_contract._kfile(kd, cfg.get("MACRO_PLACEMENT_TCL", "") or "/")
    if mp is None or not mp.is_file():
        return None
    t = mp.read_text(errors="replace")
    if not t.startswith(KV_SITES_HEAD):
        return None
    m = re.search(r"foreach \{master sites\} \{(.*)\} \{\n", t)
    if not m:
        return None
    return {k: len(re.findall(r"\{[^{}]*\}", v)) for k, v in re.findall(r"(\S+) \{((?:\{[^{}]*\}\s*)*)\}", m.group(1))}


def macro_site_count(kd, measured):
    sites = kv_site_counts(kd)
    if sites is None:
        return [], False
    if measured is None:
        return [f"{sorted(sites)}: instance count not measured (yosys elaboration failed, see rtl_check)"], True
    return [f"{m}: {n} static site(s) in macro_place.tcl but {measured.get(m, 0)} live instance(s) in the elaborated design (flatten + opt_clean, as synth) "
            f"(fix cores/macro_sites/<module>.json: one site per instance)" for m, n in sorted(sites.items())
            if measured.get(m, 0) != n], True


# AUTOBUILD-PIPE-5 10-31 (COORD 06:1x, KIT-WAVE-5 05:44 S81 iqf__t1 'ot_meso_ring/s_d 4 x 1408'): a kit with
# OT_LANDING_FF = 1 has its clock-landing ring memories mapped to flip-flops by physical/common_flow/ot_keep_regs.tcl
# BEFORE the ORFS memory check (DIE-S81-26 / COORD 10-29 10:41 ruling (a): landing rings are flops by design).  The lint
# applies the same commands, then drops the now-unused ring modules (synth -flatten does the same before mem_dump.py),
# so it measures what synth checks; every other memory keeps the unchanged bound.
LANDING_FF_TCL = r"""yosys select -set ot_lf {*}{*ot_dp_clk_landing*}
yosys flatten {*}{@ot_lf}
yosys memory -nomap {*}{@ot_lf}
yosys memory_map {*}{@ot_lf}
yosys select -clear
yosys hierarchy -top @TOP@
"""


KIT_SNAP_ROOT = re.compile(r"^.*/snaps/[0-9a-f]{40}/root(/.*)$")


def unstage(p, kd):
    """KV-102 r266 11-16: the wave's kit store (KIT-INPUT-STORE-1 / kit_snap) localizes every kit_rtl.f source to
    <W>/kit_inputs/<original abs path>, and a snapshot input further to .../snaps/<sha40>/root/<original abs path>;
    the source-tree check judges the ORIGINAL path, so both staging prefixes are stripped (a path outside them is unchanged)."""
    s = str(p)
    for w in [kd] + list(Path(kd).parents)[:3]:
        ki = str(Path(w).resolve() / "kit_inputs")
        if s.startswith(ki + "/"):
            s = s[len(ki):]
            break
    m = KIT_SNAP_ROOT.match(s)
    return Path(m.group(1)) if m else Path(s)


def kit_rtl_paths(kd):
    """-> (errors, applies): kit_rtl_paths.json (written by gen_phys.write_phys for a --kit-rtl type) names the kit source tree
    and the filelist; every file must resolve inside the source tree, the bind out dir (kit_rtl.json bind_out) or the filelist dir"""
    f = kd / "kit_rtl_paths.json"
    if not f.is_file():
        return [], False
    d = json.loads(f.read_text())
    closure = d.get("input_closure")
    if closure:
        if not closure.get("sealed"):
            return ["kit RTL closure is not sealed after source preparation"], True
        import hashlib
        roots = [Path(r) for r in closure["roots"]]
        errs = []
        files = d.get("files", [])
        if not files:
            return ["kit RTL closure has no source files"], True
        # A copy-back may rewrite .f path prefixes while leaving JSON untouched.
        # Recover only the current package prefix from a unique exact relative
        # manifest path; never infer a new permitted source/bind root.
        first = Path(files[0])
        matches = [Path(k) for k in closure["files"]
                   if str(first).endswith("/" + k) and not Path(k).is_absolute()
                   and ".." not in Path(k).parts]
        if len(matches) != 1:
            return [f"kit RTL closure cannot identify current package root: {first}"], True
        package_root = first.parents[len(matches[0].parts) - 1]
        for x in files:
            p = Path(x)
            try:
                rel = str(p.relative_to(package_root))
            except ValueError:
                errs.append(f"kit RTL closure path outside package: {p}")
                continue
            entry = closure["files"].get(rel)
            if not entry or not any(Path(entry["original"]).is_relative_to(r) for r in roots):
                errs.append(f"kit RTL closure has no permitted origin: {p}")
            elif not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != entry["sha256"]:
                errs.append(f"kit RTL closure content mismatch: {p}")
        checked = {str(Path(x).relative_to(package_root)) for x in files if Path(x).is_relative_to(package_root)}
        for rel, entry in closure["files"].items():
            rp = Path(rel)
            if rp.is_absolute() or ".." in rp.parts:
                errs.append(f"kit RTL closure has an invalid relative metadata path: {rel}")
                continue
            if rel in checked:
                continue
            p = package_root / rp
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != entry["sha256"]:
                errs.append(f"kit RTL closure metadata content mismatch: {p}")
        return errs, True
    roots = [Path(d["src_tree"]).resolve(), Path(d["filelist"]).resolve().parent]
    kj = Path(d["filelist"]).with_name("kit_rtl.json")
    if kj.is_file():
        bo = json.loads(kj.read_text()).get("bind_out")
        if bo:
            roots.append(unstage(Path(bo).resolve(), kd))
    errs = []
    for x in d.get("files", []):
        p = unstage(Path(x).resolve(), kd)
        if not any(p == r or r in p.parents for r in roots):
            errs.append(f"kit_rtl.f source {p} is outside the kit source tree {roots[0]} (bind out / kit-rtl dir allowed)")
    return errs, True


def lint_tcl(cfg, masters=()):
    """LINT_TCL for a kit: + the ot_keep_regs.tcl OT_LANDING_FF ring map when the kit config sets it."""
    on = (cfg.get("OT_LANDING_FF") or ["0"])[-1] == "1" and cfg.get("DESIGN_NAME")
    t = LINT_TCL.replace("@LANDING_FF@", LANDING_FF_TCL.replace("@TOP@", cfg["DESIGN_NAME"][-1]) if on else "")
    return t + (MACRO_COUNT_TCL.replace("@MASTERS@", " ".join(sorted(masters))) if masters else "")


def elab_script(kd, flatten=None):
    """rtl_lint's elaboration (same frontend options, liberties, top params) without its final 'check -assert':
    the tcl driver (LINT_TCL) logs `check`, then memory_collect and one row per $mem_v2 (path, WIDTH, SIZE)."""
    return "\n".join(ln for ln in rtl_lint.script(kd, flatten=flatten).splitlines() if ln.strip() != "check -assert") + "\n"


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
    # FAIL-S81-1 11-14 (COORD, EXPERT-REVIEW-6 #8): OT_LINT_MEMORY_MAX_BITS (die item_env, default 65536) raises the lint
    # bound for behavioural memories the kit synthesises as flops; it never lowers the recipe bound.  Only the memory_bits
    # row is affected: yosys elaboration failures (rtl_check) stay blocking.
    try:
        lim = max(lim, int(os.environ.get("OT_LINT_MEMORY_MAX_BITS") or LINT_MEMORY_MAX_BITS))
    except ValueError:
        pass
    out = []
    for path, w, s in rows:
        if w * s > lim:
            out.append(f"memory {path} {s} x {w} = {w * s} bits > SYNTH_MEMORY_MAX_BITS {lim} (ORFS mem_dump fails "
                       f"synth): set the recipe's synth_memory_max_bits or make it a macro")
    return out


PLATFORM_LIB_DIR = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"


def platform_liberty_tcl(kd, elab_text):
    """KIT-WAVE-8 10-31: rtl_lint.script() globs the ASAP7 platform liberties (SEQ + INVBUF, or every RVT TT lib when a
    source instantiates platform cells) on the host that WRITES the script; the wave runs this lint on a fleet host
    without /OpenROAD-flow-scripts, so those reads were silently empty and every RTL platform-cell instance (ot_hdly
    HB4xp67, ot_hdc_cg ICGx1) failed hierarchy -check.  Re-issue the same reads as a Tcl glob INSIDE the flow image,
    unless the elaboration script already names platform liberties (lint written inside the image)."""
    if "/OpenROAD-flow-scripts/" in elab_text:
        return ""
    if rtl_lint.mapped_cells(rtl_lint._kit_sources(kd)):
        pats = [(rtl_lint.PLATFORM_LIB_GLOB, 0)]
    else:
        pats = [(f"{PLATFORM_LIB_DIR}/asap7sc7p5t_SEQ_RVT_TT_nldm_*.lib*", 1),
                (f"{PLATFORM_LIB_DIR}/asap7sc7p5t_INVBUF_RVT_TT_nldm_*.lib*", 1)]
    lines = []
    for pat, first in pats:
        lines.append(f"set L [lsort [glob -nocomplain {{{pat}}}]]" + ("; set L [lrange $L 0 0]" if first else ""))
        lines.append("foreach f $L { yosys read_liberty -lib -ignore_miss_func $f }")
    return "\n".join(lines) + "\n"


# DIE-QC-61 11-01: memory for the flattened live-design re-check (QC CB kits: the flattened elaboration needs ~14 GB;
# 8 GB OOM-killed it, rc 137)
FLAT_MEM_GB = 16


def run_yosys(kd, image=IMAGE, mem_gb=8, flatten=None):
    """yosys elaboration + check (+ memory census).  Default-on (DIE-QC-61 11-01, same rule as rtl_lint.run): when every
    check problem is an undriven wire, re-check the FLATTENED live design, as ORFS synth sees it -- an undriven output of
    a pruned group that the parent leaves open (QC CB ot_qwen_w12_matvec_part x_addr) disappears, a live undriven net
    still fails."""
    errs, rows, rc = _run_yosys(kd, image, mem_gb, flatten)
    if (flatten is None and not rc and errs and (_cfg(kd).get("OT_RTL_LINT_FLATTEN") or ["0"])[-1] != "1"
            and all(rtl_lint.UNDRIVEN_RE.match(e) for e in errs)):
        errs, rows, rc = _run_yosys(kd, image, max(mem_gb, FLAT_MEM_GB), True)
    return errs, rows, rc


def _run_yosys(kd, image, mem_gb, flatten):
    elab = elab_script(kd, flatten)
    (kd / "gen_lint_elab.ys").write_text(elab)
    tcl = lint_tcl(_cfg(kd), sorted(kv_site_counts(kd) or ()))
    pre = platform_liberty_tcl(kd, elab)
    if pre:
        tcl = tcl.replace("yosys -import\n", "yosys -import\n" + pre, 1)
    (kd / "gen_lint.tcl").write_text(tcl)
    for f in ("gen_lint_check.log", "gen_lint_mem.tsv", "gen_lint_macros.tsv"):
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

    # _rtl/ and other emission scratch dirs are not kits: every existing check
    # can be NA there, which otherwise turns a wrong CLI target into a false PASS.
    # freeze.json stays optional for core kits; config.mk is the physical kit input.
    if not (kd / "config.mk").is_file():
        detail = " (freeze.json is also absent)" if not (kd / "freeze.json").is_file() else ""
        put("kit_vehicle", lambda: (["not a generated kit: missing config.mk" + detail +
                                    "; pass the generated kit directory, not _rtl/"], True))
    put("pins_vs_plan", lambda: pins_vs_plan(kd, plan_dir))
    put("clock_export_form", lambda: clock_export_form(kd))
    put("macro_tcl", lambda: macro_tcl(kd))
    put("kit_rtl_paths", lambda: kit_rtl_paths(kd))
    cfg = _cfg(kd)
    if yosys and cfg.get("DESIGN_NAME"):
        res = {}

        def ys():
            res["r"] = run_yosys(kd, image, mem_gb)
            errs, rows, rc = res["r"]
            return errs, True
        put("rtl_check", ys)
        mt = kd / "gen_lint_macros.tsv"
        measured = ({a: int(b) for a, b in (ln.split("\t") for ln in mt.read_text().splitlines() if ln.strip())}
                    if res.get("r", (None, None, 1))[2] == 0 and mt.is_file() else None)
        put("macro_site_count", lambda: macro_site_count(kd, measured))
        rows = res.get("r", (None, None, 1))[1]
        put("memory_bits", lambda: (memory_errors(rows, cfg), True) if rows is not None
            else (["not measured: yosys elaboration failed (see rtl_check)"], True))
    else:
        checks["rtl_check"] = checks["memory_bits"] = checks["macro_site_count"] = dict(verdict="NA", errors=[], n_errors=0)
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
