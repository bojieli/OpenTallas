#!/usr/bin/env python3
"""Gate C7 / O2 levers at batch > 1: the adopted stage-hop split under the T1 load of other users' collectives.

The adopted hop lever (tools/rtl_v41_collective_levers_campaign.py, results/rtl/v41_collective_levers_campaign.json:
hop_perdie7_split20) lets 2u of the 81 residual words ride ONE package's cables and cross to the other package over
the receiving module's T1 links: u / 2 words on each of the module's eight die-to-die T1 links per hop.  At batch 1
those links are otherwise idle.  In the pipeline fill the module a hop lands on is running other users' tokens,
whose tensor-group all-reduces and all-gathers use the same links.  This campaign measures, on
rtl/test/tb_v41_stage_hop_load_px.sv (the lever bench's senders, cables, receive buffers and links, with a
background source and an arbiter on every T1 link):

  * the hop tail (last residual word at every receiving die - the producer's last output), and
  * the delay the hop's T1 words impose on the other users' collectives (each collective's completion -- its last
    word at the last die -- against the same background with no hop),

for the split and for full-payload-per-package (no T1 words) under the same load, at pipeline fills of
1, 4, 14 and 28 users.  Every residual word and every background word is checked bit for bit.

Background (derived here from the design-point DAG, tools/arch_lanes_v41.design_point with the adopted levers, the
DAG tools/v41_collective_exposure.recommended_exposure prices):
  * stage of a node: the machine's hop_plan (layer -> stage of its attention half, stages after its substage hops);
  * a T1 event: every tensor-group collective the RECEIVING stage runs; per link it carries the per-peer bytes the
    lane pricing charges (arch_lanes_v41.m_lanes: the whole partial for an all-reduce, the quarter for an all-gather,
    halved by a two-step all-reduce) x the adopted relay's bytes_scale (0.5 on the relayed classes), in 512-B words;
  * burst structure: word k is produced at fin(producer) - W + ceil(W (k + 1) / n), W the producer's emission window
    (its issue; for the select / HBM-gather classes the O2 schedule span, as tools/v41_collective_exposure does); a
    two-step all-reduce's second half follows its first after a T1 flight and a fold;
  * fill n: n users evenly spaced by P / n in time (P the per-user pass period, + the draft with MTP); user k is
    k P / n ahead of the hopping user, so its stage events land at DAG time t - k P / n (mod P).  User 0 is the
    hopping user itself: its own events on the receiving stage that do not descend from the hop are included.
Events whose words fall within [lo, hi] cycles of the hop's producer finish are injected (whole events).

Modes: "ar" (one position, the 81-word hop the lever was adopted on) and "mtp" (the DSpark verify pass, gamma + 1 =
6 positions: a 481-word hop and 6x payload collectives on the m = 2 core; T1 ~15% busy at the 28-user fill).

    python3 tools/rtl_v41_hop_batch_campaign.py plan  --plan <plan.json>
    python3 tools/rtl_v41_hop_batch_campaign.py run   --plan <plan.json> --shard i/N --scratch <dir> --part <part.json>
    python3 tools/rtl_v41_hop_batch_campaign.py merge --plan <plan.json> --parts <part.json ...> [--out ...]

Run the shards through remote_gate from a pinned clean worktree.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_v41_stage_collective_campaign as B  # noqa: E402
import rtl_v41_collective_levers_campaign as L  # noqa: E402

OUT = ROOT / "results/rtl/v41_hop_batch_campaign.json"
TB = ROOT / "rtl/test/tb_v41_stage_hop_load_px.sv"
TOP = "tb_v41_stage_hop_load_px"
WORD_B, LANES, CLOCK = B.WORD_B, B.LANES, B.CLOCK
FILLS = (1, 4, 14, 28)
CTX = 1048576
MODES = {
    # hop words, one-package-word sweep (u), the adopted u, injection window around the hop's producer finish
    "ar": dict(mtp=False, words=81, splits=(8, 14, 20, 24), adopted=20, lo=-3000, hi=4000),
    "mtp": dict(mtp=True, words=481, splits=(60, 119, 180), adopted=119, lo=-4000, hi=9000),
}
ARBS = {0: "round_robin", 1: "hop_first", 2: "background_first"}
MAXW = 512


def sources():
    return L.sources() + [TB]


def source_sha256():
    pins = sources() + [Path(__file__).resolve(), Path(L.__file__).resolve(), Path(B.__file__).resolve(),
                        ROOT / "tools/arch_lanes_v41.py", ROOT / "tools/v41_collective_exposure.py",
                        ROOT / "tools/collective_exposure.py", ROOT / "results/arch/v41_lanes.json",
                        ROOT / "results/rtl/v41_collective_levers_campaign.json",
                        ROOT / "results/rtl/v41_stage_collective_campaign.json"]
    return {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest() for q in pins}


def git_head():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


# -- 1. the design-point DAG's T1 traffic ------------------------------------------------------------------------------
FIXED_WINDOW_PATTERN = {"all_gather_select": "gather_topk", "all_gather_rows": "gather_rows"}


def derive_traffic(mtp: bool):
    """Per stage hop: the receiving stage's T1 events (per-link words and the DAG cycle each is produced), the hop's
    producer finish, and the pass period, on the design point with the adopted levers."""
    from dataclasses import replace
    import arch_lanes_v41 as AL
    import arch_latency_ladder_v41 as LX
    import collective_exposure as CX
    import v41_collective_exposure as VX
    U, A = AL.U, AL.A
    dp = AL.design_point()
    lev = VX.recommended_exposure(VX.dump_on_path(U, A, dp["sp"], list(dp["muts"]) + [dp["ml"]], dp["hz"]))
    muts = list(dp["muts"]) + [dp["ml"], CX.mutation(lev["terms"])] + (
        [CX.consumer_mutation(tuple(lev["consumers"]))] if lev["consumers"] else [])
    scale = lev["bytes_scale"]
    hzv, prm = dp["hz"]
    lp = B.link_params()
    t1_bpc = lp["BPC_X"] / lp["BPC_X_DEN"]
    with LX.clock(hzv), U.params(**prm):
        clk = A._env()["clock"]
        sp = replace(dp["sp"], lane_mult=U.MTP_M) if mtp else dp["sp"]
        r = U.solve(sp, CTX, positions=(U.GAMMA + 1) if mtp else 1, levers=U.CHAIN_L3, muts=muts)
        draft = A.draft_cost_s(sp, CTX, U.GAMMA, A._env()["c"])["total_s"] if mtp else 0.0
        b = r["_built"]
        g = b.g
        mb = getattr(g, "mb", 1.0)
        fin = g.fin
        hp = b.mach.hop_plan
        crit = set(g.path(b.sink))
        kids = {}
        for n, nd in g.nodes.items():
            for d in nd["deps"]:
                kids.setdefault(d, []).append(n)
        passed, stage_of = {}, {}
        for n, nd in g.nodes.items():
            Ly = nd["layer"]
            if Ly is None or Ly not in hp:
                continue
            if nd["kind"] == "hop" and nd.get("hop_kind") == "substage":
                passed[Ly] = passed.get(Ly, 0) + 1
                stage_of[n] = ("hop", hp[Ly][1][passed[Ly] - 1])
                continue
            k = passed.get(Ly, 0)
            stage_of[n] = hp[Ly][0] if k == 0 else hp[Ly][1][k - 1]
        fold = (2 + 3 * A.ADD_LAT["fastfp"])
        events = {}
        for n, nd in g.nodes.items():
            s = stage_of.get(n)
            if nd["kind"] != "collective" or not isinstance(s, int):
                continue
            cls = CX.exposure_class(n, nd)
            per_peer = nd.get("_stream_issue_s", nd["issue"]) * clk * t1_bpc       # the lane pricing's bytes
            full_peer = nd["payload"] * mb * (1.0 if nd["op"] == "all_reduce" else 1.0 / (nd.get("span") or 4))
            two_step = nd["op"] == "all_reduce" and per_peer < 0.75 * full_peer
            sc = scale.get(cls, 1.0)
            words = max(1, math.ceil(per_peer * sc / WORD_B - 1e-9))
            prod = max(nd["deps"], key=lambda d: fin[d])
            pf = fin[prod] * clk
            if cls in FIXED_WINDOW_PATTERN:
                sch = B.schedule(B.PATTERNS[FIXED_WINDOW_PATTERN[cls]])
                W = max(sch) - min(sch) + 1
            else:
                W = max(1.0, g.nodes[prod]["issue"] * clk)
            n1 = math.ceil(words / 2) if two_step else words
            rel = [pf - W + math.ceil(W * (k + 1) / n1) for k in range(n1)]
            if two_step:                                  # reduce-scatter, then the all-gather after flight + fold
                rel += [pf + lp["LAT_X"] + fold] * (words - n1)
            events[n] = dict(stage=s, cls=cls, op=nd["op"], words=words, two_step=two_step, bytes_scale=sc,
                             per_link_bytes=per_peer * sc, rel=[int(round(x)) for x in rel], on_path=n in crit)
        hops = []
        for n, nd in g.nodes.items():
            s = stage_of.get(n)
            if not (isinstance(s, tuple) and s[0] == "hop"):
                continue
            desc, todo = set(), [n]
            while todo:
                x = todo.pop()
                for c in kids.get(x, ()):
                    if c not in desc:
                        desc.add(c)
                        todo.append(c)
            prod = nd["deps"][0]
            hops.append(dict(hop=n, stage=s[1], ref=fin[prod] * clk, producer=prod,
                             producer_issue=g.nodes[prod]["issue"] * clk, producer_depth=g.nodes[prod]["depth"] * clk,
                             payload_bytes=nd["payload"] * mb, on_path=n in crit,
                             stage_events=sorted(e for e, v in events.items() if v["stage"] == s[1]),
                             descendants=sorted(e for e in events if e in desc)))
        P = (r["period_s"] + draft) * clk
    busy = {}
    for e, v in events.items():
        busy[v["stage"]] = busy.get(v["stage"], 0.0) + v["words"] * WORD_B / t1_bpc
    return dict(mtp=mtp, clock_hz=clk, microbatch=mb, period_cycles=P, draft_cycles=draft * clk,
                t1_bytes_per_cycle=t1_bpc, bytes_scale=scale, events=events, hops=hops,
                stage_t1_busy_cycles_per_pass=busy,
                t1_busy_fraction_at_fill={str(n): {str(s): min(1.0, n * c / P) for s, c in busy.items()}
                                          for n in FILLS})


def background(tr, h, n, lo, hi, users=None):
    """The receiving module's T1 background for hop h at fill n: [(rel cycle, event key)] per word, sorted, and the
    event table.  users: explicit {k: offset cycles} (the phase scan) instead of the even spacing."""
    P = tr["period_cycles"]
    hop = tr["hops"][h]
    ref = hop["ref"]
    desc = set(hop["descendants"])
    offs = users if users is not None else {k: k * P / n for k in range(n)}
    words, table = [], {}
    for k, off in offs.items():
        for e in hop["stage_events"]:
            if k == 0 and e in desc:
                continue
            ev = tr["events"][e]
            for m in (-1, 0, 1):
                rel = [t - off + m * P - ref for t in ev["rel"]]
                if max(rel) < lo or min(rel) > hi:
                    continue
                key = f"u{k}:{e}:{m}"
                table[key] = dict(user=k, node=e, cls=ev["cls"], words=ev["words"], on_path=ev["on_path"],
                                  first_rel=int(round(min(rel))), last_rel=int(round(max(rel))))
                words += [(int(round(x)), key) for x in rel]
    words.sort()
    return words, table


# -- 2. cases -----------------------------------------------------------------------------------------------------------
def hop_schedule(mode, tr, h):
    """The hop producer's word schedule: the O2 stage_hop pattern (hc_post, 81 words at one position); with MTP the
    DAG's hc_post window and the 6-position residual."""
    p = dict(B.PATTERNS["stage_hop"], words=MODES[mode]["words"])
    if MODES[mode]["mtp"]:
        hop = tr["hops"][h]
        p.update(issue=max(1, int(round(hop["producer_issue"]))), depth=int(round(hop["producer_depth"])))
    return B.schedule(p)


