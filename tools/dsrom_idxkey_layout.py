#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash) index-key ROW LAYOUT at 1M: the re-index candidate-block gather and the
full scans on a layout where each 8-key block (17 sectors) owns one DRAM row, measured in full-shape RTL on
the real 1M candidate lists (results/rtl/w17_v41_1m_reference_token.json, seed 20260930, shards in --gold).

Why: the adopted gather (ot_hdc_v41x_idx_kgather, results/rtl/dsrom_reindex_candidates_20261004) reads the
super-block layout, where a block's 17 sectors land in 17 different banks (0.78-0.83 ACT a sector): 0.47-0.58
TB/s a rank, 12-14% of peak, worst rank 757 cycles.  The row layout (rtl/hdc/v41x/ot_hdc_v41x_idx_rowmap.svh)
puts the block in columns 0..16 of ONE row (1 ACT + 17 column reads) and rotates consecutive blocks over
pseudo-channel, bank group, bank.  Writer: ot_hdc_v41x_idx_ring_kwr_row; reader (list = gather, range = scan):
ot_hdc_v41x_idx_kgrow.  Both opt-in; the super-block layout and its readers stay the default.

Subcommands (heavy ones on the compute host under admit.sh):
  trace    rtl/test/ot_hdc_v41x_idx_hbm_trace.sv minus its TRACE lines == rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv.
  gather   timing runs (controller returns the sector-address pattern, every key of every beat checked, DRAM
           command checker on every command, refresh live): the real 1M candidate lists of every rank, two
           placements; functional edge cases; the full scans of the row layout (L20: 8,192 blocks a stack,
           L2/L8/L14: 4,096); the AS-BUILT gather (ot_hdc_v41x_idx_kgather) on the same lists under the same
           checker (derived bench, comparison only); analytic bounds of the row layout on the real lists.
  rt       write -> read ROUND TRIP per rank: the row-layout writer PLACEs every key of the candidate blocks
           (and their neighbours) of the rank's 1M state; rank 3 holds count 1,048,575 and the decode STEP of
           position 1,048,575 appends the token's own key and migrates the six 8-key groups whose quarter
           moves; then the reader gathers the candidate blocks (+ the migrated and newest blocks in a second
           rank-3 run) and every key must equal the bytes written.  The beat streams are kept.
  select   the top-512 select (ot_hdc_v41x_sel) on the round trip's RTL beat streams (positions, order and
           packing as emitted) with the golden 1M L24 / L28 index scores, rank by rank, then the cross-die
           final: bit-exact against tools/hdc_golden_v41.topk_lowest_index and equal to the golden selection.
  screen   collect the SS / FF pre-layout screen of ot_hdc_v41x_idx_kgrctl (tools/dsrom_reindex_screen.py).
  compose  the 1M AR / MTP composition (tools/dsrom_1m_measure.py compose) with the row-layout gather read and
           its select stream for the re-index layers; every other input is the adopted composition's
           (results/rtl/dsrom_reindex_candidates_20261004); the scanned layers keep their measured reader.
Records: results/rtl/dsrom_idxkey_layout_20261004/.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/dsrom_idxkey_layout_20261004"
GOLD_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
CTX, POS, TP, STACKS = 1048576, 1048575, 4, 4
PER_RANK = CTX // TP                       # 262,144 positions a rank
PER_STACK = PER_RANK // STACKS             # 65,536 a stack quarter
BLK_STACK = PER_STACK // 8                 # 8,192 blocks
RSB, RTAIL = 64, 32
C_RING = RSB * 1024 + RTAIL                # ring capacity, keys (ot_hdc_v41x_idx_ring_kwr geometry)
CBLK = C_RING // 8
NINF = 0xFF80
CLK_PS, BURST_PS = 833, 1024
PEAK_SECTORS_PER_CYCLE_RANK = STACKS * 32 * CLK_PS / BURST_PS
PEAK_TBPS_RANK = STACKS * 32 * 32 / (BURST_PS * 1e-12) / 1e12
HBM = dict(tFAW_ns=15.0, acts_per_tFAW=4, tCCD_S_ns=1.024, tCCD_L_ns=2.56, burst_ns=1.024, pcs=32,
           tRFCpb_ns=200.0, tREFIpb_ns=3900.0 / 32)
V = "rtl/hdc/v41x/"
KGR_SRC = ["rtl/test/ot_hdc_v41x_idx_hbm_trace.sv", V + "ot_hdc_v41x_idx_kgrow.sv", V + "ot_hdc_v41x_idx_ring_kwr_row.sv",
           "rtl/test/tb_hdc_v41x_idx_kgrow.sv", "rtl/test/hdc_v41x_idx_kgrow.cpp"]
