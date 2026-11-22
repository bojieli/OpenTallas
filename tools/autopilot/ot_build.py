#!/usr/bin/env python3
"""ot-build: one dependency-driven command from a die plan to a signed-off type (FABLE-PIPELINE-R1, OWNER 11-21).

    ot-build bind  --tree SRC --plan PLAN [--asbuilt AB] --out-root R [--rt RT] [--env OT_K=V ..] [--emit-j N|auto]
                   [--status | --dry] [--upto pre|elab|r8|bind|latcheck|bpc] [--force NODE ..] [--r8-pin-pre F --r8-pin-extra N]
        ON THE HOST THAT HAS THE TREE.  The bind stage of one (tree, plan): each node below is stamped with the content hash of its
        inputs (tools/autopilot/build_graph.py) and only stale nodes run, in order:
          pre       seconds, before any elaboration: plan keys against the schema.py of the runtime pin, every manifest input present,
                    row modules in the RTL, plan geometry (plan_gate_pre of the launch tree), clock / reset taps inside the type outline
          elab      bind.py elab; keyed on the as-built manifest + the sources, NOT on the plan: a plan row change reuses it
          r8        land_align r8 dies: the bind head once (bind.py r8-prepass), then the landing table AND every land_r8_extra table
                    are re-derived from the bound depths (r8_refresh.py) when they differ; a carried table can no longer be stale
          bind      ONE strict bind (--strict --all-gaps), per-type emit in OT_BIND_EMIT_J forked workers; 0 errors required
          latcheck  lane_asbuilt_latency.py on the whole bound die        bpc   bound_param_check.py
        The tools are the runtime pin's (rt/<sha>), composed with the tree's design data by rt_launch_tree.sh; nothing is written
        into SRC unless it is the lane's own unsealed fork (then the R8 tables are refreshed in place, as r8_refresh.py always did;
        for a sealed tree the refreshed tables go to OUT/.ot-build/plan and the bind uses them from there).
        OUT = R/b_<hash of plan + manifest + tree + bind tools + env>: a new plan gets a new OUT (kits of the old bind keep theirs) and
        adopts the elab of a sibling OUT with the same elab key.  Prints `OT-BUILD OUT <dir>` and `OT-BUILD EFFECTIVE <json>`.
        Exit 0 built / fresh, 1 a node failed (the message names the input), 3 --status / --dry found stale nodes, 2 usage.

    ot-build plan-overlay --from PLANDIR --to DIR [--copy NAME ..]
        a private plan delta without a 50 GB tree copy: DIR gets a real copy of each NAME (default: every *.json directly in PLANDIR
        smaller than 256 MB is linked, the named ones are copied) and symlinks to everything else.  Edit DIR/<plan>.json, then
        `ot-build bind --tree SRC --plan DIR/<plan>.json`.

    ot-build DIE TYPE [--plan P] [--tree T] --lane LANE [--goal bind|kit|finish] [--host H] [--dry]
        ON THE HUB.  Resolves the die's tree / plan / as-built / bind env from the wave config, picks the least loaded host that holds
        the tree, runs the bind stage there through ot-run (only when `--status` says a node is stale), then the kit through
        kit_wave.py private-spec --tree --bind-out + run-item --goal (place .. route, sign-off, routed LEC) and the export enqueue.

Exit codes of the hub form: 0 goal reached, 1 failed (message), 2 usage, 3 --dry found work."""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_graph as G  # noqa: E402

RT_ROOT = Path(os.environ.get("OT_RT_ROOT") or "/srv/opentallas-scratch2/claude/rt")
BIND_NODES = ("pre", "elab", "r8", "bind", "latcheck", "bpc")
SRC_GLOBS = ("*.sv", "*.v", "*.svh", "*.vh", "*.json", "*.f", "*.mem", "*.hex")
ELAB_DROP = re.compile(r"^(land_.*|.*note.*|kit_.*|internal_stations.*)$")


def log(msg):
    print(msg, flush=True)