def schemes(mode):
    m = MODES[mode]
    out = [("bgonly", None, 0), ("full", 0, 0)]
    for u in m["splits"]:
        out.append((f"split{u}", u, 0))
    for arb in (1, 2):
        out.append((f"split{m['adopted']}_{ARBS[arb]}", m["adopted"], arb))
    return out


def plan(path: Path):
    lp = B.link_params()
    tr = {mode: derive_traffic(m["mtp"]) for mode, m in MODES.items()}
    cases = []
    for mode, m in MODES.items():
        t = tr[mode]
        for h, hop in enumerate(t["hops"]):
            for n in FILLS:
                for sname, u, arb in schemes(mode):
                    cases.append(dict(name=f"{mode}_h{h:02d}_n{n:02d}_{sname}", mode=mode, hop=h, fill=n,
                                      scheme=sname, u=u, arb=arb, group=f"{mode}_h{h:02d}_n{n:02d}"))
                if n == 1:                                # the no-load reference (the lever campaign's case)
                    for sname, u, arb in schemes(mode)[1:2] + [(f"split{m['adopted']}", m["adopted"], 0)]:
                        cases.append(dict(name=f"{mode}_h{h:02d}_noload_{sname}", mode=mode, hop=h, fill=0,
                                          scheme=sname, u=u, arb=arb, group=f"{mode}_h{h:02d}_noload"))
    # phase scan: the hopping user plus ONE other user whose timeline is shifted by sigma (step 128 cycles) over every
    # shift that puts one of its receiving-stage events within 700 cycles of the hop, on the heaviest and the lightest
    # receiving stage (the worst case over any fill pattern, not only the even spacing)
    scan = []
    t = tr["ar"]
    heavy = max(range(len(t["hops"])), key=lambda h: sum(t["events"][e]["words"] for e in t["hops"][h]["stage_events"]))
    light = min(range(len(t["hops"])), key=lambda h: sum(t["events"][e]["words"] for e in t["hops"][h]["stage_events"]))
    for h in (heavy, light):
        hop = t["hops"][h]
        ts = [x for e in hop["stage_events"] for x in t["events"][e]["rel"]]
        lo_off = min(ts) - hop["ref"] - 700
        hi_off = max(ts) - hop["ref"] + 700
        for off in range(math.floor(lo_off / 128) * 128, int(hi_off) + 128, 128):
            for sname, u, arb in [("bgonly", None, 0), ("split20", 20, 0), ("split20_hop_first", 20, 1)]:
                cases.append(dict(name=f"scan_h{h:02d}_o{off:+07d}_{sname}", mode="ar", hop=h, fill=-1,
                                  scheme=sname, u=u, arb=arb, group=f"scan_h{h:02d}_o{off:+07d}", offset=off))
        scan.append(h)
    # background word lists
    for c in cases:
        m = MODES[c["mode"]]
        if c["fill"] == 0:
            bg, table = [], {}
        elif c["fill"] < 0:
            bg, table = background(tr[c["mode"]], c["hop"], 1, m["lo"], m["hi"], users={1: c["offset"]})
        else:
            bg, table = background(tr[c["mode"]], c["hop"], c["fill"], m["lo"], m["hi"])
        c["bg"] = bg
        c["events"] = table
    maxb = max(len(c["bg"]) for c in cases)
    rec = dict(schema="v41_hop_batch_plan/1", link_parameters=lp, modes=MODES, fills=FILLS,
               maxb=1 << max(6, math.ceil(math.log2(maxb + 1))), scan_hops=scan,
               traffic={k: {kk: vv for kk, vv in v.items()} for k, v in tr.items()}, cases=cases)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec) + "\n")
    print(f"{len(cases)} cases, max background words per link {maxb} -> MAXB {rec['maxb']}")
    return rec


