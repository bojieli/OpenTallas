#!/usr/bin/env python3
"""obs_sync: keep the plan's per-core blockage ceiling (hard_cores[].obs_max, default M5) and size
(outline_um) in step with the core's real LEF (OBS layers, SIZE); ceiling = highest layer with >= 10% OBS area, wall = highest with > 50%.  OBS-SYNC-1, 2026-11-12.

Why: plan-level models (route_supply, core_place, g2, proto_sweep, placement_obstacles, die_clock_mesh) read
obs_max (or the 12.1a default M5) and never look at the LEF.  VISLAYOUT3-S81-SLICE found S81 coll_lane cores
recorded as blocked up to M5 whose signed LEF also has OBS on M6, and ot_s81dv_norm_finish whose LEF has no OBS at all.

Truth order for a core module (first hit wins):
  1. a SIGNED repo core view (die cores/**/signoff.json beside the LEF)          -> "signed"
  2. the plan's own lef, unless it is a whole-block M1-M7 template                -> "plan-lef"
  3. any other repo LEF named <module>.lef (not *_tpl)                             -> "repo-lef"
  4. route_supply_views.json (signed-view measurement) / route_supply_kit_views.json (kit-wave macros/*.lef)
  5. nothing: the core has no LEF yet; the plan ceiling stays and the row is reported "no-lef".

Usage:
  obs_sync.py audit  [--die D ...] [--repo R] [--tsv OUT]      table of every hard-core module
  obs_sync.py sync   --die D [--write] [--lower]                 rewrite plan obs_max: raise to the LEF ceiling (--lower: also lower)
Library:
  lef_ceiling_for(h, die, repo)         -> "M6" | None   LEF-derived ceiling of one hard_cores entry
  apply_lef_ceilings(plan, die, repo)   -> plan copy whose hard_cores carry the LEF-derived obs_max (load-time sync)
"""
import argparse
import collections
import copy
import gzip
import json
import os
import re
import sys
from pathlib import Path

DIES = ("s81", "s81_head", "qwen_compute", "qwen_kvsys", "hbm")
DEFAULT_CEILING = "M5"            # METHODOLOGY 12.1a new-tile default, what g2/proto_sweep assume without obs_max
SIZE_TOL_UM = 0.02
ANY_FRAC = 0.01                   # a layer with >= 1% OBS area counts as touched (porous views)
CEIL_FRAC = 0.10                  # the blockage ceiling = highest layer with >= 10% OBS area (a 3% sliver is not a ceiling)
HERE = Path(__file__).resolve().parent
# plan of record per die (tools/fleet/release_tree_plan.py PLANS, 11-12): repo-relative plan file
PLAN_OF_RECORD = {
    "s81": "physical/die_plan/s81/plan_h2_2249.json",
    "s81_head": "physical/die_plan/s81_head/plan_of_record/l48uo/source_plan.json.gz",
    "qwen_compute": "physical/die_plan/qwen_compute/plan_of_record/plan_qc52t.json",
    "qwen_kvsys": "physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json",
    "hbm": "physical/die_plan/hbm/plan_of_record/d44v_gqi_cp1109_q3vm/die_plan.json.gz",
}
_RECT = r"\s*RECT\s+(?:MASK\s+\d+\s+)?([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)"


def lnum(layer):
    m = re.fullmatch(r"M(\d+)", str(layer or ""))
    return int(m.group(1)) if m else 0


