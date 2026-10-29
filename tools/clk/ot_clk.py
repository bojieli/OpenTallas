#!/usr/bin/env python3
"""ot-clk: die-agnostic die clock driver (CLK-TOOL-1, phases P0 + P1).

One config file per die (tools/clk/configs/<die>.yaml) describes the die clock build that die_trial.py runs today:
plan event inputs, the clock stack (cell / wire-RC model), the top form (link_htree / spine_fishbone / htree ...),
the region form (DME or none) and the ledgered residual tools (snakes, tap pads).  No die name appears in this file;
die quirks live only in the configs.

P0 (replay): `argv` renders the exact die_trial.py `kit` argv a config stands for; `replay` runs it (fleet host only,
never localhost) into a new directory and compares clock/tree.json + clock/ctree.v byte-for-byte with the reference
run named in the config.

P1 (fail-closed stage model): any build whose region form uses a stage model (region DME) must name a stage-model entry
in tools/clk/stage_registry.json whose key (cell, clock_rc, corner, edge) equals the config's clock stack.  There is no
implicit default: the BUFx24 1x-ladder model that die_trial uses when --region-dme-stage-cal is absent is itself a
registry entry (cell BUFx24) and is rejected on an inverter tree (the DIE-S81-17 failure).  `kit` refuses to run on a
failed check; `argv --legacy` / `replay --legacy` reproduce historical runs and print the stage verdict instead.

Usage:
  ot_clk.py check   CONFIG                      stage-model check (exit 1 on FAIL)
  ot_clk.py argv    CONFIG [--legacy] [--out D] print the die_trial kit argv (JSON list)
  ot_clk.py kit     CONFIG --out D [--workers N] fail-closed build: check, write stage cal, run die_trial kit
                                                (the die_trial kit lands in D/kit, not D)
  ot_clk.py replay  CONFIG --out D [--legacy]   P0: run kit, cmp clock outputs vs the config's reference run
  ot_clk.py replay  CONFIG --out D --compare-only   re-judge an existing replay (no die_trial run)
  ot_clk.py refit   CONFIG --tree T --arr-prefix P --id ID (--tap-from CAL | --tap K1 K2) -o CAL [--write]
                                                per-stack refit on routed legs (fit_dme_stage_cal) -> registry entry
                                                keyed by the config's stack (cell, clock_rc); --write appends it
  ot_clk.py register --cal FILE --id ID --cell C --clock-rc R [--route LABEL] [--basis TEXT]
                                                print a registry entry for a die_trial --region-dme-stage-cal file
  ot_clk.py rec     CONFIG --trial DIR --stage grt|drt   region.form mesh: routed trial -> explicit_mesh_signoff rec

region.form mesh (CLK-TOOL-6): the region clock is built by tools/clk/mesh_form.py from the config section region.mesh
(every die value explicit, no defaults), not by die_trial.  check/argv/kit/replay/rec take the same CONFIG; kit writes
OUT/mesh/<part>/ per region of region.parts; replay compares each part with event.reference_mesh_dirs[part]; refit
refuses (an equal-leg mesh tree consumes no stage model); duty reads the OT_EDGES v1 files of region.mesh.edges: both.
"""
import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DIE_TRIAL = REPO / "tools" / "die_plan" / "die_trial.py"
REGISTRY = HERE / "stage_registry.json"
SCHEMA_CFG = "ot_clk_config/1"
SCHEMA_REG = "ot_clk_stage/1"

# die_trial --clock-cell value -> library cell (die_trial.BUF / die_trial.CLK_INV); inv and inv2 share the cell,
# inv2 places them in pairs (even inverters per leg).
CELLS = {"buf": "BUFx24_ASAP7_75t_R", "inv": "CKINVDCx16_ASAP7_75t_R", "inv2": "CKINVDCx16_ASAP7_75t_R"}
POLARITY = {"buf": "noninv", "inv": "inv", "inv2": "pair"}
STAGE_FORMS = ("dme",)       # region forms whose builder consumes a stage model
MESH_FILES = ("pilot.json", "pilot.def", "run.tcl", "run_ff.tcl", "run.sh")   # mesh-form build outputs compared on replay


class ConfigError(Exception):
    pass


# ---------------------------------------------------------------------------------------------------------------- YAML
def _scalar(s):
    s = s.strip()
    if s == "" or s in ("~", "null"):
        return None
    if s in ("true", "false"):
        return s == "true"
    if s[0] in "\"'" and s[-1] == s[0]:
        return s[1:-1]
    if s[0] == "[" and s[-1] == "]":
        body = s[1:-1].strip()
        return [_scalar(x) for x in body.split(",")] if body else []
    if s[0] == "{" and s[-1] == "}":
        body = s[1:-1].strip()
        return {k.strip(): _scalar(v) for k, v in (pair.split(":", 1) for pair in body.split(","))} if body else {}
    if re.fullmatch(r"[-+]?\d+", s):
        return int(s)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?", s):
        return float(s)
    return s


