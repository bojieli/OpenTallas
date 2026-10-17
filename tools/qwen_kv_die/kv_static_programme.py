#!/usr/bin/env python3
"""KVJ-E item 9 (Q-KVJOIN 10-17): the Qwen3-8B KV-die static programme compiler.

    kv_static_programme.py --out DIR [--ages results/arch/qwen_kv_static_programme_1017/die_ages.json]
                           [--profile die|component] [--epoch 0x0b0b] [--program HOST_IMAGE.hex]

One compile emits every boot-loaded image of the static KV subsystem and the boot-dispatch bundle that
qkd_static_kv_boot_dispatch consumes (targets 1..9 in order, then the ISA target 0, encoded by
tools/qwen_static_kv/program_target_frames.encode_boot_bundle into HOST class-8 frames):

  target 1  layer programme      327 words  36 x 9 roots + digest + epoch + footer (layer_programme.assemble_rows)
  target 2  writer programme     181 words  36 x {t0..t3, stop} + footer QKVPRG36 (qkd_kv_native_programme)
  target 3  ownership            4 words    enter / leave / deadline / seal QKVM (qkd_static_kv_ownership_calendar)
  target 4  landing calendars    192 words  32 groups x 6 (qkd_kv_landing_cal: id, XU, H0, {LD,RC}, K pace, V pace)
  target 5  front calendars      192 words  32 groups x 6 (qkd_kv_front_cal: id, -, H0, -, K pace, V pace)
  targets 6..9 controller cal.   4 x 1024   per stack 32 PCs x 32 words (qkd_controller_hbm_calendar, 16 x 128 b)
  target 0  ISA                  1024 + 8   the installed HOST programme (its digest is the layer image's LP_DIGEST)

plus the attention programme words of qkd_native_attention_programme (compiled_rx_cmd / compiled_tx_first /
compiled_end, fixed by the link; compiled_calendar per context T, the law the N1 generator implements) and the
opentallas.qwen_kv_static.programme.v1 operation list on actual template ports (kv_static.compile_graph input).

Sources composed (no timing is invented here; each constant names its source):
  link        tools/qwen_split/d2d_link_calendar.py --profile program (the same flags as chain/kvsys_prep.sh)
  roots       tools/qwen_static_kv/layer_roots_from_link.py laws (+ the die ages of kv_static_ages.py)
  K / V       tools/qwen_static_schedule/kv_calendar.py (k_streams, pc_schedule, pv16_v_streams, pc_schedule_paced,
              screen_36_capacity, compile_pv16_v) at T = 8192 (the reservation every context fits in)
  attention   tools/qwen_attention_native/attn_calendar.py (w16, G3S2) and compile_native_endpoint.py
  crossing    tools/qwen_static_kv/phase_launch.py (core -> HBM fixed-phase launch law)
  controller  tools/qwen_static_kv/controller_calendar_image.py (Run / compile_image; command words of the
              JEDEC-checked native controller bench run_controller_calendar_native.py)

--profile component reproduces the bench-fed component images (zero die ages, kit QK 34 / RL 21, kit V RL 19, no
crossing): the golden checks in test_kv_static_programme.py compare it to the committed layer image, the native
endpoint compiler and the kv_calendar pacing.  --profile die is the production compile on the die ages.
Status is always COMPILED_NOT_QUALIFIED: the static floorplan, its native benches and TT/FF closure are separate.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for p in (ROOT, ROOT / 'tools', HERE, ROOT / 'tools/qwen_static_kv', ROOT / 'tools/qwen_attention_native'):
    sys.path.insert(0, str(p))

import attn_calendar as AC                                  # noqa: E402
import compile_native_endpoint as CNE                      # noqa: E402
import controller_calendar_image as CCI                    # noqa: E402
import layer_roots_from_link as LR                         # noqa: E402
import program_target_frames as PTF                        # noqa: E402
from layer_programme import assemble_rows                  # noqa: E402
from tools.qwen_static_schedule import kv_calendar as KC   # noqa: E402
from tools.qwen_kv_die import static_kv_calendar as SKC    # noqa: E402

STACKS = ('WS', 'WN', 'ES', 'EN')
ORDER = SKC.GROUP_ORDER                                     # landing group order inside a stack strip
AGES = 'results/arch/qwen_kv_static_programme_1017/die_ages.json'
LINK_ARGS = ['--txl', '6', '--phy', '5', '--profile', 'program', '--txd-c', '1,1,1,2', '--txd-k', '1,2,1,1',
             '--host-stages', '0', '--link-handoff', 'results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json',
             '--pinreg']                                    # tools/qwen_kv_die/chain/kvsys_prep.sh OT_KV_SEQ_STATIC
T_MAX = 8192
CORE_U, HBM_U = 625, 768
XU_STRICT = CORE_U + 1          # phase launch: toggle 1 core edge after capture; first HBM edge strictly after it
LAUNCH_HBM_EDGES = 3            # phase launch: output register first_hbm + 2; front / controller go_q one edge later
CAL_PIN_EDGES = 2               # qkd_controller_hbm_calendar: event pin edge = captured go + start + 2
PUT_AFTER_GO = KC.SOURCED['put_after_go_hbm']
# controller command template (run_controller_calendar_native.py, checked against the JEDEC core): per pass a
# layer-row descriptor and a second command ahead of the RD reservation, at the bench's own leads.
K_CMDS = [(-110, dict(command=(256 << 20) | 1, layer_row=True)), (-40, dict(command=(1 << 31) | 1))]
V_CMDS = [(-400, dict(command=(512 << 33) | (768 << 20) | 1, layer_row=True)), (-300, dict(command=(1 << 31) | 1))]
# (the V pass keeps the bench's own leads: the K leads -110 / -40 fail the JEDEC core bench at the first V RD;
#  compile_image refuses any lead that lands on a K RD reservation edge)
RD_SHAPE_K, RD_SHAPE_V = (8, 2), (8, 3)   # RD reservation bursts the JEDEC core bench sustains (1 RD an edge fails it)
CMD_LEAD = 118                  # first K RD reservation at 120: the K layer-row descriptor at 10 and the second command at 80, as the JEDEC bench
WRITER_STOP_AFTER = 5           # tb_qkd_kv_native_programme: stop 5 edges after the last word (RTL minimum 3)
FOOTER_WRITER = 0x514b565052473336
OWN_SEAL = 0x514b564d


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _sfi():
    s = importlib.util.spec_from_file_location('sys_face_image', ROOT / 'tools/qwen_split/sys_face_image.py')
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def link_calendar(workdir):
    out = Path(workdir) / 'cal'
    p = subprocess.run([sys.executable, str(ROOT / 'tools/qwen_split/d2d_link_calendar.py'), '--out', str(out)] + LINK_ARGS,
                       cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        raise SystemExit('link calendar compile failed: ' + p.stderr[-2000:])
    return json.loads((out / 'calendar.json').read_text())


# ---- profile: every age the compile uses -----------------------------------------------------------------------------
def profile(kind, ages=None):
    if kind == 'component':
        return dict(kind='component', start_relays=0, att=0, rx=0, writer=0, kvn=0, groups=0, crossing=False,
                    qk_age=KC.SOURCED['qk_consume_age'], qk_row_latency=KC.SOURCED['qk_row_latency'],
                    v_rl=19, d_rl=0, d_qk=0, phase=None, ld=1, rc=3, landing_uncertainty=0)
    L = ages['link']
    return dict(kind='die', start_relays=L['programme_start']['edges'], att=L['programme_to_attention']['edges'],
                rx=L['d2d_to_attention_rx']['edges'], writer=L['programme_to_writer']['edges'], kvn=L['d2d_to_writer']['edges'],
                groups=L['programme_to_groups']['edges'], crossing=True,
                qk_age=ages['qk']['QK_ISSUE_AGE'], qk_row_latency=ages['qk']['row_latency_for_calendar'],
                v_rl=ages['pv']['RL'], d_rl=ages['pv']['RL'] - 19, d_qk=ages['qk']['QK_ISSUE_AGE'] - AC.QK_CONSUME,
                phase=ages['phase_launch'], ld=L['return_to_landing_ld']['LD'], rc=3, landing_uncertainty=1,
                rd_shape=dict(K=RD_SHAPE_K, V=RD_SHAPE_V))


def kv_params(pr):
    return dict(KC.SOURCED, ring_cdc_core_edges=pr['rc'], layer_period_core=6798, write_ready_core=0, front_nblk=10,
                ring_depth=64, refresh=KC.refresh_from_table(), qk_consume_age=pr['qk_age'], qk_row_latency=pr['qk_row_latency'])


# ---- attention calendar (the N1 law) ----------------------------------------------------------------------------------
def attention_calendar(T, pr, service_end=None):
    """attn_calendar.calendar_w16(T, head_g3s2=True) with the die's QK age shift (LMAX moves with the last consume)
    and V word latency shift (pair outputs move with RL); service_end stretches R so the last result beat lands on
    the link's fixed RESULT slot (static: a context-dependent service end would miss the compiled TX slot)."""
    lmax = AC.lmax_min(T) + pr['d_qk']
    c = AC.calendar(T, lmax=lmax, pv='w1')
    for f in ('LMAX', 'EXP', 'Z', 'HUB_LMAX', 'HUB_Z', 'HUB_RECIP', 'HUB_PUB'):
        c[f] += AC.HEAD_G3S2_SHIFT
    po = [AC.w16_pair_out(T, 0) + pr['d_rl'], AC.w16_pair_out(T, 1) + pr['d_rl']]
    pv = max(c['EXP'] + AC.pv_after_exp_w16(T), c['HUB_PUB'] + AC.RZ_MARGIN - max(po))
    r = max(max(po), c['HUB_PUB'] + AC.RZ_MARGIN - pv)
    if service_end is not None:
        r_link = service_end - 49 - pv                      # service_cycles = PV_START + max(P, R) + 16 + 33
        if r_link < r:
            raise ValueError(f'T={T}: attention service needs {pv + r + 49} edges, the link slot gives {service_end}')
        r = r_link
    c.update(P0=po[0], P1=po[1], PV_START=pv, R=r)
    AC.check(c)
    return c