def lef_facts(path_or_text, macro=None):
    """{size, obs {L: frac}, obs_top, obs_rects, pin_layers {L: n}, pg_layers} of one LEF MACRO, None if no SIZE."""
    txt = path_or_text
    if isinstance(path_or_text, Path) or (isinstance(path_or_text, str) and "\n" not in path_or_text):
        try:
            txt = Path(path_or_text).read_text(errors="replace")
        except OSError:
            return None
    if macro:
        m = re.search(r"MACRO\s+" + re.escape(macro) + r"\b(.*?)\nEND\s+" + re.escape(macro), txt, re.S)
        if m:
            txt = m.group(1)
    sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt)
    if not sz:
        return None
    W, H = float(sz.group(1)), float(sz.group(2))
    area = W * H
    pins, pgl = collections.Counter(), collections.Counter()
    acc, nrect = collections.defaultdict(float), collections.Counter()
    state, cur, pin_rects, pin_pg = None, None, [], False     # state: None | "pin" | "obs"
    rect_re = re.compile(_RECT)
    for ln in txt.splitlines():
        s = ln.strip()
        if not s:
            continue
        w0 = s.split(None, 1)[0]
        if state is None:
            if w0 == "PIN":
                state, cur, pin_rects, pin_pg = "pin", None, [], False
            elif w0 == "OBS":
                state, cur = "obs", None
            continue
        if w0 == "END":
            if state == "obs" and s == "END":
                state = None
            elif state == "pin" and s != "END":          # END <pinname>
                for L in pin_rects:
                    (pgl if pin_pg else pins)[L] += 1
                state = None
            continue
        if w0 == "LAYER":
            cur = s.split()[1]
        elif w0 == "USE" and state == "pin":
            pin_pg = s.split()[1] in ("POWER", "GROUND")
        elif w0 == "RECT" and cur:
            if state == "pin":
                pin_rects.append(cur)
            else:
                m = rect_re.match(ln)
                if m:
                    x0, y0, x1, y1 = map(float, m.groups())
                    acc[cur] += abs(x1 - x0) * abs(y1 - y0)
                    nrect[cur] += 1
    obs = {L: round(min(1.0, a / area), 4) for L, a in acc.items() if re.fullmatch(r"M\d", L) and area}
    top = max([lnum(L) for L, f in obs.items() if f > 0.5] or [0])
    anyt = max([lnum(L) for L, f in obs.items() if f >= ANY_FRAC] or [0])
    ct = max([lnum(L) for L, f in obs.items() if f >= CEIL_FRAC] or [0])
    return dict(size=[W, H], obs=obs, obs_top=("M%d" % top) if top else None, obs_any_top=("M%d" % anyt) if anyt else None,
                obs_ceil=("M%d" % ct) if ct else None,
                obs_rects=dict(nrect), pin_layers=dict(pins), pg_layers=dict(pgl))


def is_template(f):
    return bool(f) and all(f["obs"].get("M%d" % k, 0) > 0.99 for k in range(1, 8))


# --------------------------------------------------------------------------------------------- sources
_IDX = {}


def repo_lef_index(repo):
    """{module: [lef paths]} of physical/ + tools/ + results/ LEFs (module = file stem); walked once per repo."""
    repo = str(Path(repo).resolve())
    if repo in _IDX:
        return _IDX[repo]
    idx = _IDX[repo] = collections.defaultdict(list)
    for root in ("physical", "tools", "results"):
        for r, ds, fs in os.walk(Path(repo) / root):
            for f in fs:
                if f.endswith(".lef"):
                    idx[f[:-4]].append(str(Path(r) / f))
    return idx


def repo_lef_for(module, repo, die_dir=None):
    """Best non-template repo LEF of a module name: prefer the die's own tree, then physical/die_plan, ref_tile, rest
    (ties: shortest path, then lexicographic).  None when the repo holds none."""
    c = [p for p in repo_lef_index(repo).get(module, []) if "_tpl" not in p]
    if not c:
        return None
    dd = str(die_dir) if die_dir else None

    def rank(p):
        return (0 if dd and p.startswith(dd) else 1, 0 if "/physical/die_plan/" in p else 1, 0 if "/physical/ref_tile/" in p else 1,
                len(p), p)
    for p in sorted(c, key=rank):
        f = lef_facts(Path(p))
        if f and f["obs"] and not is_template(f):      # a pin-only contract LEF (no OBS block) is not a blockage truth
            return p
    return None


def signed_lefs(die_dir):
    out = {}
    root = Path(die_dir) / "cores"
    if root.is_dir():
        for so in sorted(root.rglob("signoff.json")):
            try:
                txt = so.read_text(errors="replace")
            except OSError:
                continue
            if "SIGNED" not in txt and '"signed": true' not in txt.lower():
                continue
            for lef in sorted(so.parent.glob("*.lef")):
                out.setdefault(lef.stem.replace("_tpl", ""), str(lef))
    return out


def _json(p):
    p = Path(p)
    try:
        if p.suffix == ".gz":
            with gzip.open(p, "rt") as f:
                return json.load(f)
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