def _strip_comment(line):
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            q = None if ch == q else q
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def mini_yaml(text):
    """The YAML subset the configs use (block maps, block lists of scalars, flow lists/maps of scalars, comments).
    Used only when PyYAML is absent; test_ot_clk.py checks it against PyYAML on every config."""
    lines = [(len(ln) - len(ln.lstrip(" ")), ln.strip()) for ln in map(_strip_comment, text.splitlines()) if ln.strip()]

    def block(i, ind):
        if lines[i][1].startswith("- "):
            out = []
            while i < len(lines) and lines[i][0] == ind and lines[i][1].startswith("- "):
                out.append(_scalar(lines[i][1][2:]))
                i += 1
            return out, i
        out = {}
        while i < len(lines) and lines[i][0] == ind:
            key, _, rest = lines[i][1].partition(":")
            if rest.strip():
                out[key.strip()] = _scalar(rest)
                i += 1
            elif i + 1 < len(lines) and lines[i + 1][0] > ind:
                out[key.strip()], i = block(i + 1, lines[i + 1][0])
            else:
                out[key.strip()] = None
                i += 1
        return out, i

    doc, i = block(0, lines[0][0]) if lines else ({}, 0)
    if i != len(lines):
        raise ConfigError(f"mini_yaml: cannot parse line {i}: {lines[i][1]!r}")
    return doc


def load_yaml(path):
    text = Path(path).read_text()
    try:
        import yaml
    except ImportError:
        return mini_yaml(text)
    return yaml.safe_load(text)


# ------------------------------------------------------------------------------------------------------------- config
def brace(pattern):
    """bash-style brace expansion: a{x,y}{0..2} -> ax0 ax1 ax2 ay0 ay1 ay2 (bash order)"""
    parts = re.split(r"(\{[^{}]*\})", pattern)
    alts = []
    for p in parts:
        if p.startswith("{") and p.endswith("}"):
            body = p[1:-1]
            m = re.fullmatch(r"(-?\d+)\.\.(-?\d+)", body)
            alts.append([str(k) for k in range(int(m[1]), int(m[2]) + 1)] if m else body.split(","))
        else:
            alts.append([p])
    return ["".join(t) for t in itertools.product(*alts)]


def region_list(spec, cfg):
    """region set spec -> ordered list.  spec: list of names / brace patterns, or {all_from_map: true} (every region
    of inputs.region_map, sorted), or 'all' (die_trial keyword)."""
    if spec is None:
        return None
    if spec == "all":
        return "all"
    if isinstance(spec, dict):
        if spec.get("all_from_map"):
            m = json.loads(Path(cfg["inputs"]["region_map"]).read_text())["part_region"]
            return sorted(set(m.values()))
        raise ConfigError(f"unknown region set spec {spec}")
    out = []
    for item in spec:
        out.extend(brace(str(item)))
    return out


def load_config(path):
    cfg = load_yaml(path)
    if not isinstance(cfg, dict) or cfg.get("schema") != SCHEMA_CFG:
        raise ConfigError(f"{path}: schema must be {SCHEMA_CFG}")
    mesh = (cfg.get("region") or {}).get("form") == "mesh"
    for k in ("die", "event", "inputs", "stack") + (() if mesh else ("top",)):
        if k not in cfg:
            raise ConfigError(f"{path}: missing '{k}'")
    if cfg["stack"].get("cell") not in CELLS:
        raise ConfigError(f"{path}: stack.cell must be one of {sorted(CELLS)}")
    cfg.setdefault("region", {"form": "none"})
    cfg.setdefault("residual", {})
    return cfg


def _fmt(v):
    """number formatting as the die scripts wrote it (250 not 250.0; 1.78 stays 1.78)"""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def rebase_plan(cfg, out):
    """inputs.pins_rebase: plan events whose hard-core pins_file points into a (deleted) worktree are replayed from a
    plan copy whose pins_file paths are rewritten onto the pin tables committed in THIS repo.  Only hard_cores[].pins_file
    is touched (the one plan-relative sidecar die_trial reads besides die_io.json, which must not exist next to such a
    plan); the copy is written beside the kit and the rewrite is recorded.  Returns (plan path, provenance or None)."""
    i = cfg["inputs"]
    rb = i.get("pins_rebase")
    if not rb:
        return i["plan"], None
    src = Path(i["plan"])
    if (src.parent / "die_io.json").is_file():
        raise ConfigError(f"pins_rebase: {src.parent}/die_io.json is a plan-dir sidecar; a moved plan copy would lose it")
    raw = src.read_bytes()
    plan = json.loads(raw)
    old, new = rb["from"], rb.get("to_repo", "")
    done = {}
    for tn, t in sorted(plan.get("partition_types", {}).items()):
        for hc in t.get("hard_cores", []):
            pf = hc.get("pins_file")
            if not pf:
                continue
            if not pf.startswith(old):
                raise ConfigError(f"pins_rebase: type {tn} pins_file {pf!r} does not start with {old!r}")
            rel = new + pf[len(old):]
            tgt = (REPO / rel).resolve()
            if not tgt.is_file() or REPO.resolve() not in tgt.parents:
                raise ConfigError(f"pins_rebase: {rel} is not a file inside the repo ({REPO})")
            hc["pins_file"] = str(tgt)
            done[pf] = dict(repo_path=rel, sha256=hashlib.sha256(tgt.read_bytes()).hexdigest()[:16])
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    dst = out / ("ot_clk_plan_" + src.name)
    dst.write_text(json.dumps(plan, indent=1) + "\n")
    return str(dst), dict(plan=str(src), plan_sha256=hashlib.sha256(raw).hexdigest()[:16], copy=str(dst),
                          pins_files=done)


