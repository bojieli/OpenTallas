#!/usr/bin/env python3
"""TOK-S81-GAPS/XS2b (10-19): the slice x-streamer programme of the DV field placement -- what ot_s81sl_xs needs to
drive the frames of a slice with the phases xs_place.py compiles, and the capture-root configuration of those phases.

ot_s81sl_xs (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv) streams x from its own ROMs on a static calendar:
  CALENDAR  pq_calendar_action / pq_calendar_time (two ot_rom_4096x72_m8, the production paired calendar ROM,
            tools/s81_static_control/pq_calendar.action_word 75-b ABI, row = (timestamp << 75) | action): per phase
            ACCEPT (accept_tag, with the is_d GO), CFG (cfg_tag), LAUNCH (launch_tag = the frame go), one STREAM_REQ row
            per stream word (stream_tag / pos / fam / lastpos / lastop; the ROM address rides ADDR_LEAD = 2 rows later,
            stream_addr = sbase + word), RETIRE, and one final PHASE_END row.
  PHASE / STREAM ROMs  pq_phase0, pq_stream0..3 = the field's spine_phase / spine_stream words (lower_xs.xs_roms).
  is_d      the issuer words (160 b, ABI in the RTL header): the ring-arrival offset load, calendar PRIME / START,
            the gather window (family, buffer parity) and per phase the GO word {go, ph = field phase, np}.
  gathers   the x of the phase as ring all-gather beats (own / W / E, ring order of tools/s81_slice/xs_program.py).

THE STREAM SCHEDULE.  The frame return plan (frame_return_plan / xs_place ELEM_SEG) was measured on the frame bench
(tb_s81dv_frame.sv), whose x comes from the w17w10 PQ spine.  That spine streams one word per edge from go + 2 but
STALLS a beat until its x block is loaded (VM read 64 elements / edge into the act-quant: block data for load j present
at accept + LQ + j, LQ = 17; BF16: LB = 4), and the bench delays the x payload XDLY = 4 edges behind cfg / go.  The
calendar reproduces that word sequence exactly (stall-for-stall), so the frame sees the identical x words D edges
later and every return word lands on its planned edge + D -- the plan stays valid unchanged.  The xs itself never
stalls (x is in its buffer before the stream starts): the stalls are a property of the calibration vehicle that the
calendar keeps (cost = the stall edges per phase, reported; removing them needs the element terms re-measured on the xs
bench).

THE CAPTURE ROOT (ot_s81sl_cap cfg_d, per slice and die-wide phase): row tag -> the owning slice's output word.  The
cap decodes e = row - rbase (rcnt rows), leaf = (e >> 6) mod 5, word = obase + 64 ((e >> 6) div 5) + e % 64.  With the
frame row tag = the RANK-LOCAL output row (the op's row index; each slice owns one contiguous run of every op,
xs_place.op_groups), rbase = the slice's first row and rcnt = its share: every row of the slice decodes to a distinct
leaf word, rows of other slices fault (F9).  The frame images of xs_place tag phase rows 0..R-1 (phase-local): the cap
needs the rank-local tag, which `gen --tags rank` applies to a vector (cfg ROM tag fields rewritten; values and
calendar unchanged -- the bench proves it) and `cap` emits as a tag map + cfg_d words for every slice and phase.

    xs_calendar.py gen   --vec VEC --out DIR [--mutant shift|nostall|offm1|late] [--tags rank]   xs programme + images
    xs_calendar.py check --dir DIR --log RUN.LOG                                                    lockstep + RET check
    xs_calendar.py cap   --out FILE [--fixtures D] [--layer L0]                                      cap cfg_d + tag maps
    xs_calendar.py collect --out BENCH_OUT --res RESDIR DIR...                                      bench record
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lower_xs as LX  # noqa: E402  (sys.path: tools, tools/s81_dv, tools/s81, tools/s81_static_control)

ROOT = LX.ROOT
sys.path.insert(0, str(ROOT / 'tools/s81_slice'))

# ---- the calibration vehicle (tb_s81dv_frame.sv + ot_v41_spine_pq_static_w17w10 PQ 1, GSLACK 36, BST 2)
P0 = 63                       # bench go -> spine accept edge (edge_n numbering of the frame bench)
CFG_WORD = P0 + 4             # spine cfg broadcast (bt_cfg P0 + 1, BST 2, lane register) -> lane word after edge P0 + 4
CFG_TO_GO = 63                # can_go: cfg_cnt >= CW + 1 + GSLACK = 62 -> go 63 edges after cfg
GO_TO_BEAT = 2                # beat 0 leaves bt 2 edges after go (sw load, s_adv)
XDLY = 4                      # the bench's payload delay behind cc (tb_s81dv_frame.sv XDLY)
LQ, LB = 17, 4                # q: VM read + act-quant 13 -> block data of load j usable at edge P0 + LQ + j; BF16: P0 + 4 + j
# ---- the xs (ot_s81sl_xs + ot_s81sl_xs_ctl, latencies of tools/s81_slice/xs_program.py, bench-verified 10-17)
GO_LAT = 3                    # calendar timestamp t -> captured by the controller at TS + 3 + t (+ OFF + XS_LAG)
XS_LAG = 3                    # is_d pin -> delayed issuer output (pin, delay line, output register)
CTL_TO_CC = 5                 # controller capture c -> cfg / go in the frame word after edge c + 5
CTL_TO_BEAT = 11              # stream request captured at c -> the beat's frame word after edge c + 11
ADDR_LEAD = 2                 # stream ROM address row = request row + 2
ND = 8                        # xs issuer delay-line depth
# ---- programme layout (iterations = frame-bench edges)
T_OFFCFG, GW_IT, GA0, TS = 24, 150, 200, 300
ACC = 20                      # accept row; cfg row ACC + 20
OFF = 37


def isd(**f):
    lay = dict(go=(0, 1), ph=(1, 10), np=(11, 3), xbase=(14, 19), xps=(33, 19), obase=(52, 19), ops=(71, 19),
               fmt=(90, 2), f_fault=(92, 1), prime=(93, 1), start=(94, 1), base=(95, 12), length=(107, 13),
               gw=(120, 1), gw_fam=(121, 1), gw_par=(122, 1), off_we=(123, 1), off=(124, 8))
    w = 0
    for k, v in f.items():
        lo, wd = lay[k]
        assert 0 <= v < (1 << wd), (k, v)
        w |= v << lo
    return w


def phase_word(P, ph):
    w = P[2 * ph]
    return dict(ph=ph, bf=w & 1, K=(w >> 1) & 0x1FFF, nb=(w >> 14) & 0xFFFF, sbase=(w >> 30) & 0xFFFF,
                rows=(w >> 46) & 0xFFFF)


def need_elems(w, fam):
    """elements of the x vector the spine must hold before it sends stream word w (ot_v41_spine s_ok)"""
    if not w & 1:
        return 0
    if fam:
        umax = max([(w >> (8 + 8 * k)) & 255 for k in range(4) if (w >> (4 + k)) & 1] + [0])
        return umax * 128 + 128
    u, b, sv = (w >> 1) & 255, (w >> 9) & 7, (w >> 12) & 3
    return ((u << 4) | (8 if sv & 2 else 0) | b) * 32 + 32


def spine_offsets(words, fam, K, stall=True):
    """beat i leaves the spine's beat register off_i edges after go's (off_0 = GO_TO_BEAT, + stalls)"""
    go_bt = P0 + 1 + CFG_TO_GO
    L = LB if fam else LQ
    loads = -(-K // 64)
    out, prev = [], None
    for i, w in enumerate(words):
        b = go_bt + GO_TO_BEAT if prev is None else prev + 1
        n = need_elems(w, fam)
        if stall and n:
            assert n <= 64 * loads, ('beat needs x beyond K', i, n, K)
            b = max(b, P0 + L + -(-n // 64))
        out.append(b - go_bt)
        prev = b
    return out


def ring_order(nbeat, slc):
    """per source (0 own, 1 W, 2 E): beats in ring order (xs_program.ring_order 'near': owner = beat // 5)"""
    own = [g for g in range(nbeat) if g // 5 == slc]
    W, E = [], []
    for d in range(1, 9):
        W += [g for g in range(nbeat) if g // 5 == (slc - d) % 16]
    for d in range(1, 8):
        E += [g for g in range(nbeat) if g // 5 == (slc + d) % 16]
    return [own, W, E]


def compile_phase(P, S, ph, slc, mutant=None):
    """the xs programme of one field phase: calendar rows, is_d words, gather arrivals, predicted shift D"""
    from pq_calendar import action_word
    pw = phase_word(P, ph)
    fam, K, nb, sbase = pw['bf'], pw['K'], pw['nb'], pw['sbase']
    words = S[sbase:sbase + nb]
    offs = spine_offsets(words, fam, K, stall=mutant != 'nostall')
    rows = {}

    def ev(t, **f):
        r = rows.setdefault(t, {})
        for k, v in f.items():
            assert k not in r or r[k] == v, (t, k, r.get(k), v)
            r[k] = v
    a, tc = ACC, ACC + 20
    tg = tc + CFG_TO_GO + (1 if mutant == 'shift' else 0)
    ev(a, accept_tag=0)
    ev(tc, cfg=1, cfg_tag=0)
    ev(tg, launch=1, launch_tag=0)
    # payload delay XDLY behind cc and the xs beat latency (CTL_TO_BEAT - CTL_TO_CC = 6 = GO_TO_BEAT + XDLY)
    assert CTL_TO_BEAT - CTL_TO_CC == GO_TO_BEAT + XDLY
    ts = [tg + o - GO_TO_BEAT for o in offs]
    for i, t in enumerate(ts):
        ev(t, stream_req=1, stream_tag=0, stream_pos=0, stream_fam=fam, stream_lastpos=int(i == nb - 1),
           stream_lastop=int(i == nb - 1))
        ev(t + ADDR_LEAD, stream_addr=sbase + i)
    tr = max(ts) + ADDR_LEAD + 30
    ev(tr, retire_mask=1)
    ev(tr + 4, phase_end=1)
    tt = sorted(rows)
    assert len(tt) <= 4096
    packed = [(t << 75) | action_word(rows[t], action_bits=75) for t in tt]
    # is_d
    off_load = OFF - 1 if mutant == 'offm1' else OFF
    iss = {T_OFFCFG: isd(off_we=1, off=off_load), GW_IT: isd(gw=1, gw_fam=fam, gw_par=0),
           TS - 20: isd(prime=1, base=0, length=len(tt)), TS: isd(start=1, base=0, length=len(tt)),
           TS + GO_LAT + a: isd(go=1, ph=ph, np=0)}
    its = sorted(iss)
    for i in its:                                 # delay-line occupancy (words in flight OFF + 2 edges)
        assert len([j for j in its if j <= i < j + OFF + 2]) <= ND
    # gathers: every beat of the x vector (64 elements), 3 sources one beat / edge each, ring order of the slice
    nbeat = -(-K // 64)
    arr = []
    for src, li in enumerate(ring_order(nbeat, slc)):
        for n, g in enumerate(li):
            arr.append([GA0 + n + (0 if src == 0 else 1), src, fam, g])
    ctl = lambda t: TS + GO_LAT + t + OFF + XS_LAG          # noqa: E731  controller capture edge of row t
    head = {}                                     # beat -> first stream-head edge reading it
    for i, w in enumerate(words):
        for g in beats_of(w, fam):
            head.setdefault(g, ctl(ts[i]) + 6)
    if mutant == 'late':                          # the beat read first arrives one edge after its stream head
        g0 = min(head, key=lambda g: head[g])
        for x in arr:
            if x[3] == g0:
                x[0] = head[g0] + 1
    slack = min(head[g] - it for it, _, _, g in arr if g in head)
    D = ctl(tc) + CTL_TO_CC - CFG_WORD
    stalls = offs[-1] - (GO_TO_BEAT + nb - 1)
    return dict(rows=rows, packed=packed, iss=iss, arr=arr, D=D, ts=ts, tg=tg, tc=tc, nbeat_x=nbeat, slack=slack,
                stall_edges=stalls, off_load=off_load, fam=fam, K=K, nb=nb, sbase=sbase, cal_rows=len(tt),
                end_iter=ctl(max(tt)) + 40)


def beats_of(w, fam):
    if not w & 1:
        return []
    if fam:
        out = []
        for k in range(4):
            if (w >> (4 + k)) & 1:
                u = (w >> (8 + 8 * k)) & 255
                out += [2 * u, 2 * u + 1]
        return out
    u, b, sv = (w >> 1) & 255, (w >> 9) & 7, (w >> 12) & 3
    return [((16 * u + 8 * h + b) >> 1) for h in (0, 1) if sv >> h & 1]


# ------------------------------------------------------------------------------------------------ phase pipeline
# S81-RATEFIX (10-19): the field phases of one op as ONE calendar segment, phases overlapped the way an accelerator
# streams weights (double-buffered configuration: phase i+1 is accepted and configured while phase i streams).
# compile_phase gives every phase its own segment (prime / start / ... / retire + 30 / phase_end) and one tag, so
# consecutive phases serialise on the whole segment: the measured fullsix minimum is 224 edges a phase for a 64-word
# stream (TOKSIM-S81/FIELD sweep, 223 fails: GO on the live tag 0).  Here:
#   * phase i launches at tg0 + i * period; its stream rows keep compile_phase's offsets from its launch (so every
#     element / frame / return-plan edge of the phase moves by exactly i * period -- the plan stays valid);
#   * tags alternate between 0 and 2 (tag[0] = 0 keeps the x-buffer parity spar = tag[0] ^ pos[0] = 0: the retained x);
#     the q element's own op tag is the cfg7 sequencer's go count, independent of these;
#   * cfg row = launch - cfg_lead, accept row = cfg row - acc_gap, retire = last stream row + ADDR_LEAD + retire_gap;
#   * one phase_end, on the last row (the reader's END ends the segment).
# Element constraints the period / cfg_lead must satisfy (measured on the fullsix P224 trace, Q_LIFETIME of all 54
# q elements; element edge = calendar row + 1472 for both cfg and go):  walk = go + 1 .. go + 64/66;  the
# configuration load (26 words) must start after the bank it writes (phase i-1's) drained: walk end + DRAIN (127);
# swap needs the load finished and walking low; go >= swap + 22 (replay 17 + RT + QM5 stage).  Hence
#   period >= 88 (replay) and 2 * period >= 195 + cfg_lead, cfg_lead >= 48   ->   period >= 122 at DRAIN 127.
def compile_pipeline(P, S, phases, slc, period, cfg_lead=48, acc_gap=10, retire_gap=6, tags=(0, 2)):
    from pq_calendar import action_word
    rows = {}

    def ev(t, **f):
        r = rows.setdefault(t, {})
        for k, v in f.items():
            assert k not in r or r[k] == v, (t, k, r.get(k), v)
            r[k] = v
    per = []
    tg0 = None
    for n, ph in enumerate(phases):
        c = compile_phase(P, S, ph, slc)
        if tg0 is None:
            tg0 = c['tg']
        sh = tg0 + n * period - c['tg']                 # phase n's rows move by sh (its launch -> tg0 + n * period)
        tag = tags[n % len(tags)]
        assert tag & 1 == 0, 'x parity: tag[0] must be 0 for the retained x (spar = tag[0] ^ pos[0])'
        tg = c['tg'] + sh
        tc = tg - cfg_lead
        ta = tc - acc_gap
        assert ta >= 0, ('accept before the segment start', n, ta)
        ev(ta, accept_tag=tag)
        ev(tc, cfg=1, cfg_tag=tag)
        ev(tg, launch=1, launch_tag=tag)
        ts = [t + sh for t in c['ts']]
        for i, t in enumerate(ts):
            ev(t, stream_req=1, stream_tag=tag, stream_pos=0, stream_fam=c['fam'],
               stream_lastpos=int(i == c['nb'] - 1), stream_lastop=int(i == c['nb'] - 1))
            ev(t + ADDR_LEAD, stream_addr=c['sbase'] + i)
        tr = max(ts) + ADDR_LEAD + retire_gap
        ev(tr, retire_mask=1 << tag)
        per.append(dict(phase=ph, tag=tag, accept=ta, cfg=tc, launch=tg, stream=[ts[0], ts[-1]], retire=tr,
                        nb=c['nb'], stall_edges=c['stall_edges'], D=c['D'], shift=sh))
    for n in range(2, len(per)):                         # tag reuse: retire of n-2 strictly before accept of n
        assert per[n - 2]['retire'] < per[n]['accept'], ('tag reused while live', n, per[n - 2]['retire'], per[n]['accept'])
    for n in range(1, len(per)):                         # streams never overlap (one stream word an edge)
        assert per[n - 1]['stream'][1] + ADDR_LEAD < per[n]['stream'][0], ('stream overlap', n)
    tend = max(rows) + 4
    ev(tend, phase_end=1)
    tt = sorted(rows)
    assert len(tt) <= 4096 and tt[-1] < (1 << 24)
    packed = [(t << 75) | action_word(rows[t], action_bits=75) for t in tt]
    # is_d: offset load, ONE prime / start, one GO per phase captured with its accept row
    iss = {T_OFFCFG: isd(off_we=1, off=OFF), TS - 20: isd(prime=1, base=0, length=len(tt)),
           TS: isd(start=1, base=0, length=len(tt))}
    for p in per:
        assert TS + GO_LAT + p['accept'] not in iss
        iss[TS + GO_LAT + p['accept']] = isd(go=1, ph=p['phase'], np=0)
    its = sorted(iss)
    for i in its:
        assert len([j for j in its if j <= i < j + OFF + 2]) <= ND
    ctl = lambda t: TS + GO_LAT + t + OFF + XS_LAG          # noqa: E731
    return dict(rows=rows, packed=packed, iss=iss, phases=per, cal_rows=len(tt), period=period, cfg_lead=cfg_lead,
                acc_gap=acc_gap, retire_gap=retire_gap, tags=list(tags), end_iter=ctl(tend) + 40)


# ------------------------------------------------------------------------------------------------ tag remap
def remap_tags(vec, out, meta):
    """rewrite the phase's row tags in the frame cfg ROM images: phase-local r -> the rank-local row (meta row_index
    via the rows' out_index / src); returns {r: tag}"""
    from field_cfg7_image import encode_bank, decode_bank
    ph = meta['field_phase']
    tmap = {}
    for r, v in meta['rows'].items():
        tmap[int(r)] = int(v['src'][1])              # FMat src = (matrix, rank-local row)
    assert len(set(tmap.values())) == len(tmap) and max(tmap.values()) < (1 << 14)
    banks = {}
    for f in sorted(Path(out).glob('f_c*_[0-6].viamap.hex')):
        k, jb = re.match(r'f_c(\d+)_(\d)\.viamap', f.name).groups()
        banks.setdefault(int(k), {})[int(jb)] = f
    nfix = 0
    for k, bk in banks.items():
        dec = {jb: decode_bank([int(l, 16) for l in bk[jb].read_text().split()]) for jb in bk}
        for w_ in list(range(8)) + list(range(17, 25)):
            jb, row = w_ % 7, 4 * ph + w_ // 7
            v = dec[jb][row]
            if v == 0:
                continue
            t = v & 0xFFFF
            if t & 0x8000:                           # SENT (padding row of an odd super row)
                continue
            assert t in tmap, (k, w_, t)
            dec[jb][row] = (v & ~0xFFFF) | tmap[t]
            nfix += 1
        for jb in bk:
            assert all(x < (1 << 48) for x in dec[jb])
            bk[jb].write_text(''.join(f'{w:0144x}\n' for w in encode_bank(dec[jb])))
    return tmap, nfix


# ------------------------------------------------------------------------------------------------ gen / check
def viamap_of(words):
    from pq_calendar import viamap
    return viamap(words + [0] * (4096 - len(words)))


def cmd_gen(a):
    vec, out = Path(a.vec), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(vec, out)
    meta = json.loads((vec / 'meta.json').read_text())
    P = [int(v, 16) for v in (vec / 'spine_phase.hex').read_text().split()]
    S = [int(v, 16) for v in (vec / 'spine_stream.hex').read_text().split()]
    ph = meta['field_phase']
    c = compile_phase(P, S, ph, meta['slice_index'], a.mutant)
    (out / 'pq_calendar_action.viamap.hex').write_text(viamap_of([w & ((1 << 72) - 1) for w in c['packed']]))
    (out / 'pq_calendar_time.viamap.hex').write_text(viamap_of([w >> 72 for w in c['packed']]))
    (out / 'xs_is.hex').write_text(''.join(f'@{it:x}\n{(1 << 160) | w:041x}\n' for it, w in sorted(c['iss'].items())))
    g = {}
    for it, src, fam, beat in c['arr']:
        v = g.get(it, 0)
        assert not (v >> src) & 1, ('two beats on one source edge', it, src)
        g[it] = v | (1 << src) | (fam << (3 + src)) | (beat << (6 + 7 * src))
    (out / 'xs_g.hex').write_text(''.join(f'@{it:x}\n{v:07x}\n' for it, v in sorted(g.items())))
    tmap = None
    if a.tags == 'rank':
        tmap, nfix = remap_tags(vec, out, meta)
        meta['rows'] = {str(tmap[int(r)]): v for r, v in meta['rows'].items()}
        from static_return_calendar import _f, _mk, norm
        ret = []
        for e, t, d, er in meta['plan']['ret']:
            row19, lo, k, n = _f(norm(t))
            pos, hi, row = row19 >> 16, (row19 >> 14) & 3, row19 & 0x3FFF
            ret.append([e, _mk((pos << 16) | (hi << 14) | tmap[row], lo, k, n), d, er])
        meta['plan']['ret'] = ret
        assert [w[0] for w in ret] == [w[0] for w in json.loads((vec / 'meta.json').read_text())['plan']['ret']]
        meta['tag_remap'] = dict(map={str(k): v for k, v in tmap.items()}, cfg_words_rewritten=nfix)
    D = c['D']
    meta['spine_meta'] = 'meta_spine.json'
    meta['plan']['ret'] = [[w[0] + D] + list(w[1:]) for w in meta['plan']['ret']]
    T = max(w[0] for w in meta['plan']['ret']) + 600
    meta['cycles'] = T
    meta['xs'] = dict(D=D, off=OFF, off_load=c['off_load'], ts=TS, mutant=a.mutant, tags=a.tags, cal_rows=c['cal_rows'],
                      stall_edges=c['stall_edges'], gather_slack=c['slack'], nbeat_x=c['nbeat_x'], fam=c['fam'],
                      K=c['K'], nbeat_stream=c['nb'], sbase=c['sbase'], end_iter=c['end_iter'],
                      launch_row=c['tg'], cfg_row=c['tc'], stream_rows=[c['ts'][0], c['ts'][-1]],
                      is_d={str(k): f'{v:040x}' for k, v in sorted(c['iss'].items())},
                      calendar='pq_calendar_action/time.viamap.hex (75-b action ABI, tools/s81_static_control/pq_calendar)')
    shutil.copy(vec / 'meta.json', out / 'meta_spine.json')
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    # the TB cycles counted after the bench go (edge 63)
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={T - P0 - 1} +K={meta["K"]} +OPS={meta["nrows"]} '
                              f'+PH={ph} +D={D}\n')
    print(f'XS_CAL_GEN {out.name} phase {ph} K {c["K"]} fam {c["fam"]} rows {c["cal_rows"]} D {D} stalls '
          f'{c["stall_edges"]} slack {c["slack"]} mutant {a.mutant} tags {a.tags}')
    return 0


def cmd_check(a):
    d = Path(a.dir)
    meta = json.loads((d / 'meta.json').read_text())
    log = Path(a.log).read_text()
    errs, summ = LX.check_words(meta, log)
    m = re.search(r'^XSL_LOCKSTEP (.*)$', log, re.M)
    lk = dict(re.findall(r'(\w+)=(-?\d+)', m.group(1))) if m else {}
    if not m:
        errs.append('NO_LOCKSTEP')
    else:
        lk = {k: int(v) for k, v in lk.items()}
        if lk.get('mismatch', 1) or lk.get('valid_ref', 0) == 0 or lk.get('valid_ref') != lk.get('valid_xs'):
            errs.append(f'LOCKSTEP {m.group(1)}')
        if lk.get('xs_fault_at', -1) >= 0:
            errs.append(f'XS_FAULT at {lk["xs_fault_at"]}')
    errs += re.findall(r'^XSL_MISMATCH .*$', log, re.M)[:4]
    ok = not errs
    chk = dict(summary=summ, lockstep=lk, errors=errs[:200], xs=meta['xs'], op=meta['op'], field_phase=meta['field_phase'],
               pass_=ok)
    (d / 'check.json').write_text(json.dumps(chk, indent=1) + '\n')
    for e in errs[:8]:
        print(e)
    print(f'XS_CAL_CHECK {"PASS" if ok else "FAIL"} {d.name} {meta["op"]} phase {meta["field_phase"]} '
          f'mutant={meta["xs"]["mutant"]} tags={meta["xs"]["tags"]} D={meta["xs"]["D"]} words={summ["words"]} '
          f'lockstep={lk} errors={len(errs)}')
    return 0 if ok else 1


def cmd_collect(a):
    res = ROOT / a.res
    res.mkdir(parents=True, exist_ok=True)
    out = Path(a.out)
    for f in ('sources.sha256', 'verilator.version'):
        if (out / f).exists():
            shutil.copy(out / f, res / f)
    runs = []
    for vd in a.dir:
        vd = Path(vd)
        n = vd.name
        log = out / f'run_{n}.log'
        rc = cmd_check(argparse.Namespace(dir=str(vd), log=str(log)))
        chk = json.loads((vd / 'check.json').read_text())
        lines = log.read_text().splitlines()
        wit = res / f'run_{n}.log'
        wit.write_text('\n'.join([l for l in lines if l.startswith(('RET ', 'FAULT', 'XSL_', 'XO_MISMATCH'))][:240]
                                 + lines[-4:] + [f'CHECK {e}' for e in chk['errors'][:20]]
                                 + [f'XS_CAL_CHECK {"PASS" if rc == 0 else "FAIL"} {n}']) + '\n')
        meta = json.loads((vd / 'meta.json').read_text())
        (res / f'meta_{n}.json').write_text(json.dumps({k: v for k, v in meta.items() if k not in ('plan', 'rows')},
                                                       indent=1) + '\n')
        (res / f'check_{n}.json').write_text(json.dumps(chk, indent=1) + '\n')
        for f in ('pq_calendar_action.viamap.hex', 'pq_calendar_time.viamap.hex', 'xs_is.hex', 'xs_g.hex'):
            if not meta['xs']['mutant']:
                shutil.copy(vd / f, res / f'{n}_{f}')
        runs.append(dict(name=n, op=meta['op'], field_phase=meta['field_phase'], mutant=meta['xs']['mutant'],
                         rtl_mutant=a.rtl_mutant.get(n), tags=meta['xs']['tags'], D=meta['xs']['D'],
                         stall_edges=meta['xs']['stall_edges'], pass_=rc == 0, words=chk['summary']['words'],
                         lockstep=chk['lockstep'], first_errors=chk['errors'][:3], witness=str(wit.relative_to(ROOT))))
    for r in runs:
        r['pass'] = r.pop('pass_')
    base = [r for r in runs if not r['mutant'] and not r['rtl_mutant']]
    muts = [r for r in runs if r['mutant'] or r['rtl_mutant']]
    rec = dict(schema='opentallas.s81_dv.bench_xs_slice.v1', bench='tools/s81_dv/layer_prog/xs/xs_slice_bench.sh',
               tb='rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame_xs.sv', compiler='tools/s81_dv/layer_prog/xs_calendar.py',
               host=a.host, runs=runs, base_pass=bool(base) and all(r['pass'] for r in base),
               mutants_fail=bool(muts) and all(not r['pass'] for r in muts))
    rec['pass'] = rec['base_pass'] and rec['mutants_fail']
    (res / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'XS_CAL_COLLECT pass={rec["pass"]} base={[(r["name"], r["pass"]) for r in base]} '
          f'mutants={[(r["name"], r["pass"]) for r in muts]}')
    return 0 if rec['pass'] else 1


# ------------------------------------------------------------------------------------------------ capture root cfg_d
def cap_word(c):
    return (c['obase'] | c['ops'] << 12 | c['np'] << 24 | c['fmt'] << 27 | c['rbase'] << 29 | c['rcnt'] << 45 |
            c['rsplit'] << 56 | c['lo32'] << 72 | c['hi32'] << 73)


def cmd_cap(a):
    """per slice and die-wide phase: cfg_d (rbase = the slice's first row of the op, rcnt = its share, fmt from the op's
    output format) + the frame tag map (phase-local r -> rank-local row); validated through cap_model.decode: every
    row of the slice decodes in range to a distinct (leaf, word), no other slice's row decodes in range"""
    import xs_place as XP
    from cap_model import decode
    fx = XP.Fix(a.fixtures)
    ops = XP.XS_OPS[a.layer]
    seq = XP.phase_list(fx, ops)
    groups = {op: XP.op_groups(fx, op) for op in ops}
    obase = {}
    nxt = 0
    rec = dict(schema='opentallas.s81_dv.xs_cap_cfg.v1', layer=a.layer, fixtures=str(a.fixtures),
               rule='frame row tag = rank-local row; cap rbase = slice first row, rcnt = slice share', phases=[])
    bad = 0
    for k, (op, gi, ch, nseg, R) in enumerate(seq, start=1):       # field phase 0 = a_proj (lower_xs)
        grp = groups[op][gi]
        key = (op, grp['mat'])
        per_slice = [sorted(i for fr in grp['groups'][g] for i in fr) for g in range(XP.NSLICE)]
        span = max(len(s) for s in per_slice)
        if key not in obase:                      # slice vp store: one 64-row-aligned region per matrix (allocation)
            if getattr(a, 'final_ffn_placement', False) and op == 'ffn.down':
                # cap addresses WORDS, while final_ffn allocates four-word ROWS.
                from layer_prog.final_ffn import CAPTURE, expert_slot
                slot = expert_slot(grp['expert'], fx.meta['experts'])
                if span != 80 or grp['out'] != 'bf16':
                    raise ValueError('final FFN requires actual output-sharded80-row BF16 down capture')
                obase[key] = 4 * (CAPTURE + 16 * slot)
                nxt += 64 * -(-span // 320)  # preserve every other matrix's canonical allocation
            else:
                obase[key] = nxt
                nxt += 64 * -(-span // 320)
        slices = []
        for g in range(XP.NSLICE):
            rows = [grp['rows'][i] for i in per_slice[g]]
            if not rows:
                continue
            assert rows == list(range(rows[0], rows[0] + len(rows))), ('slice share not contiguous', op, g)
            fmt = 1 if grp['out'] == 'fp32' else 2
            cfg = dict(obase=obase[key] & 0xFFF, ops=0, np=0, fmt=fmt, rbase=rows[0], rcnt=len(rows), rsplit=0, lo32=0,
                       hi32=0)
            tags = {}
            for f in range(XP.NFRAME):
                sel = grp['groups'][g][f][ch * R:(ch + 1) * R]
                tags[f] = [grp['rows'][i] for i in sel]
            seen = set()
            for f, ts in tags.items():
                for t in ts:
                    b, leaf, port, addr, _ = decode(t << 13, 0, cfg)
                    if b or (leaf, addr) in seen:
                        bad += 1
                    seen.add((leaf, addr))
            for g2 in range(XP.NSLICE):           # rows of other slices must fault (F9), never alias
                if g2 != g and per_slice[g2]:
                    t = grp['rows'][per_slice[g2][0]]
                    if not decode(t << 13, 0, cfg)[0]:
                        bad += 1
            slices.append(dict(slice_index=g, cfg=cfg, cfg_d=f'{cap_word(cfg):040x}', frame_tags=tags))
        rec['phases'].append(dict(phase=k, op=op, mat=grp['mat'], chunk=ch, rows_per_phase=R, slices=slices))
    rec['faults'] = bad
    rec['vp_rows_used'] = nxt
    if getattr(a, 'final_ffn_placement', False):
        rec['final_ffn_placement'] = dict(capture_rows=[128,240],assembled_rows=[320,432],combined_rows=[448,464],
                                         admitted=False,requires='dead VPX lease + real RD/allgather reservations')
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(f'XS_CAP {a.layer} phases {len(seq)} slices/phase <= {XP.NSLICE} faults {bad} vp rows {nxt}')
    return 0 if bad == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--vec', required=True)
    g.add_argument('--out', required=True)
    g.add_argument('--mutant', choices=('shift', 'nostall', 'offm1', 'late'), default=None)
    g.add_argument('--tags', choices=('phase', 'rank'), default='phase')
    c = sp.add_parser('check')
    c.add_argument('--dir', required=True)
    c.add_argument('--log', required=True)
    k = sp.add_parser('collect')
    k.add_argument('--out', required=True)
    k.add_argument('--res', required=True)
    k.add_argument('--host', default=None)
    k.add_argument('--rtl-mutant', type=json.loads, default={}, help='JSON {vec name: rtl mutant define}')
    k.add_argument('dir', nargs='+')
    p = sp.add_parser('cap')
    p.add_argument('--out', required=True)
    p.add_argument('--fixtures', default=str(LX.FIX))
    p.add_argument('--layer', default='L0')
    p.add_argument('--final-ffn-placement', action='store_true', help='opt-in actual VS13 capture rows; requires VPX lifetime proof')
    a = ap.parse_args(argv)
    return {'gen': cmd_gen, 'check': cmd_check, 'collect': cmd_collect, 'cap': cmd_cap}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