# -- 3. run -------------------------------------------------------------------------------------------------------------
def build(scratch: Path, lp: dict, maxb: int) -> Path:
    params = dict(LANES=LANES, DEPTH=128, DEPTH_F=64, QTX=128, LAT_C=lp["LAT_C"],
                  BPC_C=int(round(7 * L.LANE_BPC * 100)), BPC_C_DEN=100, LAT_X=lp["LAT_X"], BPC_X=lp["BPC_X"],
                  BPC_X_DEN=100, LAT_U=lp["LAT_U"], BPC_U=lp["BPC_U"], MAXB=maxb)
    tag = TOP + "_" + "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    obj = scratch / f"obj_{hashlib.sha1(tag.encode()).hexdigest()[:12]}"
    exe = obj / f"V{TOP}"
    if exe.exists():
        return exe
    obj.mkdir(parents=True, exist_ok=True)
    h = obj / "harness.cpp"
    h.write_text(f'#include "V{TOP}.h"\n#include "verilated.h"\n'
                 "int main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 f"  auto* t = new V{TOP}; t->clk = 0;\n"
                 "  while (!Verilated::gotFinish()) { t->clk = !t->clk; t->eval(); }\n"
                 "  t->final(); delete t; return 0; }\n")
    B.sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
          "-Wno-MULTIDRIVEN", "-Wno-MULTITOP", "--top-module", TOP, *[f"-G{k}={v}" for k, v in params.items()],
          "-Mdir", str(obj), *map(str, sources()), str(h), "-CFLAGS", "-O1", "-j", "4"])
    for f in obj.iterdir():
        if f.name != exe.name:
            (shutil.rmtree if f.is_dir() else Path.unlink)(f)
    return exe