def fill_region_map(cfg, out, plan=None):
    """inputs.region_fill (CLK-TOOL-7): plan parts missing from inputs.region_map get a region by rule, e.g. parts split
    after the map was made inherit the region of the part they were split from.  Each rule {prefix, from, default}: every
    plan part whose name starts with `prefix` and is not in the map gets map[from] (or `default` if `from` is unmapped).
    The filled map (original order, filled parts appended in plan order) is written beside the kit.
    Returns (region map path or None, provenance or None)."""
    i = cfg["inputs"]
    rules = i.get("region_fill")
    if not rules:
        return i.get("region_map"), None
    if not i.get("region_map"):
        raise ConfigError("inputs.region_fill needs inputs.region_map")
    src = Path(i["region_map"])
    raw = src.read_bytes()
    reg = json.loads(raw)["part_region"]
    names = [p["name"] for p in json.loads(Path(plan or i["plan"]).read_text())["partitions"]]
    added = {}
    for r in rules:
        if set(r) - {"prefix", "from", "default"} or "prefix" not in r:
            raise ConfigError(f"inputs.region_fill rule {r}: keys prefix (required), from, default")
        for n in names:
            if n.startswith(str(r["prefix"])) and n not in reg:
                v = reg.get(r.get("from"), r.get("default"))
                if v is None:
                    raise ConfigError(f"inputs.region_fill {r}: part {n} has no region")
                reg[n] = added[n] = v
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    dst = out / ("ot_clk_regions_" + src.name)
    dst.write_text(json.dumps(dict(part_region=reg), indent=1) + "\n")
    return str(dst), dict(region_map=str(src), sha256=hashlib.sha256(raw).hexdigest()[:16], copy=str(dst),
                          rules=rules, added=added)