# ---- crossing: core-edge offset of an HBM event after a go capture -----------------------------------------------------
def crossing_core(hbm_edges_after_A, pr):
    """worst core edges from the go_q capture edge c of the per-group tile to an HBM event at A + n (A = front /
    controller capture of the launched go): toggle at c+1, first HBM edge <= toggle + SAFE_HIGH u, A = +3 edges"""
    if not pr['crossing']:
        return 0
    hi = pr['phase']['SAFE_HIGH_U']
    return math.ceil((CORE_U + hi + (LAUNCH_HBM_EDGES + hbm_edges_after_A) * HBM_U) / CORE_U)


# ---- per-PC HBM schedules (K and V, worst context) ---------------------------------------------------------------------
def shaped_schedule(demand, p, shape, start_core=None):
    """kv_calendar.pc_schedule / pc_schedule_paced (front credit, worst landing, put stride, ring pacing when start_core
    is given) with the RD reservation shape the native controller + JEDEC core bench sustains: after every burst of
    shape[0] RDs, shape[1] idle edges (run_controller_calendar_native: K 8 / 2, V 8 / 3).  shape None = 1 RD an edge."""
    if shape is None:
        return KC.pc_schedule_paced(demand, p, start_core) if start_core is not None else KC.pc_schedule(demand, p, 0)
    burst, gap = shape
    nb, bl, st, dep = p['front_nblk'], p['front_blk'], p['front_stride'], p['ring_depth']
    n = len(demand)
    cons = [start_core + c for _, c, _ in demand] if start_core is not None else None
    blocks = math.ceil(n / bl)
    issue, go, put, freed = [0] * n, [0] * blocks, [0] * n, [0] * blocks
    t, k = 0, 0
    lmax = p['rd_landing_nominal_hbm'] + p['front_window_hbm']
    for b in range(blocks):
        if b >= nb and freed[b - nb] > t:
            t, k = freed[b - nb], 0                          # credit wait restarts the burst
        idx = range(b * bl, min(n, (b + 1) * bl))
        for i in idx:
            issue[i] = t
            t += 1
            k += 1
            if k == burst:
                t, k = t + gap, 0
        g = issue[idx[-1]] + lmax
        if b:
            g = max(g, put[b * bl - 1] + st - p['put_after_go_hbm'])
        if cons is not None:
            for j, i in enumerate(idx):
                if i - dep >= 0:
                    g = max(g, KC._core_to_hbm(cons[i - dep] + 1, p) - p['put_after_go_hbm'] - j * st)
        go[b] = g
        for j, i in enumerate(idx):
            put[i] = g + p['put_after_go_hbm'] + j * st
        freed[b] = put[idx[-1]] + 1
    return dict(issue=issue, go=go, put=put, freed=freed, rd_end=t)


