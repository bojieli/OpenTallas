"""MU-ADOPT-TOK 2026-10-19: case generator for MU.TOK.QW (the Qwen ROM 4-user token pass) and its command-plane smoke.

Input: the 4-user static calendar of record (mu_calendar.compile_calendar(dict(users=4, occupancy='measured',
head_chunks=8), tokens=6, policy='priority'), op granularity, 14,054 tok/s modelled).  Output (JSON, one file a variant):
  * per user: every placement unit (layer / op / head chunk / head) with its compiled start cycle, the RTL stage it
    starts (layer l -> stage l + 1, head chunk -> stage 37 (LAST_STAGE), head = next token's start -> stage 0), the user
    fields every command of that unit carries (qfd_dv_cmd_cal_mu relocation: VM / AR / DD / EM base + u * UVM_STRIDE,
    SU pidx + u * PIDX_STRIDE, XC tag[UTAG_LSB +: 2] = u; STN cmd[52:51] / AMAX cmd[9:8] = u for qfd_dv_amax_mu), and
    the user's token positions (pos0 + k: every user in the T8192 context bucket, so its attention window is the
    single-user one; distinct positions / prompts so per-user exactness is meaningful; per user disjoint KV rows);
  * KV rows: kv_user_rows (64 + l + 256 u) for every user-layer, = qkd_kv_mu_rowoff;
  * playability report against the MU RTL as built: qfd_dv_cmd_cal_mu has 4 descriptors (token start, decode layer,
    LM head, boot) and plays a layer as ONE rigid segment a start, so a calendar unit finer than a layer (op
    granularity, the record) cannot be played; the report counts the intra-layer op gaps per user (B1 of the spec);
  * command-plane resources the calendar of record does not model but the RTL faults on: one start port (start edges
    distinct across users), one cmd register (no two users' entries on one edge: fault_code[1]), one done register (no
    two segment ends on one edge: fault_code[3]).  Variants 'rtl_layer' and 'cmdplane4' compile WITH them
    (mu_calendar seg_windows hook); 'rtl_layer_nocmd' compiles without them (negative control: the RTL must fault).

Variants:
  record          the calendar of record (op granularity, 4 users) -> the real MU.TOK.QW case table (not RTL-playable
                  until B1 is fixed)
  record_cp       the record + the command-plane resources (start / cmd / done / stn), entries at the smoke image's
                  offsets: what the record costs once the shared command plane is scheduled too
  rtl_layer       layer granularity, of-record resources + command-plane edges -> what qfd_dv_cmd_cal_mu can play today
                  (2 users get placed: users 2, 3 never fit -- the 9,291 row of the record)
  rtl_layer_nocmd the same without the command-plane edges (negative control)
  record_op       MU-QW-B1 (2026-10-19): the op-granular PERIODIC calendar of mu_opcal (F = 16 latency tokens a frame,
                  13,708.2 tok/s since MU-OPCAL-EMB (EMB at T = 60, after the result; was 13,711.4), command plane
                  + am.root scheduled) as the RTL plays it: the latency user's stage starts
                  from the face, the fillers' op starts from the leaf ROM (qfd_sys_face_mu_dhuser OPSEG inside
                  qfd_tt_ctlm_dv OPSEG 1) with explicit entry ranges; every start {cycle, user, stage, first, cnt, src}
                  and the DV strides (UVM 4096 / PIDX 128, mu_calendar.DV_*).  RTL-playable (bench
                  rtl/test/mu_qwen_seq/mu_opseg_bench.py).  This is the MU.TOK.QW case table of record.
  cmdplane4       layer granularity, command-plane resources ONLY (me/su/kv/coll dropped): 4 users on the MU RTL
                  command plane at once; a STRESS case of the composition, NOT a production calendar (its rates mean
                  nothing; it is labelled so in every output)

The smoke image (one decode-layer segment, token-start/argmax segment, LM-head chunk segment, boot) is defined here so
the bench and the calendar's command-plane edges come from one source.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import mu_calendar as M

UVM_STRIDE, PIDX_STRIDE, UTAG_LSB = 0x4000, 64, 6     # = rtl/test/mu_qwen_seq (MU-QWEN-SEQ) relocation parameters
LAST_STAGE = 37
IMG_BASE = 64
STN_LAT = 40           # behavioural station: first result word of an amax STN STN_LAT edges after its issue,
RW, RW_GAP = 16, 20    # then RW result words (16 logits each) RW_GAP edges apart (a chunk = 256 rows; ends < 381 cycles)
CLK = 1.2e9


# ---------------------------------------------------------------------------------------------------- command words
def F(**kv):
    w = 0
    for _, (lsb, wid, val) in kv.items():
        assert 0 <= val < (1 << wid), (lsb, wid, val)
        w |= val << lsb
    return w


# MU-DQ-SLICEKC 10-19 (coordinator: kc on EVERY matvec STN): k steps per (round, j) of each matvec op's tiles.  The tiles
# stream their running accumulator every k step; qfd_dv_redstn2 keeps only the k = kc - 1 block of every pair, from STN
# cmd[66:59] = kc - 1 (QW-DIEFIX last-k, moved off the MU user [52:51] by MU-SLICE-GATE 4180abc13).  kc 1 there would
# pass every partial sum as a result (MUT 14 behaviour).  Source: the L0 stage-1 ROM command k fields
# (rtl/test/qwen_dv/xhead/xt1_prep.py OPS, tt_ctlm_prog unit_c4 log decoded by ibdec.dec380; = input dim / split:
# qkv 4096/512, o 512/256, gate/up 4096/128, down 1536/256); LM head = split 512 over 4096 (dv_lower: split 512 ->
# level 9 like qkv) -> 8.
MATVEC_KC = {"qkv": 8, "o_proj": 2, "gate_up": 32, "down": 6, "lm_head": 8}


def su(p):                 return F(go=(0, 1, 1), kind=(1, 3, 1), pidx=(4, 9, p), dst=(112, 4, 15))
def stn(db, kc, amax=0):   return F(go=(0, 1, 1), kind=(1, 3, 2), nw=(7, 8, 16), dst2=(24, 2, 1), db=(26, 24, db),
                                    amax=(50, 1, amax), kcm1=(59, 8, kc - 1), dst=(112, 4, 15))   # kc: no default
def ports(ar, dd, em):     return F(go=(0, 1, 1), kind=(1, 3, 4), ar=(4, 24, ar), dd=(28, 24, dd), aren=(52, 1, 1),
                                    dden=(53, 1, 1), em=(54, 24, em), dst=(112, 4, 15))
def xc(seg, words):        return F(go=(0, 1, 1), kind=(1, 3, 0), sub=(4, 2, 0), mode=(6, 1, 0), words=(7, 16, words),
                                    tag=(23, 32, seg), dst=(112, 4, 15))
def amax_cmd(clr, emit):   return F(go=(0, 1, 1), kind=(1, 3, 6), clr=(4, 1, clr), emit=(5, 1, emit), dst=(112, 4, 15))
def loc_emb():             return F(go=(0, 1, 1), kind=(1, 3, 1), dst=(112, 4, 14))
def loc_seg(b):            return F(go=(0, 1, 1), kind=(1, 3, 2), base=(4, 12, b), dst=(112, 4, 14))
def setid():               return F(go=(0, 1, 1), kind=(1, 3, 7), dst=(112, 4, 15))


def layer_segment(p=None):
    """one command a layer op at its op start + 8 (the filler first-entry rule T_0 >= 4 + (NU - 1)), from the
    production layer programme of record (mu_calendar.LAYER_WINDOWS): me -> STN to a per-op VM base, su -> SU pidx,
    attention -> loc_seg (the q record to the KV die; the bench applies qkd_kv_mu_rrow/wrow with the issuing user),
    all-reduce -> PORTS (landing region) + XC (256 words)"""
    p = dict(M.SOURCED, **(p or {}))
    ops = M.layer_block(p)["ops"]
    ent, k = [], 0
    for i, (op, unit, _, _) in enumerate(M.LAYER_WINDOWS):
        a = ops[op][0]
        if unit == "me":
            ent.append((a + 8, stn(0x100 + 0x40 * i, kc=MATVEC_KC[op])))
        elif unit == "su":
            ent.append((a + 8, su(1 + i)))
        elif unit == "kv":
            ent.append((a + 8, loc_seg(0x10)))
        elif unit == "coll":
            ent += [(a + 8, ports(0x1000 + 0x400 * k, 0x2000, 0x3000)), (a + 12, xc(k, p["ar_words"]))]
            k += 1
    ent.sort()
    for (t0, _), (t1, _) in zip(ent, ent[1:]):
        assert 1 <= t1 - t0 <= 4095, (t0, t1)
    return ent


def segments(p=None):
    return {1: layer_segment(p),
            # stage 0: emit prev argmax, open next, embedding.  SMOKE convention: the EMB at 16 precedes the result (stale
            # token); the op calendar of record (mu_opcal.segments) moves it to mu_opcal.EMB_T = 60 (MU-OPCAL-EMB)
            0: [(8, amax_cmd(0, 1)), (12, amax_cmd(1, 0)), (16, loc_emb())],
            2: [(8, stn(0x180, kc=MATVEC_KC["lm_head"], amax=1))],                                         # stage 37: one LM-head row chunk
            3: [(4, setid()), (8, su(30))]}                                       # boot


def image(segs):
    order, entries, desc = [1, 0, 2, 3], [], {}
    for s in order:
        while len(entries) % 4:
            entries.append(1 << 116)
        first, t = len(entries), 0
        for T, c in segs[s]:
            entries.append(((T - t) << 116) | c)
            t = T
        desc[s] = (first, len(segs[s]))
    assert IMG_BASE + 2 * len(entries) <= 976
    pw = [0] * 1024
    for e, v in enumerate(entries):
        pw[IMG_BASE + 2 * e] = v & ((1 << 64) - 1)
        pw[IMG_BASE + 2 * e + 1] = v >> 64
    dw = [(0x43414c44 << 32) | (IMG_BASE << 16) | len(entries)] + [(desc[s][0] << 16) | desc[s][1] for s in range(4)] \
        + [0, 0, 0]
    return pw, dw


def seg_windows(segs, start=True):
    """command-plane resources of each placement unit, offsets from its start (issue edge = S + T_k: C_issue_offset 0,
    measured by MU-QWEN-SEQ): cmd = every entry's issue edge, done = the last entry's edge, start = the start edge,
    stn = the slice STN register: an STN's issue edge, and for an amax STN (an LM-head chunk) from its issue to its last
    result word -- F-TOK-1: qfd_dv_amax_mu (as qfd_dv_slice2 today) gates and attributes station results by the CURRENT
    STN register (stn_amax / stn_u), so ANY user's STN issued while a chunk's results stream silently drops or
    misattributes them (no fault); the calendar must keep the station exclusive for that window"""
    def w(ent):
        d = {"cp.cmd": [(t, t + 1) for t, _ in ent], "cp.done": [(ent[-1][0], ent[-1][0] + 1)]}
        stns = [(t, t + (STN_LAT + RW * RW_GAP if (c >> 50) & 1 else 1)) for t, c in ent
                if (c >> 1) & 7 == 2 and (c >> 112) & 15 != 14]
        if stns:
            d["cp.stn"] = stns                                         # STN register + station result bus (F-TOK-1)
        if start:
            d["cp.start"] = [(0, 1)]
        return d
    return {"layer": w(segs[1]), "head.c": w(segs[2]), "head": w(segs[0])}


# ---------------------------------------------------------------------------------------------------- user fields
def reloc(c, u):
    """the word qfd_dv_cmd_cal_mu issues for user u (its relocation rule, u = 0 adds 0)"""
    kind, dst = (c >> 1) & 7, (c >> 112) & 15
    if u == 0 or dst == 14:
        return c

    def put(w, lsb, wid, v):
        assert v < (1 << wid)
        return (w & ~(((1 << wid) - 1) << lsb)) | (v << lsb)

    def get(w, lsb, wid):
        return (w >> lsb) & ((1 << wid) - 1)
    ub = u * UVM_STRIDE
    if kind == 4:
        for lsb in (4, 28, 54):
            c = put(c, lsb, 24, get(c, lsb, 24) + ub)
    elif kind == 2 and (c >> 24) & 1:
        c = put(c, 26, 24, get(c, 26, 24) + ub)
    elif kind == 1:
        c = put(c, 4, 9, get(c, 4, 9) + u * PIDX_STRIDE)
    elif kind == 0 and get(c, 4, 2) == 0:
        c = put(c, 23 + UTAG_LSB, 2, u)
    return c


def unit_stage(name):
    if name.startswith("head.c"):
        return LAST_STAGE
    if name == "head":
        return 0
    return int(name.split(".")[0][1:]) + 1


# ---------------------------------------------------------------------------------------------------- variants
VARIANTS = {
    "record": dict(granularity="op", p={}),
    "record_cp": dict(granularity="op", p={}, cmd=True),
    "rtl_layer": dict(granularity="layer", p={}, cmd=True),
    "rtl_layer_nocmd": dict(granularity="layer", p={}),
    "record_op": dict(granularity="op_leaf", p={}),
    "cmdplane4": dict(granularity="layer", p=dict(drop_resources=("me", "su", "kvs", "d2d", "coll", "host")), cmd=True),
}


def compile_variant(name, tokens=4):
    v = VARIANTS[name]
    segs = segments()
    p = dict(users=4, occupancy="measured", head_chunks=8, **v["p"])
    if v.get("cmd"):
        p["seg_windows"] = seg_windows(segs)
    cal = M.compile_calendar(p, tokens=tokens, granularity=v["granularity"], policy="priority")
    return cal, segs


def edge_clashes(cal, segs):
    """command-plane collisions of a compiled calendar as the RTL would see them (start port, cmd register, done)"""
    seg_of = lambda n: segs[2] if n.startswith("head.c") else segs[0] if n == "head" else segs[1]
    st, cm, dn = {}, {}, {}
    for u, seq in cal["schedule"].items():
        for n, t0, _ in seq:
            if "." in n and not n.startswith("head.c"):
                continue                                               # op units: not playable (B1)
            st.setdefault(t0, []).append(u)
            e = seg_of(n)
            for T, _ in e:
                cm.setdefault(t0 + T, []).append(u)
            dn.setdefault(t0 + e[-1][0], []).append(u)
    f = lambda d: sum(1 for v in d.values() if len(set(v)) > 1)
    return dict(start=f(st), cmd=f(cm), done=f(dn))


def playability(cal):
    out = {}
    for u, seq in cal["schedule"].items():
        gaps = sum(1 for (n0, t0, b0), (n1, t1, _) in zip(seq, seq[1:])
                   if t1 != t0 + b0["length"] and n0.startswith("L") and n0.split(".")[0] == n1.split(".")[0])
        out[u] = dict(units=len(seq), intra_layer_op_gaps=gaps)
    op = cal["granularity"] == "op"
    return dict(granularity=cal["granularity"], per_user=out,
                rtl_playable=not op or all(v["intra_layer_op_gaps"] == 0 for v in out.values()),
                reason=("qfd_dv_cmd_cal_mu plays a decode layer as ONE rigid segment a start (descriptors: token start / "
                        "layer / head / boot); a filler op that waits inside a layer has no stage to start it") if op else "")


def cases_record_op(frame_tokens=16, layers=36, pos0=(8186, 8180, 8174, 8168)):
    """record_op: mu_opcal's periodic op-granular frame as played by the face (user 0) + the op-start leaf (fillers)"""
    from . import mu_opcal as O
    cal = O.compile_frame(frame_tokens, layers=layers)
    pb = O.playback(cal)
    L = O.leaf_list(cal, pb)
    H = cal["H"]
    users = []
    for x in cal["users"]:
        k = x["user"]
        st = [dict(cycle=S, stage=stg, first=f, cnt=n, src=src, first_of_frame=bool(fl))
              for S, u, stg, f, n, src, fl in pb["starts"] if u == k]
        users.append(dict(user=k, tokens_completed=x["tokens_per_frame"], tokens_per_frame=x["tokens_per_frame"],
                          token_period=H / x["tokens_per_frame"], tok_s=x["tok_s"], first_start=x["first_start"],
                          pos=[pos0[k] + i for i in range(x["tokens_per_frame"])],
                          fields=dict(vm_ar_dd_em_base_add=k * M.DV_UVM_STRIDE, su_pidx_add=k * M.DV_PIDX_STRIDE,
                                      xc_tag_bits=f"[{M.DV_UTAG_LSB + 1}:{M.DV_UTAG_LSB}]={k}", stn_user_cmd_52_51=k,
                                      amax_user_cmd_9_8=k, hc_pos_17_16=k, root_result_user_ss5_27_26=k),
                          kv_rows={f"L{l}": M.kv_user_rows(4)[(k, l)] for l in range(layers)},
                          starts=st))
    return dict(schema="opentallas.qwen.mu_tok_cases.v1", variant="record_op", granularity="op_leaf",
                production_calendar=True, aggregate_tok_s_modelled=cal["aggregate_tok_s"],
                single_user_token_cycles=cal["T"], horizon_cycles=H, frame_tokens=frame_tokens, layers=layers,
                users=users, leaf=dict(entries=len(L), rom="ot_rom_4096x72_m8", min_gap=O.LEAF_MIN_GAP,
                                       header_word=hex(O.rom_words(cal, L)[0])),
                playability=dict(granularity="op_leaf", rtl_playable=True, per_user={},
                                 reason="B1 option 2: face = latency user's stage starts, op-start leaf = fillers' "
                                        "op starts with explicit ranges (qfd_dv_cmd_cal_mu start_rng)"),
                command_plane_clashes=dict(start=0, cmd=0, done=0, note="scheduled in mu_opcal (cp.*, am.root)"),
                inputs={k: v for k, v in cal["inputs"].items() if k != "seg_windows"},
                relocation=dict(UVM_STRIDE=M.DV_UVM_STRIDE, PIDX_STRIDE=M.DV_PIDX_STRIDE, UTAG_LSB=M.DV_UTAG_LSB),
                image_descriptors={str(k): v for k, v in pb["desc"].items()},
                image_segments={str(k): [[t, hex(c)] for t, c in v] for k, v in cal["segs"].items()})