# ---- runtime pin and launch tree --------------------------------------------------------------------------------------------------
def rt_resolve(rt=None):
    """-> (dir, sha12): the runtime pin.  rt = None / 'current' -> RT_ROOT/current resolved ONCE to its sha directory"""
    p = Path(rt) if rt and "/" in str(rt) else RT_ROOT / (rt or "current")
    p = Path(os.path.realpath(p))
    if not (p / "tools" / "die_plan" / "bind.py").is_file():
        raise G.BuildError(f"runtime pin {p}: no tools/die_plan/bind.py (not an rt snapshot; give --rt <sha12> or a path)")
    return p, p.name[:12]


def tree_write_refusal(path, root):
    """tools/die_plan/tree_write_guard.py refusal ('' when this checkout has no guard)"""
    g = Path(__file__).resolve().parents[1] / "die_plan" / "tree_write_guard.py"
    if not g.is_file():
        return ""
    from importlib.machinery import SourceFileLoader
    return SourceFileLoader("tree_write_guard", str(g)).load_module().refusal(str(path), str(root))


def launch_tree(src, rt_dir, root):
    """L = rt tools + the tree's design data (tools/autopilot/rt_launch_tree.sh); idempotent"""
    src, rt_dir = Path(src), Path(rt_dir)
    L = Path(root) / f"{src.name}__rt{rt_dir.name[:12]}"
    if (L / ".rt_launch_ok").is_file():
        return L
    sh = rt_dir / "tools" / "autopilot" / "rt_launch_tree.sh"
    r = subprocess.run(["bash", str(sh), str(src), str(rt_dir), str(L)], capture_output=True, text=True)
    if r.returncode != 0 or not (L / ".rt_launch_ok").is_file():
        raise G.BuildError(f"cannot compose the launch tree {L} from {src} + {rt_dir}: {(r.stderr or r.stdout).strip()[-300:]}")
    return L


def tool_closure(rt_dir, scripts, sub="tools/die_plan"):
    """the files of the runtime pin a tool run depends on: the import closure of `scripts` inside tools/die_plan (every `import x` /
    `from x import`, also inside functions) plus the non-Python data files of that directory.  The runtime pin moves many times a
    day; a stamp keyed on its sha would re-bind every die on every unrelated tools commit, one keyed on this closure only when a
    file the bind can load changed."""
    import ast
    d = Path(rt_dir) / sub
    seen, todo = set(), [s for s in scripts]
    while todo:
        n = todo.pop()
        if n in seen or not (d / n).is_file():
            continue
        seen.add(n)
        try:
            tree = ast.parse((d / n).read_text())
        except (SyntaxError, OSError, UnicodeDecodeError):
            continue
        for x in ast.walk(tree):
            names = []
            if isinstance(x, ast.Import):
                names = [a.name.split(".")[0] for a in x.names]
            elif isinstance(x, ast.ImportFrom) and x.module:
                names = [x.module.split(".")[-1], x.module.split(".")[0]] + [a.name for a in x.names]
            elif isinstance(x, ast.Call) and getattr(x.func, "attr", getattr(x.func, "id", "")) in ("import_module", "__import__") \
                    and x.args and isinstance(x.args[0], ast.Constant) and isinstance(x.args[0].value, str):
                names = [x.args[0].value.split(".")[-1]]
            todo += [m + ".py" for m in names if m + ".py" not in seen]
    data = [f for f in sorted(os.listdir(d)) if (d / f).is_file() and not f.endswith((".py", ".pyc", ".md"))] if d.is_dir() else []
    return sorted(seen) + data


def tools_input(label, rt_dir, scripts):
    return G.Input.files(label, tool_closure(rt_dir, scripts), root=Path(rt_dir) / "tools" / "die_plan")


def tree_id(src):
    """the identity of a source tree for stamps: its seal when sealed (src_manifest), else None (inputs are hashed file by file)"""
    return G.seal_of(src)


# ---- plan helpers -----------------------------------------------------------------------------------------------------------------
def load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except OSError as e:
        raise G.BuildError(f"cannot read {p}: {e.strerror}") from e
    except ValueError as e:
        raise G.BuildError(f"{p} is not JSON: {e}") from e


def asbuilt_of(plan_path, asbuilt_path):
    if asbuilt_path:
        return load_json(asbuilt_path), Path(asbuilt_path)
    raw = load_json(plan_path)
    if "asbuilt" not in raw:
        raise G.BuildError(f"{plan_path}: no `asbuilt` section and no --asbuilt")
    return raw["asbuilt"], Path(plan_path)