def _visible(sch, p):
    return [KC.hbm_to_core(x, p) + p['ring_cdc_core_edges'] for x in sch['put']]


def v_start(demand, p, shape):
    """minimal pair start after the V RD base with every put visible before its consume (kv_calendar._layer_pc_paced
    with the RD shape)"""
    if shape is None:
        return KC._layer_pc_paced(demand, p)[0]
    start = KC._layer_pc(demand, p)[0]
    while True:
        v_ = shaped_schedule(demand, p, shape, start)
        if all(x <= start + c for x, (_, c, _) in zip(_visible(v_, p), demand)):
            return start
        start += 1


def compile_params(pr):
    """the kv_calendar parameters of a profile, with its RD-phase landing margin"""
    P = kv_params(pr)
    return dict(P, rd_landing_nominal_hbm=P['rd_landing_nominal_hbm'] + pr['landing_uncertainty'])


def pc_plans(pr):
    """per PC K and V schedules at T 8192, the K lead (QK start after the K RD base) and the V lead (pair start after the
    V RD base), worst over the 128 PCs"""
    P = kv_params(pr)
    ks = KC.k_streams(T_MAX, P)
    vs = KC.pv16_v_streams(T_MAX, pv_rl=pr['v_rl'])
    PV = dict(P, rd_landing_nominal_hbm=P['rd_landing_nominal_hbm'] + pr['landing_uncertainty'])
    shape = pr.get('rd_shape') or {}
    plans, lead_k, lead_v = {}, 0, None
    for pc in range(128):
        k = shaped_schedule(ks[pc], PV, shape.get('K'))     # one H0 per leaf: K takes the V pass's one-edge RD margin
        lk = max(v - c for v, (_, c, _) in zip(_visible(k, PV), ks[pc]))
        start = v_start(vs[pc], PV, shape.get('V'))
        v = shaped_schedule(vs[pc], PV, shape.get('V'), start)
        plans[pc] = dict(k=k, v=v, v_start=start, nk=len(ks[pc]), nv=len(vs[pc]))
        lead_k = max(lead_k, lk)
        lead_v = start if lead_v is None else max(lead_v, start)
    return plans, P, lead_k, lead_v