BGA = re.compile(r"BGA link=(\d+) word=(\d+) cyc=(\d+)")
BGL = re.compile(r"BGL " + " ".join(rf"l{i}=(\d+)/(\d+)/(\d+)" for i in range(8)))
BGDONE = re.compile(r"BGDONE bg=(\d+)/(\d+) bg_mismatches=(\d+)")


def run_case(exe: Path, scratch: Path, c: dict, tr: dict, maxb: int) -> dict:
    mode = MODES[c["mode"]]
    W = mode["words"] if c["u"] is not None else 0
    sch = hop_schedule(c["mode"], tr, c["hop"]) if W else [0]
    sched_last = max(sch)
    bg = c["bg"]
    first = min((x[0] for x in bg), default=0)
    start = max(20, 20 - sched_last - first)
    ref_bench = start + sched_last                       # the hop producer's last output, bench cycles
    vec = scratch / f"vec_{c['name']}"
    vec.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(hashlib.sha1(c["name"].encode()).hexdigest()[:8], 16))
    if W:
        lists, uniq = L.hop_lists("perdie", c["u"], W)
    else:
        lists, uniq = [[], [], [], []], [0]
    part = B.rand_f32(rng, max(W, 1) * LANES).reshape(max(W, 1), LANES)
    (vec / "part.hex").write_text("\n".join(B.hexw(part[k]) for k in range(max(W, 1))) + "\n")
    (vec / "ready.hex").write_text("\n".join(f"{x:08x}" for x in sch) + "\n")
    ll = []
    for d, lst in enumerate(lists):
        ll.append(f"@{d * MAXW:x}")
        ll += [f"{w:08x}" for w in lst]
    ll.append(f"@{4 * MAXW - 1:x}")
    ll.append("0")
    (vec / "list.hex").write_text("\n".join(ll) + "\n")
    (vec / "uniq.hex").write_text("\n".join(str(x) for x in uniq) + "\n")
    NB = len(bg)
    if NB:
        if NB > maxb:
            raise RuntimeError(f"{c['name']}: {NB} background words > MAXB {maxb}")
        bgd = B.rand_f32(rng, 8 * NB * LANES).reshape(8, NB, LANES)
        lines = []
        for l_ in range(8):
            lines.append(f"@{l_ * maxb:x}")
            lines += [B.hexw(bgd[l_, k]) for k in range(NB)]
        (vec / "bg.hex").write_text("\n".join(lines) + "\n")
        (vec / "bgrel.hex").write_text("\n".join(f"{ref_bench + x[0]:08x}" for x in bg) + "\n")
    args = [str(exe), f"+VEC={vec}", f"+WORDS={W}", f"+START={start}", f"+NB={NB}", f"+ARB={c['arb']}",
            f"+TIMEOUT={ref_bench + mode['hi'] + 40000}"] + [f"+LN{d}={len(x)}" for d, x in enumerate(lists)]
    txt = B.sh(args, timeout=3600)
    shutil.rmtree(vec, ignore_errors=True)
    dn = B.DONE.search(txt)
    bd = BGDONE.search(txt)
    if not dn or not bd:
        raise RuntimeError(f"{c['name']}: no result\n{txt[-2000:]}")
    arr = [tuple(map(int, m.groups())) for m in B.ARR.finditer(txt)]
    bga = [tuple(map(int, m.groups())) for m in BGA.finditer(txt)]
    bl = BGL.search(txt)
    lk = [tuple(map(int, bl.groups()[3 * i:3 * i + 3])) for i in range(8)] if bl else []
    # background word -> event; completion = its last word at the last die (all eight links)
    last = {}
    arrival = [0] * NB
    for l_, w, cy in bga:
        arrival[w] = max(arrival[w], cy)
    for (rel, key), cy in zip(bg, arrival):
        last[key] = max(last.get(key, -10**9), cy - ref_bench)
    # the background's own queueing: each event's completion minus its last word's production
    rec = dict(case=c["name"], mode=c["mode"], hop=c["hop"], fill=c["fill"], scheme=c["scheme"], u=c["u"],
               arb=ARBS[c["arb"]], group=c["group"], offset=c.get("offset"), hop_words=W, background_words=NB,
               background_events=len(c["events"]), start=start, ref=ref_bench,
               mismatches=int(dn.group(2)), background_mismatches=int(bd.group(3)),
               background_received=int(bd.group(1)), background_expected=int(bd.group(2)),
               timeout=int(dn.group(4)), passed=dn.group(5) == "PASS",
               link_words=[x[0] for x in lk], link_hop_words=[x[1] for x in lk], link_bg_queue_max=[x[2] for x in lk],
               event_completion_rel={k: v for k, v in sorted(last.items())})
    if W:
        per_die = {d: max(a[2] for a in arr if a[0] == d) for d in range(4)}
        rec.update(hop_tail_cycles=max(per_die.values()) - ref_bench,
                   per_die_tail_cycles={str(d): v - ref_bench for d, v in per_die.items()},
                   hop_words_received=len(arr))
    return rec


