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
  ot_clk.py replay  CONFIG --out D [--legacy]   P0: run kit, cmp clock outputs vs the config's reference run
  ot_clk.py register --cal FILE --id ID --cell C --clock-rc R [--route LABEL] [--basis TEXT]
                                                print a registry entry for a die_trial --region-dme-stage-cal file
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
    for k in ("die", "event", "inputs", "stack", "top"):
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


def kit_argv(cfg, out, stage_cal_path=None, workers=None, plan=None):
    """die_trial.py kit argv for a config (flag order is irrelevant to die_trial; values are exact)"""
    i, st, top, reg, res = cfg["inputs"], cfg["stack"], cfg["top"], cfg["region"], cfg["residual"]
    a = ["kit", plan or i["plan"], "--out", str(out)]
    if i.get("views"):
        a += ["--views", i["views"]]
    if i.get("region_map"):
        a += ["--region-trees", i["region_map"]]
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
    if st.get("clock_rc", "ndr") != "ndr":
        a += ["--clock-rc", st["clock_rc"]]
    if st["cell"] != "buf":
        a += ["--clock-cell", st["cell"]]
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
        w = workers if workers is not None else reg.get("workers")
        if w and int(w) > 1:
            a += ["--region-dme-workers", str(int(w))]
    elif reg.get("form", "none") != "none":
        raise ConfigError(f"region.form {reg['form']!r}: only dme / none are wired in P0")
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
        if n == "replay":
            p.add_argument("--python", default=sys.executable)
    r = sub.add_parser("register")
    r.add_argument("--cal", required=True)
    r.add_argument("--id", required=True)
    r.add_argument("--cell", required=True, choices=sorted(CELLS))
    r.add_argument("--clock-rc", required=True, choices=("ndr", "1x"))
    r.add_argument("--route")
    r.add_argument("--basis")
    a = ap.parse_args(argv)
    if a.cmd == "register":
        print(json.dumps(register_entry(a.cal, a.id, a.cell, a.clock_rc, a.route, a.basis), indent=1))
        return 0
    cfg = load_config(a.config)
    registry = load_registry(a.registry)
    if a.cmd == "check":
        ok, _, why = stage_check(cfg, registry)
        print(("PASS" if ok else "FAIL") + ": " + "; ".join(why))
        return 0 if ok else 1
    if a.cmd == "argv":
        ok, why, cal = _prepare(cfg, a.out, a.legacy, registry)
        print(json.dumps(dict(stage_check="PASS" if ok else "FAIL", why=why,
                              argv=kit_argv(cfg, a.out, cal, a.workers)), indent=1))
        return 0
    out = Path(a.out)
    ok, why, cal = _prepare(cfg, out / "kit", a.legacy, registry)
    plan, rebase = rebase_plan(cfg, out)
    args = kit_argv(cfg, out / "kit", cal, a.workers, plan)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ot_clk_argv.json").write_text(json.dumps(dict(config=str(a.config), stage_check="PASS" if ok else "FAIL",
                                                          why=why, pins_rebase=rebase, argv=args), indent=1) + "\n")
    rc = subprocess.call([getattr(a, "python", sys.executable), str(DIE_TRIAL)] + args,
                         stdout=open(out / "kit.log", "w"), stderr=subprocess.STDOUT)
    if rc or a.cmd == "kit":
        print(json.dumps(dict(rc=rc, stage_check="PASS" if ok else "FAIL", out=str(out))))
        return rc
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
            v["diff_keys"] = json_diff_keys(json.loads(x.read_text()), json.loads(y.read_text()))
    meta_only = all(v["identical"] or (v.get("diff_keys") is not None and
                                       all(k.startswith("meta.") for k in v["diff_keys"])) for v in res.values())
    verdict = dict(schema="ot_clk_replay/1", die=cfg["die"], event=cfg["event"].get("name"), config=str(a.config),
                   reference=str(ref), stage_check="PASS" if ok else "FAIL", stage_why=why, pins_rebase=rebase,
                   files=res,
                   replay="IDENTICAL" if all(v["identical"] for v in res.values())
                   else "IDENTICAL_EXCEPT_META" if meta_only else "DIFFERENT")
    (out / "replay.json").write_text(json.dumps(verdict, indent=1) + "\n")
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["replay"] in ("IDENTICAL", "IDENTICAL_EXCEPT_META") else 2


if __name__ == "__main__":
    sys.exit(main())
