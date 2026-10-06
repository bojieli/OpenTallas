#!/usr/bin/env python3
"""DS-ROM recovery lever "field": the ROM-field matvec NODES re-measured on the PIPELINED-PHASE successor vehicle
(PQ), one return region at full shape, every region of the rank-0 die, one layer per layer type, bit-exact against
the golden at the 1M token -- the as-built measurement (tools/dsrom_1m_field.py, results/rtl/
dsrom_1m_allmeasured_20261004/field.json) with the pinned spine/field replaced by their PQ successors.

    python3 tools/dsrom_recovery_field.py variant --plan-dir PLANDIR --out VARDIR   (re-placement R93, below)
    python3 tools/dsrom_recovery_field.py build  --work DIR [--jobs 16] [--gap 12 --guard 180 --gslack 6]
    python3 tools/dsrom_recovery_field.py run    --work DIR --plan-dir PLANDIR [--jobs 48] [--only-nodes ...]
    python3 tools/dsrom_recovery_field.py record --work DIR --plan-dir PLANDIR [--record field_pq.json]
    python3 tools/dsrom_recovery_field.py lever  [--record field_pq.json] [--ssff field_pq_ssff.json] [--verdict ADOPT]
            (-> results/rtl/dsrom_recovery_20261004/levers/field.json, opentallas.dsrom-recovery.lever.v1)

PLANDIR is a tools/dsrom_1m_field.py work directory after `plan` and `extract` (plan.json, x.npz, mats/): the SAME
S81 canonical placement, released-checkpoint rank-0 rows, golden experts and x (L20: the golden 1M token's x of
every op) as the as-built record.

RE-PLACEMENT R93 (`variant`).  S81 region 93 is the only region with 3 BF16-capable pairs (119 have 4, 8 have 5):
with 4 superrows of a wo_a group in it, one BF pair holds two of them (16 words a round > the BF16 element's 8),
which splits EVERY layer's wo_a group into a rows0 and a rows768 phase die-wide.  The variant makes one FP pair of
region 93 (NEW_BF, 1773: ~2,860 of 8,192 words used) BF16-capable (519 -> 520 BF sites on the die) and moves the
rows768 superrow(s) of each wo_a group in region 93 onto it; each group is then ONE legal phase in every region.
Everything else is the S81 canonical map unchanged.

VEHICLE.  rtl/v41die/ot_v41_fieldtop_pq_w17w10 (successors: ot_v41_spine_pq_w17w10, ot_v41_field_pq_w17w10,
ot_v41_pair_pq_w17w10, rtl/v41rom/ot_v41_rom_elem_pq_w10) with PQ = 1, built exactly as the as-built vehicle
(NP 32 pair slots, R 1, NBF 5, FAST/PP W10 element, BP 0, BST 2) except PHW 3 (8 phases) and VAW 17 (x of every op
resident).  A NODE RUN is one region with every phase of the node (on one die) that has rows in the region, in the
plan's order, issued back to back: the spine prefetches the next op's x and broadcasts its configuration while the
current op streams (the elements load it into a shadow), issues its go GAP cycles after the current op's last beat
(GUARD after the one before), and the field drains op k while op k + 1 streams.
Every row of every op is checked bit for bit against tools/hdc_golden_v41 (R-ARITH chunk8), as in the as-built bench.

COMPOSITION (die level, from the measured region runs, the as-built rule "each phase at the max over regions"):
  s_i   = max_r (last beat - go) of phase i                         (stream; measured)
  go_1  = accept + c_first;  go_{i+1} = max(end_i + c_gap, end_{i-1} + c_guard)   (spine rule; constants measured
          in the runs and checked on every consecutive op pair)
  node  = max_{r,i} (go_i + (last row write of op i in r - its go in r)) - accept       (+ S81 wire once)
The broadcast/return wire is paid ONCE per node: the next op's issue depends only on spine-local state (its own
last beat), never on a returned row, and every element's deferral is local, so the out-and-back wire overlaps.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_field as F1  # noqa: E402
import hdc_golden_v41 as G  # noqa: E402
import v41_die_images_w17w10 as I  # noqa: E402

NP, NR, NBF, PHW, VAW = 32, 1, 5, 3, 17
XSTRIDE, OBASE, OSTRIDE = 8192, 98304, 2048
CLK = 1.2e9
DIE_PQ = [ROOT / f"rtl/v41die/{n}.sv" for n in ("ot_v41_retn_w17w10", "ot_v41_pair_pq_ld", "ot_v41_pair_pq_w17w10", "ot_v41_field_pq_w17w10",
                                                 "ot_v41_spine_pq_w17w10", "ot_v41_fieldtop_pq_w17w10")]
RTL = F1.RTL + [ROOT / "rtl/v41rom/ot_v41_rom_elem_pq_w10.sv", ROOT / "rtl/v41rom/ot_v41_elem_pq_tags.sv"]
TB = ROOT / "rtl/test/dsrom_sys/tb_dsrom_recovery_field_pq.cpp"
TOOLS = [Path(__file__), ROOT / "tools/dsrom_1m_field.py", ROOT / "tools/v41_die_images_w17w10.py",
         ROOT / "tools/v41_rom_ksplit_bankmap.py", ROOT / "tools/rtl_v41_rom_array.py", ROOT / "tools/hdc_golden_v41.py"]
SOURCES = sorted(set(RTL + DIE_PQ + F1.ROMS + [TB] + TOOLS))
REC_DIR = ROOT / "results/rtl/dsrom_recovery_20261004"
ASBUILT = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/field.json"


def sha(p) -> str:
    return F1.sha(p)


# ------------------------------------------------------------------------------------------------ re-placement
NEW_BF, R93 = 1773, 93


def cmd_variant(a):
    pdir, out = a.plan_dir.resolve(), a.out.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    rb = plan["region_bounds"]
    assert rb[R93] <= NEW_BF < rb[R93 + 1] and NEW_BF not in plan["bf_sites"]
    xz = dict(np.load(pdir / "x.npz"))
    (out / "mats").mkdir(parents=True, exist_ok=True)
    phases, merged = [], {}
    for ph in plan["phases"]:
        m = re.fullmatch(r"(L\d+\.wo_a\.g\d)\.wo_a\.group\d\.rows(0|768)", ph["phase"])
        if not m:
            phases.append(ph)
            continue
        merged.setdefault(m.group(1), []).append(ph)
        if len(merged[m.group(1)]) == 1:
            phases.append(dict(_merge=m.group(1)))
    moved = []
    for i, ph in enumerate(phases):
        if "_merge" not in ph:
            continue
        name = ph["_merge"]
        a0, a1 = sorted(merged[name], key=lambda q: q["phase"].endswith("rows768"))
        assert np.array_equal(xz[a0["phase"]], xz[a1["phase"]]) and a0["out"] == a1["out"] and a0["K"] == a1["K"]
        mats = [dict(mm) for mm in a0["mats"] + a1["mats"]]
        for mm in a1["mats"]:
            assert mm["alias"].endswith("rows768")
        k = len(a0["mats"])
        for mm in mats[k:]:
            ents = mm["regions"].get(str(R93), [])
            if ents:
                mm["regions"] = dict(mm["regions"])
                mm["regions"][str(R93)] = [[sr, seg, NEW_BF] for sr, seg, _ in ents]
                moved.append(dict(phase=name, alias=mm["alias"], superrows=sorted({sr for sr, _, _ in ents}),
                                  from_pairs=sorted({p for _, _, p in ents}), to_pair=NEW_BF))
        bad = [r for r in range(128) if F1.illegal(mats, r)]
        assert not bad, (name, bad[:4], F1.illegal(mats, bad[0]))
        phases[i] = dict(a0, phase=name, mats=mats, split_reason=None,
                         regions=sorted(set(a0["regions"]) | set(a1["regions"])),
                         replaced=[a0["phase"], a1["phase"]])
        xz[name] = xz[a0["phase"]]
        z0, z1 = np.load(pdir / "mats" / f"{a0['phase']}.npz"), np.load(pdir / "mats" / f"{a1['phase']}.npz")
        arr = {kk: z0[kk] for kk in z0.files}
        for kk in z1.files:
            j, rest = kk.split(".", 1)
            arr[f"{int(j) + k}.{rest}"] = z1[kk]
        np.savez(out / "mats" / f"{name}.npz", **arr)
    for ph in phases:
        f = out / "mats" / f"{ph['phase']}.npz"
        if not f.exists():
            f.symlink_to(pdir / "mats" / f"{ph['phase']}.npz")
    vplan = dict(plan, phases=phases, bf_sites=sorted(plan["bf_sites"] + [NEW_BF]),
                 variant=dict(name="S81+R93", new_bf_site=NEW_BF, region=R93, moved=moved, base_plan_sha256=sha(pdir / "plan.json"),
                              note=__doc__.split("RE-PLACEMENT R93 (`variant`).")[1].split("VEHICLE.")[0].strip()))
    (out / "plan.json").write_text(json.dumps(vplan, indent=1) + "\n")
    np.savez(out / "x.npz", **xz)
    print(len(plan["phases"]), "->", len(phases), "phases;", len(moved), "superrow moves")
    return 0


# ------------------------------------------------------------------------------------------------ build
def cmd_build(a):
    out = (a.work / "build").resolve()
    out.mkdir(parents=True, exist_ok=True)
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([F1.VERILATOR, "-V"], text=True)).group(1)
    params = ["-GFAST=1", "-GPP=1", "-GBP=0", f"-GNP={NP}", f"-GR={NR}", f"-GNBF={NBF}", f"-GPHW={PHW}", f"-GVAW={VAW}",
              "-GPQ=1", f"-GGAP={a.gap}", f"-GGUARD={a.guard}", f"-GGSLACK={a.gslack}"]
    mdir = out / "pq"
    steps = []
    for name, cmd in (
            ("verilate", [F1.VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
                          "--top-module", "ot_v41_fieldtop_pq_w17w10", "--prefix", "Vpq", "--Mdir", str(mdir), *params,
                          *map(str, DIE_PQ + F1.ROMS + RTL)]),
            ("make", ["make", "-C", str(mdir), "-f", "Vpq.mk", f"-j{a.jobs}", "Vpq__ALL.a", "OPT_FAST=-O2",
                      "OPT_SLOW=-O1"]),
            ("link", ["g++", "-std=c++20", "-O2", f"-DNR={NR}", f"-DVAW={VAW}", f"-I{vroot}/include",
                      f"-I{vroot}/include/vltstd", f"-I{mdir}", str(TB), str(mdir / "Vpq__ALL.a"),
                      f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                      "-pthread", "-o", str(out / "tb")])):
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append(dict(name=name, seconds=round(time.time() - t0, 1), returncode=p.returncode))
        print(name, steps[-1], flush=True)
        if p.returncode:
            raise SystemExit(f"{name} failed: {(p.stdout + p.stderr)[-3000:]}")
    (out / "build.json").write_text(json.dumps(dict(
        steps=steps, params=params, tb_sha256=sha(out / "tb"),
        simulator=subprocess.check_output([F1.VERILATOR, "--version"], text=True).strip(),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in SOURCES}), indent=1) + "\n")
    return 0


# ------------------------------------------------------------------------------------------------ node groups
def node_groups(plan, only=None):
    """{(layer, node, stage): [phase dicts in plan order]} for every node with a multi-phase die (all its dies)."""
    g = {}
    for ph in plan["phases"]:
        g.setdefault((ph["layer"], ph["node"], ph["stage"]), []).append(ph)
    multi = {(L, n) for (L, n, s), v in g.items() if len(v) > 1}
    out = {k: v for k, v in g.items() if (k[0], k[1]) in multi}
    if only:
        out = {k: v for k, v in out.items() if k[1] in only}
    return out


def gname(k):
    L, n, s = k
    return f"L{L}.{n}.st{s}"


_FULL = {}


def full_mats(pdir, ph):
    key = ph["phase"]
    if key not in _FULL:
        if len(_FULL) > 8:
            _FULL.clear()
        F1._FULL.clear()
        _FULL[key] = F1.full_mats(pdir, ph)
        F1._FULL.clear()
    return _FULL[key]


def node_image(pdir, phs, reg, rb, bfs, xs, img: Path, npos: int = 1):
    """Image of region `reg` for the node's phases (those with rows in the region): phase k = op k.  Returns the ops
    file text, expect {addr: word} and per-op meta."""
    pairs = list(range(rb[reg], rb[reg + 1]))
    bfp = [p for p in pairs if p in bfs]
    qp = [p for p in pairs if p not in bfs]
    assert len(bfp) <= len(F1.BF_SLOTS) and len(qp) <= NP - len(F1.BF_SLOTS)
    qslots = [s for s in range(NP) if s not in F1.BF_SLOTS]
    slot = {p: F1.BF_SLOTS[i] for i, p in enumerate(bfp)} | {p: qslots[i] for i, p in enumerate(qp)}
    fld = I.Field(NP, NR, NBF, pp=True, fast=True)
    vm = np.zeros(1 << VAW, dtype=np.uint32)
    expect, metas, opl = {}, [], []
    for k, ph in enumerate(phs):
        mats, gmap = [], []
        for mm, full in zip(ph["mats"], full_mats(pdir, ph)):
            pl = mm["regions"].get(str(reg), [])
            if not pl:
                continue
            srows = sorted({s for s, _, _ in pl})
            loc = {s: j for j, s in enumerate(srows)}
            rows = [r for s in srows for r in (2 * s, 2 * s + 1) if r < mm["entry_rows"]]
            sub = F1.take(full, rows)
            sub.s81_segments = mm["segments"]
            sub.s81_place = [(loc[s], seg, slot[p]) for s, seg, p in pl]
            mats.append(sub)
            gmap.append((mm, rows))
        fp32 = ph["out"] == "fp32"
        meta = I.add_phase(fld, mats, (fp32, fp32), 0)
        ob = OBASE + k * OSTRIDE
        assert npos * meta["nrows"] <= OSTRIDE and meta["nrows"] < (1 << 14)
        xb = k * npos * XSTRIDE
        for pos in range(npos):
            # multi-position (MTP) self-test: position p's x is the op's x with every sign flipped for odd p
            x = xs[ph["phase"]] ^ np.uint32(0x80000000 if pos % 2 else 0)
            vm[xb + pos * XSTRIDE:xb + pos * XSTRIDE + ph["K"]] = x
            gold = I.golden_phase(mats, G.from_bits(x).astype(G.F))
            for i in range(meta["nrows"]):
                f32, b16 = gold[i]
                expect[ob + pos * meta["nrows"] + i] = f32 if fp32 else (b16 << 16)
        assert xb + npos * XSTRIDE <= OBASE
        opl.append(f"{k} {npos - 1} {xb} {XSTRIDE} {ob} {meta['nrows']}")
        metas.append(dict(phase=ph["phase"], nbeat=meta["nbeat"], t_read=meta["t_read"], nrows=meta["nrows"],
                          obase=ob, segments_per_pair_max=meta["segments_per_pair_max"]))
    assert len(phs) <= (1 << PHW) and len(fld.stream) < (1 << 14)
    I.write_field(fld, img, PHW)
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    return "\n".join(opl) + "\n", expect, metas


def run_one(args):
    work, pdir, key, phs, reg, rb, bfs, keep, npos = args
    G.set_arith("chunk8")
    xz = np.load(Path(pdir) / "x.npz")
    xs = {ph["phase"]: xz[ph["phase"]] for ph in phs}
    rd = Path(work) / ("runs" if npos == 1 else f"runs_np{npos}") / gname(key) / f"r{reg:03d}"
    if rd.exists():
        shutil.rmtree(rd)
    img = rd / "img"
    img.mkdir(parents=True)
    t0 = time.time()
    ops, expect, metas = node_image(pdir, phs, reg, rb, bfs, xs, img, npos)
    (rd / "ops.txt").write_text(ops)
    t1 = time.time()
    p = subprocess.run([str(Path(work) / "build" / "tb"), str(img), str(rd / "ops.txt")], capture_output=True,
                       text=True)
    t2 = time.time()
    lines = p.stdout.splitlines()
    writes, ev = {}, dict(A={}, G={}, E={})
    wcyc = {}
    for ln in lines:
        t = ln.split()
        if not t:
            continue
        if t[0] == "W":
            ad = int(t[2])
            writes.setdefault(ad, []).append(int(t[3], 16))
            wcyc[ad] = int(t[1])
        elif t[0] in ("G", "E"):
            ev[t[0]].setdefault(int(t[2]), []).append(int(t[1]))
        elif t[0] == "A":
            ev["A"][int(t[1])] = int(t[2])
    node = [ln for ln in lines if ln.startswith("NODE ")]
    nd = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", node[0])} if node else {}
    wrong = [ad for ad, v in expect.items() if writes.get(ad) != [v]]
    extra = [ad for ad in writes if ad not in expect]
    ok = p.returncode == 0 and bool(lines) and lines[-1].startswith("PASS") and not wrong and not extra
    # per op (in order; tags are k mod 4): go, last beat, last row write
    ops_out = []
    for k, m in enumerate(metas):
        gk = ev["G"].get(k % 4, [])
        ek = ev["E"].get(k % 4, [])
        g_ = gk[k // 4] if len(gk) > k // 4 else None
        e_ = ek[k // 4] if len(ek) > k // 4 else None
        lw = max((wcyc[a] for a in range(m["obase"], m["obase"] + npos * m["nrows"]) if a in wcyc), default=None)
        ops_out.append(dict(m, accept=ev["A"].get(k), go=g_, end=e_, last_w=lw))
    res = dict(group=gname(key), region=reg, pass_=ok, rows=len(expect), mismatched=len(wrong), extra=len(extra),
               first_mismatch=[(ad, writes.get(ad), expect[ad]) for ad in wrong[:3]], ops=ops_out,
               node=nd, image_s=round(t1 - t0, 2), sim_s=round(t2 - t1, 2),
               tail=lines[-1:] if lines else p.stderr[-300:])
    (rd / "result.json").write_text(json.dumps(res) + "\n")
    if not keep:
        shutil.rmtree(img)
        (rd / "sim.log").write_text("\n".join(ln for ln in lines if not ln.startswith("W ")) + "\n")
    else:
        (rd / "sim.log").write_text(p.stdout + p.stderr)
    return res


def cmd_run(a):
    work = a.work.resolve()
    pdir = a.plan_dir.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    rb, bfs = plan["region_bounds"], set(plan["bf_sites"])
    groups = node_groups(plan, set(a.only_nodes.split(",")) if a.only_nodes else None)
    if a.layers:
        groups = {k: v for k, v in groups.items() if k[0] in {int(x) for x in a.layers.split(",")}}
    tasks = []
    for key, phs in groups.items():
        regs = sorted({r for ph in phs for r in ph["regions"]})
        if a.regions:
            regs = [r for r in regs if r in set(map(int, a.regions.split(",")))]
        for reg in regs:
            if not a.force and (work / "runs" / gname(key) / f"r{reg:03d}" / "result.json").exists():
                continue
            sub = [ph for ph in phs if reg in ph["regions"]]
            tasks.append((str(work), str(pdir), key, sub, reg, rb, bfs, a.keep, a.positions))
    tasks.sort(key=lambda t: (gname(t[2]), t[4]))
    print(f"{len(tasks)} node-region runs over {len(groups)} node groups", flush=True)
    bad = 0
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for i, r in enumerate(ex.map(run_one, tasks, chunksize=2)):
            bad += not r["pass_"]
            if not r["pass_"] or i % 50 == 0:
                print(i, r["group"], r["region"], "PASS" if r["pass_"] else "FAIL", r["rows"], r["node"],
                      r["tail"], r["first_mismatch"], flush=True)
    print("failed", bad)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ record
def spine_rule(groups_rs):
    """The spine's measured issue constants over every node run: c_first (accept -> first go), c_gap (last beat
    -> next go), c_guard (last beat of op j-2 -> go of op j where that binds), c_cfg (go -> next go floor: the
    next configuration is broadcast after a go and loads CW words + settle).  Every consecutive pair is checked."""
    first, gaps = [], []
    for rs in groups_rs:
        for r in rs:
            o = r["ops"]
            first.append(o[0]["go"] - o[0]["accept"])
            for j in range(1, len(o)):
                gaps.append((o[j]["go"], o[j - 1]["end"], o[j - 2]["end"] if j >= 2 else None, o[j - 1]["go"]))
    c_first = max(first)
    assert min(first) == c_first, ("first go latency differs", sorted(set(first)))
    c_gap = min(g - e1 for g, e1, e2, g1 in gaps)
    c_guard = max([g - e2 for g, e1, e2, g1 in gaps if e2 is not None and g - e1 > c_gap] or [0])
    c_cfg = c_first + 1
    rule = lambda e1, e2, g1: max(e1 + c_gap, (e2 + c_guard) if e2 is not None else 0, g1 + c_cfg)
    viol = [x for x in gaps if x[0] != rule(*x[1:])]
    return dict(c_first=c_first, c_gap=c_gap, c_guard=c_guard, c_cfg=c_cfg, rule_checked=len(gaps),
                rule_violations=len(viol), violations=viol[:5])


def compose(phs, rs, k):
    """Die-level node cycles from the region runs (see the module docstring), spine constants k (spine_rule)."""
    n = len(phs)
    idx = {ph["phase"]: i for i, ph in enumerate(phs)}
    s = [0] * n
    drains = []
    for r in rs:
        for op in r["ops"]:
            i = idx[op["phase"]]
            s[i] = max(s[i], op["end"] - op["go"])
            drains.append((i, op["last_w"] - op["go"] if op["last_w"] is not None else None))
    go = [0] * n
    end = [0] * n
    go[0] = k["c_first"]
    for i in range(n):
        if i:
            go[i] = max(end[i - 1] + k["c_gap"], (end[i - 2] + k["c_guard"]) if i >= 2 else 0, go[i - 1] + k["c_cfg"])
        end[i] = go[i] + s[i]
    dmax = max((go[i] + d) for i, d in drains if d is not None)
    return dict(cycles=dmax, stream=s, go=go)


def cmd_record(a):
    work = a.work.resolve()
    pdir = a.plan_dir.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    build = json.loads((work / "build" / "build.json").read_text())
    groups = node_groups(plan)
    asb = json.loads(ASBUILT.read_text())
    asb_nodes = {(n["node"], n["die_stage"]): n for n in asb["nodes"]}
    asb_sum = {n["node"]: n for n in asb["node_summary"]}
    fp = json.loads((ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json").read_text())["trunk_stages"]
    W_S81 = 2 * fp["stages_at_504"]["field_one_way"] - F1.BST_IN_VEHICLE
    W = F1.WIRE_X_TO_FARTHEST - F1.BST_IN_VEHICLE + F1.WIRE_CLUSTER_TO_VM
    out_nodes, allx = [], True
    runs = {}
    for key, phs in sorted(groups.items()):
        regs = sorted({r for ph in phs for r in ph["regions"]})
        rs = []
        for reg in regs:
            f = work / "runs" / gname(key) / f"r{reg:03d}" / "result.json"
            rs.append(json.loads(f.read_text()) if f.exists() else None)
        runs[key] = (regs, rs)
    k_rule = spine_rule([[r for r in rs if r] for regs, rs in runs.values()])
    print("spine rule", k_rule)
    for key, phs in sorted(groups.items()):
        L, node, st = key
        regs, rs = runs[key]
        complete = all(r is not None for r in rs)
        rs = [r for r in rs if r]
        exact = complete and all(r["pass_"] for r in rs)
        allx &= exact
        c = compose(phs, rs, k_rule) if complete and exact else None
        mname = node if node.startswith("E1.") else f"L{L}.{node}"
        ab = asb_nodes.get((mname, st))
        tot = c["cycles"] + W_S81 if c else None
        out_nodes.append(dict(
            node=mname, layer=L, die_stage=st, phases=[ph["phase"] for ph in phs], regions=len(regs),
            regions_run=len(rs), rows_checked=sum(r["rows"] for r in rs),
            rows_mismatched=sum(r["mismatched"] + r["extra"] for r in rs), exact=exact,
            measured_cycles=c["cycles"] if c else None, composition=c,
            wire_stage_cycles_s81_floorplan=W_S81, total_cycles=tot,
            total_us_s81_floorplan_wire=tot / CLK * 1e6 if tot else None,
            total_us_routed_geometry_wire=(c["cycles"] + W) / CLK * 1e6 if c else None,
            asbuilt_measured_cycles=ab["measured_cycles"] if ab else None,
            asbuilt_total_us_s81_floorplan_wire=ab["total_us_s81_floorplan_wire"] if ab else None,
            model_us=ab["model_us"] if ab else None))
    summary = {}
    for n in out_nodes:
        summary.setdefault(n["node"], []).append(n)
    node_summary = []
    for name, ns in summary.items():
        top = max(ns, key=lambda n: n["total_cycles"] or 0)
        old = asb_sum.get(name, {})
        node_summary.append(dict(node=name, layer=top["layer"], dies=[n["die_stage"] for n in ns],
                                 total_cycles=top["total_cycles"], us=top["total_us_s81_floorplan_wire"],
                                 asbuilt_us=old.get("total_us_s81_floorplan_wire"), model_us=old.get("model_us"),
                                 rows_checked=sum(n["rows_checked"] for n in ns),
                                 exact=all(n["exact"] for n in ns)))
    rec = dict(
        schema="opentallas.dsrom.recovery.field_pq.v1", status="pass" if allx else "fail",
        claim_boundary=("RTL measurement (Verilator, 2-state) of the S81 rank-0 dies' multi-phase ROM-field matvec "
                        "nodes on the PQ (pipelined-phase) successor vehicle, one region at full shape, every region, "
                        "bit-exact vs the golden; die-level node time composed from the region runs with the spine's "
                        "measured issue rule; S81 floorplan wire stages added once per node."),
        vehicle=dict(top="ot_v41_fieldtop_pq_w17w10 (PQ=1, flat)", NP_slots=NP, R=NR, NBF_slots=NBF, PHW=PHW,
                     VAW=VAW, FAST=1, PP=1, BP=0, BST=F1.BST_IN_VEHICLE, build_params=build["params"],
                     description=__doc__.split("VEHICLE.")[1].split("COMPOSITION")[0].strip()),
        composition_rule=__doc__.split("COMPOSITION")[1].strip(), spine_rule=k_rule,
        plan_dir=str(pdir), plan_sha256=sha(pdir / "plan.json"), x_sha256=sha(pdir / "x.npz"),
        golden=dict(token_position=1048575, context=1048576, experts=plan["experts"], gold_vm=plan["gold_vm"],
                    arith="chunk8 (tools/hdc_golden_v41)"),
        node_summary=node_summary, nodes=out_nodes, simulator=build["simulator"], tb_sha256=build["tb_sha256"],
        build_source_sha256=build["source_sha256"],
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
        git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1) + "\n")
    for n in node_summary:
        print(f"{n['node']:24s} {n['us'] if n['us'] is None else round(n['us'], 4)} us  (as-built "
              f"{n['asbuilt_us'] and round(n['asbuilt_us'], 4)}, model {n['model_us'] and round(n['model_us'], 4)}) "
              f"exact {n['exact']}")
    return 0 if allx else 1


SUFFIXES = ("attn.a_proj", "attn.wq_b", "attn.wo_a", "ffn.experts_gu", "ffn.down")


def cmd_lever(a):
    """The lever record: every S81 graph node of a re-measured (layer type, node) gets the PQ measurement of its
    representative layer (the as-built adapter's mapping, tools/dsrom_1m_allmeasured_adapters.field_rep)."""
    import dsrom_1m_allmeasured_adapters as AD
    import dsrom_1m_measure as M
    rec = json.loads(a.record.read_text())
    ssff = json.loads(a.ssff.read_text()) if a.ssff and a.ssff.exists() else None
    by = {n["node"]: n for n in rec["node_summary"]}
    g, _, _ = M.s58_graph()
    nodes = {}
    for name in g.nodes:
        head, _, suf = name.partition(".")
        if name == "E1.wkv":
            x = by.get(name)
        elif head.startswith("L") and head[1:].isdigit() and suf in SUFFIXES:
            L = int(head[1:])
            x = by.get(name) or by.get(f"L{AD.field_rep(L)}.{suf}")
        else:
            continue
        if x is None:
            continue
        assert x["exact"], x["node"]
        nodes[name] = dict(us=round(x["us"], 6), cls="measured",
                           source=(f"{x['node']}: PQ pipelined-phase ROM field RTL (S81+R93 placement), one region at "
                                   f"full shape, every region, {x['rows_checked']} rows exact, + S81 floorplan wire "
                                   f"once (as-built {x['asbuilt_us'] and round(x['asbuilt_us'], 4)} us, model "
                                   f"{x['model_us'] and round(x['model_us'], 4)} us)"))
    exact = rec["status"] == "pass"
    out = dict(
        schema="opentallas.dsrom-recovery.lever.v1", lever="field", verdict=a.verdict, exact=exact,
        ss_ff=ssff, nodes=nodes,
        measurement=dict(record=str(a.record.resolve().relative_to(ROOT)), record_sha256=sha(a.record),
                         node_summary=[{k: n[k] for k in ("node", "dies", "total_cycles", "us", "asbuilt_us",
                                                          "model_us", "rows_checked", "exact")}
                                       for n in rec["node_summary"]],
                         vehicle=rec["vehicle"]["top"], placement="S81 canonical + R93 re-placement (one more "
                         "BF16-capable pair in region 93; each wo_a group one phase)",
                         rtl=sorted(k for k in rec["source_sha256"] if k.startswith(("rtl/", "physical/")))),
        note=a.note)
    a.lever_out.parent.mkdir(parents=True, exist_ok=True)
    a.lever_out.write_text(json.dumps(out, indent=1) + "\n")
    print(len(nodes), "nodes ->", a.lever_out)
    return 0


def phase_latency_budget(record, extra_cycles):
    """Exposed per-phase budget, charged before parallel die maximum.

    This is a conservative analytical debit, not a new measurement or a guessed
    pipeline overlap schedule. Existing measured region/stream/wire terms stay fixed.
    """
    if extra_cycles < 0 or int(extra_cycles) != extra_cycles:
        raise ValueError("extra cycles must be a nonnegative integer")
    if record["status"] != "pass":
        raise ValueError("positive historical field measurement required")
    groups = {}
    for n in record["nodes"]:
        if not n["exact"] or not n["phases"]:
            raise ValueError("missing exact measured phase ownership")
        base = n["measured_cycles"] + n["wire_stage_cycles_s81_floorplan"]
        if base != n["total_cycles"]:
            raise ValueError("measured stream/wire decomposition mismatch")
        row = dict(node=n["node"], die_stage=n["die_stage"], phases=n["phases"],
                   phase_count=len(n["phases"]), measured_base_cycles=base,
                   added_cycles=len(n["phases"]) * extra_cycles,
                   total_cycles=base + len(n["phases"]) * extra_cycles)
        groups.setdefault(n["node"], []).append(row)
    summary = {}
    for name, rows in groups.items():
        critical = max(rows, key=lambda n: n["total_cycles"])
        summary[name] = dict(us=critical["total_cycles"] / CLK * 1e6,
                             critical_die=critical["die_stage"], dies=rows)
    if extra_cycles == 0:
        for n in record["node_summary"]:
            if abs(summary[n["node"]]["us"] - n["us"]) > 1e-9:
                raise ValueError("zero-debit replay differs from measured summary")
    return summary


def cmd_sensitivity(a):
    """Read-only 1M DAG replay; the historical REJECT lever is never changed."""
    from types import SimpleNamespace
    import dsrom_1m_allmeasured as A
    import dsrom_1m_allmeasured_adapters as AD
    import dsrom_1m_measure as M
    rec = json.loads(a.record.read_text())
    plan_binding = None
    if a.plan_dir:
        plan_path = a.plan_dir / "plan.json"
        if sha(plan_path) != rec["plan_sha256"]:
            raise ValueError("retained plan SHA differs from measured field target")
        plan = json.loads(plan_path.read_text())
        plan_binding = dict(path=str(plan_path), sha256=sha(plan_path),
                            measured_layers=sorted({p["layer"] for p in plan["phases"]}),
                            measured_plan_phases=len(plan["phases"]), bf_sites=len(plan["bf_sites"]),
                            full40_native_coverage=False)
        known_phases = {p["phase"] for p in plan["phases"]}
        if any(p not in known_phases for n in rec["nodes"] for p in n["phases"]):
            raise ValueError("measurement references phase absent from retained plan")
    field = json.loads((REC_DIR / "levers/field.json").read_text())
    graph, _, _ = M.s58_graph()
    def replay(candidate=None):
        args = SimpleNamespace(rec=A.REC, out=None, baseline="recovery", recovery=REC_DIR,
                               window="s81", hop_tier="light_fec")
        r = A.compose(args, candidates=() if candidate is None else (candidate,), write_output=False)
        if r["context"] != 1048576 or r["position"] != 1048575:
            raise ValueError("sensitivity requires actual 1M target context")
        return r
    baseline = replay()
    points = []
    for delta in (0, 2, 4, 6, 8):
        budget = phase_latency_budget(rec, delta)
        nodes = {}
        for name in field["nodes"]:
            head, _, suffix = name.partition(".")
            representative = name if name in budget else f"L{AD.field_rep(int(head[1:]))}.{suffix}"
            b = budget[representative]
            nodes[name] = dict(us=b["us"], cls="conditional_measured_base_plus_model_budget",
                source=f"{representative}: fixed measured field base + {delta} streaming cycles per phase; "
                       "per-die debit then parallel maximum, wire once; no pipeline/exactness qualification")
            if name not in graph.nodes:
                raise ValueError("field mapping not in canonical 1M graph: " + name)
        r = replay(dict(lever="field_spine_sensitivity", exact=True, nodes=nodes))
        points.append(dict(extra_stream_cycles_per_phase=delta, AR_us=r["AR_us"], AR_tok_s=r["AR_tok_s"],
            MTP=r["MTP"], AR_gain_vs_baseline=r["AR_tok_s"] / baseline["AR_tok_s"] - 1,
            MTP_gain_vs_baseline=r["MTP"]["MTP_tok_s"] / baseline["MTP"]["MTP_tok_s"] - 1,
            representative_phase_budgets=budget, mapped_nodes=len(nodes)))
    out = dict(schema="opentallas.dsrom.field-spine-sensitivity.v1", verdict="ANALYTICAL_ONLY",
        adoption=False, physical_qualified=False, context=1048576, position=1048575,
        clock_domain="streaming", clock_hz=CLK, added_edge_ns=1e9/CLK,
        debit_rule="measured die cycles + ordered phase count * extra cycles; max across parallel dies, "
                   "then representative mapping and full AR/MTP DAG replay; never per instruction/row/root",
        assumption="All added phase edges exposed: conservative latency budget, not a redesigned RTL measurement. "
                   "Historical PQ exactness/measurements retain their original source pins; corrected leaf gates "
                   "do not requalify the historical full-field measurement. No arithmetic/SSFF/adoption claim.",
        baseline=dict(AR_us=baseline["AR_us"], AR_tok_s=baseline["AR_tok_s"], MTP=baseline["MTP"]),
        historical_field_verdict=field["verdict"], measured_spine_rule=rec["spine_rule"],
        plan_dir_historical=rec["plan_dir"], plan_sha256=rec["plan_sha256"],
        retained_plan_binding=plan_binding,
        graph_coverage="Full40 canonical graph uses existing field_rep mapping of seven historical measured layers; "
                       "not full40 native measurement or BF519 placement requalification",
        measurement_source_sha256=rec["build_source_sha256"],
        inputs={**baseline["inputs"], str(a.record.relative_to(ROOT)):sha(a.record),
                "tools/dsrom_recovery_field.py":sha(Path(__file__)),
                "tools/dsrom_1m_allmeasured.py":sha(ROOT/"tools/dsrom_1m_allmeasured.py")}, points=points)
    target = a.out or REC_DIR / "field_spine_sensitivity.json"
    if target.parent.resolve() == (REC_DIR / "levers").resolve():
        raise ValueError("sensitivity output belongs outside mutable adopted-lever inventory")
    if target.exists():
        raise ValueError("refusing to overwrite existing sensitivity result")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2) + "\n")
    for point in points:
        print(point["extra_stream_cycles_per_phase"], point["AR_tok_s"], point["MTP"]["MTP_tok_s"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("variant", "build", "run", "record", "lever", "sensitivity"))
    ap.add_argument("--ssff", type=Path, default=REC_DIR / "field_pq_ssff.json")
    ap.add_argument("--verdict", default="ADOPT")
    ap.add_argument("--note", default="")
    ap.add_argument("--lever-out", type=Path, default=REC_DIR / "levers/field.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--plan-dir", type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--gap", type=int, default=12)
    ap.add_argument("--guard", type=int, default=180)
    ap.add_argument("--gslack", type=int, default=6)
    ap.add_argument("--only-nodes", default="")
    ap.add_argument("--layers", default="")
    ap.add_argument("--regions", default="")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--positions", type=int, default=1, help="run: MTP positions per op (self-test of np > 0 ops)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--record", type=Path, default=REC_DIR / "field_pq.json")
    a = ap.parse_args()
    G.set_arith("chunk8")
    return {"variant": cmd_variant, "build": cmd_build, "run": cmd_run, "record": cmd_record,
            "lever": cmd_lever, "sensitivity": cmd_sensitivity}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
