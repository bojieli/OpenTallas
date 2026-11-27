#!/usr/bin/env python3
"""KW-RESUME-1 (OWNER 11-01 19:5x "couldn't we restart from the failed position?"): stage resume for kit-wave relaunches.

A class-fix relaunch used to rebuild attempt N+1 from scratch (gen -> kit_rtl -> preflight -> synth -> floorplan -> place
-> cts -> grt -> route -> sign-off).  The new kit is still generated in full (generation is the fingerprint source and
is cheap); this module then decides which ORFS make steps of the previous attempt can be reused unchanged:

  manifest   (on the host holding a kit) hash every kit INPUT file (files gen wrote: K/.kw_inputs.json, or, for kits
             from before this tool, the files not newer than the attempt's gen.log), classify each file to the earliest
             make step that reads it, parse config.mk, and read the checkpoint state of K/run (which steps completed
             and passed).  Writes per-step fingerprints.
  decide     (pure, on the hub) new-kit manifest x old-kit manifest -> S = the first step whose fingerprint differs,
             capped by the first step the old attempt did not complete and by 'route' (route/sign-off is never reused:
             the autopilot refuses a routed kit, and a re-sign of a routed DB is resign.py's kind:resign path).
             Gate / LEC / sign-off scripts are re-run by run_kit.sh on every invocation, so they never force a rebuild;
             if NOTHING differs at all the relaunch is refused (decision 'nochange'), except for INFRA retries.
  apply      (on the new kit's host) link the reused step outputs into K/run: files >= 1 MB are hardlinked, smaller
             files and the boundary checkpoint the next step reads are copied (mtime kept); the old dir is never
             written except for a K/.keep marker this tool removes again (release).  Writes K/resume.json, which
             run_kit.sh (gen_phys RUN_KIT, marker OT_STAGE_RESUME_V1) reads: steps before S are skipped and the later
             steps use the dependency-free ORFS do-* targets (a make dependency check on reused intermediates would
             rebuild them and write through the hardlinks).
  verify     every linked source file still has the size/mtime recorded at apply time (a write through a hardlink
             is detected and the attempt fails FLOW).

Steps: synth < floorplan < place < cts < grt < route.  Any doubt (missing/pruned checkpoint, a log with errors,
non-monotone outputs, a different ORFS image, a runner without the resume marker, unknown file or config variable,
a source on a host we cannot reach) -> full rebuild.  Stdlib only: the same file runs on the hub (import) and on a
fleet host (python3 - <args> < kit_resume.py).
"""
import errno
import hashlib
import json
from math import isfinite
import os
import re
import shutil
import subprocess
import sys
import time

SCHEMA = "opentallas.kw_stage_resume.v1"
STEPS = ("synth", "floorplan", "place", "cts", "grt", "route")
IDX = {s: i for i, s in enumerate(STEPS)}
GATE = "gate"                       # re-run on every run_kit.sh invocation: never forces a rebuild
MARKER = "OT_STAGE_RESUME_V1"       # gen_phys RUN_KIT supports K/resume.json
INPUTS_FILE = ".kw_inputs.json"
RESUME_FILE = "resume.json"
LINK_MIN = 1 << 20                  # smaller files are copied
TEXT_MAX = 4 << 20                  # files scanned for references
SKIP_TOP = {"run", "__pycache__", INPUTS_FILE, RESUME_FILE, ".keep", "resume_src"}

# Final outputs of each step (ORFS results dir).  A step is complete when all exist, are non-empty and are not older
# than the previous step's outputs; it PASSED when its logs carry no error line.
STEP_OUT = {"synth": ("1_2_yosys.v", "1_synth.odb", "1_synth.sdc"),
            "floorplan": ("2_floorplan.odb", "2_floorplan.sdc"),
            "place": ("3_place.odb", "3_place.sdc"),
            "cts": ("4_cts.odb", "4_cts.sdc"),
            "grt": ("5_1_grt.odb",)}
STEP_LOGS = {"synth": ("1_2_yosys.log", "1_synth.log"),
             "floorplan": ("2_1_floorplan.log", "2_4_floorplan_pdn.log"),
             "place": ("3_3_place_gp.log", "3_5_place_dp.log"),
             "cts": ("4_1_cts.log",),
             "grt": ("5_1_grt.log",)}
# FLOW-24 11-03: HOLD-GUARD-GRT ends each buffer-capped hold chunk on a caught RSZ-0060 (OpenROAD still logs it as
# [ERROR RSZ-0060]); the guard prints its "OT_HOLD_GUARD_GRT chunk N" line right after and continues.  That caught
# cap is not a crash; an RSZ-0060 the guard did not catch has no chunk line after it and still counts.
HOLD_GUARD_CAP_RE = re.compile(r"^\[ERROR RSZ-0060\][^\n]*\n(?=(?:[^\n]*\n){0,4}OT_HOLD_GUARD_GRT chunk \d+:)", re.M)
ERR_LINE = re.compile(r"^(?:\[ERROR|ERROR:|Error:)", re.M)


def grt_terminal_dpl(text):
    """Use a final global-route placement failure after a proven caught buffer cap."""
    first = ERR_LINE.search(text)
    if not first or not HOLD_GUARD_CAP_RE.match(text, first.start()):
        return ""
    dpl = re.search(r"(?m)^(\[ERROR DPL-0033\][^\n]*)\nError: global_route\.tcl, \d+ DPL-0033$", text[first.start():])
    if not dpl:
        return ""
    start = first.start()
    prior = HOLD_GUARD_CAP_RE.sub("", text[start:start + dpl.start()])
    if (ERR_LINE.search(prior) or ERR_LINE.search(text[start + dpl.end():])
            or "OT_HOLD_GUARD_GRT: chunk buffer caps reached (RSZ-0060 caught per chunk); continuing on the repaired design" not in prior):
        return ""
    return dpl[1]

# run_kit.sh (gen_phys RUN_KIT) itself reads these kit files.  Producers: the make step whose output they change.
RUNNER_ROOTS = {"orfs_hold_mm.py": "synth", "native_bb.py": "synth", "partition_ir.py": "synth",
                "adder_map_dontuse.py": "synth", "signed_parent_source.json": "synth",
                "signed_parent_synth_prep.sh": "synth", "tapbal_grt.tcl": "cts", "macro_ff_repair.mk": "grt"}
# Gates / proofs / sign-off: re-run by run_kit.sh on every invocation (their verdicts are never reused).
GATE_ROOTS = {"PROVENANCE.json", "PROVENANCE.generated.json", "type_overlay.json", "LEC_TOOL.json", "kit_preflight.py", "sdc_lint.py", "rtl_lint.py", "rtl_lint.ys", "selrange_gate.py", "port_bind_gate.py",
              "face_guard.py", "reg_fanout_gate.py", "hold_gate.tcl", "postcts_gate.tcl", "legacy_gate.py",
              "grt_policy.json", "pin_audit.py", "native_pin_contract.py", "audit_pins.json", "lec.py", "lec_async.sh", "lec_completed_transfer.py", "lec_options.json",
              "lec_async.on", "lec_async.identity", "signoff.py", "lec_options.json", "straps.json",
              "grt183_make.sh", "grt183_resume.tcl"}      # FLOW-28: inert unless a run stops on GRT-0183; a kit with no such stop rebuilds nothing