class Sources:
    def __init__(self, die, repo, plan_dir=None):
        self.die, self.repo = die, Path(repo)
        self.die_dir = self.repo / "physical" / "die_plan" / die
        self.refs = [Path(plan_dir)] if plan_dir else []
        self.signed = signed_lefs(self.die_dir)
        for d in self.refs:
            for k, v in signed_lefs(d).items():
                self.signed.setdefault(k, v)
        self.idx = repo_lef_index(self.repo)
        self.views = _json(HERE / "route_supply_views.json").get("views", {})
        self.kit = _json(HERE / "route_supply_kit_views.json").get(die, {})
        self._f = {}

    def facts(self, path):
        if path not in self._f:
            self._f[path] = lef_facts(Path(path))
        return self._f[path]

    def alts(self, mod):
        """distinct (obs_top, size) among the non-template repo LEF copies of a module (ambiguity of the repo-lef pick)."""
        out = set()
        for p in self.idx.get(mod, []):
            if "_tpl" in p:
                continue
            f = self.facts(p)
            if f and not is_template(f):
                out.add((f["obs_top"], tuple(f["size"])))
        return out

    def ref(self, rel):
        for d in self.refs + [self.repo]:
            if (Path(d) / rel).is_file():
                return Path(d) / rel
        return self.repo / rel

    def truth(self, h):
        """(source, path-or-key, facts) of the best LEF for hard-core entry h, or ("no-lef", None, None)."""
        mod = h["module"]
        if mod in self.signed:
            f = self.facts(self.signed[mod])
            if f:
                return "signed", self.signed[mod], f
        pl = h.get("lef")
        if pl:
            p = self.ref(pl)
            f = self.facts(str(p)) if p.is_file() else None
            if f and not is_template(f):
                return "plan-lef", str(p), f
        rl = repo_lef_for(mod, self.repo, self.die_dir)
        if rl:
            return "repo-lef", rl, self.facts(rl)
        v = self.views.get(mod)
        if v and v.get("obs_top"):
            top = lnum(v["obs_top"])
            cov = float(v.get("coverage", 1.0))
            return "views-table", mod, dict(size=None, obs={"M%d" % k: cov for k in range(1, top + 1)}, obs_top=v["obs_top"],
                                            obs_any_top=v["obs_top"], obs_ceil=v["obs_top"], obs_rects={}, pin_layers={}, pg_layers={})
        stem = Path(str(h.get("lef") or "")).stem
        for key in (mod, stem):
            kv = self.kit.get(key) if key else None
            if kv:
                obs = {L: float(x) for L, x in kv["obs"].items()}
                top = max([lnum(L) for L, x in obs.items() if x > 0.5] or [0])
                return "kit-lef", key, dict(size=kv.get("size"), obs=obs, obs_top=("M%d" % top) if top else None,
                                            obs_any_top=("M%d" % max([lnum(L) for L, x in obs.items() if x >= ANY_FRAC] or [0])) or None,
                                            obs_ceil=("M%d" % max([lnum(L) for L, x in obs.items() if x >= CEIL_FRAC] or [0])) or None,
                                            obs_rects={}, pin_layers={}, pg_layers={})
        if h.get("lef") and self.ref(h["lef"]).is_file():
            f = self.facts(str(self.ref(h["lef"])))
            if f:
                return "template-only", str(self.ref(h["lef"])), f
        return "no-lef", None, None


def classify(h, src, f):
    """mismatch classes of one core against its truth LEF (list; empty = in step)."""
    plan_ceil = h.get("obs_max") or DEFAULT_CEILING
    if f is None:
        return ["no-lef"]
    if src == "template-only":
        return ["template-only"]
    out = []
    top, ct, pc = lnum(f["obs_top"]), lnum(f.get("obs_ceil")), lnum(plan_ceil)
    if not f["obs"]:
        out.append("LEF-missing-OBS")
    elif top > pc:
        out.append("under-modelled")             # a wall (>50% of the area) above the plan ceiling
    elif ct > pc:
        out.append("under-modelled-partial")     # no wall above it, but >= 10% OBS on a higher layer
    elif ct < pc:
        out.append("over-modelled")              # the plan blocks layers the LEF leaves (almost) free
    elif top < pc:
        out.append("porous")                     # ceiling agrees; the layers above the wall are only partly blocked
    sz = f.get("size")
    ol = h.get("outline_um")
    if sz and ol:
        a = max(abs(sz[0] - ol[0]), abs(sz[1] - ol[1]))
        b = max(abs(sz[0] - ol[1]), abs(sz[1] - ol[0]))
        if min(a, b) > SIZE_TOL_UM:
            out.append("size-mismatch")
    return out


def lef_ceiling_for(h, die, repo, sources=None):
    """LEF-derived blockage ceiling of one hard_cores entry ("M6"), or None when no LEF says (keep the plan's)."""
    s = sources or Sources(die, repo)
    src, _, f = s.truth(h)
    if f is None or src == "template-only" or not f["obs"]:
        return None
    return f.get("obs_ceil") or f["obs_top"]


def apply_lef_ceilings(plan, die, repo, sources=None):
    """Load-time sync: copy of the plan dict whose hard_cores carry obs_max = LEF-derived ceiling where a LEF exists."""
    s = sources or Sources(die, repo)
    P = copy.deepcopy(plan)
    for t in P.get("partition_types", {}).values():
        for h in t.get("hard_cores", []) or []:
            c = lef_ceiling_for(h, die, repo, s)
            if c:
                h["obs_max"] = c
    return P