def kit_argv(cfg, out, stage_cal_path=None, workers=None, plan=None, region_map=None):
    """die_trial.py kit argv for a config (flag order is irrelevant to die_trial; values are exact)"""
    if is_mesh(cfg):
        raise ConfigError("region.form mesh is built by tools/clk/mesh_form.py (ot_clk kit), not by die_trial")
    i, st, top, reg, res = cfg["inputs"], cfg["stack"], cfg["top"], cfg["region"], cfg["residual"]
    a = ["kit", plan or i["plan"], "--out", str(out)]
    if i.get("views"):
        a += ["--views", i["views"]]
    if region_map or i.get("region_map"):
        a += ["--region-trees", region_map or i["region_map"]]
    if i.get("feed"):
        a += ["--feed", i["feed"]]
    a += ["--tree-form", top["form"]]
    for k, flag in (("leaf_um", "--leaf-um"), ("rep_um", "--rep-um")):
        if top.get(k) is not None:
            a += [flag, _fmt(top[k])]
    if top.get("site_legal"):
        a.append("--tree-site-legal")
    if top.get("site_slide"):
        a.append("--tree-site-slide")
    for k, v in (top.get("opts") or {}).items():
        a += ["--tree-opt", f"{k}={_fmt(v)}"]
    if top.get("rep_on_leg"):                   # blocked leg repeater slides along its planned leg (opt-in)
        a.append("--rep-on-leg")
    if top.get("rep_off_leg_max") is not None:  # kit fails when a repeater lands farther than UM off its leg
        a += ["--rep-off-leg-max", _fmt(top["rep_off_leg_max"])]
    if top.get("rep_reach_max") is not None:    # CLK-TOOL-4: re-place any non-snake leg (global FEED incl.) whose
        a += ["--rep-reach-max", _fmt(top["rep_reach_max"])]   # snapped span > UM; priced record meta.reach_fix
    if top.get("rep_actual_max") is not None:   # post-build guard: every actual cell/tap hop <= UM (actual_reach.json)
        a += ["--rep-actual-max", _fmt(top["rep_actual_max"])]
    if top.get("body_sites"):                   # CLK-TOOL-7: clock sites keep the native cell body legal
        a.append("--clock-body-sites")
    if top.get("chain_hop_max") is not None:    # CLK-TOOL-7: DME chain candidates with a hop > UM are rejected
        a += ["--chain-hop-max", _fmt(top["chain_hop_max"])]
    det = top.get("detour", "astar")
    if det == "adaptive":                       # CLK-TOOL-7: failed A* detour retried around the connected macro wall
        a.append("--detour-adaptive")
    elif det != "astar":
        raise ConfigError(f"top.detour {det!r}: astar | adaptive")
    if st.get("clock_rc", "ndr") != "ndr":
        a += ["--clock-rc", st["clock_rc"]]
    if st["cell"] != "buf":
        a += ["--clock-cell", st["cell"]]
    eb = st.get("edge_balance", "none")
    if eb == "dme_alt":                         # CLK-TOOL-8: region DME branch polarity chosen per node (duty)
        if st["cell"] != "inv2":
            raise ConfigError("stack.edge_balance dme_alt needs stack.cell inv2")
        a.append("--clock-edge-alt")
    elif eb != "none":
        raise ConfigError(f"stack.edge_balance {eb!r}: none | dme_alt")
    if reg.get("form", "none") == "dme":
        mode = reg.get("dme_mode", True)
        a += ["--region-dme"] + ([] if mode is True else [str(mode)])
        only = region_list(reg.get("only"), cfg)
        if only is not None:
            a += ["--region-dme-only", ",".join(only)]
        e = reg.get("early") or {}
        if e.get("tt") is not None:
            a += ["--region-dme-early", _fmt(e["tt"])]
        if e.get("ff") is not None:
            a += ["--region-dme-early-ff", _fmt(e["ff"])]
        if e.get("mode", "hang") != "hang":
            a += ["--region-dme-early-mode", e["mode"]]
        mo = region_list(e.get("merge_only"), cfg)
        if mo:
            a += ["--region-dme-early-merge-only", ",".join(mo)]
        if stage_cal_path:
            a += ["--region-dme-stage-cal", str(stage_cal_path)]
        if reg.get("actual_max") is not None:   # coherent physical DME legs: one snapped legal chain prices + emits each leg
            a += ["--region-dme-actual-max", _fmt(reg["actual_max"])]
        w = workers if workers is not None else reg.get("workers")
        if w and int(w) > 1:
            a += ["--region-dme-workers", str(int(w))]
    elif reg.get("form", "none") == "mesh":
        raise ConfigError("region.form mesh is built by tools/clk/mesh_form.py (ot_clk kit), not by die_trial")
    elif reg.get("form", "none") != "none":
        raise ConfigError(f"region.form {reg['form']!r}: only dme / mesh / none are wired")
    sn = region_list(res.get("snake"), cfg)
    if sn:
        a += ["--region-dme-snake", sn if sn == "all" else ",".join(sn)]
    if res.get("tap_pad"):
        a += ["--tap-pad", res["tap_pad"]]
    if res.get("cell_paths"):
        a.append("--cell-paths")
    for x in cfg.get("extra_argv") or []:      # flags not yet modelled as config keys (listed in the README)
        a.append(str(x))
    return a


# --------------------------------------------------------------------------------------------------- stage registry
def coeff_sha(entry):
    body = {k: entry[k] for k in ("leg", "tap", "leg_FF", "tap_FF") if k in entry}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def load_registry(path=REGISTRY):
    r = json.loads(Path(path).read_text())
    if r.get("schema") != SCHEMA_REG:
        raise ConfigError(f"{path}: schema must be {SCHEMA_REG}")
    return {e["id"]: e for e in r["entries"]}


def stage_check(cfg, registry):
    """-> (ok, entry or None, reasons).  FAIL closed: a stage-consuming region form needs a named registry entry whose
    key matches the stack on cell, clock_rc and every corner/edge the builder uses."""
    reg_form = cfg["region"].get("form", "none")
    if reg_form not in STAGE_FORMS:
        return True, None, [f"region.form={reg_form}: builder balances geometrically, no stage model consumed"]
    st = cfg["stack"]
    want = dict(cell=CELLS[st["cell"]], polarity=POLARITY[st["cell"]], clock_rc=st.get("clock_rc", "ndr"))
    sm = cfg.get("stage_model") or {}
    eid = sm.get("entry")
    if not eid:
        return False, None, ["no stage_model.entry: region DME would fall back to die_trial's built-in BUFx24 1x "
                             "ladder model; name a registry entry fitted on this stack (no implicit default)"]
    e = registry.get(eid)
    if e is None:
        return False, None, [f"stage_model.entry {eid!r} not in the registry"]
    bad = []
    key = e["key"]
    for k, v in want.items():
        if key.get(k) != v:
            bad.append(f"stack {k}={v} but entry {eid} was fitted on {k}={key.get(k)}")
    for c in sm.get("corners", ["TT"]):
        if c not in key.get("corners", []):
            bad.append(f"entry {eid} has no {c} fit")
    if sm.get("edge", "rise") not in key.get("edges", []):
        bad.append(f"entry {eid} has no {sm.get('edge', 'rise')} fit")
    if e.get("coeff_sha") != coeff_sha(e):
        bad.append(f"entry {eid} coefficients do not match their recorded coeff_sha (edited by hand?)")
    if sm.get("coeff_sha") and sm["coeff_sha"] != e.get("coeff_sha"):
        bad.append(f"config pins coeff_sha {sm['coeff_sha']} but entry {eid} is {e.get('coeff_sha')}")
    return (not bad), e, bad or [f"entry {eid} matches {want} ({e.get('basis', '')})"]