# KW-FIX-24/LEAFREP 11-06: grt183_make.sh (a gate root) sources clk_leaf_repeat_default.tcl inside the CTS and GRT
# steps (clock-tree repeaters): a physical input read at cts, not a gate
RUNNER_ROOTS["clk_leaf_repeat_default.tcl"] = "cts"
# KW-FIX-25/AUTORENDER 11-06: advisory renders, read stage ODBs only and write run/layout_review; no stage output depends on them
GATE_ROOTS |= {"layout_render_hook.sh", "layout_render.tcl", "layout_smells.py"}
GATE_ROOTS |= {"failfast_rules.py"}   # FAILFAST-1 11-11: stops a run on progress; inert unless a rule fires
GATE_ROOTS |= {"kit_reports.py", "stage_odb_cap.py", "kit_resume.py"}   # FLOW-FIX-2045: helpers the wave ships into every kit (report quarantine, ODB cap, this file): no stage output depends on them
GATE_ROOTS |= {"grt_stall_resume.tcl"}   # KW-FIX-17 11-05 GRT-STALL: inert unless a 5_1_grt stage stalls in -end_incremental
# The pre-GRT hold hook replaces 4_cts.odb. Changing the hook or its settings must rebuild
# CTS so removing or narrowing a repair starts from the original clock tree.
RUNNER_ROOTS["pregrt_ff_hold.tcl"] = "cts"
# run_kit.sh reads these config variables itself (outside the ORFS make steps)
RUNNER_VARS = {
    "OT_HOLD_FF_MARGIN": "grt",
    "OT_TAP_GRT_PRE": "cts",
    "OT_PINREG_PAD": "cts",
    "OT_TAP_GRT_PRE_ITERS": "cts",
    "OT_PINREG_PAD_CELL": "cts",
    "OT_PINREG_PAD_ITERS": "cts",
    "OT_PINREG_PAD_STEP": "cts",
    "OT_PINREG_PAD_TOL": "cts",
    "OT_PREGRT_FF_HOLD": "cts",
    "OT_PREGRT_HOLD_GUARD": "cts",
    "OT_PREGRT_HOLD_PORT_MARGIN": "cts",
    "OT_PREGRT_HOLD_R2R_MARGIN": "cts",
    "OT_PREGRT_HOLD_R2R_CHUNK_BUFS": "cts",
    "OT_PREGRT_SKIP_SETUP_PS": "cts",
}
# ORFS variables first read after synthesis (anything else: synth, i.e. a full rebuild)
VAR_STAGE = {}
for _s, _vs in (("floorplan", "DIE_AREA CORE_AREA CORE_UTILIZATION CORE_ASPECT_RATIO CORE_MARGIN IO_CONSTRAINTS PDN_TCL "
                              "MACRO_PLACEMENT_TCL MACRO_PLACEMENT PRE_FLOORPLAN_TCL POST_FLOORPLAN_TCL TAPCELL_TCL "
                              "MACRO_PLACE_HALO MACRO_PLACE_CHANNEL FOOTPRINT_TCL MAKE_TRACKS IO_PLACER_H IO_PLACER_V "
                              "PLACE_PINS_ARGS"),
                ("place", "PLACE_DENSITY PLACE_DENSITY_LB_ADDON GPL_TIMING_DRIVEN GPL_ROUTABILITY_DRIVEN "
                          "MIN_PLACE_STEP_COEF MAX_PLACE_STEP_COEF CELL_PAD_IN_SITES_GLOBAL_PLACEMENT "
                          "PRE_GLOBAL_PLACE_TCL POST_GLOBAL_PLACE_TCL PRE_DETAIL_PLACE_TCL POST_DETAIL_PLACE_TCL "
                          "PRE_RESIZE_TCL POST_RESIZE_TCL PRE_IO_PLACEMENT_TCL POST_IO_PLACEMENT_TCL GPL_KEEP_OVERFLOW"),
                ("cts", "PRE_CTS_TCL POST_CTS_TCL CTS_BUF_DISTANCE CTS_CLUSTER_SIZE CTS_CLUSTER_DIAMETER CTS_BUF_LIST "
                        "CTS_LIB_NAME CTS_ARGS"),
                ("grt", "PRE_GLOBAL_ROUTE_TCL POST_GLOBAL_ROUTE_TCL FASTROUTE_TCL ROUTING_LAYER_ADJUSTMENT "
                        "GLOBAL_ROUTE_ARGS MAX_REPAIR_ANTENNAS_ITER_GRT SKIP_ANTENNA_REPAIR_PRE_GRT OT_PG_TRACK_TRUTH "
                        "OT_PG_CELL_KEEPOUT OT_PG_CELL_KEEPOUT_MARGIN_UM OT_PG_CELL_KEEPOUT_DPL_ARGS"),
                ("route", "PRE_DETAIL_ROUTE_TCL POST_DETAIL_ROUTE_TCL DETAILED_ROUTE_ARGS DETAILED_ROUTE_END_ITERATION "
                          "MAX_REPAIR_ANTENNAS_ITER_DRT SKIP_ANTENNA_REPAIR_POST_DRT PRE_FILLCELL_TCL "
                          "POST_FILLCELL_TCL")):
    for _v in _vs.split():
        VAR_STAGE[_v] = _s


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def runner_norm(text):
    """the runner without its stage-resume edits (gen_phys RUN_KIT: '# KWRS' lines, the
    '# KWRS-BEGIN' .. '# KWRS-END' block and ${KWRS_*} tokens), so a runner
    that only gained stage resume compares equal to the one that built the previous attempt"""
    keep, skip = [], False
    for ln in text.splitlines(True):
        r = ln.rstrip()
        if r.endswith("# KWRS-BEGIN"):
            skip = True
        if not skip and not r.endswith("# KWRS"):
            keep.append(ln)
        if r.endswith("# KWRS-END"):
            skip = False
    t = "".join(keep)
    t = re.sub(r"\$\{KWRS_\w+:-([^}]*)\}", r"\1", t)
    return re.sub(r"\$\{KWRS_\w+\}", "", t)


def adapt_type_runner(text, template):
    """Add only the pinned resume harness to a recognized old TYPE runner.

    Normalized old physical commands and gates must remain byte-identical.
    Unknown/core runners retain the existing full rebuild fallback.
    """
    if MARKER in text:
        return text, "already supports resume"
    anchor = re.findall(r"^NAME=dpkit-.*\n", text, re.M)
    make = re.compile(r"(  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=\$CPUS'; )rc=0;")
    if len(anchor) != 1 or len(make.findall(text)) != 1:
        return text, "unrecognized runner; normal full rebuild/ECO fallback"
    start = template.index("# KW-RESUME-1 OT_STAGE_RESUME_V1")
    end = template.index("fi  # KWRS", start) + len("fi  # KWRS")
    harness = template[start:end] + "\n"
    adapted = text.replace(anchor[0], anchor[0] + harness, 1)
    adapted = make.sub(lambda m: m.group(1) + "${KWRS_M}rc=0;", adapted, count=1)
    if runner_norm(adapted) != runner_norm(text):
        raise ValueError("resume harness changed normalized physical runner")
    return adapted, "resume harness only; normalized physical commands and gates identical"


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def minstage(a, b):
    """earliest of two categories (a step name, GATE or None); a step always wins over GATE"""
    if a is None or a == GATE:
        return b if b is not None else a
    if b is None or b == GATE:
        return a
    return a if IDX[a] <= IDX[b] else b


# ------------------------------------------------------------------------------------------------ kit side
def parse_config(text):
    """config.mk -> {VAR: value}; a line that is not a plain assignment is kept as '__line__<text>' (-> synth)"""
    out = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(?:override\s+)?(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\?|:|\+)?=\s*(.*)$", s)
        if m:
            k = m.group(1)
            out[k] = (out[k] + "\n" + m.group(2)) if k in out else m.group(2)
        else:
            out["__line__" + s] = ""
    return out


