#!/usr/bin/env python3
"""flow_canary: one reference partition per die runs the FULL kit flow from current main's flow tools.

Why (lane FLOW-CANARY, owner-approved 2026-10-25): flow bugs hid behind our own gates and cost kit waves -- the asap7
image ignored SET_RC_TCL, face_guard skipped rst_o_* while the flow buffered keep-reg relays, an implicit undriven
net tied 8 regs to 0 (ot_s81eng_aq_n32), cts.tcl:87 'la_d' (POST_CTS hook scope).  A canary regenerates a known,
already-routed reference kit with main's generator, runs it end to end through ot-run, and checks (a) that every
stage ran on the intended inputs and (b) the sign-off result against the golden record.  Mass kit waves of a die
start only after that die's canary PASSes.

  canary.py list
  canary.py submit  --src MAIN_WT [--die D ...] [--root DIR] [--dry]     regen + ot-run (run on epyc1)
  canary.py lint    --kit KIT --top MOD [--image IMG] --out lint.json   (inside the job; yosys -noautowire)
  canary.py check   --run RUN_DIR [--out canary.json]                    (inside the job, or again by hand)
  canary.py summary --root DIR                                           newest verdict per die

Verdict per canary: PASS only when every required stage has evidence and passes and the sign-off is not worse than the
golden record.  Missing evidence is a FAIL (NOT RUN is never a pass).
"""
import argparse
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / "canaries.json"
IMAGE = "openroad/orfs:asap7lock"
OT_RUN = "~/.local/bin/ot-run"
# A face register is required on every partition port except the clock / async reset inputs.  Unlike
# tools/die_plan/face_guard.SKIP_RE this does NOT skip rst_o_* / start_o_* (reset wavefront outs are registered relays).
CLOCK_ONLY_SKIP_RE = r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|rst_n|rst_i|start_i)$"
TCL_ERR_RE = re.compile(r"can't read \"[^\"]+\": no such variable|invalid command name \"|"
                        r"Error: [^\n]*\.tcl, \d+|couldn't open \"[^\"]+\"|can't find package|"
                        r"ERROR \[?[A-Z]{3}-\d+")
STAGES = ("lint", "sdc_lint", "selrange", "synth", "lec", "face_guard", "face_cover", "reg_fanout", "rc_file", "vclk_basis",
          "cts", "grt_gate", "route", "rcx", "signoff", "tcl_errors")
# vclk_basis (COORD 10-25, main 9f716b354, METHODOLOGY 9.7 / BRIEFING 5e): the IO virtual clock must be the kit's
# per-corner pin-register insertion binding, never the old fixed plan latency.
VCLK_SDC_TOL_PS = 0.5          # constraint.sdc vclk source latency vs config.mk OT_VCLK_TT (and OT_VCLK_* vs binding)
PLAN_FIXED_LATENCY_PS = 250.0  # the pre-binding plan common latency every kit SDC carried
VCLK_LAT_RE = re.compile(r"^\s*set_clock_latency\s+-source\s+(?:-(?:early|late|max|min|rise|fall)\s+)*"
                         r"(-?[0-9.]+(?:[eE][-+]?[0-9]+)?)\s+\[get_clocks\s+\{?vclk\}?\]", re.M)


def load_spec(path=SPEC):
    d = json.loads(Path(path).read_text())
    return {c["die"]: c for c in d["canaries"]}, d


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, **kw)


def fmt(s, **kv):
    return s.format(**kv) if isinstance(s, str) else [fmt(x, **kv) for x in s]


# ------------------------------------------------------------------------------------------------------------- lint
def lint_script(kit, top):
    """yosys script: macros as liberty blackboxes, RTL read with default_nettype none (implicit nets are errors),
    hierarchy -check (missing modules / ports are errors), then proc + check (undriven / multi-driven wires)."""
    k = Path(kit)
    libs, seen = [], set()                     # one timing view per macro (TT preferred): blackbox interface only
    for p in sorted(k.glob("macros/*.lib*"), key=lambda p: (not re.search(r"_tt\.lib", p.name), p.name)):
        stem = re.sub(r"_(tt|ff|ss)?\.lib(\.gz)?$|\.lib(\.gz)?$", "", p.name)
        if stem not in seen:
            seen.add(stem)
            libs.append(p.name)
    srcs = cfg_list(k, "VERILOG_FILES")
    lines = [f"read_liberty -lib -ignore_miss_func /work/macros/{x}" for x in libs]
    lines.append("verilog_defines -DSYNTHESIS")
    lines += [f"read_verilog -sv -noautowire {s}" for s in srcs]
    lines += [f"hierarchy -check -top {top}", "proc", "check"]
    return "\n".join(lines) + "\n"


