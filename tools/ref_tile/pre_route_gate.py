#!/usr/bin/env python3
"""Pre-route gate (tools/ref_tile, ref-flow-1011 2026-10-11): reject the known flow / structure pitfalls in minutes,
before a multi-hour route.  Clear PASS / WARN / FAIL with the fix for every finding.

    pre_route_gate.py KIT_DIR_OR_SPEC [--job JOB.json] [--remote HOST [--cts] [--synth-cap S] [--mem GB]] [--json OUT]
    pre_route_gate.py --job JOB.json                 (any closure-loop spec: source-sync + generic checks only)

LOCAL (seconds; also run by the closure loop at submit for "ref_tile": true jobs):
  floorplan     outline / util 45-60% / >= 20 um channels / no macro at a pin face / macros on the asap7 track lattice
  layer         leaf signals AND PG <= layer_cap (M5 default, M6 by die-lead grant, legacy kits M6/M7 PG) via explicit
                RLAYERS, PG = full-length stripes on the cap layer, pins <= cap, parent strap = cap + 1; cluster PG M7
                over M5/M6 children; PDN macro grids only for present masters (PDN-0217); kit routing layers are explicit
  pins          pin plan vs the top module's ports: every base name exists, every port in exactly one face, no x[0]
                names (PPL-0061), the clock port planned
  rtl           textbook_lint.py rtl: runtime-indexed wide part-selects (yosys SHARE stall), hard-child #() overrides
  children      tools/hier_contract/child_lint.py (a)-(g) on every hard child; TT/FF/SS libs of every macro view
  slot_fit      (submit only, owner 2026-10-13) a tile with a slot in a die contract fits it: outline, pin faces, pin
                layers, layer cap, estimated clock insertion (tools/hier_contract/slot_fit.py); a mismatch is REFUSED
                unless the spec carries "slot_change_request" (then WARN + a line in the die lead's log)
  sources       every file the flow reads (kit hooks, the scripts they source, views, RTL) exists and lies inside the
                job's synced source paths (the loop copies only source.paths + extra_paths: hbm-no3 'No rule to make
                target /src/physical/redesign_ds/coll_split/pin_access_pregrt.tcl')
REMOTE (--remote HOST, minutes, on the fleet via ot-heavy): the real ORFS synthesis under a time cap (a SHARE stall
fails here, not after hours), floorplan + PDN + IO placement of the kit (PDN-0217/0233/0006, PPL-0061 surface here),
then the netlist textbook lint (clock root size / span, high fanout + reset on datapath, logic behind pins, ICG enable
from a port, logic depth, > 500 um wire per stage) on the synthesized netlist + the placed-IO floorplan, and the pin
plan against the SYNTHESIZED port names.  MEASURED CLOCK RULE (owner 2026-10-13, constants in tools/textbook_lint.py):
> 15,000 sinks on one clock root FAILs unless this run's --cts measured TT insertion <= 300 ps and leaf spread <= 80 ps;
a declared spine does not waive it.  A --remote run writes <kit>/gate_result.json (commit it: the submit gate reads it).  --cts continues through CTS and reports clock insertion spread (ck_insertion)
and the worst-path classes.
Exit 0 PASS / WARN, 1 FAIL, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hier_contract"))
import ref_tile as RT  # noqa: E402
import child_lint  # noqa: E402
import textbook_lint as TL  # noqa: E402

DEFAULT_SRC_PATHS = ("tools", "rtl", "physical", "Makefile")
# the textbook checks whose refuse tier the gate enforces (calibrated: zero closed-set refusals, see README)
GATE_REFUSE = ("clock_domain", "high_fanout", "wire_reach")
DAEMON_TREE = Path(os.environ.get("OT_CLOSURE_DAEMON_TREE", "/home/ubuntu/wt-claude-closure-daemon-1010"))
# flow helpers the loop ships into every job snapshot (closure_loop.py ship_fpl / HELPERS); the remote gate does the same
SHIP_HELPERS = ("tools/orfs_hold_mm.py", "tools/orfs_hold_mm.tcl", "tools/fp_margin_lint.py", "tools/fp_margin_lint.tcl",
                "tools/textbook_lint.py", "physical/common_flow/macro_cts_cluster.tcl")


class Gate:
    def __init__(self):
        self.items = []

    def add(self, sev, check, msg, fix=""):
        self.items.append({"severity": sev, "check": check, "message": msg, "fix": fix})

    @property
    def verdict(self):
        s = {i["severity"] for i in self.items}
        return "FAIL" if "FAIL" in s else ("WARN" if "WARN" in s else "PASS")

    def print(self):
        for i in self.items:
            print(f"GATE {i['severity']} {i['check']}: {i['message']}" + (f"  -> FIX: {i['fix']}" if i["fix"] else ""))
        print(f"PRE_ROUTE_GATE: {self.verdict} ({sum(i['severity'] == 'FAIL' for i in self.items)} fail, "
              f"{sum(i['severity'] == 'WARN' for i in self.items)} warn)")


# --------------------------------------------------------------------------------------------- pins
def synthesis_std_area(chip_area: float, blocks: list, root=ROOT) -> float:
    """Yosys chip area includes each hard instance's Liberty area.

    A hardened child's Liberty area is its occupied logical area; its LEF
    rectangle includes whitespace. Subtract the Liberty areas before adding
    the physical envelopes to utilization, otherwise children count twice.
    Preserve the conservative old behavior when a library area is unavailable.
    """
    logical = 0.0
    for b in blocks:
        view = b.get("view")
        if not view:
            envelope = sum(x["w"] * x["h"] for x in blocks)
            return chip_area - envelope if chip_area > envelope else chip_area
        directory = root / view
        lib = directory / (directory.name + "_tt.lib")
        if not lib.exists():
            envelope = sum(x["w"] * x["h"] for x in blocks)
            return chip_area - envelope if chip_area > envelope else chip_area
        match = re.search(r"\barea\s*:\s*([\d.eE+-]+)", lib.read_text())
        if not match:
            envelope = sum(x["w"] * x["h"] for x in blocks)
            return chip_area - envelope if chip_area > envelope else chip_area
        logical += float(match.group(1))
    if logical > chip_area + 0.01:
        raise ValueError(f"synthesis chip area {chip_area} is smaller than summed macro Liberty area {logical}")
    return max(0.0, chip_area - logical)


def rtl_ports(sources, top, root=None):
    root = root or ROOT
    texts = []
    for f in sources:
        p = root / f
        if p.exists():
            texts.append(p.read_text(errors="replace"))
    # a module named through a macro (`define X top ... module `X: dsfd_coll_cb / cbf) is not seen by the text parser
    texts = [re.sub(r"\bmodule\s+`(\w+)", lambda m: f"module {top}" if re.search(
        rf"`define\s+{m.group(1)}\s+{re.escape(top)}\b", tx) else m.group(0), tx) for tx in texts]
    mods = TL.rtl_modules(texts)
    if top not in mods:
        return None
    return TL.module_ports(mods[top])


def check_pins(g: Gate, spec: dict, ports: dict | None, where="RTL"):
    if ports is None:
        g.add("FAIL", "pins", f"top module {spec['top']} not found in the {where} sources", "fix 'top' / 'sources'")
        return
    plan = {}
    for f, names in spec["pins"].items():
        for n in names:
            plan.setdefault(n, []).append(f)
    if spec["pins"].get("ANY"):
        g.add("WARN", "pins", f"{len(spec['pins']['ANY'])} port group(s) left to the IO placer (ANY): {spec['pins']['ANY'][:4]}",
              "give every bus a face (and an offset range) from the die contract before the die integrates it")
    for n, fs in plan.items():
        if len(fs) > 1:
            g.add("FAIL", "pins", f"port {n} planned on {len(fs)} faces {fs}", "one face per port")
        if n not in ports:
            near = [p for p in ports if p.startswith(n.rstrip("[0]"))][:3]
            g.add("FAIL", "pins", f"pin plan names '{n}', not a port of {spec['top']} ({where})"
                  + (f"; ports like it: {near}" if near else ""), "name ports by their (scalar) base name")
    miss = [p for p in ports if p not in plan]
    if miss:
        g.add("FAIL", "pins", f"{len(miss)} ports not in the pin plan (exhaustive regions fail the floorplan): {miss[:8]}",
              "assign every port to a face")
    one = [p for p, (w, vec) in ports.items() if vec and w == 1]
    if one:
        g.add("WARN", "pins", f"1-bit vector ports {one[:6]}: scalars after synthesis (named by base name here, which is "
              "safe; a hand pin list must not say x[0])", "declare them scalar in RTL")
    if spec["clock_port"] not in ports:
        g.add("FAIL", "pins", f"clock port {spec['clock_port']} is not a port of {spec['top']}", "fix clock_port")


# --------------------------------------------------------------------------------------------- sources
PATH_RE = re.compile(r"(?:/src/|\{SRC\}/|\$SRC/|\$\{SRC\}/)?\b((?:physical|tools|rtl|results|configs)/[\w./+-]+\."
                     r"(?:tcl|sdc|sh|py|v|sv|svh|vh|env|lef|lib|json))\b")


def git_show(commit, path):
    if not commit:
        p = ROOT / path
        return p.read_text(errors="replace") if p.is_file() else None
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def referenced_closure(seeds, commit=None, args_env=None):
    """every repo path reachable from the seeds through the files they name (tcl source, sh, env, sdc; a .py named by
    a command is scanned one level deep -- generators such as hbm_w2_station_hier_physical.py write the hooks into
    their run.sh -- and paths found only in a .py are checked for the sync set, not for existence)"""
    seen, missing, weak = set(), set(), set()
    soft = set()     # found only inside a generator .py and not a flow script (.tcl/.sdc/.sh/.env): may be an unused option
    todo = [(s, 0, False) for s in seeds]
    while todo:
        p, depth, from_py = todo.pop()
        p = p.replace("//", "/")
        if p in seen:
            continue
        txt = git_show(commit, p)
        if txt is None:
            if "$" not in p and "*" not in p:
                (weak if from_py else missing).add(p)
            continue
        seen.add(p)
        if from_py and (not p.endswith((".tcl", ".sh", ".env", ".sdc")) or depth > 0 and p.endswith(".sv")):
            soft.add(p)
        if p.endswith((".tcl", ".sh", ".env", ".sdc")) or (p.endswith(".py") and depth == 0):
            body = re.sub(r"(?m)^\s*#.*$", "", txt)
            for m in PATH_RE.finditer(body):
                q = m.group(1)
                if "$" not in q and "{" not in q:
                    # ${VAR:-default}: the default only applies when the caller does not set VAR -> soft
                    dflt = body[max(0, m.start() - 2):m.start()] == ":-"
                    todo.append((q, depth + 1, from_py or p.endswith(".py") or dflt))
            if p.endswith("route_master.sh") and args_env:
                todo.append((f"physical/qwen_die_masters/cfg/{args_env}.env", depth + 1, False))
    return seen, missing - seen, soft


def check_sources(g: Gate, job: dict, extra_seeds=(), commit=None):
    src = job.get("source") or {}
    synced = [str(x).rstrip("/") for x in list(src.get("paths", DEFAULT_SRC_PATHS)) + list(src.get("extra_paths", []))]
    cmds = []
    st = job.get("stages") or {}
    for k in ("route", "calibrate", "collect"):
        if isinstance(st.get(k), dict) and st[k].get("cmd"):
            cmds.append(st[k]["cmd"])
    for b in st.get("bench") or []:
        cmds.append(b.get("cmd", ""))
    seeds = set(extra_seeds)
    cfg = None
    for c in cmds:
        for m in PATH_RE.finditer(c.replace("{SRC}/", "")):
            seeds.add(m.group(1))
        m = re.search(r"route_master\.sh\s+(\S+)", c)
        if m:
            cfg = m.group(1)
    for p in (job.get("verdict") or {}).get("post_sdc") or []:
        seeds.add(p)
    seen, missing, soft = referenced_closure(sorted(seeds), commit, cfg)
    out_all = sorted(p for p in seen if not any(p == s or p.startswith(s + "/") for s in synced))
    if True:   # the loop ships these flow helpers into every job (closure_loop HELPERS / tt_overlay TTB_FILES)
        soft |= {f"physical/common_flow/{n}" for n in ("macro_sliver_block.tcl", "edge_sliver_block.tcl",
                                                       "macro_cts_cluster.tcl", "io_ref_routed.sdc")}
        soft |= {f"physical/common_flow/{n}" for n in ("cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl",
                                                       "link_budget_consistent.sdc", "nbr_clk_measured_ttb.sdc")}
    outside = [p for p in out_all if p not in soft]
    if missing:     # WARN: a recipe may write the file at run time (generated SDC / run script)
        g.add("WARN", "sources", f"{len(missing)} referenced file(s) do not exist"
              + (f" at {commit}" if commit else "") + f": {sorted(missing)[:6]}", "commit them / fix the path")
    if outside:
        g.add("FAIL", "sources", f"{len(outside)} referenced file(s) outside the synced source paths {synced}: "
              f"{outside[:6]} (the loop copies only source.paths + extra_paths; the route dies with 'No rule to make "
              f"target /src/...')", "add their directories to source.extra_paths (or drop source.paths for the default)")
    return {"referenced": len(seen), "missing": sorted(missing), "outside": outside}


# --------------------------------------------------------------------------------------------- kit checks
def check_kit(g: Gate, kd: Path, job: dict | None, commit=None):
    spec = RT.load_spec(str(kd / "spec.json"))
    try:
        fresh = RT.gen(str(kd / "spec.json"), spec.get("std_area_um2"), write=False)
    except RT.SpecError as ex:
        g.add("FAIL", "spec", str(ex), "fix the tile spec")
        return spec
    for sev, chk, msg, fix in fresh["findings"]:
        g.add(sev, chk, msg, fix)
    fp = json.loads((kd / "floorplan.json").read_text())
    if [round(x, 3) for x in fp["die"][2:]] != [round(x, 3) for x in fresh["outline"]]:
        g.add("FAIL", "kit", f"kit outline {fp['die'][2:]} != regenerated {fresh['outline']}", "re-run ref_tile.py gen")
    env = (kd / "kit.env").read_text()
    if "PLACE_DENSITY_LB_ADDON=" not in env:
        g.add("FAIL", "density", "kit leaves ORFS's PLACE_DENSITY_LB_ADDON in force: the placer target becomes lower-bound + "
              "0.05, not the spec PD (qkd_nhb_pbst 0.50 -> 0.1075, GPL-0305)", "re-run ref_tile.py gen")
    lc = fp["layer_contract"]
    rl = re.search(r"^RLAYERS='M2 (M[5-9])'$", env, re.M)
    if not rl:
        g.add("FAIL", "layer", "kit.env has no explicit RLAYERS M2..M5/M6/M7/M8/M9 (a script default would override the "
              "layer contract)", "re-run ref_tile.py gen")
    elif spec["kind"] == "tile":
        fresh_lc = RT.layer_contract(spec, RT.contract_slot(spec))
        if rl.group(1) != fresh_lc["rlayers"][1] or lc.get("pg_layer") != fresh_lc["pg_layer"]:
            g.add("FAIL", "layer", f"kit routes signals to {rl.group(1)} / PG {lc.get('pg_layer')} but the layer contract "
                  f"gives cap {fresh_lc['rlayers'][1]} / PG {fresh_lc['pg_layer']} ({fresh_lc.get('cap_basis')}; new tiles "
                  "cap at M5, M6 only with layer_cap_grant)", "re-run ref_tile.py gen")
        cap_n = int(rl.group(1)[1:])
        pins_used = set()
        for k in ("PIN_H", "PIN_V", "export OT_PIN_BALANCE_H", "export OT_PIN_BALANCE_V"):
            mm = re.search(rf"^{k}='([^']*)'", env, re.M)
            pins_used |= set(mm.group(1).split()) if mm else set()
        over = sorted(x for x in pins_used if re.fullmatch(r"M\d+", x) and int(x[1:]) > cap_n)
        if over and not (over == ["M6"] and fresh_lc.get("m6_pin_grant")):
            g.add("FAIL", "layer", f"pin layers {over} above the tile cap {rl.group(1)}: the parent strap layer would "
                  "carry pins", "pins on M4/M5 (route.pin_h / pin_v / pin_balance)")
    elif rl is not None and spec["kind"] == "cluster":
        cap, grant = RT.cluster_signal_cap(spec, RT.contract_slot(spec))
        if rl.group(1) != cap or lc.get("pg_layer") != "M7":
            g.add("FAIL", "layer", "cluster kit signals/PG differ from its audited layer contract", "re-run ref_tile.py gen")
        if grant:
            g.add("INFO", "layer_grant", f"digest-bound {cap} grant {grant['source']}; no die signals through rectangle; phase-aligned die PG required")
    g.add("INFO", "layer", f"{spec['kind']}: PG {lc['pg_layer']} stripes as pins, signals {lc['rlayers'][0]}-"
          f"{lc['rlayers'][1]}, parent strap {lc['strap_layer']}"
          + (f", cap {lc['layer_cap']} ({lc.get('cap_basis')})" if lc.get("layer_cap") else "")
          + (f"; children PG {lc['children']}" if lc.get("children") else ""))
    pdn = (kd / "pdn.tcl").read_text()
    if re.search(r"define_pdn_grid[^\n]*-macro", pdn) and "ot_ref_present" not in pdn:
        g.add("FAIL", "pdn", "macro grid without a present-master guard (PDN-0217)", "re-run gen")
    # pins vs RTL
    check_pins(g, spec, rtl_ports(spec["sources"], spec["top"]))
    # RTL lint
    files = [str(ROOT / f) for f in spec["sources"] if (ROOT / f).exists()]
    hard = sorted({RT.view_name(c["view"]) for c in spec["children"]})
    r = TL.rtl_lint(files, hard, spec.get("hard_define"), top=spec["top"])
    for k, v in r["findings"].items():
        sev = "FAIL" if k == "hard_child_params" else "WARN"
        fix = ("decoded constant-index slices; the --remote synthesis smoke decides (a SHARE stall FAILs there)"
               if k == "runtime_partselect" else "no #() on hard children under the hard define")
        for line in v[:2]:
            g.add(sev, "rtl", f"{k}: {line}", fix)
    # children + macro views
    for it in spec["children"]:
        v = it["view"]
        lef = ROOT / v / f"{RT.view_name(v)}.lef"
        res = child_lint.lint(str(lef), str(ROOT / v))
        if res["verdict"] != "PASS":
            g.add("FAIL", "children", f"{RT.view_name(v)} child_lint: " + "; ".join(res["fails"])[:600],
                  "re-export the child through tools/ref_tile (exact abstract, PG stripes, keepout, TT/FF/SS)")
        for w in res["warns"]:
            g.add("WARN", "children", f"{RT.view_name(v)}: {w}", "export the child's clock insertion (ref_tile export)")
    for it in spec["macros"] + spec["children"]:
        v = it["view"]
        miss = [c for c in ("ss", "ff", "tt") if not (ROOT / v / f"{RT.view_name(v)}_{c}.lib").exists()]
        if miss:
            g.add("FAIL", "libs", f"{RT.view_name(v)}: no {', '.join(miss)} lib", "export all three corners")
    if job is not None:
        if not job.get("ref_tile"):
            g.add("WARN", "job", "job spec lacks \"ref_tile\": true", "submit the generated job.json")
        if "tools/ref_tile/ref_route.sh" not in job["stages"]["route"]["cmd"]:
            g.add("FAIL", "job", "route command is not tools/ref_tile/ref_route.sh", "use the generated job.json")
        check_sources(g, job, fp.get("referenced", []), commit)
    return spec


# --------------------------------------------------------------------------------------------- remote
REMOTE_SH = r"""set -uo pipefail
R={R}; mkdir -p $R/src $R/bin && tar -xzf $R.tgz -C $R/src && rm -f $R.tgz
cat > $R/bin/docker <<'EOS'
#!/bin/bash
for e in ${{PATH//:/ }}; do if [ -x "$e/docker" ] && ! [ "$e/docker" -ef "$0" ]; then
  if [ "${{1:-}}" = run ]; then shift; exec "$e/docker" run -e LEC_CHECK=0 -e OT_CTS_MACRO_CLUSTER "$@"; fi
  exec "$e/docker" "$@"; fi; done; exit 127
EOS
chmod +x $R/bin/docker; export PATH=$R/bin:$PATH
cd $R/src && echo {COMMIT} > SOURCE_COMMIT
T0=$(date +%s)
# the gate builds the tree at the ROUTE's corner (ref_tile.py ROUTE_PREFIX: setup at TT, owner option B): a cluster spine
# balanced at SS against the children's TT insertion targets measured a mixed-corner spread (dsfd_sp_pq_c, dscoll_ces0_sp)
export OT_ORFS_CORNER_OVERRIDE=TC
SRC=$R/src SYNTH_TIMEOUT={CAP} bash tools/ref_tile/ref_route.sh {KIT}/kit.env gate $R/routes floorplan; FRC=$?
echo "GATE_FLOW_RC=$FRC GATE_FLOW_S=$(( $(date +%s) - T0 ))"
C=$R/routes/gate/work/orfs; B=$(ls -d $C/results/asap7/*/base 2>/dev/null | head -1)
grep -hE "^\[ERROR|Error:|ERROR \[|timed out|TimeoutExpired|exceeded" $R/routes/gate/flow.log $C/*.log 2>/dev/null | head -8 | sed 's/^/GATE_FLOWERR /'
[ $FRC -eq 0 ] || exit 0
NB=${{B#$C/}}
docker run --rm -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow {IMG} bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/$NB/3_2_place_iop.odb" > $R/iop.log 2>&1; echo "GATE_IOP_RC=$?"
grep -hE "\[ERROR" $R/iop.log | head -4 | sed 's/^/GATE_FLOWERR /'
printf 'read_db /work/%s/3_2_place_iop.odb\nsource /src/tools/fp_margin_lint.tcl\not_fp_lint_dump /work/gate_dump.json\nexit\n' $NB > $C/gate_dump.tcl
docker run --rm -v $R/src:/src:ro -v $C:/work {IMG} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/gate_dump.tcl > $R/dump.log 2>&1; echo "GATE_DUMP_RC=$?"
python3 tools/textbook_lint.py check --netlist $B/1_2_yosys.v --dump $C/gate_dump.json --out $R/textbook.json --mode refuse --refuse-checks {RC} | sed 's/^/GATE_TB /'
python3 - $B/1_2_yosys.v {TOP} <<'EOP'
import re,sys,json
t=open(sys.argv[1]).read(); m=re.search(r"module\s+\\?"+re.escape(sys.argv[2])+r"\s*\((.*?)\);(.*?)endmodule",t,re.S)
ports={{}}
if m:
  for d in re.finditer(r"\b(input|output|inout)\b\s*(?:signed\s*)?(\[[^\]]*\])?\s*([^;]+);",m.group(2)):
    for n in d.group(3).split(","): ports[n.strip().lstrip("\\")]=[1 if not d.group(2) else None, bool(d.group(2))]
print("GATE_PORTS "+json.dumps(ports))
EOP
grep -h "Chip area\|chip area" $C/reports/asap7/*/base/synth_stat.txt 2>/dev/null | tail -1 | sed 's/^/GATE_AREA /'
if [ "{CTS}" = 1 ]; then
  docker run --rm -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow {IMG} bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts" > $R/cts.log 2>&1; echo "GATE_CTS_RC=$?"
  grep -h "\[ERROR" $R/cts.log | head -3 | sed 's/^/GATE_CTSERR /'
  grep -h "^OT_SPINE iter\|^REF_TILE spine" $R/cts.log | tail -2 | sed 's/^/GATE_SPINE /'
  grep -h "OT_SPINE done port" $R/cts.log $C/logs/asap7/*/base/4_1_cts.log 2>/dev/null | head -1 | sed 's/^/GATE_SPINE_DONE /'
  grep -h "^global_placement -density\|Placement target density" $R/cts.log | head -2 | sed 's/^/GATE_GPLD /'
  python3 tools/closure_loop/ck_insertion.py --base $B --clock {CLK} --output $R/ck.json > $R/ck.log 2>&1; echo "GATE_CK_RC=$?"
  python3 -c "import json;d=json.load(open('$R/ck.json'));print('GATE_CK '+'; '.join(c+' insertion all '+str(d[c]['all']['min'])+'..'+str(d[c]['all']['max'])+' ps (spread '+str(round(d[c]['all']['max']-d[c]['all']['min'],1))+'), boundary mean '+str(d[c]['boundary']['mean']) for c in ('ss','tt','ff') if isinstance(d.get(c),dict) and d[c].get('all'))+'; macro_clk flag '+str((d.get('macro_clk') or {{}}).get('flag')))" 2>/dev/null
  docker run --rm -v $R/src:/src:ro -v $C:/work {IMG} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tools/ref_tile/path_classes.tcl > $R/pc.log 2>&1
  grep "^GATE_PC" $R/pc.log
fi
echo GATE_DONE
"""


def ship_tar(paths):
    import io
    import tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for p in sorted(set(paths)):
            src = ROOT / p
            if src.exists():
                tf.add(str(src), arcname=p, filter=lambda ti: None if ("/views/" in ti.name and ti.name.endswith(".gds"))
                       or "__pycache__" in ti.name else ti)
        for h in SHIP_HELPERS:      # the loop's shipped flow helpers win over the snapshot's copies
            f = DAEMON_TREE / h
            if f.exists():
                tf.add(str(f), arcname=h)
    return buf.getvalue()


def remote(g: Gate, kd: Path, spec: dict, host: str, cap: int, mem: int, cts: bool):
    fp = json.loads((kd / "floorplan.json").read_text())
    ref = set(fp["referenced"])
    # Ship the same transitive Tcl/shell dependencies checked by the local gate.
    # A custom PRE_GLOBAL_PLACE hook may source helpers outside its own folder.
    ref |= referenced_closure(sorted(ref))[0]
    dirs = {"tools", "rtl", str(kd.relative_to(ROOT)), "physical/qwen_die_masters", "physical/common_flow",
            "physical/hbm_accel_die_views/stations/bench", "physical/hbm_w2_rb_station_20261006"}
    dirs |= {str(Path(p).parent) for p in ref}
    ts = time.strftime("%Y%m%d-%H%M%S")
    R = f"/srv/opentallas-scratch/claude/ref_gate/{spec['name']}-{ts}"
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short=9", "HEAD"], capture_output=True,
                            text=True).stdout.strip() + "+wt"
    sh = REMOTE_SH.format(R=R, COMMIT=commit, CAP=cap, KIT=kd.relative_to(ROOT), IMG="openroad/orfs:latest",
                          RC=",".join(GATE_REFUSE), TOP=spec["top"], CTS=1 if cts else 0,
                          CLK=spec["clock_port"])   # ck_insertion (9f48f5ed8): --clock = clock name or its source port; the default 'ck' failed every kit whose port is 'clk'
    script = f"/tmp/ref_gate_{spec['name']}_{ts}.sh"
    t0 = time.time()
    data = ship_tar(dirs)
    up = subprocess.run(["ssh", host, f"cat > {script}"], input=sh.encode(), capture_output=True)
    if not up.returncode:
        up = subprocess.run(["ssh", host, f"mkdir -p {Path(R).parent} && cat > {R}.tgz"], input=data, capture_output=True)
    if up.returncode:
        g.add("FAIL", "remote", f"cannot ship to {host}: {up.stderr[-200:]!r}", "pick another host")
        return
    cmd = f"ot-heavy --mem {mem} -- bash {script}"
    p = subprocess.run(["ssh", host, cmd], stdin=subprocess.DEVNULL, capture_output=True)
    out = p.stdout.decode(errors="replace")
    logp = Path(os.environ.get("TMPDIR", "/tmp")) / f"ref_gate_{spec['name']}_{ts}.log"   # never into the kit (dirty tree)
    logp.write_text(out + "\n--- stderr\n" + p.stderr.decode(errors="replace")[-4000:])
    g.add("INFO", "remote", f"remote log {logp}; host dir {host}:{R}")
    secs = round(time.time() - t0)
    kv = dict(re.findall(r"\b(GATE_[A-Z_]+)=(\S+)", out))
    errs = re.findall(r"^GATE_FLOWERR (.*)$", out, re.M)
    if kv.get("GATE_FLOW_RC") != "0":
        why = "; ".join(errs[:4]) or "see gate_remote.log"
        stall = any(re.search(r"tim(ed)? ?out|TimeoutExpired|exceeded", e, re.I) for e in errs) or \
            int(kv.get("GATE_FLOW_S", 0)) >= cap
        g.add("FAIL", "synth_smoke" if stall else "floorplan_run",
              (f"ORFS synthesis did not finish within {cap} s (yosys SHARE / ABC stall class): " if stall else
               "synthesis + floorplan + PDN failed: ") + why[:600],
              "decoded constant-index slices instead of runtime part-selects; replicate instead of wide shifters"
              if stall else "read the first [ERROR] above (PDN-0217/0233/0006, PPL-0061, MPL, ...) and fix the kit/RTL")
        return
    g.add("INFO", "remote", f"synth + floorplan + PDN OK on {host} in {kv.get('GATE_FLOW_S')} s (gate total {secs} s)")
    if kv.get("GATE_IOP_RC") not in (None, "0"):
        g.add("FAIL", "io_place", "IO placement failed: " + "; ".join(errs[:3]), "fix the pin plan / pin layers")
    m = re.search(r"^GATE_PORTS (.*)$", out, re.M)
    if m:
        ports = {k: tuple(v) for k, v in json.loads(m.group(1)).items()}
        check_pins(g, spec, ports, where="synthesized netlist")
    am = re.search(r"^GATE_AREA .*?([\d.]+)\s*$", out, re.M)
    if am:
        area = float(am.group(1))
        W, H = fp["die"][2], fp["die"][3]
        core = (W - 2 * RT.CORE_MARGIN) * (H - 2 * RT.CORE_MARGIN)
        mac = sum(b["w"] * b["h"] for b in fp["blocks"])
        area = synthesis_std_area(area, fp["blocks"])
        u = (area + mac) / core
        # high util is a closure risk (FAIL > 70%); low util only costs wire / area (closed blocks sit at 6-22%): WARN
        sev = "INFO" if RT.UTIL_LO <= u <= RT.UTIL_HI + 0.05 else ("FAIL" if u > 0.70 else "WARN")
        g.add(sev, "util", f"synthesized std area {area:.0f} um2 + macros {mac:.0f} in core {core:.0f}: util {u:.0%}",
              f"set \"std_area_um2\": {area:.0f} and drop 'outline' (gen sizes to util 0.52)" if sev != "INFO" else "")
    for line in re.findall(r"^GATE_TB (.*)$", out, re.M):
        if line.startswith("TEXTBOOK_LINT:"):
            continue
        mm = re.match(r"textbook_lint: (REFUSE|WARN\(refuse-tier\)|WARN|PASS|WAIVED) ?(\w+)?:? ?(.*)", line)
        if not mm:
            continue
        tag, chk, msg = mm.groups()
        if chk in TL.HARD_CHECKS:
            continue                    # the measured clock rule is judged below, after the CTS numbers
        if tag == "PASS" or not chk or " cells " in line[:200] and " flops " in line[:200] and ":" not in line[15:40]:
            g.add("INFO", "textbook", line[len("textbook_lint: "):][:300])
            continue
        g.add("FAIL" if tag == "REFUSE" else "WARN", f"textbook.{chk}", msg[:500], TEXTBOOK_FIX.get(chk, ""))
    if cts and kv.get("GATE_CTS_RC") not in (None, "0"):
        g.add("FAIL", "cts_run", "placement / CTS of the kit failed: " + "; ".join(re.findall(r"^GATE_CTSERR (.*)$", out, re.M))[:500],
              "the route would fail the same way (DPL-0033 / GPL-0305 / CTS-*): fix the floorplan / density before routing")
    if cts:
        ck = re.search(r"^GATE_CK (.*)$", out, re.M)
        g.add("INFO" if ck else "WARN", "cts_calibration", (ck.group(1)[:900] if ck else
              f"CTS rc={kv.get('GATE_CTS_RC')} ck_insertion rc={kv.get('GATE_CK_RC')}"))
        pd = float(spec["route"].get("pd", 0.55))
        dens = [float(x) for x in re.findall(r"^GATE_GPLD .*?(?:-density|target density:)\s+([\d.]+)", out, re.M)]
        if dens:
            sev = "WARN" if abs(dens[0] - pd) > 0.05 else "INFO"
            g.add(sev, "density", f"effective global-placement target density {dens[0]:.3f} vs spec PD {pd:.2f}",
                  "clear PLACE_DENSITY_LB_ADDON (ref_tile does) or set route.pd to what the placer should target"
                  if sev == "WARN" else "")
        if spec["kind"] == "cluster" and spec.get("clock", "spine") == "spine" and kv.get("GATE_CTS_RC") == "0":
            done = re.search(r"^GATE_SPINE_DONE .*OT_SPINE done port (\S+)", out, re.M)
            if not done or re.sub(r"\[0\]$", "", done.group(1)) != re.sub(r"\[0\]$", "", spec["clock_port"]):
                g.add("FAIL", "clock_spine", f"no 'OT_SPINE done port {spec['clock_port']}' in the CTS log: the spine did not "
                      "build, TritonCTS ran instead (OT_SPINE_PORT not reaching the container before 225badfab)",
                      "check OT_SPINE_PORT in config.mk and the PRE_CTS hook order (spine sourced first)")
            else:
                g.add("INFO", "clock_spine", f"spine built on port {done.group(1)}")
        for line in re.findall(r"^GATE_SPINE (.*)$", out, re.M):
            g.add("INFO", "clock_spine", line[:300])
        for line in re.findall(r"^GATE_PC (.*)$", out, re.M):
            g.add("INFO", "path_classes", line)
    clock_item(g, clock_record(out, cts, spec))


CLOCK_RESULT = "gate_result.json"       # <kit>/gate_result.json: the kit's gate result (commit it with the kit)


def clock_record(out: str, cts: bool, spec: dict | None = None) -> dict:
    """the clock evidence of one remote gate run: sinks of the largest root from the synthesized netlist (textbook
    lint 'clock_roots' line) and, with --cts, the measured TT insertion (latest leaf arrival) and leaf arrival spread
    (max - min over all register clock pins, ck_insertion.py 'all')."""
    rec = {"max_root_sinks": None, "root": None, "cts": bool(cts), "tt_insertion_ps": None, "tt_spread_ps": None,
           "declared_clock": (spec or {}).get("clock"),
           "limits": {"sinks": TL.CLK_ROOT_SINKS_MAX, "insertion_ps": TL.CLK_INSERTION_MAX_PS,
                      "spread_ps": TL.CLK_SPREAD_MAX_PS}}
    m = re.search(r"textbook_lint: INFO clock_roots max_root_sinks=(\d+) root=(\S+)", out)
    if m:
        rec["max_root_sinks"], rec["root"] = int(m.group(1)), m.group(2)
    ck = re.search(r"^GATE_CK .*?\btt insertion all ([\d.]+)\.\.([\d.]+) ps", out, re.M)
    if cts and ck:
        lo, hi = float(ck.group(1)), float(ck.group(2))
        rec["tt_insertion_ps"], rec["tt_spread_ps"] = hi, round(hi - lo, 1)
    ok, text = TL.clock_rule(rec["max_root_sinks"], rec)
    rec["verdict"] = "PASS" if ok and rec["max_root_sinks"] is not None else ("UNKNOWN" if ok else "REFUSE")
    rec["text"] = text
    return rec


def clock_item(g: Gate, rec: dict) -> None:
    """measured clock rule (owner 2026-10-13, constants in textbook_lint.py): reported for every kit."""
    g.clock = rec
    if rec["verdict"] == "REFUSE":
        g.add("FAIL", "clock_rule", rec["text"] + ("" if rec["cts"] else " -- this gate ran without --cts")
              + (f" (declared clock '{rec['declared_clock']}' does not waive it)" if rec.get("declared_clock") else ""),
              TL.CLOCK_RULE_FIX)
    elif rec["verdict"] == "UNKNOWN":
        g.add("WARN", "clock_rule", "the synthesized netlist's clock sinks were not reported: " + rec["text"],
              "read the remote log (textbook lint line 'clock_roots')")
    else:
        g.add("INFO", "clock_rule", f"root {rec['root']}: {rec['text']}")


def kit_clock_evidence(kd: Path) -> dict | None:
    try:
        d = json.loads((kd / CLOCK_RESULT).read_text())
        return d["clock"] if isinstance(d.get("clock"), dict) else None
    except (OSError, ValueError, KeyError, AttributeError):
        return None


def check_clock_evidence(g: Gate, kd: Path, known_sinks: int | None = None, closed_stands: bool = False) -> dict:
    """SUBMIT side of the measured clock rule.  The kit's committed gate result decides when it exists; without one the
    sink count of this block's latest synthesized design (known_sinks, from the loop's job history) does.  A kit with no
    gate result and no history passes here and is judged by the in-flow lint right after synthesis (FLOORPLAN_MARGIN,
    before placement).  closed_stands: a CLOSED tile is not re-judged."""
    ev = kit_clock_evidence(kd)
    n = (ev or {}).get("max_root_sinks")
    if not isinstance(n, int):          # the kit's own gate result outranks history (a rebuilt tile proves itself)
        n = known_sinks if isinstance(known_sinks, int) else None
    ok, text = TL.clock_rule(n if isinstance(n, int) else None, ev)
    res = {"evidence": ev, "sinks": n, "ok": ok, "text": text, "closed_stands": bool(closed_stands)}
    g.clock = res
    if ok or closed_stands:
        g.add("INFO", "clock_rule", text + (" (CLOSED tile: stands)" if closed_stands and not ok else ""))
    else:
        src = "kit gate_result.json" if ev and ev.get("max_root_sinks") == n else "this block's latest synthesized design"
        g.add("FAIL", "clock_rule", f"{text} [{src}]", TL.CLOCK_RULE_FIX)
    return res


TEXTBOOK_FIX = {
    "clock_domain": "hardened sub-tiles with local roots and registered seams (kind cluster), <= ~15k sinks / 600 um a root",
    "high_fanout": "no reset on datapath registers; replicate enables / selects / pointer bits per region (<= ~256 loads)",
    "boundary": "register every boundary: pin flop in, flop out; never an ICG enable from a port",
    "logic_depth": "pipeline to ~700 ps a stage: trees, 2-3 rungs for wide compare / mux / arbitration",
    "wire_reach": "relay flops every <= 500 um, or move the logic next to its pins/macros",
    "util_channel": "size the outline to util 0.50-0.55 with >= 20 um macro channels",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="kit dir (physical/ref_tile/<name>) or a tile spec json")
    ap.add_argument("--job", help="closure-loop job spec (default: the kit's job.json)")
    ap.add_argument("--commit", help="check source paths at this commit (default: working tree)")
    ap.add_argument("--remote", help="fleet host for the synthesis / floorplan / textbook run (ot-epyc2, ...)")
    ap.add_argument("--cts", action="store_true", help="with --remote: continue through CTS, report insertion + paths")
    ap.add_argument("--synth-cap", type=int, default=2700, help="synthesis time cap, s (default 2700)")
    ap.add_argument("--mem", type=int, default=24, help="ot-heavy GB (< 32 = small slot, no big-slot wait)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    g = Gate()
    job = json.loads(Path(a.job).read_text()) if a.job else None
    if job and "spec" in job and "stages" not in job:
        job = job["spec"]
    try:
        if a.target:
            t = Path(a.target)
            t = t if t.is_absolute() else (Path.cwd() / t)
            if t.is_file():
                r = RT.gen(str(t))
                kd = ROOT / r["kit"]
                print(f"GATE: kit regenerated -> {r['kit']}")
            else:
                kd = t
            if job is None and (kd / "job.json").exists():
                job = json.loads((kd / "job.json").read_text())
            spec = check_kit(g, kd, job, a.commit)
            if a.remote and g.verdict != "FAIL":
                remote(g, kd, spec, a.remote, a.synth_cap, a.mem, a.cts)
            elif a.remote:
                g.add("INFO", "remote", "skipped: local FAIL first")
        elif job is not None:
            check_sources(g, job, (), a.commit or (job.get("source") or {}).get("commit"))
        else:
            ap.error("give a kit dir / spec, or --job")
    except RT.SpecError as ex:
        g.add("FAIL", "spec", str(ex), "fix the tile spec")
    g.print()
    if a.remote and getattr(g, "clock", None) and "kd" in locals():
        out = {"schema": "opentallas.ref_tile.gate_result.v1", "kit": kd.name, "verdict": g.verdict,
               "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": a.remote, "cts": bool(a.cts),
               "commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short=9", "HEAD"], capture_output=True,
                                        text=True).stdout.strip(),
               "clock": g.clock, "items": [i for i in g.items if i["severity"] != "INFO"][:40]}
        (kd / CLOCK_RESULT).write_text(json.dumps(out, indent=1) + "\n")
        print(f"GATE: {kd.name}/{CLOCK_RESULT} written (clock evidence for the submit gate: commit it with the kit)")
    if a.json:
        Path(a.json).write_text(json.dumps({"verdict": g.verdict, "items": g.items}, indent=1) + "\n")
    return 1 if g.verdict == "FAIL" else 0


def _materialise(repo: str, commit: str, kit: str, dst: Path) -> None:
    """extract the kit and everything its spec names (sources, views, contract) at the commit into dst"""
    def arch(paths):
        paths = [x for x in paths if subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{commit}:{x}"],
                                                    capture_output=True).returncode == 0]
        if not paths:
            return
        a = subprocess.run(["git", "-C", repo, "archive", commit, *paths], capture_output=True, timeout=120)
        subprocess.run(["tar", "-x", "-C", str(dst)], input=a.stdout, check=True)
    arch([kit, "physical/qwen_die_masters/io_ref_skew.sdc"])
    sp = json.loads((dst / kit / "spec.json").read_text())
    # sdc_extra too: without it RT.gen raised FileNotFoundError and the whole gate went SKIP for every kit that has one
    arch(list(sp.get("sources", [])) + list(sp.get("sdc_extra", []))
         + [it["view"] for it in sp.get("macros", []) + sp.get("children", [])]
         + ([sp["contract"]["file"]] if sp.get("contract") else []))


def check_slot_fit(g: Gate, kd: Path, job: dict, repo: str, commit: str = "") -> dict | None:
    """SLOT FIT (owner 2026-10-13, tools/hier_contract/slot_fit.py): a tile with a slot in a die contract must fit it
    BEFORE it routes -- outline, pin faces, pin layers, layer cap and the estimated clock insertion against the LIVE
    contract (origin/main of the repo's object store, else main, the job's commit, the working tree).  A mismatch FAILs (REFUSED at submit) unless the
    spec carries "slot_change_request": "<die lead log line or contract version>": then it is a WARN and the request is
    appended to the die lead's log."""
    import slot_fit
    cs, ref = slot_fit.live_contracts(Path(repo), commit)
    res = slot_fit.check(kd, Path(repo), job, cs)
    if res["status"] == "no_slot":
        return res
    where = f"slot {res['slot']} of {res['contract']} v{res['version']} ({ref})"
    for n in res["notes"]:
        g.add("INFO", "slot_fit", f"{where}: {n}")
    if res["status"] == "fit":
        g.add("INFO", "slot_fit", f"{res['top']} fits {where}")
        return res
    msg = f"{res['top']} does not fit {where}: " + "; ".join(res["mismatches"])
    req = res.get("slot_change_request")
    if req:
        log = slot_fit.append_request(res, str(job.get("name", res["kit"])), commit)
        g.add("WARN", "slot_fit", f"{msg} -- routes on slot_change_request {str(req)[:160]!r}"
              + (f" (appended to {log.name})" if log else " (no die lead log for this die: tell the lead)"))
    else:
        g.add("FAIL", "slot_fit", msg, "build the tile to its slot, or get the slot changed by the die lead and put "
              "\"slot_change_request\": \"<die lead log line or contract version>\" in the spec (check before submit: "
              "tools/hier_contract/slot_fit.py KIT_DIR)")
    return res


def submit_check(spec: dict, repo: str | None = None, known_sinks: int | None = None,
                 closed_stands: bool = False, clock_mode: str = "refuse") -> dict:
    """closure-loop submit hook: the LOCAL gate on a job spec AT ITS SOURCE COMMIT (kit / pins / RTL / children /
    source-sync for "ref_tile": true; source-sync only for any other job).  {"verdict": PASS|WARN|REFUSE|SKIP, "message"}.
    Never raises."""
    global ROOT
    import tempfile
    repo = repo or str(ROOT)
    g = Gate()
    old = (ROOT, RT.ROOT)
    try:
        commit = str((spec.get("source") or {}).get("commit", ""))
        with tempfile.TemporaryDirectory() as td:
            if spec.get("ref_tile"):
                m = re.search(r"ref_route\.sh\s+(\S+)/kit\.env", spec["stages"]["route"]["cmd"])
                if not m:
                    g.add("FAIL", "job", "ref_tile job without a tools/ref_tile/ref_route.sh <kit>/kit.env route")
                else:
                    kit = m.group(1)
                    _materialise(repo, commit, kit, Path(td))
                    if not (Path(td) / kit / "kit.env").exists():
                        g.add("FAIL", "kit", f"{kit}/kit.env missing at {commit}", "commit the generated kit")
                    else:
                        ROOT = RT.ROOT = Path(td)
                        check_kit(g, Path(td) / kit, None)
                        ROOT = RT.ROOT = Path(repo)
                        check_sources(g, spec, json.loads((Path(td) / kit / "floorplan.json").read_text())
                                      .get("referenced", []), commit)
                        check_slot_fit(g, Path(td) / kit, spec, repo, commit)
                        if clock_mode != "off":
                            check_clock_evidence(g, Path(td) / kit, known_sinks, closed_stands)
                            if clock_mode != "refuse":
                                for i in g.items:
                                    if i["check"] == "clock_rule" and i["severity"] == "FAIL":
                                        i["severity"] = "WARN"
            else:
                ROOT = RT.ROOT = Path(repo)
                check_sources(g, spec, (), commit)
    except Exception as ex:  # noqa: BLE001
        return {"verdict": "SKIP", "message": f"gate error {type(ex).__name__}: {str(ex)[:200]}"}
    finally:
        ROOT, RT.ROOT = old
    fails = [i for i in g.items if i["severity"] == "FAIL"]
    warns = [i for i in g.items if i["severity"] == "WARN"]
    msg = " | ".join(f"{i['check']}: {i['message']}" + (f" (fix: {i['fix']})" if i["fix"] else "")
                     for i in (fails or warns))[:1500]
    return {"verdict": "REFUSE" if fails else ("WARN" if warns else "PASS"), "message": msg or "pre-route gate PASS",
            "clock": getattr(g, "clock", None)}

if __name__ == "__main__":
    sys.exit(main())