def input_files(K, cutoff=None):
    """kit input files (rel paths): K/.kw_inputs.json when gen recorded it, else files not newer than cutoff"""
    rec = os.path.join(K, INPUTS_FILE)
    if os.path.isfile(rec):
        try:
            d = _load(rec)
            return sorted(d["files"]), "recorded"
        except (OSError, ValueError, KeyError):
            pass
    out = []
    for root, dirs, files in os.walk(K):
        rel_root = os.path.relpath(root, K)
        if rel_root == ".":
            dirs[:] = [d for d in dirs if d not in SKIP_TOP]
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            rel = os.path.normpath(os.path.join(rel_root, f))
            if rel in SKIP_TOP:
                continue
            p = os.path.join(root, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            if cutoff is not None and os.path.getmtime(p) > cutoff + 2:
                continue
            out.append(rel)
    return sorted(out), ("mtime<=gen_end" if cutoff is not None else "all")


LANDING_CONTRACT = "landing_contract.json"


def _names(rel):
    b = os.path.basename(rel)
    out = {b}
    # SDC annotations use the landing_contract namespace without reading the JSON file.
    if rel == LANDING_CONTRACT:
        return out
    stem, ext = os.path.splitext(b)
    if ext in (".py", ".tcl", ".sh", ".mk", ".json", ".v", ".sv", ".svh", ".lef", ".lib", ".txt") and \
            (len(stem) >= 6 or "_" in stem):
        out.add(stem)
    return out


FLOW_REFRESH_LOG = "flow_refresh.jsonl"


def flow_refresh_audit_only(text):
    """A normal refresh audit changes no stage inputs itself; runner overrides can."""
    try:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except (ValueError, AttributeError):
        return False
    return bool(rows) and all(isinstance(row, dict) and row.get("stage") and isinstance(row.get("replaced"), list)
                              and not row.get("runner_override") and not row.get("partial") for row in rows)


def classify(texts, files, config, *, early_readers=None):
    """{rel: step | GATE} -- the earliest make step that reads each kit input file.

    Roots: config.mk hook variables (VAR_STAGE; any other variable whose value names a file -> synth), the files
    run_kit.sh reads (RUNNER_ROOTS / GATE_ROOTS).  Propagation: a file named (basename, or module/proc stem) in the
    text of a producer of step s is read at s at the latest.  A file named only by gates is gate-only.  A file nobody
    names is assumed to be read at synth (conservative: a full rebuild when it changes)."""
    stage = {}
    gate_ref = set()
    for rel in files:
        if rel in RUNNER_ROOTS:
            stage[rel] = RUNNER_ROOTS[rel]
        elif is_gate_root(rel) or (rel == FLOW_REFRESH_LOG and flow_refresh_audit_only(texts.get(rel, ""))):
            stage[rel] = GATE
    for var, val in config.items():
        vs = VAR_STAGE.get(var, "synth")
        for m in re.finditer(r"/work/([^\s'\"]+)", var + " " + val):
            rel = os.path.normpath(m.group(1))
            if var == "OT_FT_POLARITY_LOCAL_SITES" and rel == "ft_polarity_local_sites.tsv" and val == f"/work/{rel}":
                # Below, infer the first reader from the executable hook, as with a literal path.
                continue
            if rel in files and not is_gate_root(rel):
                cur = stage.get(rel)
                stage[rel] = vs if cur in (None, GATE) else minstage(cur, vs)
    # STAGE-PLATEAU 11-25 (HEAD-OBSGC: valid cts checkpoints discarded): a Tcl file nobody names was assumed read at synth, and that synth guess then propagated to every file it names
    # (hold_repair_pre.tcl -> grt_pre.tcl -> grt_layers / hold_guard_grt / obs_gcell_cap / grt_clock_first: 14 grt-time hooks of kits2/hostw/hd_host_w were 'synth', so editing one
    # re-ran floorplan).  A file whose basename carries the grt / hold token is read at grt at the latest (pre-GRT hold build and GRT hooks); a producer that really names it earlier
    # still lowers it (minstage), so only the unnamed-file default changes.
    for rel in files:
        if rel not in stage and rel.endswith(".tcl") and GRT_HINT_RE.search(os.path.basename(rel)):
            stage[rel] = "grt"
    by_name = {}
    for rel in files:
        for n in _names(rel):
            by_name.setdefault(n, set()).add(rel)
    big = re.compile(r"(?<![\w.])(%s)(?![\w])" % "|".join(re.escape(n) for n in sorted(by_name, key=len, reverse=True))) \
        if by_name else None
    named = {}                                          # src -> {rel named in its text}
    for src, txt in texts.items():
        if src == FLOW_REFRESH_LOG:
            continue  # the audit names observed kit files; it does not consume them
        # QC-HC-KWRS 11-08: full-line Tcl comments describe other stages (e.g. face_keep's reset_taps note).
        # They are not reads. Keep executable lines, inline comments and unknown files conservative.
        if src.endswith(".tcl"):
            txt = "\n".join(line for line in txt.splitlines() if not line.lstrip().startswith("#"))
        # FLOW-OPS-R3 11-24 (QC STB dff1e9a2ad86): HDL text reads other files only through string literals
        # (`include "x.svh", $readmemh("x.hex")).  Identifiers and comments that happen to equal a hook stem
        # (clock_taps, tap_reset_split) are not reads, and classing those hooks synth forced full reruns.
        elif src.endswith(HDL_EXT):
            txt = "\n".join(HDL_STR_RE.findall(txt))
        if txt and big is not None:
            named[src] = set().union(*[by_name[n] for n in set(big.findall(txt))]) if txt else set()
    ft_sites = "ft_polarity_local_sites.tsv"
    ft_hook = "ft_polarity_local.tcl"
    if (config.get("OT_FT_POLARITY_LOCAL_SITES") == f"/work/{ft_sites}" and ft_sites in files
            and re.search(r"(?m)^[^#\n]*\$::env\(OT_FT_POLARITY_LOCAL_SITES\)", texts.get(ft_hook, ""))):
        named.setdefault(ft_hook, set()).add(ft_sites)
    gate_named = set()
    changed = True
    while changed:
        changed = False
        for src, refs in named.items():
            s = stage.get(src)
            if s is None:
                continue
            for rel in refs:
                if rel == src:
                    continue
                if s == GATE:
                    gate_named.add(rel)
                    continue
                if is_gate_root(rel):
                    continue
                cur = stage.get(rel)
                new = s if cur in (None, GATE) else minstage(cur, s)
                if new != cur:
                    stage[rel] = new
                    changed = True
        for rel in gate_named:
            if rel not in stage:
                stage[rel] = GATE
                changed = True
    if early_readers is not None:
        early_readers.update(rel for rel, step in stage.items() if step in ("synth", "floorplan"))
    for rel in files:
        stage.setdefault(rel, "synth")
    return stage


GRT_HINT_RE = re.compile(r"(?:^|_)(?:grt|hold)(?:_|\.)")
HDL_EXT = (".v", ".sv", ".svh", ".vh")
HDL_STR_RE = re.compile(r'"([^"\n]*)"')


def is_gate_root(rel):
    """a top-level gate root keeps GATE even when a producer names it (run_kit.sh runs it as a gate)"""
    return os.path.dirname(rel) == "" and os.path.basename(rel) in GATE_ROOTS


def config_var_stages(config, texts, stage):
    """{VAR: step | GATE}.  An ORFS variable: VAR_STAGE (else synth), lowered by every kit producer naming it.
    An OT_* kit variable (only kit scripts read it): RUNNER_VARS / the earliest producer naming it; named by gates
    only -> GATE; named by nobody -> synth."""
    out = {}
    for var in config:
        if var.startswith("__line__"):
            out[var] = "synth"
            continue
        custom = var.startswith("OT_")
        s = RUNNER_VARS.get(var) if custom else VAR_STAGE.get(var, "synth")
        pat = re.compile(r"(?<![\w])%s(?![\w])" % re.escape(var))
        named_gate = False
        for src, txt in texts.items():
            if not txt or not pat.search(txt):
                continue
            ss = stage.get(src)
            if ss == GATE:
                named_gate = True
            elif ss is not None:
                s = minstage(s, ss)
        out[var] = s if s is not None else (GATE if named_gate else "synth")
    return out


def edge_sha(p):
    """FLEET-OPS 11-25: content identity of a (possibly multi-GB) step output that survives a copy: sha256 of the size and the first and last 1 MiB"""
    import hashlib
    h = hashlib.sha256()
    n = os.path.getsize(p)
    h.update(str(n).encode())
    with open(p, "rb") as f:
        h.update(f.read(1 << 20))
        if n > (2 << 20):
            f.seek(n - (1 << 20))
            h.update(f.read(1 << 20))
    return h.hexdigest()


def ck_identity(K, ck):
    """{step: {output name: [size, edge_sha]}} of the complete and passed steps of checkpoint(K): the copy-proof identity of a reusable checkpoint"""
    out = {}
    if not ck.get("base"):
        return out
    B = os.path.join(K, ck["base"])
    for s in STEPS[:-1]:
        st = ck["steps"].get(s) or {}
        if not (st.get("complete") and st.get("passed")):
            break
        try:
            out[s] = {n: [os.path.getsize(os.path.join(B, n)), edge_sha(os.path.join(B, n))] for n in st["outputs"]}
        except OSError:
            break
    return out


def checkpoint(K, ident=None):
    """state of K/run: {base, steps: {step: {complete, passed, outputs{name: [size, mtime]}, why}}, upto}.
    ident = ck_identity() recorded in an earlier resume plan: a step whose outputs still have that content is in order whatever a copy did to the mtimes"""
    import glob
    bases = sorted(glob.glob(os.path.join(K, "run", "results", "asap7", "*", "base")))
    out = {"base": None, "steps": {}, "upto": None}
    if len(bases) != 1:
        out["why"] = f"{len(bases)} ORFS results dirs"
        return out
    B = bases[0]
    L = B.replace(os.sep + "results" + os.sep, os.sep + "logs" + os.sep, 1)
    out["base"] = os.path.relpath(B, K)
    prev_t = 0.0
    for s in STEPS[:-1]:
        st = {"outputs": {}, "complete": False, "passed": False}
        miss = [n for n in STEP_OUT[s] if not os.path.isfile(os.path.join(B, n)) or os.path.getsize(os.path.join(B, n)) == 0]
        for n in STEP_OUT[s]:
            p = os.path.join(B, n)
            if os.path.isfile(p):
                st["outputs"][n] = [os.path.getsize(p), os.path.getmtime(p)]
        if miss:
            st["why"] = "missing/empty " + ",".join(miss)
        else:
            t0 = min(v[1] for v in st["outputs"].values())
            t1 = max(v[1] for v in st["outputs"].values())
            same_content = bool(ident and ident.get(s)) and all(
                n in st["outputs"] and ident[s][n] == [st["outputs"][n][0], edge_sha(os.path.join(B, n))] for n in ident[s])
            if t0 + 1 < prev_t and not same_content:
                st["why"] = "outputs older than the previous step (stale / out of order)"
            else:
                st["complete"] = True
                bad = []
                for lg in STEP_LOGS[s]:
                    p = os.path.join(L, lg)
                    if not os.path.isfile(p):
                        bad.append(f"{lg} missing")
                        continue
                    with open(p, errors="replace") as f:
                        m = ERR_LINE.search(HOLD_GUARD_CAP_RE.sub("", f.read()))
                    if m:
                        bad.append(f"{lg} has an error line")
                st["passed"] = not bad
                if bad:
                    st["why"] = "; ".join(bad)
                st["end"] = t1
                prev_t = t1
        out["steps"][s] = st
        if not (st["complete"] and st["passed"]):
            break
        out["upto"] = s
    return out


def image_info(image):
    try:
        p = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}} {{.Created}}", image], capture_output=True,
                           text=True, timeout=60)
        if p.returncode == 0 and p.stdout.strip():
            i, c = p.stdout.split()[:2]
            return {"image": image, "id": i, "created": c}
    except (OSError, subprocess.SubprocessError):
        pass
    return {"image": image, "id": None, "created": None}