def cfg_list(kit, var):
    """export VAR = a b c from config.mk (paths stay as the kit writes them: /work/...)"""
    txt = (Path(kit) / "config.mk").read_text() if (Path(kit) / "config.mk").is_file() else ""
    m = re.search(rf"^(?:override\s+)?export\s+{var}\s*[:?]?=\s*(.*)$", txt, re.M)
    return m.group(1).split() if m else []


def cfg_val(kit, var):
    v = cfg_list(kit, var)
    return v[0] if v else None


def parse_lint(log, rc):
    implicit = re.findall(r"(?:Identifier|Wire) `?\\?([^'\s`]+)'? is implicitly declared|"
                          r"ERROR: Identifier `([^']+)' is implicitly declared", log)
    implicit = [(a or b).lstrip("\\") for a, b in implicit]
    undriven = re.findall(r"Warning: [Ww]ire ([^\s]+) is used but has no driver", log)
    multi = re.findall(r"Warning: [^\n]*multiple conflicting drivers[^\n]*", log)
    errors = re.findall(r"^ERROR: .*$", log, re.M)
    verdict = "PASS" if rc == 0 and not implicit and not errors and not multi else "FAIL"
    return dict(verdict=verdict, rc=rc, implicit=implicit[:50], n_implicit=len(implicit), undriven=undriven[:50],
                n_undriven=len(undriven), multi_driven=multi[:20], errors=errors[:20])


def lint_via_rtl_lint(kit, image, tool):
    """FLOW-FIX 10-25: the canary lint = the flow's own tools/die_plan/rtl_lint.py (main, Codex 63795270e:
    read_verilog -sv -noautowire, hierarchy -check, proc, check -assert; one liberty view per macro), run in the kit
    image exactly as gen_phys RUN_KIT runs it, mapped to the canary lint.json fields."""
    tool = Path(tool).resolve()
    r = sh(f"docker run --rm -v {shlex.quote(str(kit))}:/work -v {shlex.quote(str(tool.parent))}:/canary_tool:ro {image} "
           f"bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /canary_tool/{tool.name} /work'")
    rj = jload(kit / "rtl_lint.json") or {}
    errs = rj.get("errors") or []
    imp = [e for e in errs if "implicit" in e.lower()]
    und = [e for e in errs if "undriven" in e.lower() or "no driver" in e.lower()]
    v = rj.get("verdict", "NOT RUN")
    return dict(verdict="PASS" if v == "PASS" else "FAIL", rc=rj.get("rc", getattr(r, "returncode", None)),
                implicit=imp[:50], n_implicit=len(imp), undriven=und[:50], n_undriven=len(und), multi_driven=[],
                errors=errs[:20], why=([] if v == "PASS" else [f"rtl_lint {v}"] + errs[:2]),
                rtl_lint=str(kit / "rtl_lint.json"))


