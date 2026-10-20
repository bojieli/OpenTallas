#!/usr/bin/env python3
"""MU-KV-CTX bench (2026-10-19, coordinator 0kg): the fillers' initial context from the KV die host plane over the EXISTING
KV->compute d2d record stream into the compute ctlm boot-context loader (qfd_tt_ctlm_dv OPSEG, main 811e75a88).

    mu_kvctx_bench.py --work DIR [--kmut M] [--rmut M] [--verilator PATH] [--jobs N]

Harness tb_mu_kvctx.sv (see its header).  The ctlm half is the MU-QW-B1 op-segment bench (rtl/test/mu_qwen_seq/
mu_opseg_bench.py, imported unchanged): case `red` (mu_opcal F = 16, 2 layers, 3 frames + 2,000 edges), its checks C1..C7
(C2 = the latency user cycle-identical to the NU 1 reference, C5 = every filler EMB / SEG uses the filler's bank, which
starts from its initial context PRE[u]) -- except that the compute image's DW5 / DW6 carry NO context record here: the
records come from the KV die only.  KV-side schedule (cycles before the first L0 start S0 = 1100):
  user 0 request at 51 (U0), fillers 1 / 2 / 3 admitted at 61 / 71 / 81 (PRE[u]); filler 1 continues at 301 (pos + 1, not
  an admission); filler 3 continues at 351 BEFORE its initial context is sent (the initial context must survive); user 0's
  next step at 501; slot pairs at 200 / 400 / 600 / 800 (rotation 1, 2, 3, then none: the user-0 copy).
Checks (PASS needs all, plus mu_opseg_bench C1..C7):
  K1 KV identity: on every edge the reference port (MU 0 original, user-0 traffic, single-slot calendar) sends a word, the
     MU port sends the SAME word (valid, observed, 548 bits) -- 4 edges;
  K2 the MU port sends 8 words (4 pairs), all observed;
  K3 the face's own kind-12 receiver: no fault, and after the 2nd slot of every pair its TAG is user 0's current TAG;
  K4 the leaf loads exactly users 1, 2, 3 in that order with PRE[u] (token, {5'd0, position}), before the first filler
     EMB / SEG; no other load;
  K5 no sticky fault on the KV MU port, the reference port, the face receiver or the leaf.
Mutants (each must FAIL): --kmut 1 wrong user field, --kmut 2 wrong slot (pair order swapped), --kmut 3 producer off;
--rmut 1 leaf loads into the wrong user.
CAL mode (MU-DQ-SYSFACE 2026-10-19; DEFAULT, --model-link = the original bench-edge pair): the pair slots come from the
two dies' REAL D2D sequencers (qfd_d2d_cal_seq = the qfd_sys_face MU kit's, qkd_d2d_cal_seq) built from
ot_qwen_d2d_cal_seq_dies_mu.sv / d2d_cal_image_mu.svh, played by the real ot_qwen_d2d_cal (C RX, KV TX); each pair = one
token-run start of both calendars 3 edges before the old pair edge (K TX context beats at token-run cycles 2 / 3), halted
40 edges later.  The link = LINK_CAL = 16 edges (production image: K TX slot 2 -> C pin arrival 18).  Extra check:
  K6 no sequencer / calendar fault; the KV TX and C RX calendars each play 2 context events per pair.
--cmut 1 (CAL only): the face sequencer carries the MU 0 C RX image (a qfd_sys_face kit without the MU image): must FAIL.
QW-KVCTX 10-19: the ctlm runs CTX_SRC 1 FCTX 1 (die_params) with the leaf on its ctx_x port (was a force on c_ctx,
FCTX 0, no LCV / CTXU log): the shared checks C8 (MU-DQ-D2DUSER user carrier) and C10 (MU-DQ-BOOTCTX filler native
contexts, 108 in `red`) now see the harness; tb_mu_kvctx.sv header.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'rtl/test/mu_qwen_seq'))
import mu_opseg_bench as B                                # noqa: E402
O = B.O

TB = HERE / 'tb_mu_kvctx.sv'
LIST = HERE / 'lists/tb_mu_kvctx.f'
LINK_CAL = 16                  # CAL: K TX context slot (token-run cycle 2) -> C RX pin arrival (18) in the production image
D2D = ROOT / 'rtl/qwen_sys/d2d_static_20261015'
NU, LINK = B.NU, 14            # send -> compute RX slot = 2 record-port edges + LINK = 16 = the production image (K cyc 2 -> C arrive 18)
PRE, U0 = B.PRE, B.U0


def ep(u, seq): return (seq << 2) | u
def tag(e, tok, pos): return (e << 43) | (tok << 19) | (pos << 6)


U0B = ((U0[0] + 7) & 0x3FFFF, U0[1] + 1)          # user 0's next step
SCHED = [  # (cycle of the request; the epoch pulse is one edge before), user, seq, token, position
    (51, 0, 1) + U0, (61, 1, 1) + PRE[1], (71, 2, 1) + PRE[2], (81, 3, 1) + PRE[3],
    (301, 1, 2, (PRE[1][0] + 5) & 0x3FFFF, PRE[1][1] + 1), (351, 3, 2, (PRE[3][0] + 9) & 0x3FFFF, PRE[3][1] + 1),
    (501, 0, 2) + U0B]
PAIRS = [200, 400, 600, 800]


CAL = True


def img_const(path, name):
    import re
    return re.search(name + r" = (\d+'h[0-9a-f]+)", path.read_text()).group(1)


def kv_events():
    ev = []
    for c, u, s, tok, pos in SCHED:
        e = ep(u, s)
        ev.append((c - 1, 4, e))
        ev.append((c, 5, (s & 3) << 59 | tag(e, tok, pos)))
    if CAL:
        ev += [(c - 3, 7, 0) for c in PAIRS] + [(c - 3 + 40, 8, 0) for c in PAIRS]
    else:
        ev += [(c, 6, 0) for c in PAIRS]
    return ev


_orig_events_for = B.events_for


def events_for(pb, face, res, users, ctx=True):
    if users == {0}:
        return _orig_events_for(pb, face, res, users, ctx=False)
    # NO image filler context: the KV die sends it.  The OPSEG image still carries its DW5 / DW6 context record (the ctlm
    # checks it on the seal edge, ~1035, AFTER the KV loads at 218 / 418 / 618; a plain-0 record is a bad tag -> op_fault):
    # the record with tag CTX_TAG and an EMPTY mask = a valid record that loads no filler (QW-KVCTX 10-19; the old harness
    # forced c_ctx / c_ctxld and so never saw the seal check).
    dw5, dw6 = O.ctx_words({}, set())
    rec = {O.CTX_DW[0]: dw5, O.CTX_DW[1]: dw6}
    ev = [(c, k, (v >> 64 << 64) | rec[v >> 64]) if k == 1 and (v >> 64) in rec else (c, k, v)
          for c, k, v in _orig_events_for(pb, face, res, users, ctx=False)]
    return ev + kv_events()


B.events_for = events_for


def build(work, vl, kmut, rmut, jobs, cmut=0):
    d = work / (f'b_kvctx_k{kmut}_r{rmut}' + (f'_cal_c{cmut}' if CAL else ''))
    exe = d / 'Vtb_mu_kvctx'
    if exe.exists(): return exe
    srcs = [str(ROOT / l.strip()) for l in LIST.read_text().split('\n') if l.strip() and not l.startswith('#')]
    cmd = [vl, '--binary', '--timing', '-O2', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-TIMESCALEMOD',
           '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_mu_kvctx',
           f'-GNU={NU}', '-GMUT=0', '-GOPSEG=1', f'-GKMUT={kmut}', f'-GRMUT={rmut}', f'-GLINK={LINK_CAL if CAL else LINK}',
           f'-GCAL={int(CAL)}', f'-GCMUT={cmut}', f'-I{D2D}',
           '-GCRX_SEG1=' + img_const(D2D / 'd2d_cal_image_mu.svh', 'D2D_CAL_C_RX_SEG1'),
           '-GKTX_SEG1=' + img_const(D2D / 'd2d_cal_image_mu.svh', 'D2D_CAL_K_TX_SEG1'),
           '-GCRX_MU0=' + img_const(D2D / 'd2d_cal_image.svh', 'D2D_CAL_C_RX_IMG'), '-Mdir', str(d)] + srcs
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode != 0 or not exe.exists():
        sys.exit(f'BUILD FAILED kvctx k{kmut} r{rmut}: see {d}/build.log\n' + (r.stdout + r.stderr)[-3000:])
    return exe


def kv_checks(log, mu, fails, summ):
    ktx, kid, frx, ld, kend, kidn, kcal = [], [], [], [], None, None, None
    for ln in log.read_text().split('\n'):
        p = ln.split()
        if len(p) < 2: continue
        c, k = int(p[0]), p[1]
        if k == 'KTX': ktx.append((c, int(p[2]), int(p[3], 16)))
        elif k == 'KID': kid.append(ln)
        elif k == 'KIDN': kidn = int(p[2])
        elif k == 'FRX': frx.append((c, int(p[2], 16), int(p[3]), int(p[4])))
        elif k == 'CTXLD': ld.append((c, int(p[2]), int(p[3], 16), int(p[4], 16)))
        elif k == 'KEND': kend = tuple(int(x) for x in p[2:6])
        elif k == 'KCALEND': kcal = tuple(int(x) for x in p[2:8])
    # K1
    if kid or kidn != len(PAIRS):
        fails.append(f'K1 KV identity: {len(kid)} reference words differ (of {kidn}, want {len(PAIRS)}): {kid[:2]}')
    # K2
    if len(ktx) != 2 * len(PAIRS) or any(o != 1 for c, o, t in ktx):
        fails.append(f'K2 MU port words {len(ktx)} (want {2 * len(PAIRS)}), unobserved {[x for x in ktx if x[1] != 1][:2]}')
    # K3 face: the 2nd received slot of every pair ends on user 0's current TAG
    u0tags = [(c, tag(ep(0, s), tok, pos)) for c, u, s, tok, pos in SCHED if u == 0]
    bad3 = []
    if len(frx) != 2 * len(PAIRS): bad3.append(f'{len(frx)} face receives (want {2 * len(PAIRS)})')
    for i in range(1, len(frx), 2):
        c, t, v, f = frx[i]
        want = [x for cc, x in u0tags if cc < c][-1]
        if t != want or not v: bad3.append(f'pair end {c}: face TAG {t:x} (want user 0 {want:x}) valid {v}')
    if any(f for c, t, v, f in frx): bad3.append('face receiver fault')
    if bad3: fails.append('K3 face ' + '; '.join(bad3[:3]))
    # K4 leaf loads
    want4 = [(u, PRE[u][0], PRE[u][1]) for u in (1, 2, 3)]
    got4 = [(u, tk, ps) for c, u, tk, ps in ld]
    fill = [x[0] for x in mu['emb'] + mu['seg'] if x[1] != 0]
    late = [c for c, u, tk, ps in ld if fill and c >= min(fill)]
    if got4 != want4 or late:
        fails.append(f'K4 leaf loads {got4} (want {want4}); after the first filler EMB/SEG: {late[:2]}')
    # K5
    if kend != (0, 0, 0, 0):
        fails.append(f'K5 sticky faults kv_mu / kv_ref / face / leaf = {kend}')
    # K6 (CAL): real sequencers / calendars
    if CAL and kcal != (0, 0, 0, 0, 2 * len(PAIRS), 2 * len(PAIRS)):
        fails.append(f'K6 calendars: faults cseq / kseq / crx / ktx + context events ktx / crx = {kcal} '
                     f'(want 0 0 0 0 {2 * len(PAIRS)} {2 * len(PAIRS)})')
    summ['kv'] = dict(kcal=kcal, cal=CAL, ktx=len(ktx), kid_compared=kidn, kid_bad=len(kid), face_rx=[(c, f'{t:x}') for c, t, v, f in frx],
                      loads=ld, kend=kend, link=LINK_CAL if CAL else LINK, pairs=PAIRS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True); ap.add_argument('--kmut', type=int, default=0)
    ap.add_argument('--rmut', type=int, default=0)
    ap.add_argument('--cmut', type=int, default=0)
    ap.add_argument('--model-link', action='store_true', help='the original bench-edge pair (no sequencers / calendars)')
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', 'verilator')); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    global CAL
    CAL = not a.model_link
    if a.cmut and not CAL: sys.exit('--cmut needs CAL mode')
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    e1 = B.build(work, a.verilator, 1, 0, 0, a.jobs)
    e4 = build(work, a.verilator, a.kmut, a.rmut, a.jobs, a.cmut)
    fails, summ = [], dict(kmut=a.kmut, rmut=a.rmut, cmut=a.cmut, cal=CAL)
    cal = O.compile_frame(16, layers=2)
    rd = work / 'rom_red'; rd.mkdir(exist_ok=True)
    (rd / f'{B.INST}.viamap.hex').write_text(O.viamap_hex(O.rom_words(cal)))
    name = f'kvctx_k{a.kmut}_r{a.rmut}' + (f'_cal_c{a.cmut}' if CAL else '')
    B.check_case(name, cal, B.RED_FRAMES + 1, B.S0 + B.RED_FRAMES * cal['H'] + 2000, e1, e4, work, rd, 0, fails, summ)
    # re-read the MU run's log (check_case ran it as <name>_mu)
    log = work / f'{name}_mu.log'
    mu_parsed = dict(emb=[], seg=[])
    for ln in log.read_text().split('\n'):
        p = ln.split()
        if len(p) > 2 and p[1] == 'EMB': mu_parsed['emb'].append((int(p[0]), int(p[2])))
        if len(p) > 2 and p[1] == 'SEG': mu_parsed['seg'].append((int(p[0]), int(p[2])))
    kv_checks(log, mu_parsed, fails, summ)
    summ['verdict'] = 'PASS' if not fails else 'FAIL'
    summ['fails'] = fails
    (work / f'summary_{name}.json').write_text(json.dumps(summ, indent=1, default=str))
    print(f"MU_KVCTX_{summ['verdict']} kmut {a.kmut} rmut {a.rmut}" + (f' cal cmut {a.cmut}' if CAL else '') + ('' if not fails else ': ' + ' | '.join(fails)))
    print(json.dumps({k: v for k, v in summ.items() if k != 'fails'}, default=str)[:4000])
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