def sender_budget_fingerprints(text):
    """Keep the exact parent release identity separate from physical inputs."""
    try:
        budget = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(budget, dict) or budget.get("schema") != "opentallas.die_plan.partition_budget.v1":
        return {}
    hold = budget.get("io_hold")
    if not isinstance(hold, dict) or hold.get("mode") != "sender_min" or hold.get("requires_parent") is not True:
        return {}
    plan = hold.get("plan_sha256")
    if not isinstance(plan, str) or re.fullmatch(r"[0-9a-f]{64}", plan) is None:
        return {}
    del hold["plan_sha256"]
    return {"physical_sha256": H(budget), "parent_plan_sha256": plan}


def topology_fingerprints(text, kit, files):
    """A generated audit's work path can move with its identical bound RTL."""
    try:
        audit = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(audit, dict) or audit.get("schema") != "opentallas.kit_topology.v1":
        return {}
    source, digest = audit.get("source"), audit.get("source_sha256")
    if not isinstance(source, str) or not isinstance(digest, str):
        return {}
    name = os.path.basename(source)
    rel = os.path.join("rtl", name)
    generated = os.path.join(os.path.dirname(os.path.dirname(kit)), rel)
    bound = files.get(rel, {})
    if (source != generated or not name.endswith("_bound.sv")
            or bound.get("stage") != "synth" or bound.get("sha256") != digest):
        return {}
    audit["source"] = rel
    return {"physical_sha256": H(audit)}


def landing_contract_fingerprints(text):
    """Split only generated native seat rows and single fixed-flop band rectangles.

    All other metadata, including the presence of the typed keys, remains in the
    earlier-stage identity. The emitted placement Tcl has its own fingerprint.
    """
    try:
        contract = json.loads(text)
    except (ValueError, TypeError):
        return {}
    if not isinstance(contract, dict):
        return {}

    def rectangle(rect):
        return (isinstance(rect, list) and len(rect) == 4
                and all(type(v) is int or (type(v) is float and isfinite(v)) for v in rect)
                and rect[0] < rect[2] and rect[1] < rect[3])

    def nonempty(value):
        return isinstance(value, str) and bool(value)

    placement = {}
    if "native_stage_groups" in contract:
        native = contract["native_stage_groups"]
        if not isinstance(native, dict):
            return {}
        version = native.get("schema")
        if version == "opentallas.native_stage_groups.v1" and set(native) == {"schema", "content", "module", "params", "groups"}:
            owners = [{key: native[key] for key in ("content", "module", "params")}]
        elif version == "opentallas.native_stage_groups.v2" and set(native) == {"schema", "contents", "groups"}:
            owners = native["contents"]
        else:
            return {}
        if not isinstance(owners, list) or not owners or any(
            not isinstance(owner, dict) or set(owner) != {"content", "module", "params"}
            or not nonempty(owner["content"]) or not nonempty(owner["module"]) or not isinstance(owner["params"], dict)
            for owner in owners
        ):
            return {}
        rows = native["groups"]
        if not isinstance(rows, list) or not rows or any(
            not isinstance(row, dict) or not {"prefix", "rect_um", "tag"} <= row.keys()
            or row.keys() - {"prefix", "rect_um", "tag", "density", "match"}
            or not nonempty(row["prefix"]) or not nonempty(row["tag"]) or not rectangle(row["rect_um"])
            or row.get("match", "prefix") not in ("prefix", "cell")
            or ("density" in row and (row.get("match") != "cell" or type(row["density"]) not in (int, float)
                                      or not 0.4 <= row["density"] <= 0.6))
            for row in rows
        ):
            return {}
        placement["native_stage_groups"] = rows
        native["groups"] = None

    bands = contract.get("bands", {})
    if not isinstance(bands, dict):
        return {}
    band_rects = {}
    for name, band in bands.items():
        if not isinstance(band, dict):
            return {}
        if ("rect_um" not in band or "rects_um" in band or band.get("ring_place") != "ff"
                or type(band.get("width")) is not int or band["width"] <= 0
                or not isinstance(band.get("instance"), str) or not band["instance"].startswith("u_cland_")):
            continue
        if not rectangle(band["rect_um"]):
            return {}
        band_rects[name] = band["rect_um"]
        band["rect_um"] = None
    if band_rects:
        placement["bands"] = band_rects
    if not placement:
        return {}
    return {"landing_early_sha256": H(contract), "landing_place_sha256": H(placement)}