def stage_cal_file(entry):
    """die_trial --region-dme-stage-cal JSON for a registry entry; None for the built-in model (die_trial default)"""
    if entry.get("builtin"):
        return None
    d = {k: entry[k] for k in ("leg", "tap", "leg_FF", "tap_FF") if k in entry}
    d["scope"] = f"ot_clk stage registry entry {entry['id']} ({entry.get('basis', '')})"
    d["source"] = entry.get("source", {})
    return d


def register_entry(cal_path, eid, cell, clock_rc, route=None, basis=None):
    c = json.loads(Path(cal_path).read_text())
    corners = ["TT"] + (["FF"] if "leg_FF" in c else [])
    e = dict(id=eid, key=dict(cell=CELLS[cell], polarity=POLARITY[cell], clock_rc=clock_rc, corners=corners,
                              edges=["rise"], route=route),
             basis=basis or c.get("scope", ""), source=dict(file=str(cal_path),
                                                            sha256=hashlib.sha256(Path(cal_path).read_bytes()).hexdigest(),
                                                            **(c.get("source") or {})))
    for k in ("leg", "tap", "leg_FF", "tap_FF", "rms_ps"):
        if k in c:
            e[k] = c[k]
    e["coeff_sha"] = coeff_sha(e)
    return e


def refit_entry(cfg, registry, a):
    """OWNER 12.17 (b): refit the region stage model of CONFIG's own stack on the routed legs of a tree it built.
    Runs fit_dme_stage_cal (rep_um from the config; built_with = the config's current registry model, so rms_built_ps
    shows how far the old model was off) and returns a registry entry keyed by the config's stack.cell/clock_rc."""
    sys.path.insert(0, str(REPO / "tools" / "die_plan"))
    import fit_dme_stage_cal
    st = cfg["stack"]
    argv = ["--tree", a.tree, "--arr-prefix", a.arr_prefix, "--corners", a.corners, "-o", a.o,
            "--rep-um", _fmt((cfg.get("top") or {}).get("rep_um", 250.0))]
    argv += ["--tap-from", a.tap_from] if a.tap_from else ["--tap"] + [str(x) for x in a.tap]
    if a.even_legs:
        argv.append("--even-legs")
    if getattr(a, "placed_stages", False):
        argv.append("--placed-stages")
    ok, cur, _ = stage_check(cfg, registry)
    built = stage_cal_file(cur) if (ok and cur) else None
    if built is not None:
        bp = Path(a.o).with_suffix(".built_with.json")
        bp.write_text(json.dumps(built, indent=1) + "\n")
        argv += ["--built-with", str(bp)]
    fit = fit_dme_stage_cal.main(argv)
    stats = {c: {k: f.get(k) for k in ("legs", "rms_ps", "rms_built_ps")} for c, f in fit["fit"].items()}
    basis = (f"ot_clk refit ({cfg['die']} {cfg['event'].get('name')}) of stack {st['cell']}/{st.get('clock_rc', 'ndr')}"
             f" on routed legs {a.arr_prefix}_<C>; " + ", ".join(f"{c} {v['legs']} legs rms {v['rms_ps']} ps"
                                                               f" (old model {v['rms_built_ps']})" for c, v in stats.items()))
    e = register_entry(a.o, a.id, st["cell"], st.get("clock_rc", "ndr"), a.route, basis)
    e["source"].update(tree=str(a.tree), arrivals=str(a.arr_prefix))
    e["fit"] = stats
    return e


def die_trial_rev(path):
    """provenance of the die_trial.py a build ran: path, file sha256, git commit of its checkout and whether its
    tools/die_plan is dirty (None outside a git checkout)"""
    path = Path(path)
    rev = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else None)
    try:
        g = lambda *x: subprocess.run(["git", "-C", str(path.parent)] + list(x), capture_output=True, text=True,
                                      timeout=60).stdout.strip()
        rev["git_rev"] = g("rev-parse", "@") or None
        rev["dirty"] = bool(g("status", "--porcelain", "--", ".")) if rev["git_rev"] else None
    except (OSError, subprocess.SubprocessError):
        rev["git_rev"] = rev["dirty"] = None
    return rev


def reference_file(ref, f):
    """die runs that post-process the kit (clock_body_bays overlay) keep die_trial's own output as <stem>_GENERATED<ext>;
    compare against that when present"""
    g = Path(ref) / f"{Path(f).stem}_GENERATED{Path(f).suffix}"
    return g if g.is_file() else Path(ref) / f


