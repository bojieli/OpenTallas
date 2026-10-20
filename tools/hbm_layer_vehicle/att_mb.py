#!/usr/bin/env python3
"""HBM-ATTN-MB (10-19): MULTI-BLOCK attention calendar for the d4g SM attention path (ot_hbm_accel_smh_attn), compiler +
unit runner.  Compiler-only lever on the CURRENT RTL (no tile changes): the same per-beat command fields, converter model
and result laws as sm_elem_bench.compile_op (DS) / qwen_att_unit.compile_q (Qwen), with the op-serial gaps removed.

What changes against the serial calendars ("base"):
  (1) KV PREFETCH: the run descriptor (dload) and the converter configure are issued BEFORE the x loader (q / p), so the
      KV line stream fills the converter's two wave buffers (the double-buffered K/V operand SRAM: 2 waves x 8 banks of
      64x512 macros) while the operand vector is still loading.  On the die this prefetch sits in the gap before the op
      (q from SU for QK, softmax for PV); `--req-lead` puts the line requests a full HBM loaded latency ahead.
  (2) x-LOAD OVERLAP: consume slots wait per operand word, not for the whole load: QK step t only after q word t has
      landed + x_lead (calibrated); PV token i only after p[i] is written + 5 (pstore read-after-write law).
  (3) BLOCK CHAINING (PV, several KV blocks in flight per SM): block k+1's descriptor loads as soon as block k's last
      request is out, its converter op starts at block k's op_done, its lines and its probabilities (p of k+1 written
      behind block k's pstore read pointer: W >= R_k(i) + 2) stream during block k's merge drain / folds / publication,
      and only its CHUNK-LAST beats (the merge events) wait for block k's publication to clear (release = publish +
      chain_gap, calibrated).  One SM programme per kind instead of a re-launched op per block.
  (4) DS: one op per SM (the 2,048-word SM programme store, HBM-SMBUDGET 0jx) instead of 32-row sub-runs.
NOT done (and why): QK of block k+1 overlapped with PV of block k needs an online-softmax rescale (exp(s - m_partial)
then x exp(m_partial - m)); the golden takes the global max first (attend.max over all T before exp), so any rescale
changes rounding (class C) -- excluded by the owner (no numerics change).  The exact equivalent kept here is (1)+(3):
the PV KV stream and probabilities of the next block are in flight during the current block's tail.

  att_mb.py ds   --kv DIR --layer 2 --bundle B --work W --out J --mode {base,mb} [--sms ..] [--kinds ..] [--smut ..]
  att_mb.py qwen --kv DIR --stage L0 --L 0 --bundle B --work W --out J --mode {base,mb} [--sms ..] [--smut ..]
Verilator 5.050, fleet only (run_att_mb.sh).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import hashlib
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
import qwen_att_unit as QU  # noqa: E402

F = np.float32
# MB latencies (calibrated by the sweep in run_att_mb.sh; see README):
#   x_lead     QK: command cycles from the last x beat of q word t to the first consume of step t
#              (Qwen h128 needs more than DS: becde1162 sweep x_lead 0/2/4/8 -> 62/42/25/4 mismatches, all wave 0,
#              head-3 columns 6/7 = the last beats of each q word; the per-column x landing is staggered)
#   pre        cycles from the converter configure to the first x beat (prefetch window; the die fills it in the gap)
#   chain_gap  PV chain: block k+1's chunk-last consumes >= block k's publish command + chain_gap
MB_LAT = dict(x_lead=8, pre=48, chain_gap=80, p_war=2)


def hexdump_run(exe, cal, d: Path, n):
    d.mkdir(parents=True, exist_ok=True)
    if n > 4096:
        raise SystemExit(f"{d.name}: calendar {n} > tb MAXC 4096")
    cal.write(d, n)
    r = subprocess.run([str(exe), f"+CMD={d}/cmd.hex", f"+PKT={d}/pkt.hex", f"+XW={d}/xw.hex", f"+KVD={d}/kvd.hex",
                        f"+N={n}"], capture_output=True, text=True, timeout=7200)
    out = r.stdout + r.stderr
    (d / "run.log").write_text(out)
    return r.returncode, out


def lat_tag(lat):
    return hashlib.sha256(json.dumps(lat, sort_keys=True).encode()).hexdigest()[:8]


def first_word(cal):
    return min([c for c, f in enumerate(cal.cyc) if f] + list(cal.kvd) + list(cal.pkt) + list(cal.xw))


def first_x(cal):
    return min(cal.xw) if cal.xw else None


# ------------------------------------------------------------------------------------------------ the engine
class Seg:
    """one converter op (KV block) of a chained calendar"""

    def __init__(self, fmt, kind, rows, lines, xbeats, n8=0, kv4=0):
        self.fmt, self.kind, self.rows, self.lines, self.xbeats = fmt, kind, rows, lines, xbeats
        self.qk = kind == "qk"
        self.n, self.n8, self.kv4 = len(rows), n8, kv4
        self.h128 = fmt == "qw"
        if self.h128:
            self.mode = 4 | (0 if self.qk else 2)
            self.hold = dict(mode=self.mode, h128=1)
            self.cfg_fields = dict(rows=self.n, n8=self.n)
            self.mcfg = (self.qk, False, self.n, True, self.n)
            self.nbeats = 2 * self.n
        else:
            self.mode = 4 | (2 if not self.qk else 0) | (1 if (kv4 and not self.qk) else 0)
            self.hold = dict(mode=self.mode)
            n8f = n8 if self.qk else (0 if kv4 else self.n)
            self.cfg_fields = dict(rows=self.n, n8=n8f)
            self.mcfg = (self.qk, bool(kv4) and not self.qk, n8f, False, self.n)
            self.nbeats = 8 * self.n
        self.beats = []          # (cycle, beat dict, consumed index)
        self.pread = {}          # addr -> pread cycle
        self.pwrite = {}         # addr -> write cycle
        self.xdone = {}          # QK x word t -> cycle of its last beat
        self.release = None      # PV chain: earliest chunk-last consume of the next block

    def ring(self, b):
        if self.qk:
            return b["slot"]
        return 2 * (b["slot"] % 4) + b["step"] if self.h128 else b["step"]

    def fields(self, b, k):
        """command fields of consume k (beat b) + (x key, pread addr, chunk-last)"""
        if self.qk:
            w = k // 64
            row = (32 * w + 4 * b["slot"]) if self.h128 else (8 * w + b["slot"])
            f = dict(consume=1, eslot=b["slot"], estep=b["step"], first=int(b["step"] == 0), last=int(b["step"] == 7),
                     tag_row=row, tag_last=1, tag_slot=b["slot"], xaddr=b["step"])
            return f, b["step"], None, False
        if self.h128:
            i = 8 * (k // 16) + b["slot"]
            u, kk = i % 4, i // 4
            nk = self.n // 4
            f = dict(consume=1, eslot=b["slot"], estep=b["step"], first=int(kk % 8 == 0), last=int(kk % 8 == 7),
                     run_first=int(kk < 8), run_last=int(kk >= nk - 8), tag_row=i, tag_slot=2 * u + b["step"])
            return f, i, i, kk % 8 == 7
        wave = k // 64
        tk = 8 * wave + b["slot"]
        lastc = (self.n - 1) & ~7
        lst = tk % 8 == 7 or tk + 1 == self.n
        f = dict(consume=1, eslot=b["slot"], estep=b["step"], first=int(tk % 8 == 0), last=int(lst),
                 run_first=int(tk < 8), run_last=int(tk >= lastc), tag_row=tk, tag_slot=b["step"])
        return f, tk, tk, lst


def engine(segs, lat, t0=8, smut=""):
    """play the segments (KV blocks of one SM and kind) through ONE converter model and one xw port; returns the calendar
    (the result tails are placed by each segment's tail_hook at its last consume)."""
    cal = E.Calendar()
    m = E.KvLineModel()
    c = t0
    base = 0x1000
    xq = []                                   # pending x beats: (seg, key, word, beat j of key, beats of key)
    cur = -1                                  # segment whose converter op is configured / running
    dl, cfgc = {}, {}
    li = acc = 0
    last_req = None
    xi_next = 0
    xw_open = None                            # first xw cycle (configure of segment 0 + pre: the prefetch window)
    while True:
        assert c < 60000, "calendar runaway"
        # x beats of segment k enter the xw queue once segment k-1 has started consuming (they then trail its reads)
        while xi_next < len(segs) and (xi_next == 0 or segs[xi_next - 1].beats):
            xq += [(xi_next,) + xb for xb in segs[xi_next].xbeats]
            xi_next += 1
        nxt = cur + 1
        # descriptor load of the next segment: as soon as the previous segment's last line request is out
        if nxt < len(segs) and nxt not in dl:
            if nxt == 0 or (li >= len(segs[cur].lines) and last_req is not None and c > last_req):
                s = segs[nxt]
                cal.kvd[c] = base | (len(s.lines) << 32)
                cal.set(c, dload=1, **s.hold)
                dl[nxt] = c
        # converter configure of the next segment: at the previous op's op_done (converter idle)
        if nxt < len(segs) and nxt in dl and not m.act and c > dl[nxt] and \
                (cur < 0 or len(segs[cur].beats) == segs[cur].nbeats):
            s = segs[nxt]
            cal.set(c, configure=1, **s.cfg_fields, **s.hold)
            m.cfg(*s.mcfg)
            cfgc[nxt] = c
            cur, li, acc = nxt, 0, 0
            if xw_open is None:
                xw_open = c + lat["pre"]
            c += 1
            continue
        # xw port: one beat a cycle in queue order; PV beats of block k overwrite p[i] only behind block k-1's read of i
        if xq and xw_open is not None and c >= xw_open:
            si, a, w, j, nb = xq[0]
            s = segs[si]
            okw = True
            if not s.qk and si > 0 and smut != "pwar":
                r = segs[si - 1].pread.get(a)
                okw = r is not None and c >= r + lat["p_war"]
            if okw:
                xq.pop(0)
                cal.xw[c] = w
                if s.qk:
                    if j == nb - 1:
                        s.xdone[a] = c
                else:
                    s.pwrite[a] = c
        if cur >= 0 and m.act:
            s = segs[cur]
            acc += E.LINE_RATE[0]
            give = False
            if li < len(s.lines) and acc >= E.LINE_RATE[1] and m.s_ready() and c - lat["req_lead"] > dl[cur]:
                acc -= E.LINE_RATE[1]
                give = True
            elif acc >= E.LINE_RATE[1]:
                acc = E.LINE_RATE[1]
            take = False
            if m.m_valid():
                h = m.head()
                if c % 8 == s.ring(h):
                    _f, key, pa, chunk_last = s.fields(h, len(s.beats))
                    if s.qk:
                        xd = s.xdone.get(key)
                        take = xd is not None and c >= xd + lat["x_lead"]
                    else:
                        pw = s.pwrite.get(pa)
                        take = pw is not None and c - 3 >= pw + 2
                        if take and chunk_last and cur > 0:
                            take = c >= segs[cur - 1].release
            popped = m.step(give, take)
            if give:
                tag = li & 0x3FF
                cal.pkt[c] = (1 << 1098) | (tag << 1088) | s.lines[li]
                cal.set(c, pkt=1, pkt_tag=tag, **s.hold)
                rq = c - lat["req_lead"]
                cal.set(rq, req=1, req_addr=base + li, req_tag=tag, **s.hold)
                last_req = rq if last_req is None else max(last_req, rq)
                li += 1
            if take:
                f, key, pa, chunk_last = s.fields(popped, len(s.beats))
                cal.set(c, **f, **s.hold)
                if pa is not None:
                    cal.set(c - 3, pread=1, paddr=pa, **s.hold)
                    s.pread[pa] = c - 3
                s.beats.append((c, popped, len(s.beats)))
                if len(s.beats) == s.nbeats:
                    s.last_consume = c
                    s.tail_hook(cal, s, lat)
        if all(len(x.beats) == x.nbeats for x in segs):
            break
        c += 1
    return cal


# ------------------------------------------------------------------------------------------------ DS (d4g, hd 512)
def ds_xbeats(rec, kind, rows):
    out = []
    if kind == "qk":
        qb = B.bf16b(rec["q"])
        for t in range(8):
            fields = {}
            for col in range(8):
                for lr in range(4):
                    fields[(col, lr)] = sum(int(qb[8 * (16 * lr + l) + t]) << (16 * l) for l in range(16))
            for g, beat in enumerate(E.x_beats(fields)):
                out.append((t, (1 << 2062) | (t << 2055) | (g << 2048) | beat, g, 13))
    else:
        pb = B.bf16b(rec["p"])
        for i, r in enumerate(rows):
            out.append((i, (1 << 2062) | (i << 2055) | (127 << 2048) | sum(int(pb[r]) << (16 * col) for col in range(8)),
                        0, 1))
    return out


def ds_segs(rec, op):
    name, kind, kv4, rows = op[:4]
    T8 = len(rec["rows8"])
    s = Seg("ds", kind, rows, AI.op_lines(rec, rows), ds_xbeats(rec, kind, rows),
            n8=sum(1 for r in rows if r < T8), kv4=kv4)
    s.nrun = op[4]
    return s


def ds_tail(cal, s, lat, smut=""):
    if s.qk:
        nw = (s.n + 7) // 8
        exp = []
        lasts = [max(cc for cc, _b, k in s.beats if k // 64 == w) for w in range(nw)]
        prev_pub = None
        for w in range(nw):
            last_w = lasts[w]
            ncols = min(8, s.n - 8 * w)
            pub = last_w + lat["qk_land"] + 1
            clr = last_w + lat["qk_clear"] if prev_pub is None else prev_pub + 1
            if smut == "early":
                pub = last_w + lat["qk_land_meas"]
            assert clr < last_w + lat["qk_first"], f"wave {w}: clear {clr} not before first landing"
            if not smut and w + 1 < nw:
                assert pub < lasts[w + 1] + lat["qk_first"], f"wave {w}: publish {pub} after wave {w + 1} lands"
            cal.set(clr, be_clear=1, **s.hold)
            cal.set(pub, be_publish=1, be_row=8 * w, be_expect=(1 << ncols) - 1, **s.hold)
            exp.append(dict(wave=w, rows=[s.rows[8 * w + k] for k in range(ncols)], last_consume=last_w, clear=clr,
                            publish=pub))
            prev_pub = pub
        s.exp = dict(qk=exp)
        s.end = exp[-1]["publish"] + lat["out"]
    else:
        pub = s.last_consume + lat["pv_node"]
        cal.set(pub, publish=1, **s.hold)
        s.exp = dict(pv_publish=pub)
        s.end = pub + 64 + lat["out"]
        s.release = pub + lat["chain_gap"]


# ------------------------------------------------------------------------------------------------ Qwen (h128)
def qw_xbeats(rec, kind, rows):
    out = []
    if kind == "qk":
        for t in range(8):
            fields = {}
            for col in range(8):
                qb = B.bf16b(rec["q"][col // 2])
                v = sum(int(qb[8 * l + t]) << (16 * l) for l in range(16))
                for lr in range(4):
                    fields[(col, lr)] = v
            for g, beat in enumerate(E.x_beats(fields)):
                out.append((t, (1 << 2062) | (t << 2055) | (g << 2048) | beat, g, 13))
    else:
        pb = [B.bf16b(rec["p"][h]) for h in range(QU.HEADS)]
        for i, r in enumerate(rows):
            out.append((i, (1 << 2062) | (i << 2055) | (127 << 2048) |
                        sum(int(pb[col // 2][r]) << (16 * col) for col in range(8)), 0, 1))
    return out


def qw_seg(rec, op):
    codes = rec["Kc"] if op["kind"] == "qk" else rec["Vc"]
    lines = B.stream_lines(b"".join(bytes(np.asarray(codes[r], dtype=np.uint8)) for r in op["rows"]))
    s = Seg("qw", op["kind"], op["rows"], lines, qw_xbeats(rec, op["kind"], op["rows"]))
    s.block = op.get("block")
    return s


def qw_tail(cal, s, lat, smut=""):
    if s.qk:
        wave_beats = []
        for cc, b, k in s.beats:
            w = k // 64
            if w == len(wave_beats):
                wave_beats.append([])
            wave_beats[w].append((cc, b["slot"], b["step"]))
        waves = []
        lq0, lq1 = lat["q_land_min"], lat["q_land_max"]
        prev_last_pub = None
        for w, wb in enumerate(wave_beats):
            b7 = {sl: cc for cc, sl, t in wb if t == 7}
            pub0 = max(b7.values()) + lq1 + 1 + lat["q_pub_margin"]
            if smut == "early":
                pub0 = max(b7.values()) + lq0 - 16
            first_land = min(b7.values()) + lq0
            clr = (first_land - 4) if prev_last_pub is None else prev_last_pub + 1
            assert clr < first_land
            cal.set(clr, be_clear=1, **s.hold)
            nidx = 2 * len(b7)
            for i in range(nidx):
                cal.set(pub0 + i, be_publish=1, be_index=i, be_row=32 * w + 2 * i, be_expect=0xFF, **s.hold)
            waves.append(dict(wave=w, beat7=b7, clear=clr, publish=[pub0, pub0 + nidx - 1]))
            prev_last_pub = pub0 + nidx - 1
        if not smut:
            for w in range(len(waves) - 1):
                a, b_ = waves[w], waves[w + 1]
                for i in range(2 * len(a["beat7"])):
                    assert a["publish"][0] + i < b_["beat7"][i // 2] + lq0, f"wave {w}: publish {i} after wave {w + 1}"
        s.exp = dict(waves=len(waves))
        s.end = waves[-1]["publish"][1] + lat["out"]
    else:
        F0 = s.last_consume + lat["pv_node"]
        st = lat["fold_step"]
        for j, (fa, fb) in enumerate(((0, 2), (4, 6), (1, 3), (5, 7))):
            cal.set(F0 + st * j, fold=1, fold_a=fa, fold_b=fb, **s.hold)
        for j, (fa, fb) in enumerate(((0, 4), (1, 5))):
            cal.set(F0 + lat["fold_l2"] + st * j, fold=1, fold_a=fa, fold_b=fb, **s.hold)
        pub = F0 + lat["fold_pub"]
        cal.set(pub, publish=1, folded=1, **s.hold)
        s.exp = dict(fold=F0, pv_publish=pub)
        s.end = pub + 64 + lat["out"]
        gap = lat["chain_gap"] - (40 if smut == "chainearly" else 0)
        s.release = pub + gap


def compile_chain(segs, lat, mb, tail, smut=""):
    for s in segs:
        s.tail_hook = (lambda cal, s_, lat_: tail(cal, s_, lat_, smut))
    cal = engine(segs, lat, smut=smut)
    end = max(s.end for s in segs)
    t_first = min(min(cal.kvd), min(cal.xw) if cal.xw else 10 ** 9)
    mode = segs[0].mode
    be_mode = (1 if segs[0].qk else 3) if segs[0].fmt == "ds" else (2 if segs[0].qk else 3)
    for cc in range(min(cal.kvd), end + 1):
        d = cal.at(cc)
        d.setdefault("mode", mode)
        if segs[0].h128:
            d.setdefault("h128", 1)
        d.setdefault("be_mode", be_mode)
    return cal, end, t_first


# ------------------------------------------------------------------------------------------------ build / run
DIE_DEFINES = AI.DIE_DEFINES + ["OT_SMH_ATTN_INT8"]


def build(work: Path, bundle: Path, dmut: int):
    obj = work / f"obj_d{dmut}"
    exe = obj / "Vtb_hbm_smh_attn"
    if exe.exists():
        return exe
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    tb = ROOT / "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv"
    srcs = AI.die_sources(bundle)
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--top-module", "tb_hbm_smh_attn", f"-GDMUT={dmut}", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in DIE_DEFINES] + \
          [f"-I{bundle / p}" for p in sorted({str(Path(s).parent.relative_to(bundle)) for s in srcs})] + \
          [str(s) for s in srcs] + [str(tb)]
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_d{dmut}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr +
                                             f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_d{dmut}.log)")
    return exe


def ds_check_seg(rec, s, out_words):
    """bit-exact check of one DS segment's result words (E.check semantics)"""
    exp = dict(s.exp)
    res = E.check(rec, (None, s.kind, s.kv4, s.rows, s.nrun), exp, "\n".join(
        f"R {c} {r:03x} {d:064x}" for c, r, d in out_words))
    return res


def r_words(out):
    return [(int(x[1]), int(x[2], 16), int(x[3], 16)) for x in (ln.split() for ln in out.splitlines()
                                                                 if ln.startswith("R "))]


def cmd_ds(a):
    rec, src = AI.load_ds(Path(a.kv), a.layer)
    lat = dict(E.DEFAULT_LAT, **MB_LAT)
    if a.lat:
        lat.update(json.loads(a.lat))
    lat["req_lead"] = a.req_lead or lat["req_lead"]
    mb = a.mode == "mb"
    sub = 0 if mb else a.subrun
    ops, nrun = AI.plan_d4g(rec, sub)
    allops = list(ops)
    sms = sorted({o[5] for o in ops})
    if a.sms:
        sms = [s for s in sms if s in {int(x) for x in a.sms.split(",")}]
    kinds = a.kinds.split(",") if a.kinds else ["qk", "pv"]
    work = Path(a.work).resolve()
    exe = build(work, Path(a.bundle).resolve(), a.dmut)
    jobs = []
    for s in sms:
        for kind in kinds:
            sops = [o for o in ops if o[5] == s and o[1] == kind]
            jobs.append((s, kind, sops))

    def run(job):
        s, kind, sops = job
        segs = [ds_segs(rec, o) for o in sops]
        tag = f"L{a.layer:02d}_{AI.SM_NAMES[s]}_{kind}_{a.mode}{('_s%d' % sub) if sub else ''}_d{a.dmut}" \
              f"{('_' + a.smut) if a.smut else ''}_{lat_tag(lat)}"
        if not mb:
            # base = the serial calendars exactly as att_images.py unit (one op per sim, spans summed + go bubble 5)
            res_ops, ok, words_all = [], True, []
            for o, sg in zip(sops, segs):
                cal, exp = E.compile_op(rec, o[:5], lat, kind == "pv", smut=a.smut)
                rc, out = hexdump_run(exe, cal, work / f"{tag}_{o[0]}", exp["end"] + 4)
                chk = E.check(rec, o[:5], exp, out)
                p = rc == 0 and "FAULT" not in out and chk["mismatches"] == 0 and chk["results"] == chk["expected"]
                ok &= p
                sp = (chk["last_result"] - first_word(cal)) if chk["last_result"] is not None else None
                spx = (chk["last_result"] - first_x(cal)) if chk["last_result"] is not None else None
                res_ops.append(dict(op=o[0], rc=rc, fault="FAULT" in out, span_first_word=sp, span_first_x=spx,
                                    words=exp["end"] + 1 - first_word(cal), **chk))
                if kind == "pv" and p:
                    words_all.append((o[6], r_words(out)))
            spans = [r["span_first_word"] for r in res_ops]
            tot = sum(x for x in spans if x is not None) + 5 * (len(spans) - 1)
            nodes = {k: AI.node_from_words(w).astype(np.uint32).view(F) for k, w in words_all}
            return dict(sm=AI.SM_NAMES[s], kind=kind, mode="base", pass_=ok, span=tot, ops=res_ops,
                        words_resident=max(r["words"] for r in res_ops), nodes=nodes, nsub=len(sops))
        cal, end, t_first = compile_chain(segs, lat, True, ds_tail, a.smut)
        rc, out = hexdump_run(exe, cal, work / tag, end + 4)
        words = r_words(out)
        sg = segs[0]
        chk = ds_check_seg(rec, sg, words)
        p = rc == 0 and "FAULT" not in out and chk["mismatches"] == 0 and chk["results"] == chk["expected"]
        lr = chk["last_result"]
        nodes = {0: AI.node_from_words(words).astype(np.uint32).view(F)} if (kind == "pv" and p) else {}
        return dict(sm=AI.SM_NAMES[s], kind=kind, mode="mb", pass_=p, rc=rc, fault="FAULT" in out,
                    span=(lr - first_x(cal)) if lr is not None else None,
                    span_first_word=(lr - first_word(cal)) if lr is not None else None,
                    prefetch=first_x(cal) - first_word(cal), words_resident=end + 1 - first_word(cal),
                    nodes=nodes, nsub=1, **chk)

    results = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r in ex.map(run, jobs):
            results.append(r)
            print(("PASS " if r["pass_"] else "FAIL ") + json.dumps({k: v for k, v in r.items() if k not in ("nodes", "ops")},
                                                                     default=int), flush=True)
    merged = None
    pvn = {}
    for r in results:
        if r["kind"] == "pv":
            for k, v in r["nodes"].items():
                pvn[(AI.SM_NAMES.index(r["sm"]), k)] = v
    keys = sorted({(o[5], o[6]) for o in allops if o[1] == "pv"})
    if keys and all(k in pvn for k in keys):
        pad = AI.merge_pad(rec, allops)
        mm = AI.pv_merge([pvn[k] for k in keys], pad)
        merged = dict(nodes=len(keys), pad=pad, equals_fixture_pv=bool(np.array_equal(AI.zb(mm), AI.zb(rec["pv"]))))
    busiest = {}
    for r in results:
        if r["span"] is not None:
            busiest[r["kind"]] = max(busiest.get(r["kind"], 0), r["span"])
    summ = dict(lane="HBM-ATTN-MB", design="DS", layer=a.layer, mode=a.mode, subrun=sub, nrun=nrun, lat=lat,
                dmut=a.dmut, smut=a.smut, sms=[AI.SM_NAMES[s] for s in sms], busiest_span=busiest, cross_sm_merge=merged,
                passed=sum(r["pass_"] for r in results), runs=len(results), source=src,
                rtl="ot_hbm_accel_smh_attn (bundle master_files.json, defines " + ",".join(DIE_DEFINES) + ")",
                verdict="PASS" if results and all(r["pass_"] for r in results) and
                (merged is None or merged["equals_fixture_pv"]) else "FAIL")
    for r in results:
        r.pop("nodes", None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, runs=results), indent=1, default=int))
    print(summ["verdict"] + " HBM_ATTN_MB_DS " + json.dumps({k: v for k, v in summ.items() if k != "source"}, default=int))
    return 0 if summ["verdict"] == "PASS" else 1


def cmd_qwen(a):
    rec, src = QU.load_qwen(Path(a.kv), a.stage, a.L)
    ops = QU.plan(rec)
    lat = dict(QU.DEFAULT_LAT, **MB_LAT)
    if a.calib and Path(a.calib).exists():
        cb = json.loads(Path(a.calib).read_text())
        lat.update(q_land_min=cb["q_land_min"], q_land_max=cb["q_land_max"])
    if a.lat:
        lat.update(json.loads(a.lat))
    lat["req_lead"] = a.req_lead or lat["req_lead"]
    if "q_land_min" not in lat:
        raise SystemExit("--calib (qwen_att_unit probe calibration json) or --lat q_land_min/q_land_max required")
    mb = a.mode == "mb"
    sms = list(range(QU.NSM))
    if a.sms:
        sms = [int(x) for x in a.sms.split(",")]
    kinds = a.kinds.split(",") if a.kinds else ["qk", "pv"]
    work = Path(a.work).resolve()
    exe = build(work, Path(a.bundle).resolve(), a.dmut)
    jobs = [(s, k) for s in sms for k in kinds]
    blocks_f = {int(x) for x in a.blocks.split(",")} if a.blocks else None

    def run(job):
        s, kind = job
        sops = [o for o in ops if o["sm"] == s and o["kind"] == kind and
                (kind == "qk" or blocks_f is None or o["block"] in blocks_f)]
        tag = f"{a.stage}_L{a.L}_{QU.SM_NAMES[s]}_{kind}_{a.mode}_d{a.dmut}{('_' + a.smut) if a.smut else ''}" \
              f"_{lat_tag(lat)}"
        nodes = {}
        if not mb:
            res_ops, tot, ok = [], 0, True
            for o in sops:
                cal, exp = QU.compile_q(rec, o, lat, smut=a.smut)
                rc, out = hexdump_run(exe, cal, work / f"{tag}_{o['name']}", exp["end"] + 4)
                chk, node = QU.check(rec, o, exp, out)
                p = rc == 0 and "FAULT" not in out and chk["mismatches"] == 0 and chk["results"] == chk["expected"]
                ok &= p
                sp = (chk["last_result"] - first_word(cal)) if chk["last_result"] is not None else None
                res_ops.append(dict(op=o["name"], rc=rc, fault="FAULT" in out, span_first_word=sp,
                                    span_first_x=(chk["last_result"] - first_x(cal)) if sp is not None else None,
                                    words=exp["end"] + 1 - first_word(cal), **chk))
                tot += sp or 0
                if node is not None:
                    nodes[o["block"]] = node
            return dict(sm=QU.SM_NAMES[s], kind=kind, mode="base", pass_=ok, span=tot, ops=res_ops, nodes=nodes,
                        words_resident=max(r["words"] for r in res_ops), nblocks=len(sops))
        segs = [qw_seg(rec, o) for o in sops]
        cal, end, t_first = compile_chain(segs, lat, True, qw_tail, a.smut)
        rc, out = hexdump_run(exe, cal, work / tag, end + 4)
        words = r_words(out)
        ok = rc == 0 and "FAULT" not in out
        per = []
        if kind == "qk":
            chk, _n = QU.check(rec, sops[0], {}, out)
            ok &= chk["mismatches"] == 0 and chk["results"] == chk["expected"]
            per.append(chk)
        else:
            # split the publication words by block: block k's 64 words precede block k+1's (chain law)
            for k, o in enumerate(sops):
                wk = words[64 * k:64 * (k + 1)]
                chk, node = QU.check(rec, o, {}, "\n".join(f"R {c} {r:03x} {d:064x}" for c, r, d in wk))
                ok &= chk["mismatches"] == 0 and chk["results"] == chk["expected"]
                per.append(dict(block=o["block"], **chk))
                if node is not None:
                    nodes[o["block"]] = node
            ok &= len(words) == 64 * len(sops)
        lr = words[-1][0] if words else None
        return dict(sm=QU.SM_NAMES[s], kind=kind, mode="mb", pass_=ok, rc=rc, fault="FAULT" in out,
                    fault_line=next((ln for ln in out.splitlines() if "FAULT" in ln), None),
                    span=(lr - first_x(cal)) if lr is not None else None,
                    span_first_word=(lr - first_word(cal)) if lr is not None else None,
                    prefetch=first_x(cal) - first_word(cal), words_resident=end + 1 - first_word(cal),
                    nblocks=len(sops), per_block=per, nodes=nodes,
                    block_periods=[segs[k + 1].beats[0][0] - segs[k].beats[0][0] for k in range(len(segs) - 1)])

    results = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r in ex.map(run, jobs):
            results.append(r)
            print(("PASS " if r["pass_"] else "FAIL ") + json.dumps({k: v for k, v in r.items() if k not in ("nodes", "ops", "per_block")},
                                                                     default=int), flush=True)
    merged = None
    nodes = {}
    for r in results:
        nodes.update(r["nodes"])
    nblk = rec["K"].shape[0] // QU.BLK
    if len(nodes) == nblk:
        mm = []
        for h in range(QU.HEADS):
            m_ = B.A.pairwise([nodes[b][h] for b in range(nblk)])
            mm.append(int(np.sum(B.zbits(m_) != B.zbits(rec["pv"][h]))))
        merged = dict(blocks=nblk, equals_fixture_pv=all(x == 0 for x in mm), mismatches_per_head=mm)
    busiest = {}
    for r in results:
        if r["span"] is not None:
            busiest[r["kind"]] = max(busiest.get(r["kind"], 0), r["span"])
    summ = dict(lane="HBM-ATTN-MB", design="Qwen", stage=a.stage, L=a.L, mode=a.mode, lat=lat, dmut=a.dmut, smut=a.smut,
                sms=[QU.SM_NAMES[s] for s in sms], busiest_span=busiest, cross_block_merge=merged,
                passed=sum(r["pass_"] for r in results), runs=len(results), source=src,
                kv_heads_per_die=1, q_heads_per_die=QU.HEADS,
                rtl="ot_hbm_accel_smh_attn (bundle master_files.json, defines " + ",".join(DIE_DEFINES) + ")",
                verdict="PASS" if results and all(r["pass_"] for r in results) and
                (merged is None or merged["equals_fixture_pv"]) else "FAIL")
    for r in results:
        r.pop("nodes", None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, runs=results), indent=1, default=int))
    print(summ["verdict"] + " HBM_ATTN_MB_QWEN " + json.dumps({k: v for k, v in summ.items() if k != "source"}, default=int))
    return 0 if summ["verdict"] == "PASS" else 1


# ------------------------------------------------------------------------------------------------ campaign
def _run(args, log):
    r = subprocess.run([sys.executable, str(Path(__file__).resolve())] + args, capture_output=True, text=True)
    Path(log).write_text(" ".join(args) + "\n" + r.stdout + r.stderr + f"\nRC {r.returncode}\n")
    return r.returncode


def _summ(path):
    try:
        return json.loads(Path(path).read_text())["summary"]
    except Exception:  # noqa: BLE001
        return None


def cmd_campaign(a):
    """calibrate (SM 0 sweeps: smallest passing latency), then full before/after runs + negative controls."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    W = Path(a.work)
    dsc = ["ds", "--kv", a.kv_ds, "--layer", str(a.layer), "--bundle", a.bundle, "--jobs", str(a.jobs)]
    qwc = ["qwen", "--kv", a.kv_qw, "--stage", a.stage, "--L", str(a.L), "--bundle", a.bundle, "--jobs", str(a.jobs)]
    pool = cf.ThreadPoolExecutor(a.jobs)
    # 0. builds (d0 shared by every run of a work dir; KVMUT 2 for the converter negative control) + Qwen QK calibration
    calib = W / "qprobe" / f"calib_{a.stage}_L{a.L}.json"

    def probe():
        if calib.exists():
            return 0
        r = subprocess.run([sys.executable, str(HERE / "qwen_att_unit.py"), "run", "--kv", a.kv_qw, "--stage", a.stage,
                            "--L", str(a.L), "--bundle", a.bundle, "--work", str(W / "qprobe"), "--out",
                            str(out / "qwen_probe_qk_sm0.json"), "--sms", "0", "--kinds", "qk"],
                           capture_output=True, text=True)
        (out / "qwen_probe_qk_sm0.log").write_text(r.stdout + r.stderr)
        return r.returncode
    bf = [pool.submit(build, W / "w", Path(a.bundle).resolve(), d) for d in (0, 2)] + [pool.submit(probe)]
    for f in bf:
        f.result()
    qwc += ["--calib", str(calib)]
    # 1. sweeps on SM 0 (all in parallel)
    sweeps = dict(
        ds_qk_x=[("ds", ["--sms", "0", "--kinds", "qk"], dict(x_lead=v)) for v in (0, 2, 4, 8)],
        ds_pv_node=[("ds", ["--sms", "0", "--kinds", "pv"], dict(pv_node=v)) for v in (60, 80, 100, 120, 140, 160)],
        qw_qk_x=[("qw", ["--sms", "0", "--kinds", "qk"], dict(x_lead=v)) for v in (8, 10, 12, 16, 20, 24, 32)],
        qw_pv=[("qw", ["--sms", "0", "--kinds", "pv"], dict(pv_node=n, chain_gap=g))
               for n in (80, 100, 120, 160) for g in (40, 60, 80, 100)],
    )
    futs = {}
    for key, lst in sweeps.items():
        for i, (d, extra, lt) in enumerate(lst):
            nm = f"sweep_{key}_{i}"
            base = dsc if d == "ds" else qwc
            args = base + ["--mode", "mb", "--work", str(W / "w"), "--out", str(out / f"{nm}.json"),
                           "--lat", json.dumps(lt), "--jobs", "1"] + extra
            futs[pool.submit(_run, args, out / f"{nm}.log")] = (key, lt, out / f"{nm}.json")
    table = {}
    for fu in cf.as_completed(futs):
        key, lt, j = futs[fu]
        s = _summ(j)
        table.setdefault(key, []).append(dict(lat=lt, verdict=s and s["verdict"], busiest=s and s["busiest_span"]))
    chosen = {}
    for key, rows in table.items():
        ok = [r for r in rows if r["verdict"] == "PASS"]
        if not ok:
            continue
        best = min(ok, key=lambda r: (min(r["busiest"].values()), json.dumps(r["lat"])))
        chosen[key] = best["lat"]
    (out / "sweep.json").write_text(json.dumps(dict(table=table, chosen=chosen), indent=1))
    ds_lat = dict(chosen.get("ds_qk_x", {}), **chosen.get("ds_pv_node", {}))
    qw_lat = dict(chosen.get("qw_qk_x", {}), **chosen.get("qw_pv", {}))
    # 2. full before / after + 3. negative controls (each must FAIL) + 4. deep request lead (HBM loaded latency)
    runs = dict(
        ds_base=(dsc, ["--mode", "base", "--subrun", "32"], {}),
        ds_mb=(dsc, ["--mode", "mb"], ds_lat),
        qw_base=(qwc, ["--mode", "base"], {}),
        qw_mb=(qwc, ["--mode", "mb"], qw_lat),
        ds_mb_rl300=(dsc, ["--mode", "mb", "--sms", "0", "--req-lead", "300"], dict(ds_lat, pre=380)),
        qw_mb_rl300=(qwc, ["--mode", "mb", "--sms", "0", "--req-lead", "300"], dict(qw_lat, pre=380)),
        mut_ds_xearly=(dsc, ["--mode", "mb", "--sms", "0", "--kinds", "qk", "--smut", "xearly"], ds_lat),
        mut_ds_early=(dsc, ["--mode", "mb", "--sms", "0", "--kinds", "qk", "--smut", "early"], ds_lat),
        mut_ds_kv2=(dsc, ["--mode", "mb", "--sms", "0", "--kinds", "pv", "--dmut", "2"], ds_lat),
        mut_qw_chainearly=(qwc, ["--mode", "mb", "--sms", "0", "--kinds", "pv", "--smut", "chainearly"], qw_lat),
        mut_qw_pwar=(qwc, ["--mode", "mb", "--sms", "0", "--kinds", "pv", "--smut", "pwar"], qw_lat),
        mut_qw_xearly=(qwc, ["--mode", "mb", "--sms", "0", "--kinds", "qk", "--smut", "xearly"], qw_lat),
        mut_qw_kv2=(qwc, ["--mode", "mb", "--sms", "0", "--kinds", "pv", "--dmut", "2"], qw_lat),
    )
    futs = {}
    for nm, (base, extra, lt) in runs.items():
        args = base + extra + ["--work", str(W / "w"), "--out", str(out / f"{nm}.json"), "--lat", json.dumps(lt),
                               "--jobs", "4"]
        futs[pool.submit(_run, args, out / f"{nm}.log")] = nm
    res = {}
    for fu in cf.as_completed(futs):
        nm = futs[fu]
        s = _summ(out / f"{nm}.json")
        res[nm] = dict(rc=fu.result(), verdict=s and s["verdict"], busiest=s and s["busiest_span"],
                       merge=s and (s.get("cross_sm_merge") or s.get("cross_block_merge")))
    neg_ok = all(res[k]["verdict"] != "PASS" for k in res if k.startswith("mut_"))
    pos_ok = all(res[k]["verdict"] == "PASS" for k in res if not k.startswith("mut_"))
    doc = dict(lane="HBM-ATTN-MB", chosen=dict(ds=ds_lat, qwen=qw_lat), runs=res, positives_pass=pos_ok,
               negatives_fail=neg_ok, verdict="PASS" if pos_ok and neg_ok else "FAIL")
    (out / "campaign.json").write_text(json.dumps(doc, indent=1, default=int))
    print(doc["verdict"] + " HBM_ATTN_MB_CAMPAIGN " + json.dumps(doc, default=int))
    return 0 if doc["verdict"] == "PASS" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("ds", "qwen"):
        p = sub.add_parser(nm)
        p.add_argument("--kv", required=True)
        p.add_argument("--bundle", required=True)
        p.add_argument("--work", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--mode", choices=["base", "mb"], default="mb")
        p.add_argument("--sms", default="")
        p.add_argument("--kinds", default="")
        p.add_argument("--dmut", type=int, default=0)
        p.add_argument("--smut", default="", choices=["", "early", "xearly", "chainearly", "pwar"])
        p.add_argument("--lat", default="")
        p.add_argument("--req-lead", type=int, default=0)
        p.add_argument("--jobs", type=int, default=8)
        if nm == "ds":
            p.add_argument("--layer", type=int, default=2)
            p.add_argument("--subrun", type=int, default=32)
        else:
            p.add_argument("--stage", default="L0")
            p.add_argument("--L", type=int, default=0)
            p.add_argument("--calib", default="")
            p.add_argument("--blocks", default="")
    p = sub.add_parser("campaign")
    for k in ("--kv-ds", "--kv-qw", "--bundle", "--work", "--out"):
        p.add_argument(k, required=True)
    p.add_argument("--layer", type=int, default=2)
    p.add_argument("--stage", default="L0")
    p.add_argument("--L", type=int, default=0)
    p.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args(argv)
    if a.cmd == "campaign":
        return cmd_campaign(a)
    if a.smut == "xearly":
        a.lat = json.dumps(dict(json.loads(a.lat or "{}"), x_lead=-40))
    return {"ds": cmd_ds, "qwen": cmd_qwen}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
