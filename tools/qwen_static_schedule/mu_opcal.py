"""MU-QW-B1 2026-10-19 (coordinator: B1 = option 2): op-granular playback of the Qwen ROM 4-user static calendar.

Why.  The 4-user calendar of record (mu_calendar.compile_calendar, op granularity, ~14,054 tok/s) lets a filler user wait
between the programme ops of a decode layer.  The RTL as built (qfd_dv_cmd_cal_mu) starts one rigid segment per stage
start, and the stage starts come from the closed qfd_sys_face T calendar (NE 64 events a token period), so the RTL can
only play whole layers: 2 users, 9,291 tok/s (MU-ADOPT-TOK F-TOK-2).  A filler needs ~150 op starts a token; the T
calendar cannot carry them and the closed face is not re-closed (coordinator).

What this compiles (one source for the three images):
  1. the DV calendar image (qfd_dv_cmd_cal_mu PW/DW): the decode-layer segment is laid out in OP GROUPS (programme ops;
     an op shorter than MIN_OP_CYC cycles is fused with the next op), every group's first entry 4-aligned (NOP pads after
     the previous group) and >= T0_MIN edges after the previous entry.  A group run [g_i .. g_j] of one layer is then a
     contiguous entry sub-range [first, first + cnt) of the layer segment that plays with the layer segment's own deltas.
  2. the op-start list of the observer leaf qfd_sys_face_mu_dhuser (OPSEG mode, beside the closed qfd_sys_face): one
     entry per filler segment start {t, user, stage, first, cnt}; the leaf plays it at compiled edges (frame counter
     anchored on the latency user's L0 stage start, period H) and qfd_dv_cmd_cal_mu starts that user's playhead on the
     explicit range.  A filler that does not wait between groups keeps playing (no start); after a wait w >= 1 the leaf
     starts the next run at S' = (the previous run's last entry edge) + w, so every entry fires exactly where the
     calendar placed its op.  The latency user (user 0) keeps the face's layer-granular stage starts: its timeline, its
     segments and its command edges are the single-user ones (cycle-identical).
  3. a PERIODIC frame: the record is a finite-horizon greedy list schedule; a ROM-played list must repeat.  Frame =
     F latency-user tokens (H = F x T); reservations are cyclic (every window also at +-H); a filler places WHOLE tokens
     inside [s_k, s_k + H) (priority policy = the record's: user 1 first, then 2, 3), so the frame repeats exactly.
Command-plane resources the RTL faults on are scheduled too (record_cp): cp.start (one start port: the face's stage
starts and the leaf's starts), cp.cmd (one cmd register), cp.done (one done register), cp.stn (F-TOK-1 station window),
and am.root (the argmax root merge, item 2 of the coordinator: the root (qfd_dv_scalar2) merges one user's candidates
at a time, so two users' LM-head emits must never be in flight at the root together; the RTL carries the user with the
candidates and faults on a mixed merge; here it is a reserved window, checked again by check_root_merge()).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .calendar import ScheduleError
from . import mu_calendar as M
from . import mu_tok_cases as C

NU = 4
T0_MIN = 4 + (NU - 1)       # qfd_dv_cmd_cal_mu: a filler playhead's first entry T_0 >= 4 + (NU - 1)
MIN_OP_CYC = 16             # an op shorter than this cannot open a run (T0_MIN + 3 NOP pads + its own entry offset)
OP_ENTRY_OFS = 8            # every op's commands from its op start + 8 (the smoke image convention, >= T0_MIN)
AM_EMIT_T = 8               # the token-start segment emits the previous token's argmax at T = 8
# argmax root merge span: the AMAX emit reaches slice i of a 12-slice chain i edges after issue (cmd_eo register per
# slice), its AMI/AMV beats travel <= 11 hops x 2 edges (scalar out register + the top's pin register) + 2 beats to the
# root; 1 + 11 + 22 + 2 = 36 edges after the emit the last candidate has merged.  48 = 36 + 12 margin.
AM_ROOT_SPAN = 48
# MU-OPCAL-EMB 10-19: the token-start segment's LOCAL EMB sends tok_b[user] (qfd_tt_ctlm_dv: emb_token <= tok_b[b_rd] on
# the edge after the entry's issue edge), so it must issue only once the user's argmax result is IN the bank.  Edges from
# the AMAX emit's issue edge I (u_cal cmd register), RTL as built:
AM_CMD_PIN = 1      # I -> W5 slice cmd_q (qfd_dv_slice2 pin register; die bind tt_ctlm.cmd -> dvs_W5.cmd_wi direct,
                    #     tools/qwen_split/dv_case.W5_PEERS) = e, the am_root_window reference edge
ST_REG = 1          # W5 scalar tok_v register -> qfd_dv_slice2 st register (st[24] tok_v, st[23:0] tok_idx, st[27:26] user)
SS_PIN = 1          # st (= ss_wo) -> qfd_tt_ctlm_dv ss_q pin register (die bind dvs_W5.ss_wo -> tt_ctlm.ss5 direct)
BANK_WR = 1         # ss_q tok_v (r_fill) -> tok_b[u] register
# (a relay stage the die GEN inserts on cmd or ss5 adds one edge each to AM_CMD_PIN / SS_PIN and moves EMB_T with it)


def tok_slice0_edge(n=M.AM_SLICES):
    """edges after e on which W5's (slice 0's) qfd_dv_scalar2 tok_v register is set, worst case over the root position r.
    The root's last candidate merges on edge X(r) = max(own 2r + 2, slice k's 2k + 2|k - r| + 3) (mu_calendar
    am_root_window); on X the root sets tok_v (r = 0: that is W5) and tk_send; its TOK broadcast leaves dn_o on X + 1 and
    travels 2 edges a hop (neighbour pin register scd_q, then its pass register / tok_v): slice 0 sets tok_v on
    X + 2r + 1.  n = 12 -> 48 (r = 0: 47; r >= 1: 48)."""
    worst = 0
    for r in range(n):
        x = max([2 * r + 2] + [2 * k + 2 * abs(k - r) + 3 for k in range(n) if k != r])
        worst = max(worst, x if r == 0 else x + 2 * r + 1)
    return worst


RES_SSQ = AM_CMD_PIN + tok_slice0_edge() + ST_REG + SS_PIN     # 51: ctlm ss_q holds the result (bench ss5 event edge)
RES_BANK = RES_SSQ + BANK_WR                                    # 52: tok_b[u] written on I + 52
EMB_T = AM_EMIT_T + RES_BANK    # 60: EMB issue edge S + 60 -> emb_token sampled on S + 61 >= the write edge + 1
EMB_T_SMOKE = 16                # the pre-fix image (mu_tok_cases smoke segment 0): EMB before the result (stale token)
UVM, PIDX, UTAG = M.DV_UVM_STRIDE, M.DV_PIDX_STRIDE, M.DV_UTAG_LSB
LAST_STAGE = C.LAST_STAGE
CLK = 1.2e9
# leaf ROM (ot_rom_4096x72_m8): word 0 header, words 1.. entries
ROM_WORDS = 4096
LEAF_MAGIC = 0x4F50                     # "OP"
TB, UB_, SB, FB, CB = 22, 2, 6, 10, 10  # entry fields: t, user, stage, first, cnt  (+ flag FIRST)
# leaf spacing rule (qfd_sys_face_mu_dhuser OPSEG): the leaf consumes an entry on edge e and issues the ROM read of the
# next entry on that same edge (1-edge read, captured into the prefetch register on e + 1), so the next entry can be
# consumed on e + 2 at the earliest: consecutive t_rom (and the frame wrap, last -> first + H) >= LEAF_MIN_GAP
LEAF_MIN_GAP = 2


# ---------------------------------------------------------------------------------------------------- image
def F(**kv):
    return C.F(**kv)


def ports_w(ar, dd, em):
    return C.ports(ar, dd, em)


def op_groups(p=None):
    """[(group name, [ops])]: every op of the layer programme; an op shorter than MIN_OP_CYC is fused with the NEXT op
    (rmsnorm1 15 -> qkv, attn_tail 2 -> rmsnorm2): a run can only open on a group"""
    p = dict(M.SOURCED, **(p or {}))
    ops = M.layer_block(p)["ops"]
    names = [o for o, _, _, _ in M.LAYER_WINDOWS]
    out, cur = [], []
    for o in names:
        cur.append(o)
        a, b = ops[o]
        if b - a >= MIN_OP_CYC:
            out.append(("+".join(cur), list(cur)))
            cur = []
    if cur:
        out[-1] = (out[-1][0] + "+" + "+".join(cur), out[-1][1] + cur)
    return out


def layer_entries(p=None):
    """decode-layer segment commands (layer-relative T, cmd), one command group per op at op start + 8, user-0 regions
    inside [0, UVM) so the per-user relocation never overlaps users"""
    p = dict(M.SOURCED, **(p or {}))
    ops = M.layer_block(p)["ops"]
    ent, k = [], 0
    for i, (op, unit, _, _) in enumerate(M.LAYER_WINDOWS):
        a = ops[op][0] + OP_ENTRY_OFS
        if unit == "me":
            ent.append((a, C.stn(0x100 + 0x40 * i, kc=C.MATVEC_KC[op]), op))
        elif unit == "su":
            ent.append((a, C.su(1 + i), op))
        elif unit == "kv":
            ent.append((a, C.loc_seg(0x10), op))
        elif unit == "coll":
            ent += [(a, ports_w(0x800 + 0x100 * k, 0xA00, 0xC00), op), (a + 4, C.xc(k, p["ar_words"]), op)]
            k += 1
    return sorted(ent)


def op_layer_image(p=None):
    """the layer segment in op-group layout: entries [(T, cmd)] (NOP = cmd 0) and per group {first, cnt, T_prev,
    T_first, T_last, a, b} (entry indices relative to the segment; layer-relative times; a, b = the group's op span)"""
    p = dict(M.SOURCED, **(p or {}))
    ops = M.layer_block(p)["ops"]
    raw = layer_entries(p)
    ent, grp, prev = [], {}, 0
    for gname, gops in op_groups(p):
        a, b = ops[gops[0]][0], ops[gops[-1]][1]
        mine = [(t, c) for t, c, o in raw if o in gops]
        if not mine:
            mine = [(a + OP_ENTRY_OFS, 0)]                     # a group without commands still opens with a NOP
        while len(ent) % 4:
            prev += 1
            ent.append((prev, 0))
        t_prev = prev if ent else 0
        if mine[0][0] - t_prev < T0_MIN or mine[0][0] < a:
            raise ScheduleError(f"group {gname}: first entry {mine[0][0]} too close to the previous entry {t_prev}")
        f = len(ent)
        ent += mine
        prev = ent[-1][0]
        if prev >= b:
            raise ScheduleError(f"group {gname}: entry {prev} outside its span [{a}, {b})")
        grp[gname] = dict(first=f, cnt=len(mine), T_prev=t_prev, T_first=mine[0][0], T_last=prev, a=a, b=b,
                          ops=gops)
    for (t0, _), (t1, _) in zip(ent, ent[1:]):
        if not 1 <= t1 - t0 <= 4095:
            raise ScheduleError(f"layer entry delta {t1 - t0}")
    return ent, grp


def segments(p=None):
    """the DV calendar image segments: 1 decode layer (op-group layout), 0 token start (emit the previous argmax, open
    the next, embedding), 2 one LM-head row chunk (amax STN), 3 boot -- the MU-ADOPT-TOK smoke image's 0 / 2 / 3"""
    lay, grp = op_layer_image(p)
    s = C.segments(p)
    s[1] = lay
    emb_t = (p or {}).get("emb_t", EMB_T)
    s[0] = [(t, c) if not _is_emb(c) else (emb_t, c) for t, c in s[0]]       # MU-OPCAL-EMB: EMB after the result
    s[0].sort()
    return s, grp


def _is_emb(c):
    return c & 1 and (c >> 112) & 15 == 14 and (c >> 1) & 7 == 1


def _is_emit(c):
    return c & 1 and (c >> 112) & 15 != 14 and (c >> 1) & 7 == 6 and (c >> 5) & 1


def check_emb_after_result(cal):
    """MU-OPCAL-EMB assertion: every user's LOCAL EMB issues on or after the edge its own argmax result is written into
    tok_b[user] (emit issue edge + RES_BANK), and no other emit of the same user intervenes.  Derived from the image's
    actual token-start entries (not the constants), for every token-start unit of every user over the frame (cyclic).
    Raises ScheduleError; returns the number of token starts checked."""
    seg0 = cal["segs"][0]
    emits = [t for t, c in seg0 if _is_emit(c)]
    embs = [t for t, c in seg0 if _is_emb(c)]
    if len(emits) != 1 or len(embs) != 1:
        raise ScheduleError(f"token-start segment needs one AMAX emit and one LOCAL EMB (emits {emits}, embs {embs})")
    n = 0
    for u, seq in cal["schedule"].items():
        for name, t0, _ in seq:
            if name != "head":
                continue
            w, e = t0 + emits[0] + RES_BANK, t0 + embs[0]
            if e < w:
                raise ScheduleError(f"user {u}: LOCAL EMB at {e} precedes its argmax result in tok_b[{u}] (written on {w}: "
                                    f"emit {t0 + emits[0]} + RES_BANK {RES_BANK}) -- the EMB would send the previous token")
            n += 1
    return n


def image(segs):
    """PW / DW words + the segment descriptors (absolute entry index, count); = mu_tok_cases.image"""
    pw, dw = C.image(segs)
    desc = {s: ((dw[1 + s] >> 16) & 0xFFFF, dw[1 + s] & 0xFFFF) for s in range(4)}
    return pw, dw, desc


# ---------------------------------------------------------------------------------------------------- user words
def reloc(c, u):
    """the word qfd_dv_cmd_cal_mu (NU 4, UFOLD 1, DV strides) issues for user u; u = 0 -> the image word"""
    kind, dst = (c >> 1) & 7, (c >> 112) & 15
    if u == 0 or dst == 14:
        return c

    def put(w, lsb, wid, v):
        assert 0 <= v < (1 << wid), (lsb, wid, v)
        return (w & ~(((1 << wid) - 1) << lsb)) | (v << lsb)

    def get(w, lsb, wid):
        return (w >> lsb) & ((1 << wid) - 1)
    if kind == 4:
        for lsb in (4, 28, 54):
            c = put(c, lsb, 24, get(c, lsb, 24) + u * UVM)
    elif kind == 2:
        if (c >> 24) & 1:
            c = put(c, 26, 24, get(c, 26, 24) + u * UVM)
        c = put(c, 51, 2, u)
    elif kind == 1:
        c = put(c, 4, 9, get(c, 4, 9) + u * PIDX)
    elif kind == 0 and get(c, 4, 2) == 0:
        c = put(c, 23 + UTAG, 2, u)
    elif kind == 6:
        c = put(c, 8, 2, u)
    return c


# ---------------------------------------------------------------------------------------------------- placement units
def _cp(ent, t_ref, start=None):
    """command-plane windows of entries [(T, cmd)] relative to t_ref: cmd (go entries that leave), stn, done"""
    d = {}
    for t, c in ent:
        if c & 1:                                    # LOCAL (dst 14) entries also use the one issue register (i_col)
            d.setdefault("cp.cmd", []).append((t - t_ref, t - t_ref + 1))
        if c & 1 and (c >> 1) & 7 == 2 and (c >> 112) & 15 != 14:
            w = C.STN_LAT + C.RW * C.RW_GAP if (c >> 50) & 1 else 1
            d.setdefault("cp.stn", []).append((t - t_ref, t - t_ref + w))
    d["cp.done"] = [(ent[-1][0] - t_ref, ent[-1][0] - t_ref + 1)]
    if start is not None:
        d["cp.start"] = [(start, start + 1)]
    return d


def _merge(*ws):
    out = {}
    for w in ws:
        for r, iv in w.items():
            out.setdefault(r, []).extend(iv)
    return {r: sorted(v) for r, v in out.items()}


def _cut(w, a, b):
    """windows of a layer block that start inside [a, b), relative to a"""
    out = {}
    for r, iv in w.items():
        for x, y in iv:
            if a <= x < b:
                out.setdefault(r, []).append((x - a, y - a))
    return out


def token_units(p, segs, grp, filler, layers=36):
    """one token of one user as placement units [(name, block)], block = {windows, length, kind, ...}.
    latency user: whole layers (the face's stage starts; rigid layer segment at the layer start), head chunks, head.
    filler: op groups (a run may open on any group), head chunks, head."""
    head_cp = _cp(segs[2], 0, start=0)
    tok_cp = _merge(_cp(segs[0], 0, start=0), {"am.root": [(AM_EMIT_T, AM_EMIT_T + AM_ROOT_SPAN)]})
    lay_cp = _cp(segs[1], 0, start=0)
    names = [g for g, _ in op_groups(p)]
    out = []
    kvr = p.get("kv_lp_rows")      # MU-KV-BOOT 10-19 (opt-in): the KV layer programme's own edges as resource kv.lp
    for i in range(layers):
        blk = M.layer_block(p, l0=(i == 0))
        extra = blk["length"] - p["layer_period"]
        kv0 = blk["windows"]["kvs"][0][0] if kvr else 0                # the KV stage begins kv0 before its kvs window
        if not filler:
            w = _merge(blk["windows"], lay_cp)
            if kvr:
                w = _merge(w, kv_lp_windows(kvr[i], 0))
            out.append((f"L{i}", dict(windows=w, length=blk["length"], kind="layer", stage=i + 1,
                                      **({"kv_begin": 0} if kvr else {}))))
            continue
        ops = blk["ops"]
        for gi, g in enumerate(names):
            gg = grp[g]
            a = ops[gg["ops"][0]][0]
            b = blk["length"] if gi == len(names) - 1 else ops[gg["ops"][-1]][1]
            # the group's commands at their image offsets from the group's image start (an L0 qkv is longer: its
            # slack is after its commands, the next group opens later = a wait the leaf plays)
            gent = [e for e in segs[1][gg["first"]:gg["first"] + gg["cnt"]]]
            cp = _cp(gent, gg["a"], start=gg["T_prev"] - gg["a"])
            gw = _merge(_cut(blk["windows"], a, b), cp)
            kb = {}
            if kvr and "kvs" in gw:                                     # rigid with this group's kvs window
                kb = dict(kv_begin=gw["kvs"][0][0] - kv0)                 # the KV stage begin, from the group start
                gw = _merge(gw, kv_lp_windows(kvr[i], kb["kv_begin"]))
            out.append((f"L{i}.{g}", dict(windows=gw, length=b - a, kind="group",
                                          stage=i + 1, group=g, l0_extra=extra, **kb)))
    for n, b in M.head_blocks(p):
        if n == "head":
            out.append((n, dict(windows=_merge(b["windows"], tok_cp), length=b["length"], kind="token", stage=0)))
        else:
            out.append((n, dict(windows=_merge(b["windows"], head_cp), length=b["length"], kind="chunk",
                                stage=LAST_STAGE)))
    return out


def kv_lp_windows(row, b):
    """MU-KV-BOOT 10-19: unit windows of one KV layer-programme stage that begins at b (stage_start, the 8 roots,
    stage_done = b + stage_end): qkd_static_kv_layer_programme_mu faults when two users' events share an edge"""
    offs = sorted({0, row["stage_end"]} | {row[k] for k in M.KV_LP_ROOTS[:8]})
    go = {row[k] for k in M.KV_GO_ROOTS}                 # launches: + META_HOLD_CORE (another user's go faults inside)
    return {"kv.lp": [(b + o, b + o + (M.KV_META_HOLD + 1 if o in go else 1)) for o in offs],
            # the attention programme's exclusive busy span [issue, run + 1784] on the KV programme's own frame
            "kv.att": [(b + row["attention_issue"], b + row["attention_run"] + M.KV_ATT_END + 1)]}


# ---------------------------------------------------------------------------------------------------- frame compile
class CyclicRes(M.Reservations):
    def __init__(self, H):
        super().__init__()
        self.H = H

    def add(self, wins, t0, owner):
        for k in (-1, 0, 1):
            super().add(wins, t0 + k * self.H, owner)

    def remove(self, wins, t0, owner):
        for k in (-1, 0, 1):
            for res, iv in wins.items():
                lst = self.r[res]
                for a, b in iv:
                    lst.remove((a + t0 + k * self.H, b + t0 + k * self.H, owner))


# ------------------------------------------------------------------------------------- filler initial context (0ka)
CTX_TAG = 0x4D43            # qfd_tt_ctlm_dv OPSEG: CTX[127:112]
CTX_DW = (5, 6)             # the calendar image words that carry CTX = {DW6, DW5} (reserved 0 at CTX_DW 0)


def ctx_words(ctx, mask=None, tag=CTX_TAG):
    """the boot context record of the OPSEG fillers (MU-QW-DIE 10-19, coordinator 0ka: loaded at boot through the image /
    host config plane into the ctlm per-user token / position bank, no bench-only preload).  ctx = {u: (tok, pos)} for
    fillers u = 1..NU-1; mask = the users the record loads (default: every user in ctx).  Returns (DW5, DW6):
    CTX[36(u-1) +: 36] = {tok 18, pos 18}, CTX[108 +: 3] = mask (bit u-1), CTX[111] = 0, CTX[127:112] = tag."""
    mask = set(ctx) if mask is None else set(mask)
    v = 0
    for u, (tok, pos) in ctx.items():
        if not 1 <= u < NU or not 0 <= tok < (1 << 18) or not 0 <= pos < (1 << 18):
            raise ScheduleError(f"context of user {u} out of range (filler 1..{NU - 1}, tok / pos 18 b)")
        v |= ((tok << 18) | pos) << (36 * (u - 1))
    if not mask <= set(ctx):
        raise ScheduleError(f"context mask {sorted(mask)} names a user without a record")
    v |= sum(1 << (u - 1) for u in mask) << 108
    v |= (tag & 0xFFFF) << 112
    return v & ((1 << 64) - 1), v >> 64


def with_ctx(dw, ctx, mask=None, tag=CTX_TAG):
    """the DW image with the context record in DW5 / DW6 (both must be 0 in the plain image)"""
    if any(dw[i] for i in CTX_DW):
        raise ScheduleError("DW5 / DW6 already used: the context record needs them")
    out = list(dw)
    out[CTX_DW[0]], out[CTX_DW[1]] = ctx_words(ctx, mask, tag)
    return out


def compile_frame(F=16, p=None, layers=36, starts=None):
    """periodic NU-user op-granular calendar over a frame of F latency-user tokens; ScheduleError on any collision"""
    p = M._need(dict(M.SOURCED, users=NU, occupancy="measured", head_chunks=8, **(p or {})))
    # the embedding request / host return / row fetch consume the NEW token: they start at the EMB edge (mu_calendar
    # head_blocks tok_ofs), so the token-start block is EMB_T longer than the pre-fix image's (single-user too)
    p.setdefault("head_tok_ofs", p.get("emb_t", EMB_T))
    P = p["layer_period"]
    segs, grp = segments(p)
    u0 = token_units(p, segs, grp, filler=False, layers=layers)
    uf = token_units(p, segs, grp, filler=True, layers=layers)
    T = sum(b["length"] for _, b in u0)
    if T != sum(b["length"] for _, b in uf) or T != M.single_user_period(p, layers):
        raise ScheduleError("placement units do not tile the single-user token")
    H = F * T
    R = CyclicRes(H)
    sched = {0: []}
    t = 0
    for _ in range(F):
        for n, b in u0:
            R.add(b["windows"], t, 0)
            sched[0].append((n, t, b))
            t += b["length"]
    Q = p.get("kv_phase_quantum", 0)                       # MU-KV-BOOT opt-in (mu_calendar.kv_frame_params)
    if Q and T % Q:
        raise ScheduleError(f"token period {T} not a multiple of the KV HBM-beat cycle {Q} (token_pad)")
    kvr = p.get("kv_lp_rows")
    ntok = {0: F}
    for k in range(1, NU):
        t = starts[k - 1] if starts else round(k * P / NU)
        t = R.earliest(uf[0][1]["windows"], t, k)
        s_k = t
        sched[k], ntok[k] = [], 0
        while True:
            placed, tt = [], t
            for n, b in uf:
                tt = R.earliest(b["windows"], tt, k)
                while Q and "kv_begin" in b and not M.kv_launch_legal(kvr[b["stage"] - 1], tt + b["kv_begin"]):
                    tt += 1                                             # MU-KV-BOOT: every launch of the KV stage on a
                    tt = R.earliest(b["windows"], tt, k)                # legal HBM-beat phase (phase launch window)
                if tt + b["length"] > s_k + H:
                    break
                R.add(b["windows"], tt, k)
                placed.append((n, tt, b))
                tt += b["length"]
            else:
                sched[k] += placed
                ntok[k] += 1
                t = tt
                continue
            for n, t0, b in placed:                                    # roll back the partial token
                R.remove(b["windows"], t0, k)
            break
        if ntok[k] == 0:
            raise ScheduleError(f"user {k}: no whole token fits the frame (F = {F})")
    # independent whole-frame check: every resource's windows over all users, 3 frame copies, pairwise disjoint
    per = {}
    for u, seq in sched.items():
        for n, t0, b in seq:
            for res, iv in b["windows"].items():
                for a, bb in iv:
                    for kk in (-1, 0, 1):
                        per.setdefault(res, []).append((a + t0 + kk * H, bb + t0 + kk * H, u, n))
    clashes = []
    for res, lst in per.items():
        lst.sort()
        if res in M.SELF_OK:                                           # kv.lp: one user's own events may share
            lst = sorted({(a, b, u) for a, b, u, _ in lst})              # an edge (done + next start); others not
            lst = [(a, b, u, None) for a, b, u in lst]
        for x, y in zip(lst, lst[1:]):
            if y[0] < x[1] and not (res in M.SELF_OK and x[2] == y[2]):
                clashes.append((res, x, y))
    if clashes:
        raise ScheduleError(f"frame collision: {clashes[:3]}")
    ref = [(n, i * T + sum(b["length"] for _, b in u0[:j]))
           for i in range(F) for j, (n, b) in enumerate(u0)]
    if [(n, t0) for n, t0, _ in sched[0]] != ref:
        raise ScheduleError("latency user timeline differs from the single-user timeline")
    cal = dict(schema="opentallas.qwen.mu_opcal.v1", frame_tokens=F, layers=layers, H=H, T=T, inputs=p, segs=segs, grp=grp,
               schedule=sched, tokens_per_frame=ntok,
               users=[dict(user=u, tokens_per_frame=ntok[u], tok_s=ntok[u] * CLK / H,
                           first_start=sched[u][0][1]) for u in range(NU)])
    cal["aggregate_tok_s"] = sum(x["tok_s"] for x in cal["users"])
    check_root_merge(cal)
    if p.get("check_emb", True):
        cal["emb_checked"] = check_emb_after_result(cal)
    return cal


def check_root_merge(cal):
    """coordinator item 2, compiler side: the argmax root merges ONE user's candidates at a time.  Every LM-head emit
    (token-start segment, T = AM_EMIT_T) opens [emit, emit + AM_ROOT_SPAN) at the root; two users' spans must not
    overlap (cyclically over the frame).  Raises ScheduleError (independent of the am.root reservation)."""
    H = cal["H"]
    sp = sorted(((t0 + AM_EMIT_T) % H, u) for u, seq in cal["schedule"].items() for n, t0, _ in seq if n == "head")
    for (a, u), (b, v) in zip(sp, sp[1:] + [(sp[0][0] + H, sp[0][1])]):
        if b < a + AM_ROOT_SPAN and u != v:
            raise ScheduleError(f"argmax root merge mixes users {u} and {v}: emits at {a} and {b} (span {AM_ROOT_SPAN})")
    return len(sp)


# ---------------------------------------------------------------------------------------------------- playback
def playback(cal):
    """segment starts and command fires of the frame (times in [0, H) mod H for fillers; user 0 from its unit starts):
    starts = [(S, user, stage, first_abs, cnt, src)] (src 'face' = the latency user's stage start, 'leaf' = a leaf
    entry, with flag FIRST on a filler's first run of the frame); fires = [(t, user, word)] (go entries leaving cmd)"""
    segs, grp, H = cal["segs"], cal["grp"], cal["H"]
    pw, dw, desc = image(segs)
    names = [g for g, _ in op_groups(cal["inputs"])]
    starts, fires = [], []

    def play(S, u, seg_ent, T_prev):
        for t, c in seg_ent:
            if c & 1 and (c >> 112) & 15 != 14:
                fires.append((S + t - T_prev, u, reloc(c, u)))
    for u, seq in cal["schedule"].items():
        run = None                                           # an open filler run: [S, stage, gi_first, gi_last]
        first_unit = True

        def close():
            nonlocal run
            if run:
                S, stg, g0, g1, fl = run
                f = desc[1][0] + grp[names[g0]]["first"]
                e = desc[1][0] + grp[names[g1]]["first"] + grp[names[g1]]["cnt"]
                starts.append((S, u, stg, f, e - f, "leaf", fl))
                play(S, u, segs[1][f - desc[1][0]:e - desc[1][0]], grp[names[g0]]["T_prev"])
            run = None
        prev_end = None
        for n, t0, b in seq:
            if b["kind"] == "group":
                gi = names.index(b["group"])
                g = grp[b["group"]]
                if run and run[1] == b["stage"] and gi == run[3] + 1 and t0 == prev_end:
                    run[3] = gi                                  # no wait: the run keeps playing
                else:
                    close()
                    run = [t0 + g["T_prev"] - g["a"], b["stage"], gi, gi, first_unit]
                    first_unit = False
                prev_end = t0 + b["length"]
                continue
            close()
            seg = {"layer": 1, "chunk": 2, "token": 0}[b["kind"]]
            f, cnt = desc[seg]
            src = "face" if u == 0 else "leaf"
            starts.append((t0, u, b["stage"], f, cnt, src, first_unit and u != 0))
            first_unit = False
            play(t0, u, segs[seg], 0)
            prev_end = t0 + b["length"]
        close()
    starts.sort()
    fires.sort()
    return dict(starts=starts, fires=fires, pw=pw, dw=dw, desc=desc)


def leaf_list(cal, pb=None):
    """the leaf ROM entries (filler starts), sorted by t_rom = (S - 1) mod H: the leaf consumes an entry on the edge its
    frame counter equals t_rom and presents the start (registered) on the next edge = S"""
    pb = pb or playback(cal)
    H = cal["H"]
    L = sorted(((S - 1) % H, u, stg, f, cnt, fl) for S, u, stg, f, cnt, src, fl in pb["starts"] if src == "leaf")
    ts = [x[0] for x in L]
    if len(set(ts)) != len(ts):
        raise ScheduleError("two leaf starts on one edge")
    gaps = [b - a for a, b in zip(ts, ts[1:])] + ([ts[0] + H - ts[-1]] if ts else [])
    if ts and min(gaps) < LEAF_MIN_GAP:
        raise ScheduleError(f"leaf entries {min(gaps)} edges apart (< LEAF_MIN_GAP {LEAF_MIN_GAP}: ROM prefetch)")
    if any(f % 4 for _, _, _, f, _, _ in L):
        raise ScheduleError("a leaf range does not start on a 4-entry store row (qfd_dv_cmd_cal_mu fetch alignment)")
    if len(L) + 1 > ROM_WORDS:
        raise ScheduleError(f"{len(L)} leaf entries do not fit the {ROM_WORDS}-word ROM")
    if H >= (1 << TB):
        raise ScheduleError(f"frame {H} needs more than {TB} counter bits")
    if any(u == 0 or not 1 <= cnt < (1 << CB) or f + cnt >= (1 << FB) for _, u, _, f, cnt, _ in L):
        raise ScheduleError("leaf entry user 0 / empty / out-of-field range")
    return L


def rom_words(cal, L=None):
    """ROM word 0 = {magic 16 [71:56], H 22 [55:34], nent 12 [33:22], T 22 [21:0]}; entry word = {FIRST [71], 2'd0, cnt 10
    [68:59], first 10 [58:49], stage 6 [48:43], user 2 [42:41], t_rom 22 [40:19], 19'd0}"""
    L = L if L is not None else leaf_list(cal)
    w = [(LEAF_MAGIC << 56) | (cal["H"] << 34) | (len(L) << 22) | cal["T"]]
    for t, u, stg, f, cnt, fl in L:
        w.append((int(bool(fl)) << 71) | (cnt << 59) | (f << 49) | (stg << 43) | (u << 41) | (t << 19))
    return w


def via_map(words, rows=512, mux=8):
    """ot_rom_4096x72_m8 via mask rows (tools/mem_compiler/rom_gen.via_map): column b*mux + s = bit b of word r*mux+s"""
    out = [0] * rows
    for a, w in enumerate(words):
        r, s = divmod(a, mux)
        b = 0
        while w:
            if w & 1:
                out[r] |= 1 << (b * mux + s)
            w >>= 1
            b += 1
    return out


def viamap_hex(words):
    """the $readmemh text of ot_rom_4096x72_m8's via array (512 rows x 576 columns, one 144-digit row a line)"""
    return "".join(f"{r:0144x}\n" for r in via_map(words))


def face_stage_list(cal):
    """the latency user's stage starts of one token (the leaf's STG_SEQ alignment list): stages in order"""
    T = cal["T"]
    return [b["stage"] for n, t0, b in cal["schedule"][0] if t0 < T]


def receipt(cal, pb=None):
    pb = pb or playback(cal)
    L = leaf_list(cal, pb)
    per = {u: sum(1 for x in pb["starts"] if x[1] == u) for u in range(NU)}
    return dict(schema=cal["schema"], frame_tokens=cal["frame_tokens"], layers=cal["layers"], H=cal["H"], T=cal["T"],
                aggregate_tok_s=cal["aggregate_tok_s"], users=cal["users"], leaf_entries=len(L),
                starts_per_frame=per, fires_per_frame=len(pb["fires"]), op_groups=op_groups(cal["inputs"]),
                group_layout={g: {k: v for k, v in x.items() if k != "ops"} for g, x in cal["grp"].items()},
                descriptors={str(k): v for k, v in pb["desc"].items()},
                am_root=dict(span=AM_ROOT_SPAN, emits_per_frame=check_root_merge(cal)),
                emb=dict(EMB_T=EMB_T, AM_EMIT_T=AM_EMIT_T, RES_SSQ=RES_SSQ, RES_BANK=RES_BANK,
                         tok_slice0_edge=tok_slice0_edge(), head_tok_ofs=cal["inputs"].get("head_tok_ofs", 0),
                         token_starts_checked=check_emb_after_result(cal),
                         path="AMAX issue I -> W5 cmd_q +1 -> root merge + TOK to W5 tok_v +48 -> st +1 -> ctlm ss_q +1 "
                              "-> tok_b +1 = I + 52; EMB issue >= S + 8 + 52 (emb_token sampled on issue + 1)"),
                rules=dict(T0_MIN=T0_MIN, MIN_OP_CYC=MIN_OP_CYC, OP_ENTRY_OFS=OP_ENTRY_OFS, LEAF_MIN_GAP=LEAF_MIN_GAP))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, nargs="+", default=[16])
    ap.add_argument("--layers", type=int, default=36)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    for F in a.frames:
        cal = compile_frame(F, layers=a.layers)
        r = receipt(cal)
        print(F, round(r["aggregate_tok_s"], 1), [(u["user"], u["tokens_per_frame"], round(u["tok_s"], 1))
                                                  for u in r["users"]], "leaf", r["leaf_entries"], r["starts_per_frame"])
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / f"receipt_F{F}{'' if a.layers == 36 else f'_L{a.layers}'}.json").write_text(json.dumps(r, indent=1) + "\n")


if __name__ == "__main__":
    main()
