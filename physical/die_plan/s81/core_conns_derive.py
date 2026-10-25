#!/usr/bin/env python3
"""S81/PORTFIX 10-25: derive core_conns (G0C core-face rule sidecar) for hard-core types that CORE_CONNS does not list
(the landed frames' qbank / node / ROM / view cores, gunit, bk_sel) straight from the RTL: each type's contents module is
elaborated by yosys with its hard cores as black boxes (proc; flatten; opt_clean -- no logic optimisation), and every core
port whose net reaches ANOTHER hard core or a type bus port DIRECTLY (no soft cell between) is listed as
core:<inst> / bus:<bus>.  Ports that meet soft glue only stay unlisted (unchecked by design, as CORE_CONNS).

usage: core_conns_derive.py REPO PLAN_JSON OUT_JSON [--work DIR] [--mem GB]
OUT_JSON: {contents module: {"cores": {core inst (relative to the contents inst): {port: [targets]}},
                             "ports": {module port: [core inst.port, ...]}}}
gen_plan_v4 maps module ports to buses per type (contents bind "bus:<bus>", or PF_PORT_BUS for unbound contents)."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import bind_elab as BE  # noqa: E402

plan = json.load(open(sys.argv[2]))
out_path = Path(sys.argv[3])
work = Path(sys.argv[sys.argv.index("--work") + 1] if "--work" in sys.argv else out_path.parent / "ccd_work").resolve()
mem = int(sys.argv[sys.argv.index("--mem") + 1]) if "--mem" in sys.argv else 16
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
work.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "physical" / "die_plan" / "s81"))

# which (contents module, contents inst) to derive: every type with hard_cores
jobs = {}
for tn, t in plan["partition_types"].items():
    if not t.get("hard_cores") or len(t.get("contents", [])) != 1:
        continue
    c = t["contents"][0]
    m = c["module"]
    if only and m not in only:
        continue
    cores = {}
    for h in t["hard_cores"]:
        assert h["inst"].startswith(c["inst"] + "."), (tn, h["inst"])
        cores[h["inst"][len(c["inst"]) + 1:]] = h["module"]
    j = jobs.setdefault(m, dict(cores={}, params={}, types=[]))
    j["cores"].update(cores)
    j["types"].append(tn)
    for k, v in (c.get("params") or {}).items():
        j["params"].setdefault(k, v)

idx = BE.module_index([REPO / "rtl", REPO / "physical" / "asap7_memory_macros_v2"], [], REPO)
res = {}
for m, j in sorted(jobs.items()):
    coremods = sorted(set(j["cores"].values()))
    # soft closure: walk from m, never into a core module
    prefer = []
    fm = re.match(r"(col_h(?:9|10)_l4_lp)_r\d", m)
    if fm:      # the landed frames: gen_plan_v4.FRAME_SOURCES (the plan kit, not the older *_plan.sv)
        prefer = [str(REPO / f) for f in (
            "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
            "rtl/common/landed_parent/ot_pl_land_reset_forest.sv", "rtl/common/landed_parent/ot_pl_seam.sv",
            "rtl/dsrom_sys/s81_glue/ot_s81_rly.sv", "rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv",
            "rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col_kit.sv",
            "rtl/dsrom_sys/s81_dv/frame_lp/plan/%s_plan_kit.sv" % fm.group(1))] + \
            [str(REPO / ("rtl/dsrom_sys/s81_glue/dsfd_rly_masters%s.sv" % x)) for x in ("", "_266ew", "_536", "_c26l", "_gen18", "_v16")]
    seen, files, todo = set(), [], [m]
    while todo:
        n = todo.pop()
        if n in seen or n in coremods:
            continue
        seen.add(n)
        f, _ = BE.pick(idx, n, prefer)
        if f is None:
            continue
        if f not in files:
            files.append(f)
        todo += sorted(BE.instantiated(BE.module_body(f, n), idx))
    corefiles = []
    for cm in coremods:
        bb = [x for x in idx.get(cm, []) if x.endswith("_bb.v")]      # a macro's black-box view when it has one
        f = bb[0] if bb else BE.pick(idx, cm, [])[0]
        assert f, cm
        if f not in corefiles:
            corefiles.append(f)
    wd = work / m
    wd.mkdir(exist_ok=True)
    yj = wd / "flat.json"
    # every file read once, normally; then the core modules' bodies are emptied (blackbox) before elaboration
    s = ["read_verilog -sv -DSYNTHESIS %s" % f for f in files + [f for f in corefiles if f not in files]]
    s += ["blackbox %s" % " ".join(coremods)]
    s += ["hierarchy -top %s" % m, "proc", "flatten", "opt_clean", "write_json %s" % yj]
    (wd / "ccd.ys").write_text("\n".join(s) + "\n")
    BE.run_yosys(wd / "ccd.ys", wd / "ccd.log", [REPO, wd], mem_gb=mem)
    Y = json.load(open(yj))["modules"]
    top = Y[m]
    # yosys flatten names a nested core u_a.u_b ; generate scopes u_sel.g_q[0].u_q
    cells = {}
    for cn, c in top["cells"].items():
        if c["type"] in coremods or c["type"].lstrip("\\") in coremods:
            cells[cn.lstrip("\\")] = c
    norm = lambda s: re.sub(r"\\", "", s)
    want = {norm(k): k for k in j["cores"]}
    missing = sorted(set(want) - set(cells))
    bit2 = {}                                  # bit -> [(kind, name, port)]
    for cn, c in cells.items():
        for p, bits in c["connections"].items():
            for b in bits:
                if isinstance(b, int):
                    bit2.setdefault(b, []).append(("core", cn, p))
    for pn, pd in top["ports"].items():
        for b in pd["bits"]:
            if isinstance(b, int):
                bit2.setdefault(b, []).append(("port", pn, pn))
    cores_out, ports_out = {}, {}
    for cn, c in cells.items():
        if cn not in want:
            continue
        for p, bits in c["connections"].items():
            if p.lower() in ("clk", "ck", "rst_n", "rst", "rs", "rsi", "rs_n", "arst_n"):
                continue
            tg = set()
            for b in bits:
                for k, n, pp in bit2.get(b, []) if isinstance(b, int) else []:
                    if k == "core" and n != cn:
                        tg.add("core:" + want.get(n, n) if n in want else "core:" + n)
                    elif k == "port":
                        tg.add("port:" + n)
            if tg:
                cores_out.setdefault(want[cn], {})[p] = sorted(tg)
                for x in tg:
                    if x.startswith("port:"):
                        ports_out.setdefault(x[5:], []).append("%s.%s" % (want[cn], p))
    res[m] = dict(cores=cores_out, ports=ports_out, types=j["types"], missing_cores=missing,
                  unlisted_cores=sorted(set(want) - set(cores_out) - set(missing)))
    print(m, "cores", len(want), "with conns", len(cores_out), "missing", missing[:5])
out_path.write_text(json.dumps(res, indent=1, sort_keys=True))
