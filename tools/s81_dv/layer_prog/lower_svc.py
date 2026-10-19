#!/usr/bin/env python3
"""LB2-S81/CC-svc (10-18): lowering of the attention pass onto the 16 regional service slices dsdv_svc_rs (die.v
u_rsv_00 .. u_rsv_15; entries u_rsv_05 W / u_rsv_11 E) -- the svc ATTENTION-JOB ABI.

One svc job per layer = one seq_host calendar row of engine 4 + one q-frame stream on both entry q pins + the HBM
window image.  Every field is the decode of the BUILT RTL (main f93fea12a+, credit-free svc_rs):

  job word (seq_host engine 4 -> s_j -> entry j pin), rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv:4-17, 91-93:
      j = {v, arg 24, tag 8};  arg[4:0] = END sources (1: source 0 = the entry's synthetic END word,
      dsdv_svc_rs.sv:294-295), arg[14:7] = q-frame count, arg[6:5] = arg[23:15] = 0 (else fault);
      tag = {issuer context slot, calendar row index} (rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host.sv:222,
      ot_dsdv_fixed_issue.sv:170 OP_BASE 0): every q-frame header must carry the job's tag (ot_s81_svc_job.sv:45).
  q-frame header (512-b word, SVC FRAME PROTOCOL v1.1; dsdv_svc_att.sv:125-138, ot_s81_svc_job.sv:7-9):
      [511:508] type, [507] END (the job's last frame), [506:503] mask (bit 0 = this die's slices), [502:495] tag,
      [491:480] len (payload words), [479:459] pos / 21-b field, [458:449] user, [448:0] spec.
  frames (dsdv_svc_att.sv:17-31 + decode lines):
      12 CFG      spec[29:0] WB (window ring base), [32] ST valid, [31:30] ST (G10: the die's stack position)
       3 OWN_ROW  [465:459] slot = pos mod 128, [458:449] user; 16 words {scale 8, codes 256} (word t -> tile t):
                  codes -> sector WB + 68 u + slot[6:1] on PC slot[0]; scale byte slot[4:0] of sector
                  WB + 68 u + 64 + slot[6] on PC slot[5]                            dsdv_svc_att.sv:177-193
       2 WIN_LOAD spec[29:0] SB, [88:81] wcount, [98:89] nsel, [119:99] first window pos, [458:449] user, tag
                                                                                     dsdv_svc_att.sv:152-153, 239
       1 ATTN_Q   spec[448] = half b; 128 words, word r = head 8 b + r / 16, dims 32 (r % 16) .. +31 (BF16)
       9 SMJ      spec[0] start, [4:1] kind (4 = SE), [12:5] jid; 2 parameter rows: row 0 {[13:0] obase, [64 +: 7]
                  nv = ceil(T / 16), [96 +: 32] scale, [128 +: 3] lt = log2(nv)}, row 1 sinks [32 h +: 32]
                                                                       rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv:12-13, 95
      13 GO       len 0, spec[15:0] PO (p-feed start), [31:16] PVO (P.V drain base), [47:32] PIO (on-die P injection
                  start; TOK-S81-GAPS/SVCP 10-19), cycles after the share start
       5 PV       p words: word w = rows 2 w, 2 w + 1, head h at bits 16 (j 16 + h) (BF16) -- ON-DIE since SVCP
                  (PPATH): the SM e rows -> BF16 -> score-exchange P beats -> fold root rsv_09 packs this frame -> both
                  entries put it on their dn stream (dsdv_svc_rs.sv P PATH); the host sends no PV frame.  PPATH False =
                  the legacy host PV frame (bench reference only)
  static rules (no credit / ready; dsdv_svc_att.sv:33-58, tb_dsdv_svc_rs.sv build_frames):
      PV send >= GO + ceil(5 T / 4) + 150 (after the last fold score); PO = PVS + ceil(n / 2) + ceil(n / 250) + 4,
      n = ceil(T / 2); PVO = PO + 8 ceil(T / 32) + 55; the quarter-ST P.V leaves the entry of half PVH (ST < 2: E)
      as 160 words in 4 x 40-cycle windows from GO + PVO + 56 (fixed: SVC-PV3 logs, every T and seed); the jobs'
      done pulse at the P.V entry's jd one edge after the last P.V word, at the other entry pv_first - 6 (measured).
  HBM (elastic boundary, owner 10-15): the window ring of the 127 rows before this position is the compiler's image
  in each slice's own 2 PCs (tile t = dims 32 t .. 32 t + 31; rs_role tile map, dsdv_svc_rs_roles.svh); the own row
  is written by the job's OWN_ROW frame; GO waits W_SLACK edges after WIN_LOAD (64 sector reads a PC at DQ 8 credits).

Status (L0, sliding window, TP4 rank 0 = heads 0..15):
  attn.own_row_write / window_load / scores: LOWERED with the committed slice-set bench
      (results/rtl/s81_layer_tput_1018/compiler/bench_svc: the 16 real dsdv_svc_rs, the images and cycles emitted here,
      bit-exact vs the L0 fixtures).
  attn.max / exp: LOWERED (TOK-S81-GAPS/SVCP 10-19, PPATH): the SE job's e rows feed the on-die P path (SM -> BF16
      pbuf -> score-exchange P beats -> fold root PV frame -> entries' dn stream -> owners' p feed); bench_svc_p checks
      every P word at the root and on both entries' dn streams = bf16(fixture attn.exp) and the P.V bit-exact.
  attn.den / sink: PARTIAL -- computed on-die by the same SE job (SM head), consumed only by the SO normalisation.
  attn.normalize: GAP G9b -- the SO job's o rows leave only on w_* (no on-die consumer; the SO operand rows = P.V by
      head would come back as SMJ frames from the slice band, and the other 3 quarters need the cross-die exchange).
  attn.pv: PARTIAL -- the P.V words of quarter ST are bit-exact; ST is now the CFG field (G10 strap part fixed), but
      the other 3 quarters of the rank's 512 dims reach wo_a only through an unpriced cross-die exchange (G10).
  The q words reach the entry q pins from u_s_3S (W) / u_s_4S (E) ot_s81sl_xr band bo (pk[511:0], same cycle on both
  sides); producing those rows (header rows + q / own-row payload) is the slice families' send programme.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / 'tools', ROOT / 'tools/s81_dv', ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

OPS = [r'^attn\.(own_row_write|window_load|scores|max|exp|den|sink|pv|normalize)$']
BENCH = 'results/rtl/s81_layer_tput_1018/compiler/bench_svc'
BENCH_P = 'results/rtl/s81_layer_tput_1018/compiler/bench_svc_p'   # TOK-S81-GAPS/SVCP: on-die P path (PPATH)
UNIT = 'svc_rs x16 (u_rsv_00..15; entries u_rsv_05 W / u_rsv_11 E) + seq_host engine 4'
INSTS = [f'u_rsv_{i:02d}' for i in range(16)] + ['u_seqhost']

H, D, TD, WIN = 16, 512, 32, 128
WB, SB, USER = 0x100, 0x1000, 3
ST = 0                       # the die's stack position, sent in the CFG frame ([32] valid, [31:30]) -- G10
PVS0, KPV, PV_LAT = 150, 55, 56
PPATH = True                 # TOK-S81-GAPS/SVCP: P is produced on-die (GO PIO != 0); False = legacy host PV frame
# on-die P path constants (share cycles; measured by tb_svc_lower, results/rtl/s81_layer_tput_1018/compiler/bench_svc_p):
#   PIO = PIO0 + 5 ceil(T / 4) / 4 ... see p_sched(); PO = PIO + P_ARR + ceil(n / 2) + P_PO_M; PVO = PO + 8 ceil(T / 32) + KPV
# measured 10-19 (bench_svc_p sweep, out_p1 build src 85340f61a, T 128, GO 1555): SM e rows land GO+283..GO+305; the
# P beats read pbuf from PIO+75 (2 edges/beat) -> PIO0 270 FAIL (P read before the first e row), 285 PASS; the PV frame
# reaches the owners PIO+90 (W) / +85 (E) -> P_ARR 60 FAIL (PO before the frame: fault 00104000), 70 PASS.  Tight = 285 / 70.
PIO0, P_ARR, P_PO_M, PIO_EARLY = 285, 70, 8, 150
W_SLACK = 560                # WIN_LOAD -> GO: 64 code + 2 scale reads a PC at DQ 8 credits x <= 56-edge latency + margin
Q_ARM = 4                    # j pin -> first q header (job pin flop + table push, ot_s81_svc_job.sv:31-32, 91-92)
JD_LAT = 1                   # last P.V word at the pv pin -> jd done pulse (SVC-PV3 logs: end = pv_last + 1)
JD_NOPV = -6                 # the half without the quarter's P.V: jd done = pv_first - 6 (bench_svc run1, both seeds)

ROLE = {0: 0x01990c, 1: 0x04124d, 2: 0x04110f, 3: 0x040ace, 4: 0x040908, 5: 0x0400e9, 6: 0x01910b, 7: 0x040c4a,
        8: 0x055102, 9: 0x054a43, 10: 0x054900, 11: 0x0540e4, 12: 0x055101, 13: 0x054c65, 14: 0x02d906, 15: 0x02d447}


QF_PRODUCER_GAP = ('the q words reach the entry q pins from u_s_3S (W) / u_s_4S (E) ot_s81sl_xr band bo; the slice send '
                   'programme of the svc q stream (frame header rows + q / own-row payload rows) is not compiled, so a '
                   'cut holding the producer slice cannot be checked for these words (a cut holding the svc entry is '
                   'driven with them)')


def tile_of(sid):
    return ROLE[sid] & 15


def hdr(typ, ln, tag, spec=0, pos=777, user=USER, end=False, mask=1):
    """q-frame header word (tb_dsdv_svc_rs.sv hdr(); field decode dsdv_svc_att.sv:125-138)"""
    w = (typ & 15) << 508 | int(end) << 507 | (mask & 15) << 503 | (tag & 255) << 495 | (ln & 4095) << 480
    return w | (pos & ((1 << 21) - 1)) << 459 | (user & 1023) << 449 | (spec & ((1 << 449) - 1))


def job_word(nframes, tag):
    """s_j / entry j = {v, arg 24, tag 8}: arg[4:0] = 1 (END source 0), arg[14:7] = q frames (ot_s81_svc_job.sv:91-93)"""
    assert 0 < nframes < 256
    arg = (nframes << 7) | 1
    return arg, (1 << 32) | (arg << 8) | (tag & 255)


def f32bits(x):
    return np.asarray(x, dtype=np.float32).view(np.uint32).astype(np.int64)


class Job:
    """the layer's svc attention job, built once per (layer, fixtures, tag, mutant)"""

    def __init__(self, fx, tag=0, mutant=None):
        import rtl_hdc_v41x_attn_campaign as C
        self.C, V = C, C.V
        fx = Path(fx)
        self.meta = json.loads((fx / 'meta.json').read_text())
        files = json.loads((fx / 'files.json').read_text())
        ops = json.loads((fx / 'ops.json').read_text())

        def ld(rel, info):
            a = np.fromfile(fx / rel, dtype=np.dtype(info['dtype']))
            assert hashlib.sha256((fx / rel).read_bytes()).hexdigest() == info['sha256'], rel
            return a.reshape(info['shape'])

        def op(n):
            return ld(f'ops/{n}.bin', ops[n])
        assert self.meta['kind'] == 'sliding', 'window-only layers (compressed-row selection not lowered here)'
        h0, h1 = self.meta['tp_split']['heads'][self.meta['rank']]
        assert h1 - h0 == H
        self.h0 = h0
        pos = int(self.meta['position'])
        self.pos, self.wfirst = pos, pos - (WIN - 1)
        codes = ld('state/kv.window.codes.bin', files['state/kv.window.codes.bin']).astype(np.int64)   # [127, 512]
        e8 = ld('state/kv.window.scale.bin', files['state/kv.window.scale.bin']).astype(np.int64)       # [127, 16]
        own = op('attn.own_row_write')
        oc, os16 = C.fp8_row_codes(own)
        self.codes = np.vstack([codes, oc[None]])
        self.e8 = np.vstack([e8, os16[0::2][None]])                                                   # [128, 16]
        q = op('attn.q_rope')[h0:h1]
        e = op('attn.exp')[h0:h1]
        T = WIN
        job = C.Job(q, np.zeros(T, np.int64), self.codes, np.repeat(self.e8, 2, axis=1), V.to_bf16(e), 'L0 svc')
        kvm = job.kvm()
        # anchors: the job's stored rows are the fixture's window rows; the engine products scaled = the fixture ops
        assert np.array_equal(V.bits(kvm), V.bits(op('attn.window_load'))), 'window rows'
        sc, pv = job.expected()
        scale = np.float32(self.meta.get('attn_scale', D ** -0.5))
        self.anchor = dict(
            scores=bool(np.array_equal(V.bits(V.mul(sc, scale)), V.bits(op('attn.scores')[h0:h1]))),
            pv=bool(np.array_equal(V.bits(pv), V.bits(op('attn.pv')[h0:h1]))),
            window=True, q_bf16=bool(np.all((C.u32(q) & 0xFFFF) == 0)))
        assert all(self.anchor.values()), self.anchor
        self.T, self.q, self.p, self.sc, self.pv, self.scale = T, q, V.to_bf16(e), sc, op('attn.pv')[h0:h1], scale
        self.sink = op('attn.sink')  # (den + exp(sink - max)); the raw sink weights are the SMJ row 1
        sw = np.fromfile(fx / 'weights/attn_sink.bin', dtype=np.float32)
        assert files['weights/attn_sink.bin']['rows'] == [h0, h1]
        self.sinkw = sw
        self.tag, self.mutant = tag, mutant
        self.frames = self._frames()

    # ------------------------------------------------------------------ q frames
    def _frames(self):
        C, T, tag, mut = self.C, self.T, self.tag, self.mutant
        fr = []
        fr.append(('CFG', [hdr(12, 0, tag, spec=WB | (1 << 32) | ((ST & 3) << 30))]))
        ow = []
        pos = self.pos - 1 if mut == 'slot' else self.pos             # MUTANT 'slot': wrong OWN_ROW pos field
        ow.append(hdr(3, 16, tag, pos=pos))
        for b in range(16):
            cw = sum(int(self.codes[T - 1, 32 * b + x]) << (8 * x) for x in range(32))
            ow.append(cw | int(self.e8[T - 1, b]) << 256)
        fr.append(('OWN_ROW', ow))
        fr.append(('WIN_LOAD', [hdr(2, 0, tag, spec=SB | (T << 81) | (0 << 89) | (self.wfirst << 99))]))
        qb = C.bf16_bits(self.q)                                                                       # [16, 512]
        for b in range(2):
            ws = [hdr(1, 128, tag, spec=b << 448)]
            for r in range(128):
                h, c = 8 * b + r // 16, r % 16
                ws.append(sum(int(qb[h, 32 * c + k]) << (16 * k) for k in range(32)))
            fr.append((f'ATTN_Q{b}', ws))
        nv = -(-T // 16)
        r0 = (0 & 0x3FFF) | (nv << 64) | (int(f32bits(self.scale)) << 96) | ((nv - 1).bit_length() << 128)
        r1 = sum(int(f32bits(self.sinkw[h])) << (32 * h) for h in range(H))
        fr.append(('SMJ', [hdr(9, 2, tag, spec=1 | (4 << 1) | (0x21 << 5)), r0, r1]))
        fr.append(('GO', None))                                                                        # filled by schedule
        pb = C.bf16_bits(self.p)                                                                       # [16, T]
        self.p_bits = pb
        n = -(-T // 2)
        pw = []
        for w in range(n):
            word = 0
            for jj in range(2):
                t = 2 * w + jj
                if t < T:
                    for h in range(H):
                        word |= int(pb[h, t]) << (16 * (jj * H + h))
            pw.append(word)
        assert n <= 250
        self.p_words = [hdr(5, n, tag, pos=0, user=0)] + pw    # the PV frame as the fold root packs it (on-die)
        if not PPATH:
            fr.append(('PV', [hdr(5, n, tag, end=True)] + pw))
        return fr

    # ------------------------------------------------------------------ static schedule (cycles at the entry q pins)
    def schedule(self, t_q0, t_q, t_exp, j_age_w, j_age_e):
        """t_q0: the CFG word's cycle (own row ready), t_q: q_rope done, t_exp: P (exp) ready -- all at the q pins.
        Returns {frame: first word cycle} and the job's derived cycles."""
        T = self.T
        n = -(-T // 2)
        t = t_q0
        at, words, fw = {}, [], {}
        go_min = None
        for name, ws in self.frames:
            if name.startswith('ATTN_Q') and name.endswith('0'):
                t = max(t, t_q)
            if name == 'GO':
                go = max(t, go_min)
                pio = 0
                if PPATH:
                    # on-die P: PIO after the SM's last e row (measured), the PV frame reaches the owners P_ARR after
                    # PIO, one word a cycle.  MUTANT 'pio_early': the GO frame's PIO PIO_EARLY cycles early, PO / PVO
                    # unchanged (the first P beats find no e row in pbuf: sticky slice fault)
                    pio = PIO0
                    pvs = pio
                    po = pio + P_ARR + -(-n // 2) + P_PO_M
                    if self.mutant == 'pio_early':
                        pio -= PIO_EARLY
                else:
                    pvs = max(-(-5 * T // 4) + PVS0, t_exp - go)
                    po = pvs + -(-n // 2) + -(-n // 250) + 4
                pvo = po + 8 * -(-T // 32) + KPV
                ws = [hdr(13, 0, self.tag, spec=(po & 0xFFFF) | ((pvo & 0xFFFF) << 16) | ((pio & 0xFFFF) << 32))]
                self.pio = pio
                t = go
                self.go, self.pvs, self.po, self.pvo = go, pvs, po, pvo
            if name == 'PV':
                t = self.go + self.pvs + (40 if self.mutant == 'late' else 0)   # MUTANT 'late': PV frame 40 edges late
            at[name] = t
            fw[name] = [(t + k, w) for k, w in enumerate(ws)]
            for k, w in enumerate(ws):
                words.append((t + k, w))
            if name == 'WIN_LOAD':
                go_min = t + W_SLACK
            t += len(ws)
        j_pin = t_q0 - Q_ARM
        s_j = j_pin - max(j_age_w, j_age_e)
        pv_first = self.go + self.pvo + PV_LAT
        return dict(at=at, words=words, frame_words=fw, s_j=s_j, j_w=s_j + j_age_w, j_e=s_j + j_age_e, go=self.go, pvs=self.pvs,
                    po=self.po, pvo=self.pvo, pv_first=pv_first, pv_last=pv_first + 159,
                    done=pv_first + 160 - 1 + JD_LAT, done_nopv=pv_first + JD_NOPV, nframes=len(self.frames))

    # ------------------------------------------------------------------ HBM window image (the 127 rows before pos)
    def hbm_image(self):
        img = {}
        ring = WB + 68 * USER
        for r in range(self.T - 1):
            slot = (self.wfirst + r) & 127
            for sd in range(16):
                t = tile_of(sd)
                cw = sum(int(self.codes[r, 32 * t + x]) << (8 * x) for x in range(32))
                img[((2 * sd + (slot & 1)) << 32) | (ring + (slot >> 1))] = cw
                k = ((2 * sd + ((slot >> 5) & 1)) << 32) | (ring + 64 + (slot >> 6))
                img[k] = img.get(k, 0) | int(self.e8[r, t]) << (8 * (slot & 31))
        return img

    def expected_hex(self):
        C = self.C
        sc = [C.pack_vals(self.sc[:, t]) for t in range(self.T)]
        pv = [C.pack_vals(self.pv[:, d]) for d in range(D)]
        return sc, pv


def pv_words(job, s):
    """the quarter-ST P.V stream at the P.V entry's {pv_d 513, pv_v} pins: 160 words back to back from pv_first (the
    register set at edge pv_first - 1): per tile t (4 ST + w // 40) 8 beats of 5 words; word 0 = header {1, 440'd0,
    pv_c 8, flags 64} (dsdv_svc_att.sv:349-350), words 1..4 = {0, 16 heads x 32 b} of dims 32 t + 8 (wi - 1) + pv_c
    (tb_svc_lower decode).  Values: pv_c = the beat index (engine column order -- tb_svc_lower READS pv_c, it does not
    assert it, so pv_c and the data are masked in the check; the value is what a consumer cut is driven with)"""
    C = job.C
    pv = job.pv                                                     # [16 heads, 512 dims] FP32 (fixture attn.pv)
    vals = C.u32(pv) if hasattr(C, 'u32') else np.asarray(pv, np.float32).view(np.uint32)
    out, e0 = [], s['pv_first'] - 1
    hm = 1 | (1 << 513) | (((1 << 441) - 1) << 73)                 # v, pv_d[512], pv_d[511:72]
    dm = 1 | (1 << 513)
    for w in range(160):
        t, b, wi = 4 * ST + w // 40, (w % 40) // 5, w % 5
        if wi == 0:
            d = (1 << 512) | (b << 64)
            m = hm
        else:
            d = 0
            for h in range(H):
                d |= int(vals[h, 32 * t + 8 * (wi - 1) + b]) << (32 * h)
            m = dm
        out.append([e0 + w, f'{(d << 1) | 1:x}', f'{m:x}'])
    out.append([e0 + 160, '0', '1'])                                # valid low after the last word
    return out


def _ages(die):
    lk = getattr(die, 'links', {}) if die is not None else {}
    g = lambda k, d: (lk.get(k) or {}).get('age_edges', d)
    return dict(j_w=g('jw_W_l0', 34), j_e=g('jw_E_l0', 24), jd_w=g('jd_W', 32), jd_e=g('jd_E', 25),
                q_w=g('q_W_l0', 4), q_e=g('q_E_l0', 4), pv_w=g('pv_W', 4), pv_e=g('pv_E', 4))


def _op_t(sched, name, key):
    for o in (sched or {}).get('ops', []):
        if o['op'] == name:
            return o[key]
    return None


def build(fx, sched=None, die=None, tag=0, mutant=None):
    """the job + its static schedule at the layer's cycles (layer entry = 0)"""
    job = Job(fx, tag=tag, mutant=mutant)
    ag = _ages(die)
    t_own = int(np.ceil(_op_t(sched, 'attn.own_row_write', 'start') or 1805))
    t_q = int(np.ceil(_op_t(sched, 'attn.q_rope', 'end') or 3001))
    t_exp = int(np.ceil(_op_t(sched, 'attn.exp', 'end') or 3763))
    s = job.schedule(t_own, t_q, t_exp, ag['j_w'], ag['j_e'])
    from dv_layer_compile import SEQ
    s['issue'] = s['s_j'] - SEQ['svc_to_sj']
    dw, de = (s['done_nopv'], s['done']) if ST < 2 else (s['done'], s['done_nopv'])
    s['done_w'], s['done_e'] = dw, de
    s['ls'] = max(dw + ag['jd_w'], de + ag['jd_e']) - s['s_j']
    s['ages'] = ag
    return job, s


def bench_image(job, s, out, base=60):
    """the bench kit: images at tb cycles (tb cycle = layer cycle - s_j + base; the tb drives a value at cycle c, the
    pin holds it from the next edge -- the tb_dsdv_svc_rs convention the SVC-PV3 constants were measured in)"""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    off = base - s['s_j']
    w = s['words']
    arg, jw = job_word(s['nframes'], job.tag)
    pv_c = s['at']['PV'] + off if 'PV' in s['at'] else s['go'] + job.pio + off      # PPATH: nominal P start (GO + PIO)
    meta = [len(w), job.T, s['j_w'] + off, s['j_e'] + off, jw & 0xFFFFFFFF, jw >> 32, 0, s['pv_first'] + off,
            s['done_e'] + off, s['go'] + off, pv_c, ST, s['done_w'] + off, int(PPATH), len(job.p_words), 0]
    img = job.hbm_image()
    meta[6] = len(img)
    sc, pv = job.expected_hex()
    hx = lambda ws, bits: ''.join(f'{x:0{-(-bits // 4)}x}\n' for x in ws)
    files = {'meta.hex': hx(meta + [0] * (32 - len(meta)), 32),
             'qcyc.hex': hx([c + off for c, _ in w], 32), 'qwd.hex': hx([x for _, x in w], 512),
             'hkey.hex': hx(sorted(img), 64), 'hdat.hex': hx([img[k] for k in sorted(img)], 256),
             'sc.hex': hx(sc, 33 * H), 'pv.hex': hx(pv, 33 * H), 'pexp.hex': hx(job.p_words, 512)}
    for k, v in files.items():
        (out / k).write_text(v)
    rec = dict(schema='opentallas.s81_dv.svc_bench_image.v1', tb_offset=off, mutant=job.mutant, tag=job.tag,
               j_arg=arg, j_word=f'{jw:09x}', frames={k: v + off for k, v in s['at'].items()},
               go=s['go'] + off, pvs=s['pvs'], po=s['po'], pvo=s['pvo'], pio=job.pio, ppath=PPATH, pv_first=s['pv_first'] + off,
               pv_last=s['pv_last'] + off, done_w=s['done_w'] + off, done_e=s['done_e'] + off, anchors=job.anchor, T=job.T, heads=[job.h0, job.h0 + H],
               st=ST, sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()})
    (out / 'image.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


_CACHE = {}


def lower(die, op, ctx):
    name = op['op']
    fx = ctx.get('fixtures')
    base = dict(unit=UNIT, insts=INSTS, bench=BENCH, rows=[], templates=[], gunit_rows=[], svc_jobs=[], files={},
                events=[])
    if fx is None:
        return dict(base, status='GAP', gap=dict(module='lower_svc', port='fixtures',
                                                 missing='no fixture dir (--fixtures): q / P / own row are runtime data'))
    key = (str(fx), ctx.get('layer'), ctx.get('svc_tag', 0))
    if key not in _CACHE:
        try:
            _CACHE[key] = build(fx, ctx.get('sched'), die, tag=ctx.get('svc_tag', 0))
        except AssertionError as e:
            _CACHE[key] = (None, str(e))
    job, s = _CACHE[key]
    if job is None:
        return dict(base, status='GAP', gap=dict(module='lower_svc', port='fixtures', missing=s))
    r = dict(base)
    if name == 'attn.own_row_write':        # the job is issued with the first svc op of the layer
        from dv_layer_compile import ENG, SEQ
        arg, jw = job_word(s['nframes'], job.tag)
        r['rows'] = [dict(eng=ENG['SVC'], issue=s['issue'], done=s['issue'] + SEQ['done_v'] + s['ls'], arg=arg,
                          raw_arg=True, what=f'svc attention job ({s["nframes"]} q frames, T {job.T}, tag {job.tag:#04x})')]
        r['svc_jobs'] = [dict(layer=ctx.get('layer'), tag=job.tag, arg=arg, j_word=f'{jw:09x}', s_j=s['s_j'],
                              j_pin=dict(u_rsv_05=s['j_w'], u_rsv_11=s['j_e']), frames=s['at'], go=s['go'],
                              pvs=s['pvs'], po=s['po'], pvo=s['pvo'], pv_first=s['pv_first'], pv_last=s['pv_last'],
                              done_pin=dict(u_rsv_05=s['done_w'], u_rsv_11=s['done_e']), ls=s['ls'], hbm_sectors=len(job.hbm_image()),
                              q_words=len(s['words']), q_image=f'prog/svc/{ctx.get("layer")}/qwd.hex',
                              tag_rule='q headers carry {issuer slot, calendar row index}: re-emit with the final row '
                                       'index / per-slot header rows')]
        ev = [dict(cycle=s['j_w'], inst='u_rsv_05', port='j', dir='in', kind='SVCJ', tag='attn.job', payload=f'{jw:09x}'),
              dict(cycle=s['j_e'], inst='u_rsv_11', port='j', dir='in', kind='SVCJ', tag='attn.job', payload=f'{jw:09x}')]
        # LB2-S81/EVENTS: every boundary event carries its words [[edge, value hex, mask hex], ...] on its ports
        # (LSB-first concatenation of `ports`).  'in' words: the edge the consumer pin's landed register takes the value
        # (tb_svc_lower: the tb drives at cycle c, the pin holds it from edge c); 'out' words: the edge the PRODUCER's
        # output register takes it (tb_svc_lower samples pv_v / jd at cycle c = the register set at edge c - 1).
        for fname, t in s['at'].items():
            ws = [[c, f'{(w << 1) | 1:x}', f'{(1 << 515) - 1:x}'] for c, w in s['frame_words'][fname]]
            for inst in ('u_rsv_05', 'u_rsv_11'):
                ev.append(dict(cycle=t, inst=inst, port='q', ports=['q'], dir='in', kind='QF', tag=f'attn.{fname}',
                               payload=f'frame {fname}: {len(ws)} q words {{2\'d0, d 512, v}} (producer u_s_3S / u_s_4S '
                                       f'xr band bo)', words=ws, valid_bit=0, producer_gap=QF_PRODUCER_GAP))
        pvh = 'u_rsv_11' if ST < 2 else 'u_rsv_05'
        ev.append(dict(cycle=s['pv_first'], inst=pvh, port='pv_v / pv_d', ports=['pv_v', 'pv_d'], dir='out', kind='PV',
                       tag='attn.pv', payload=f'160 words (quarter {ST}: 4 x 40-cycle windows) to '
                       f'u_s_{"4" if pvh == "u_rsv_11" else "3"}S bi', words=pv_words(job, s), valid_bit=0,
                       data_masked='P.V values + header flags / pv_c (engine data, bit-exact in bench_svc; the cut '
                                   'bench has no HBM window image): checked = valid, the header marker pv_d[512] '
                                   'and the header zero field pv_d[511:72] on every compiled edge'))
        for inst, t in (('u_rsv_05', s['done_w']), ('u_rsv_11', s['done_e'])):
            ev.append(dict(cycle=t, inst=inst, port='jd', ports=['jd'], dir='out', kind='SVCDONE', tag='attn.job',
                           payload='done {fault, done} = 01 one edge', words=[[t - 1, '1', '3'], [t, '0', '3']]))
        r['events'] = ev
        # the lanes' valid bits (a data lane may hold stale bits while v = 0: dsdv_svc_rs.sv:264 pv_d <= rm_d every edge)
        r['port_valid'] = [dict(inst=i, ports=pp, bit=0) for i in ('u_rsv_05', 'u_rsv_11') for pp in (['q'], ['pv_v', 'pv_d'])]
        im = job.hbm_image()
        layer = ctx.get('layer')
        r['files'] = {f'prog/svc/{layer}/hbm_window.hex': ''.join(f'{k:016x} {im[k]:064x}\n' for k in sorted(im)),
                      f'prog/svc/{layer}/qwd.hex': ''.join(f'{c} {x:0128x}\n' for c, x in s['words'])}
        st = 'LOWERED'
    elif name in ('attn.window_load', 'attn.scores'):
        st = 'LOWERED'
    elif name in ('attn.max', 'attn.exp') and PPATH:
        st = 'LOWERED'
        r['bench'] = BENCH_P
    elif name in ('attn.den', 'attn.sink') and PPATH:
        st = 'PARTIAL'
        r['gap'] = dict(module='dsdv_svc_rs SM head (ot_s81_su_sms) SO job -- die gap G9b',
                        port='w_v / w_a / w_m / w_d (SO o rows)',
                        missing='den / sink are computed on-die by the layer\'s SE job (the same SMJ frame as max / exp, '
                                'lowered), but their only consumer is the SO normalisation, whose o rows have no on-die '
                                'consumer (G9b): no bench checks den / sink')
    elif name == 'attn.pv':
        st = 'PARTIAL'
        r['gap'] = dict(module='dsdv_svc_att quarter ST (pvown) -- die gap G10 (cross-die part)',
                        port='P.V quarters 4 ST .. 4 ST + 3 (one die) -> wo_a (all 512 dims of the rank)',
                        missing='by design (results/arch/s81_dv_1016/svc_rs/decisions.json, svc_c rule) a die emits the P.V '
                                'of its stack\'s output quarter only (tiles 4 ST .. 4 ST + 3, dsdv_svc_att pvown); the '
                                'quarter words are bench-exact with P produced ON-DIE (PPATH).  ST is the CFG frame field '
                                '[32] / [31:30] since TOK-S81-GAPS/SVCP (one die netlist, 4 stack positions); the other 3 '
                                'quarters reach wo_a only through a cross-die exchange that no layer op prices or lowers '
                                '(TOK.DS.XDIE / S81-DIE8 decision)')
    else:
        st = 'GAP'
        r['gap'] = dict(module='results/arch/s81_dv_1016/bind_p4l3_g8/die.v u_rsv_00..15 (dsdv_svc_rs SM face) -- die gap G9',
                        port='w_v / w_a / w_m / w_d / w_st',
                        missing='the SM head (ot_s81_su_sms, dsdv_svc_rs.sv:215-219) computes the head\'s max / exp / '
                                'den from the SE rows, but its write face has NO consumer anywhere in rtl/ (open outputs '
                                'on all 16 u_rsv_*; die_port_bind does not count unconnected outputs, so strict bind '
                                'PASSes and synthesis would remove the SM): the P operand of the PV frame (16 heads x 2 '
                                'rows BF16 a word, from 16 different slices) and the normalised o rows have no on-die '
                                'path; the bench feeds P = bf16(fixture attn.exp) as runtime data. Needs an RTL dataflow '
                                'decision (gaps.json G9 options), not a lowering') if not PPATH else dict(
                        module='dsdv_svc_rs SM head (ot_s81_su_sms) SO job -- die gap G9b',
                        port='w_v / w_a / w_m / w_d (SO o rows; die.v: open)',
                        missing='the SO job (den divide + inverse RoPE -> BF16 o rows) runs in slice g, but its o rows '
                                'leave only on w_*, which nothing on the die reads, and its operand rows (P.V of head g, '
                                'all dims) exist on-die only as the owners\' P.V quarter words at the entry pv pins: '
                                'needs (a) the SO operand rows back as SMJ frames (slice band send programme) or an '
                                'in-grid head gather, (b) an o-row exit (return tree -> pv pins), (c) the cross-die '
                                'quarters (G10)')
    return dict(r, status=st)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='emit the svc bench images (base + mutants) from a layer fixture')
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sched', default=None, help='schedule.json of dv_layer_compile (else the L0 priced defaults)')
    ap.add_argument('--tag', type=lambda x: int(x, 0), default=0)
    a = ap.parse_args(argv)
    sched = json.loads(Path(a.sched).read_text()) if a.sched else None
    die = None
    try:
        import dv_layer_compile as DC
        die = DC.Die(DC.die_tree(DC.DIE_REF))
    except Exception as e:    # noqa: BLE001 -- the link ages fall back to the bind9 values
        print('die model unavailable, bind9 link ages:', e)
    for mut in (None, 'slot', 'pio_early' if PPATH else 'late'):
        job, s = build(a.fixtures, sched, die, tag=a.tag, mutant=mut)
        rec = bench_image(job, s, Path(a.out) / (mut or 'base'))
        print(mut or 'base', json.dumps({k: rec[k] for k in ('go', 'pv_first', 'done_w', 'done_e', 'frames')}))


if __name__ == '__main__':
    main()
