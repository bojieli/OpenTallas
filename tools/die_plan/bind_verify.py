"""bind_verify: independent proof that the bound die keeps the as-built connectivity (tools/die_plan/bind.py verify).

The generated RTL (DIR/bind.f: leaf interface files + bind_cells.sv + the partition modules + the bound top) is
elaborated again by Yosys, the partition modules dissolved, and every leaf input bit traced to its logical source with
the inserted cells as transport (ot_dp_st boundary flops / stations, ot_dp_dly kept stages), ot_dp_or as a reducer and
ot_reset_sync as the partition reset.  Each as-built leaf input bit (DIR/bind_sinks.json) must see:
  * the same driver pin (as-built path.port[bit]) -- intra-partition with the same stage count, crossing with 2;
  * a fault-OR with the same set of source pins;
  * the partition clock of the same domain / the partition's synchronised reset.
Sinks or sources inside a dissolved parent's glue are counted (not matched by name: Yosys renames glue cells).
Writes DIR/verify_report.json; exit 0 only with 0 mismatches, 0 unbound, 0 tied, 0 undriven, 0 multiply-driven.
Verilator lint of the bound top runs when a Verilator is found ($OT_BIND_VERILATOR or the opentallas 5.050 install).
"""
import json
import re
import os
import shutil
import subprocess
from pathlib import Path

import bind_elab as E
from bind import Binder, Graph, Rules, load_plan, sv_id  # noqa: F401

VERIFY_RULES = {
    "transport": [
        {"module": "ot_dp_st", "map": {"q": "d", "eq": "ea"}, "drop_in": ["clk", "rst_n"], "stages": 1},
        {"module": "ot_dp_dly", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 1, "stages_param": "D"},
        {"module": "ot_dp_rsync", "map": {"q": "a"}, "drop_in": ["clk"], "stages": 2, "stages_param": "S"},
        {"module": "ot_dp_rrelay", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 1},
        # decision 13c consumer-tap relay: reset traced through d; the START (run) leg is checked by the lockstep tests
        {"module": "ot_dp_rgate", "map": {"q": "d"}, "drop_in": ["clk", "run"], "stages": 1},
    ],
    "reducers": [{"module": "ot_dp_or", "out": "y"}, {"module": "ot_dp_and", "out": "y", "op": "and"}],
    "sources": [{"module": "ot_reset_sync|ot_dp_rsync_s[23]", "kind": "reset", "outputs": {"sync_rst_n": "low"},
                 "drop_in": ["clk", "async_rst_n"]}],
}


def verilator():
    for c in (os.environ.get("OT_BIND_VERILATOR"), str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"),
              shutil.which("verilator")):
        if c and Path(c).exists():
            return c
    return None


def lint(out, top, files, defines=(), waive=(), incs=()):
    v = verilator()
    if not v:
        return dict(ran=False, reason="no verilator")
    cmd = [v, "--lint-only", "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-UNUSEDSIGNAL", "-Wno-PINCONNECTEMPTY",
           "--top-module", top] + [f"+define+{d}" for d in defines] + \
        sorted({f"-I{Path(f).parent}" for f in list(files) + list(incs)}) + [str(f) for f in files]
    (Path(out) / "verilator_lint.f").write_text("\n".join(cmd[1:]) + "\n")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=out)
    errs = [ln for ln in r.stderr.splitlines() if ln.startswith("%Error") and not ln.startswith("%Error: Exiting")]
    waived = [ln for ln in errs if any(re.search(w["rx"], ln) for w in waive)]
    errs = [ln for ln in errs if ln not in waived]
    warns = [ln for ln in r.stderr.splitlines() if ln.startswith("%Warning")]
    (Path(out) / "verilator_lint.log").write_text(r.stderr)
    return dict(ran=True, rc=r.returncode, errors=len(errs), warnings=len(warns), first_errors=errs[:20],
                waived=waived, waivers=list(waive))