def manifest(K, cutoff=None, runner=None, image="openroad/orfs:asap7lock", with_checkpoint=True):
    """everything decide() needs about one kit, computed on its host"""
    K = os.path.abspath(K)
    if not os.path.isfile(os.path.join(K, "config.mk")):
        return {"schema": SCHEMA, "kit": K, "error": "no config.mk"}
    files, basis = input_files(K, cutoff)
    sha, texts = {}, {}
    for rel in files:
        p = os.path.join(K, rel)
        try:
            sha[rel] = sha256_file(p)
            if os.path.getsize(p) <= TEXT_MAX:
                with open(p, "rb") as f:
                    b = f.read()
                if b"\0" not in b[:8192]:
                    texts[rel] = b.decode(errors="replace")
        except OSError:
            sha[rel] = None
    runner = runner or os.path.join(os.path.dirname(K), "run_kit.sh")
    rtext = ""
    if os.path.isfile(runner):
        with open(runner, errors="replace") as f:
            rtext = f.read()
        texts["<runner>"] = rtext
    config = parse_config(texts.get("config.mk", ""))
    kit_texts = {k: v for k, v in texts.items() if k not in ("<runner>", "config.mk")}   # hooks / RUNNER_* tables
    early_readers = set()
    stage = classify(kit_texts, files, config, early_readers=early_readers)
    vstage = config_var_stages(config, kit_texts, stage)
    m = {"schema": SCHEMA, "kit": K, "host": os.uname().nodename, "basis": basis, "cutoff": cutoff,
         "files": {rel: {"sha256": sha[rel], "stage": stage[rel]} for rel in files},
         "config": {k: {"value": v, "stage": vstage[k]} for k, v in config.items()},
         "runner": {"path": runner, "sha256_raw": hashlib.sha256(rtext.encode()).hexdigest() if rtext else None,
                    "sha256": hashlib.sha256(runner_norm(rtext).encode()).hexdigest() if rtext else None,
                    "resume_capable": MARKER in rtext},
         "image": image_info(image)}
    if "budget.json" in m["files"]:
        m["files"]["budget.json"].update(sender_budget_fingerprints(texts.get("budget.json", "")))
    topology = m["files"].get("kit_topology.json")
    if topology and "kit_topology.json" not in early_readers:
        topology.update(topology_fingerprints(texts.get("kit_topology.json", ""), K, m["files"]))
    if LANDING_CONTRACT in m["files"]:
        landing = m["files"][LANDING_CONTRACT]
        landing["stage"] = "synth"  # earlier metadata stays a full-rebuild input
        if LANDING_CONTRACT not in early_readers:
            landing.update(landing_contract_fingerprints(texts.get(LANDING_CONTRACT, "")))
    m["fingerprints"] = fingerprints(m)
    if with_checkpoint:
        m["checkpoint"] = checkpoint(K)
        m["run_files"] = run_tree(K)
    return m


def fingerprints(m):
    """per-step input fingerprint: sha256 over the (file, sha) and (var, value) items first read at that step;
    synth also carries the runner and the ORFS image; 'gate' = gates / LEC / sign-off scripts"""
    items = {s: [] for s in STEPS + (GATE,)}
    for rel, f in m["files"].items():
        if rel == "config.mk":
            continue                                    # its variables are items of their own steps
        early = f.get("landing_early_sha256", f.get("physical_sha256", f["sha256"]))
        items[f["stage"]].append(["file", rel, early])
        if "landing_place_sha256" in f:
            items["place"].append(["landing-seats", rel, f["landing_place_sha256"]])
        if "parent_plan_sha256" in f:
            items[GATE].append(["parent-plan", rel, f["parent_plan_sha256"]])
    for k, v in m["config"].items():
        items[v["stage"]].append(["var", k, v["value"]])
    items["synth"] += [["runner", m["runner"]["sha256"]], ["image", (m.get("image") or {}).get("id")]]
    return {s: H(sorted(v)) for s, v in items.items()}


def write_inputs(K):
    """right after gen: record the kit's input files + hashes (K/.kw_inputs.json, the record later relaunches use)"""
    files, _ = input_files(K, None)
    rec = {"schema": SCHEMA, "written": time.time(), "files": {r: sha256_file(os.path.join(K, r)) for r in files}}
    tmp = os.path.join(K, INPUTS_FILE + ".tmp")
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=0)
    os.replace(tmp, os.path.join(K, INPUTS_FILE))
    return rec


# ------------------------------------------------------------------------------------------------ hub side (pure)
def saved_stage_semantics_usable(new, saved):
    """Older cached manifests need normal inspection only for changed, newly modeled inputs."""
    for rel in ("budget.json", "kit_topology.json", FLOW_REFRESH_LOG, LANDING_CONTRACT, "ft_polarity_local_sites.tsv"):
        a, b = new["files"].get(rel), saved["files"].get(rel)
        if not a or not b or a["sha256"] == b["sha256"]:
            continue
        if any(a.get(key) and not b.get(key) for key in ("physical_sha256", "landing_place_sha256")):
            return False
        if rel == FLOW_REFRESH_LOG and a["stage"] == GATE and b["stage"] != GATE:
            return False
        if rel == "ft_polarity_local_sites.tsv" and a["stage"] != b["stage"]:
            return False
    return True


def changed_items(new, old):
    """[(category, kind, name)] of every input that differs between the two kit manifests"""
    out = []
    for rel in sorted(set(new["files"]) | set(old["files"])):
        if rel == "config.mk":
            continue                                    # compared per variable below
        a, b = new["files"].get(rel), old["files"].get(rel)
        if a and b and a["sha256"] == b["sha256"] and a["sha256"] is not None:
            continue
        if rel == LANDING_CONTRACT:
            place_only = (a and b and a.get("landing_early_sha256") and a["landing_early_sha256"] == b.get("landing_early_sha256")
                          and a.get("landing_place_sha256") and b.get("landing_place_sha256")
                          and a["landing_place_sha256"] != b["landing_place_sha256"])
            out.append(("place" if place_only else "synth", "file", rel))
            continue
        if a and b and a.get("physical_sha256") and a["physical_sha256"] == b.get("physical_sha256"):
            out.append((GATE, "file", rel))
            continue
        out.append((minstage(a and a["stage"], b and b["stage"]), "file", rel))
    for k in sorted(set(new["config"]) | set(old["config"])):
        a, b = new["config"].get(k), old["config"].get(k)
        if a and b and a["value"] == b["value"]:
            continue
        out.append((minstage(a and a["stage"], b and b["stage"]), "var", k))
    if not new["runner"]["sha256"] or new["runner"]["sha256"] != old["runner"]["sha256"]:
        out.append(("synth", "runner", new["runner"]["path"]))
    ni, oi = (new.get("image") or {}).get("id"), (old.get("image") or {}).get("id")
    if not ni or ni != oi:
        out.append(("synth", "image", f"{oi} -> {ni}"))
    return out


def _iso_ts(s):
    """docker Created (RFC3339, ns) -> epoch s"""
    import datetime as dt
    try:
        s = re.sub(r"\.(\d{6})\d*", r".\1", s.replace("Z", "+00:00"))
        return dt.datetime.fromisoformat(s).timestamp()
    except (ValueError, AttributeError):
        return None