# --------------------------------------------------------------------------------------------- audit
def plan_path(die, repo, plan=None):
    return Path(repo) / (plan or PLAN_OF_RECORD[die])


def audit_die(die, repo, plan_rel=None):
    pp = plan_path(die, repo, plan_rel)
    plan = _json(pp)
    S = Sources(die, repo, pp.parent)
    mods = collections.OrderedDict()
    for tn, t in (plan.get("partition_types") or {}).items():
        for h in t.get("hard_cores", []) or []:
            m = mods.setdefault(h["module"], dict(h=h, types=set(), insts=0, ceilings=set(), outlines=set()))
            m["types"].add(tn)
            m["insts"] += 1
            m["ceilings"].add(h.get("obs_max") or "-")
            m["outlines"].add(tuple(h.get("outline_um") or ()))
    ninst = collections.Counter(p["type"] for p in plan.get("partitions", []))
    rows = []
    for mod, m in mods.items():
        h = m["h"]
        src, path, f = S.truth(h)
        cls = classify(h, src, f)
        rows.append(dict(die=die, core=mod,
                         plan_ceiling="/".join(sorted(c for c in m["ceilings"] if c != "-")) or "-(M5 default)",
                         lef_src=src, lef=(os.path.relpath(path, repo) if path and os.path.isabs(path) else path),
                         lef_obs_layers=(",".join("%s:%.2f" % (L, v) for L, v in sorted(f["obs"].items(), key=lambda x: lnum(x[0])))
                                         if f else ""),
                         lef_wall=(f or {}).get("obs_top"), lef_ceiling=(f or {}).get("obs_ceil"),
                         lef_pin_layers=",".join(sorted((f or {}).get("pin_layers", {}), key=lnum)),
                         lef_size=(f or {}).get("size"), plan_outline=sorted(m["outlines"])[0] if m["outlines"] else None,
                         mismatch=",".join(cls) or "ok", lef_alts=len(S.alts(mod)) if src == "repo-lef" else "", types=len(m["types"]), instances=m["insts"],
                         partitions=sum(ninst[t] for t in m["types"]), type_names=sorted(m["types"])))
    return rows


def write_sync(die, repo, write, plan_rel=None, lower=False):
    pf = plan_path(die, repo, plan_rel)
    plan = _json(pf)
    S = Sources(die, repo, pf.parent)
    changes = []
    for tn, t in (plan.get("partition_types") or {}).items():
        for h in t.get("hard_cores", []) or []:
            c = lef_ceiling_for(h, die, repo, S)
            if c and c != h.get("obs_max"):
                if h.get("obs_max") is None and c == DEFAULT_CEILING:
                    continue            # same as the implicit default: leave the field absent
                if lnum(c) < lnum(h.get("obs_max") or DEFAULT_CEILING) and not lower:
                    continue            # a plan ceiling above the LEF may be a deliberate keep-out: lowered only on --lower
                changes.append((tn, h["inst"], h.get("obs_max"), c))
                h["obs_max"] = c
    if write and changes:
        pf.write_text(json.dumps(plan, indent=1) + "\n")
    return changes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("audit", "sync"))
    ap.add_argument("--die", action="append")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--plan", help="repo-relative plan file (default: the plan of record of --die)")
    ap.add_argument("--tsv")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--lower", action="store_true",
                    help="sync also LOWERS a plan ceiling that is above the LEF (default: raise only, i.e. add the blockage the LEF has)")
    a = ap.parse_args(argv)
    dies = a.die or list(DIES)
    if a.cmd == "audit":
        rows = []
        for d in dies:
            rows += audit_die(d, a.repo, a.plan if a.die and len(a.die) == 1 else None)
        cols = ["die", "core", "plan_ceiling", "lef_wall", "lef_ceiling", "lef_obs_layers", "lef_pin_layers", "mismatch", "lef_src", "lef_size",
                "plan_outline", "types", "instances", "partitions", "lef_alts", "lef"]
        lines = ["\t".join(cols)] + ["\t".join(str(r[c]) for c in cols) for r in rows]
        if a.tsv:
            Path(a.tsv).write_text("\n".join(lines) + "\n")
        else:
            print("\n".join(lines))
        cnt = collections.Counter((r["die"], r["mismatch"]) for r in rows)
        for (d, m), n in sorted(cnt.items()):
            print("SUMMARY", d, m, n, file=sys.stderr)
        return 0
    for d in dies:
        ch = write_sync(d, a.repo, a.write, a.plan, a.lower)
        for c in ch:
            print(d, *c)
        print("%s: %d core entries %s" % (d, len(ch), "rewritten" if a.write else "would change"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
