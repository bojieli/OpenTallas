#!/usr/bin/env python3
"""LANE-CONSTS (LANEAGE-SWEEP 11-24, COORD; FABLE-RC-QC a3974c38 ruling (2); report only, r703).

Class: a generated consumer (compiler input, program / ROM image + digest, calendar json, a core parameter compiled into the
RTL) bakes lane ages / transport edges / calendar offsets from a metadata file of an OLDER die instead of the bound plan.
QC tt_ctlm C1g: the program was compiled with R_CMD/R_HR/R_SS/R_AG 19/19/17/17 (lane_ages_dv2f14bi.json) and the core with
XPF_TRANSPORT_EDGES 21 (HR_SOURCE_CONTRACT, never measured) while the bound lanes deliver 14/10/10/13 (xpf = 1 + R_HR = 11):
boot faults, every gate passed.  The fix of the class: those constants are OUTPUTS of the bound plan, derived from its
LATCHECK, and every consumer reads them from there (or is compared with them).

One registry (lane_consts_registry.json next to this file) names, per die,
  consts     NAME <- one LATCHECK lane (exact "lane" id, or "lane_re" fullmatch on the lane id, or "match" on
             src/bus_out/dst/bus_in fields) with law  value = delivered + offset  (offset default 0), or
             NAME <- "expr" over other consts of the die (+ - * // max min, integers), e.g. XPF_TRANSPORT_EDGES = 1 + R_HR, or
             NAME <- "param_regen" {param, inst_re}: the value the bind hook regenerated into the bound RTL (--bind
             BIND_DIR/param_regen.json changed[].bound; one value on every instance, else SPLIT), e.g. KV ECTL RESPONSE_LAT
  consumers  where a baked copy of a const lives, with a reader:
             json      glob (tree-relative) + dotted key or segment list (e.g. results/**/*ctlm_metadata_source.json relay.R_HR;
                       ["buses", {"id": "tt_ctlm.hr -> dvs_W5.hr_wi"}, "age_edges"] for ctlm_image's default relay table)
             sv_param  glob + parameter name: the declared default (rtl/**/qfd_tt_ctlm_dv*.sv XPF_TRANSPORT_EDGES)
             inst_param  module regex + parameter: every #(.P(v)) override in the BOUND RTL dir (--bind-rtl), or with
                       "root": "tree" in the tree's RTL (a core master wrapper that pins the value, e.g. corepub39)
             regex     glob + a regex whose group 1 is the integer (a constant inside a generator script)
             each with "generator" (the tool that bakes it) and optional "delegate" (a check that already judges it, e.g.
             ADV-CTLM-AGES: the row is still listed, marked delegated).

    lane_consts.py derive    --die D --latcheck LATCHECK.json [--bind BIND_DIR] [--out lane_consts.json]
    lane_consts.py compare   --die D --latcheck LATCHECK.json --tree TREE [--bind-rtl BIND_DIR/rtl] [--tsv OUT] [--json OUT] [--strict]
    lane_consts.py lane-ages --die qwen_compute --latcheck LATCHECK.json --out lane_ages.json   (ctlm_image.py --lane-ages input)
    lane_consts.py fixed-census --die D --plan PLAN.json --latcheck LATCHECK.json [--tsv OUT]   (fixed_cycles > 0 lanes: which
                   observed register stages carry them; NONE / FIXED-IN-CORE rows need a named register: FABLE-RC-ALL d73d2275)

derive = the bind / compose OUTPUT (schema opentallas.die_plan.lane_consts.v1: value, lane, delivered, law, latcheck sha256).
compare = report: one row per (consumer, file or instance): MATCH | MISMATCH | UNMEASURED (const not derivable: lane missing or
split) | NOT-FOUND (reader found nothing in the tree).  Exit 0 always (report only, r703); --strict exits 4 on any MISMATCH
(for the later promotion of a functional mismatch, the one place a hard fail is right: FABLE-RC-QC a3974c38 (2)).
LATCHECK json = gen_lane_latcheck.py / lane_asbuilt_latency.py --json (lanes[].lane/src/bus_out/dst/bus_in/delivered); a bind's
bind_lane_asbuilt.json has the same shape.
"""
import argparse
import ast
import glob
import hashlib
import json
import operator
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REGISTRY = HERE / "lane_consts_registry.json"
SCHEMA = "opentallas.die_plan.lane_consts.v1"
LANE_AGES_SCHEMA = "opentallas.qwen.ctlm-lane-ages.v1"
MAX_FILES = 200
DIE_ALIAS = {"qc": "qwen_compute", "kv": "qwen_kvsys", "head": "s81_head", "s81": "s81"}