def decide(new, old, allow_nochange=False, latest_start=None):
    """-> decision dict {decision: resume|full|nochange, start, reuse[], why, changed[], fingerprints}"""
    d = {"schema": SCHEMA, "decision": "full", "start": "synth", "reuse": [], "why": "", "changed": []}
    for m, w in ((new, "new"), (old, "old")):
        if not isinstance(m, dict) or m.get("error"):
            d["why"] = f"{w} kit manifest: {(m or {}).get('error', 'missing')}"
            return d
    ch = changed_items(new, old)
    d["changed"] = [list(c) for c in ch]
    d["fingerprints"] = {"new": new.get("fingerprints"), "old": old.get("fingerprints")}
    if not ch:
        if not allow_nochange:
            d.update(decision="nochange", why="every kit input, config variable, runner and image equals the previous "
                                              "attempt: the relaunch would repeat the same run")
            return d
    s_fp = "route"
    for cat, _, _ in ch:
        if cat != GATE:
            s_fp = minstage(s_fp, cat)
    ck = old.get("checkpoint") or {}
    upto = ck.get("upto")
    s_ck = STEPS[IDX[upto] + 1] if upto else "synth"
    start = minstage(s_fp, s_ck)
    if latest_start is not None:
        start = minstage(start, latest_start)
    d["start_fingerprint"], d["start_checkpoint"] = s_fp, s_ck
    if start == "synth":
        why = []
        if s_fp == "synth":
            why.append("synth inputs changed: " + ", ".join(f"{k} {n}" for c, k, n in ch if c == "synth")[:300])
        if s_ck == "synth":
            st = (ck.get("steps") or {}).get("synth") or {}
            why.append("no reusable synth checkpoint (" + (st.get("why") or ck.get("why") or "none") + ")")
        d["why"] = "; ".join(why)
        return d
    if not new["runner"].get("resume_capable"):
        d["why"] = f"runner {new['runner'].get('path')} has no {MARKER} support (core / KV / HBM runners rebuild)"
        return d
    created = _iso_ts((new.get("image") or {}).get("created") or "")
    first = min((v[1] for st in (ck.get("steps") or {}).values() for v in (st.get("outputs") or {}).values()), default=0)
    if created is None or created >= first:
        d["why"] = "ORFS image created after (or unknown vs) the old checkpoint: cannot prove the same tools"
        return d
    d.update(decision="resume", start=start, reuse=list(STEPS[:IDX[start]]),
             why=f"first changed step {s_fp}, old attempt complete through {upto}"
                 + (f", restart no later than {latest_start}" if latest_start else ""))
    return d


KWRS_MARKER = ".kwrs_done."           # run_kit.sh stage-resume step markers (/work/.kwrs_done.$PPID)


AUTO_SKIP_RE = re.compile(r"(\.log|\.jsonl|\.tmp|\.new)$|^(FAIL_|DONE|PASS_|GATE_|\.kwrs|kwrs_|stale_reports/|stage_odb_|tools_rev|flow_refresh|KIT_FORK|\.kit_resume_inputs|resume_auto_none)")
INPUT_SHA_FILE = ".kit_resume_inputs.json"     # STAGE-PLATEAU 11-25: sha256 of every kit input at the time its mtime was <= the newest step end (content baseline)
SHA_MAX = 8 << 20


def _sha(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _load_baseline(K):
    try:
        return json.load(open(os.path.join(K, INPUT_SHA_FILE)))
    except (OSError, ValueError):
        return {}


def auto_plan(K, goal="route", now=None, why_out=None, prior=None):
    """FLOW-FIX-2045 (S81-GEOM-OPUS 39ed0e56: run_kit.sh restarted in place with no resume file redid floorplan onward, keeping only synth): the plan of an IN-PLACE restart.  The newest step of
    K/run that is complete, passed, and whose inputs are not newer than its outputs is reused; the run starts at the step after it.  Input = a kit file classify() says is read at that step or
    earlier (gates and files nobody reads do not count; logs, markers and the helpers the wave ships are never inputs).  -> resume record (not yet written) or None when nothing past synth can be reused"""
    why_out = why_out if why_out is not None else {}
    prior = prior or {}
    ck = checkpoint(K, prior.get("ck_id"))
    if not ck.get("upto") or IDX[ck["upto"]] < IDX["floorplan"]:
        why_out["why"] = ("checkpoint reaches only " + str(ck.get("upto")) + "; " + "; ".join(f"{k}: {v.get('why')}" for k, v in ck.get("steps", {}).items() if v.get("why"))
                          + (f"; {ck['why']}" if ck.get("why") else ""))[:600]
        return None
    files, how = input_files(K)
    files = [f for f in files if not AUTO_SKIP_RE.search(f)]
    texts = {}
    for rel in files:
        p = os.path.join(K, rel)
        try:
            if os.path.getsize(p) <= TEXT_MAX and not rel.endswith((".odb", ".lef", ".lib", ".gz")):
                texts[rel] = open(p, errors="replace").read()
        except OSError:
            pass
    try:
        config = parse_config(open(os.path.join(K, "config.mk")).read())
    except OSError:
        why_out["why"] = "config.mk unreadable"
        return None
    # FLOW-OPS-R3 11-24 (QC STB dff1e9a2ad86, unit 3561932): config.mk is a root (parse_config), never a producer.
    # Its text names every hook, and once a hook names "config.mk" the propagation made config.mk synth and then every
    # CTS/GRT hook synth, so a hook edited after place forced a full rerun.  manifest() already leaves it out.
    # The file itself stays synth: an in-place restart cannot tell which variable changed.
    texts.pop("config.mk", None)
    stage = classify(texts, files, config)
    if "config.mk" in stage:
        stage["config.mk"] = "synth"
    mt = {}
    for rel in files:
        try:
            mt[rel] = os.path.getmtime(os.path.join(K, rel))
        except OSError:
            pass
    valid = "synth"
    # FLEET-OPS 11-25 (HEAD-OBSGC 03:56: a kit copied to a new dir lost its resume plan and redid floorplan): the content baseline travels inside the auto plan itself
    # (input_sha, ck_id), so it survives a copy that drops the dotfile baseline and reorders every mtime.  Identity is content (sha256), never path or mtime.
    base, notes = {**(prior.get("input_sha") or {}), **_load_baseline(K)}, []
    for s in STEPS[:-1]:
        st = ck["steps"].get(s) or {}
        if not (st.get("complete") and st.get("passed")):
            break
        newer = [rel for rel, t in mt.items() if stage.get(rel) not in (None, GATE) and IDX[stage[rel]] <= IDX[s] and t > st["end"] + 2]
        # STAGE-PLATEAU 11-25 (HEAD-OBSGC: valid cts checkpoints were discarded and the kit redid floorplan): a kit copy, a tools refresh or a move reorders mtimes
        # without changing a byte.  A file whose content equals the baseline sha recorded when it was last known unchanged is not newer.
        same = []
        for rel in list(newer):
            try:
                if os.path.getsize(os.path.join(K, rel)) <= SHA_MAX and base.get(rel) and _sha(os.path.join(K, rel)) == base[rel]:
                    newer.remove(rel)
                    same.append(rel)
            except OSError:
                pass
        if same:
            notes.append(f"{len(same)} input(s) with a newer mtime but the baseline content ({','.join(sorted(same)[:3])}) are not counted")
        if newer:
            valid_why = f"inputs newer than {s} and changed or without a content baseline: " + ",".join(sorted(newer)[:6])
            break
        valid = s
    else:
        valid_why = ""
    # a step the earlier plan reused must still have the content that plan recorded (a copy that changed an output is not trusted)
    if prior.get("ck_id"):
        cur_id = ck_identity(K, ck)
        for s in prior.get("reused_steps", []):
            if s in prior["ck_id"] and s in IDX and IDX[s] <= IDX[valid] and cur_id.get(s) != prior["ck_id"][s]:
                valid = STEPS[max(IDX[s] - 1, 0)]
                valid_why = f"output of {s} differs from the content the earlier resume plan recorded"
                break
    # record the content baseline of every input whose mtime is not newer than the last complete step (trusted unchanged), keeping earlier entries
    nb = dict(base)
    try:
        t_last = max(v["end"] for v in ck["steps"].values() if v.get("end"))
        for rel, t in mt.items():
            if t <= t_last + 2 and rel not in nb and os.path.getsize(os.path.join(K, rel)) <= SHA_MAX:
                nb[rel] = _sha(os.path.join(K, rel))
        if nb != base:
            tmp_ = os.path.join(K, INPUT_SHA_FILE + ".tmp")
            json.dump(nb, open(tmp_, "w"))
            os.replace(tmp_, os.path.join(K, INPUT_SHA_FILE))
    except (OSError, ValueError):
        pass
    plan_sha = dict(nb)
    if IDX[valid] < IDX["floorplan"]:
        why_out["why"] = (f"checkpoint complete through {ck['upto']} but {locals().get('valid_why') or 'no step is valid'}")[:600]
        return None
    start = STEPS[IDX[valid] + 1]
    if goal in IDX and IDX[goal] < IDX[start]:
        start = goal if goal != "synth" else None
        if start is None:
            return None
    return {"schema": SCHEMA, "auto": True, "start": start, "reused_steps": list(STEPS[:IDX[valid] + 1]), "why": f"in-place restart: newest valid step {valid}" + (f" ({valid_why})" if locals().get("valid_why") else ""),
            "source": {"host": os.uname().nodename, "kit": K, "attempt": None, "attempt_dir": K, "relay": False}, "links": [], "changed": [], "applied": time.time(), "applied_on": os.uname().nodename,
            "n_link": 0, "n_copy": 0, "bytes_link": 0, "bytes_copy": 0, "markers_dropped": [], "keep_created": False, "keep_path": None, "source_checkpoint": {}, "fingerprints": None,
            "input_sha": plan_sha, "ck_id": ck_identity(K, ck)}


def _prior_valid(K, prior):
    """an existing auto plan is still exact when every reused step output and every input it recorded has the recorded content (copy-proof, path- and mtime-free)"""
    try:
        ck_id, sha = prior.get("ck_id") or {}, prior.get("input_sha") or {}
        reused = [s for s in prior.get("reused_steps", []) if s != "synth"]
        if not ck_id or not sha or not reused:
            return False
        cur = ck_identity(K, checkpoint(K, ck_id))
        if any(cur.get(s) != ck_id.get(s) for s in reused):
            return False
        files, _ = input_files(K)
        for rel in files:
            if AUTO_SKIP_RE.search(rel):
                continue
            q = os.path.join(K, rel)
            if os.path.getsize(q) <= SHA_MAX and (rel not in sha or _sha(q) != sha[rel]):
                return False
        return True
    except (OSError, ValueError, KeyError):
        return False


def auto_write(K, goal="route"):
    """write K/resume.json for an in-place restart.  A resume.json that is not auto (the wave's own stage-resume plan) is never touched; an auto one is recomputed.  -> the record or None"""
    p = os.path.join(K, RESUME_FILE)
    prior = None
    if os.path.exists(p):
        try:
            prior = _load(p)
            if not prior.get("auto"):
                return None
        except (OSError, ValueError):
            return None
    why = {}
    rec = auto_plan(K, goal, why_out=why, prior=prior)
    if rec is None and prior and _prior_valid(K, prior):
        # the plan this kit arrived with is exact by content: keep it, pointing its source at this directory
        rec = dict(prior)
        rec["source"] = dict(prior.get("source") or {}, host=os.uname().nodename, kit=K, attempt_dir=K)
        rec["why"] = "kept: recorded checkpoint and input content verified by sha (" + str(prior.get("why", ""))[:200] + ")"
    if rec is None:
        # STAGE-PLATEAU 11-25: never silent.  The reason is printed (run_kit.sh shows KW_RESUME_AUTO) and kept in K/resume_auto_none.json.
        try:
            json.dump({"t": time.time(), "why": why.get("why", "nothing past synth is reusable"), "discarded_resume": os.path.exists(p)}, open(os.path.join(K, "resume_auto_none.json"), "w"))
        except OSError:
            pass
        print("KW_RESUME_AUTO_DISCARD " + json.dumps({"kit": K, "why": why.get("why", "nothing past synth is reusable")}), file=sys.stderr)
        if os.path.exists(p):
            os.unlink(p)
        return None
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1)
    os.replace(tmp, p)
    return rec