def law_offsets(n, p0, gap):
    """qkd_kv_landing_cal / qkd_kv_front_cal put offsets: i up to P0, then GAP more before every further 8-block"""
    return [i + (gap * (1 + (i - p0) // 8) if i >= p0 else 0) for i in range(n)]


LAW_TS = sorted(set(list(range(1, 8193, 61)) + [x + d for x in (128, 256, 512, 1024, 2048, 4096, 4224, 4352, 4480, 8192)
                                                   for d in (-1, 0, 1) if 1 <= x + d <= 8192]))


def law_check(pr, plans, Ts=LAW_TS):
    """The calendar leaves replay ONE (P0, GAP) law per group for every context, so the T-8192 image must hold at every
    T: K / V put visible before its consume (fixes the leads), every sector landed before its block's law blk_go, and
    (V) the ring slot of sector i - depth consumed before put i.  Returns the leads that hold for every T checked."""
    P = compile_params(pr)
    lmax = P['rd_landing_nominal_hbm'] + P['front_window_hbm']
    law = {}
    for s in range(4):
        for g in range(8):
            pl = plans[SKC.physical_pc(s, g, 0)]
            law[(s, g)] = {kind: dict(zip(('P0', 'GAP'), pacing_of(pl[kind]['put'])), go0=pl[kind]['go'][0] - pl[kind]['issue'][0],
                                      issue=[x - pl[kind]['issue'][0] for x in pl[kind]['issue']]) for kind in ('k', 'v')}
    need_k, need_v, bad = 0, None, []
    for T in Ts:
        ks = KC.k_streams(T, P)
        vs = KC.pv16_v_streams(T, pv_rl=pr['v_rl'])
        for (s, g), L in law.items():
            pc = SKC.physical_pc(s, g, 0)
            for kind, st in (('k', ks.get(pc, [])), ('v', vs.get(pc, []))):
                if not st:
                    continue
                l = L[kind]
                off = law_offsets(len(st), l['P0'], l['GAP'])
                put = [l['go0'] + PUT_AFTER_GO + o for o in off]
                for b in range(0, len(st), 8):
                    last = min(len(st), b + 8) - 1
                    if l['issue'][last] + lmax > l['go0'] + off[b]:
                        bad.append(dict(T=T, group=f'{s}{g}', kind=kind, block=b // 8, why='blk_go before landing'))
                req = max(KC.hbm_to_core(x, P) + P['ring_cdc_core_edges'] - c for x, (_, c, _) in zip(put, st))
                if kind == 'k':
                    need_k = max(need_k, req)
                else:
                    need_v = req if need_v is None else max(need_v, req)
                    L.setdefault('v_cases', []).append((T, put, [c for _, c, _ in st]))
    for (s, g), L in law.items():                            # V ring room at the one lead every T uses
        for T, put, cons in L.get('v_cases', []):
            for i in range(P['ring_depth'], len(put)):
                if KC.hbm_to_core(put[i], P) < need_v + cons[i - P['ring_depth']] + 1:
                    bad.append(dict(T=T, group=f'{s}{g}', kind='v', sector=i, why='put before its ring slot is consumed'))
                    break
        L.pop('v_cases', None)
    return need_k, need_v, bad, len(Ts)


def runs_from_edges(edges, base, mask):
    """compress sorted RD reservation edges (+ base) into exact Run descriptors (count <= 1023, burst 1..16, gap)"""
    rel = [e + base for e in edges]
    runs, i = [], 0
    while i < len(rel):
        best = (1, 1, 0)
        for burst in range(1, 17):
            if i + burst < len(rel):
                gap = rel[i + burst] - rel[i + burst - 1] - 1
                if not 0 <= gap <= 255:
                    gap = 0
            else:
                gap = 0
            n = 0
            while i + n < len(rel) and n < 1023 and rel[i + n] == rel[i] + n + (n // burst) * gap:
                n += 1
            if n > best[0]:
                best = (n, burst, gap)
        n, burst, gap = best
        runs.append(CCI.Run(rel[i], n, burst, gap, mask=mask))
        i += n
    return runs


def pacing_of(put):
    from tools.qwen_static_kv.landing_cal_golden import pacing
    return pacing([x - put[0] for x in put]) if put else (511, 0)


# ---- the compile -------------------------------------------------------------------------------------------------------
def compile_all(pr, epoch=0x0b0b, program_words=None, workdir=None):
    sfi = _sfi()
    prog = program_words or sfi.bench_program()
    if len(prog) != sfi.PW + sfi.DW:
        raise ValueError('HOST programme image must be PW1024 + DW8 words')
    digest = sfi.image_digest(prog)
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        cal = link_calendar(td)
    prog_cal = cal['program']
    lay = prog_cal['layers']
    starts = [l['start'] for l in lay]
    msgs = cal['messages']
    seg0 = [m for m in msgs if m.get('seg', 0) == 0]
    cmd = [m for m in seg0 if m['src'] == 'C' and m['rx_port'] == 0 and m['kind'] == 1]
    kvn = sorted((m for m in seg0 if m['src'] == 'C' and m['rx_port'] == 3 and m['kind'] == 5), key=lambda m: m['beat'])
    st = [m for m in seg0 if m['src'] == 'K' and m['tx_port'] == 0 and m['kind'] == 4]
    res = sorted((m for m in seg0 if m['src'] == 'K' and m['tx_port'] == 0 and m['kind'] == 3), key=lambda m: m['beat'])
    if len(cmd) != 1 or len(st) != 1 or len(kvn) != 4 or len(res) != 32:
        raise ValueError('link calendar: one CMD / STATUS, 4 KVN and 32 RESULT beats per layer run expected')

    # ---- attention programme: link-fixed words ----
    cmd_ev = cmd[0]['rx_out'] + LR.D2D_OUT + pr['rx']           # CMD at the attention programme's rx pin (run-base)
    run_ev = cmd_ev - LR.RX_CMD
    start_qk = run_ev + LR.RX_CMD + LR.Q_TO_START
    tx_first = res[0]['cyc'] + LR.D2D_OUT - run_ev              # att_tx_slot of RESULT beat 0 at the programme
    tx_end = tx_first + 34
    service_end = tx_first - LR.RX_CMD - 2 + 31
    if res[-1]['cyc'] - res[0]['cyc'] != 31 or st[0]['cyc'] != res[0]['cyc'] + 33:   # static_ctl: STATUS at tx_first + 33
        raise ValueError('RESULT burst / STATUS not on consecutive link slots')

    # ---- K / V leads and the layer roots ----
    plans, P, lead_k, lead_v = pc_plans(pr)
    law = None
    if pr['kind'] == 'component':                           # the bench-fed image used the capacity screen's lead
        lead_k = KC.screen_36_capacity(T_MAX, P)['layer']['qk_start_after_prefetch_core']
    else:
        lk, lv, bad, nT = law_check(pr, plans)
        if bad:
            raise ValueError(f'one calendar law per group does not hold for every context: {bad[:5]}')
        law = dict(contexts_checked=nT, lead_k_T8192=lead_k, lead_v_T8192=lead_v, lead_k=lk, lead_v=lv)
        lead_k, lead_v = max(lead_k, lk), max(lead_v, lv)
    att8192 = attention_calendar(T_MAX, pr)
    e_k = CMD_LEAD + 2
    if pr['kind'] == 'component':
        kgo_ev, d_v = start_qk - lead_k, KC._pv_start(T_MAX)    # layer_roots_from_link: kgo = start_qk - lead, vgo = kgo + PV
    else:
        kgo_ev = start_qk - lead_k - crossing_core(e_k + CAL_PIN_EDGES, pr) - 1 - pr['groups'] - 1
        d_v = att8192['PV_START'] + lead_k - lead_v - 2
    writer_ev = kvn[0]['rx_out'] + LR.D2D_OUT + pr['kvn'] - LR.WRITER_T0 - pr['writer']
    rel = dict(ctrl_go=kgo_ev, kgo=kgo_ev, vgo=kgo_ev + d_v, attention_issue=run_ev - LR.ISSUE_TO_RUN - pr['att'],
               attention_run=run_ev - pr['att'], writer_start=writer_ev, link_start=LR.LINK_START,
               expected_quiet=st[0]['cyc'] + 1)
    lead = LR.START_LEAD - pr['start_relays']
    rel = {k: (v + lead if k != 'link_start' else v) for k, v in rel.items()}
    ends = [starts[1]] + [lay[s]['start'] - lay[s - 1]['start'] for s in range(2, 36)] + [lay[35]['cycles']]
    rows = []
    for s in range(1, 37):
        base = starts[0] if s == 1 else 0
        roots = {k: (v + base if k != 'link_start' else v) for k, v in rel.items()}
        roots['stage_end'] = ends[s - 1]
        rows.append(dict(stage=s, roots=roots))
    img = assemble_rows(rows, digest, epoch)
    if img['token_core_cycles'] != prog_cal['token_cycles_through_L35']:
        raise ValueError('layer frames differ from the link token cycles')
    layer_words = img['words']

    # ---- writer programme (target 2): word slots after the writer start ----
    t = [LR.WRITER_T0 + (m['rx_out'] - kvn[0]['rx_out']) for m in kvn]
    stop = t[3] + WRITER_STOP_AFTER
    if t[0] < 4 or any(b <= a for a, b in zip(t, t[1:])) or stop - t[3] < 3:
        raise ValueError('writer programme slots violate qkd_kv_native_programme boot checks')
    writer_words = [w for _ in range(36) for w in t + [stop]] + [FOOTER_WRITER]

    # ---- ownership (target 3): go = token start (programme internal start) ----
    quiet36 = max(e['token_cycle'] for e in img['events'] if e['kind'] == 'expected_quiet')
    own = [3, quiet36 + 1, img['token_core_cycles'], OWN_SEAL]
    if not 3 <= own[0] < own[1] < own[2]:
        raise ValueError('ownership roots out of order')

    # ---- per-group landing / front calendars (targets 4, 5) ----
    group = {}
    d_hbm_floor = (CORE_U * d_v) // HBM_U
    for s, stn in enumerate(STACKS):
        for g in range(8):
            pcs = [SKC.physical_pc(s, g, q) for q in range(4)]
            k = [plans[pc]['k'] for pc in pcs]
            v = [plans[pc]['v'] for pc in pcs]
            if any(x['put'] != k[0]['put'] for x in k) or any(x['put'] != v[0]['put'] for x in v):
                raise ValueError(f'group {stn}{g}: the four PCs need one put stream (one calendar leaf a group)')
            kp0, kgap = pacing_of(k[0]['put'])
            vp0, vgap = pacing_of(v[0]['put'])
            # front A (K) -> first put; V uses the same RD base convention through the controller's V run
            h0_k = e_k + CAL_PIN_EDGES + k[0]['go'][0] + PUT_AFTER_GO - k[0]['issue'][0]
            h0_v = e_k + CAL_PIN_EDGES + v[0]['go'][0] + PUT_AFTER_GO - v[0]['issue'][0]
            if pr['crossing'] and h0_k != h0_v:
                raise ValueError(f'group {stn}{g}: K / V first-put ages differ ({h0_k} / {h0_v}); one H0 per leaf')
            h0 = h0_k
            xu = XU_STRICT if pr['crossing'] else 0
            h0_l = h0 + (LAUNCH_HBM_EDGES if pr['crossing'] else 0)
            if not (0 <= xu < 768 and 0 <= h0_l < 256 and 0 <= h0 - 3 < 256 and 0 <= pr['ld'] <= 8 and 0 <= pr['rc'] < 16):
                raise ValueError(f'group {stn}{g}: calendar constant outside its field')
            ident = (s << 3) | g
            group[f'{stn}_{g}'] = dict(index=8 * s + g, pcs=pcs, K=dict(P0=kp0, GAP=kgap, n=len(k[0]['put'])),
                                       V=dict(P0=vp0, GAP=vgap, n=len(v[0]['put'])), H0_front=h0, H0_landing=h0_l, XU=xu,
                                       landing_words=[ident, xu, h0_l, (pr['ld'] << 4) | pr['rc'], (kgap << 9) | kp0, (vgap << 9) | vp0],
                                       front_words=[ident, 0, h0, 0, (kgap << 9) | kp0, (vgap << 9) | vp0])
    landing_words = [w for k_ in sorted(group, key=lambda n: group[n]['index']) for w in group[k_]['landing_words']]
    front_words = [w for k_ in sorted(group, key=lambda n: group[n]['index']) for w in group[k_]['front_words']]

    # ---- per-PC controller calendars (targets 6..9): K and V RD reservations + the command template ----
    e_v = e_k + d_hbm_floor + (1 if pr['crossing'] else 0)
    ctrl = {}
    for s in range(4):
        for pcl in range(32):
            pc = 32 * s + pcl
            pl = plans[pc]
            kr = runs_from_edges(pl['k']['issue'], e_k - pl['k']['issue'][0], 1)
            vr = runs_from_edges(pl['v']['issue'], e_v - pl['v']['issue'][0], 1)
            k0, v0 = kr[0].edge, vr[0].edge
            cmds = [CCI.Run(k0 + o, **kw) for o, kw in K_CMDS] + [CCI.Run(v0 + o, **kw) for o, kw in V_CMDS]
            runs = sorted(cmds + kr + vr, key=lambda r: r.edge)
            z = CCI.compile_image(runs, deadline=65535, capacity=16)
            want = {k0 + (e - pl['k']['issue'][0]) for e in pl['k']['issue']} | {v0 + (e - pl['v']['issue'][0]) for e in pl['v']['issue']}
            got = {e for e, ev in z['events'].items() if ev['mask'] == 1}
            if got != want:
                raise ValueError(f'PC {pc}: controller RD reservations differ from the kv_calendar issue edges')
            words = []
            for w in z['words']:
                words += [w & ((1 << 64) - 1), w >> 64]     # cfg addr[4] selects the high half: addr n -> low, 16+n -> high
            lo, hi = words[0::2], words[1::2]
            ctrl[pc] = dict(runs=len(runs), k_first=k0, v_first=v0, words=lo + hi)
    ctrl_targets = {6 + s: [w for pcl in range(32) for w in ctrl[32 * s + pcl]['words']] for s in range(4)}

    # ---- phase legality of the launches (beat-aligned token run start) ----
    phase = None
    if pr['phase']:
        ph = pr['phase']
        bad = []
        for e in img['events']:
            if e['kind'] in ('ctrl_go', 'kgo', 'vgo'):
                c = e['token_cycle'] + 1 + pr['groups'] + 1      # internal start +1, tree, go_q capture at the group tile
                toggle_u = CORE_U * (c + 1)
                gap = (ph['PH0'] - toggle_u) % HBM_U or HBM_U
                if not ph['SAFE_LOW_U'] <= gap <= ph['SAFE_HIGH_U']:
                    bad.append(dict(stage=e['stage'], root=e['kind'], gap_u=gap))
        period = prog_cal.get('token_period')
        phase = dict(assumption='token run start at HBM-beat phase 0 (q = PH0 at the reset-release beat)',
                     launches=36 * 3, outside_window=bad, token_period_core=period,
                     token_period_mod_768=None if period is None else period % 768,
                     requirement='the token period (or each run start) must be a multiple of 768 core edges for one compiled '
                                 'set of launch phases to hold every token; otherwise a phase-launch fault aborts some tokens')

    # ---- attention words ----
    att = dict(compiled_rx_cmd=LR.RX_CMD, compiled_tx_first=tx_first, compiled_end=tx_end, service_end=service_end,
               start_qk_run_age=start_qk - run_ev, law='calendar(T) = attention_calendar(T, profile, service_end): R stretched so '
               'PV_START + max(P0, P1, R) + 49 = service_end for every T in 1..8192',
               samples={})
    for T in (1, 128, 1000, 2048, 4096, 6144, 8192):
        c = attention_calendar(T, pr, service_end)
        att['samples'][str(T)] = dict(cal=AC.hexcal(c), fields=c)

    # ---- boot bundle ----
    sfi_pw = sfi.PW
    images = [dict(target=1, program=layer_words, descriptors=[]), dict(target=2, program=writer_words, descriptors=[]),
              dict(target=3, program=own, descriptors=[]), dict(target=4, program=landing_words, descriptors=[]),
              dict(target=5, program=front_words, descriptors=[])] + \
             [dict(target=t_, program=ctrl_targets[t_], descriptors=[]) for t_ in (6, 7, 8, 9)] + \
             [dict(target=0, program=prog[:sfi_pw], descriptors=prog[sfi_pw:])]
    bundle = PTF.encode_boot_bundle(epoch, images)
    if int(bundle['images'][-1]['digest'], 16) != digest:
        raise ValueError('HOST ISA image digest differs from the layer programme LP_DIGEST')
    return dict(profile=pr, link=dict(cmd_event=cmd_ev, run_event=run_ev, start_qk=start_qk, result_first_slot=res[0]['cyc'],
                                      token_cycles=prog_cal['token_cycles_through_L35'], token_period=prog_cal.get('token_period')),
                leads=dict(k=lead_k, v=lead_v, kgo_event=kgo_ev, vgo_minus_kgo=d_v, e_k=e_k, e_v=e_v, start_lead=lead, law=law),
                layer=dict(rows=rows, words=layer_words, digest=digest, epoch=epoch, token_core_cycles=img['token_core_cycles'],
                           events=img['events']),
                writer=dict(slots=t, stop=stop, words=writer_words), ownership=dict(words=own, go='token start (assumed)'),
                groups=group, landing_words=landing_words, front_words=front_words, controller=ctrl, controller_targets=ctrl_targets,
                attention=att, phase=phase, images=images, bundle=bundle)


# ---- operations on actual template ports (opentallas.qwen_kv_static.programme.v1) -------------------------------------
ROOT_PORTS = {
    'ctrl_go': ('hbm_command', [('phase_{st}_{g}', 'ctrl_go')]),
    'kgo': ('k_row', [('phase_{st}_{g}', 'kgo'), ('lcal_{st}_{g}', 'kgo'), ('ki_{st}_{g}', 'kgo')]),
    'vgo': ('v_row', [('phase_{st}_{g}', 'vgo'), ('lcal_{st}_{g}', 'vgo')]),
    'attention_issue': ('head_compute', [('attention_programme', 'issue')]),
    'attention_run': ('head_compute', [('attention_programme', 'run')]),
    'writer_start': ('kv_write', [('wprg', 'start')]),
}


def operations(r):
    ops = []
    for e in r['layer']['events']:
        if e['kind'] not in ROOT_PORTS:
            continue
        kind, cons = ROOT_PORTS[e['kind']]
        operands = []
        for inst, port in cons:
            if '{st}' in inst:
                operands += [dict(instance=inst.format(st=st, g=g), port=port) for st in STACKS for g in range(8)]
            else:
                operands.append(dict(instance=inst, port=port))
        ops.append(dict(id=f'S{e["stage"]}.{e["kind"]}', kind=kind, cycle=e['token_cycle'], domain='core',
                        results=[dict(instance='layer_programme', port=e['kind'])], operands=operands))
        if e['kind'] == 'attention_run':
            ops.append(dict(id=f'S{e["stage"]}.att_cmd_rx', kind='link_transfer', cycle=e['token_cycle'] + r['attention']['compiled_rx_cmd'],
                            domain='core', results=[dict(instance='d2d', port='att_rx_v')],
                            operands=[dict(instance='attention_programme', port='rx_event')]))
            ops.append(dict(id=f'S{e["stage"]}.att_result_tx', kind='link_transfer',
                            cycle=e['token_cycle'] + r['attention']['compiled_tx_first'], domain='core',
                            results=[dict(instance='attention_programme', port='tx_valid')],
                            operands=[dict(instance='d2d', port='att_tx_v')]))
    return ops


def check_ports(ops, root=ROOT):
    """every operand / result names an actual input / output port of the static-join template instance"""
    import kv_static as K
    g, _ = K.template(root)
    specs = {}
    for i in g['instances']:
        sp = K.source(i['source'], i['module'], root)
        specs[i['name']] = {p['name']: p['direction'] for p in sp['ports']}
    for op in ops:
        for key, d in (('operands', 'input'), ('results', 'output')):
            for ep in op[key]:
                if specs.get(ep['instance'], {}).get(ep['port']) != d:
                    raise ValueError(f'{op["id"]}: {ep["instance"]}.{ep["port"]} is not an actual {d}')
    return len(ops)


def write(r, out, root=ROOT):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ops = operations(r)
    check_ports(ops, root)
    srcs = ['tools/qwen_kv_die/kv_static_programme.py', 'tools/qwen_kv_die/kv_static_ages.py', 'tools/qwen_split/d2d_link_calendar.py',
            'tools/qwen_static_kv/layer_roots_from_link.py', 'tools/qwen_static_kv/layer_programme.py',
            'tools/qwen_static_kv/program_target_frames.py', 'tools/qwen_static_kv/controller_calendar_image.py',
            'tools/qwen_static_kv/landing_cal_golden.py', 'tools/qwen_static_schedule/kv_calendar.py',
            'tools/qwen_kv_die/static_qk_calendar.py', 'tools/qwen_kv_die/static_kv_calendar.py',
            'tools/qwen_attention_native/attn_calendar.py', 'tools/qwen_kv_die/compile_native_endpoint.py',
            'tools/qwen_split/sys_face_image.py', AGES]
    programme = dict(schema='opentallas.qwen_kv_static.programme.v1', status='COMPILED_NOT_QUALIFIED', profile=r['profile']['kind'],
                     compiler_sources=[dict(path=p, sha256=sha(root / p)) for p in srcs if (root / p).exists()],
                     operations=ops, emitted_instruction_count=len(ops))
    (out / 'programme.json').write_text(json.dumps(programme, indent=1) + '\n')
    (out / 'boot_bundle.json').write_text(json.dumps(r['bundle'], indent=1) + '\n')
    for im in r['images']:
        (out / f'target{im["target"]}.hex').write_text(''.join(f'{w:016x}\n' for w in im['program'] + im['descriptors']))
    vec = ''.join(f'{w:08x}' for w in reversed(r['layer']['words'][:324]))
    (out / 'layer_programme_image.svh').write_text(
        f'// GENERATED by tools/qwen_kv_die/kv_static_programme.py (profile {r["profile"]["kind"]}): do not edit\n'
        f"localparam [36*9*32-1:0] LP_ROOTS = {36*9*32}'h{vec};\n"
        f"localparam [63:0] LP_DIGEST = 64'h{r['layer']['digest']:016x};\n"
        f"localparam [15:0] LP_EPOCH = 16'd{r['layer']['epoch']};\n")
    report = dict(schema='opentallas.qwen_kv_static.programme_report.v1', status='COMPILED_NOT_QUALIFIED',
                  profile=r['profile'], link=r['link'], leads=r['leads'],
                  layer_relative_roots=r['layer']['rows'][1]['roots'], stage1_roots=r['layer']['rows'][0]['roots'],
                  writer=dict(slots=r['writer']['slots'], stop=r['writer']['stop']), ownership=r['ownership'],
                  groups={k: {kk: vv for kk, vv in v.items() if kk not in ('landing_words', 'front_words')} for k, v in r['groups'].items()},
                  controller={str(pc): {k: v for k, v in c.items() if k != 'words'} for pc, c in r['controller'].items()},
                  attention=r['attention'], phase=r['phase'],
                  boot=dict(target_order=r['bundle']['target_order'], frames=len(r['bundle']['frames528']),
                            words={str(im['target']): len(im['program']) + len(im['descriptors']) for im in r['images']},
                            digests={str(i['target']): i['digest'] for i in r['bundle']['images']}),
                  operations=len(ops), boot_bundle_sha256=sha(out / 'boot_bundle.json'), programme_sha256=sha(out / 'programme.json'),
                  open=['static floorplan (OT_KV_STATIC plan) to replace PLAN_ANALOG / COLOCATED ages, then recompile',
                        'native benches of the boot-loaded images on the joined subsystem; TT/FF closure of every element',
                        'controller command words are the native bench template; JEDEC timing of the moved runs to re-check',
                        'embedding row / host transfer operations (KVJ-C) and the N1 generator RTL (KVJ-B) join'])
    (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--ages', type=Path, default=ROOT / AGES)
    ap.add_argument('--profile', choices=('die', 'component'), default='die')
    ap.add_argument('--epoch', type=lambda s: int(s, 0), default=0x0b0b)
    ap.add_argument('--program', type=Path, help='installed HOST programme image (PW1024 + DW8 64-b hex words)')
    a = ap.parse_args()
    ages = json.loads(a.ages.read_text()) if a.profile == 'die' else None
    words = [int(x, 16) for x in a.program.read_text().split()] if a.program else None
    r = compile_all(profile(a.profile, ages), a.epoch, words)
    rep = write(r, a.out)
    print(json.dumps(dict(status=rep['status'], profile=a.profile, leads=rep['leads'], stage1=rep['stage1_roots'],
                          attention={k: rep['attention'][k] for k in ('compiled_rx_cmd', 'compiled_tx_first', 'compiled_end')},
                          boot=rep['boot']['words'], frames=rep['boot']['frames'], operations=rep['operations'],
                          phase_outside=None if rep['phase'] is None else len(rep['phase']['outside_window']))))


if __name__ == '__main__':
    main()