def lint_split(out, top, F, G, gen_rtl, idx, prefer, rs, lib, ab0):
    """asbuilt.lint_split: a die too large for one Verilator run is linted in pieces that together cover it:
    the bound top + every partition module against leaf INTERFACE stubs, then each partition module with the real
    RTL closure of its own leaves (one run per partition module, jobs in parallel)."""
    from concurrent.futures import ThreadPoolExecutor
    defines, waive = ab0.get("defines", []), ab0.get("lint_waive", [])
    ldir = Path(out) / "lint"
    ldir.mkdir(exist_ok=True)
    stubs = E.lib_stubs(lib, ldir / "leaf_stubs.sv")
    runs = {"top": [stubs, str(rs)] + gen_rtl}
    cells = [f for f in gen_rtl if Path(f).name == "bind_cells.sv"]
    byfile = {}
    for f in gen_rtl:
        if f.endswith("_bound_top.sv") or f in cells:
            continue
        t = Path(f).read_text(errors="replace")
        mods = re.findall(r"^module\s+(\w+)", t, re.M)
        leafm = sorted(set(re.findall(r"^\s+(\w+)\s+(?:#\(.*?\)\s+)?u_\w+\s*\(", t, re.M)) - set(mods) -
                       {"ot_dp_st", "ot_dp_dly", "ot_dp_or", "ot_dp_and", "ot_dp_rsync", "ot_reset_sync", "ot_dp_rrelay", "ot_dp_rgate", "ot_dp_rsync_s2", "ot_dp_rsync_s3"})
        cl, _ = E.closure(leafm, idx, prefer)
        for m in mods:
            byfile[m] = [f] + cells + [str(rs)] + cl
    runs.update(byfile)

    def one(item):
        name, files = item
        d = ldir / name
        d.mkdir(exist_ok=True)
        # the top run reads leaf stubs, which keep the leaves' `include lines: their source directories are include dirs
        return name, lint(d, top if name == "top" else name, files, defines, waive, lib if name == "top" else ())
    res = dict(ThreadPoolExecutor(int(ab0.get("lint_jobs", 4))).map(one, sorted(runs.items())))
    errs = sum(r.get("errors", 0) for r in res.values() if r.get("ran"))
    first = [f"[{n}] {e}" for n, r in sorted(res.items()) for e in r.get("first_errors", [])][:20]
    return dict(ran=all(r.get("ran") for r in res.values()), split=True, runs=len(res), errors=errs,
                warnings=sum(r.get("warnings", 0) for r in res.values()), first_errors=first,
                failed_runs=sorted(n for n, r in res.items() if r.get("errors")),
                waived=[w for r in res.values() for w in r.get("waived", [])][:50], waivers=list(waive))