def run(a):
    pl = json.loads(a.plan.read_text())
    i, n = map(int, a.shard.split("/"))
    cases = [c for k, c in enumerate(sorted(pl["cases"], key=lambda c: c["name"])) if k % n == i]
    if a.only:
        cases = [c for c in cases if a.only in c["name"]]
    a.scratch = a.scratch.resolve()
    a.scratch.mkdir(parents=True, exist_ok=True)
    exe = build(a.scratch, pl["link_parameters"], pl["maxb"])
    tr = pl["traffic"]
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda c: run_case(exe, a.scratch, c, tr[c["mode"]], pl["maxb"]), cases))
    a.part.parent.mkdir(parents=True, exist_ok=True)
    a.part.write_text(json.dumps(dict(shard=a.shard, git_head=git_head(), source_sha256=source_sha256(),
                                      cases=res)) + "\n")
    print(f"shard {a.shard}: {len(res)} cases, all pass {all(r['passed'] for r in res)}")


# -- 4. merge and summarise ----------------------------------------------------------------------------------------------
def victim_delays(case, ref, events):
    """Per other user: the largest completion delay over its collectives (conservative: every collective charged),
    and over its critical-path collectives only; the hopping user's own events are excluded (user 0)."""
    per, per_path = {}, {}
    for k, v in case["event_completion_rel"].items():
        e = events[k]
        if e["user"] == 0 and case["fill"] >= 0:
            continue
        d = v - ref["event_completion_rel"][k]
        per[e["user"]] = max(per.get(e["user"], 0), d)
        if e["on_path"]:
            per_path[e["user"]] = max(per_path.get(e["user"], 0), d)
    return per, per_path


