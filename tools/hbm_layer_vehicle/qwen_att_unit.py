#!/usr/bin/env python3
"""VEH-ATT3 (10-19): Qwen3-8B D4G8 ATT.QK / ATT.PV unit pre-check on the d4g die SM master, from the REAL fixture rows.

Input: qwen_att_kv.py capture (q 4 x 128 BF16, the P = 8,192 K / V rows as FP8 E4M3 codes, p 4 x P BF16, the unit outputs)
of one layer of the committed D4G8 programme (qwen_d4g_proof.py: TP-8, 1 KV head + 4 q heads a die, position 8191).

d4g placement (W2, "token blocks of the head are dealt to the 16 SMs"; GEN2b die: sm_SW0..7, sm_NW0..7): SM s owns the
P / 16 = 512 tokens [512 s, 512 s + 512) = four 128-token blocks b = 4 s .. 4 s + 3 (contiguous, so the cross-SM PV merge
is the golden pairwise tree over the 64 block nodes).  Stored row order inside a block = the head-dim-128 converter's
(rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv): stored row 4 k + u = token 32 u + k (4 token streams round-robin).
The SM runs the h128 path of ot_hbm_accel_smh_attn (never exercised on the element before this lane):
  QK   one op over the SM's 512 stored rows (waves of 32: ring slot s = rows 4 s .. 4 s + 3, leaf q = row 4 s + q, step t =
       dims 8 j + t); x = the q head of column c // 2 (4 heads x 2 columns); BE mode 2 lands the leaf scores of the
       column's row parity (score index 2 s + q // 2); 16 compiler publishes a wave (index i, row 32 w + 2 i: column c =
       head c // 2, stored row 32 w + 2 i + c % 2).  Landing window calibrated from a PROBE run (no publishes).
  PV   one op a 128-token block (the probability store holds 128 rows): ring slot / merge entry 2 u + h = stream u, dim
       half h (beat h of a row: lane j = dim 8 (j % 16) + 4 h + j / 16); chunk = 8 tokens of a stream, run = 4 chunks;
       folds (0,2)(4,6)(1,3)(5,7) then (0,4)(1,5) give the 16-chunk block node ((s0+s1)+(s2+s3)) (golden order); folded
       publication: column c publishes entry c % 2 -> head c // 2, dim 8 w + 4 (c % 2) + leaf.
Checks every score / node bit for bit against the golden (att_qk / chunk sums + pairwise of the fixture rows) and
composes the 64 block nodes (pairwise, golden order) against the fixture PV output.  The cross-SM merge runs OUTSIDE
the SM (not on any on-die owner: VEH-ATT finding 3) -- composed in Python here.

    qwen_att_unit.py run --kv DIR --stage L0 --L 0 --bundle B --work W --out J [--sms ..] [--kinds qk,pv] [--dmut N]
                         [--smut early] [--blocks 0,..]
Verilator 5.050, fleet only (run_qwen_att_unit.sh).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "hbm_sm_attention"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402
import sm_attn_bench as B  # noqa: E402
import sm_elem_bench as E  # noqa: E402
import att_images as AI  # noqa: E402

F = np.float32
NSM, HEADS, HD, BLK = 16, 4, 128, 128
SM_NAMES = AI.SM_NAMES
HOP = [3, 2, 1, 0, 0, 1, 2, 3]
# control delay of the BE per column (measured, results/hbm_sm_attention_1015/elem_r8/qk_landing_calibration.json):
# 11 + 4 x hop; the probe re-measures it from the clear -> score_valid drop when it can
CTRL_DELAY = [11 + 4 * h for h in HOP]
DEFAULT_LAT = dict(req_lead=8, q_pub_margin=8, pv_node=160, fold_step=2, fold_l2=20, fold_pub=40, out=40)


# ------------------------------------------------------------------------------------------------ fixture
def load_qwen(kv_dir: Path, stage: str, L: int, rank=0):
    d = kv_dir / stage
    meta = json.loads((d / "att_kv.json").read_text())
    z = np.load(d / "att_kv.npz")
    recs = {r["op"]: r for r in meta["records"] if r["rank"] == rank and r["L"] == L}
    qk, pv = recs["ATT.QK"], recs["ATT.PV"]
    g = lambda r, n: z[r["arrays"][n]["key"]]  # noqa: E731
    rec = dict(q=g(qk, "A").astype(F), K=g(qk, "K").astype(F), Kc=g(qk, "Kc"), s=g(qk, "O").astype(F),
               p=g(pv, "A").astype(F), V=g(pv, "K").astype(F), Vc=g(pv, "Kc"), pv=g(pv, "O").astype(F))
    assert rec["q"].shape == (HEADS, HD) and rec["p"].shape[0] == HEADS, (rec["q"].shape, rec["p"].shape)
    tab = np.array([B._dec8(c) for c in range(256)], dtype=np.float64).astype(F)
    for k, c in (("K", "Kc"), ("V", "Vc")):
        if not np.array_equal(B.zbits(tab[rec[c]]), B.zbits(rec[k])):
            raise SystemExit(f"{k} codes do not decode to the fixture rows")
    for h in range(HEADS):
        if not np.array_equal(B.zbits(B.A.att_qk(rec["q"][h], rec["K"])), B.zbits(rec["s"][h])):
            raise SystemExit(f"att_qk(q[{h}], K) != fixture scores")
        if not np.array_equal(B.zbits(B.A.att_pv(rec["p"][h], rec["V"])), B.zbits(rec["pv"][h])):
            raise SystemExit(f"att_pv(p[{h}], V) != fixture PV")
    src = dict(att_kv_json=str(d / "att_kv.json"), npz_sha256=meta["npz_sha256"], stage=stage, L=L, rank=rank,
               qk_priced=qk.get("priced_d4g8"), pv_priced=pv.get("priced_d4g8"), P=int(rec["K"].shape[0]))
    return rec, src


def stored(block):
    """stored row order of a 128-token block: stored row 4 k + u = token 32 u + k"""
    return [BLK * block + 32 * u + k for k in range(32) for u in range(4)]


def plan(rec):
    P = rec["K"].shape[0]
    if P % (NSM * BLK):
        raise SystemExit(f"P {P} is not a multiple of 16 x 128")
    nb = P // BLK // NSM
    ops = []
    for s in range(NSM):
        blocks = list(range(nb * s, nb * (s + 1)))
        ops.append(dict(name=f"qk_{SM_NAMES[s]}", kind="qk", sm=s, rows=sum((stored(b) for b in blocks), [])))
        for b in blocks:
            ops.append(dict(name=f"pv_{SM_NAMES[s]}_b{b}", kind="pv", sm=s, block=b, rows=stored(b)))
    return ops


# ------------------------------------------------------------------------------------------------ compiler (h128)
def compile_q(rec, op, lat, smut="", probe=False, t0=8):
    """one h128 attention op on one SM -> (calendar, expectation).  probe: QK without publishes (landing calibration).
    smut 'early': every QK wave published 16 cycles before its measured first-possible landing of slot 7 (must FAIL)."""
    qk = op["kind"] == "qk"
    rows = op["rows"]
    n = len(rows)
    cal = E.Calendar()
    c = t0
    if qk:
        for t in range(8):
            fields = {}
            for col in range(8):
                qb = B.bf16b(rec["q"][col // 2])
                v = sum(int(qb[8 * l + t]) << (16 * l) for l in range(16))
                for lr in range(4):
                    fields[(col, lr)] = v
            for g, beat in enumerate(E.x_beats(fields)):
                cal.xw[c] = (1 << 2062) | (t << 2055) | (g << 2048) | beat
                c += 1
    else:
        if n > 128:
            raise SystemExit("PV op > 128 rows: the probability store holds 128")
        pb = [B.bf16b(rec["p"][h]) for h in range(HEADS)]
        for i, r in enumerate(rows):
            cal.xw[c] = (1 << 2062) | (i << 2055) | (127 << 2048) | sum(int(pb[col // 2][r]) << (16 * col)
                                                                        for col in range(8))
            c += 1
    codes = rec["Kc"] if qk else rec["Vc"]
    lines = B.stream_lines(b"".join(bytes(np.asarray(codes[r], dtype=np.uint8)) for r in rows))
    base = 0x1000
    c += 2
    mode = 4 | (0 if qk else 2)
    hold = dict(mode=mode, h128=1)
    cal.kvd[c] = base | (len(lines) << 32)
    cal.set(c, dload=1, **hold)
    t_cfg = c
    c += 1
    cal.set(c, configure=1, rows=n, n8=n, **hold)
    m = E.KvLineModel()
    m.cfg(qk, False, n, True, n)
    c += 1
    if qk:
        assert n % 32 == 0, "QK op rows must be whole 32-row waves"
        nbeats = 2 * n
    else:
        nbeats = 2 * n
    li, acc, consumed, beats, first_line = 0, 0, 0, [], None
    wave_beats = []                     # QK: per wave list of (cycle, slot, step)
    while consumed < nbeats:
        assert c < 60000, "calendar runaway"
        acc += E.LINE_RATE[0]
        give = False
        if li < len(lines) and acc >= E.LINE_RATE[1] and m.s_ready() and c > t_cfg + lat["req_lead"]:
            acc -= E.LINE_RATE[1]
            give = True
        elif acc >= E.LINE_RATE[1]:
            acc = E.LINE_RATE[1]
        take = False
        if m.m_valid():
            h = m.head()
            ring = h["slot"] if qk else 2 * (h["slot"] % 4) + h["step"]
            if c % 8 == ring:
                take = True
        popped = m.step(give, take)
        if give:
            tag = li & 0x3FF
            cal.pkt[c] = (1 << 1098) | (tag << 1088) | lines[li]
            cal.set(c, pkt=1, pkt_tag=tag, **hold)
            cal.set(c - lat["req_lead"], req=1, req_addr=base + li, req_tag=tag, **hold)
            if first_line is None:
                first_line = c
            li += 1
        if take:
            b = popped
            if qk:
                w = consumed // 64                  # waves of 32 rows = 8 slots x 8 steps (n % 32 == 0 asserted)
                if w == len(wave_beats):
                    wave_beats.append([])
                wave_beats[w].append((c, b["slot"], b["step"]))
                cal.set(c, consume=1, eslot=b["slot"], estep=b["step"], first=int(b["step"] == 0),
                        last=int(b["step"] == 7), tag_row=32 * w + 4 * b["slot"], tag_last=1, tag_slot=b["slot"],
                        xaddr=b["step"], **hold)
            else:
                i = 8 * (consumed // 16) + b["slot"]
                u, k = i % 4, i // 4
                nk = n // 4
                cal.set(c, consume=1, eslot=b["slot"], estep=b["step"], first=int(k % 8 == 0), last=int(k % 8 == 7),
                        run_first=int(k < 8), run_last=int(k >= nk - 8), tag_row=i, tag_slot=2 * u + b["step"], **hold)
                cal.set(c - 3, pread=1, paddr=i, **hold)
            beats.append(c)
            consumed += 1
        c += 1
    last_consume = beats[-1]
    exp = dict(first_line=first_line, last_consume=last_consume, lines=len(lines), t_cfg=t_cfg)
    if qk:
        exp["waves"] = []
        lq0, lq1 = lat.get("q_land_min"), lat.get("q_land_max")
        prev_last_pub = None
        for w, wb in enumerate(wave_beats):
            b7 = {s: cc for cc, s, t in wb if t == 7}
            ent = dict(wave=w, beat7=b7, last_consume=wb[-1][0])
            if not probe:
                pub0 = max(b7.values()) + lq1 + 1 + lat["q_pub_margin"]
                if smut == "early":
                    pub0 = max(b7.values()) + lq0 - 16
                first_land = min(b7.values()) + lq0
                clr = (first_land - 4) if prev_last_pub is None else prev_last_pub + 1
                assert clr < first_land, f"wave {w}: clear {clr} not before first landing {first_land}"
                cal.set(clr, be_clear=1, **hold)
                nidx = 2 * len(b7)
                for i in range(nidx):
                    cal.set(pub0 + i, be_publish=1, be_index=i, be_row=32 * w + 2 * i, be_expect=0xFF, **hold)
                ent.update(clear=clr, publish=[pub0, pub0 + nidx - 1])
                prev_last_pub = pub0 + nidx - 1
            else:
                cal.set(min(b7.values()), be_clear=1, **hold)     # probe: one clear a wave (control-delay witness)
                ent["clear"] = min(b7.values())
            exp["waves"].append(ent)
        if not probe:
            for w in range(len(exp["waves"]) - 1):         # publish i of wave w before wave w+1 slot i//2 lands
                a, b_ = exp["waves"][w], exp["waves"][w + 1]
                for i in range(2 * len(a["beat7"])):
                    if smut:
                        break
                    assert a["publish"][0] + i < b_["beat7"][i // 2] + lq0, f"wave {w}: publish {i} after wave {w + 1} lands"
            end = exp["waves"][-1]["publish"][1] + lat["out"]
        else:
            end = last_consume + 200
        be_mode = 2
    else:
        F0 = last_consume + lat["pv_node"]
        st = lat["fold_step"]
        for j, (fa, fb) in enumerate(((0, 2), (4, 6), (1, 3), (5, 7))):
            cal.set(F0 + st * j, fold=1, fold_a=fa, fold_b=fb, **hold)
        for j, (fa, fb) in enumerate(((0, 4), (1, 5))):
            cal.set(F0 + lat["fold_l2"] + st * j, fold=1, fold_a=fa, fold_b=fb, **hold)
        pub = F0 + lat["fold_pub"]
        cal.set(pub, publish=1, folded=1, **hold)
        exp.update(fold=F0, pv_publish=pub)
        end = pub + 64 + lat["out"]
        be_mode = 3
    for cc in range(t_cfg, end + 1):
        d = cal.at(cc)
        d.setdefault("mode", mode)
        d.setdefault("h128", 1)
        d.setdefault("be_mode", be_mode)
    exp["end"] = end
    return cal, exp


def r_words(out):
    return [(int(x[1]), int(x[2], 16), int(x[3], 16)) for x in (ln.split() for ln in out.splitlines()
                                                                 if ln.startswith("R "))]


def pv_block_node(rec, block):
    """golden 128-dim node of a block for every head: pairwise over its 16 chunk sums (token order)"""
    tk = list(range(BLK * block, BLK * (block + 1)))
    out = np.zeros((HEADS, HD), dtype=F)
    for h in range(HEADS):
        cs = B.chunk_sums(rec["p"][h][tk], rec["V"][tk])
        out[h] = B.A.pairwise([cs[i] for i in range(cs.shape[0])])
    return out


def check(rec, op, exp, out):
    words = r_words(out)
    rows = op["rows"]
    if op["kind"] == "qk":
        got = np.full((HEADS, len(rows)), -1, dtype=np.int64)
        extra = 0
        for _cyc, rrow, data in words:
            for col in range(8):
                idx = rrow + col % 2
                if idx >= len(rows) or got[col // 2, idx] >= 0:
                    extra += 1
                    continue
                got[col // 2, idx] = (data >> (32 * col)) & 0xFFFFFFFF
        want = np.stack([B.bits32(rec["s"][h][rows]) for h in range(HEADS)]).astype(np.int64)
        res = dict(results=int(np.sum(got >= 0)), expected=HEADS * len(rows),
                   mismatches=int(np.sum(got != want)) + extra)
        node = None
    else:
        got = np.full((HEADS, HD), -1, dtype=np.int64)
        extra = 0
        for _cyc, rrow, data in words:
            leaf, wd = (rrow >> 4) & 3, rrow & 15
            for col in range(8):
                dim = 8 * wd + 4 * (col % 2) + leaf
                if got[col // 2, dim] >= 0:
                    extra += 1
                    continue
                got[col // 2, dim] = (data >> (32 * col)) & 0xFFFFFFFF
        want = B.bits32(pv_block_node(rec, op["block"])).astype(np.int64)
        res = dict(results=int(np.sum(got >= 0)), expected=HEADS * HD, mismatches=int(np.sum(got != want)) + extra)
        node = got.astype(np.uint32).view(F) if res["mismatches"] == 0 and res["results"] == res["expected"] else None
    res.update(result_rows=len(words), first_result=words[0][0] if words else None,
               last_result=words[-1][0] if words else None)
    return res, node


def calibrate(out, exp):
    """landing window from a probe run: G lines = BE tree-input valid (mode 2 score landing) per column, S lines =
    score_valid changes (a drop after a probe clear gives the column's control delay)."""
    g = {}
    s_drop = {}
    for ln in out.splitlines():
        p = ln.split()
        if p[:1] == ["G"]:
            g.setdefault(int(p[2]), []).append(int(p[1]))
        elif p[:1] == ["S"] and int(p[3], 16) == 0:
            s_drop.setdefault(int(p[2]), []).append(int(p[1]))
    clears = [w["clear"] for w in exp["waves"]]
    delay = {}
    for col, ds in s_drop.items():
        cand = sorted({x - cc for x in ds for cc in clears if 0 < x - cc < 64})
        delay[col] = cand[0] if cand else None
    order = [(w["wave"], s, b7) for w in exp["waves"] for s, b7 in sorted(w["beat7"].items())]
    offs = []
    per_col = {}
    for col in range(8):
        ev = sorted(g.get(col, []))
        d = delay.get(col) if delay.get(col) is not None else CTRL_DELAY[col]
        per_col[col] = dict(landings=len(ev), control_delay=d)
        if len(ev) != len(order):
            continue
        o = [e - d - b7 for e, (_w, _s, b7) in zip(ev, order)]
        per_col[col].update(min=min(o), max=max(o))
        offs += o
    if not offs:
        raise SystemExit(f"probe: no column with {len(order)} landings ({ {c: v['landings'] for c, v in per_col.items()} })")
    return dict(q_land_min=min(offs), q_land_max=max(offs), per_column=per_col, slots=len(order))


# ------------------------------------------------------------------------------------------------ runner
def run_op(exe, rec, op, lat, work, tagname, smut="", probe=False):
    cal, exp = compile_q(rec, op, lat, smut=smut, probe=probe)
    d = work / f"{op['name']}_{tagname}"
    d.mkdir(parents=True, exist_ok=True)
    n = exp["end"] + 4
    if n > 4096:
        raise SystemExit(f"{op['name']}: calendar {n} > tb MAXC 4096")
    cal.write(d, n)
    r = subprocess.run([str(exe), f"+CMD={d}/cmd.hex", f"+PKT={d}/pkt.hex", f"+XW={d}/xw.hex", f"+KVD={d}/kvd.hex",
                        f"+N={n}"], capture_output=True, text=True, timeout=7200)
    out = r.stdout + r.stderr
    (d / "run.log").write_text(out)
    first_word = min([cc for cc, f in enumerate(cal.cyc) if f] + list(cal.kvd) + list(cal.pkt))
    res = dict(name=op["name"], sm=SM_NAMES[op["sm"]], kind=op["kind"], block=op.get("block"), rows=len(op["rows"]),
               rc=r.returncode, fault=("FAULT" in out), calendar={k: v for k, v in exp.items() if k != "waves"},
               first_word=first_word, lines=exp["lines"])
    node = None
    if not probe:
        chk, node = check(rec, op, exp, out)
        res.update(chk)
        res["pass"] = r.returncode == 0 and not res["fault"] and res["mismatches"] == 0 and \
            res["results"] == res["expected"]
        if res["first_result"] is not None:
            res["span_first_word_to_last_result"] = res["last_result"] - first_word
            res["span_first_line_to_last_result"] = res["last_result"] - exp["first_line"]
            # TOKSIM-HBM-att: whole record at the SM face incl. the x-load (xw) beats
            res["span_first_any_to_last_result"] = res["last_result"] - min([first_word] + list(cal.xw))
    return res, node, out, exp


def cmd_run(a):
    rec, src = load_qwen(Path(a.kv), a.stage, a.L)
    ops = plan(rec)
    if a.sms:
        want = {int(x) for x in a.sms.split(",")}
        ops = [o for o in ops if o["sm"] in want]
    if a.kinds:
        ops = [o for o in ops if o["kind"] in a.kinds.split(",")]
    if a.blocks:
        want = {int(x) for x in a.blocks.split(",")}
        ops = [o for o in ops if o["kind"] == "qk" or o["block"] in want]
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    lat = dict(DEFAULT_LAT)
    if a.lat:
        lat.update(json.loads(a.lat))
    exe = AI.build_unit(work, Path(a.bundle).resolve(), ROOT / "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv",
                        a.dmut, True)
    t0 = time.time()
    calib = None
    qk_ops = [o for o in ops if o["kind"] == "qk"]
    if qk_ops and "q_land_min" not in lat:
        # PROBE (calibration only, never a qualifying run): the first QK op without publishes
        if a.calib and Path(a.calib).exists():
            calib = json.loads(Path(a.calib).read_text())
        else:
            res, _n, out, exp = run_op(exe, rec, qk_ops[0], lat, work, f"probe_d{a.dmut}", probe=True)
            calib = calibrate(out, exp)
            calib.update(op=qk_ops[0]["name"], rc=res["rc"], fault=res["fault"])
            (work / f"calib_{a.stage}_L{a.L}.json").write_text(json.dumps(calib, indent=1))
        lat.update(q_land_min=calib["q_land_min"], q_land_max=calib["q_land_max"])
        print("CALIB " + json.dumps({k: v for k, v in calib.items() if k != "per_column"}), flush=True)
    tagname = f"d{a.dmut}{('_' + a.smut) if a.smut else ''}"
    results, nodes = [], {}
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = [ex.submit(run_op, exe, rec, o, lat, work, tagname, a.smut) for o in ops]
        for o, fu in zip(ops, futs):
            res, node, _out, _exp = fu.result()
            if node is not None:
                nodes[o["block"]] = node
            results.append(res)
            print(("PASS " if res["pass"] else "FAIL ") + json.dumps({k: v for k, v in res.items() if k != "calendar"}),
                  flush=True)
    merged = None
    nblk = rec["K"].shape[0] // BLK
    if len(nodes) == nblk:
        mm = []
        for h in range(HEADS):
            m = B.A.pairwise([nodes[b][h] for b in range(nblk)])
            mm.append(int(np.sum(B.zbits(m) != B.zbits(rec["pv"][h]))))
        merged = dict(blocks=nblk, equals_fixture_pv=all(x == 0 for x in mm), mismatches_per_head=mm)
    per_sm = {}
    for r in results:
        if "span_first_word_to_last_result" not in r:
            continue
        e = per_sm.setdefault(r["sm"], dict(qk=0, pv=0, pv_ops=0))
        e[r["kind"]] += r["span_first_word_to_last_result"]
        e["pv_ops"] += r["kind"] == "pv"
    summ = dict(stage=a.stage, L=a.L, ops=len(results), passed=sum(r["pass"] for r in results), dmut=a.dmut,
                smut=a.smut, lat=lat, calibration=calib, source=src, cross_block_merge=merged,
                per_sm_span_sum=per_sm,
                cross_sm_merge_scope="pairwise over the 64 block nodes (golden order), composed in Python: the cross-SM "
                                     "PV merge has no on-die owner (VEH-ATT finding 3)",
                rtl="ot_hbm_accel_smh_attn die master (GEN2b bundle master_files.json + defines "
                    + ",".join(AI.DIE_DEFINES) + ") in tb_hbm_smh_attn (PROBE build: extra G/S probe prints only)",
                wall_s=round(time.time() - t0, 1),
                verdict="PASS" if results and all(r["pass"] for r in results) and
                (merged is None or merged["equals_fixture_pv"]) else "FAIL")
    Path(a.out).write_text(json.dumps(dict(summary=summ, ops=results), indent=1, default=int))
    print(("PASS" if summ["verdict"] == "PASS" else "FAIL") + " HBM_VEH_QWEN_ATT_UNIT " +
          json.dumps({k: v for k, v in summ.items() if k not in ("source", "calibration")}, default=int))
    return 0 if summ["verdict"] == "PASS" else 1


def cmd_selftest(a):
    """python-only: compile every op (no simulator) and check the golden composition (block nodes -> fixture PV)"""
    rec, src = load_qwen(Path(a.kv), a.stage, a.L)
    ops = plan(rec)
    lat = dict(DEFAULT_LAT, q_land_min=20, q_land_max=30)
    spans = {}
    for o in ops[:5]:
        cal, exp = compile_q(rec, o, lat)
        spans[o["name"]] = dict(end=exp["end"], last_consume=exp["last_consume"], lines=exp["lines"])
    nblk = rec["K"].shape[0] // BLK
    nodes = [pv_block_node(rec, b) for b in range(nblk)]
    ok = all(np.array_equal(B.zbits(B.A.pairwise([nodes[b][h] for b in range(nblk)])), B.zbits(rec["pv"][h]))
             for h in range(HEADS))
    print(json.dumps(dict(ops=len(ops), compiled=spans, block_merge_equals_fixture_pv=ok)))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("run", "selftest"):
        p = sub.add_parser(nm)
        p.add_argument("--kv", required=True, help="qwen_att_kv.py output dir (contains <stage>/att_kv.json)")
        p.add_argument("--stage", default="L0")
        p.add_argument("--L", type=int, default=0)
        if nm == "run":
            p.add_argument("--out", required=True)
            p.add_argument("--work", required=True)
            p.add_argument("--bundle", required=True)
            p.add_argument("--sms", default="")
            p.add_argument("--kinds", default="")
            p.add_argument("--blocks", default="")
            p.add_argument("--dmut", type=int, default=0)
            p.add_argument("--smut", default="", choices=["", "early"])
            p.add_argument("--lat", default="")
            p.add_argument("--calib", default="", help="reuse a probe calibration json")
            p.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    return {"run": cmd_run, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