def cmd_verify(a):
    import bind as _b
    _b._AB_OVERRIDE["path"] = getattr(a, "asbuilt", None)
    raw = load_plan(a.plan)
    out = Path(a.out).resolve()
    rep = json.loads((out / "bind_report.json").read_text())
    srcs = json.loads((out / "asbuilt_sources.json").read_text())
    gen = [f for f in rep["files"]]
    top = f"{sv_id(raw['die']['name'])}_bound_top"
    dissolve = sorted({t["module"] for t in rep["types"].values()})     # as bound (variants / renamed included)
    ab = dict(netlist=[f for f in gen if f.endswith("_bound_top.sv")], top=top, dissolve=dissolve,
              defines=raw["asbuilt"].get("defines", []), substitute={})
    full = [f for f in gen if not f.endswith("_bound_top.sv")]
    rs = Path(E.REPO / "rtl/lib/ot_reset_sync.sv")
    # leaf interfaces: lib files, files of dissolved parents that also define leaves (not the die top / shims), variants
    pfull = [f for f in srcs.get("full", []) if f not in srcs.get("tops", []) and not Path(f).name.startswith("shim_")]
    lib = [f for f in srcs.get("lib", []) + pfull + rep.get("extra_lib", []) if f not in full] + \
        ([str(rs)] if str(rs) not in srcs.get("lib", []) else [])
    vdir = out / "verify"
    vdir.mkdir(exist_ok=True)
    sc = vdir / "bound.ys"
    js = vdir / "bound.json"
    ylib = [E.lib_stubs(lib, vdir / "lib_stubs.sv")] if lib else []
    sc.write_text(E.yosys_script(ab, ab["netlist"], full, ylib, js, check=True, inc_files=lib))
    mounts = [out, E.REPO] + [Path(f).parent for f in lib]
    roots = sorted({str(Path(m).resolve()) for m in mounts}, key=len)
    mounts = [m for i, m in enumerate(roots) if not any(m.startswith(r + "/") for r in roots[:i])]
    E.run_yosys(sc, vdir / "bound.yosys.log", mounts, a.mem)
    F = E.flatten(json.loads(js.read_text()), top)
    errs = []
    vr = dict(VERIFY_RULES)
    vr["clocks"], vr["resets"], vr["map"] = [], [], {}
    G = Graph(F, Rules(vr), errs)
    names = json.loads((out / "bind_names.json").read_text())
    sinks = json.loads((out / "bind_sinks.json").read_text())
    clk_top = {}
    for pn, (d, bits) in F.top_ports.items():
        if pn.startswith("clk_"):
            clk_top[pn] = pn[4:]

    def gdesc(s):
        k = s[0]
        if k == "pin":
            c = F.cells[s[1]]
            p = names.get(c.path, c.path) if G.kind[s[1]] != "glue" else None
            return ["pin", f"{p}.{s[2]}[{s[3]}]" if p else None, s[4], G.kind[s[1]] == "glue"]
        if k == "top":
            if s[1] in clk_top:
                return ["clk", clk_top[s[1]]]
            if raw.get("reset", {}).get("release") == "wavefront" and s[1] == "rst_n":
                return ["rst", "low"]  # native hard-partition delivered reset; timing checked by offsets
            return ["top", s[1]]
        if k == "reset":
            return ["rst", s[1]]
        if k in ("or", "and"):
            return [k, sorted(gdesc(x)[1] for x in s[1] if x[0] == "pin")]
        if k == "const":
            return ["tied", s[1]]
        return [k]

    reg_parts = {sv_id(p) for p in rep.get("registered_pins", {})}
    cnt = dict(compared=0, matched=0, mismatched=0, glue_unmatched=0, unbound=0, tied=0, undriven=0, multiply_driven=0, plan_driven=0)
    mism, tied_ex = [], []
    seen = set()
    for ci, c in enumerate(F.cells):
        if G.kind[ci] in ("transport", "reducer", "source", "glue"):
            continue
        ap = names.get(c.path)
        if ap is None:
            continue
        seen.add(ap)
        for pn, bits in c.ports.items():
            if G.dirs[ci].get(pn) != "input":
                continue
            for i, b in enumerate(bits):
                key = f"{ap}.{pn}[{i}]"
                want = sinks.get(key)
                s = G.source(b)
                got = gdesc(s)
                if got[0] in ("undriven", "dropped"):
                    cnt["undriven"] += 1
                    cnt["unbound"] += 1
                if want and want[0] == "plan":
                    # a plan-cell driven input: a live driver; a same-partition plan cell / leaf must be the one named
                    cnt["plan_driven"] += 1
                    if got[0] in ("pin", "clk", "rst", "or", "and") and (want[1] is None or got[0] == "pin" and got[1] == want[1]):
                        cnt["compared"] += 1
                        cnt["matched"] += 1
                        continue
                if got[0] == "tied" and not (want and want[0] == "strap" and want[1] == got[1]):
                    cnt["tied"] += 1
                    if len(tied_ex) < 50:
                        tied_ex.append((key, want, got))
                if got[0] == "tied" and want and want[0] == "strap" and want[1] == got[1]:
                    got = want          # a declared strap: the partition parameter carries the as-built value
                if got[0] == "multi":
                    cnt["multiply_driven"] += 1
                if want is None:
                    mism.append((key, "not in as-built", got))
                    cnt["mismatched"] += 1
                    continue
                cnt["compared"] += 1
                if want[0] == "pin" and (want[3] or got[0] == "pin" and got[3]):
                    cnt["glue_unmatched"] += 1
                    continue
                if want == ["rst", "low"] and got == ["top", "rst_n"] and c.path.split(".")[0] in reg_parts:
                    # registered-pin hard partition (bind.py reg_hard): no synchroniser of ours inside the bare
                    # macro, its leaf reset is the delivered die reset (arst_n) as in a wavefront hard partition
                    got = want
                if want == ["start"] and got == ["rst", "low"]:
                    # local START tap start_t<k> = ot_dp_rgate(raw reset, run): its reset leg traces to the die reset
                    # (run is dropped like on every gated tap); START timing is proven by the lockstep tests
                    got = want
                ok = want[:3] == got[:3] if want[0] == "pin" else want == got
                if ok:
                    cnt["matched"] += 1
                else:
                    cnt["mismatched"] += 1
                    if len(mism) < 200:
                        mism.append((key, want, got))
    missing = sorted(set(names.values()) - seen)
    # lint: the bound RTL plus the full RTL closure of every leaf master (unchanged as-built sources)
    from bind import plan_base
    ab0 = raw["asbuilt"]
    base = plan_base(a.plan, raw)
    idx = E.module_index(ab0.get("rtl_roots", ["rtl"]), ab0.get("files", []), base)
    prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab0.get("prefer", [])]
    leafm = sorted({c.module for ci, c in enumerate(F.cells) if G.kind[ci] == "leaf"})
    prefer += rep.get("extra_lib", [])
    cl, cl_missing = E.closure(leafm, idx, prefer)
    gen_rtl = [f for f in rep["files"]]
    if not ab0.get("lint_split"):
        lt = lint(out, top, cl + gen_rtl + [str(rs)], ab0.get("defines", []), ab0.get("lint_waive", []))
    else:
        lt = lint_split(out, top, F, G, gen_rtl, idx, prefer, rs, lib, ab0)
    lt["closure_files"], lt["closure_missing"] = len(cl), cl_missing
    v = dict(top=top, cells=len(F.cells), leaves_missing=len(missing), leaves_missing_examples=missing[:20],
             counts=cnt, mismatches=mism[:200], tied_examples=tied_ex, graph_errors=errs[:50], lint=lt,
             asbuilt_proof=rep["proof"], asbuilt_errors=rep["n_errors"])
    ok = (cnt["mismatched"] == 0 and cnt["unbound"] == 0 and cnt["tied"] == 0 and cnt["multiply_driven"] == 0 and
          not missing and not errs and rep["n_errors"] == 0 and (not lt.get("ran") or lt.get("errors") == 0))
    v["verdict"] = "PASS" if ok else "FAIL"
    (out / "verify_report.json").write_text(json.dumps(v, indent=1))
    print(json.dumps(dict(verdict=v["verdict"], **cnt, leaves_missing=len(missing), lint=lt.get("errors"),
                          asbuilt_errors=rep["n_errors"])))
    for m in mism[:10]:
        print("  ", m)
    return 0 if ok else 1