def summarise(pl, cases):
    by = {c["case"]: c for c in cases}
    plan_by = {c["name"]: c for c in pl["cases"]}
    rows = []
    for c in cases:
        if c["scheme"] == "bgonly" or c["fill"] == 0:
            continue
        ref = by[f"{c['group']}_bgonly"]
        vd, vdp = victim_delays(c, ref, plan_by[c["case"]]["events"])
        # the hopping user's own background events (user 0, not descending from the hop)
        own = {k: v - ref["event_completion_rel"][k] for k, v in c["event_completion_rel"].items()
               if plan_by[c["case"]]["events"][k]["user"] == 0}
        rows.append(dict(case=c["case"], mode=c["mode"], hop=c["hop"], fill=c["fill"], scheme=c["scheme"],
                         offset=c["offset"], tail=c["hop_tail_cycles"], victim_delay=sum(vd.values()),
                         victim_delay_on_path=sum(vdp.values()), victims=len(vd),
                         max_victim_delay=max(vd.values(), default=0), own_event_delay=max(own.values(), default=0),
                         background_events=c["background_events"]))
    out = dict(all_pass=all(c["passed"] for c in cases),
               bit_exact=all(c["mismatches"] == 0 and c["background_mismatches"] == 0 for c in cases),
               cases=len(cases))
    # no-load reference: must reproduce the lever campaign's per-hop tails
    lev = json.loads(L.OUT.read_text())
    lev_t = {c["case"]: c["exposed_tail_cycles"] for c in lev["cases"]}
    noload = {}
    for mode, m in MODES.items():
        nl = [c for c in cases if c["mode"] == mode and c["fill"] == 0]
        noload[mode] = {s: sorted({c["hop_tail_cycles"] for c in nl if c["scheme"] == s})
                        for s in sorted({c["scheme"] for c in nl})}
    noload["lever_campaign_ar"] = dict(full=lev_t.get("hop_perdie7_full"), split20=lev_t.get("hop_perdie7_split20"))
    out["no_load"] = noload
    fills = {}
    for mode, m in MODES.items():
        nh = len(pl["traffic"][mode]["hops"])
        fm = {}
        for n in pl["fills"]:
            R = [r for r in rows if r["mode"] == mode and r["fill"] == n]
            sch = {}
            for s in sorted({r["scheme"] for r in R}):
                rs = [r for r in R if r["scheme"] == s]
                assert len(rs) == nh, (mode, n, s, len(rs))
                sch[s] = dict(tail_mean=sum(r["tail"] for r in rs) / nh, tail_max=max(r["tail"] for r in rs),
                              tail_min=min(r["tail"] for r in rs),
                              victim_delay_mean=sum(r["victim_delay"] for r in rs) / nh,
                              victim_delay_max=max(r["victim_delay"] for r in rs),
                              victim_delay_on_path_mean=sum(r["victim_delay_on_path"] for r in rs) / nh,
                              max_single_collective_delay=max(r["max_victim_delay"] for r in rs),
                              hops_with_victims=sum(1 for r in rs if r["victims"]),
                              hops_with_delayed_victims=sum(1 for r in rs if r["victim_delay"] > 0),
                              own_event_delay_max=max(r["own_event_delay"] for r in rs),
                              # per user per token, over the pass's stage hops: its own hop tails plus the delay
                              # its collectives take from the hop behind it (every user is the victim once per hop)
                              token_cycles=sum(r["tail"] + r["victim_delay"] for r in rs),
                              token_cycles_on_path=sum(r["tail"] + r["victim_delay_on_path"] for r in rs),
                              effective_hop_cycles=sum(r["tail"] + r["victim_delay"] for r in rs) / nh)
            full = sch["full"]["token_cycles"]
            for s, v in sch.items():
                v["token_cycles_vs_full"] = v["token_cycles"] - full
                v["token_cycles_on_path_vs_full"] = v["token_cycles_on_path"] - sch["full"]["token_cycles_on_path"]
            best = min(sch, key=lambda s: sch[s]["token_cycles"])
            fm[str(n)] = dict(schemes=sch, best_scheme=best,
                              t1_busy_fraction_mean=sum(pl["traffic"][mode]["t1_busy_fraction_at_fill"][str(n)].values())
                              / len(pl["traffic"][mode]["t1_busy_fraction_at_fill"][str(n)]),
                              t1_busy_fraction_max=max(pl["traffic"][mode]["t1_busy_fraction_at_fill"][str(n)].values()))
        adopted = f"split{m['adopted']}"
        gains = {n: -fm[str(n)]["schemes"][adopted]["token_cycles_vs_full"] for n in pl["fills"]}
        cross = None
        ns = list(pl["fills"])
        for a_, b_ in zip(ns, ns[1:]):
            if gains[a_] > 0 >= gains[b_]:
                cross = a_ + (b_ - a_) * gains[a_] / (gains[a_] - gains[b_])
                break
        if cross is None and gains[ns[0]] <= 0:
            cross = ns[0]
        fills[mode] = dict(adopted=adopted, per_fill=fm, split_gain_cycles_per_token=gains,
                           split_loses_at=[n for n in ns if gains[n] <= 0], crossover_fill_interpolated=cross,
                           policy={str(n): fm[str(n)]["best_scheme"] for n in ns})
    out["fills"] = fills
    scan = {}
    for h in pl["scan_hops"]:
        R = [r for r in rows if r["fill"] == -1 and r["hop"] == h]
        sc = {}
        for s in sorted({r["scheme"] for r in R}):
            rs = sorted((r for r in R if r["scheme"] == s), key=lambda r: r["offset"])
            worst = max(rs, key=lambda r: r["tail"] + r["victim_delay"])
            sc[s] = dict(offsets=len(rs), tail_max=max(r["tail"] for r in rs), tail_min=min(r["tail"] for r in rs),
                         victim_delay_max=max(r["victim_delay"] for r in rs),
                         worst_offset=worst["offset"], worst_tail_plus_victim=worst["tail"] + worst["victim_delay"],
                         mean_tail_plus_victim=sum(r["tail"] + r["victim_delay"] for r in rs) / len(rs))
        scan[str(h)] = dict(hop=pl["traffic"]["ar"]["hops"][h]["hop"], schemes=sc)
    out["phase_scan"] = scan
    return out, rows