def cases(name, tokens=None, pos0=(8186, 8180, 8174, 8168)):
    if name == "record_op":
        return cases_record_op(pos0=pos0)
    tokens = tokens or (6 if name.startswith("record") else 4)                 # record: the receipt's 6-token horizon
    cal, segs = compile_variant(name, tokens)
    users = []
    for u in cal["users"]:
        k = u["user"]
        seq = cal["schedule"][k]
        starts = [dict(unit=n, cycle=t0, stage=unit_stage(n), length=b["length"]) for n, t0, b in seq]
        users.append(dict(u, pos=[pos0[k] + i for i in range(u["tokens_completed"])],
                          fields=dict(vm_ar_dd_em_base_add=k * UVM_STRIDE, su_pidx_add=k * PIDX_STRIDE,
                                      xc_tag_bits=f"[{UTAG_LSB + 1}:{UTAG_LSB}]={k}", stn_user_cmd_52_51=k,
                                      amax_user_cmd_9_8=k, hc_pos_17_16=k),
                          kv_rows={f"L{l}": M.kv_user_rows(4)[(k, l)] for l in range(36)},
                          starts=starts))
    s = M.summary(cal)
    return dict(schema="opentallas.qwen.mu_tok_cases.v1", variant=name, granularity=cal["granularity"],
                production_calendar=name != "cmdplane4",
                aggregate_tok_s_modelled=cal["aggregate_tok_s"], single_user_token_cycles=cal["single_user_token_cycles"],
                horizon_cycles=cal["horizon_cycles"], users=users, playability=playability(cal),
                command_plane_clashes=edge_clashes(cal, segs) if cal["granularity"] == "layer" else None,
                inputs={k: v for k, v in s["inputs"].items() if k != "seg_windows"},
                relocation=dict(UVM_STRIDE=UVM_STRIDE, PIDX_STRIDE=PIDX_STRIDE, UTAG_LSB=UTAG_LSB),
                image_segments={str(k): [[t, hex(c)] for t, c in v] for k, v in segs.items()})