def die_name(d):
    return DIE_ALIAS.get(d.lower(), d)


def load_registry(path=None):
    return json.loads(Path(path or REGISTRY).read_text())


def load_latcheck(path):
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    lanes = d["lanes"] if isinstance(d, dict) else d
    return lanes, hashlib.sha256(raw).hexdigest()


# ------------------------------------------------------------------------------------------------------------ derive
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv}


def eval_expr(expr, env):
    """integer arithmetic over const names: + - * // max() min() and int literals.  KeyError on an unknown / underived name."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        if isinstance(n, ast.Name):
            if env.get(n.id) is None:
                raise KeyError(n.id)
            return int(env[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("max", "min") and not n.keywords:
            return {"max": max, "min": min}[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"unsupported expression element {ast.dump(n)[:60]}")
    return ev(ast.parse(str(expr), mode="eval"))


def select_lanes(lanes, c):
    if c.get("lane"):
        return [x for x in lanes if x.get("lane") == c["lane"]]
    if c.get("lane_re"):
        rx = re.compile(c["lane_re"])
        return [x for x in lanes if rx.fullmatch(str(x.get("lane", "")))]
    m = c.get("match") or {}
    if m:
        return [x for x in lanes if all(re.fullmatch(str(v), str(x.get(k, ""))) for k, v in m.items())]
    return []


def _from_param_regen(c, bind_dir):
    pr = c["param_regen"]
    r = dict(law=f"param_regen {pr['param']}" + (f" inst~{pr['inst_re']}" if pr.get("inst_re") else ""), why=c.get("why"))
    p = Path(bind_dir) / "param_regen.json" if bind_dir else None
    if not p or not p.is_file():
        return dict(r, value=None, status="UNMEASURED", note="no --bind dir with param_regen.json")
    d = json.loads(p.read_text())
    rx = re.compile(pr.get("inst_re", ".*"))
    vals = sorted({int(x["bound"]) for x in d.get("changed", []) if x.get("param") == pr["param"] and rx.fullmatch(str(x.get("inst", "")))
                   and str(x.get("bound", "")).lstrip("-").isdigit()})
    if len(vals) == 1:
        return dict(r, value=vals[0], status="OK", lanes=[f"param_regen:{pr['param']}"])
    return dict(r, value=None, status="SPLIT" if vals else "UNMEASURED", delivered=vals or None)


def derive(die, lanes, reg, latcheck=None, sha=None, bind_dir=None):
    die = die_name(die)
    out = {}
    rows = [c for c in reg.get("consts", []) if die_name(c["die"]) == die]
    for c in rows:                                   # lane consts first
        if "expr" in c:
            continue
        if "param_regen" in c:                       # the bind hook's regenerated RTL value (BIND_DIR/param_regen.json)
            out[c["name"]] = _from_param_regen(c, bind_dir)
            continue
        hit = select_lanes(lanes, c)
        vals = sorted({x.get("delivered") for x in hit if x.get("delivered") is not None})
        r = dict(law=f"delivered + {int(c.get('offset', 0))}", why=c.get("why"), lanes=[x.get("lane") for x in hit][:8])
        if len(vals) == 1:
            r.update(value=int(vals[0]) + int(c.get("offset", 0)), delivered=int(vals[0]), status="OK")
        else:
            r.update(value=None, delivered=vals or None, status="SPLIT" if vals else "UNMEASURED")
        out[c["name"]] = r
    pending = [c for c in rows if "expr" in c]
    for _ in range(len(pending) + 1):                # exprs in dependency order (simple fixpoint)
        left = []
        for c in pending:
            env = {k: v.get("value") for k, v in out.items()}
            try:
                out[c["name"]] = dict(value=eval_expr(c["expr"], env), law=c["expr"], why=c.get("why"), status="OK")
            except KeyError:
                left.append(c)
        pending = left
    for c in pending:
        out[c["name"]] = dict(value=None, law=c["expr"], why=c.get("why"), status="UNMEASURED")
    return dict(schema=SCHEMA, die=die, latcheck=str(latcheck) if latcheck else None, latcheck_sha256=sha,
                generator="tools/die_plan/lane_consts.py derive", consts=out)


# ------------------------------------------------------------------------------------------------------------ readers
def _strip_sv(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def _files(root, pattern):
    if not root:
        return []
    return sorted(p for p in glob.glob(str(Path(root) / pattern), recursive=True) if Path(p).is_file())[:MAX_FILES]


def _dig(d, key):
    """key: a dotted string, or a list of segments (str = dict key / list index; {field: value} = the first list element whose
    fields equal those values; use the list form when a key or value holds a dot, e.g. a relay bus id 'tt_ctlm.cmd -> dvs_W5.cmd_wi')."""
    for k in (key if isinstance(key, list) else str(key).split(".")):
        if isinstance(k, dict):
            d = next((x for x in (d if isinstance(d, list) else []) if isinstance(x, dict)
                      and all(x.get(f) == v for f, v in k.items())), None)
            if d is None:
                return None
            continue
        if isinstance(k, int):
            k = str(k)
        if isinstance(d, dict) and k in d:
            d = d[k]
        elif isinstance(d, list) and k.isdigit() and int(k) < len(d):
            d = d[int(k)]
        else:
            return None
    return d


def read_baked(rd, tree, bind_rtl=None):
    """-> [(where, value)] ; value None when the file matched but held no readable integer."""
    kind = rd.get("kind")
    got = []
    if kind == "json":
        for f in _files(tree, rd["glob"]):
            try:
                d = json.loads(Path(f).read_text())
            except (OSError, ValueError):
                got.append((f, None))
                continue
            items = d if isinstance(d, list) and rd.get("each") else [d]
            for i, it in enumerate(items):
                v = _dig(it, rd["key"])
                if v is None and len(items) > 1:
                    continue
                tag = f if len(items) == 1 else f"{f}[{(it.get(rd['each']) if isinstance(it, dict) else i)}]"
                got.append((tag, v if isinstance(v, int) else None))
    elif kind == "sv_param":
        rx = re.compile(r"\b(?:local)?parameter\b[^;=]*?\b" + re.escape(rd["param"]) + r"\s*=\s*(\d+)")
        for f in _files(tree, rd["glob"]):
            for m in rx.finditer(_strip_sv(Path(f).read_text(errors="replace"))):
                got.append((f, int(m.group(1))))
    elif kind == "inst_param":
        mrx = re.compile(rd["module_re"])
        prx = re.compile(r"\.\s*" + re.escape(rd["param"]) + r"\s*\(\s*(\d+)\s*\)")
        irx = re.compile(r"(?<![\w$.])([A-Za-z_]\w*)\s*#\s*\(([^;]*?)\)\s*([A-Za-z_][\w$]*)\s*\(", re.S)
        root = tree if rd.get("root") == "tree" else bind_rtl
        for f in _files(root, rd.get("glob", "**/*.sv")) + ([] if rd.get("glob") else _files(root, "**/*.v")):
            for m in irx.finditer(_strip_sv(Path(f).read_text(errors="replace"))):
                if mrx.fullmatch(m.group(1)):
                    p = prx.search(m.group(2))
                    if p:
                        got.append((f"{Path(f).name}:{m.group(3)}", int(p.group(1))))
    elif kind == "regex":
        rx = re.compile(rd["regex"], re.M)
        for f in _files(tree, rd["glob"]):
            for m in rx.finditer(Path(f).read_text(errors="replace")):
                got.append((f, int(m.group(1))))
    else:
        raise ValueError(f"unknown reader kind {kind}")
    return got


# ------------------------------------------------------------------------------------------------------------ compare
def compare(die, derived, reg, tree, bind_rtl=None):
    die = die_name(die)
    rows = []
    consts = derived["consts"]
    for c in reg.get("consumers", []):
        if die_name(c["die"]) != die:
            continue
        k = consts.get(c["const"], {})
        want = k.get("value")
        base = dict(consumer=c["consumer"], die=die, const=c["const"], measured=want, measured_lanes=",".join(k.get("lanes") or []),
                    generator=c.get("generator"), delegate=c.get("delegate"), baked_from=c.get("baked_from"))
        try:
            got = read_baked(c["reader"], tree, bind_rtl)
        except (OSError, ValueError, re.error) as e:
            rows.append(dict(base, where=None, baked=None, verdict="NOT-FOUND", note=f"{type(e).__name__}: {str(e)[:120]}"))
            continue
        if not got:
            rows.append(dict(base, where=c["reader"].get("glob") or c["reader"].get("module_re"), baked=None, verdict="NOT-FOUND"))
            continue
        for where, v in got:
            if want is None:
                verdict = "UNMEASURED"
            elif v is None:
                verdict = "NOT-FOUND"
            else:
                verdict = "MATCH" if int(v) == int(want) else "MISMATCH"
            rows.append(dict(base, where=str(where), baked=v, verdict=verdict))
    return rows


def summary(rows):
    s = {}
    for r in rows:
        s[r["verdict"]] = s.get(r["verdict"], 0) + 1
    return s


COLS = ("consumer", "die", "const", "baked", "measured", "verdict", "where", "measured_lanes", "generator", "baked_from", "delegate")


def tsv(rows):
    out = ["\t".join(COLS)]
    for r in rows:
        out.append("\t".join("" if r.get(c) is None else str(r.get(c)) for c in COLS))
    return "\n".join(out) + "\n"


def lane_ages(derived):
    """ctlm_image.py --lane-ages document (schema of tools/qwen_layerbench/lane_ages_export.py) from the bound LATCHECK."""
    c = derived["consts"]
    need = ("R_CMD", "R_HR", "R_SS", "R_AG")
    miss = [k for k in need if c.get(k, {}).get("value") is None]
    if miss:
        raise SystemExit(f"lane-ages: {miss} not derivable from {derived['latcheck']} ({ {k: c.get(k, {}).get('status') for k in miss} })")
    doc = dict(schema=LANE_AGES_SCHEMA, die=derived["die"],
               why="lane age = the bound plan's LATCHECK delivered cycles of the tt_ctlm -> W5 lanes (tools/die_plan/lane_consts.py, "
                   "LANEAGE-SWEEP 11-24); replaces fwd_lanes E+1 of an old GEN die",
               source=derived["latcheck"], source_sha256=derived["latcheck_sha256"],
               lanes={k: dict(lanes=c[k].get("lanes"), delivered=c[k].get("delivered")) for k in c if k.startswith("R_")})
    for k in ("R_CMD", "R_HR", "R_SS", "R_AG", "R_ST"):
        if c.get(k, {}).get("value") is not None:
            doc[k] = c[k]["value"]
    if c.get("XPF_TRANSPORT_EDGES", {}).get("value") is not None:
        doc["XPF_TRANSPORT_EDGES"] = c["XPF_TRANSPORT_EDGES"]["value"]
    return doc


# ------------------------------------------------------------------------------------------------------------ fixed census
SIDE_PAT = {"pads": "u_b{io}_{bus}_pad*", "bound_ist": "u_ist_{bus}_*", "core_chain": "u_ist_{bus}__<cores>_*",
            "lpad": "u_lpad_{bus} (ot_dp_dly D)", "bound_lob": "u_lob_{bus}__<leaf>__<port>_<bit>_*"}


def fixed_census(plan, lanes):
    """FABLE-RC-ALL d73d2275 (HEAD coll_WN0_u: fixed_cycles 1, no register in either core, LATCHECK believed it): every plan lane
    with fixed_cycles > 0 and the LATCHECK-observed register stages that carry it.  class BACKED (bound-RTL stages >= fixed),
    BACKED+KIT-PREDICTED (needs the kit_istations stations LATCHECK predicts), FIXED-IN-CORE (gen_lane_latcheck --fixed-in-core:
    the cycles are taken on trust: the core register must be named, see register), NONE (fixed exceeds every observed stage),
    NOT-IN-LATCHECK."""
    by = {x.get("lane"): x for x in lanes}
    rows = []
    for l in plan.get("lanes", []):
        f = int(l.get("fixed_cycles") or 0)
        if f <= 0:
            continue
        x = by.get(l["id"])
        if not x:
            rows.append(dict(lane=l["id"], fixed=f, cls="NOT-IN-LATCHECK"))
            continue
        obs = []
        for side, io, bus in (("source", "out", x.get("bus_out")), ("receiver", "in", x.get("bus_in"))):
            for k, v in sorted((x.get(side) or {}).items()):
                if k not in ("face", "kit_ist") and isinstance(v, int) and v:
                    obs.append((f"{side}.{k}", v, SIDE_PAT.get(k, "<" + k + ">").format(io=io, bus=bus)))
        kit = sum(int((x.get(s) or {}).get("kit_ist") or 0) for s in ("source", "receiver"))
        n = sum(v for _, v, _ in obs)
        if x.get("fixed_in_core") is not None:
            cls = "FIXED-IN-CORE"
        elif f <= n:
            cls = "BACKED"
        elif f <= n + kit:
            cls = "BACKED+KIT-PREDICTED"
        else:
            cls = "NONE"
        reg = "; ".join(f"{k}={v} {p}" for k, v, p in obs) + (f"; kit_ist={kit} (kit_istations, predicted)" if kit else "")
        rows.append(dict(lane=l["id"], src=x.get("src"), src_type=x.get("src_type"), dst=x.get("dst"), dst_type=x.get("dst_type"),
                         fixed=f, observed=n, kit_predicted=kit, fixed_in_core=x.get("fixed_in_core"), cls=cls,
                         register=reg or ("<core register: name it in the plan>" if cls == "FIXED-IN-CORE" else "NONE")))
    return rows


def report_latency_packages(plan_path, packages):
    """Compare a generated latency package header with its plan's generator digest."""
    from gen import plan_digest

    expected = plan_digest(json.loads(plan_path.read_text()))
    for package in packages:
        try:
            if package.suffix == ".json":
                observed = json.loads(package.read_text()).get("plan_digest")
            else:
                with package.open() as source:
                    header = source.readline()
                match = re.search(r"\bplan digest ([0-9a-f]{16})\b", header)
                observed = match[1] if match else None
        except (OSError, ValueError):
            observed = None
        verdict = "LATPKG-MATCH" if observed == expected else "LATPKG-STALE"
        print(f"{verdict} {package} plan={expected} package={observed or 'UNKNOWN'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["derive", "compare", "lane-ages", "fixed-census", "latpkg"])
    ap.add_argument("--plan", type=Path, help="fixed-census or latpkg: the bound plan")
    ap.add_argument("--die")
    ap.add_argument("--latcheck", type=Path)
    ap.add_argument("--latpkg", type=Path, action="append", help="generated latency JSON or SV package; repeatable")
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--tree", type=Path, help="compare: the bound kit tree (tools/ rtl/ results/ physical/)")
    ap.add_argument("--bind-rtl", type=Path, help="compare: the bind output rtl dir (inst_param readers)")
    ap.add_argument("--bind", type=Path, help="the bind output dir (param_regen consts: BIND/param_regen.json)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--tsv", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--strict", action="store_true", help="exit 4 on any MISMATCH (not used by any gate yet: r703 report only)")
    a = ap.parse_args(argv)
    if a.cmd == "latpkg":
        if not a.plan or not a.latpkg:
            ap.error("latpkg requires --plan and --latpkg")
        report_latency_packages(a.plan, a.latpkg)
        return 0
    if not a.die or not a.latcheck:
        ap.error(f"{a.cmd} requires --die and --latcheck")
    lanes, sha = load_latcheck(a.latcheck)
    if a.cmd == "fixed-census":
        rows = fixed_census(json.loads(a.plan.read_text()), lanes)
        cols = ("lane", "src", "src_type", "dst", "dst_type", "fixed", "observed", "kit_predicted", "fixed_in_core", "cls", "register")
        t = "\t".join(cols) + "\n" + "".join("\t".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + "\n" for r in rows)
        (a.tsv.write_text(t) if a.tsv else sys.stdout.write(t))
        s = {}
        for r in rows:
            s[r["cls"]] = s.get(r["cls"], 0) + 1
        print(f"LANE_CONSTS {die_name(a.die)} FIXED_CENSUS {json.dumps(s, sort_keys=True)}", file=sys.stderr)
        return 4 if (a.strict and s.get("NONE")) else 0
    reg = load_registry(a.registry)
    d = derive(a.die, lanes, reg, a.latcheck, sha, a.bind)
    if a.cmd == "derive":
        js = json.dumps(d, indent=1) + "\n"
        (a.out.write_text(js) if a.out else sys.stdout.write(js))
        bad = {k: v["status"] for k, v in d["consts"].items() if v["status"] != "OK"}
        print(f"LANE_CONSTS {d['die']} DERIVE {len(d['consts'])} consts" + (f" not-derived={bad}" if bad else ""), file=sys.stderr)
        return 0
    if a.cmd == "lane-ages":
        doc = lane_ages(d)
        js = json.dumps(doc, indent=1) + "\n"
        (a.out.write_text(js) if a.out else sys.stdout.write(js))
        return 0
    rows = compare(a.die, d, reg, a.tree, a.bind_rtl)
    t = tsv(rows)
    (a.tsv.write_text(t) if a.tsv else sys.stdout.write(t))
    if a.json:
        a.json.write_text(json.dumps(dict(schema=SCHEMA + ".compare", derived=d, rows=rows, summary=summary(rows)), indent=1) + "\n")
    s = summary(rows)
    print(f"LANE_CONSTS {d['die']} REPORT {json.dumps(s, sort_keys=True)}", file=sys.stderr)
    return 4 if (a.strict and s.get("MISMATCH")) else 0


if __name__ == "__main__":
    sys.exit(main())