def drop_markers(K):
    """COORD 11-05 11:1x class fix (DIE-HEAD-68 ctln2 skipped GRT; DIE-QC-75 sle_fe_v3 skipped place): a kit copied
    with cp -al carries the old run's .kwrs_done.<ppid> markers, and the container's PPID repeats, so kwrs_make.sh
    reads the old run's steps as done and skips them.  Remove every marker in K and K/run before a launch.
    -> [removed paths]"""
    out = []
    for d in (K, os.path.join(K, "run")):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            p = os.path.join(d, n)
            if n.startswith(KWRS_MARKER) and (os.path.isfile(p) or os.path.islink(p)):
                os.unlink(p)            # unlink only: a hardlinked marker in the source kit stays as it was
                out.append(p)
    return sorted(out)


def link_plan(old_ck, start, run_files):
    """files of the old K/run to reuse for steps before start: [(rel, mode)] (mode link | copy).
    run_files: {rel under K: [size, mtime]} of the old K/run tree."""
    last = STEPS[IDX[start] - 1]
    t_end = old_ck["steps"][last]["end"]
    boundary = {os.path.join(old_ck["base"], n) for n in STEP_OUT[last]}
    # KW-FIX-40 11-08 (hd_host a13): ORFS closes a step's log about 2 s after write_db, so the last reused step's log was over
    # the 1 s mtime limit below and dropped, and legacy_gate's GRT layer check stopped on 'no 5_1_grt.log'.  checkpoint()
    # already reads exactly these logs to pass the step, so they belong to the reused run whatever their mtime.
    step_logs = {os.path.join(old_ck["base"].replace("results" + os.sep, "logs" + os.sep, 1), n) for n in STEP_LOGS[last]}

    def step_of(name):
        m = re.match(r"^(\d)_(\d+)?", name)
        if not m:
            return None
        n = int(m.group(1))
        if n == 5:
            return "grt" if m.group(2) == "1" else "route"
        return {1: "synth", 2: "floorplan", 3: "place", 4: "cts"}.get(n, "route")
    out = []
    for rel, (size, mtime) in sorted(run_files.items()):
        if os.path.basename(rel).startswith(KWRS_MARKER):
            continue                    # a step marker of the old run never carries over
        s = step_of(os.path.basename(rel))
        if s is not None and IDX[s] >= IDX[start]:
            continue
        if mtime > t_end + 1 and rel not in step_logs:
            continue
        # hardlink only the numbered step outputs (written once by their step); reports / objects / unnumbered files
        # (a later step may rewrite them in place) and the boundary checkpoint the next step reads are copied
        mode = "link" if (s is not None and size >= LINK_MIN and rel not in boundary
                          and os.sep + "results" + os.sep in os.sep + rel) else "copy"
        out.append((rel, mode))
    return out


# ------------------------------------------------------------------------------------------------ apply / verify
def run_tree(K):
    out = {}
    R = os.path.join(K, "run")
    for root, _, files in os.walk(R):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            st = os.stat(p)
            out[os.path.relpath(p, K)] = [st.st_size, st.st_mtime]
    return out