def ab_base(ab, manifest_path, tree):
    b = ab.get("base")
    if b is None:
        return Path(tree)
    return Path(b) if Path(b).is_absolute() else (Path(manifest_path).parent / b)


def r8_tables(ab, base):
    """[(key, index, Path)] of the R8 landing tables the manifest names (land_r8 + land_r8_extra)"""
    out = []
    if ab.get("land_r8"):
        p = Path(ab["land_r8"])
        out.append(("land_r8", None, p if p.is_absolute() else Path(base) / p))
    for i, x in enumerate(ab.get("land_r8_extra") or []):
        p = Path(x)
        out.append(("land_r8_extra", i, p if p.is_absolute() else Path(base) / p))
    return out


def _xy_list(v):
    """every [x, y] pair in a tap value: [x, y] | [[x, y], ..] | [{xy / tap_um / at: [x, y]}, ..]"""
    if isinstance(v, (list, tuple)):
        if len(v) == 2 and all(isinstance(q, (int, float)) and not isinstance(q, bool) for q in v):
            return [tuple(v)]
        res = []
        for q in v:
            res += _xy_list(q)
        return res
    if isinstance(v, dict):
        for k in ("xy", "tap_um", "at", "xy_um"):
            if k in v:
                return _xy_list(v[k])
    return []


TAP_KEYS = (("clock", "tap_um"), ("clock", "taps"), ("clock", "added_taps"), ("clock", "edge_clocks"),
            ("reset", "tap_um"), ("reset", "local_taps_um"))


def taps_findings(plan, eps=1e-6):
    """FAIL TAPS lines: a clock / reset tap of a type outside that type's outline (the 11-21 re-grid class: taps shifted by a stale
    offset land outside or on the wrong side of the outline; bind / gen find it an hour in)"""
    out = []
    for tn, t in sorted((plan.get("partition_types") or {}).items()):
        o = t.get("outline_um")
        if not (isinstance(o, list) and len(o) == 2):
            continue
        w, h = float(o[0]), float(o[1])
        for sec, key in TAP_KEYS:
            v = (t.get(sec) or {}).get(key) if isinstance(t.get(sec), dict) else None
            if v is None:
                continue
            bad = [(x, y) for x, y in _xy_list(v) if not (-eps <= x <= w + eps and -eps <= y <= h + eps)]
            if bad:
                out.append(f"FAIL TAPS type {tn}: {len(bad)} {sec}.{key} point(s) outside the outline {w:g} x {h:g} um "
                           f"(first: {bad[0][0]:g},{bad[0][1]:g}); re-derive the taps for this outline before the bind")
    return out


def bpc_type_modules(plan_path, types):
    """-> the bound modules of the named types (their kit RTL)"""
    if not types:
        return set()
    pt = load_json(plan_path).get("partition_types") or {}
    return {str((pt.get(tn) or {}).get("module") or tn) for tn in types}


def bpc_hits(err, mods):
    """a BOUND-PARAM finding ("BOUND-PARAM <mod>.<param>: passed by <file>.sv:<inst>, ..") in one of mods' RTL"""
    m = re.match(r"BOUND-PARAM (\S+?)\.[^.\s:]+:", err)
    if m and m.group(1) in mods:
        return True
    return any(re.search(r"(^|[\s,/])" + re.escape(x) + r"\.sv:", err) for x in mods)


def overlay_dir(src_dir, dst, copy=()):
    """dst = symlinks to every entry of src_dir, real copies of the names in `copy` (the files a private delta edits)"""
    src_dir, dst = Path(src_dir), Path(dst)
    if not src_dir.is_dir():
        raise G.BuildError(f"plan directory {src_dir} missing")
    dst.mkdir(parents=True, exist_ok=True)
    for e in sorted(os.listdir(src_dir)):
        d = dst / e
        if d.exists() or d.is_symlink():
            continue
        if e in copy:
            shutil.copy2(src_dir / e, d)
            os.chmod(d, 0o644)
        else:
            os.symlink(os.path.realpath(src_dir / e), d)
    return dst