def json_diff_keys(a, b, pre=""):
    """differing keys of two JSON objects: top level, and one level down inside 'meta' (tool-version provenance)"""
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            if k == "meta" and isinstance(a.get(k), dict) and isinstance(b.get(k), dict):
                out += json_diff_keys(a[k], b[k], "meta.")
            else:
                out.append(pre + k)
    return out


def ctree_clock_cells(ctree_v):
    """library cells instantiated in a ctree.v (the physical record a tree.json meta.clock_cell must agree with)"""
    return sorted(set(re.findall(r"^\s*([A-Za-z0-9]+x[0-9A-Za-z]+_ASAP7_75t_[RLS])\s", Path(ctree_v).read_text(), re.M)))


def compare_replay(cfg, config, out, ok, why, rebase):
    """replay verdict of out/kit/clock vs the config's reference clock dir.  IDENTICAL_EXCEPT_META = every compared file
    byte-identical or differing only in tree.json meta keys; a meta key ABSENT in the reference (schema field added
    after the reference run, e.g. meta.clock_cell) is listed as meta_added and, for clock_cell, must name the cell
    family that the byte-identical ctree.v actually instantiates (else DIFFERENT)."""
    ref = Path(cfg["event"]["reference_clock_dir"])
    res = {}
    for f in cfg["event"].get("compare", ["tree.json", "ctree.v"]):
        x, y = out / "kit" / "clock" / f, reference_file(ref, f)
        res[f] = dict(identical=x.is_file() and y.is_file() and x.read_bytes() == y.read_bytes(),
                      sha_new=hashlib.sha256(x.read_bytes()).hexdigest()[:16] if x.is_file() else None,
                      sha_ref=hashlib.sha256(y.read_bytes()).hexdigest()[:16] if y.is_file() else None)
    for f, v in res.items():          # tree.json: name the differing top-level / meta keys (provenance-only diffs)
        x, y = out / "kit" / "clock" / f, reference_file(ref, f)
        v["reference_file"] = y.name
        if not v["identical"] and f.endswith(".json") and x.is_file() and y.is_file():
            jx, jy = json.loads(x.read_text()), json.loads(y.read_text())
            v["diff_keys"] = json_diff_keys(jx, jy)
            mx, my = jx.get("meta") or {}, jy.get("meta") or {}
            v["meta_added"] = [f"meta.{k}" for k in sorted(set(mx) - set(my))]
            if "clock_cell" in mx and "clock_cell" not in my:
                cv = out / "kit" / "clock" / "ctree.v"
                want = CELLS.get(mx["clock_cell"])
                have = ctree_clock_cells(cv) if cv.is_file() else []
                v["clock_cell_check"] = dict(meta=mx["clock_cell"], cell=want, ctree_cells=have,
                                             consistent=bool(want) and have == [want]
                                             and res.get("ctree.v", {}).get("identical", False))
    meta_only = all(v["identical"] or (v.get("diff_keys") is not None and
                                       all(k.startswith("meta.") for k in v["diff_keys"]) and
                                       v.get("clock_cell_check", {}).get("consistent", True))
                    for v in res.values())
    return dict(schema="ot_clk_replay/1", die=cfg["die"], event=cfg["event"].get("name"), config=str(config),
                reference=str(ref), stage_check="PASS" if ok else "FAIL", stage_why=why, pins_rebase=rebase,
                files=res,
                replay="IDENTICAL" if all(v["identical"] for v in res.values())
                else "IDENTICAL_EXCEPT_META" if meta_only else "DIFFERENT")


# ------------------------------------------------------------------------------------------------- region mesh form
def is_mesh(cfg):
    return (cfg.get("region") or {}).get("form") == "mesh"


def mesh_parts(cfg):
    parts = region_list(cfg["region"].get("parts"), cfg)
    if not parts or parts == "all":
        raise ConfigError("region.form mesh needs an explicit region.parts list")
    return parts


def mesh_plan(cfg):
    """what a mesh-form kit builds: inputs (with sha), parts, the region.mesh section and its sha"""
    import mesh_form
    i = cfg["inputs"]
    mesh_form.params(cfg["region"].get("mesh"))
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] if Path(p).is_file() else None
    return dict(form="mesh", builder="tools/clk/mesh_form.py", plan=i["plan"], plan_sha256=sha(i["plan"]),
                tree=i["tree"], tree_sha256=sha(i["tree"]), parts=mesh_parts(cfg),
                mesh_sha=hashlib.sha256(json.dumps(cfg["region"]["mesh"], sort_keys=True).encode()).hexdigest()[:16])


def mesh_kit(cfg, out):
    import mesh_form
    built = {}
    for p in mesh_parts(cfg):
        built[p] = mesh_form.build(cfg["inputs"]["plan"], cfg["inputs"]["tree"], p, Path(out) / "mesh" / p,
                                   cfg["region"]["mesh"])
    return built