def apply(newK, src, dec, source_meta):
    """link/copy the reused outputs from src (the old kit dir, or a staged relay copy of it) into newK/run and write
    newK/resume.json.  newK/run must not exist.  -> resume record"""
    if os.path.exists(os.path.join(newK, "run")):
        raise RuntimeError(f"{newK}/run exists: a resumed attempt must start from a fresh kit")
    dropped = drop_markers(newK)
    old_ck = checkpoint(src)
    for s in dec["reuse"]:
        st = (old_ck["steps"] or {}).get(s) or {}
        want = ((source_meta.get("checkpoint") or {}).get("steps") or {}).get(s) or {}
        if not (st.get("complete") and st.get("passed")):
            raise RuntimeError(f"step {s} of the source is no longer complete/passed: {st.get('why')}")
        if want.get("outputs") and {k: v[0] for k, v in st["outputs"].items()} != {k: v[0] for k, v in want["outputs"].items()}:
            raise RuntimeError(f"step {s} outputs changed since the manifest (size)")
    plan = link_plan(old_ck, dec["start"], run_tree(src))
    keep = os.path.join(src, ".keep")
    keep_created = False
    if not os.path.exists(keep) and source_meta.get("same_host"):
        with open(keep, "w") as f:
            f.write(f"KW-RESUME source of {newK} (stage resume, removed when that attempt's wave run ends)\n")
        keep_created = True
    links = []
    try:
        for rel, mode in plan:
            a, b = os.path.join(src, rel), os.path.join(newK, rel)
            os.makedirs(os.path.dirname(b), exist_ok=True)
            st = os.stat(a)
            if mode == "link":
                try:
                    os.link(a, b)
                except OSError as exc:
                    if exc.errno not in (errno.EPERM, errno.EXDEV):
                        raise
                    # OpenROAD may produce a readable checkpoint owned by the
                    # container user, or the resume workspace may be on another device.
                    mode = "copy"
            if mode == "copy":
                shutil.copy2(a, b)
            links.append({"rel": rel, "mode": mode, "size": st.st_size, "mtime": st.st_mtime, "ino": st.st_ino})
    except Exception:
        shutil.rmtree(os.path.join(newK, "run"), ignore_errors=True)
        if keep_created:
            os.unlink(keep)
        raise
    rec = {"schema": SCHEMA, "start": dec["start"], "reused_steps": dec["reuse"], "why": dec["why"],
           "source": {k: source_meta.get(k) for k in ("host", "kit", "attempt", "attempt_dir", "relay")},
           "source_checkpoint": {s: old_ck["steps"][s] for s in dec["reuse"]},
           "changed": dec["changed"], "fingerprints": dec.get("fingerprints"),
           "links": links, "markers_dropped": dropped, "keep_created": keep_created, "keep_path": keep if keep_created else None,
           "applied": time.time(), "applied_on": os.uname().nodename,
           "n_link": sum(1 for x in links if x["mode"] == "link"), "n_copy": sum(1 for x in links if x["mode"] == "copy"),
           "bytes_link": sum(x["size"] for x in links if x["mode"] == "link"),
           "bytes_copy": sum(x["size"] for x in links if x["mode"] == "copy")}
    tmp = os.path.join(newK, RESUME_FILE + ".tmp")
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1)
    os.replace(tmp, os.path.join(newK, RESUME_FILE))
    return rec


def _load(p):
    with open(p) as f:
        return json.load(f)


def verify(newK, src=None):
    """-> [problems]: a linked source file whose size/mtime changed (a write through a hardlink)"""
    rec = _load(os.path.join(newK, RESUME_FILE))
    src = src or rec["source"]["kit"]
    bad = []
    for x in rec["links"]:
        if x["mode"] != "link":
            continue
        p = os.path.join(src, x["rel"])
        try:
            st = os.stat(p)
        except OSError:
            continue                    # the source was pruned: the new attempt's link keeps its own data
        if st.st_ino == x["ino"] and (st.st_size != x["size"] or abs(st.st_mtime - x["mtime"]) > 1e-3):
            bad.append(f"{x['rel']}: size/mtime {st.st_size}/{st.st_mtime} != {x['size']}/{x['mtime']}")
    return bad


def release(newK):
    """remove the source .keep this attempt created"""
    try:
        rec = _load(os.path.join(newK, RESUME_FILE))
    except (OSError, ValueError):
        return False
    p = rec.get("keep_path")
    if rec.get("keep_created") and p and os.path.isfile(p):
        os.unlink(p)
        return True
    return False


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("grt-terminal-dpl", help="print the terminal placement error after a caught GRT hold cap")
    a.add_argument("log")
    a = sub.add_parser("inputs")
    a.add_argument("kit")
    a = sub.add_parser("manifest")
    a.add_argument("kit")
    a.add_argument("--cutoff", type=float)
    a.add_argument("--runner")
    a.add_argument("--image", default="openroad/orfs:asap7lock")
    a.add_argument("--no-checkpoint", action="store_true")
    a = sub.add_parser("checkpoint")
    a.add_argument("kit")
    a.add_argument("--run-files", action="store_true", help="include the file inventory required for a cross-host relay")
    a = sub.add_parser("apply")
    a.add_argument("kit")
    a.add_argument("--src", required=True)
    a.add_argument("--decision", required=True, help="json file or '-' (stdin): {decision, source}")
    a = sub.add_parser("verify")
    a.add_argument("kit")
    a = sub.add_parser("release")
    a.add_argument("kit")
    a = sub.add_parser("auto", help="in-place restart: write K/resume.json from the newest valid stage result (run_kit.sh does this unless OT_RESUME=0)")
    a.add_argument("kit")
    a.add_argument("goal", nargs="?", default="route")
    a = sub.add_parser("clean", help="drop stale .kwrs_done.* step markers (run after cp -al of a kit, before launch)")
    a.add_argument("kit")
    a = ap.parse_args(argv)
    if a.cmd == "grt-terminal-dpl":
        with open(a.log, errors="replace") as stream:
            print(grt_terminal_dpl(stream.read()))
    elif a.cmd == "inputs":
        r = write_inputs(a.kit)
        print("KW_RESUME_INPUTS " + json.dumps({"n": len(r["files"])}))
    elif a.cmd == "manifest":
        m = manifest(a.kit, a.cutoff, a.runner, a.image, not a.no_checkpoint)
        print("KW_RESUME_MANIFEST " + json.dumps(m))
    elif a.cmd == "checkpoint":
        m = {"kit": os.path.abspath(a.kit), "checkpoint": checkpoint(a.kit)}
        if a.run_files:
            m["run_files"] = run_tree(a.kit)
        print("KW_RESUME_CHECKPOINT " + json.dumps(m))
    elif a.cmd == "apply":
        d = json.load(sys.stdin if a.decision == "-" else open(a.decision))
        try:
            r = apply(a.kit, a.src, d["decision"], d["source"])
            print("KW_RESUME_APPLIED " + json.dumps({k: v for k, v in r.items() if k != "links"}))
        except Exception as e:                  # noqa: BLE001 -- any doubt: the caller rebuilds in full
            print("KW_RESUME_APPLY_FAIL " + json.dumps({"error": f"{type(e).__name__}: {e}"}))
            return 3
    elif a.cmd == "auto":
        r = auto_write(os.path.abspath(a.kit), a.goal)
        print("KW_RESUME_AUTO " + (json.dumps({"start": r["start"], "reused": r["reused_steps"], "why": r["why"]}) if r else "none (full flow: nothing past synth is reusable, or the kit has a wave resume plan; reason in K/resume_auto_none.json)"), file=sys.stderr)
    elif a.cmd == "verify":
        bad = verify(a.kit)
        print("KW_RESUME_VERIFY " + json.dumps({"ok": not bad, "bad": bad[:20]}))
        return 4 if bad else 0
    elif a.cmd == "clean":
        print("KW_RESUME_CLEAN " + json.dumps({"removed": drop_markers(a.kit)}))
    elif a.cmd == "release":
        print("KW_RESUME_RELEASE " + json.dumps({"removed": release(a.kit)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
