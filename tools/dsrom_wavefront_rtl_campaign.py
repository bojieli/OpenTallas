#!/usr/bin/env python3
"""DS-ROM wavefront verify, measured in RTL on the reduced V4.1 package array.

The reduced DeepSeek-V4.1-Flash vehicle (40 layers, dim 160, vocab 4040) runs on a
point-to-point ring of BODY packages (contiguous layer ranges, the last one with the
whole lm_head), each an all-unit ot_hdc_core_v41x with its KV in attached HBM
(kv_prefetch + shared K stacks) and the pooled index keys in HBM -- the
tools/rtl_hdc_v41x_array_campaign.py all-unit KV-HBM vehicle -- under the successor
bench rtl/test/dsrom_wavefront/tb_dsrom_wavefront_array.sv and the successor
controller rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv (WAVE parameter, default 0).

Two configurations of the same build inputs:
  ar    WAVE=0: the clean greedy sequence, one position in flight (autoregressive
        reference: per-token latency and per-package job times).
  wave  WAVE=1, WIN=6: positions 0 .. P-1 are the prompt; the first draft block is
        the golden continuation with ONE corrupted draft (position REJ); the
        controller issues every known-token position back to back (same user,
        one stage apart), verifies each draft against the returned argmax,
        rejects the corrupted one (squashing the positions behind it), re-issues
        it with the argmax, continues with the second draft block (the clean
        continuation) and finally autoregressively.

Checks (bench, bit for bit): every committed token against the clean golden; every
lm_head job's 4,040 logits against the golden of the context that job saw (the
corrupted first pass for squashed positions, the clean sequence otherwise); the
final KV (shadow and HBM sectors) and persistent vector-memory segment of every
package against the ISA pipeline after the clean sequence (the dead-row invariant:
every row a squashed position wrote is rewritten before it is read).  The ISA
replay of the worst-case wavefront job order is checked against the same final
state before any RTL runs.

Usage:
  python3 tools/dsrom_wavefront_rtl_campaign.py prepare --scratch D      # local (golden + ISA + images)
  python3 tools/dsrom_wavefront_rtl_campaign.py run --scratch D --config wave|ar   # build + simulate
  python3 tools/dsrom_wavefront_rtl_campaign.py record --scratch D --output F       # parse runs -> record
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

for flag in ("--all-unit", "--kv-hbm"):          # the array campaign reads these at import
    if flag not in sys.argv:
        sys.argv.append(flag)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_array_campaign as AC  # noqa: E402
import numpy as np  # noqa: E402

A, P, I, V, core, ximg, G = AC.A, AC.P, AC.I, AC.V, AC.core, AC.ximg, AC.A.G

TB = ROOT / "rtl/test/dsrom_wavefront/tb_dsrom_wavefront_array.sv"
HARNESS = ROOT / "rtl/test/dsrom_wavefront/dsrom_wavefront_harness.cpp"
CTRL = ROOT / "rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv"
BODY = 5            # packages: 8 layers each; package 2 holds layers 16..23 (the L20 producer/scan layer)
PLEN = 2            # prompt tokens
STEPS = 12          # committed positions 0 .. 11
REJ = 4             # the corrupted draft's position (first block: positions 1 .. 6)
BLK0_END = 7        # block 0 known positions 0 .. 6 (verify block: positions 1 .. 6)
BLK1_END = 10       # block 1 known positions .. 9 (after the rejection: REJ re-issued + drafts REJ+1 .. 9)
AR_STEPS = 4        # the autoregressive reference: positions 0 .. 3
WIN = 6
NBLK, KMAX, SMAX = 4, 16, 16
CONFIGS = {"wave": dict(wave=1, steps=STEPS), "ar": dict(wave=0, steps=AR_STEPS)}


def sources():
    return [*core.rtl_sources(True), *AC.BENCH_AUX_RTL, *AC.KV_HBM_RTL, AC.LINK, AC.ROUTER, CTRL,
            TB, HARNESS, core.SVH, core.VLT, *core.TOOLS, ROOT / "tools/hdc_program_v41_array.py",
            ROOT / "tools/rtl_hdc_v41x_array_campaign.py", Path(__file__)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def golden(model, tokens, n, greedy_from):
    """Teacher-forced decode of positions 0 .. n-1; from position greedy_from-1 on the
    next input is the argmax (greedy), before that tokens[p].  Returns inputs, argmax, logit bits."""
    st = model.new_state()
    seq = list(tokens[:greedy_from])
    steps = []
    for p in range(n):
        if p >= len(seq):
            seq.append(steps[-1]["argmax"])
        lg = model.decode_token(seq[p], p, st)
        a = int(np.argmax(lg))
        steps.append(dict(pos=p, input=int(seq[p]), argmax=a, logits=[int(x) for x in G.bits(lg)]))
    return steps


def isa_replay(plan, progs, base, jobs):
    """ISA pipeline over a job order [(token, pos)]; the Engram history is the
    committed prefix (truncated to the position, as the bench's position ring)."""
    pipe = A.Pipeline(plan, progs, base)
    out = []
    for tok, pos in jobs:
        for mc in pipe.pk:
            mc.tokens = mc.tokens[:pos]
        a, vb, lg = pipe.step(tok, pos)
        out.append((a, [int(x) for x in G.bits(lg)]))
    state = [(mc.kv.copy(), mc.vm[plan.pb:plan.pb + A.PS].copy()) for mc in pipe.pk]
    return out, state


def prepare(scratch: Path):
    t0 = time.time()
    scratch.mkdir(parents=True, exist_ok=True)
    model = V.Model()
    lay = P.Layout(model)
    A.place_head_parts(lay)
    roms = scratch / "roms"
    if not (roms / "hbm_q.hex").exists():
        A.write_roms(roms, lay)
        ximg.write_banked(roms / "hbank.hex", ximg.hbank_image(lay, 8), 32, 8)
        ximg.write(roms, lay, hhw=8, mg=8)
        sectors, _ = P.qe_hbm_image(lay)
        (roms / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    plan = A.Plan(lay, A.split(model, BODY), 0, False, "relay")
    progs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    vocab = plan.vocab

    prompt = A.prompts(PLEN)[0]
    gcache = scratch / "golden.json"
    if gcache.exists():
        gold = json.loads(gcache.read_text())
    else:
        clean = golden(model, prompt, STEPS, PLEN)
        seq = [s["input"] for s in clean]
        bad = (seq[REJ] + 1) % vocab
        seq_c = seq[:BLK0_END]
        seq_c[REJ] = bad
        corrupt = golden(model, seq_c, BLK0_END, BLK0_END)
        gold = dict(prompt=prompt, clean=clean, seq=seq, seq_c=seq_c, corrupt=corrupt)
        gcache.write_text(json.dumps(gold))
    clean, seq, seq_c, corrupt = gold["clean"], gold["seq"], gold["seq_c"], gold["corrupt"]
    assert seq_c[REJ] != clean[REJ - 1]["argmax"], "the corrupted draft must be rejected"
    # the first pass agrees with the clean sequence before the corrupted position
    assert all(corrupt[p]["logits"] == clean[p]["logits"] for p in range(REJ))

    # ISA: the clean sequence (expected final state) and the worst-case wavefront job order
    isa = {}
    for name, n in (("wave", STEPS), ("ar", AR_STEPS)):
        out, state = isa_replay(plan, progs, base, [(seq[p], p) for p in range(n)])
        isa[name] = dict(state=state, exact=all(o[1] == clean[p]["logits"] for p, o in enumerate(out)))
    jobs = [(seq_c[p], p) for p in range(BLK0_END)] + [(seq[p], p) for p in range(REJ, STEPS)]
    out, wstate = isa_replay(plan, progs, base, jobs)
    first = all(out[p][1] == corrupt[p]["logits"] for p in range(BLK0_END))
    second = all(out[BLK0_END + i][1] == clean[p]["logits"] for i, p in enumerate(range(REJ, STEPS)))
    same_state = all(np.array_equal(G.bits(a[0]), G.bits(b[0])) and np.array_equal(G.bits(a[1]), G.bits(b[1]))
                     for a, b in zip(wstate, isa["wave"]["state"]))
    isa_rec = dict(clean_sequence_exact=isa["wave"]["exact"], ar_sequence_exact=isa["ar"]["exact"],
                   wavefront_order_first_pass_exact_vs_corrupted_golden=first,
                   wavefront_order_reissue_exact_vs_clean_golden=second,
                   wavefront_order_final_state_equals_clean=same_state,
                   worst_case_job_order=[p for _, p in jobs])
    if not (isa_rec["clean_sequence_exact"] and isa_rec["ar_sequence_exact"] and first and second and same_state):
        raise RuntimeError(f"ISA replay not exact: {isa_rec}")

    for name, c in CONFIGS.items():
        img = scratch / f"cfg_{name}"
        img.mkdir(parents=True, exist_ok=True)
        for k, prog in enumerate(progs):
            words = [I.encode(**{a: v for a, v in f.items() if not a.startswith("_")}) for f in prog]
            (img / f"prog_stage{k:02d}.hex").write_text(P.hexwords(words, I.INSTR_BITS))
        sectors, firsts = P.qe_hbm_image(lay)
        for k, prog in enumerate(progs):
            ents = P.qe_fetch_list(lay, prog, firsts)
            (img / f"qlist_stage{k:02d}.hex").write_text(P.hexwords(P.encode_list(ents), P.LIST_BITS))
        known = [0] * (NBLK * KMAX)
        if c["wave"]:
            for p in range(BLK0_END):
                known[p] = (1 << 16) | seq_c[p]
            for p in range(BLK1_END):
                known[KMAX + p] = (1 << 16) | seq[p]
        else:
            for p in range(PLEN):
                known[p] = (1 << 16) | seq[p]
        (img / "known.hex").write_text(P.hexwords(known, 17))
        steps = c["steps"]
        (img / "expect_tokens.hex").write_text(P.hexwords(
            [clean[p]["argmax"] if p < steps else 0 for p in range(SMAX)], 16))
        pad = [0] * vocab
        v0 = [corrupt[p]["logits"] if (c["wave"] and p < BLK0_END) else (clean[p]["logits"] if p < steps else pad)
              for p in range(SMAX)]
        v1 = [clean[p]["logits"] if p < steps else pad for p in range(SMAX)]
        (img / "expect_logits.hex").write_text(P.hexwords([x for row in v0 + v1 for x in row], 32))
        for k in range(plan.n):
            kv, vm = isa[name]["state"][k]
            (img / f"expect_kv{k:02d}_0.hex").write_text(P.hexwords(G.bits(kv), 32))
            (img / f"expect_vm{k:02d}_0.hex").write_text(P.hexwords(G.bits(vm), 32))
    svh = AC.config_svh(plan, lay, "p2p").replace("NPR = 2", "NPR = 1")
    assert "NPR = 1" in svh
    (scratch / "array_cfg.svh").write_text(svh)
    roles = [plan.role(k) for k in range(plan.n)]
    prep = dict(
        schema="opentallas.rtl.dsrom_wavefront_prepare.v1",
        vehicle="deepseek-v4.1-flash-reduced-v2 (40 layers, dim 160, vocab 4040)",
        body_packages=BODY, layers_per_package=plan.body, hop_words=[r["txw"] for r in roles],
        engram_hashing_packages=[k for k in range(plan.n) if plan.ehash(k)],
        prompt=prompt, clean_sequence=seq[:STEPS], first_block_tokens=seq_c,
        corrupted_position=REJ, corrupted_token=seq_c[REJ], clean_token_at_rejection=seq[REJ],
        prompt_len=PLEN, steps=STEPS, ar_steps=AR_STEPS, win=WIN,
        blocks=dict(block0_known_positions=[0, BLK0_END - 1], block1_known_positions=[0, BLK1_END - 1]),
        isa=isa_rec, prepare_seconds=round(time.time() - t0, 1),
        input_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources()})
    (scratch / "prepare.json").write_text(json.dumps(prep, indent=1) + "\n")
    print(json.dumps(isa_rec))
    return prep


def build(scratch: Path, wave: int) -> Path:
    threads = int(os.environ.get("OT_WF_THREADS", "0"))     # Verilator --threads (0: single-threaded)
    stage = os.environ.get("OT_WF_STAGE", "0") == "1"
    obj = scratch / (f"obj_stage_w{wave}" if stage else f"obj_w{wave}" + (f"_t{threads}" if threads else ""))
    obj.mkdir(parents=True, exist_ok=True)
    (obj / "v41_array_cfg.svh").write_text((scratch / "array_cfg.svh").read_text())
    cmd = ["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD",
           "-Wno-MODDUP", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT", "-Wno-PINMISSING",
           *(["--threads", str(threads)] if threads else []),
           "--top-module", "tb_dsrom_wavefront_array", "-GUSERS=1", "-GSTALL=0", f"-GWAVE={wave}", f"-GWIN={WIN}", f"-GSTAGE_BENCH={int(stage)}",
           "-Mdir", str(obj), f"-I{obj}", f"-I{core.SVH.parent}", str(core.VLT),
           f"+define+HDC_SW={I.SU_LANES}",
           *[f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}" for x in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
           "+define+HDC_W_HBM=1", "+define+HDC_KV_HBM=1",
           *map(str, core.rtl_sources(True)), *map(str, AC.BENCH_AUX_RTL), *map(str, AC.KV_HBM_RTL),
           str(AC.LINK), str(AC.ROUTER), str(CTRL), str(TB), str(HARNESS),
           "-CFLAGS", "-O1", "-MAKEFLAGS", os.environ.get("OT_WF_MAKEFLAGS", "OPT_FAST=-O1 OPT_GLOBAL=-O1"),
           "-j", os.environ.get("OT_WF_JOBS", "16")]
    (obj / "build_cmd.json").write_text(json.dumps(cmd))
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (obj / "build.log").write_text(r.stdout[-200000:] + r.stderr[-200000:])
    if r.returncode:
        raise RuntimeError(f"build failed, see {obj / 'build.log'}\n{r.stderr[-3000:]}")
    (obj / "build_seconds.txt").write_text(f"{time.time() - t0:.1f}\n")
    return obj / "Vtb_dsrom_wavefront_array"


def run(scratch: Path, name: str):
    c = CONFIGS[name]
    exe = build(scratch, c["wave"])
    tag = os.environ.get("OT_WF_TAG", "")
    name_t = name + tag
    log = scratch / f"out_{name_t}.txt"
    cmd = [str(exe), f"+DIR={scratch / f'cfg_{name}'}", f"+ROMS={scratch / 'roms'}", "+NUSERS=1",
           f"+NPROMPT={PLEN}", f"+NGEN={c['steps'] - PLEN + 1}", "+LINK_CH=60", "+HB=1000000"]
    (scratch / f"run_{name_t}.json").write_text(json.dumps(dict(cmd=cmd, start=time.time())))
    t0 = time.time()
    with open(log, "w") as fh:
        rc = subprocess.run(["stdbuf", "-oL", *cmd], stdout=fh, stderr=subprocess.STDOUT).returncode
    (scratch / f"run_{name_t}.rc").write_text(f"{rc} {time.time() - t0:.1f}\n")
    return rc


JOB = re.compile(r"JOB node=(\d+) user=(\d+) pos=(\d+) hdr=(\d+) pay=(\d+) cstart=(\d+) start=(\d+) done=(\d+)")
WF = re.compile(r"WF cycle=(\d+) issue=(\d) reject=(\d) squash=(\d)")
VIS = re.compile(r"VIS kind=(\w+) pkg=(\d+) stack=(\d+) job=(\d+) words=(\d+) wlast=(\d+) vis=(\d+) lat=(\d+) "
                 r"need=(-?\d+) pending=(\d+)")


def analyse(out: str, name: str):
    c = CONFIGS[name]
    rec = dict(config=name, wave=c["wave"], win=WIN if c["wave"] else 1)
    try:
        rec["parsed"] = AC.parse(out, 1, c["steps"], c["steps"] - PLEN + 1)
    except Exception as e:  # noqa: BLE001
        rec["parse_error"] = str(e)
        rec["tail"] = out[-4000:]
        return rec
    jobs = [dict(zip(("node", "user", "pos", "hdr", "pay", "cstart", "start", "done"), map(int, m)))
            for m in JOB.findall(out)]
    nodes = sorted({j["node"] for j in jobs})
    per = {}
    for n in nodes:
        js = [j for j in jobs if j["node"] == n]
        for i, j in enumerate(js):
            j["seq"] = i + 1
            j["busy"] = j["done"] - j["start"]
            j["entry_gap"] = j["start"] - js[i - 1]["start"] if i else None
            j["wait_after_prev_done"] = j["start"] - js[i - 1]["done"] if i else None
        per[n] = js
    # window of a job at node n: its HIDDEN header at n to its header at n+1 (or its done at the last)
    for n in nodes:
        for i, j in enumerate(per[n]):
            if n + 1 in per and i < len(per[n + 1]):
                j["window"] = per[n + 1][i]["hdr"] - j["hdr"]
            else:
                j["window"] = j["done"] - j["hdr"]
    rec["jobs"] = per
    wf = [dict(zip(("cycle", "issue", "reject", "squash"), map(int, m))) for m in WF.findall(out)]
    rec["wf_events"] = wf
    vis = [dict(zip(("kind", "pkg", "stack", "job", "words", "wlast", "vis", "lat", "need", "pending"),
                    [m[0], *map(int, m[1:])])) for m in VIS.findall(out)]
    agg = {}
    for v in vis:
        key = (v["kind"], v["pkg"], v["job"])
        a = agg.setdefault(key, dict(kind=v["kind"], pkg=v["pkg"], job=v["job"], words=0, wlast=0, vis=0,
                                     lat=0, need=None, pending=0))
        a["words"] += v["words"]; a["wlast"] = max(a["wlast"], v["wlast"]); a["vis"] = max(a["vis"], v["vis"])
        a["lat"] = max(a["lat"], v["lat"]); a["pending"] += v["pending"]
        if v["need"] >= 0:
            a["need"] = v["need"] if a["need"] is None else min(a["need"], v["need"])
    vlist = sorted(agg.values(), key=lambda a: (a["kind"], a["pkg"], a["job"]))
    # visibility of job j's writes to job j+1 (same package): margin = first read by j+1 - all of j visible
    for a in vlist:
        nxt = agg.get((a["kind"], a["pkg"], a["job"] + 1))
        a["next_need"] = nxt["need"] if nxt else None
        a["visible_after_last_write"] = a["vis"] - a["wlast"] if a["words"] else None
        a["margin_to_next_read"] = (a["next_need"] - a["vis"]) if (a["next_need"] is not None and a["words"]) else None
    rec["visibility"] = vlist
    rec["summary"] = summarise(rec, name)
    return rec


def summarise(rec, name):
    """The three measurements, in cycles of the reduced vehicle (no clock is claimed)."""
    per, toks = rec["jobs"], rec["parsed"]["tokens"]
    commit = {t["position"]: t["cycle"] for t in toks}
    nodes = sorted(per)
    out = dict(commit_cycle=commit)
    out["per_node"] = {n: [dict(pos=j["pos"], start=j["start"], busy=j["busy"], entry_gap=j["entry_gap"],
                               handoff=j["wait_after_prev_done"], window=j["window"]) for j in per[n]]
                       for n in nodes}
    if name == "ar":
        lat = [commit[p] - commit[p - 1] for p in sorted(commit) if p - 1 in commit]
        out["ar_token_cycles"] = lat
        out["ar_busy_per_node"] = {n: [j["busy"] for j in per[n]] for n in nodes}
        out["ar_window_per_node"] = {n: [j["window"] for j in per[n]] for n in nodes}
        return out
    # wave: the second draft block (re-issued position REJ .. BLK1_END-1, all accepted)
    starts0 = [j for j in per[0]]
    seen, reissue = set(), None
    for j in starts0:
        if j["pos"] in seen and reissue is None:
            reissue = j
        seen.add(j["pos"])
    out["squashed_jobs"] = sum(e["squash"] for e in rec["wf_events"])
    out["rejections"] = [e["cycle"] for e in rec["wf_events"] if e["reject"]]
    if reissue is not None:
        i0 = starts0.index(reissue)
        blk = starts0[i0:i0 + (BLK1_END - REJ)]
        out["block1_positions"] = [j["pos"] for j in blk]
        out["block1_issue_cycle"] = blk[0]["start"]
        out["block1_last_commit_cycle"] = commit.get(BLK1_END - 1)
        out["block1_verify_cycles"] = commit.get(BLK1_END - 1, 0) - blk[0]["start"]
        out["reject_to_reissue_cycles"] = blk[0]["start"] - out["rejections"][0] if out["rejections"] else None
    # block 0 (positions 1 .. 6 issued back to back; position 1's input is the last prompt token)
    b0 = [j for j in starts0 if 1 <= j["pos"] < BLK0_END][:BLK0_END - 1]
    out["block0_issue_cycles"] = [j["start"] for j in b0]
    # steady-state entry spacing of consecutive same-user positions at every node (block 1)
    sp = {}
    for n in nodes:
        js = per[n]
        k = next((i for i in range(1, len(js)) if js[i]["pos"] <= js[i - 1]["pos"]), None)
        b1 = js[k:k + (BLK1_END - REJ)] if k is not None else []
        sp[n] = dict(entry_gaps=[j["entry_gap"] for j in b1[1:]], busy=[j["busy"] for j in b1],
                     handoff=[j["wait_after_prev_done"] for j in b1[1:]], window=[j["window"] for j in b1])
    out["block1_per_node"] = sp
    return out


def record(scratch: Path, output: Path):
    prep = json.loads((scratch / "prepare.json").read_text())
    res = dict(schema="opentallas.rtl.dsrom_wavefront_verify.v1", prepare=prep, runs={})
    for name in CONFIGS:
        log = scratch / f"out_{name}.txt"
        if not log.exists():
            continue
        out = log.read_text()
        r = analyse(out, name)
        rcf = scratch / f"run_{name}.rc"
        r["returncode_and_seconds"] = rcf.read_text().split() if rcf.exists() else None
        r["log_sha256"] = hashlib.sha256(out.encode()).hexdigest()
        r["sys_lines"] = [l for l in out.splitlines() if l.split(" ")[0] in
                          ("HDC41_ARRAY", "PASS", "FAIL", "NODE", "HBM_NODE", "KVHBM", "LOGIT", "MISMATCH",
                           "FAULT", "KVHBM_FAIL", "IDXHBM_USERS", "TIMEOUT", "KV", "VM", "KVHBM_STATE")]
        res["runs"][name] = r
    output.write_text(json.dumps(res, indent=1) + "\n")
    return res


# -- one stage in isolation (owner method, 2026-10-04): the L20 package alone --------------------
STAGE_BODY = lambda L: [list(range(0, 20)), [20], list(range(21, L))]   # package 1 = layer 20 (CSA producer + index scan)
STAGE_K = 1
STAGE_BAD = 3                                                           # position whose first input is corrupted


class _OneStage:
    """config_svh view of one package of a plan, as NODES = 1."""
    def __init__(self, plan, k):
        self.p, self.k = plan, k
        self.n, self.nb, self.hp, self.side, self.head_mcast = 1, 1, 0, {}, False
        self.vocab, self.pb = plan.vocab, plan.pb

    def role(self, _):
        r = dict(self.p.role(self.k))
        r["hid_dest"] = 1
        return r

    def ehash(self, _):
        return self.p.ehash(self.k)

    def result_parts(self):
        return 1


def _hdr(pos, length, tok):
    return (1 << 16) | (length << 24) | (pos << 40) | (tok << 104)


def _flits(vm, word, nwords):
    out = []
    for w in range(nwords):
        bits = G.bits(vm[(word + w) * A.W:(word + w + 1) * A.W])
        out.append(sum(int(b) << (32 * l) for l, b in enumerate(bits)))
    return out


def prepare_stage(scratch: Path, gold_from: Path):
    t0 = time.time()
    scratch.mkdir(parents=True, exist_ok=True)
    model = V.Model()
    lay = P.Layout(model)
    A.place_head_parts(lay)
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    plan = A.Plan(lay, STAGE_BODY(model.L), 0, False, "relay")
    progs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    k = STAGE_K
    rk, rprev = plan.role(k), plan.role(k - 1)
    gold = json.loads(gold_from.read_text())
    seq = gold["seq"]
    bad = (seq[STAGE_BAD] + 1) % plan.vocab
    jobs = [(seq[0], 0), (seq[1], 1), (seq[2], 2), (bad, STAGE_BAD), (seq[3], 3), (seq[4], 4)]

    def replay(order, capture):
        pipe = A.Pipeline(plan, progs, base)
        inj, exo = [], []
        for tok, pos in order:
            for mc in pipe.pk:
                mc.tokens = mc.tokens[:pos]
            # the pipeline up to and including package k (package k + 1 is not needed)
            pipe.pk[0].run(progs[0], tok, pos)
            pipe.hop(0, 1)
            if capture:
                inj.append([(0, _hdr(pos, rk["rxw"], tok))] +
                           [(int(i == rk["rxw"] - 1), f) for i, f in
                            enumerate(_flits(pipe.pk[k].vm, rk["rxb"], rk["rxw"]))])
            pipe.pk[k].run(progs[k], tok, pos)
            if capture:
                exo.append([(0, _hdr(pos, rk["txw"], tok))] +
                           [(int(i == rk["txw"] - 1), f) for i, f in
                            enumerate(_flits(pipe.pk[k].vm, rk["txb"], rk["txw"]))])
        mc = pipe.pk[k]
        return inj, exo, (mc.kv.copy(), mc.vm[plan.pb:plan.pb + A.PS].copy())

    inj, exo, st = replay(jobs, True)
    _, _, st_clean = replay([(seq[p], p) for p in range(5)], False)
    same = (np.array_equal(G.bits(st[0]), G.bits(st_clean[0])) and
            np.array_equal(G.bits(st[1]), G.bits(st_clean[1])))
    if not same:
        raise RuntimeError("stage ISA: squash + re-issue does not restore the clean state")
    img = scratch / "cfg_stage"
    img.mkdir(parents=True, exist_ok=True)
    words = [I.encode(**{a: v for a, v in f.items() if not a.startswith("_")}) for f in progs[k]]
    (img / "prog_stage00.hex").write_text(P.hexwords(words, I.INSTR_BITS))
    sectors, firsts = P.qe_hbm_image(lay)
    (img / "qlist_stage00.hex").write_text(P.hexwords(P.encode_list(P.qe_fetch_list(lay, progs[k], firsts)),
                                                      P.LIST_BITS))
    flat = lambda msgs: [(l << 512) | f for m in msgs for l, f in m]
    (img / "inject.hex").write_text(P.hexwords(flat(inj), 513))
    (img / "expect_out.hex").write_text(P.hexwords(flat(exo), 513))
    (img / "known.hex").write_text(P.hexwords([0] * (NBLK * KMAX), 17))
    (img / "expect_tokens.hex").write_text(P.hexwords([0] * SMAX, 16))
    (img / "expect_logits.hex").write_text(P.hexwords([0] * (2 * SMAX * plan.vocab), 32))
    (img / "expect_kv00_0.hex").write_text(P.hexwords(G.bits(st[0]), 32))
    (img / "expect_vm00_0.hex").write_text(P.hexwords(G.bits(st[1]), 32))
    svh = AC.config_svh(_OneStage(plan, k), lay, "p2p").replace("NPR = 2", "NPR = 1")
    (scratch / "stage_cfg.svh").write_text(svh)
    prep = dict(schema="opentallas.rtl.dsrom_wavefront_stage_prepare.v1", layers=plan.body[k], package=k,
                rxw=rk["rxw"], txw=rk["txw"], prev_txw=rprev["txw"], jobs=[(int(t), p) for t, p in jobs],
                corrupted_position=STAGE_BAD, corrupted_token=bad, clean_token=seq[STAGE_BAD],
                isa_squash_reissue_state_equals_clean=same, program_instructions=len(progs[k]),
                prepare_seconds=round(time.time() - t0, 1),
                input_sha256={str(p_.relative_to(ROOT)): sha(p_) for p_ in sources()})
    (scratch / "prepare_stage.json").write_text(json.dumps(prep, indent=1) + "\n")
    print(json.dumps({x: prep[x] for x in ("layers", "rxw", "txw", "jobs", "isa_squash_reissue_state_equals_clean")}))
    return prep


def run_stage(scratch: Path):
    (scratch / "array_cfg.svh").write_text((scratch / "stage_cfg.svh").read_text())
    os.environ["OT_WF_STAGE"] = "1"
    wave = int(os.environ.get("OT_WF_STAGE_WAVE", "1"))   # WAVE=0: negative control (a rewind latches proto_fault)
    exe = build(scratch, wave)
    log = scratch / f"out_stage_w{wave}.txt"
    n_out = len(json.loads((scratch / "prepare_stage.json").read_text())["jobs"])
    cmd = [str(exe), f"+DIR={scratch / 'cfg_stage'}", f"+ROMS={scratch / 'roms'}", "+NUSERS=1",
           f"+NOUT={n_out}", "+HB=1000000"]
    t0 = time.time()
    with open(log, "w") as fh:
        rc = subprocess.run(["stdbuf", "-oL", *cmd], stdout=fh, stderr=subprocess.STDOUT).returncode
    (scratch / f"run_stage_w{wave}.rc").write_text(f"{rc} {time.time() - t0:.1f}\n")
    return rc


# -- composition (model, from the measured per-stage terms) -----------------------------------
S81 = {"1048576": dict(ar=2466.2, pass_tok_s_tau3649=3742.8), "200000": dict(ar=2574.1, pass_tok_s_tau3649=4096.7)}
import third_party_tau as _TPT   # noqa: E402
TAU = _TPT.tau_ds_v41(5)          # V4.1 DSpark gamma 5, third-party published (4.159 self-measured blend SUPERSEDED)
DRAFT_OVER_AR = 0.1173            # scenario C draft composition (dsrom_wavefront_verify_20261003)
# SUCCESSOR (2026-10-04): the MEASURED DSpark draft (+ seed/commit), dsrom_dspark_mtp_step_compose.py; compose
# --draft {as_built, l1} uses it, --draft assumed keeps DRAFT_OVER_AR (reproduces the 20261004 record.json).
DRAFT_RECORD = ROOT / "results/rtl/dsrom_dspark_step_slices_20261004/composition.json"
DRAFT_VARIANTS = {"as_built": "as_built_chain", "l1": "fused_head"}


def draft_us(ctx, ar, variant):
    if variant == "assumed":
        return DRAFT_OVER_AR * ar
    c = json.loads(DRAFT_RECORD.read_text())["full_shape"]["ctx"][ctx]
    return c[DRAFT_VARIANTS[variant]]["draft_us"] + c["seed_commit_us"]
STAGE_US = {"1048576": dict(head_occ=12.37, l20_occ=11.62, window=19.24),
            "200000": dict(head_occ=12.37, l20_occ=4.51, window=15.42)}    # 4f0c050b8 model.json (S73 run)
HOP_US = 0.48                     # one 4 x 5,120 BF16 hidden state per interval (model hop term)
HEAD_RTL = dict(ii_cycles=12219, latency_cycles=12217, source="results/rtl/dsrom_c8_wavefront_20261003/head_interval_r1.json")


def stage_measure(out: str):
    jobs = [dict(zip(("node", "user", "pos", "hdr", "pay", "cstart", "start", "done"), map(int, m)))
            for m in JOB.findall(out)]
    outs = [int(c) for c in re.findall(r"OUT msg=\d+ cycle=(\d+)", out)]
    rows = []
    for i, j in enumerate(jobs):
        rows.append(dict(pos=j["pos"], start=j["start"], busy=j["done"] - j["start"],
                         entry_gap=(j["start"] - jobs[i - 1]["start"]) if i else None,
                         handoff_after_prev_done=(j["start"] - jobs[i - 1]["done"]) if i else None,
                         out_done_after_done=(outs[i] - j["done"]) if i < len(outs) else None))
    vis = [dict(zip(("kind", "pkg", "stack", "job", "words", "wlast", "vis", "lat", "need", "pending"),
                    [m[0], *map(int, m[1:])])) for m in VIS.findall(out)]
    starts = {i + 1: j["start"] for i, j in enumerate(jobs)}
    v = {}
    for kind in ("KV", "IK"):
        xs = [x for x in vis if x["kind"] == kind and x["words"]]
        nxt = [x for x in vis if x["kind"] == kind and x["need"] >= 0 and x["job"] > 1]
        v[kind] = dict(write_to_visible_max_cycles=max(x["lat"] for x in xs),
                       write_to_visible_median_cycles=sorted(x["lat"] for x in xs)[len(xs) // 2],
                       last_write_to_all_visible_max_cycles=max(x["vis"] - x["wlast"] for x in xs),
                       next_position_first_read_after_its_start_min_cycles=min(
                           x["need"] - starts[x["job"]] for x in nxt) if nxt else None,
                       visible_before_next_start_min_cycles=min(
                           starts[x["job"] + 1] - x["vis"] for x in xs if x["job"] + 1 in starts))
    m = re.search(r"KVHBM ops=(\d+) words=(\d+) writes=(\d+) holds=(\d+) state_bad=(\d+)", out)
    so = re.search(r"STAGE_OUT msgs=(\d+) out_mismatch=(\d+)", out)
    fa = re.search(r"FAULT core=(\d+) protocol=(\d+)", out)
    st = re.search(r"state_mismatch=(\d+) total_cycles=(\d+)", out)
    return dict(jobs=rows, visibility=v, kv_hold_cycles=int(m.group(4)), kv_state_bad=int(m.group(5)),
                out_msgs=int(so.group(1)), out_mismatch=int(so.group(2)),
                fault_protocol=int(fa.group(2)) if fa else 0, state_mismatch=int(st.group(1)),
                total_cycles=int(st.group(2)), pass_=("\nPASS" in out))


def compose(stage, draft_variant="as_built"):
    busy = [r["busy"] for r in stage["jobs"]]
    hand = [r["handoff_after_prev_done"] for r in stage["jobs"][1:]]
    over = max(h / b for h, b in zip(hand, busy))           # interval / occupancy - 1, measured
    vis_frac = max(stage["visibility"][k]["last_write_to_all_visible_max_cycles"] for k in ("KV", "IK")) / min(busy)
    rows = {}
    for ctx, c in S81.items():
        ar = 1e6 / c["ar"]; draft = draft_us(ctx, ar, draft_variant)
        pass_step = 3.649e6 / c["pass_tok_s_tau3649"]
        su = STAGE_US[ctx]
        r = dict(ar_us=round(ar, 2), ar_tok_s=c["ar"], pass_m1=dict(step_us=round(pass_step, 2),
                 mtp_tok_s=round(TAU * 1e6 / pass_step, 1)))
        for rule, occ in (("occupancy", max(su["head_occ"], su["l20_occ"])), ("window", su["window"])):
            ii = occ * (1 + over) + HOP_US
            ver = ar + 5 * ii
            step = ver + draft
            r[f"wavefront_{rule}"] = dict(ii_us=round(ii, 3), verify_us=round(ver, 2), verify_over_ar=round(ver / ar, 3),
                                         step_us=round(step, 2), mtp_tok_s=round(TAU * 1e6 / step, 1),
                                         gain_vs_pass=round(pass_step / step - 1, 4))
        rows[ctx] = r
    return dict(tau=TAU, draft_over_ar=DRAFT_OVER_AR if draft_variant == "assumed" else None,
                draft_variant=draft_variant, draft_record=None if draft_variant == "assumed" else str(DRAFT_RECORD.relative_to(ROOT)),
                measured_interval_overhead=round(over, 5),
                measured_visibility_over_occupancy=round(vis_frac, 5), hop_us=HOP_US, head_rtl=HEAD_RTL,
                basis="II = max stage occupancy (head 12.37 us; L20 11.62 us at 1M) x (1 + measured handoff/occupancy) "
                      "+ hop transfer (serialised, as in the reduced controller); visibility adds nothing: every K/V and "
                      "index-key row is visible before the next position starts. Verify = AR + 5 II; step = verify + "
                      "draft. S81 AR from results/uarch/dsrom_c_recheck_20261004; pass step from its tau-3.649 MTP figure.",
                ctx=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("prepare", "run", "record", "prepare-stage", "run-stage", "compose"))
    ap.add_argument("--gold", type=Path, help="prepare-stage: golden.json of a prepare run")
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--config", choices=sorted(CONFIGS))
    ap.add_argument("--output", type=Path)
    ap.add_argument("--draft", choices=("as_built", "l1", "assumed"), default="as_built",
                    help="compose: MEASURED DSpark draft (as_built / l1 fused head) or the legacy assumed 0.1173 x AR")
    ap.add_argument("--all-unit", action="store_true"); ap.add_argument("--kv-hbm", action="store_true")
    a = ap.parse_args()
    if a.action == "prepare":
        prepare(a.scratch)
    elif a.action == "prepare-stage":
        prepare_stage(a.scratch, a.gold)
    elif a.action == "run-stage":
        return run_stage(a.scratch)
    elif a.action == "compose":
        res = dict(schema="opentallas.rtl.dsrom_wavefront_stage.v1",
                   prepare=json.loads((a.scratch / "prepare_stage.json").read_text()))
        for w in (0, 1):
            f = a.scratch / f"out_stage_w{w}.txt"
            if f.exists():
                res[f"stage_wave{w}"] = stage_measure(f.read_text())
                res[f"stage_wave{w}"]["log_sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        res["composition"] = compose(res["stage_wave1"], a.draft)
        (a.output or a.scratch / "record.json").write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps(res["composition"], indent=1))
    elif a.action == "run":
        return run(a.scratch, a.config)
    else:
        record(a.scratch, a.output or a.scratch / "record.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