def compare_mesh(cfg, config, out):
    refs = (cfg["event"].get("reference_mesh_dirs") or {})
    files = cfg["event"].get("compare", list(MESH_FILES))
    res = {}
    for p in mesh_parts(cfg):
        if p not in refs:
            res[p] = dict(reference=None, identical=False, why="no event.reference_mesh_dirs entry")
            continue
        fr = {}
        for f in files:
            x, y = Path(out) / "mesh" / p / f, Path(refs[p]) / f
            fr[f] = dict(identical=x.is_file() and y.is_file() and x.read_bytes() == y.read_bytes(),
                         sha_new=hashlib.sha256(x.read_bytes()).hexdigest()[:16] if x.is_file() else None,
                         sha_ref=hashlib.sha256(y.read_bytes()).hexdigest()[:16] if y.is_file() else None)
        res[p] = dict(reference=refs[p], files=fr, identical=all(v["identical"] for v in fr.values()))
    return dict(schema="ot_clk_replay/1", die=cfg["die"], event=cfg["event"].get("name"), config=str(config),
                form="mesh", parts=res, replay="IDENTICAL" if all(v["identical"] for v in res.values()) else "DIFFERENT")


# ---------------------------------------------------------------------------------------------------------- commands
def _prepare(cfg, out, legacy, registry):
    ok, entry, why = stage_check(cfg, registry)
    if not ok and not legacy:
        raise SystemExit("ot_clk: STAGE MODEL CHECK FAIL (build refused):\n  " + "\n  ".join(why))
    cal = None
    if entry is not None and ok:
        d = stage_cal_file(entry)
        if d is not None:
            out = Path(out)
            out.mkdir(parents=True, exist_ok=True)
            cal = out / "ot_clk_stage_cal.json"
            cal.write_text(json.dumps(d, indent=1) + "\n")
    elif legacy and (cfg.get("stage_model") or {}).get("legacy_cal"):
        cal = cfg["stage_model"]["legacy_cal"]         # replay of a run that passed a cal file directly
    return ok, why, cal


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("check", "argv", "kit", "replay"):
        p = sub.add_parser(n)
        p.add_argument("config")
        p.add_argument("--registry", default=str(REGISTRY))
        if n != "check":
            p.add_argument("--out", default="OUT")
            p.add_argument("--legacy", action="store_true",
                           help="reproduce a historical run: stage check reported, not enforced")
            p.add_argument("--workers", type=int, default=None)
        if n in ("kit", "replay"):
            p.add_argument("--die-trial", default=str(DIE_TRIAL),
                           help="die_trial.py to run (default: this checkout); path + git sha are recorded")
        if n == "replay":
            p.add_argument("--python", default=sys.executable)
            p.add_argument("--compare-only", action="store_true",
                           help="do not run die_trial: compare the clock outputs already in --out/kit/clock")
    rf = sub.add_parser("refit")
    rf.add_argument("config")
    rf.add_argument("--registry", default=str(REGISTRY))
    rf.add_argument("--tree", required=True)
    rf.add_argument("--arr-prefix", required=True)
    rf.add_argument("--corners", default="TT,FF")
    rf.add_argument("--id", required=True)
    g = rf.add_mutually_exclusive_group(required=True)
    g.add_argument("--tap-from")
    g.add_argument("--tap", nargs=2, type=float)
    rf.add_argument("--even-legs", action="store_true")
    rf.add_argument("--placed-stages", action="store_true",
                    help="fit retained native parent_of/sites chains, including isolated region coupons")
    rf.add_argument("--route")
    rf.add_argument("-o", required=True)
    rf.add_argument("--write", action="store_true", help="append the entry to --registry (refuses a duplicate id)")
    rc_ = sub.add_parser("rec", help="region.form mesh: routed trial -> explicit_mesh_signoff rec")
    rc_.add_argument("config")
    rc_.add_argument("--trial", required=True)
    rc_.add_argument("--stage", required=True, choices=("grt", "drt"))
    r = sub.add_parser("register")
    r.add_argument("--cal", required=True)
    r.add_argument("--id", required=True)
    r.add_argument("--cell", required=True, choices=sorted(CELLS))
    r.add_argument("--clock-rc", required=True, choices=("ndr", "1x"))
    r.add_argument("--route")
    r.add_argument("--basis")
    local = sub.add_parser("local-entry", help="place one native clock-load isolation buffer per emitted stage group")
    import local_entry
    local_entry.add_arguments(local)
    duty = sub.add_parser("duty", help="measured both-edge duty with shared clock calibration")
    sys.path.insert(0, str(REPO / "tools" / "die_plan"))
    import clock_duty
    clock_duty.add_arguments(duty)
    a = ap.parse_args(argv)
    if a.cmd == "local-entry":
        return local_entry.run(a)
    if a.cmd == "duty":
        return clock_duty.run(a)
    if a.cmd == "register":
        print(json.dumps(register_entry(a.cal, a.id, a.cell, a.clock_rc, a.route, a.basis), indent=1))
        return 0
    cfg = load_config(a.config)
    if is_mesh(cfg):
        return main_mesh(cfg, a)
    if a.cmd == "rec":
        raise ConfigError("rec needs region.form mesh")
    registry = load_registry(a.registry)
    if a.cmd == "refit":
        e = refit_entry(cfg, registry, a)
        if a.write:
            r = json.loads(Path(a.registry).read_text())
            if e["id"] in [x["id"] for x in r["entries"]]:
                raise ConfigError(f"registry already has an entry {e['id']!r}")
            r["entries"].append(e)
            Path(a.registry).write_text(json.dumps(r, indent=1) + "\n")
        print(json.dumps(e, indent=1))
        return 0
    if a.cmd == "check":
        ok, _, why = stage_check(cfg, registry)
        print(("PASS" if ok else "FAIL") + ": " + "; ".join(why))
        return 0 if ok else 1
    if a.cmd == "argv":
        ok, why, cal = _prepare(cfg, a.out, a.legacy, registry)
        rmap, _ = fill_region_map(cfg, a.out)
        print(json.dumps(dict(stage_check="PASS" if ok else "FAIL", why=why,
                              argv=kit_argv(cfg, a.out, cal, a.workers, region_map=rmap)), indent=1))
        return 0
    out = Path(a.out)
    ok, why, cal = _prepare(cfg, out / "kit", a.legacy, registry)
    plan, rebase = rebase_plan(cfg, out)
    rmap, rfill = fill_region_map(cfg, out, plan)
    args = kit_argv(cfg, out / "kit", cal, a.workers, plan, rmap)
    out.mkdir(parents=True, exist_ok=True)
    dt = Path(a.die_trial).resolve()
    (out / ("ot_clk_argv_compare.json" if getattr(a, "compare_only", False) else "ot_clk_argv.json")).write_text(json.dumps(dict(config=str(a.config), stage_check="PASS" if ok else "FAIL",
                                                          why=why, pins_rebase=rebase, die_trial=die_trial_rev(dt),
                                                          argv=args, **({"region_fill": rfill} if rfill else {})),
                                                          indent=1) + "\n")
    if getattr(a, "compare_only", False):          # re-judge an existing replay's clock outputs, no rebuild
        if not (out / "kit" / "clock").is_dir():
            print(f"compare-only: {out / 'kit' / 'clock'} missing", file=sys.stderr)
            return 2
        rc = 0
    else:
        rc = subprocess.call([getattr(a, "python", sys.executable), str(dt)] + args,
                             stdout=open(out / "kit.log", "w"), stderr=subprocess.STDOUT)
    if rc or a.cmd == "kit":
        print(json.dumps(dict(rc=rc, stage_check="PASS" if ok else "FAIL", out=str(out))))
        return rc
    verdict = compare_replay(cfg, a.config, out, ok, why, rebase)
    (out / "replay.json").write_text(json.dumps(verdict, indent=1) + "\n")
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["replay"] in ("IDENTICAL", "IDENTICAL_EXCEPT_META") else 2