def cmd_lint(a):
    kit = Path(a.kit).resolve()
    tool = HERE / "rtl_lint.py"
    if not tool.is_file():
        tool = HERE.parent / "die_plan" / "rtl_lint.py"
    if tool.is_file():
        res = lint_via_rtl_lint(kit, a.image, tool)
        res.update(top=a.top, kit=str(kit), tool="tools/die_plan/rtl_lint.py")
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
        print(f"CANARY_LINT {res['verdict']} implicit={res['n_implicit']} undriven={res['n_undriven']} "
              f"errors={len(res['errors'])} {'; '.join(res['why'][:3])}")
        return 0 if res["verdict"] == "PASS" else 1
    (kit / "canary_lint.ys").write_text(lint_script(kit, a.top))
    r = sh(f"docker run --rm -v {kit}:/work {a.image} bash -lc "
           f"'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /work; yosys -q -l /work/canary_lint.log "
           f"-s /work/canary_lint.ys >/dev/null 2>&1; echo RC=$?'")
    m = re.search(r"RC=(\d+)", r.stdout)
    rc = int(m.group(1)) if m else 99
    log = (kit / "canary_lint.log").read_text(errors="replace") if (kit / "canary_lint.log").is_file() else r.stderr
    res = parse_lint(log, rc)
    res.update(top=a.top, kit=str(kit), tool="yosys read_verilog -noautowire; hierarchy -check; proc; check")
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(f"CANARY_LINT {res['verdict']} implicit={res['n_implicit']} undriven={res['n_undriven']} "
          f"errors={len(res['errors'])}")
    return 0 if res["verdict"] == "PASS" else 1