KGR_INC = [V + "ot_hdc_v41x_idx_rowmap.svh"]
OLD_SRC = [V + "ot_hdc_v41x_idx_kgather.sv", "rtl/test/tb_hdc_v41x_idx_kgather.sv", "rtl/test/hdc_v41x_idx_kgather.cpp"]
# placements: p1 = the real ring geometry at count 262,144 a rank (quarter q starts at ring slot q 65,536 mod C:
# stacks 1-3 wrap the ring after 4, 8 and 12 blocks); p2 = other region rows and ring heads
PLACE = {"p1": lambda q: (q * 16, ((q * PER_STACK) % C_RING) // 8),
         "p2": lambda q: (37 + 11 * q, (123 + 777 * q) % CBLK)}


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verilator():
    import rtl_hdc_v41x_sel_campaign as S
    return S.VERILATOR


# ------------------------------------------------------------------------------------------------ layout
def rowmap(row0: int, x: int, col: int) -> int:
    """Python mirror of idx_rowmap_sec (ot_hdc_v41x_idx_rowmap.svh)."""
    row = row0 + (x >> 10)
    pc = (x & 31) ^ (row & 31)
    bank = (x >> 5) & 31
    b42 = (bank >> 2) ^ ((row >> 2) & 7)
    b10 = (bank & 3) ^ (row & 3)
    return (row << 15) | (b42 << 12) | (col << 7) | ((pc ^ col ^ (((row & 3) << 3) | b42)) << 2) | b10


def ctrl_map(s: int):
    """The controller's map (ot_hdc_v41x_idx_hbm, NPC 32): (pc, bank, row, column) of sector s."""
    row = s >> 15
    pc = ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31
    bank = ((((s >> 12) ^ (row >> 2)) & 7) << 2) | ((s ^ row) & 3)
    return pc, bank, row, (s >> 7) & 31


def layout_check():
    """Every block: 17 sectors on one (pc, bank, row), columns 0..16; blocks of a region on distinct rows."""
    seen = set()
    for row0 in (0, 37):
        for x in range(0, 2 * 8196):
            locs = {ctrl_map(rowmap(row0, x, c))[:3] for c in range(17)}
            cols = sorted(ctrl_map(rowmap(row0, x, c))[3] for c in range(17))
            assert len(locs) == 1 and cols == list(range(17)), (row0, x)
            key = (row0,) + next(iter(locs))
            assert key not in seen
            seen.add(key)
    return dict(blocks_checked=len(seen), one_row_per_block=True, columns="0..16", distinct_rows=True)


def cand_blocks(gold: Path):
    c = np.load(gold / "ctx1048576_cand.npz")["cand"]
    b = c.reshape(-1, 8)
    assert not (b.any(1) & ~b.all(1)).any(), "candidate blocks are whole 8-position blocks"
    return c, np.nonzero(b.any(1))[0]


def rank_lists(blk, r):
    out = []
    for q in range(STACKS):
        lo = (r * PER_RANK + q * PER_STACK) // 8
        out.append([int(x - lo) for x in blk if lo <= x < lo + BLK_STACK])
    return out


def bounds(lists, place):
    """Analytic lower bounds of the row layout for one rank: each block's 17 column reads are on one
    (channel, bank group): >= 17 x 1.024 ns per block on its channel, >= 17 x tCCD_L on its bank group."""
    worst_pc, worst_bg, tot = 0.0, 0.0, 0
    for q, l in enumerate(lists):
        row0, x0 = PLACE[place](q)
        pcs, bgs = {}, {}
        for lb in l:
            x = (x0 + lb) % CBLK
            pc, bank, _, _ = ctrl_map(rowmap(row0, x, 0))
            pcs[pc] = pcs.get(pc, 0) + 1
            bgs[(pc, bank & 3)] = bgs.get((pc, bank & 3), 0) + 1
            tot += 17
        worst_pc = max(worst_pc, 17 * max(pcs.values(), default=0) * HBM["burst_ns"])
        worst_bg = max(worst_bg, 17 * max(bgs.values(), default=0) * HBM["tCCD_L_ns"])
    t = max(worst_pc, worst_bg)
    return dict(sectors=tot, channel_bound_ns=round(worst_pc, 1), bank_group_bound_ns=round(worst_bg, 1),
                bound_cycles=round(t / (CLK_PS / 1000)), peak_cycles=round(tot / PEAK_SECTORS_PER_CYCLE_RANK),
                bound_fraction_of_peak=round(tot / PEAK_SECTORS_PER_CYCLE_RANK / (t / (CLK_PS / 1000)), 4))


def balance_bounds(blk):
    """Channel-balance bound of ANY static block -> channel map at this gather size: a block cut into m
    chunks on m distinct channels, chunks dealt round robin; worst rank's (total / (128 x max channel))."""
    out = {}
    for m, sizes in ((1, [17]), (2, [9, 8]), (4, [5, 4, 4, 4]), (17, [1] * 17)):
        worst = 1.0
        for r in range(TP):
            loads, tot = [], 0
            for q, l in enumerate(rank_lists(blk, r)):
                pc = np.zeros(32)
                for lb in l:
                    for i, n in enumerate(sizes):
                        pc[(m * (lb + 17 * q) + i) % 32] += n
                        tot += n
                loads.append(pc.max())
            worst = min(worst, tot / (128 * max(loads)))
        out[f"chunks_{m}"] = dict(chunk_sectors=sizes, acts_per_sector=round(m / 17, 3),
                                  worst_rank_balance_fraction=round(worst, 3))
    return out


# ------------------------------------------------------------------------------------------------ benches
KGS = re.compile(r"KGSTACK s=(\d+) blocks=(\d+) sectors=(\d+) first=(-?\d+) last=(-?\d+)")
KGH = re.compile(r"KGHBM s=(\d+) rd=(\d+) act=(\d+) hit=(\d+) conf=(\d+) ref=(\d+) bp=(\d+) lat_sum_ps=(\d+) "
                 r"lat_max_ps=(\d+) pc_rd_min=(\d+) pc_rd_max=(\d+)")
DCK = re.compile(r"DRAMCHK s=(\d+) pre=(\d+) ref=(\d+) act=(\d+) rd=(\d+) wr=(\d+) viol=(\d+) rrefd=(\d+) "
                 r"ref_round_bad=(\d+) ref_gap_max_ps=(\d+)")
DVL = re.compile(r"DRAMCHK_VIOLATION t=(\d+) ps pc=(\d+) bank=(\d+) (.*)")
PASS_NEW = re.compile(r"KGROW_PASS blocks=([\d,]+) sectors=(\d+) last=(-?\d+)")
PASS_OLD = re.compile(r"KGATHER_PASS blocks=([\d,]+) sectors=(\d+) last=(-?\d+)")
WRL = re.compile(r"KGROW_WRITE cmds=(\d+) keys=(\d+) migrations=(\d+) copied=(\d+) cycles=(\d+)")


def build_new(obj: Path, params: dict):
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [verilator(), "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
           "--top-module", "tb_hdc_v41x_idx_kgrow", *[f"-G{k}={v}" for k, v in params.items()],
           f"-I{ROOT / V}", "--Mdir", str(obj), *[str(ROOT / s) for s in KGR_SRC]]
    subprocess.run(cmd, check=True, capture_output=True, cwd=ROOT)
    return obj / "Vtb_hdc_v41x_idx_kgrow"


def build_old(obj: Path, params: dict):
    """The as-built gather bench with its controller swapped for the traced copy (derived file, comparison)."""
    obj.mkdir(parents=True, exist_ok=True)
    tb = (ROOT / "rtl/test/tb_hdc_v41x_idx_kgather.sv").read_text()
    a, b = "        ot_hdc_v41x_idx_hbm #(", "                     s,rd,act,hit,conf,refs,hm.st_bp_cycles,hm.st_rd_lat_sum,hm.st_rd_lat_max,rmin,rmax);\n"
    assert tb.count(a) == 1 and tb.count(b) == 1
    tb = tb.replace(a, "        ot_hdc_v41x_idx_hbm_trace #(").replace(b, b + "            hm.dram_check(s);\n")
    (obj / "tb_old_traced.sv").write_text(tb)
    cmd = [verilator(), "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
           "--top-module", "tb_hdc_v41x_idx_kgather", *[f"-G{k}={v}" for k, v in params.items()], "--Mdir", str(obj),
           str(ROOT / "rtl/test/ot_hdc_v41x_idx_hbm_trace.sv"), str(ROOT / OLD_SRC[0]), str(obj / "tb_old_traced.sv"),
           str(ROOT / OLD_SRC[2])]
    subprocess.run(cmd, check=True, capture_output=True, cwd=ROOT)
    return obj / "Vtb_hdc_v41x_idx_kgather"


def write_inputs(pfx: Path, cmds, lists, wr=None):
    with open(f"{pfx}.cmd", "w") as f:
        for c in cmds:
            f.write(" ".join(str(int(v)) for v in c) + "\n")
    for q, l in enumerate(lists):
        if l is not None:
            assert l == sorted(set(l)) and len(l) <= 2048
            Path(f"{pfx}.s{q}").write_text(f"{len(l)}\n" + "".join(f"{x:x}\n" for x in l))
    if wr is not None:
        Path(f"{pfx}.wr").write_text("".join(f"{o} {n} {p}\n" for o, n, p in wr))


def parse(stdout: str, rc: int, old=False, extra=None):
    m = (PASS_OLD if old else PASS_NEW).search(stdout)
    if rc or not m:
        return dict(pass_=False, log=stdout[-3000:])
    stacks = []
    for sm, hm, dm in zip(KGS.finditer(stdout), KGH.finditer(stdout), DCK.finditer(stdout)):
        s, nb, sec, first, last = map(int, sm.groups())
        _, rd, act, hit, conf, ref, bp, ls, lm, rmin, rmax = map(int, hm.groups())
        _, pre, refc, actc, rdc, wrc, viol, rrefd, rbad, gap = map(int, dm.groups())
        stacks.append(dict(stack=s, blocks=nb, sectors=sec, first_out=first, last_out=last, hbm_reads=rd,
                           activates=act, row_hits=hit, row_conflicts=conf, refreshes=ref,
                           mean_read_latency_ns=round(ls / rd / 1000, 1) if rd else None,
                           max_read_latency_ns=round(lm / 1000, 1), reads_per_pc_min=rmin, reads_per_pc_max=rmax,
                           dram_check=dict(pre=pre, refpb=refc, act=actc, rd=rdc, wr=wrc, violations=viol,
                                           tRREFD_not_modelled=rrefd, refpb_round_bad=rbad,
                                           refpb_gap_max_ns=round(gap / 1000, 1))))
    sectors, last = int(m.group(2)), int(m.group(3))
    first = min((s["first_out"] for s in stacks if s["first_out"] >= 0), default=-1)
    row = dict(pass_=True, blocks=[int(x) for x in m.group(1).split(",")], sectors=sectors, bytes=32 * sectors,
               cycles=last, first_out=first, seconds=last * CLK_PS * 1e-12, stacks=stacks)
    viols = [dict(t_ps=int(v[0]), pc=int(v[1]), bank=int(v[2]), rule=v[3].strip()) for v in DVL.findall(stdout)]
    row["dram_check"] = dict(violations=sum(s["dram_check"]["violations"] for s in stacks),
                             tRREFD_not_modelled=sum(s["dram_check"]["tRREFD_not_modelled"] for s in stacks),
                             refpb=sum(s["dram_check"]["refpb"] for s in stacks),
                             refpb_gap_max_ns=max(s["dram_check"]["refpb_gap_max_ns"] for s in stacks),
                             first_violations=viols[:8])
    if last > 0:
        row["achieved_TBps"] = round(32 * sectors / row["seconds"] / 1e12, 4)
        row["fraction_of_peak"] = round(sectors / last / PEAK_SECTORS_PER_CYCLE_RANK, 4)
        if last > first >= 0:
            row["fraction_of_peak_first_to_last_beat"] = round(sectors / (last - first) / PEAK_SECTORS_PER_CYCLE_RANK, 4)
        rd = sum(s["hbm_reads"] for s in stacks)
        row["activates_per_sector"] = round(sum(s["activates"] for s in stacks) / rd, 4) if rd else None
    w = WRL.search(stdout)
    if w:
        row["write"] = dict(zip(("commands", "keys", "migrations", "copied_sectors", "cycles"), map(int, w.groups())))
    if extra:
        row.update(extra)
    return row


def run_bin(binary, pfx, args=(), old=False, extra=None):
    t0 = time.time()
    r = subprocess.run([str(binary), f"+PFX={pfx}", *args], capture_output=True, text=True)
    row = parse(r.stdout, r.returncode, old, extra)
    row["wall_s"] = round(time.time() - t0, 1)
    return row


def functional_cases(rng):
    """Local block lists of a 65,536-key stack quarter (0 .. 8,191)."""
    cases = {"edges": [sorted(set(list(range(0, 16)) + [126, 127, 128, 129, 1023, 1024, 8190, 8191])), [], [4000],
                       sorted(int(x) for x in rng.choice(8192, 300, replace=False))],
             "full_list_2048": [sorted(int(x) for x in rng.choice(8192, 2048, replace=False)), [7], [], [8191]],
             "dense_run_2048": [list(range(3000, 5048)), list(range(0, 8192, 4)), [0], list(range(8192 - 64, 8192))],
             "same_channel_bank": [list(range(5, 8192, 1024)), list(range(0, 8192, 32))[:200],
                                   list(range(3, 2048, 128)), list(range(17, 8192, 512))]}
    for i in range(3):
        cases[f"random{i}"] = [sorted(int(x) for x in rng.choice(8192, int(rng.integers(0, 600)), replace=False))
                               for _ in range(STACKS)]
    return cases


def cmd_trace(a=None):
    c = (ROOT / "rtl/test/ot_hdc_v41x_idx_hbm_trace.sv").read_text().split("\n")
    o = [l[len("// TRACE-ORIG "):] if l.startswith("// TRACE-ORIG ") else l for l in c
         if l.startswith("// TRACE-ORIG ") or "// TRACE" not in l]
    ok = "\n".join(o) == (ROOT / V / "ot_hdc_v41x_idx_hbm.sv").read_text()
    print("trace copy minus TRACE lines == ot_hdc_v41x_idx_hbm.sv:", ok)
    return ok


def cmd_gather(a):
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert cmd_trace()
    lay = layout_check()
    _, blk = cand_blocks(a.gold)
    rng = np.random.default_rng(20261004)
    funcs = functional_cases(rng)
    newb = build_new(out / "obj_new", dict(CLK_PS=CLK_PS))
    jobs = []
    for p in PLACE:
        for r in range(TP):
            cmds = [(0, 0, *PLACE[p](q), CBLK, q * PER_STACK) for q in range(STACKS)]
            jobs.append((f"real_rank{r}_{p}", cmds, rank_lists(blk, r), dict(kind="real", rank=r, placement=p)))
        for f, lists in funcs.items():
            cmds = [(0, 0, *PLACE[p](q), CBLK, q * PER_STACK) for q in range(STACKS)]
            jobs.append((f"func_{f}_{p}", cmds, lists, dict(kind="functional", placement=p)))
        for tag, nb in (("scan_L20", BLK_STACK), ("scan_L2", BLK_STACK // 2)):
            cmds = [(1, nb, *PLACE[p](q), CBLK, q * PER_STACK) for q in range(STACKS)]
            jobs.append((f"{tag}_{p}", cmds, [None] * 4, dict(kind="scan", placement=p, keys_per_rank=4 * 8 * nb)))

    def one(j):
        name, cmds, lists, extra = j
        write_inputs(out / name, cmds, lists)
        row = run_bin(newb, out / name, extra=extra)
        if extra["kind"] == "real":
            row["bound"] = bounds(lists, extra["placement"])
        print(name, json.dumps({k: row.get(k) for k in ("pass_", "cycles", "achieved_TBps", "fraction_of_peak",
                                                        "activates_per_sector")}),
              json.dumps(row.get("dram_check", {}).get("violations")), flush=True)
        return name, row
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        runs = dict(ex.map(one, jobs))
    # the as-built gather on the same lists, same traced controller (comparison of timing and DRAM legality)
    old = {}
    for p, prm in (("p1", dict(BASE=0, BSTEP=1000, OSTEP=136)), ("p2", dict(BASE=123, BSTEP=777, OSTEP=8))):
        ob = build_old(out / f"obj_old_{p}", dict(prm, CLK_PS=CLK_PS))
        for r in range(TP):
            name = f"asbuilt_rank{r}_{p}"
            for q, l in enumerate(rank_lists(blk, r)):
                Path(f"{out / name}.s{q}").write_text(f"{len(l)}\n" + "".join(f"{x:x}\n" for x in l))
            old[name] = run_bin(ob, out / name, old=True, extra=dict(kind="asbuilt", rank=r, placement=p))
            print(name, old[name].get("cycles"), old[name].get("dram_check", {}).get("violations"), flush=True)
    real = {k: v for k, v in runs.items() if v.get("kind") == "real"}
    worst = max(real, key=lambda k: real[k].get("cycles", 1 << 30))
    oworst = max(old, key=lambda k: old[k].get("cycles", 1 << 30))
    scans = {k: v for k, v in runs.items() if v.get("kind") == "scan"}
    srcs = {p: sha(ROOT / p) for p in KGR_SRC + KGR_INC + OLD_SRC + [V + "ot_hdc_v41x_idx_hbm.sv", "tools/dsrom_idxkey_layout.py"]}
    ver = subprocess.run([verilator(), "--version"], capture_output=True, text=True).stdout.strip()
    w = runs[worst]
    rec = dict(schema="opentallas.dsrom-idxkey-layout.gather.v1", simulator=ver, source_sha256=srcs,
               golden_candidates=dict(npz=sha(a.gold / "ctx1048576_cand.npz"), blocks=int(len(blk)), keys=int(8 * len(blk))),
               clock_ps=CLK_PS, peak_TBps_rank=PEAK_TBPS_RANK, hbm=HBM, ring=dict(C_keys=C_RING, blocks=CBLK),
               layout=dict(check=lay, capacity=dict(
                   bytes_per_key_packed=68, bytes_per_key_row_layout=128,
                   note="a block (8 keys, 544 B) owns a 1-KB row: 47% of each row unused; for the four re-index "
                        "layers at 1M (4 x 1,048,576 keys) 512 MiB instead of 272 MiB, +15 MiB a stack (16 stacks)")),
               worst_rank=dict(name=worst, cycles=w["cycles"], sectors=w["sectors"], bytes=w["bytes"],
                               achieved_TBps=w["achieved_TBps"], fraction_of_peak=w["fraction_of_peak"],
                               fraction_of_peak_first_to_last_beat=w.get("fraction_of_peak_first_to_last_beat"),
                               activates_per_sector=w["activates_per_sector"], bound=w["bound"]),
               asbuilt_worst_rank=dict(name=oworst, cycles=old[oworst]["cycles"],
                                       achieved_TBps=old[oworst]["achieved_TBps"],
                                       fraction_of_peak=old[oworst]["fraction_of_peak"],
                                       activates_per_sector=old[oworst]["activates_per_sector"]),
               balance_bounds_any_static_map=balance_bounds(blk),
               scans={k: dict(cycles=v.get("cycles"), sectors=v.get("sectors"), keys_per_rank=v.get("keys_per_rank"),
                              achieved_TBps=v.get("achieved_TBps"), fraction_of_peak=v.get("fraction_of_peak"),
                              activates_per_sector=v.get("activates_per_sector"),
                              dram_violations=v.get("dram_check", {}).get("violations")) for k, v in scans.items()},
               runs=runs, asbuilt_runs=old,
               status="pass" if all(v.get("pass_") for v in list(runs.values()) + list(old.values())) else "fail")
    (out / "gather.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("gather", rec["status"], json.dumps(rec["worst_rank"]), json.dumps(rec["scans"]), flush=True)


# ------------------------------------------------------------------------------------------------ round trip
def rt_plan(blk, r, extras=False):
    """Writer commands and reader lists of rank r's 1M state (rank-local positions 0 .. 262,143)."""
    loc = set(int(x - r * PER_RANK // 8) for x in blk if r * PER_RANK // 8 <= x < (r + 1) * PER_RANK // 8)
    wblk = set()
    for x in loc:
        for d in (-1, 0, 1):
            if 0 <= x + d < PER_RANK // 8:
                wblk.add(x + d)
    step = (r == TP - 1)               # the newest position 1,048,575 is rank 3's local 262,143
    mig = []
    if step:
        qs_old = ((PER_RANK - 1) >> 5) << 3
        mig = [(q * qs_old + 8 * g) // 8 for q in range(1, 4) for g in range(q)]
        wblk |= set(mig) | {(PER_RANK - 1) // 8}
    n_place = PER_RANK - 1 if step else PER_RANK
    wr = [(1, n_place, 8 * b + k) for b in sorted(wblk) for k in range(8) if not (step and 8 * b + k == PER_RANK - 1)]
    if step:
        wr.append((0, PER_RANK - 1, 0))
    rd = loc | ((set(mig) | {(PER_RANK - 1) // 8}) if extras else set())
    lists = [sorted(x - q * BLK_STACK for x in rd if q * BLK_STACK <= x < (q + 1) * BLK_STACK) for q in range(STACKS)]
    cmds = [(0, 0, 0, ((q * PER_STACK) % C_RING) // 8, CBLK, q * PER_STACK) for q in range(STACKS)]
    return cmds, lists, wr, dict(written_blocks=len(wblk), migrated_blocks=mig, step=step)


def cmd_rt(a):
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    _, blk = cand_blocks(a.gold)
    b = build_new(out / "obj_rt", dict(CLK_PS=CLK_PS, RT=1))
    jobs = [(f"rt_rank{r}", r, False) for r in range(TP)] + [("rt_rank3_migration", 3, True)]

    def one(j):
        name, r, ex = j
        cmds, lists, wr, meta = rt_plan(blk, r, ex)
        write_inputs(out / name, cmds, lists, wr)
        row = run_bin(b, out / name, [f"+RANK={r}"], extra=dict(rank=r, **meta))
        row["stream_sha256"] = sha(f"{out / name}.out") if row["pass_"] else None
        print(name, row["pass_"], row.get("cycles"), row.get("write"), row.get("dram_check", {}).get("violations"), flush=True)
        return name, row
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        runs = dict(ex.map(one, jobs))
    srcs = {p: sha(ROOT / p) for p in KGR_SRC + KGR_INC + ["tools/dsrom_idxkey_layout.py"]}
    rec = dict(schema="opentallas.dsrom-idxkey-layout.roundtrip.v1", source_sha256=srcs,
               key="544-bit hash of (rank, rank-local position) written by ot_hdc_v41x_idx_ring_kwr_row, read back by "
                   "ot_hdc_v41x_idx_kgrow through the controller's backing array; every key of every beat compared",
               runs=runs, status="pass" if all(v["pass_"] for v in runs.values()) else "fail")
    (out / "roundtrip.json").write_text(json.dumps(rec, indent=1, default=int) + "\n")


# ------------------------------------------------------------------------------------------------ select
def beats_from_stream(path: Path, stack: int, qbase_global: int, bits_of):
    beats = []
    for line in Path(path).read_text().splitlines():
        s, cyc, kv, b0, b1 = line.split()
        if int(s) != stack:
            continue
        lanes = []
        for bi, bb in enumerate((int(b0), int(b1))):
            for k in range(8):
                if bb < 0:
                    lanes.append(None)
                else:
                    p = qbase_global + 8 * bb + k
                    lanes.append((int(bits_of(p)), int(p)))
        beats.append(lanes)
    return beats or [[None] * 16]


def cmd_select(a):
    import rtl_hdc_v41x_sel_campaign as S
    import hdc_golden_v41 as G
    import dsrom_1m_measure as M
    import dsrom_reindex_candidates as RC
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    W, IW, K = 16, 20, 512
    cand, _ = cand_blocks(a.gold)
    rtd = Path(a.rt).resolve()
    rt = json.loads((rtd / "roundtrip.json").read_text())
    assert rt["status"] == "pass"
    results = {}
    for L in [int(x) for x in a.layers.split(",")]:
        z, j = M.gold_layer(a.gold, L)
        s = z[f"L{L}.index_scores"]
        assert len(s) == CTX and (np.isfinite(s) == cand).all()
        golden_sel = sorted(int(x) for x in j["ctx_out"]["sel"])
        bits_all = np.where(cand, RC.bf16_bits(np.where(cand, s, 0.0)), NINF).astype(np.int64)
        segs, labels, locals_ = [], [], []
        for r in range(TP):
            lo = r * PER_RANK
            pos = np.arange(lo, lo + PER_RANK)
            cuts = [q * PER_STACK for q in range(STACKS + 1)]
            exps, lsel = RC.expect(bits_all[lo:lo + PER_RANK], pos, cuts, K)
            locals_.append(lsel)
            stream = rtd / f"rt_rank{r}.out"
            beats = [beats_from_stream(stream, q, lo + q * PER_STACK, lambda p: bits_all[p]) for q in range(STACKS)]
            segs.append((beats, K, exps, {"n": int(cand[lo:lo + PER_RANK].sum())}))
            labels.append(f"L{L}_rank{r}")
        cfg = S.run_config(f"L{L}_rowgather", STACKS, W, IW, K, 8, segs, labels, out, runs=((0, 0, 1),))
        cb = np.concatenate([bits_all[np.asarray(x)] for x in locals_])
        cp = np.concatenate([np.asarray(x) for x in locals_])
        cuts = np.cumsum([0] + [len(x) for x in locals_]).tolist()
        segx, gsel = M._segment(S, G, cb, cp, cuts, K, W)
        cfgx = S.run_config(f"L{L}_final", STACKS, W, IW, K, 6, [segx], [f"L{L}_final"], out, runs=((0, 0, 1),))
        res = dict(layer=L, gather=dict(pass_=cfg["pass"], beats=cfg["beats"], elements=cfg["elements"],
                                        runs=[{k: v for k, v in rr.items() if k != "log"} for rr in cfg["runs"]],
                                        cost_cycles_convention=RC.seg_cost(cfg["runs"][0]) if cfg["pass"] else None),
                   final=dict(pass_=cfgx["pass"], runs=[{k: v for k, v in rr.items() if k != "log"} for rr in cfgx["runs"]]),
                   global_selection_equals_golden_layer=sorted(gsel) == golden_sel,
                   golden_selection_sha256=hashlib.sha256(json.dumps(golden_sel).encode()).hexdigest(),
                   rtl_streams={f"rank{r}": rt["runs"][f"rt_rank{r}"]["stream_sha256"] for r in range(TP)})
        res["pass_"] = res["gather"]["pass_"] and res["final"]["pass_"] and res["global_selection_equals_golden_layer"]
        results[f"L{L}"] = res
        print(f"L{L}", res["pass_"], res["gather"]["cost_cycles_convention"], flush=True)
    srcs = {p: sha(ROOT / p) for p in ["tools/dsrom_idxkey_layout.py", "tools/rtl_hdc_v41x_sel_campaign.py",
                                        "tools/hdc_golden_v41.py", "tools/dsrom_1m_measure.py",
                                        "tools/dsrom_reindex_candidates.py"]}
    pins = {f"L{L}": dict(npz=sha(a.gold / f"ctx1048576_L{L:02d}.npz")) for L in [int(x) for x in a.layers.split(",")]}
    pins["cand"] = sha(a.gold / "ctx1048576_cand.npz")
    rec = dict(schema="opentallas.dsrom-idxkey-layout.select.v1", source_sha256=srcs, golden_shards=pins,
               layers=results, status="pass" if all(r["pass_"] for r in results.values()) else "fail")
    (out / "select.json").write_text(json.dumps(rec, indent=1) + "\n")


def cmd_screen(a):
    w = Path(a.work)
    r = json.loads((w / "screen.json").read_text())
    ok = r["ss_setup_wns_ps"] is not None and r["ss_setup_wns_ps"] >= 0 and r["ff_hold_wns_ps"] is not None \
        and r["ff_hold_wns_ps"] >= 0
    rec = dict(schema="opentallas.dsrom-idxkey-layout.screen.v1", period_ps=833.0, setup_uncertainty_ps=60,
               hold_uncertainty_ps=25,
               basis="pre-layout: ORFS yosys/abc at CORNER=WC (ADDER_MAP_FILE off), OpenSTA ASAP7 RVT SS (setup) and FF "
                     "(hold) libs, ideal clock, inputs/outputs false-pathed; the data banks (ot_hdc_v41x_idx_kgrdata) "
                     "and the list SRAM outside the screened control, as for ot_hdc_v41x_idx_kgctl",
               source_sha256={p: sha(ROOT / p) for p in (V + "ot_hdc_v41x_idx_kgrow.sv", "tools/dsrom_reindex_screen.py")},
               runs={"kgrctl": r}, status="pass" if ok else "fail")
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: r.get(k) for k in ("ss_setup_wns_ps", "ff_hold_wns_ps")}), rec["status"])


def cmd_compose(a):
    M1 = ROOT / "results/rtl/dsrom_1m_measured_20261004"
    RCD = ROOT / "results/rtl/dsrom_reindex_candidates_20261004"
    new = json.loads(Path(a.select).read_text())
    old = json.loads((RCD / "select.json").read_text())
    assert new["status"] == "pass" and old["status"] == "pass"
    merged = dict(status="pass", layers={})
    for tag, r in new["layers"].items():
        merged["layers"][tag] = dict(drop_dense=old["layers"][tag]["drop_dense"], gather=r["gather"], final=r["final"])
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    msel = out.parent / "select_for_compose.json"
    msel.write_text(json.dumps(merged, indent=1) + "\n")
    cmd = [sys.executable, str(ROOT / "tools/dsrom_1m_measure.py"), "compose", "--reader", str(M1 / "reader.json"),
           "--select", str(M1 / "select.json"), str(M1 / "select_l24_full.json"),
           "--ckv", str(M1 / "ckv_lat100.json"), str(M1 / "ckv_lat259.json"),
           "--gather", str(Path(a.gather).resolve()), "--reindex-select", str(msel), "--out", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    c = json.loads(out.read_text())
    prev = json.loads((RCD / "composition.json").read_text())
    k = "candidate_gather.lat259"
    c["idxkey_layout"] = dict(
        basis="candidate_gather variant: re-index index read = the ROW-LAYOUT gather (worst rank of the real 1M "
              "lists, both placements) and the select on its RTL beat stream; previous = the super-block gather",
        previous=dict(AR_tok_s=prev["variants"][k]["AR_tok_s"], MTP_fused_tok_s=prev["variants"][k]["MTP_tok_s"]["fused_us"],
                      AR_us=prev["variants"][k]["AR_us"], II_us=prev["variants"][k]["II_us"]),
        row_layout=dict(AR_tok_s=c["variants"][k]["AR_tok_s"], MTP_fused_tok_s=c["variants"][k]["MTP_tok_s"]["fused_us"],
                        AR_us=c["variants"][k]["AR_us"], II_us=c["variants"][k]["II_us"]),
        AR_gain_pct=round(100 * (c["variants"][k]["AR_tok_s"] / prev["variants"][k]["AR_tok_s"] - 1), 3),
        MTP_gain_pct=round(100 * (c["variants"][k]["MTP_tok_s"]["fused_us"] / prev["variants"][k]["MTP_tok_s"]["fused_us"] - 1), 3))
    out.write_text(json.dumps(c, indent=1, default=str) + "\n")
    print(json.dumps(c["idxkey_layout"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("trace")
    g = sub.add_parser("gather")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    g.add_argument("--jobs", type=int, default=8)
    t = sub.add_parser("rt")
    t.add_argument("--out", type=Path, required=True)
    t.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    t.add_argument("--jobs", type=int, default=5)
    s = sub.add_parser("select")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--rt", required=True)
    s.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    s.add_argument("--layers", default="24,28")
    c = sub.add_parser("screen")
    c.add_argument("--work", required=True)
    c.add_argument("--out", required=True)
    m = sub.add_parser("compose")
    m.add_argument("--gather", required=True)
    m.add_argument("--select", required=True)
    m.add_argument("--out", required=True)
    a = ap.parse_args()
    dict(compose=cmd_compose, trace=cmd_trace, gather=cmd_gather, rt=cmd_rt, select=cmd_select, screen=cmd_screen)[a.cmd](a)


if __name__ == "__main__":
    main()