# ---------------------------------------------------------------------------------------------------- bench events
def bench_events(cs, t_end=None, c0=2, s0=1100, users=None):
    """event file for rtl/test/mu_qwen_tok/tb_mu_tok_compose.sv: image load (kinds 0/1), per-user AMAX prime (kind 3,
    the boot step that opens each user's first head), every RTL-playable start (kind 2 {user, stage}) shifted by s0"""
    segs = {int(k): [(t, int(c, 16)) for t, c in v] for k, v in cs["image_segments"].items()}
    pw, dw = image(segs)
    ev = [(c0 + a, 0, (a << 64) | pw[a]) for a in range(1024)] + [(c0 + 1024 + a, 1, (a << 64) | dw[a]) for a in range(8)]
    ev += [(c0 + 2 * u + 1, 3, u) for u in range(4)]
    sts = []
    for x in cs["users"]:
        u = x["user"]
        if users is not None and u not in users:
            continue
        for s in x["starts"]:
            if "." in s["unit"] and not s["unit"].startswith("head.c"):
                raise SystemExit(f"variant {cs['variant']} is not RTL-playable (op unit {s['unit']})")
            c = s0 + s["cycle"]
            if t_end is None or c < t_end:
                sts.append((c, u, s["stage"], s["unit"]))
                ev.append((c, 2, (u << 6) | s["stage"]))
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev, sts, segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=sorted(VARIANTS), action="append")
    ap.add_argument("--tokens", type=int, default=None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--brief", action="store_true", help="one summary file (no per-unit start tables)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    brief = {}
    for v in a.variant or sorted(VARIANTS):
        cs = cases(v, a.tokens)
        if a.brief:
            brief[v] = dict({k: x for k, x in cs.items() if k not in ("users", "image_segments")},
                            users=[{k: x for k, x in u.items() if k not in ("starts", "kv_rows")} for u in cs["users"]])
        else:
            (a.out / f"cases_{v}.json").write_text(json.dumps(cs, indent=1) + "\n")
        print(v, round(cs["aggregate_tok_s_modelled"], 1), [(u["user"], u["tokens_completed"], u["token_period"])
                                                            for u in cs["users"]],
              "playable" if cs["playability"]["rtl_playable"] else "NOT-playable", cs["command_plane_clashes"])
    if a.brief:
        (a.out / "cases_summary.json").write_text(json.dumps(brief, indent=1) + "\n")


if __name__ == "__main__":
    main()
