#!/usr/bin/env python3
"""MU-QW-B1 bench (2026-10-19): op-granular 4-user playback through the DV compute-die control cluster qfd_tt_ctlm_dv
NU 4 OPSEG 1 (the op-start leaf qfd_sys_face_mu_dhuser OPSEG inside the cluster + qfd_dv_cmd_cal_mu explicit-range
starts), against the compiled periodic calendar tools/qwen_static_schedule/mu_opcal.py (one source: DV image, leaf ROM
image ot_rom_4096x72_m8 via-map, playback starts / fires).

    mu_opseg_bench.py --work DIR [--mut M] [--cases full red neg_drift neg_coll] [--verilator PATH] [--jobs N]

Cases:
  full       mu_opcal F = 16, 36 layers (H = 4,025,840 edges): the face plays the latency user's stage starts (user 0
             only), the leaf the fillers' op starts; the run covers frame 0 and the first FULL_TAIL edges of frame 1
             (anchor check at the frame wrap, frame-1 entries).  Reference: NU 1 OPSEG 0 with user 0's starts only.
  red        mu_opcal F = 16, 2 layers (H = 279,856): RED_FRAMES frames (steady state: every frame after frame 0 plays
             every entry), the same checks, per-user measured token rates in frame 1.
  neg_drift  red, the latency user's 2nd L0 start one edge late: the leaf must raise op_fcode[1] (anchor drift).
  neg_coll   red, an extra face start on a leaf start's edge: the cluster must raise op_fault (start collision).
  ctx_part   red (1 + 1 frames) with the boot context record loading users 1 and 3 only (mask 0b101): user 2's bank starts
             at 0 (MU-QW-DIE 10-19).
  neg_ctx    red, the context record with a bad tag: the cluster must raise op_fault on the seal edge (and load nothing).
  d2d_ctx    red (RED_FRAMES frames) + the RUNTIME filler context (MU-DQ-BOOTCTX 10-19, coordinator 0kg): for users 1..3 one
             KV-die D2D HOST context record (kind 12, filler field {user, seq, tok, pos}) through the real receiver
             qfd_host_native_context_rx FILL 1 + the face decoder qfd_sys_face_fill_ctx onto dh's DW lane; each replaces
             that user's result number seq (the bank takes the record's tok / pos instead of argmax / pos + 1).
  neg_late   red, a record for user 1 arriving AFTER the result it names: the cluster must raise op_fault on the arming
             edge (record slot + 4) and arm nothing.
Checks (PASS needs all; positive cases):
  C1 no calendar fault, no start_fault, no op_fault / leaf fault code;
  C2 latency user identity vs the NU 1 reference: user 0's CMD (cycle + word), EMB / SEG / MES, the head SU accepted
     count, dc on every change (filler results must not reach the face's RESULT capture), and the head-side outputs up
     to the first filler LOCAL SEG (the head is shared from then on);
  C3 every u_cal start (cycle, user, stage, range) == the compiled playback (face starts of user 0, leaf starts of the
     fillers: S = t_rom + 1 of every leaf entry, frame k at k x H; in frame 0 a filler's entries before its FIRST entry
     are not started -- they are the tails of tokens that began in the previous frame);
  C4 every user's command fire == the compiled fire (cycle and word, the user's relocation): fires derive from the
     compiled starts and the image entries [first, first + cnt);
  C5 filler token / position: every filler LOCAL EMB sends, and every filler LOCAL SEG starts the ME segment with, the
     filler's bank: its BOOT CONTEXT RECORD (MU-QW-DIE 10-19, coordinator 0ka: the calendar image's DW5 / DW6,
     mu_opcal.ctx_words, loaded on the seal edge; the bench-only preload is gone), then tok = the root token and pos + 1
     at each of the user's results (ss5 tok_v, ss5[27:26] = user);
  C6 the head running stage after every ME start = that segment's user's stage (per-user stage bank);
  C7 (MU-OPCAL-EMB 10-19) every filler's token-start LOCAL EMB sends that user's JUST-COMPUTED token: the root result of
     the AMAX emit of the same token-start segment.  The result reaches ss5 (the ctlm ss_q capture edge) at the RTL-derived
     edge mu_opcal.RES_SSQ after the emit's issue edge (W5 cmd_q, root merge + TOK to W5, slice st, ctlm pin register),
     and tok_b is written mu_opcal.BANK_WR later (exact model; no ambiguity margin).
Bench witnesses (mut 0 RTL, compiled-model mutants; each must FAIL C7): --emb-t 16 (the pre-fix image: EMB at T = 16,
compiler assertion bypassed), --res-skew 1 (the result one edge later than derived: the EMB at EMB_T is exactly the first
edge that sees it).
Negative cases: the named fault rises on the named edge.
Mutants (--mut, each must FAIL): 21 range ignored (descriptor plays), 22 collision not flagged, 23 filler result into
the next filler's bank, 24 leaf entry one edge late, 25 leaf re-anchors on every L0 start (anchor drift), 26 leaf drift
check dropped, 27 context record never loaded (red), 28 records rotated between fillers (red), 29 record not checked
(neg_ctx), 32 runtime record armed into the wrong user (d2d_ctx), 33 runtime seq / late check dropped (neg_late).
C8 (d2d_ctx): every record armed (RTA log: label = slot + 3, armed on slot + 4; user, tok, pos) and no receiver / face-fill fault (RXF).
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_static_schedule import mu_opcal as O            # noqa: E402

TB = HERE / 'tb_mu_opseg_dv.sv'
SRCF = ROOT / 'rtl/test/qwen_dv/tt_ctlm_dv_sources.f'
INST = 'qfd_tt_ctlm_opseg'
S0 = 1100                       # event cycle of the latency user's first L0 start (frame time 0)
FULL_TAIL = 30000
RED_FRAMES = 3
C_CAL = 1                       # u_cal issue edge = start event + entry T + C_CAL (measured C of the reference run)
RES_LAT = O.AM_EMIT_T + C_CAL + O.RES_SSQ    # a user's root result at ctlm ss_q: RTL-derived (MU-OPCAL-EMB; was 8 + 32)
RES_SKEW = 0                    # bench witness --res-skew
NU = 4
PRE = {u: (0x2000 + 0x111 * u, 8186 - 6 * u) for u in range(1, NU)}   # filler boot context record (tok, pos): image DW5 / DW6
CTX = dict(mask=None, tag=O.CTX_TAG)                                   # per case (ctx_part: mask {1, 3}; neg_ctx: bad tag)
RT = dict(recs=[])                  # d2d_ctx / neg_late: runtime records [(event cycle, user, seq, tok, pos)]
RT_ARM = 4                          # record slot event cycle -> armed (face fill reg, dh pin, u_cal ctx_rt, arm)
RT_SEQ = {1: 1, 2: 2, 3: 1}         # d2d_ctx: the result each filler's record replaces
U0 = (0x1100, 8186)


def tok0(i): return (U0[0] + 7 * i) & 0x3FFFF
def res_tok(u, n): return (0x1000 * u + 0x35 * n + 3) & 0x3FFFF


def build(work, vl, nu, opseg, mut, jobs):
    d = work / f'b_nu{nu}_o{opseg}_m{mut}'
    exe = d / 'Vtb_mu_opseg_dv'
    if exe.exists(): return exe
    srcs = [str(ROOT / l.strip()) for l in SRCF.read_text().split('\n') if l.strip()]
    srcs += [str(ROOT / 'rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv'),
             str(ROOT / 'rtl/qwen_split/qfd_sys_face_record_port.sv')]
    cmd = [vl, '--binary', '--timing', '-O2', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
           '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_mu_opseg_dv',
           f'-GNU={nu}', f'-GMUT={mut}', f'-GOPSEG={opseg}', '-Mdir', str(d)] + srcs + [str(TB)]
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode != 0 or not exe.exists():
        sys.exit(f'BUILD FAILED nu{nu} o{opseg} m{mut}: see {d}/build.log\n' + (r.stdout + r.stderr)[-3000:])
    return exe


def run(work, exe, name, events, ncyc, romdir):
    events = sorted(events, key=lambda e: (e[0], e[1]))
    evf, lg = work / f'{name}.ev', work / f'{name}.log'
    evf.write_text(''.join(f'{c} {k} {v:x}\n' for c, k, v in events))
    args = [str(exe), f'+EV={evf}', f'+LOG={lg}', f'+NCYC={ncyc}', f'+OT_ROM_DIR={romdir}']
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0: sys.exit(f'RUN FAILED {name}: {r.stdout[-2000:]} {r.stderr[-2000:]}')
    out = {k: [] for k in ('cmd', 'emb', 'seg', 'mes', 'sua', 'hd', 'cst', 'dc', 'sta', 'faults', 'opf', 'rta', 'rxf')}
    out['end'] = None
    for ln in lg.read_text().split('\n'):
        p = ln.split()
        if not p: continue
        c, k = int(p[0]), p[1]
        if k == 'CMD': out['cmd'].append((c, int(p[2]), int(p[3], 16)))
        elif k == 'EMB': out['emb'].append((c, int(p[2]), int(p[3], 16)))
        elif k == 'SEG': out['seg'].append((c, int(p[2]), int(p[3], 16), int(p[4], 16), int(p[5], 16)))
        elif k == 'MES': out['mes'].append((c, int(p[2], 16), int(p[3], 16)))
        elif k == 'SUA': out['sua'].append((c, int(p[2])))
        elif k == 'HD': out['hd'].append((c, p[2]))
        elif k == 'CST': out['cst'].append((c, int(p[2])))
        elif k == 'DC': out['dc'].append((c, p[2]))
        elif k == 'STA': out['sta'].append((c,) + tuple(int(x) for x in p[2:7]))
        elif k == 'FAULT': out['faults'].append((c, p[2]))
        elif k == 'OPF': out['opf'].append((c, p[2], int(p[3])))
        elif k == 'RTA': out['rta'].append((c, int(p[2]), int(p[3], 16), int(p[4], 16)))
        elif k == 'RXF': out['rxf'].append((c, int(p[2]), int(p[3])))
        elif k == 'END': out['end'] = (int(p[2]), p[3], int(p[4]), int(p[5]), p[6])
    return out


# ------------------------------------------------------------------------------------------------ the compiled model
def model(cal, nfr, ncyc_ev):
    """face events, expected starts and result events in EVENT cycles (an event at cycle c = a u_cal start consumed on
    the edge the face's h_start at c reaches it).  starts = [(c, user, stage, rng, first, cnt)]"""
    pb = O.playback(cal)
    H, T, F = cal['H'], cal['T'], cal['frame_tokens']
    L = O.leaf_list(cal, pb)
    desc = pb['desc']
    face, starts = [], []
    for k in range(nfr):
        for n, t0, b in cal['schedule'][0]:
            c = S0 + k * H + t0
            if c >= ncyc_ev: continue
            i = k * F + t0 // T
            seg = 0 if b['stage'] == 0 else 2 if b['stage'] == O.LAST_STAGE else 1
            face.append((c, 0, b['stage'], tok0(i), (U0[1] + i) & 0x3FFFF))
            starts.append((c, 0, b['stage'], 0, desc[seg][0], desc[seg][1]))
    first_t = {u: min(t for t, uu, s, f, n, ff in L if uu == u and ff) for u in range(1, NU)}
    for k in range(nfr):
        for t, u, stg, f, n, ff in L:
            if k == 0 and t < first_t[u]: continue                 # tail of a token begun in the previous frame
            c = S0 + k * H + t + 1
            if c < ncyc_ev: starts.append((c, u, stg, 1, f, n))
    starts.sort()
    res, nres = [], {u: 0 for u in range(NU)}
    for c, u, stg, rng, f, n in starts:
        if stg == 0:
            res.append((c + RES_LAT + RES_SKEW, u, res_tok(u, nres[u]), (0x51 * (u + 1) + nres[u]) & 0xFFFFFF))
            nres[u] += 1
    return pb, L, face, starts, res


def image_entries(pw):
    ent = []
    for e in range(0, (976 - 64) // 2):
        v = pw[64 + 2 * e] | (pw[64 + 2 * e + 1] << 64)
        ent.append((v >> 116, v & ((1 << 116) - 1)))
    return ent


def expected_fires(starts, ent, K, C):
    """from every (logged-convention) start: CMD (cycle, user, word) and LOCAL EMB / SEG (cycle, user, kind/base)"""
    cmd, loc = [], []
    for c, u, stg, rng, f, n in starts:
        t = c + C
        for e in range(f, f + n):
            d, w = ent[e]
            t += d
            if not w & 1: continue
            if (w >> 112) & 15 == 14:
                loc.append((t + 1, u, 'EMB' if (w >> 1) & 7 == 1 else 'SEG', (w >> 4) & 0xFFF))
            else:
                cmd.append((t, u, O.reloc(w, u)))
    return sorted(cmd), sorted(loc)


def events_for(pb, face, res, users, ctx=True):
    pw, dw = pb['pw'], pb['dw']
    if ctx:                       # the NU 4 OPSEG cluster: the boot context record in DW5 / DW6 (the NU 1 reference: plain)
        dw = O.with_ctx(dw, PRE, CTX['mask'], CTX['tag'])
    ev = [(2 + a, 0, (a << 64) | pw[a]) for a in range(1024)] + [(2 + 1024 + a, 1, (a << 64) | dw[a]) for a in range(8)]
    for c, u, stg, tok, pos in face:
        ev.append((c, 2, (u << 43) | (1 << 42) | (stg << 36) | (tok << 18) | pos))
    for c, u, tok, val in res:
        if u in users: ev.append((c, 3, (u << 42) | (val << 18) | tok))
    if ctx:
        for c, u, seq, tok, pos in RT['recs']:
            ev.append((c, 4, (seq << 38) | (u << 36) | (tok << 18) | pos))
    return ev


def rt_records(res, seqs):
    """one runtime record per filler: midway between the result before the replaced one and the replaced result"""
    recs = []
    for u, q in sorted(seqs.items()):
        rs = sorted(c for c, uu, tok, val in res if uu == u)
        lo = rs[q - 1] if q >= 1 else S0
        c = (lo + rs[q]) // 2
        assert c + RT_ARM <= rs[q] and c > lo + 2, (u, q, lo, rs[q])
        recs.append((c, u, q, 0x10000 + 0x101 * u, 4000 + 17 * u))
    return recs


def check_case(name, cal, nfr, ncyc_ev, e1, e4, work, romdir, mut, fails, summ):
    pb, L, face, starts, res = model(cal, nfr, ncyc_ev)
    H = cal['H']
    ncyc = ncyc_ev
    sol = run(work, e1, f'{name}_solo', events_for(pb, face, res, {0}, ctx=False), ncyc, romdir)
    mu = run(work, e4, f'{name}_mu', events_for(pb, face, res, set(range(NU))), ncyc, romdir)
    end_cut = ncyc - 8
    # C1
    for n, r in (('solo', sol), ('mu', mu)):
        e = r['end']
        if r['faults'] or r['opf'] or r['rxf'] or e is None or e[0] or e[2] or e[3] or e[4] != '0000':
            fails.append(f'{name} C1 {n} faulted: cal {r["faults"][:3]} opf {r["opf"][:3]} rxf {r["rxf"][:2]} end {e}')
    # C8 runtime records: each armed RT_ARM edges after its slot, for its user, with its tok / pos (the RTA line is
    # labelled with the posedge before the arming one, as STA: rt_arm is the D of the pending register)
    w8 = sorted((c + RT_ARM - 1, u, tok, pos) for c, u, q, tok, pos in RT['recs'])
    if sorted(mu['rta']) != w8:
        fails.append(f'{name} C8 runtime context arms {sorted(mu["rta"])[:4]} != records {w8[:4]}')
    # calibration from the reference: K = STA log cycle - event cycle, C = fire log cycle - (start log + entry time)
    sta1 = sol['sta']
    K = sta1[0][0] - S0 if sta1 else 0
    ent = image_entries(pb['pw'])
    f0 = starts[0]
    t_first = f0[0] + K + ent[f0[4]][0]
    first_cmd = [x for x in sol['cmd'] if x[0] >= S0]
    C = first_cmd[0][0] - t_first if first_cmd else 0
    if K != 0 or C != C_CAL:
        fails.append(f'{name} calibration K {K} C {C} != (0, {C_CAL}): the result events assume them')
    st_exp = sorted((c + K, u, stg, rng, f if rng else 0, n if rng else 0) for c, u, stg, rng, f, n in starts if c + K < end_cut)
    st_got = sorted((c, u, stg, rng, f if rng else 0, n if rng else 0) for c, u, stg, rng, f, n in mu['sta'] if c < end_cut)
    st_sol = sorted((c, u, stg, rng, 0, 0) for c, u, stg, rng, f, n in sol['sta'] if c < end_cut)
    if st_sol != [x for x in st_exp if x[1] == 0]:
        fails.append(f'{name} C3 reference face starts != compiled ({len(st_sol)} vs {len([x for x in st_exp if x[1] == 0])})')
    if st_got != st_exp:
        miss = [x for x in st_exp if x not in st_got][:3]; extra = [x for x in st_got if x not in st_exp][:3]
        fails.append(f'{name} C3 u_cal starts != compiled playback ({len(st_got)} vs {len(st_exp)}; missing {miss}; extra {extra})')
    lstarts = [(c + K, u, stg, rng, f, n) for c, u, stg, rng, f, n in starts]
    w_cmd, w_loc = expected_fires(lstarts, ent, K, C)
    w_cmd = [x for x in w_cmd if x[0] < end_cut]
    g_cmd = sorted(x for x in mu['cmd'] if S0 <= x[0] < end_cut)
    if g_cmd != w_cmd:
        miss = [x for x in w_cmd if x not in set(g_cmd)][:2]; extra = [x for x in g_cmd if x not in set(w_cmd)][:2]
        fails.append(f'{name} C4 command fires != compiled (got {len(g_cmd)} want {len(w_cmd)}; missing '
                     f'{len(set(w_cmd) - set(g_cmd))} e.g. {str(miss)[:240]}; extra {len(set(g_cmd) - set(w_cmd))} e.g. {str(extra)[:240]})')
    # C5 per-user bank model (fillers; user 0 = its latest face start), result applied RES_APPLY edges after its event
    RES_APPLY = O.BANK_WR           # exact: ss_q capture edge c -> tok_b written on c + 1 (read by an EMB / SEG logged >= c + 2)
    rlog = {u: sorted((c + RES_APPLY, tok) for c, uu, tok, val in res if uu == u) for u in range(NU)}
    rrep = {(u, q): (tok, pos) for c, u, q, tok, pos in RT['recs']}       # runtime records replace result q of user u
    rnum, rcnt = {}, {}
    for c, u, tok, val in sorted(res):
        rnum[(c, u)] = rcnt.get(u, 0); rcnt[u] = rnum[(c, u)] + 1
    flog = sorted((c + K, tok, pos) for c, u, stg, tok, pos in face)

    def bank(u, c):
        if u == 0:
            v = [x for x in flog if x[0] < c]
            return (v[-1][1], v[-1][2]) if v else (0, 0)
        tok, pos = PRE[u] if (CTX['mask'] is None or u in CTX['mask']) else (0, 0)
        for n, (rc, rt) in enumerate(rlog[u]):
            if rc <= c:
                if (u, n) in rrep: tok, pos = rrep[(u, n)]
                else: tok, pos = rt, pos + 1
        return tok, pos
    w_emb = sorted((t, u, bank(u, t - 1)[0]) for t, u, k, b in w_loc if k == 'EMB' and t < end_cut)
    w_seg = sorted((t, u, b) + bank(u, t - 1) for t, u, k, b in w_loc if k == 'SEG' and t < end_cut)
    g_emb = sorted(x for x in mu['emb'] if S0 <= x[0] < end_cut)
    g_seg = sorted(x for x in mu['seg'] if S0 <= x[0] < end_cut)
    for k, g, w in (('EMB', g_emb, w_emb), ('SEG', g_seg, w_seg)):
        if g != w:
            miss = [x for x in w if x not in g][:2]; extra = [x for x in g if x not in w][:2]
            fails.append(f'{name} C5 {k} (cycle, user, tok[, pos]) != compiled bank (got {len(g)} want {len(w)}; missing {miss}; extra {extra})')
    # C7 each filler EMB = its own just-computed token (the result of the same token-start segment's emit)
    seg0 = [t for t, w in cal['segs'][0] if O._is_emb(w)][0]
    w7 = sorted((c - RES_LAT - RES_SKEW + K + C + seg0 + 1, u, rrep.get((u, rnum[(c, u)]), (tok,))[0])
                for c, u, tok, val in res if u != 0)
    w7 = [x for x in w7 if x[0] < end_cut]
    g7 = [x for x in g_emb if x[1] != 0]
    bad7 = [x for x in g7 if x not in set(w7)]
    if len(g7) != len(w7) or bad7:
        fails.append(f'{name} C7 filler EMB != its just-computed token ({len(bad7)} of {len(g7)} wrong, want {len(w7)}; '
                     f'e.g. {bad7[:2]})')
    u0_emb = [x for x in g_emb if x[1] == 0]
    u0_res = {c - RES_LAT - RES_SKEW + K + C + seg0 + 1: tok for c, u, tok, val in res if u == 0}
    c7_u0 = dict(emb=len(u0_emb), equal_just_computed=sum(1 for t, u, tok in u0_emb if u0_res.get(t) == tok),
                 note='user 0 EMB sends tok_b[0] = the face stage-0 start token (no ss5 result write for user 0)')
    # C2 latency user identity
    fseg = [x[0] for x in mu['seg'] if x[1] != 0]
    hcut = min(fseg) if fseg else 10 ** 12
    pick = lambda r, cut: dict(cmd=[x for x in r['cmd'] if x[1] == 0 and x[0] < end_cut],
                               emb=[x for x in r['emb'] if x[1] == 0 and x[0] < end_cut],
                               seg=[x for x in r['seg'] if x[1] == 0 and x[0] < end_cut],
                               mes=[x for x in r['mes'] if x[0] < end_cut], sua=r['sua'], dc=r['dc'],
                               hd=[x for x in r['hd'] if x[0] < cut])
    a0, b0 = pick(sol, hcut), pick(mu, hcut)
    for k in a0:
        if a0[k] != b0[k]:
            d = [x for x in b0[k] if x not in a0[k]][:2] + [x for x in a0[k] if x not in b0[k]][:2]
            fails.append(f'{name} C2 latency user {k} differs mu vs solo ({len(a0[k])}/{len(b0[k])}; first diffs {str(d)[:300]})')
    # C6 head running stage after each ME start
    runst = {}
    for c, u, stg, rng, f, n in sorted(lstarts):
        runst.setdefault(u, []).append((c, stg))

    def stage_of(u, c):
        v = [s for cc, s in runst.get(u, []) if cc <= c]
        return v[-1] if v else 0

    def cst_at(c):
        v = 0
        for cc, s in mu['cst']:
            if cc <= c: v = s
        return v
    bad = [(c, u, cst_at(c + 1), stage_of(u, c)) for c, u, b, t, p in g_seg if cst_at(c + 1) != stage_of(u, c)]
    if bad: fails.append(f'{name} C6 head running stage wrong at {len(bad)} ME starts, e.g. {bad[:3]}')
    # measured rates (token-start segment starts of each user in the last full frame inside the run)
    meas = {}
    if nfr >= 2 and S0 + 2 * H + K < end_cut:
        a, b = S0 + H + K, S0 + 2 * H + K
        for u in range(NU):
            n = sum(1 for x in mu['sta'] if a <= x[0] < b and x[1] == u and x[2] == 0)
            meas[u] = dict(tokens=n, tok_s=round(n * O.CLK / H, 1))
    summ[name] = dict(H=H, T=cal['T'], ncyc=ncyc, K=K, C=C, starts=len(st_got), starts_per_user={u: sum(1 for x in st_got if x[1] == u) for u in range(NU)},
                      fires=len(g_cmd), fires_per_user={u: sum(1 for x in g_cmd if x[1] == u) for u in range(NU)},
                      emb=len(g_emb), seg=len(g_seg), c7_filler_emb=len(g7), c7_bad=len(bad7), c7_user0=c7_u0,
                      emb_t=seg0, res_lat=RES_LAT + RES_SKEW, leaf_entries=len(L), head_identity_window=[S0, hcut],
                      measured_frame1=meas, compiled=[dict(user=x['user'], tokens_per_frame=x['tokens_per_frame'], tok_s=round(x['tok_s'], 1)) for x in cal['users']])


def neg_case(name, cal, e4, work, romdir, fails, summ):
    H, T = cal['H'], cal['T']
    pb, L, face, starts, res = model(cal, 1, S0 + 2 * T + 2000)
    if name == 'neg_late':
        # user 1's record naming result 1, arriving 2 edges AFTER that result's event: op_fault on its arming edge
        pb, L, face, starts, res = model(cal, 2, S0 + 2 * H)
        r1 = sorted(c for c, u, tok, val in res if u == 1)
        RT["recs"] = [(r1[1] + 2, 1, 1, 0x10101, 4017)]
        want_edge = r1[1] + 2 + RT_ARM
    elif name == 'neg_ctx':
        # the context record with a bad tag: op_fault on the seal edge (DW7 event at 2 + 1024 + 7, + dh_q + seal + load)
        want_edge = 2 + 1024 + 7 + 2
    elif name == 'neg_drift':
        # the latency user's L0 start of token 1 one edge late
        face = [(c + 1, u, s, t, p) if (s == 1 and c == S0 + T) else (c, u, s, t, p) for c, u, s, t, p in face]
        want_edge = S0 + T
    else:
        # an extra face start (token start, stage 0) on the edge of the first leaf start after the fillers' FIRST entries
        lst = [x for x in starts if x[1] != 0 and x[0] > S0 + 4000]
        want_edge = lst[0][0]
        face = sorted(face + [(want_edge, 0, 0, tok0(0), U0[1])])
    ncyc = want_edge + 3000
    if name == 'neg_ctx':
        CTX['tag'] = O.CTX_TAG ^ 0x0100
    if name == 'neg_late':
        ncyc = max(ncyc, RT['recs'][0][0] + 3000)
    r = run(work, e4, name, events_for(pb, face, res, set(range(NU))), ncyc, romdir)
    CTX['tag'] = O.CTX_TAG
    RT['recs'] = []
    if name in ('neg_ctx', 'neg_late'):
        hit = [x for x in r['opf'] if x[1] == '0000' and x[2] == 0]   # op_fault, no leaf code, no collision
    elif name == 'neg_drift':
        hit = [x for x in r['opf'] if x[1][2] == '1']          # op_fcode[1] (string is MSB first: [3][2][1][0])
    else:
        hit = [x for x in r['opf'] if x[1] == '0000']           # op_fault rose with no leaf fault: the collision
    ok = bool(hit) and abs(hit[0][0] - want_edge) <= 4 and not (name == 'neg_late' and r['rta'])
    if not ok:
        fails.append(f'{name}: required fault not raised at ~{want_edge} (opf log {r["opf"][:4]})')
    summ[name] = dict(want_edge=want_edge, opf=r['opf'][:4], raised=ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--cases', nargs='+', default=['red', 'ctx_part', 'd2d_ctx', 'neg_drift', 'neg_coll', 'neg_ctx',
                                                   'neg_late', 'full'])
    ap.add_argument('--full-frames', type=int, default=1)
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', 'verilator')); ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--emb-t', type=int, default=None, help='witness: image EMB at this T (compiler assertion bypassed)')
    ap.add_argument('--res-skew', type=int, default=0, help='witness: result events this many edges later than derived')
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    global RES_SKEW
    RES_SKEW = a.res_skew
    cp = {} if a.emb_t is None else dict(emb_t=a.emb_t, check_emb=False)
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    m = a.mut
    e1 = build(work, a.verilator, 1, 0, 0, a.jobs)
    e4 = build(work, a.verilator, NU, 1, m, a.jobs)
    fails, summ = [], dict(mut=m, cases=a.cases, emb_t=a.emb_t, res_skew=a.res_skew)
    cals = {}

    def romdir_for(key, cal):
        d = work / f'rom_{key}{a.tag}'
        d.mkdir(exist_ok=True)
        (d / f'{INST}.viamap.hex').write_text(O.viamap_hex(O.rom_words(cal)))
        return d
    for case in a.cases:
        if case == 'full':
            cal = cals.setdefault('full', O.compile_frame(16, layers=36, p=cp))
            rd = romdir_for('full', cal)
            nfr = a.full_frames + 1
            ncyc = S0 + a.full_frames * cal['H'] + FULL_TAIL
            check_case('full', cal, nfr, ncyc, e1, e4, work, rd, m, fails, summ)
        else:
            cal = cals.setdefault('red', O.compile_frame(16, layers=2, p=cp))
            rd = romdir_for('red', cal)
            if case == 'red':
                check_case('red', cal, RED_FRAMES + 1, S0 + RED_FRAMES * cal['H'] + 2000, e1, e4, work, rd, m, fails, summ)
            elif case == 'd2d_ctx':
                _pb, _L, _face, _st, res = model(cal, RED_FRAMES + 1, S0 + RED_FRAMES * cal['H'] + 2000)
                RT['recs'] = rt_records(res, RT_SEQ)
                summ['d2d_records'] = RT['recs']
                check_case('d2d_ctx', cal, RED_FRAMES + 1, S0 + RED_FRAMES * cal['H'] + 2000, e1, e4, work, rd, m, fails, summ)
                RT['recs'] = []
            elif case == 'ctx_part':
                CTX['mask'] = {1, 3}
                check_case('ctx_part', cal, 2, S0 + cal['H'] + 2000, e1, e4, work, rd, m, fails, summ)
                CTX['mask'] = None
            else:
                neg_case(case, cal, e4, work, rd, fails, summ)
        print(f'case {case} done: {len(fails)} fails so far', flush=True)
    summ['verdict'] = 'PASS' if not fails else 'FAIL'
    summ['fails'] = fails
    (work / f'summary_m{m}{a.tag}.json').write_text(json.dumps(summ, indent=1, default=str))
    print(f"MU_OPSEG_{summ['verdict']} mut {m}{a.tag}" + ('' if not fails else ': ' + ' | '.join(fails)))
    print(json.dumps({k: v for k, v in summ.items() if k != 'fails'}, default=str))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