def merge(a):
    pl = json.loads(a.plan.read_text())
    cases, heads, pins = [], set(), None
    for p in a.parts:
        d = json.loads(Path(p).read_text())
        cases += d["cases"]
        heads.add(d["git_head"])
        pins = pins or d["source_sha256"]
        if d["source_sha256"] != pins:
            raise SystemExit(f"{p}: shard ran on different sources")
    names = {c["name"] for c in pl["cases"]}
    got = {c["case"] for c in cases}
    if names != got:
        raise SystemExit(f"missing {len(names - got)} cases, e.g. {sorted(names - got)[:5]}")
    if pins != source_sha256():
        raise SystemExit("shards ran on sources that differ from this tree")
    summ, rows = summarise(pl, cases)
    tr = {}
    for mode, t in pl["traffic"].items():
        tr[mode] = dict(clock_hz=t["clock_hz"], microbatch=t["microbatch"], period_cycles=t["period_cycles"],
                        draft_cycles=t["draft_cycles"], bytes_scale=t["bytes_scale"],
                        t1_bytes_per_cycle=t["t1_bytes_per_cycle"],
                        stage_t1_busy_cycles_per_pass=t["stage_t1_busy_cycles_per_pass"],
                        t1_busy_fraction_at_fill=t["t1_busy_fraction_at_fill"],
                        hops=[dict(hop=h["hop"], stage=h["stage"], ref_cycle=h["ref"], on_path=h["on_path"],
                                   payload_bytes=h["payload_bytes"],
                                   stage_events={e: dict(cls=t["events"][e]["cls"], words_per_link=t["events"][e]["words"],
                                                         two_step=t["events"][e]["two_step"],
                                                         on_path=t["events"][e]["on_path"],
                                                         first_word_cycle=min(t["events"][e]["rel"]),
                                                         last_word_cycle=max(t["events"][e]["rel"]))
                                                 for e in h["stage_events"]})
                              for h in t["hops"]])
    rec = dict(schema="v41_hop_batch_campaign/1", tool="tools/rtl_v41_hop_batch_campaign.py",
               gate="C7 / O2 levers at batch > 1", bench=str(TB.relative_to(ROOT)),
               lever_campaign=str(L.OUT.relative_to(ROOT)), git_head=sorted(heads),
               link_parameters=pl["link_parameters"], modes=MODES, fills=list(pl["fills"]),
               arbitration=ARBS, sources=[str(p.relative_to(ROOT)) for p in sources()],
               source_sha256=pins,
               derivation=__doc__.split("Background (")[1].split("    python3")[0].strip(),
               claim_boundary=("behavioural links (flight ring + token-bucket rate + credit lane) and the lever bench's "
                               "hop senders / receivers; the other users' collectives are open-loop word sources at "
                               "their DAG production cycles (a delayed collective does not move its user's later "
                               "collectives), consumed on arrival; UCIe contention (0.4% busy) not modelled; single "
                               "clock, no PHY / FEC / retries"),
               traffic=tr, summary=summ, rows=rows, cases=cases)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for mode, f in summ["fills"].items():
        print(mode, "gain/token", {n: round(v) for n, v in f["split_gain_cycles_per_token"].items()},
              "cross", f["crossover_fill_interpolated"], "policy", f["policy"])
    print("all_pass", summ["all_pass"], "bit_exact", summ["bit_exact"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--plan", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--plan", type=Path, required=True)
    r.add_argument("--shard", default="0/1")
    r.add_argument("--scratch", type=Path, required=True)
    r.add_argument("--part", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--only", default="")
    m = sub.add_parser("merge")
    m.add_argument("--plan", type=Path, required=True)
    m.add_argument("--parts", nargs="+", required=True)
    m.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    {"plan": lambda: plan(a.plan), "run": lambda: run(a), "merge": lambda: merge(a)}[a.cmd]()


if __name__ == "__main__":
    main()