# ---- the bind stage ---------------------------------------------------------------------------------------------------------------
class BindStage:
    def __init__(self, a):
        self.a = a
        self.src = Path(os.path.realpath(a.tree))
        if not self.src.is_dir():
            raise G.BuildError(f"tree {a.tree} missing on {os.uname().nodename}")
        # real paths: a tree reached through a scratch alias (epyc2: scratch2 -> scratch3) is still the tree
        self.plan = Path(os.path.realpath(a.plan))
        self.remap_base = getattr(a, "remap_base", None)
        self.asbuilt = Path(os.path.realpath(a.asbuilt)) if a.asbuilt else None
        self.rt_dir, self.rt_sha = rt_resolve(a.rt)
        self.env = {}
        for kv in a.env or []:
            k, eq, v = kv.partition("=")
            if not eq or not re.fullmatch(r"[A-Z][A-Z0-9_]*", k):
                raise G.BuildError(f"--env {kv!r}: KEY=VALUE")
            self.env[k] = v
        self.seal = tree_id(self.src)
        self.root = Path(os.path.abspath(a.out_root))
        self.ab, self.ab_path = asbuilt_of(self.plan, self.asbuilt)
        self.base = ab_base(self.ab, self.ab_path, self.src)
        self.tools = tools_input("tools", self.rt_dir, ["bind.py", "plan_gate_pre.py", "land_r8_derive.py", "r8_refresh.py"])
        ctx = dict(plan=G.sha_json_file(self.plan), asbuilt=G.sha_obj(self.ab), tree=self.seal or str(self.src),
                   tools=self.tools.hash(), env=self.env)
        self.ctx = G.sha_obj(ctx)[:12]
        self.out = self.root / f"b_{self.ctx}"
        self.L = None
        self.eff_asbuilt = self.asbuilt          # replaced by the r8 node when it refreshes tables into the overlay

    # -- inputs
    def _tree_input(self, label, paths):
        if self.seal:
            return G.Input.value(label, "seal:" + self.seal)
        files = []
        for p in paths:
            p = Path(p)
            if p.is_dir():
                files += [str(p / r) for r in G.tree_files(p, SRC_GLOBS)]
            else:
                files.append(str(p))
        return G.Input.files(label, files)

    def _manifest_sources(self):
        sys.path.insert(0, str(self.rt_dir / "tools" / "die_plan"))
        try:
            import plan_gate_pre as PGP
            _, res = PGP.manifest_paths(self.ab, self.ab_path.parent, self.src)
            return [p for _, p, _ in res]
        except Exception:
            return [self.base / r for r in (self.ab.get("rtl_roots") or ["rtl"])]
        finally:
            sys.path.pop(0)

    def effective(self):
        f = self.out / G.STAMP_DIR / "effective.json"
        try:
            return json.loads(f.read_text())
        except (OSError, ValueError):
            return {}

    def _eff_asbuilt(self):
        e = self.effective().get("asbuilt")
        return Path(e) if e else self.asbuilt

    def _plan_side(self):
        """everything of the plan side a bind reads besides the plan file: the plan folder (sidecars, inputs/) and the R8 tables"""
        eff = self._eff_asbuilt()
        ab = load_json(eff) if eff else self.ab
        base = ab_base(ab, eff or self.ab_path, self.src)
        ins = [G.Input.json("plan", self.plan)]
        if eff:
            ins.append(G.Input.json("asbuilt", eff))
        for key, i, p in r8_tables(ab, base):
            ins.append(G.Input.json(f"table:{key}" + ("" if i is None else f"[{i}]"), p))
        if not self.seal or not str(self.plan).startswith(str(self.src) + "/"):
            pd = self.plan.parent
            ins.append(G.Input.files("plan_dir", [str(pd / r) for r in G.tree_files(pd, ("*.json",), followlinks=True)
                                                  if (pd / r) != self.plan]))
        return ins

    def nodes(self):
        a, out = self.a, self.out
        common = [self.tools, G.Input.value("env", self.env)]
        ab_elab = {k: v for k, v in self.ab.items() if not ELAB_DROP.match(k)}
        n = [G.Node("pre", [G.Input.json("plan", self.plan), G.Input.value("asbuilt", self.ab),
                            self._tree_input("tree", [self.plan.parent])] + common, run=self.run_pre, out=out,
                    doc="fast consistency checks"),
             G.Node("elab", [G.Input.value("asbuilt_elab", ab_elab), self._tree_input("sources", self._manifest_sources())] + common,
                    after=["pre"], run=self.run_elab, out=out, cost="slow")]
        last = "elab"
        if self.ab.get("land_align") == "r8":
            n.append(G.Node("r8", [G.Input.json("plan", self.plan), G.Input.value("asbuilt", self.ab),
                                   G.Input.value("pin", [a.r8_pin_pre, a.r8_pin_extra])] + common,
                            deps=["elab"], run=self.run_r8, out=out, cost="slow"))
            last = "r8"
        n.append(G.Node("bind", lambda: self._plan_side() + [self._tree_input("tree", [])] + common, deps=[last], run=self.run_bind,
                        out=out, cost="slow"))
        n.append(G.Node("latcheck", [tools_input("tools", self.rt_dir, ["lane_asbuilt_latency.py"])], deps=["bind"],
                        run=self.run_latcheck, out=out))
        n.append(G.Node("bpc", [tools_input("tools", self.rt_dir, ["bound_param_check.py"])], deps=["bind"], run=self.run_bpc, out=out))
        return n

    # -- running tools of the launch tree
    def _launch(self):
        if self.L is None:
            self.L = launch_tree(self.src, self.rt_dir, self.root / "launch")
        return self.L

    def _tool(self, name, argv, logname, extra_env=None, ok=(0,)):
        L = self._launch()
        ld = self.out / G.STAMP_DIR / "logs"
        ld.mkdir(parents=True, exist_ok=True)
        (self.root / "tmp").mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(self.root / "tmp"), OT_RT_CURRENT=str(self.rt_dir))
        env.update(self.env)
        env.update(extra_env or {})
        cmd = [sys.executable, "-I", "-B", f"tools/die_plan/{name}"] + [str(x) for x in argv]
        lf = ld / logname
        t0 = time.time()
        with open(lf, "w") as f:
            f.write("# cwd " + str(L) + "\n# " + " ".join(shlex.quote(c) for c in cmd) + "\n")
            f.flush()
            rc = subprocess.run(cmd, cwd=L, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
        log(f"ot-build:   {name} {argv[0] if argv else ''} rc={rc} in {time.time() - t0:.0f} s  (log {lf})")
        if rc not in ok:
            tail = [ln for ln in lf.read_text(errors="replace").splitlines() if ln.strip()][-12:]
            raise G.BuildError(f"{name} rc={rc}; log {lf}\n    " + "\n    ".join(x[:300] for x in tail))
        return rc, lf

    def _ab_args(self, eff=False):
        p = self._eff_asbuilt() if eff else self.asbuilt
        return ["--asbuilt", p] if p else []

    # -- node rules
    def run_pre(self, node):
        plan = load_json(self.plan)
        finds = taps_findings(plan)
        die = (plan.get("die") or {}).get("name")
        for key, i, p in r8_tables(self.ab, self.base):
            if not p.is_file():
                finds.append(f"FAIL R8-TABLE {key}{'' if i is None else f'[{i}]'} {p}: missing")
                continue
            td = load_json(p).get("die")
            if td and die and td != die:
                finds.append(f"FAIL R8-TABLE {p}: table is of die {td!r}, the plan is die {die!r}")
        js = self.out / G.STAMP_DIR / "pre.json"
        js.parent.mkdir(parents=True, exist_ok=True)
        argv = ["check", "--tree", self._launch(), "--plan", self.plan, "--skip", "TOOLSTALE", "--json", js, "--quiet"]
        if self.asbuilt:
            argv += ["--asbuilt", self.asbuilt]
        rb = getattr(self, "remap_base", None) or os.environ.get("OT_PLAN_REMAP_BASE")
        if rb:                                           # REMAP-BASE-1122; without it plan_gate_pre falls back to <plan dir>/bind_of_record
            argv += ["--remap-base", rb]
        try:
            self._tool("plan_gate_pre.py", argv, "pre.log", ok=(0, 1))
            got = load_json(js)
            lines = got.get("findings") if isinstance(got, dict) else got
            finds += [x for x in (lines or []) if isinstance(x, str) and x.startswith("FAIL")]
        except G.BuildError as e:
            finds.append(f"FAIL PRE plan_gate_pre could not run: {e}")
        if finds:
            raise G.BuildError(f"{len(finds)} inconsistent input(s) (runtime pin rt/{self.rt_sha}), nothing was elaborated:\n    "
                               + "\n    ".join(x[:400] for x in finds[:25]))
        return 0

    def _adopt_elab(self, node):
        """the elab of a sibling OUT with the same elab key (another plan of the same tree and manifest): copy its outputs"""
        key = G.key_of(G.parts_now(node, {}))
        for st in sorted(self.root.glob(f"b_*/{G.STAMP_DIR}/elab.stamp.json"), key=lambda p: -p.stat().st_mtime):
            d = st.parent.parent
            if d == self.out:
                continue
            try:
                rec = json.loads(st.read_text())
            except (OSError, ValueError):
                continue
            files = (rec.get("extra") or {}).get("files") or []
            if rec.get("key") != key or not files or not all((d / f).is_file() for f in files):
                continue
            self.out.mkdir(parents=True, exist_ok=True)
            for f in files:
                subprocess.run(["cp", "--reflink=auto", "-p", str(d / f), str(self.out / f)], check=True)
            log(f"ot-build:   elab adopted from {d} ({len(files)} files; same manifest + sources + rt)")
            return files
        return None

    def run_elab(self, node):
        files = self._adopt_elab(node)
        if files is None:
            before = set(os.listdir(self.out)) if self.out.is_dir() else set()
            self._tool("bind.py", ["elab", self.plan, "--out", self.out, "--mem", self.a.mem] + self._ab_args(), "elab.log")
            files = sorted(f for f in set(os.listdir(self.out)) - before if (self.out / f).is_file())
        node.extra = dict(files=files)
        return 0

    def run_r8(self, node):
        a = self.a
        self._tool("bind.py", ["r8-prepass", self.plan, "--out", self.out, "--r8-out", self.out / "r8_derived.json"] + self._ab_args(),
                   "r8_head.log")
        tables = r8_tables(self.ab, self.base)
        main = next((p for k, i, p in tables if k == "land_r8"), None)
        if main is None:
            raise G.BuildError("asbuilt land_align is r8 but it names no land_r8 table")
        bg = self.out / "bus_groups.json"
        rc, lf = self._tool("land_r8_derive.py", ["check", self.plan, bg, "--table", main], "r8_check.log", ok=(0, 1))
        eff = dict(plan=str(self.plan), asbuilt=str(self.asbuilt) if self.asbuilt else None, tree=str(self.src), rt=str(self.rt_dir),
                   r8="carried table equals the derivation")
        if rc == 1:
            in_tree = all(str(p).startswith(str(self.src) + "/") for _, _, p in tables) and self.asbuilt is not None
            if in_tree:                                  # TREE-WRITE-GUARD (FLOW-FLEET-R1 11-22): a table reached through a symlink leaving SRC is not in place
                linked = [w for w in (tree_write_refusal(p, self.src) for _, _, p in tables) if w]
                if linked:
                    log(f"ot-build:   R8 tables of SRC resolve outside it ({linked[0][:240]}): refreshing into OUT instead of in place")
                    in_tree = False
            if in_tree and not self.seal and all(os.access(p, os.W_OK) for _, _, p in tables):
                tgt_ab, tgt_main, root, where = self.asbuilt, main, self.base, "in place (unsealed lane tree)"
            else:
                tgt_ab, tgt_main, root, where = self._r8_overlay(tables)
            argv = [self.plan, bg, tgt_main, "--asbuilt", tgt_ab, "--root", root]
            if a.r8_pin_pre:
                argv += ["--pin-pre", a.r8_pin_pre] + (["--pin-extra", a.r8_pin_extra] if a.r8_pin_extra is not None else [])
            _, lf2 = self._tool("r8_refresh.py", argv, "r8_refresh.log")
            last = [ln for ln in lf2.read_text(errors="replace").splitlines() if ln.startswith("R8_REFRESH")][-1:]
            log(f"ot-build:   R8 tables were STALE against this plan: refreshed {where}: {last[0][:300] if last else ''}")
            eff.update(asbuilt=str(tgt_ab), r8=f"refreshed {where}")
        tmp = self.out / G.STAMP_DIR / "effective.json.tmp"
        tmp.write_text(json.dumps(eff, indent=1) + "\n")
        os.replace(tmp, self.out / G.STAMP_DIR / "effective.json")
        return 0

    def _r8_overlay(self, tables):
        """sealed tree (or an as-built inside the plan): refreshed tables + an as-built copy that names them, under OUT/.ot-build/plan"""
        if self.asbuilt is None:
            raise G.BuildError("R8 tables are stale and the as-built section is inside the plan file: give --asbuilt FILE "
                               "(the refresh rewrites the tables the manifest names)")
        od = self.out / G.STAMP_DIR / "plan"
        if od.exists():
            shutil.rmtree(od)
        overlay_dir(self.asbuilt.parent, od)
        (od / "r8").mkdir()
        ab = json.loads(self.asbuilt.read_text())
        ab["base"] = str(Path(os.path.realpath(self.base)))
        main = None
        for n, (key, i, p) in enumerate(tables):
            c = od / "r8" / f"{n}_{p.name}"
            shutil.copy2(p, c)
            os.chmod(c, 0o644)
            if key == "land_r8":
                ab["land_r8"], main = str(c), c
            else:
                ab["land_r8_extra"][i] = str(c)
        t = od / self.asbuilt.name
        if t.is_symlink() or t.exists():
            t.unlink()
        t.write_text(json.dumps(ab, indent=1) + "\n")
        return t, main, od, f"into {od} (the tree is sealed: nothing written into it)"

    def run_bind(self, node):
        j = str(self.a.emit_j)
        self._tool("bind.py", ["bind", self.plan, "--out", self.out, "--mem", self.a.mem, "--strict", "--all-gaps"] + self._ab_args(True),
                   "bind.log", extra_env={"OT_BIND_EMIT_J": j})
        rep = load_json(self.out / "bind_report.json")
        if rep.get("n_errors") != 0:
            raise G.BuildError(f"strict bind reports {rep.get('n_errors')} error(s): {json.dumps(rep.get('errors', [])[:5])[:600]}")
        node.extra = dict(emit_j=j)
        return 0

    def run_latcheck(self, node):
        d = self.out / G.STAMP_DIR
        eff = self._eff_asbuilt()
        argv = [self.out, self.plan] + (["--asbuilt", eff, "--pricing", "as-bound"] if eff else [])
        self._tool("lane_asbuilt_latency.py", argv + ["--tsv", d / "latcheck.tsv", "--json", d / "latcheck.json"], "latcheck.log")
        return 0

    def run_bpc(self, node):
        """BOUND-PARAM-1 is ADVISORY in the plan publish gate (publish_gate.check_bound_params).  Here it blocks only a finding
        in the RTL of a type this build makes a kit of (--type): a parameter its own module passes, or one passed to it, that
        no definition declares (its kit elaboration would fail).  A finding elsewhere (KV D27d3: kv3_pc__cl5a95b461 from the
        die top) is printed as advisory and the build goes on (OPUS-PIPELINE-R2 11-21, e2e defect D4)."""
        js = self.out / G.STAMP_DIR / "bpc.json"
        rc, lf = self._tool("bound_param_check.py", ["--tree", self._launch(), "--rtl-dir", self.out / "rtl", "--json", js],
                            "bpc.log", ok=(0, 1))
        if rc == 0:
            return 0
        try:
            errs = list(load_json(js).get("errors") or [])
        except (OSError, ValueError) as e:
            raise G.BuildError(f"bound_param_check.py rc=1 and no readable {js}: {e}")
        mods = bpc_type_modules(self.plan, self.a.type or [])
        block = [e for e in errs if bpc_hits(e, mods)]
        for e in errs:
            log(f"ot-build:   {'BLOCK' if e in block else 'ADVISORY'} {e[:300]}")
        if block:
            raise G.BuildError(f"bound_param_check.py: {len(block)} finding(s) in the RTL of {', '.join(sorted(mods))}; log {lf}")
        return 0

    def main(self):
        a = self.a
        self._nodes = self.nodes()
        goal = a.upto or "bpc"
        if goal == "bpc":
            goal = ["latcheck", "bpc"]
        elif goal == "r8" and not any(n.name == "r8" for n in self._nodes):
            goal = "elab"
        log(f"OT-BUILD OUT {self.out}")
        log(f"ot-build: bind stage tree {self.src} ({'sealed ' + self.seal[:12] if self.seal else 'unsealed'}) plan {self.plan} "
            f"rt {self.rt_sha} host {os.uname().nodename}")
        rc = G.build(self._nodes, goal, dry=a.status or a.dry, log=log, force=tuple(a.force or ()))
        eff = self.effective() or dict(plan=str(self.plan), asbuilt=str(self.asbuilt) if self.asbuilt else None, tree=str(self.src),
                                       rt=str(self.rt_dir))
        eff.update(out=str(self.out), rc=rc, keys={n.name: (G.read_stamp(n) or {}).get("key") for n in self._nodes},
                   tree_id=("seal:" + self.seal) if self.seal else str(self.src), host=os.uname().nodename)
        if a.type:
            # what a KIT of each named type is made from: its plan block, the rest of the plan, its bound RTL (hub: kit stamp)
            plan = load_json(self.plan)
            eff_ab = self._eff_asbuilt()
            eff["asbuilt_sha"] = G.sha_json_file(eff_ab) if eff_ab else G.sha_obj(self.ab)
            eff["plan_rest"] = G.sha_obj({k: v for k, v in plan.items() if k not in ("partition_types", "note")})
            eff["types"] = {}
            for tn in a.type:
                t = (plan.get("partition_types") or {}).get(tn)
                if t is None:
                    eff["types"][tn] = None
                    continue
                f = self.out / "rtl" / f"{t.get('module')}.sv"
                eff["types"][tn] = dict(block=G.sha_obj(t), module=t.get("module"), rtl=G.sha_file(f) if rc == 0 else None)
        log("OT-BUILD EFFECTIVE " + json.dumps(eff, sort_keys=True))
        return rc


def cmd_bind(a):
    try:
        return BindStage(a).main()
    except G.BuildError as e:
        log(f"ot-build: REFUSED {e}")
        return 1


def cmd_plan_overlay(a):
    try:
        src = Path(a.src)
        copy = set(a.copy or [])
        if not copy:
            copy = {e for e in os.listdir(src) if e.endswith(".json") and (src / e).is_file() and (src / e).stat().st_size < (256 << 20)
                    and not (src / e).is_symlink()} if a.all_json else set()
        overlay_dir(src, a.to, copy)
    except G.BuildError as e:
        log(f"ot-build: REFUSED {e}")
        return 1
    log(f"ot-build: plan overlay {a.to}: {len(copy)} real cop{'y' if len(copy) == 1 else 'ies'} ({', '.join(sorted(copy)[:8])}), "
        f"the rest links to {src}")
    return 0


def parser():
    ap = argparse.ArgumentParser(prog="ot-build", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("bind", help="the bind stage of one (tree, plan) on this host")
    b.add_argument("--tree", required=True)
    b.add_argument("--plan", required=True)
    b.add_argument("--asbuilt")
    b.add_argument("--out-root", required=True)
    b.add_argument("--rt")
    b.add_argument("--env", action="append", default=[], metavar="OT_KEY=VALUE")
    b.add_argument("--emit-j", default="auto")
    b.add_argument("--mem", default="48")
    b.add_argument("--status", action="store_true", help="hash and report; run nothing (exit 3 when a node is stale)")
    b.add_argument("--dry", action="store_true")
    b.add_argument("--upto", choices=BIND_NODES)
    b.add_argument("--force", action="append", default=[], choices=BIND_NODES)
    b.add_argument("--type", action="append", default=[], help="report this type's plan-block and bound-RTL hashes (kit stamp inputs)")
    b.add_argument("--remap-base", help="REMAP-BASE-1122: base plan for plan_gate_pre LANDREMAP / ISTCYC (default $OT_PLAN_REMAP_BASE, else the tree bind_of_record plan)")
    b.add_argument("--r8-pin-pre")
    b.add_argument("--r8-pin-extra")
    b.set_defaults(fn=cmd_bind)
    o = sub.add_parser("plan-overlay", help="a private plan folder: real copies of the edited files, links to the rest")
    o.add_argument("--from", dest="src", required=True)
    o.add_argument("--to", required=True)
    o.add_argument("--copy", action="append", default=[])
    o.add_argument("--all-json", action="store_true")
    o.set_defaults(fn=cmd_plan_overlay)
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("bind", "plan-overlay", "-h", "--help"):
        import ot_build_hub
        return ot_build_hub.main(argv)
    a = parser().parse_args(argv)
    if not getattr(a, "fn", None):
        parser().print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