def main_mesh(cfg, a):
    """check/argv/kit/replay/rec for region.form mesh (no die_trial run, no stage model)"""
    if a.cmd == "check":
        mesh_plan(cfg)
        print("PASS: region.form=mesh: equal-leg tree balanced by construction, no stage model consumed")
        return 0
    if a.cmd == "refit":
        raise ConfigError("refit: region.form mesh consumes no stage model (equal-leg tree by construction)")
    if a.cmd == "rec":
        sys.path.insert(0, str(REPO / "tools" / "die_plan"))
        import explicit_mesh_signoff
        import mesh_form
        r, warn = mesh_form.rec(a.trial, a.stage, cfg["region"]["mesh"], explicit_mesh_signoff.mesh_rc)
        if warn:
            print("WARNING:", warn)
        print(json.dumps(dict(rec=str(Path(a.trial) / f"rec_{a.stage}.json"), nodes=len(r["nodes"]), segs=len(r["segs"]),
                              taps=len(r["taps"]))))
        return 0
    if a.cmd == "argv":
        print(json.dumps(dict(stage_check="PASS", why=["region.form=mesh"], mesh=mesh_plan(cfg)), indent=1))
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    plan = mesh_plan(cfg)
    if not getattr(a, "compare_only", False):
        plan["built"] = mesh_kit(cfg, out)
    (out / ("ot_clk_argv_compare.json" if getattr(a, "compare_only", False) else "ot_clk_argv.json")).write_text(
        json.dumps(dict(config=str(a.config), stage_check="PASS", mesh=plan), indent=1) + "\n")
    if a.cmd == "kit":
        print(json.dumps(dict(rc=0, form="mesh", out=str(out), parts=plan["parts"])))
        return 0
    verdict = compare_mesh(cfg, a.config, out)
    (out / "replay.json").write_text(json.dumps(verdict, indent=1) + "\n")
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["replay"] == "IDENTICAL" else 2


if __name__ == "__main__":
    sys.exit(main())