# ------------------------------------------------------------------------------------------------------------ check
def jload(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def first(pattern):
    g = sorted(glob.glob(pattern, recursive=True))
    return g[-1] if g else None


def read(p):
    try:
        return Path(p).read_text(errors="replace")
    except Exception:
        return ""


def st(ok, why, **kw):
    """stage result; ok None = NOT RUN (counts as FAIL when the stage is required)"""
    return dict(verdict="PASS" if ok else ("NOT RUN" if ok is None else "FAIL"), why=why, **kw)


def chk_signoff(so, golden, tol):
    if not so:
        return st(None, "no signoff.json")
    c = so.get("checks") or {}
    s, h = (c.get("setup_tt") or {}).get("wns_ps"), (c.get("hold_ff") or {}).get("wns_ps")
    par = {k: (v or {}).get("parasitics") for k, v in (so.get("corners") or {}).items()}
    out = dict(verdict_so=so.get("verdict"), setup_tt_wns=s, hold_ff_wns=h, parasitics=par,
               reasons=(so.get("reasons") or [])[:8])
    g = golden or {}
    if not g.get("verdict"):
        return st(so.get("verdict") is not None, "BASELINE (no golden record): " + str(so.get("verdict")), **out)
    bad = []
    if g["verdict"] == "SIGNED" and so.get("verdict") != "SIGNED":
        bad.append(f"verdict {so.get('verdict')} vs golden SIGNED")
    for k, v in (("setup_tt_wns", s), ("hold_ff_wns", h)):
        gv = g.get(k)
        if gv is not None and (v is None or v < gv - tol):
            bad.append(f"{k} {v} vs golden {gv} (tol {tol})")
    return st(not bad, "; ".join(bad) or f"verdict {so.get('verdict')} (golden {g['verdict']}), "
              f"setup_tt {s} vs {g.get('setup_tt_wns')}, hold_ff {h} vs {g.get('hold_ff_wns')}", **out)


def configured_clock_ports(sdc):
    """Only literal ports named by create_clock are additional clock inputs, never arbitrary skip regexes."""
    out = set()
    text = sdc.replace("\\\n", " ")
    for m in re.finditer(r"create_clock[^\n]*?\[get_ports\s+(?:\{([^}]+)\}|([A-Za-z_][A-Za-z0-9_$]*))\]", text):
        for word in (m.group(1) or m.group(2)).split():
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", word):
                out.add(word)
    return sorted(out)


def face_cover(netlist, pins_json, top=None, die_plan_dir=None, clock_ports=()):
    """re-run tools/die_plan/face_guard.guard with clock/reset-input-only skips: every other port, incl. rst_o_* and
    start_o_*, must have its own face register."""
    if not netlist or not Path(netlist).is_file():
        return st(None, "no netlist")
    sys.path.insert(0, str(die_plan_dir or (HERE.parent / "die_plan")))
    import face_guard as FG
    pins = jload(pins_json) if pins_json else None
    skip = CLOCK_ONLY_SKIP_RE
    if clock_ports:
        skip = "(?:" + skip + "|^(?:" + "|".join(re.escape(p) for p in clock_ports) + ")$)"
    # Planned clock/reset pins are excluded from both wanted and present data-bit sets.
    # Otherwise the guard reports an excluded-but-present clock as a missing data port.
    if pins is not None:
        pins = [p for p in pins if not re.match(skip, p["bus"])]
    ftf = Path(pins_json).with_name("ft_stations.txt") if pins_json else None
    ft1 = FG.read_ft1(str(ftf)) if ftf and ftf.is_file() else set()
    r = FG.guard(read(netlist), top, skip_re=skip, pins=pins, ft1=ft1)
    mods = FG.parse(read(netlist))
    T = mods[r["top"]]
    wave = [p for p in T.ports if re.match(r"^(rst_o_|start_o_)", p)]
    return st(r["verdict"] == "PASS", f"{r['verdict']} checked {r['checked']} ok {r['ok']} fails {r['fail_counts']} "
              f"(wavefront ports {len(wave)})", checked=r["checked"], wave_ports=wave[:20], clock_ports=list(clock_ports),
              fails={k: v[:5] for k, v in r["fails"].items()})


def vclk_basis(kit, so):
    """IO virtual-clock basis = per-corner insertion binding (gen_phys keys).  FAIL when config.mk lacks
    OT_VCLK_TT / OT_VCLK_FF, clock_binding.json {insertion_ps: {tt, ff}, insertion_tol_ps} is missing, OT_VCLK_* differ
    from the binding, the constraint.sdc vclk source latency != OT_VCLK_TT (VCLK_SDC_TOL_PS), the SDC carries the old
    fixed 250 ps plan latency with no binding, or (sign-off) the record did not rebind each corner to its routed
    pin-register mean or that mean is more than insertion_tol_ps from the bound value.  No sign-off record = NOT RUN.
    Units: config.mk / SDC are liberty time units (ASAP7: ps, gen_phys.t_lib), binding + signoff.json are ps."""
    kit = Path(kit)
    bad, info = [], {}
    vt, vf = cfg_val(kit, "OT_VCLK_TT"), cfg_val(kit, "OT_VCLK_FF")
    info["ot_vclk"] = dict(tt=vt, ff=vf)
    for k, v in (("OT_VCLK_TT", vt), ("OT_VCLK_FF", vf)):
        if v is None:
            bad.append(f"config.mk sets no {k}")
    try:
        vt = float(vt) if vt is not None else None
        vf = float(vf) if vf is not None else None
    except ValueError:
        bad.append(f"config.mk OT_VCLK_TT/FF not numeric: {vt} / {vf}")
        vt = vf = None
    cb = jload(kit / "clock_binding.json")
    ins = (cb or {}).get("insertion_ps") or {}
    tol = (cb or {}).get("insertion_tol_ps")
    bt, bf = ins.get("tt"), ins.get("ff")
    info["binding"] = dict(tt=bt, ff=bf, tol=tol) if cb else None
    if cb is None:
        bad.append("no clock_binding.json")
    elif bt is None or bf is None or tol is None:
        bad.append(f"clock_binding.json incomplete: insertion_ps {ins} insertion_tol_ps {tol}")
    for k, v, b in (("OT_VCLK_TT", vt, bt), ("OT_VCLK_FF", vf, bf)):
        if v is not None and b is not None and abs(v - float(b)) > VCLK_SDC_TOL_PS:
            bad.append(f"{k} {v:g} != clock_binding {b:g}")
    lats = [float(x) for x in VCLK_LAT_RE.findall(read(kit / "constraint.sdc"))]
    info["sdc_vclk_latency"] = lats
    if not lats:
        bad.append("constraint.sdc sets no vclk source latency")
    elif cb is None and any(abs(x - PLAN_FIXED_LATENCY_PS) <= VCLK_SDC_TOL_PS for x in lats):
        bad.append(f"constraint.sdc vclk latency = old fixed {PLAN_FIXED_LATENCY_PS:g} ps plan latency, no binding")
    if vt is not None and any(abs(x - vt) > VCLK_SDC_TOL_PS for x in lats):
        bad.append(f"constraint.sdc vclk latency {lats} != OT_VCLK_TT {vt:g} (tol {VCLK_SDC_TOL_PS:g})")
    if bad:
        return st(False, "; ".join(bad), **info)
    if not so:
        return st(None, f"pre-route basis OK (TT {vt:g} / FF {vf:g}, tol {tol:g}); no signoff.json: routed per-corner "
                        f"pin-register mean not checked", **info)
    pol = so.get("policy") or {}
    if pol.get("ff_vclk") != "rebind":
        bad.append(f"sign-off IO vclk mode {pol.get('ff_vclk')!r}, not 'rebind' (IO timed against the fixed SDC vclk)")
    ib = pol.get("insertion_bound") or {}
    routed = {}
    for c, b in (("tt", bt), ("ff", bf)):
        if ib.get(c) is not None and abs(float(ib[c]) - float(b)) > VCLK_SDC_TOL_PS:
            bad.append(f"sign-off bound {c.upper()} {ib[c]} != clock_binding {b:g}")
        cr = (so.get("corners") or {}).get(c) or {}
        ref = cr.get("ff_vclk_reference") or ""
        if pol.get("ff_vclk") == "rebind" and not ref.startswith("applied mode pin_flop_mean "):
            bad.append(f"{c.upper()} vclk rebind not applied ({ref or 'no reference'})")
        mean = (cr.get("insertion_pinflops") or {}).get("mean")
        routed[c] = mean
        if mean is None:
            bad.append(f"{c.upper()} routed pin-register mean not measured")
        elif abs(float(mean) - float(b)) > float(tol):
            bad.append(f"{c.upper()} routed pin-register mean {float(mean):.1f} ps vs bound {float(b):g} > tol {float(tol):g}")
    info["routed_mean"] = routed
    return st(not bad, "; ".join(bad) or f"bound TT {bt:g} / FF {bf:g} +- {tol:g}; SDC {lats}; routed mean "
              f"TT {routed['tt']:.1f} / FF {routed['ff']:.1f}", **info)


def check_run(run, spec=None, die_plan_dir=None):
    run = Path(run)
    meta = jload(run / "canary_meta.json") or {}
    spec = spec or meta.get("spec") or {}
    kit = Path(meta.get("kit") or (run / "kit"))
    if die_plan_dir is None and meta.get("src"):
        die_plan_dir = Path(meta["src"]) / "tools" / "die_plan"
    req = spec.get("require", list(STAGES))
    base = first(f"{kit}/run/results/asap7/*/base")
    logs = first(f"{kit}/run/logs/asap7/*/base")
    res = {}
    # lint (canary's own)
    lj = jload(run / "lint.json")
    res["lint"] = st(None, "lint not run") if not lj else st(lj["verdict"] == "PASS",
                                                             f"{lj['verdict']} implicit {lj['n_implicit']} "
                                                             f"{lj['implicit'][:5]} undriven {lj['n_undriven']} "
                                                             f"errors {lj['errors'][:3]}")
    sl = read(kit / "sdc_lint.log")
    res["sdc_lint"] = st(None, "no sdc_lint.log") if not sl else st(
        not re.search(r"\bFAIL", sl) and "FAIL_PREFLOOR sdc_lint" not in read(kit / "FAIL_PREFLOOR"), sl.strip()[-160:])
    sr = jload(kit / "selrange.json")
    res["selrange"] = st(None, "no selrange.json") if not sr else st(sr.get("verdict") == "PASS",
                                                                      f"{sr.get('verdict')} unwaived {sr.get('unwaived')}")
    ys = first(f"{base}/1_2_yosys.v") if base else None
    res["synth"] = st(bool(ys) or None, ys or "no 1_2_yosys.v")
    lec = jload(kit / "lec" / "lec.json")
    res["lec"] = st(None, "no lec/lec.json") if not lec else st(lec.get("verdict") == "EQUIVALENT",
                                                                 f"{lec.get('verdict')} {lec.get('reason', '')}"[:200])
    fg = jload(kit / "face_guard.json")
    res["face_guard"] = st(None, "no face_guard.json") if not fg else st(fg.get("verdict") == "PASS",
                                                                         f"{fg.get('verdict')} checked {fg.get('checked')}")
    clock_ports = configured_clock_ports(read(kit / "constraint.sdc"))
    covs = []
    for nl in [ys, str(kit / "1_synth_odb.v") if (kit / "1_synth_odb.v").is_file() else None]:
        if nl:
            try:
                c = face_cover(nl, kit / "pins.json" if (kit / "pins.json").is_file() else None,
                               die_plan_dir=die_plan_dir, clock_ports=clock_ports)
            except Exception as e:                       # a crash of the cover check is NOT RUN, never a pass
                c = st(None, f"face_cover error {type(e).__name__}: {e}")
            c["netlist"] = Path(nl).name
            covs.append(c)
    if covs:
        bad = [c for c in covs if c["verdict"] != "PASS"]
        res["face_cover"] = dict(bad[0] if bad else covs[0], per_netlist=covs)
    else:
        res["face_cover"] = st(None, "no netlist")
    # register fanout (COORD 10-25: Yosys-merged replicas): kit gate record if the flow has one, else measured here
    rf = jload(kit / "reg_fanout.json")
    if rf is None and ys:
        try:
            sys.path[:0] = [str(die_plan_dir or HERE.parent / "die_plan"), str(run), str(HERE.parent / "die_plan")]
            import reg_fanout_gate as RF
            rf = RF.fanout(read(ys))
            rf["source"] = "canary"
        except Exception as e:
            rf = dict(verdict="ERROR", error=f"{type(e).__name__}: {e}")
    if not rf:
        res["reg_fanout"] = st(None, "no netlist")
    elif rf.get("verdict") == "ERROR":
        res["reg_fanout"] = st(None, rf.get("error", "error"))
    else:
        res["reg_fanout"] = st(rf["verdict"] == "PASS", f"{rf['verdict']} ({rf.get('source', 'kit gate')}) registers "
                               f"{rf.get('registers')} over_{rf.get('max_loads')} {rf.get('over')} "
                               f"worst {[(w['loads'], w['regs'][0]) for w in rf.get('worst', [])[:5]]}")
    # rc file: the configured RC tcl must be the one sourced in floorplan..GRT (ORFS: log_cmd source $LAYER_PARASITICS_FILE)
    want = cfg_val(kit, "LAYER_PARASITICS_FILE")
    step_logs = sorted(glob.glob(f"{logs}/*.log")) if logs else []
    if not want:
        res["rc_file"] = st(False, "config.mk sets no LAYER_PARASITICS_FILE (asap7lock image ignores SET_RC_TCL): "
                                   "stock platform setRC.tcl in place/CTS/GRT")
    elif not step_logs:
        res["rc_file"] = st(None, "no step logs")
    else:
        used = [Path(l).name for l in step_logs if want in read(l)]
        stock = [Path(l).name for l in step_logs if re.search(r"source \S*platforms/asap7/setRC\.tcl", read(l))]
        need = [Path(l).name for l in step_logs if re.match(r"(3_3|4_1|5_1)_", Path(l).name)]
        miss = [n for n in need if n not in used]
        res["rc_file"] = st(bool(used) and not miss and not stock, f"{want} sourced in {len(used)} step logs; "
                            f"missing in {miss[:4]}; stock setRC in {stock[:4]}")
    cts = first(f"{base}/4_cts.odb") if base else None
    res["cts"] = st(bool(cts) or None, "4_cts.odb" if cts else "no 4_cts.odb " + read(kit / "FAIL_POSTCTS")[-200:])
    g = [read(kit / f"postcts_gate_{c}.log") for c in ("TT", "FF")]
    gl = [l for x in g for l in x.splitlines() if l.startswith("OT_POSTCTS_GATE")]
    if spec.get("grt_gate", True) is False:
        res["grt_gate"] = st(True, "not part of this flow (spec grt_gate false)")
    else:
        res["grt_gate"] = st(None, "no OT_POSTCTS_GATE lines") if not gl else st(
            len(gl) >= 2 and not any("FAIL" in l for l in gl), " | ".join(gl)[:300])
    rt = first(f"{base}/6_final.odb") or first(f"{base}/5_route.odb") if base else None
    res["route"] = st(bool(rt) or None, Path(rt).name if rt else "no routed odb")
    sop = sorted(glob.glob(f"{kit}/signoff*/signoff.json"), key=os.path.getmtime)
    so = jload(sop[-1]) if sop else None
    res["signoff"] = chk_signoff(so, spec.get("golden"), float(spec.get("wns_tol_ps", 15)))
    res["signoff"]["path"] = sop[-1] if sop else None
    res["vclk_basis"] = vclk_basis(kit, so)
    par = (res["signoff"].get("parasitics") or {})
    res["rcx"] = st(None, "no signoff corners") if not par else st(all(v == "spef" for v in par.values()), str(par))
    errs = []
    for l in step_logs + [str(kit / f) for f in ("hold_gate.log", "synth_odb_v.log")] + sorted(glob.glob(f"{kit}/run_*.log")):
        for m in TCL_ERR_RE.finditer(read(l)):
            errs.append(f"{Path(l).name}: {m.group(0)[:120]}")
    res["tcl_errors"] = st(not errs, "; ".join(errs[:6]) or "none", n=len(errs))
    failing = [k for k in req if res.get(k, {}).get("verdict") != "PASS"]
    out = dict(schema="opentallas.flow_canary.v1", die=spec.get("die"), item=spec.get("item"), run=str(run),
               kit=str(kit), src=meta.get("src_commit"), generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               verdict="PASS" if not failing else "FAIL", failing=failing, stages=res,
               fail_prefloor=read(kit / "FAIL_PREFLOOR").strip()[-400:], fail_postcts=read(kit / "FAIL_POSTCTS").strip()[-400:])
    return out


def cmd_check(a):
    r = check_run(a.run)
    Path(a.out or Path(a.run) / "canary.json").write_text(json.dumps(r, indent=1) + "\n")
    print(f"CANARY {r['verdict']} die={r['die']} item={r['item']} src={r['src']} failing={r['failing']}")
    for k in r["failing"]:
        print(f"  - {k}: {r['stages'][k]['verdict']} {r['stages'][k]['why'][:220]}")
    return 0 if r["verdict"] == "PASS" else 1


# ----------------------------------------------------------------------------------------------------------- submit
JOB = """#!/bin/bash
# GENERATED by tools/flow_canary/canary.py submit ({die} {item} @ {src}).  Runs under ot-run: kit generation from
# main's tools, canary lint, the die's kit flow, then the canary check (canary.json).
set -u
R={run}; K={kit}
echo "CANARY_START $(date '+%F %T %Z') host=$(hostname)"
{prep}
( cd {gen_cwd} && {genenv}{gen} ) > $R/gen.log 2>&1; G=$?
echo "CANARY_GEN rc=$G"
if [ $G != 0 ] || [ ! -d $K ]; then echo "CANARY_GEN FAIL (see $R/gen.log)"; tail -n 20 $R/gen.log
  python3 -I $R/canary.py check --run $R; exit 3; fi
python3 -I $R/canary.py lint --kit $K --top {top} --image {image} --out $R/lint.json
{runcmd}
echo "CANARY_FLOW_RC $?"
python3 -I $R/canary.py check --run $R
"""


def git_head(src):
    r = sh(f"git -C {shlex.quote(str(src))} rev-parse HEAD")
    return r.stdout.strip()[:12] or "unknown"


def cmd_submit(a):
    specs, _ = load_spec(a.spec)
    dies = a.die or list(specs)
    src = Path(a.src).resolve()
    sha = git_head(src)
    stamp = time.strftime("%m%d_%H%M%S") + f"_{time.time_ns() % 1000000:06d}"
    for die in dies:
        c = specs[die]
        run = Path(a.root) / f"{die}_{sha[:9]}_{stamp}"
        run.mkdir(parents=True, exist_ok=True)
        kv = dict(src=str(src), gen=str(run / "gen"), run=str(run), item=c["item"], top=c["top"], image=a.image,
                  mem=c["mem_gb"], cpus=c.get("threads", 8))
        kv.update({k: fmt(v, **kv) for k, v in c.get("vars", {}).items()})   # e.g. kv_core {inputs}
        kit = fmt(c["kit"], **kv)
        kv["kit"] = kit
        (run / "canary.py").write_text((HERE / "canary.py").read_text())
        rtl = HERE.parent / "die_plan" / "rtl_lint.py"
        if rtl.is_file():
            (run / "rtl_lint.py").write_text(rtl.read_text())
        rfg = HERE.parent / "die_plan" / "reg_fanout_gate.py"
        if rfg.is_file():
            (run / "reg_fanout_gate.py").write_text(rfg.read_text())
        (run / "canary_meta.json").write_text(json.dumps(dict(spec=c, kit=kit, src=str(src), src_commit=sha,
                                                              submitted=time.strftime("%F %T %Z")), indent=1) + "\n")
        genenv = "".join(f"{k}={shlex.quote(fmt(v, **kv))} " for k, v in c.get("gen_env", {}).items())
        job = JOB.format(die=die, item=c["item"], src=sha, run=run, kit=kit, top=c["top"], image=a.image,
                         prep="\n".join(fmt(c.get("prep", []), **kv)), gen_cwd=fmt(c.get("gen_cwd", "{src}"), **kv),
                         genenv=genenv, gen=fmt(c["gen"], **kv), runcmd=fmt(c["run"], **kv))
        (run / "job.sh").write_text(job)
        cmd = (f"{OT_RUN} --mem {c['mem_gb']} --threads {kv['cpus']} --dir {run} -- bash {run}/job.sh "
               f"> {run}/otrun.log 2>&1")
        print(f"CANARY {die} {c['item']} src {sha}: {run}")
        if a.dry:
            print("  DRY", cmd)
            continue
        # nohup/new-session does not leave the trigger's systemd cgroup: oneshot exit kills those clients.
        # A separate user service owns each ot-run client until its job has finished.
        unit = "flow-canary-" + die.replace("_", "-") + "-" + sha[:9] + "-" + stamp.replace("_", "-")
        r = subprocess.run(["systemd-run", "--user", "--unit", unit, "--collect", "--property=Type=exec",
                            "--property=KillMode=process", "--", "bash", "-lc", cmd],
                           capture_output=True, text=True)
        mp = run / "canary_meta.json"
        meta = jload(mp) or {}
        meta["client_unit"] = unit
        if r.returncode:
            meta["submission_error"] = r.stderr.strip()
            result = dict(schema="opentallas.flow_canary.v1", die=die, item=c["item"], src=sha,
                          run=str(run), kit=kit, verdict="FAIL", failing=["launch"],
                          stages={"launch": st(False, r.stderr.strip())}, generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            (run / "canary.json").write_text(json.dumps(result, indent=1) + "\n")
            mp.write_text(json.dumps(meta, indent=1) + "\n")
            print(f"CANARY {die} NOT RUN: transient client service failed: {r.stderr.strip()}")
            return r.returncode
        mp.write_text(json.dumps(meta, indent=1) + "\n")
        print(f"CANARY {die} client service {unit}")
    return 0


def cmd_summary(a):
    best = {}
    for p in sorted(glob.glob(f"{a.root}/*/canary.json"), key=os.path.getmtime):
        r = jload(p)
        if r:
            best[r.get("die")] = (r, p)
    for die, (r, p) in sorted(best.items()):
        print(f"{die:13s} {r['verdict']:4s} {r.get('item')} src {r.get('src')} failing {r['failing']}  {p}")
    return 0


def cmd_list(a):
    specs, _ = load_spec(a.spec)
    for d, c in specs.items():
        print(f"{d:13s} {c['item']:40s} {c['flow']:10s} mem {c['mem_gb']} golden {(c.get('golden') or {}).get('verdict')}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", default=str(SPEC))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--src", required=True)
    s.add_argument("--die", action="append")
    s.add_argument("--root", default="/srv/opentallas-scratch2/claude/flow-canary/runs")
    s.add_argument("--image", default=IMAGE)
    s.add_argument("--dry", action="store_true")
    l = sub.add_parser("lint")
    l.add_argument("--kit", required=True)
    l.add_argument("--top", required=True)
    l.add_argument("--image", default=IMAGE)
    l.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("--run", required=True)
    c.add_argument("--out")
    m = sub.add_parser("summary")
    m.add_argument("--root", default="/srv/opentallas-scratch2/claude/flow-canary/runs")
    sub.add_parser("list")
    a = ap.parse_args(argv)
    return dict(submit=cmd_submit, lint=cmd_lint, check=cmd_check, summary=cmd_summary, list=cmd_list)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
