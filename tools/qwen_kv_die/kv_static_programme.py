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
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for p in (ROOT, ROOT / 'tools', HERE, ROOT / 'tools/qwen_static_kv', ROOT / 'tools/qwen_attention_native'):
    sys.path.insert(0, str(p))

import attn_calendar as AC                                  # noqa: E402
import kv_qkh_safe32 as QKH32                               # noqa: E402
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
# HKV-ASTK 2026-10-18: the expanded ASTK strip (OT_KV_ASTK_EXPAND=1, as kv_static_die: RL 3 die-relayed chain hops, closed
# ctl Z stride 4, distributed e-read qkd_astk_er_chain_st ERL 42) moves the attention calendar by MEASURED shifts relative to
# the RL 1 / ERL 7 strip the attn_calendar laws were measured on (astk_calendar_sweep.sh on the actual strip + mapped SRAM,
# Verilator 5.050): LMAX / EXP / Z (+ the hub ages that follow them), the P.V e-read issue gap and the e-read latency.
# KV-FLOOR1 10-20 (default off): the pair END FLOOR control (ot_qwen_tp8_pv_wide_ctl_tbf, kv_bootage OT_KV_PVFIN_FLOOR):
# both pairs publish on pair 0's issue count, so the compiler law is P1 = P0 (die profile pv_floor)
PV_FLOOR = os.environ.get('OT_KV_PVFIN_FLOOR', '0') == '1'
ASTK_EXPAND = os.environ.get('OT_KV_ASTK_EXPAND', '1') == '1'   # HKV-DIE3 10-19: production default ON (= kv_static_die)
ASTK_LAW = 'results/arch/qwen_kv_die/hkv_astk_calendar_1018/astk_calendar_law.json'


def astk_law():
    law = json.loads((ROOT / ASTK_LAW).read_text())
    if law.get('schema') != 'opentallas.qwen_kv.astk_calendar_law.v1':
        raise ValueError('kv_static_programme: unknown ASTK calendar law schema')
    return law


def astk_pv_gap_shift(T, law):
    """P.V e-read issue gap shift at T: the larger of the measured neighbours (clamped at the measured range)"""
    pts = sorted((int(t), v) for t, v in law['d_pv_gap'].items())
    lo = [v for t, v in pts if t <= T] or [pts[0][1]]
    hi = [v for t, v in pts if t >= T] or [pts[-1][1]]
    return max(lo[-1], hi[0])
# ROOT-QLINE 10-18: the SAME compile as the committed production image rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh
# (tools/qwen_split/d2d_cal_image_production.sh, QXF-LINK 6ef1a097f): die seam stages + the LAYERBENCH compiled token path,
# so target 11 (KV sequencer init) loads exactly the calendar the RTL image / D2D_TXDP_K were compiled from.  The old
# '--txd-c 1,1,1,2 --txd-k 1,2,1,1' args predate the compiled TXDP and no longer match the image.
# KV-LINKCFG-MU 10-19: ONE seam source.  The die seam stages are no longer a constant here (it was the stale dv2f14bq / kvs14p
# seam 2,2,2,2,2,2/11,11,9,9,9,11,11 after the pair image moved to the MU release seam): they are read from the D2D_TXDP_C
# record of the BOUND image (LINK_IMAGE), i.e. the stages the strict bind checks against the compute die.v
# (die_params audit (e), record_bundles.seam_stages) and the KV die table (BUNDLE_EQ K.*) the image was compiled for.
# OT_KV_MU=1 binds the MU image d2d_cal_image_mu.svh and compiles with --mu (the token run's MU context slot: K TX +1 entry,
# K TX SEG2 8 -> 9), so the KV link end carries the slot.  link_image_check() proves target 11 == the bound image.
LINK_IMAGE_SU = 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh'
LINK_IMAGE_MU = 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh'
LINK_MU = os.environ.get('OT_KV_MU', '0') == '1'
LINK_IMAGE = LINK_IMAGE_MU if LINK_MU else LINK_IMAGE_SU
# KV-EMBWIN16 10-20 (DRIVE-KV decision, KV-CAL15 finding): OT_KV_EMB_WIN=<edges> grows the token-run embedding window
# (d2d_link_calendar --emb-window; L0..L35 and the token period move with it) so the embedding fill meets the row header
# slot on the die relays.  The pair image is the committed d2d_cal_image[_mu]_ew<N>.svh (d2d_cal_image_production.sh with
# D2D_EMB_WINDOW=<N>); both link ends bind it (KV: target 11 + the dcal tile's START / period constants, compute: its
# sequencer).  Default unset = the priced window (272), images unchanged.
LINK_EMB_WIN = os.environ.get('OT_KV_EMB_WIN', '')
if LINK_EMB_WIN:
    if not LINK_EMB_WIN.isdigit():
        raise SystemExit(f'OT_KV_EMB_WIN={LINK_EMB_WIN!r}: an integer edge count expected')
    LINK_IMAGE = LINK_IMAGE.replace('.svh', f'_ew{int(LINK_EMB_WIN)}.svh')
# KV-PROG17 10-20: the r16 attention tile (OT_KV_ATTN_R16=1, kv_static_die.ATTN_R16) moves the K RESULT burst +1 (TX_SHIFT)
# and the K STATUS +213 (STATUS_DELAY) in every layer, so target 11 must load the r16 pair image
# d2d_cal_image[_mu][_ew<N>]_r16.svh (d2d_cal_image_production.sh D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213); fail closed.
LINK_R16 = os.environ.get('OT_KV_ATTN_R16', '0') == '1'
if LINK_R16:
    LINK_IMAGE = LINK_IMAGE.replace('.svh', '_r16.svh')
# The OVL source uses the actual RoPE pair image, not an intermediate scalar variant.
LINK_ROPE_OVL = os.environ.get('OT_KV_ROPE_OVL', '0') == '1'
if LINK_ROPE_OVL:
    LINK_IMAGE = LINK_IMAGE.replace('.svh', '_rope.svh')
# KV-P6-BOOT 10-23 (opt-in, default unset = unchanged): OT_KV_LINK_IMAGE=<path> binds a CANDIDATE pair image compiled by
# d2d_cal_image_production.sh with the bound KV seam stages (D2D_K_STAGES); link_image_check stays fail-closed on it.
# A candidate image is a PAIR change: the compute die sequencer must bind the same image before a release.
if os.environ.get('OT_KV_LINK_IMAGE'):
    LINK_IMAGE = os.environ['OT_KV_LINK_IMAGE']
if not (ROOT / LINK_IMAGE).is_file():
    raise SystemExit(f'no committed selected pair image {LINK_IMAGE} '
                     f'(MU={int(LINK_MU)}, EMB_WINDOW={LINK_EMB_WIN!r}, '
                     f'R16={int(LINK_R16)}, ROPE_OVL={int(LINK_ROPE_OVL)})')


def image_die_stages(img=None, root=None):
    """the die seam stages a committed d2d_cal_seq_image.py image records (D2D_TXDP_C comment) as a --die-stages string"""
    import ast
    import re
    txt = ((root or ROOT) / (img or LINK_IMAGE)).read_text()
    m = re.search(r"D2D_TXDP_C = 32'h[0-9a-fA-F]+;.*die stages (\{[^}]*\})", txt)
    if not m:
        raise SystemExit(f'kv_static_programme: {img or LINK_IMAGE} records no die stages (recompile it with '
                         'tools/qwen_split/d2d_cal_image_production.sh)')
    sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
    import d2d_link_calendar as _L
    st = ast.literal_eval(m.group(1))
    if set(st) != set(_L.STAGE_NAMES):
        raise SystemExit(f'kv_static_programme: image die stages {sorted(st)} != {_L.STAGE_NAMES}')
    v = [st[k] for k in _L.STAGE_NAMES]
    return ','.join(map(str, v[:6])) + '/' + ','.join(map(str, v[6:]))


def _link_kv_codec():
    """the KV attention codec edges as instantiated in the KV tile source (.LAND(1) -> 2), as the production image"""
    sys.path.insert(0, str(ROOT / 'tools' / 'qwen_layerbench'))
    import layer_compile as _LC
    return str(_LC.kv_codec_edges((ROOT / 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv').read_text()))


LINK_DIE_STAGES = image_die_stages()
LINK_TOKEN_PATH = 'results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/token_path_compiled.json.gz'
LINK_ARGS = ['--txl', '6', '--phy', '5', '--profile', 'program', '--die-stages', LINK_DIE_STAGES, '--kv-codec', _link_kv_codec(),
             '--host-stages', '0', '--link-handoff', 'results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json',
             '--pinreg'] + (['--mu'] if LINK_MU else []) + (['--emb-window', str(int(LINK_EMB_WIN))] if LINK_EMB_WIN else []) + (['--rope'] if LINK_ROPE_OVL else [])
#            + --token-path (decompressed in link_calendar)
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


def attn_r16():
    """KV-BIND4 10-19 (kv_static_die.ATTN_R16): (rx edges, tx shift, STATUS_DELAY) of the bound r16 attention tile"""
    from tools.qwen_kv_die import kv_static_die as KSD
    if not getattr(KSD, 'ATTN_R16', False):
        return dict(on=False, rx_edges=0, tx_shift=0, status_delay=0)
    return dict(on=True, rx_edges=KSD.ATTN_R16_RX_EDGES, tx_shift=KSD.ATTN_R16_TX_SHIFT,
                status_delay=KSD.ATTN_R16_PARAMS['STATUS_DELAY'])


def link_calendar(workdir, status_delay=0, attn_tx_shift=None):
    """attn_tx_shift None = the bound attention tile's TX shift (KV-BIND4 r16: +1 on the K RESULT burst / STATUS)"""
    import gzip
    if attn_tx_shift is None:
        attn_tx_shift = attn_r16()['tx_shift']
    out = Path(workdir) / 'cal'
    tp = Path(workdir) / 'token_path_compiled.json'
    tp.write_bytes(gzip.decompress((ROOT / LINK_TOKEN_PATH).read_bytes()))
    p = subprocess.run([sys.executable, str(ROOT / 'tools/qwen_split/d2d_link_calendar.py'), '--out', str(out)] + LINK_ARGS
                       + ['--token-path', str(tp), '--status-delay', str(status_delay)]
                       + (['--attn-tx-shift', str(attn_tx_shift)] if attn_tx_shift else []),
                       cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        raise SystemExit('link calendar compile failed: ' + p.stderr[-2000:])
    return json.loads((out / 'calendar.json').read_text())


LINK_CFG_TARGET, LINK_CFG_WORDS = 11, 66


def link_cfg_words(caldir, end='K', base_seg=2):
    """KVJ-SMALL 10-17: boot dispatcher target 11 (qkd_static_kv_boot_dispatch LINKCFG=1) for the KV link end's cfg port.
    Words in the calendar sequencer's init order (ot_qwen_d2d_cal_seq): TX entry i, RX entry i (i = 0..31), then the TX and
    RX segment-1 bases.  The KV sequencer runs ADM=1, so its init bases are the admission segment (seg2); data[63:32] = 0."""
    cd = Path(caldir)
    rd = lambda f: [int(x, 16) for x in (cd / f).read_text().split()]
    tx, rx = rd(f'cal_{end}_tx.memh'), rd(f'cal_{end}_rx.memh')
    if len(tx) != 32 or len(rx) != 32:
        raise ValueError('link calendar image must have 32 TX and 32 RX entries')
    sfx = f'_seg{base_seg}'
    words = [w for i in range(32) for w in (tx[i], rx[i])] + [rd(f'cal_{end}_tx{sfx}.memh')[0], rd(f'cal_{end}_rx{sfx}.memh')[0]]
    if len(words) != LINK_CFG_WORDS or any(not 0 <= w < 1 << 32 for w in words):
        raise ValueError('link cfg image: 66 words of 32 bits expected')
    return words


def image_link_cfg_words(img=None, end='K', root=None):
    """the 66 target-11 words a committed sequencer image implies for the KV end (the qkd_d2d_cal_seq init stream with
    ADM=1: TX i, RX i for i = 0..31, then the admission-segment TX / RX bases)"""
    import re
    txt = ((root or ROOT) / (img or LINK_IMAGE)).read_text()
    val = lambda n: int(re.search(rf"{n} = \d+'h([0-9a-fA-F]+);", txt).group(1), 16)
    tx, rx = val(f'D2D_CAL_{end}_TX_IMG'), val(f'D2D_CAL_{end}_RX_IMG')
    return [w for i in range(32) for w in ((tx >> 32 * i) & 0xffffffff, (rx >> 32 * i) & 0xffffffff)] + \
        [val(f'D2D_CAL_{end}_TX_SEG2'), val(f'D2D_CAL_{end}_RX_SEG2')]


def link_image_check(words, cal=None, img=None, root=None):
    """KV-LINKCFG-MU 10-19: target 11 must be the bound image's K calendar word for word (fail closed).  Also records the
    KV TXDP the compile implies with the die's own attention codec against the image's D2D_TXDP_K (a codec disagreement
    changes TXDP_K and the compute C RX image, never the K words: reported, not hidden)."""
    import re
    img = img or LINK_IMAGE
    want = image_link_cfg_words(img, root=root)
    diff = [i for i, (a, b) in enumerate(zip(words, want)) if a != b] + ([len(want)] if len(words) != len(want) else [])
    if diff:
        raise ValueError(f'target 11 differs from {img} at word(s) {diff[:8]} (MU {LINK_MU}, die stages {LINK_DIE_STAGES}): '
                         'the link end would load another calendar than the bound sequencer image')
    rec = dict(image=img, mu=LINK_MU, die_stages=LINK_DIE_STAGES, words=len(words), equal=True)
    if cal is not None and cal.get('txd'):
        sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
        import d2d_link_calendar as _L
        txt = ((root or ROOT) / img).read_text()
        rec.update(txdp_k_image=int(re.search(r"D2D_TXDP_K = 32'h([0-9a-fA-F]+);", txt).group(1), 16),
                   txdp_k_die_codec=_L.txdp_word(cal['txd']['K']), kv_codec=int(_link_kv_codec()))
        rec['txdp_k_agree'] = rec['txdp_k_image'] == rec['txdp_k_die_codec']
        if not rec['txdp_k_agree']:
            raise ValueError(f"target 11 TXDP codec differs from {img}: image {rec['txdp_k_image']:#010x}, die {rec['txdp_k_die_codec']:#010x}; recompile both pair images for the die codec")
    return rec


ES_CFG_TARGETS, ES_CFG_WORDS = (12, 13), (1024, 8)
ES_CFG_CTRL_LAT = 92          # KVJ-C3 bench model of the controller es -> er latency (open: measured per-PC value owed)


def es_cfg_words(ctrl_lat=ES_CFG_CTRL_LAT, relay=(0, 0, 0, 0), return_relay=(0, 0, 0, 0)):
    """KVJ-SMALL b2 10-17: boot dispatcher targets 12 / 13 (qkd_static_kv_boot_dispatch ESCFG=1) for the shared boot bus
    of qkd_kv_es_fan_root + qkd_embedding_static_join4_cal (KVJ-C3).  Image = kvjc3_pc_chain.boot_words.  Target 12 word
    a = {stack[1:0], pc[4:0], reg[2:0]} (the dispatcher's es_cfg_addr = a[7:0]; data[17:16] = stack is checked against
    a[9:8]); target 13 word a = beat segment a (8 words, unused segments {len 0, off 0} = never a slot)."""
    import kvjc3_pc_chain as C3
    words = C3.boot_words(C3.emb_calendar(ctrl_lat, list(relay), return_relay=return_relay))
    pc, beat = [None] * ES_CFG_WORDS[0], [(1 << 62)] * ES_CFG_WORDS[1]
    for addr, data in words:
        if data >> 62 == 0:
            a = (((data >> 16) & 3) << 8) | addr
            if pc[a] is not None or data >> 18:
                raise ValueError(f'es cfg: PC word {a} duplicated or malformed')
            pc[a] = data
        elif data >> 62 == 1:
            if addr > 7 or (data >> 24) & ((1 << 38) - 1):
                raise ValueError(f'es cfg: beat segment word {addr} malformed')
            beat[addr] = data
        else:
            raise ValueError('es cfg: boot word targets only 0 (root) / 1 (join4_cal)')
    if any(w is None for w in pc):
        raise ValueError('es cfg: the 128 x 8 PC player constants must all be present')
    return pc, beat


# ---- profile: every age the compile uses -----------------------------------------------------------------------------
def _face_land():
    """HKV-RSTCAP 10-19: kvs_attn_fl lands i_ctl (+1: every lprg -> attention launch one edge earlier = att + 1) and fin
    (+1: F_DLY + 1); every _fl tile releases reset +3 edges later (startup only; checked against the region hold budget).
    HKV-DIE3 10-19: per tile -- only the SELECTED tiles (kv_static_die.FACE_LAND_SEL) add their edges."""
    from tools.qwen_kv_die import kv_static_die as KSD
    sel = sorted(getattr(KSD, 'FACE_LAND_SEL', set(KSD.FACE_LAND_TILES) if KSD.FACE_LAND else set()))
    if not sel:
        return dict(enabled=False, selected=[], i_ctl=0, fin=0, rst_release_max=0)
    t = {k: KSD.FACE_LAND_TILES[k] for k in sel}
    rr = max(v['rst_release'] for v in t.values())
    if rr > KSD.FACE_LAND_RST_BUDGET:
        raise ValueError(f'face_land reset release +{rr} exceeds the region hold budget {KSD.FACE_LAND_RST_BUDGET}')
    a = t.get('kvs_attn', {})
    return dict(enabled=True, selected=sel, i_ctl=a.get('i_ctl', 0), fin=a.get('fin', 0), rst_release_max=rr,
                F_DLY_delta=a.get('fin', 0), tiles=sel,
                rst_release={k: v['rst_release'] for k, v in t.items()})


def hroot_landing(ksd=None):
    """Increment over the unlanded HROOT, per actual selected RTL implementation.

    Gather is an observer transport age, not an extra compute cycle. Its
    boot/ownership qualification still requires the die observer deadline audit.
    Do not use this delta model as proof of the unlanded die's absolute ages.
    """
    if ksd is None:
        from tools.qwen_kv_die import kv_static_die as ksd
    if not ksd.HROOT_LAND:
        return dict(chain=0, fan=0, gather=0, embedding=0)
    if ksd.HROOT_S32:
        raise ValueError('HROOT safe32 is retired; no production calendar law')
    if ksd.HROOT_ESH_MOD != 'qkd_kv_es_fan_stack_bl' or ksd.HROOT_RLY_MOD != 'qkd_kv_stack_relays_l':
        raise ValueError('HROOT landing implementation has no executable calendar law')
    return dict(chain=1, fan=1, gather=1, embedding=1)


# ---- KV-CAL15 10-20: ONE registry of the per-tile cycle deltas the die schedule admits (route A GEN9 strict source) -----
# Every flag below changes a tile's edge count; the compiler takes each delta exactly once, here, and the compile records
# them (compile_all()['cal_deltas']).  DRIVE-KV 10-20: the structurally safe variant + its cycles, priced, instead of waivers.
#   hroot     OT_KV_HROOT_LAND=1 (qkd_kv_es_fan_stack_bl / qkd_kv_stack_relays_l): chain +1 (es head h -> o_pc: PC players
#             and the join beat calendar via es_cfg relay), fan +1 (group launch age: pr['groups']), gather +1 (observer
#             transport only), embedding return +1 (es_cfg return_relay).  Law = hroot_landing (Codex 740bde993).
#   emb_join  OT_KV_EMB_PJ=1 (qkd_embedding_static_join4_cal PIPE_JOIN=1, KV-EMB4 z3): every join word / fault +1 edge after
#             the beat slot; the beat calendar (target 13) is unchanged, the row fill completes +1 later (emb_fill below).
#   ctl_own   OT_KV_CTL_C32=1|2 (qkd_static_kv_ownership_calendar_mu_c32 PIPE 1 SAFE 1, KV-CTL10): the enter / leave
#             drain guards sample &group_drained 2 edges earlier (guard at root - 2 on a one-edge-older AND) -> the
#             leave root (target 3 word 1) moves +2 so the drain / quiet margin of the BA tile is preserved; enter stays 3
#             (its guard samples the idle pre-token state; enter checks only the host -> native transition).
#             u_boot SRQ 2: setup_ready +2 boot edges -- HOST boot boundary (elastic, off-die), no static consumer.
#   ahub      OT_KV_AHUB_PAD=1 (+ OT_KV_AHUB_OFS): the hub view's fixed AP_OFS / FR_OFS; the generator pads ap_<st> /
#             ks_ahfr up to them (kv_bundle_eq) and kv_static_params AHUB_OFS_BOUND proves table == binding == kit:
#             0 compiler edges (the attention calendar already runs at the hub's offsets; fr_ofs read from the binding).
#   seam      OT_KV_SEAM_PIN=1: the K seam is padded to the PAIR image (TXDP_K 22 by contract, KV-D2D3): 0 compiler edges;
#             link_image_check stays fail-closed on the bound image.
CTL_OWN_GUARD_LEAD = 2
CAL_DELTAS_ZERO = dict(hroot=dict(chain=0, fan=0, gather=0, embedding=0), emb_join=0, ctl_own_leave=0, ctl_boot_setup_ready=0,
                       ahub=dict(compiler_edges=0, pad=False), seam=dict(compiler_edges=0, pin=False))


def final_reset_calendar():
    path = os.environ.get('OT_KV_FINAL_RESET_CALENDAR')
    if not path: return None
    data = json.loads(Path(path).read_text())
    if data.get('schema') != 'opentallas.kv_final_reset_stations.v1':
        raise ValueError('unknown final reset station calendar')
    return dict(data, ledger_path=path)


def cal_deltas(ksd=None):
    env = os.environ.get
    ctl = env('OT_KV_CTL_C32', '0')
    if ctl not in ('0', '1', '2'):
        raise ValueError(f'OT_KV_CTL_C32={ctl!r}: no calendar law')
    hl = hroot_landing(ksd)
    deltas = dict(hroot=hl, emb_join=1 if env('OT_KV_EMB_PJ', '0') == '1' else 0,
                ctl_own_leave=CTL_OWN_GUARD_LEAD if ctl != '0' else 0, ctl_boot_setup_ready=2 if ctl != '0' else 0,
                ahub=dict(compiler_edges=0, pad=env('OT_KV_AHUB_PAD', '0') == '1', proof='kv_static_params AHUB_OFS_BOUND'),
                seam=dict(compiler_edges=0, pin=env('OT_KV_SEAM_PIN', '0') == '1', proof='link_image_check (TXDP_K 22)'))
    reset = final_reset_calendar()
    if reset is not None: deltas['final_reset_stations'] = reset
    return deltas


# ---- KV-CAL15: embedding row fill deadline (RESULT -> the row_tx header slot) -----------------------------------------
# row_tx needs the row resident (64 words + scale) at the kind-8 header slot (d2d_link_calendar emb_header_send); the
# fill starts when the token-run RESULT start (svc[24]) is at the fan root.  Edge accounting (segment-1 edges):
#   r        = hbm_embedding_budget.result_at_kv_host + svc relays d2d -> kvs_ctl (fan root emb_start)
#   join     = svc relays d2d -> kvs_emb (join4_cal start); the calendar's beat slots count from the JOIN start, so a
#              root/join start skew (ctl - emb relays) is one more return edge on every stack
#   last     = r + emb_calendar(down, return)['last_word'] + PIPE_JOIN
#   deadline = header slot + emb_tx_slot relays d2d -> kvs_emb (row_tx sees the slot that much later); last + 1 <= it
# down[s] = die relays kvs_ctl.o_hroot_s -> hroot.i_ctl + hroot.o_pc -> kvpc_s_31 (+ hroot chain); return[s] = kvpc_s_31
# -> hroot.i_r + hroot.o_emb -> kvs_emb (+ hroot embedding).  The die relays come from the plan's relay_stages.json.
EMB_FILL_BUSES = dict(down=(('kvs_ctl', 'o_hroot_{s}', 'kvs_hroot_{s}', 'i_ctl'), ('kvs_hroot_{s}', 'o_pc', 'kvpc_{s}_31', 'i_next')),
                      ret=(('kvpc_{s}_31', 'o_next', 'kvs_hroot_{s}', 'i_r'), ('kvs_hroot_{s}', 'o_emb', 'kvs_emb', 'i_hroot_{s}')),
                      svc_root=('d2d_kv', 'svc', 'kvs_ctl', 'd2d__svc'), svc_join=('d2d_kv', 'svc', 'kvs_emb', 'd2d__svc'),
                      slot=('d2d_kv', 'emb_tx_slot', 'kvs_emb', 'd2d__emb_tx_slot'))


def die_emb_relays(relay_stages):
    """{down, ret, svc_root, svc_join, slot} from a kv_die relay_stages.json (buses by src/dst inst.port)"""
    doc = json.loads(Path(relay_stages).read_text()) if not isinstance(relay_stages, dict) else relay_stages
    B = {(b['src']['inst'], b['src']['port'], b['dst']['inst'], b['dst']['port']): b['stages'] for b in doc['buses']}

    def g(k, s=None):
        k = tuple(x.format(s=s) for x in k)
        if k not in B:
            raise ValueError(f'kv_static_programme emb_fill: no die bus {".".join(k[:2])} -> {".".join(k[2:])}')
        return B[k]
    import kvjc3_pc_chain as C3
    return dict(down=[sum(g(k, s) for k in EMB_FILL_BUSES['down']) for s in C3.STACKS],
                ret=[sum(g(k, s) for k in EMB_FILL_BUSES['ret']) for s in C3.STACKS],
                svc_root=g(EMB_FILL_BUSES['svc_root']), svc_join=g(EMB_FILL_BUSES['svc_join']), slot=g(EMB_FILL_BUSES['slot']),
                source=str(relay_stages) if not isinstance(relay_stages, dict) else 'dict')


# ---- KV-EMBWIN16 10-20: writer lanes on the die relays (shared es chain: writer KV words ride kvs_ctl.o_hroot -> hroot h ->
# o_pc -> PC chain, the same DOWN path as the embedding issue words, so HROOT_LAND chain +1 delays them too) ---------------
# On the GEN9 static die the native writer sits in kvs_ctl: its KVN words arrive over d2d_kv.{skw,srx,kvn_word_*} ->
# kvs_ctl relays (die ages d2d_to_writer is the old colocated plan's 0).  writer_die() composes (a) that KVN relay depth
# (OT_KV_WRITER_DIE=1: compile the writer start on it, pr['kvn']) and (b) every PC's writer word arrival age at its face /
# controller es (kvjc3_pc_chain.writer_ages on the die down relays + the HROOT_LAND chain delta) for the consumers
# (controller write readiness, K.STA.RETIRE); the record is written with every compile that names the die relays.
WRITER_KVN_BUSES = (('d2d_kv', 'skw', 'kvs_ctl', 'd2d__skw'), ('d2d_kv', 'srx', 'kvs_ctl', 'd2d__srx'),
                    ('d2d_kv', 'kvn_word_generation', 'kvs_ctl', 'd2d__kvn_word_generation'),
                    ('d2d_kv', 'kvn_word_identity', 'kvs_ctl', 'd2d__kvn_word_identity'))


def writer_die(relay_stages, deltas):
    doc = json.loads(Path(relay_stages).read_text()) if not isinstance(relay_stages, dict) else relay_stages
    B = {(b['src']['inst'], b['src']['port'], b['dst']['inst'], b['dst']['port']): b['stages'] for b in doc['buses']}
    kv = {'.'.join(k[:2]) + '->' + '.'.join(k[2:]): B[k] for k in WRITER_KVN_BUSES if k in B}
    if not kv:
        raise ValueError('writer_die: no d2d_kv -> kvs_ctl KVN bus in the die relays')
    if len(set(kv.values())) != 1:
        raise ValueError(f'writer_die: KVN buses to the writer differ in relay depth {kv}: pad them to one age')
    import kvjc3_pc_chain as C3
    d = die_emb_relays(doc)
    down = [x + deltas['hroot']['chain'] for x in d['down']]
    wa = C3.writer_ages(down)
    per = {st: dict(down=down[i], pc31_wes=wa[f'{st}_31']['wes_lane01'], pc0_ctrl_es=wa[f'{st}_0']['ctrl_es_lane23'])
           for i, st in enumerate(C3.STACKS)}
    return dict(kvn_relays=next(iter(kv.values())), kvn_buses=kv, land_chain=deltas['hroot']['chain'], per_stack=per,
                worst_ctrl_es_age=max(v['pc0_ctrl_es'] for v in per.values()),
                rule='writer word at PC p of stack s reaches its controller es kvjc3.writer_ages(down + LAND chain) edges after '
                     'it leaves the writer; KVN words reach the writer kvn_relays edges after the d2d end')


def emb_fill(layout, deltas, die=None, ctrl_lat=ES_CFG_CTRL_LAT):
    """the fill deadline on the link calendar layout (+ die relays when given; None = the zero-relay model)"""
    import kvjc3_pc_chain as C3
    d = die or dict(down=[0] * 4, ret=[0] * 4, svc_root=0, svc_join=0, slot=0, source='zero-relay model')
    hl = deltas['hroot']
    skew = d['svc_root'] - d['svc_join']
    if skew < 0:
        raise ValueError(f'emb_fill: join start {-skew} edges after the fan root start: beat calendar has no law for it')
    down = [x + hl['chain'] for x in d['down']]
    ret = [x + hl['embedding'] + skew for x in d['ret']]
    cal = C3.emb_calendar(ctrl_lat, down, return_relay=ret)
    eb = layout['hbm_embedding_budget']
    r = eb['result_at_kv_host'] + d['svc_root']
    last = r + cal['last_word'] + deltas['emb_join']
    hdr = layout['emb_header_send']
    deadline = hdr + d['slot']
    margin = deadline - (last + 1)
    return dict(result_at_kv_host=eb['result_at_kv_host'], root_start=r, down=down, ret=ret, root_join_skew=skew,
                last_word_rel=cal['last_word'], pipe_join=deltas['emb_join'], last_word=last, header_slot=hdr,
                row_tx_slot=deadline, margin=margin, embed_window=layout['embed']['cycles'],
                embed_window_needed=layout['embed']['cycles'] + max(0, -margin), token_period=layout.get('token_period'),
                token_period_needed=(layout.get('token_period') or 0) + max(0, -margin), die_relays=d.get('source'),
                status='PASS' if margin >= 0 else 'FAIL',
                rule='last join word r + emb_calendar(down, return).last_word + PIPE_JOIN, + 1 (row_tx write) <= header slot '
                     '+ emb_tx_slot relays; r = RESULT at the KV d2d + svc relays to the fan root')


def profile(kind, ages=None):
    if kind == 'component':
        return dict(kind='component', start_relays=0, att=0, rx=0, writer=0, kvn=0, groups=0, crossing=False,
                    qk_age=KC.SOURCED['qk_consume_age'], qk_row_latency=KC.SOURCED['qk_row_latency'],
                    v_rl=19, d_rl=0, d_qk=0, phase=None, ld=1, rc=3, landing_uncertainty=0)
    L = ages['link']
    fl = _face_land()
    from tools.qwen_kv_die import kv_static_die as KSD
    ofs = KSD.ahub_ofs_bound()
    hl = hroot_landing(KSD)
    return dict(kind='die', fr_ofs=ofs['FR_OFS'] if ofs else None, start_relays=L['programme_start']['edges'], att=L['programme_to_attention']['edges'] + fl['i_ctl'],
                face_land=fl, hroot_landing=hl, cal_deltas=cal_deltas(KSD),
                rx=L['d2d_to_attention_rx']['edges'], writer=L['programme_to_writer']['edges'], kvn=L['d2d_to_writer']['edges'],
                groups=L['programme_to_groups']['edges'] + hl['fan'], crossing=True,
                qk_age=ages['qk']['QK_ISSUE_AGE'], qk_row_latency=ages['qk']['row_latency_for_calendar'],
                v_rl=ages['pv']['RL'], d_rl=ages['pv']['RL'] - 19, d_qk=QKH32.calendar_d_qk(ages['qk']['QK_ISSUE_AGE'], AC.QK_CONSUME),
                phase=ages['phase_launch'], link_ages=L, ld=L['return_to_landing_ld']['LD'], rc=3, landing_uncertainty=1,
                rd_shape=dict(K=RD_SHAPE_K, V=RD_SHAPE_V), astk_law=astk_law() if ASTK_EXPAND else None,
                # KV-BOOTAGE 10-19: the result face's boot F_DLY (kv_bootage image; 1 = the closed face law, unchanged)
                f_dly=((ages.get('boot_ages') or {}).get('attn') or {}).get('F_DLY') or 1,
                pv_floor=PV_FLOOR)


def kv_params(pr):
    return dict(KC.SOURCED, ring_cdc_core_edges=pr['rc'], layer_period_core=6798, write_ready_core=0, front_nblk=10,
                ring_depth=64, refresh=KC.refresh_from_table(), qk_consume_age=pr['qk_age'], qk_row_latency=pr['qk_row_latency'])


# ---- attention calendar (the N1 law) ----------------------------------------------------------------------------------
# HKV-DIE3 10-19 (HKV-AHUB4 findings, coordinator (b)): ONE schedule for the hub export and the pvfin join.
#  * the link's RESULT slot is fixed, so R stays stretched to it (R = service_end - 49 - PV_START); qkd_pv_fin_s (QXF-FACE
#    F3, b6d08acc2) joins on max(P0, P1, R) through its 32-beat sum buffer, so a stretched R is legal there (the
#    'R <= LASTP + ADD_LAT + 1' refusal HKV-AHUB4 hit is the pre-F3 pvfin of its bench base, not the die's RTL);
#  * qkd_ahub_static_dw exports fr at io age PV_START + R + FR_OFS and faults unless that is after its rz_publish:
#    PV_START + R + FR_OFS >= HUB_PUB + HUB_EXPORT_AFTER_PUB (3).  The minimal R / PV_START therefore use the margin
#    max(RZ_MARGIN, 3 - FR_OFS) with the BOUND FR_OFS (pr['fr_ofs']; component profile / unbound: RZ_MARGIN 2);
#  * qkd_pv_fin_s refuses |P0 - P1| > SKEW (die binding SKEW 1).  P0 - P1 is set by the PAIR hardware (w16_nq: pair 1
#    has 0 / 16 / 32 fewer issue cycles when T <= 128 or T mod 256 in 1..128) -- no compiled field moves it; attention_checks
#    reports those contexts and kv_static_params FAILS (ATTN_CALENDAR PVFIN_PAIR_SKEW) until the RTL absorbs the skew.
HUB_EXPORT_AFTER_PUB = 3
PVFIN_SKEW = 1            # kv_static_die bindings qkd_pvfin SKEW


def rz_margin(pr):
    fr = (pr or {}).get('fr_ofs')
    return AC.RZ_MARGIN if fr is None else max(AC.RZ_MARGIN, HUB_EXPORT_AFTER_PUB - fr)


def attention_calendar(T, pr, service_end=None):
    """attn_calendar.calendar_w16(T, head_g3s2=True) with the die's QK age shift (LMAX moves with the last consume)
    and V word latency shift (pair outputs move with RL); service_end stretches R so the last result beat lands on
    the link's fixed RESULT slot (static: a context-dependent service end would miss the compiled TX slot)."""
    lmax = AC.lmax_min(T) + pr['d_qk']
    c = AC.calendar(T, lmax=lmax, pv='w1')
    for f in ('LMAX', 'EXP', 'Z', 'HUB_LMAX', 'HUB_Z', 'HUB_RECIP', 'HUB_PUB'):
        c[f] += AC.HEAD_G3S2_SHIFT
    law = pr.get('astk_law')
    d_gap = d_erl = 0
    if law:
        for f, k in (('LMAX', 'dLMAX'), ('HUB_LMAX', 'dLMAX'), ('EXP', 'dEXP'), ('Z', 'dZ'), ('HUB_Z', 'dZ'),
                     ('HUB_RECIP', 'dZ'), ('HUB_PUB', 'dZ')):
            c[f] += law[k]
        d_gap, d_erl = astk_pv_gap_shift(T, law), law['dERL']
    po = [AC.w16_pair_out(T, 0) + pr['d_rl'] + d_erl, AC.w16_pair_out(T, 1) + pr['d_rl'] + d_erl]
    if pr.get('pv_floor'):
        # KV-FLOOR1: ctl_tbf ends FEED / publishes out_age on pair 0's issue count for both pairs (pv_floor_bench: P1 = P0
        # at every context, bit-exact).  Pair 0 has the most rows, so P0 = max(P0, P1): the join age is unchanged.
        if po[1] > po[0]:
            raise ValueError(f'T={T}: pair END FLOOR needs P0 >= P1 (P0 {po[0]}, P1 {po[1]})')
        po[1] = po[0]
    mg = rz_margin(pr)
    pv = max(c['EXP'] + AC.pv_after_exp_w16(T) + d_gap, c['HUB_PUB'] + mg - max(po))
    r = max(max(po), c['HUB_PUB'] + mg - pv)
    if service_end is not None:
        # service_cycles = PV_START + max(P, R) + 16 + 32 + F_DLY (KV-BOOTAGE: the face's RESULT_AGE PV_START + R + 16 +
        # F_DLY stays on the link slot service_end - 32; F_DLY 1 = the closed law service_end - 49 - PV_START)
        r_link = service_end - 48 - pr.get('f_dly', 1) - pv
        if r_link < r:
            raise ValueError(f'T={T}: attention service needs {pv + r + 49} edges, the link slot gives {service_end}')
        r = r_link
    c.update(P0=po[0], P1=po[1], PV_START=pv, R=r)
    AC.check(c)
    return c


def service_end_of(pr, workdir=None):
    """the attention service end the link's fixed RESULT slot leaves (= compile_all's service_end for this profile)"""
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        cal = link_calendar(td)
    seg0 = [m for m in cal['messages'] if m.get('seg', 0) == 0]
    cmd = [m for m in seg0 if m['src'] == 'C' and m['rx_port'] == 0 and m['kind'] == 1]
    res = sorted((m for m in seg0 if m['src'] == 'K' and m['tx_port'] == 0 and m['kind'] == 3), key=lambda m: m['beat'])
    run_ev = cmd[0]['rx_out'] + LR.D2D_OUT + pr['rx'] - LR.RX_CMD
    tx_first = res[0]['cyc'] + LR.D2D_OUT - run_ev
    return tx_first - LR.RX_CMD - 2 + 31 - attn_r16()['tx_shift']   # KV-BIND4: r16 TX_SHIFT keeps SERVICE_END 1777


def attention_checks(pr, service_end, fr_ofs=None, pvfin_skew=PVFIN_SKEW, pair_delta=0, Ts=range(1, 8193)):
    """HKV-DIE3: every context's emitted calendar against the BOUND hub / pvfin RTL refusals (fail-closed, no RTL
    threshold touched).  pair_delta = D(pvw_0 -> pvfin.p0) - D(pvw_1 -> pvfin.p1) on the die table (0 when equalised).
    -> dict(fails=[{id, contexts, examples}], ...)"""
    pr = dict(pr, fr_ofs=fr_ofs)
    bad = {}

    def add(k, T, **kw):
        b = bad.setdefault(k, dict(id=k, contexts=0, examples=[]))
        b['contexts'] += 1
        if len(b['examples']) < 8:
            b['examples'].append(dict(T=T, **kw))
    worst = dict(hub_export_margin=None, pvfin_skew=0)
    for T in Ts:
        try:
            c = attention_calendar(T, pr, service_end)
        except ValueError as e:
            add('CALENDAR_UNMEETABLE', T, what=str(e)[:200])
            continue
        hm = c['PV_START'] + c['R'] + (fr_ofs or 0) - (c['HUB_PUB'] + HUB_EXPORT_AFTER_PUB)
        worst['hub_export_margin'] = hm if worst['hub_export_margin'] is None else min(worst['hub_export_margin'], hm)
        if fr_ofs is not None and hm < 0:
            add('HUB_FR_EXPORT', T, PV_START=c['PV_START'], R=c['R'], FR_OFS=fr_ofs, HUB_PUB=c['HUB_PUB'], short=-hm)
        p0, p1 = c['P0'] + pair_delta, c['P1']
        sk = abs(p0 - p1)
        worst['pvfin_skew'] = max(worst['pvfin_skew'], sk)
        if sk > pvfin_skew:
            add('PVFIN_PAIR_SKEW', T, P0=p0, P1=p1, skew=sk, limit=pvfin_skew)
        if min(p0, p1, c['R']) < 1 or max(p0, p1, c['R']) + 64 + 13 > 0xffff:
            add('PVFIN_CAL_RANGE', T, P0=p0, P1=p1, R=c['R'])
    return dict(schema='opentallas.qwen_kv.attention_checks.v1', service_end=service_end, fr_ofs=fr_ofs,
                pvfin_skew_limit=pvfin_skew, pair_delta=pair_delta, contexts=len(list(Ts)), worst=worst,
                fails=sorted(bad.values(), key=lambda b: b['id']),
                rule='hub: PV_START + R + FR_OFS >= HUB_PUB + 3 (qkd_ahub_static_dw emit after rz_publish); pvfin: '
                     '|P0 - P1| <= SKEW, P/R >= 1, max + 77 <= 0xffff (qkd_pv_fin_s cal_bad); R stretched to the link slot')


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


EARLY_MAX = 16                  # phase alignment: the most core edges a stage's launches may move earlier


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
                    L.setdefault('k_cases', []).append((put, [c for _, c, _ in st]))
                else:
                    need_v = req if need_v is None else max(need_v, req)
                    L.setdefault('v_cases', []).append((T, put, [c for _, c, _ in st]))
    v_slack, k_peak = None, [0] * (EARLY_MAX + 1)
    for (s, g), L in law.items():                            # V ring room at the one lead every T uses
        for T, put, cons in L.get('v_cases', []):
            for i in range(P['ring_depth'], len(put)):
                sl = KC.hbm_to_core(put[i], P) - (need_v + cons[i - P['ring_depth']] + 1)
                v_slack = sl if v_slack is None else min(v_slack, sl)
                if sl < 0:
                    bad.append(dict(T=T, group=f'{s}{g}', kind='v', sector=i, why='put before its ring slot is consumed'))
                    break
        for put, cons in L.get('k_cases', []):               # K ring occupancy if K is launched e edges earlier
            vis = [KC.hbm_to_core(x, P) + P['ring_cdc_core_edges'] for x in put]
            for e in range(EARLY_MAX + 1):
                occ = peak = 0
                for _, d in sorted([(v, 1) for v in vis] + [(need_k + e + c + 1, -1) for c in cons]):
                    occ += d
                    peak = max(peak, occ)
                k_peak[e] = max(k_peak[e], peak)
        L.pop('v_cases', None)
        L.pop('k_cases', None)
    margins = dict(v_ring_slack_core=v_slack, k_ring_peak_by_early_edges=k_peak, ring_depth=P['ring_depth'])
    return need_k, need_v, bad, len(Ts), margins


LAUNCH_ROOTS = ('ctrl_go', 'kgo', 'vgo')
CAL_GEN_LAT = 10                # qkd_attn_cal_gen (KVJ-B): go -> done edges (10-edge pipeline, II 1)
STAGE_START_EDGE = 1            # qkd_static_kv_layer_programme: stage_start registered one edge after the stage load
TOKEN_START_PHASE_U = 0         # 625 x (token run start core edge) mod 768: the run start sits on the reset-release beat


def token_phases(period, phi0=TOKEN_START_PHASE_U):
    """the HBM-beat phases (625 u x start mod 768) every token run start of a run of tokens takes: one phase when the
    period is a multiple of 768 core edges, else up to 768 (token n at phi0 + 625 n P)"""
    return sorted({(phi0 + CORE_U * n * period) % HBM_U for n in range(HBM_U)})


def launch_gap(cyc, pr, phi):
    """qkd_static_kv_phase_launch next_gap (u) at the toggle edge of a root emitted at token cycle cyc: programme
    internal start +1, lprg -> group tree, go_q capture at the group tile, toggle one edge later (phase_launch.launch)"""
    c = cyc + 1 + pr['groups'] + 1
    return (pr['phase']['PH0'] - phi - CORE_U * (c + 1)) % HBM_U or HBM_U


def launch_legal(cyc, pr, phases):
    lo, hi = pr['phase']['SAFE_LOW_U'], pr['phase']['SAFE_HIGH_U']
    return all(lo <= launch_gap(cyc, pr, ph) <= hi for ph in phases)


def phase_align(pr, rel, frame, period, law, lead_k, lead_v):
    """Choose, once per compile, a V advance a (vgo and the controller V run move a core edges earlier than kgo + d_v)
    and per stage s an advance d_s (ctrl_go / kgo / vgo of stage s all move d_s edges earlier) so that all 108 launches
    sit inside the phase window at every token phase; minimise a + max d_s.  Moving a launch earlier only lengthens a
    fetch lead: the V ring room (law margins) bounds a + d_s, the K ring occupancy bounds d_s.  A period that is not a
    multiple of 768 core edges gives each launch every phase, so no choice holds and the compile refuses."""
    phases = token_phases(period)
    m = law['margins']
    v_room = m['v_ring_slack_core'] + (lead_v - law['lead_v'])          # V may move this many core edges earlier
    k_base = lead_k - law['lead_k']
    # K: the law-wide K lead already over-fills the 64-slot return ring at short contexts (peak at d = 0 reported
    # below, OPEN to the K ring owner); the alignment may only add the few sectors its advance lands early
    k_ok = lambda d: d + k_base <= EARLY_MAX
    best = None
    for a in range(EARLY_MAX + 1):
        adv = []
        for s in range(36):
            kc, vc = frame[s] + rel['kgo'], frame[s] + rel['vgo'] - a
            d = next((d for d in range(EARLY_MAX + 1) if launch_legal(kc - d, pr, phases) and launch_legal(vc - d, pr, phases)), None)
            if d is None:
                break
            adv.append(d)
        if len(adv) != 36:
            continue
        dm = max(adv)
        if a + dm + 1 > v_room or not k_ok(dm):          # +1: the HBM edge of an earlier launch may round one edge earlier
            continue
        if best is None or (a + dm, a) < (best['vgo_advance'] + max(best['stage_advance']), best['vgo_advance']):
            best = dict(vgo_advance=a, stage_advance=adv)
    if best is None:
        raise ValueError(f'no launch alignment within {EARLY_MAX} edges holds at token phases {phases[:4]}.. '
                         f'(token period {period}, mod 768 = {period % HBM_U}): pad the period to a multiple of 768')
    dm = max(best['stage_advance'])
    best.update(token_phases=phases, max_stage_advance=dm, v_ring_room_core=v_room, v_early_used=best['vgo_advance'] + dm + 1,
                k_ring_peak=m['k_ring_peak_by_early_edges'][dm + k_base], k_ring_peak_unaligned=m['k_ring_peak_by_early_edges'][k_base],
                ring_depth=m['ring_depth'],
                k_ring_open='K return-ring peak exceeds ring_depth with the one law-wide K lead (all contexts), before any '
                            'alignment: pre-existing, K ring / lead owner',
                law='ctrl_go = kgo = layer root - d_s; vgo = kgo + d_v - a; e_v follows d_v - a (the controller V run)')
    return best


def phase_legality(pr, launches, period):
    """compiler legality check: every launch inside [SAFE_LOW, SAFE_HIGH] at every token phase the period gives, and the
    held-metadata / per-lane hold of qkd_static_kv_phase_launch (META_HOLD_CORE) between consecutive launches, across
    the token boundary too"""
    ph = pr['phase']
    phases = token_phases(period)
    bad, table = [], []
    for l in launches:
        gaps = sorted({launch_gap(l['token_cycle'], pr, p) for p in phases})
        out = [g for g in gaps if not ph['SAFE_LOW_U'] <= g <= ph['SAFE_HIGH_U']]
        table.append(dict(l, gap_u=gaps[0] if len(gaps) == 1 else [gaps[0], gaps[-1]]))
        if out:
            bad.append(dict(stage=l['stage'], root=l['root'], gaps_outside=len(out), phases=len(phases)))
    hold = []
    seq = sorted(launches, key=lambda l: l['token_cycle'])
    seq2 = seq + [dict(l, token_cycle=l['token_cycle'] + period) for l in seq[:3]]
    for x, y in zip(seq2, seq2[1:]):
        dt = y['token_cycle'] - x['token_cycle']
        if dt and dt <= ph['META_HOLD_CORE'] and (x['stage'] != y['stage'] or x['root'] == y['root']):
            hold.append(dict(a=f'S{x["stage"]}.{x["root"]}', b=f'S{y["stage"]}.{y["root"]}', edges=dt))
    return dict(assumption=f'first token run start at HBM-beat phase {TOKEN_START_PHASE_U} u (q = PH0 at the reset-release '
                           'beat); later runs at start + n x token period',
                token_period_core=period, token_period_mod_768=period % HBM_U, token_phases=len(phases),
                launches=len(launches), checks=len(launches) * len(phases), outside_window=bad, hold_conflicts=hold,
                window_u=[ph['SAFE_LOW_U'], ph['SAFE_HIGH_U']], launch_table=table)


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


# ---- KV-PROG17 10-20: the retirement contract of the r16 STATUS (K.STA.RETIRE), built from the DIE health plane ----------
# OT_KV_RETIRE_SUCCESSOR=<run>/health_successor.json (kv_health_plane install: every source's measured plane edges on the
# die netlist), OT_KV_RETIRE_RESET (default the committed GEN7 reset candidate), OT_KV_RETIRE_RESET_DEPTH (default the
# die's rst_regional.json max_total_depth beside the successor: depth for sources the GEN7 candidate does not list).
RETIRE_RESET_DEFAULT = 'results/arch/kv_fault_reset_1019/gen7_evidence.tar.gz:gen7/reset_branch_candidate.json'
RETIRE_HOLD_BOUND = 273      # qkd_rst_region_pr_h273b HOLD (kvsys_prep OT_KV_RST_HOLD=273)


def die_retirement_contract(rx_cmd, tx_first, tx_end, service_end, token_period):
    import kv_retirement_contract as RC
    succ = Path(os.environ['OT_KV_RETIRE_SUCCESSOR'])
    rst = os.environ.get('OT_KV_RETIRE_RESET', str(ROOT / RETIRE_RESET_DEFAULT))
    depth = os.environ.get('OT_KV_RETIRE_RESET_DEPTH')
    if depth is None and (succ.parent / 'rst_regional.json').is_file():
        depth = json.loads((succ.parent / 'rst_regional.json').read_text())['max_total_depth']
    prog = dict(compiled_rx_cmd=rx_cmd, compiled_tx_first=tx_first, compiled_end=tx_end, service_end=service_end,
                token_period=token_period)
    c = RC.build(succ, rst, prog, 6 + 5, default_depth=None if depth is None else int(depth))   # link = --txl 6 --phy 5
    need = c['reset']['required_sink_release_depth']
    reset = final_reset_calendar()
    if reset is not None:
        # Budget the generated station delay against THIS die plane's whole-plane requirement (K.RST 10-21: never a
        # constant from an older plane -- the 325 of PROG17/d22hl2 made every opt-in run read 414 > HOLD273).
        need = need + int(reset['max_added_reset_edges'])
        c['reset'].update(required_sink_release_depth=need,
                          hold_counter_bits=max(8,math.ceil(math.log2(need))),
                          final_reset_stations=reset)
        for source in c['sources']: source['sink_release_age'] = need
    c['reset'].update(bound_hold=RETIRE_HOLD_BOUND, fits_bound_hold=need <= RETIRE_HOLD_BOUND,
                      default_depth=None if depth is None else int(depth))
    return c


# ---- the compile -------------------------------------------------------------------------------------------------------
def compile_all(pr, epoch=0x0b0b, program_words=None, workdir=None, die_cfg_words=None, retirement_contract=None, status_delay=None):
    r16 = attn_r16()
    if status_delay is None:     # KV-BIND4: the bound r16 tile's STATUS_DELAY (213) is a die fact, not an option
        status_delay = r16['status_delay']
    elif r16['on'] and status_delay != r16['status_delay']:
        raise ValueError(f"r16 attention tile binds STATUS_DELAY {r16['status_delay']}, compile asked for {status_delay}")
    # die_cfg_words: the pre-boot target-10 image (kv_static_kvjf_join.die_cfg_image from a die plan's ECTL cfg + reset
    # delays); without it the bundle carries targets 0..9, 11..13 and the die plan supplies target 10
    sfi = _sfi()
    prog = program_words or sfi.bench_program()
    if len(prog) != sfi.PW + sfi.DW:
        raise ValueError('HOST programme image must be PW1024 + DW8 words')
    digest = sfi.image_digest(prog)
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        cal = link_calendar(td, status_delay)
        link_words = link_cfg_words(Path(td) / 'cal')
    link_check = link_image_check(link_words, cal)        # KV-LINKCFG-MU: target 11 == the bound image (fail closed)
    hl = pr.get('hroot_landing', dict(chain=0, fan=0, gather=0, embedding=0))
    es_relay, es_return = [hl['chain']] * 4, [hl['embedding']] * 4
    _die_rs = os.environ.get('OT_KV_EMB_FILL_RELAYS')     # KV-CAL15: compile targets 12/13 on the plan's real relays
    if _die_rs and pr['kind'] == 'die':                   # (down / return per stack + root-join skew + LAND, emb_fill law)
        _f = emb_fill(cal['program'], pr.get('cal_deltas') or CAL_DELTAS_ZERO, die_emb_relays(_die_rs))
        es_relay, es_return = _f['down'], _f['ret']
    es_pc, es_beat = es_cfg_words(relay=es_relay, return_relay=es_return)
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
    start_qk = run_ev + LR.RX_CMD + LR.Q_TO_START + r16['rx_edges']   # KV-BIND4: r16 registered RX validation +1
    tx_first = res[0]['cyc'] + LR.D2D_OUT - run_ev              # att_tx_slot of RESULT beat 0 at the programme
    tx_end = tx_first + 34 + status_delay
    service_end = tx_first - LR.RX_CMD - 2 + 31 - r16['tx_shift']   # r16: TX_SHIFT 1 -> tx_first 1751, SERVICE_END 1777
    if res[-1]['cyc'] - res[0]['cyc'] != 31 or st[0]['cyc'] != res[0]['cyc'] + 33 + status_delay:   # static_ctl: STATUS at tx_first + 33
        raise ValueError('RESULT burst / STATUS not on consecutive link slots')

    retirement = None
    if status_delay:
        if retirement_contract is None and os.environ.get('OT_KV_RETIRE_SUCCESSOR'):
            retirement_contract = die_retirement_contract(LR.RX_CMD, tx_first, tx_end, service_end,
                                                          cal['program']['token_period'])
        if retirement_contract is None:
            raise ValueError('delayed STATUS requires a complete retirement contract (OT_KV_RETIRE_SUCCESSOR=<run>/'
                             'health_successor.json builds it from the die health plane)')
        from kv_retirement import prove
        retirement = prove(retirement_contract, tx_first, tx_end - 1)
        retirement['reset'] = retirement_contract.get('reset')
        retirement['inputs'] = {k: v for k, v in (retirement_contract.get('inputs') or {}).items() if k != 'programme'}
        if not retirement['qualified']:
            if os.environ.get('OT_KV_RETIRE_LOGICAL', '0') != '1':
                raise ValueError('delayed production STATUS requires qualified deadline/path/reset evidence '
                                 '(OT_KV_RETIRE_LOGICAL=1 compiles on the LOGICAL_ONLY contract, recorded NOT a release)')
            retirement['release'] = ('NOT_RELEASE: LOGICAL_ONLY retirement (no measured native path / reset / cross-root '
                                     'skew receipts); the frame and slots are final, the qualification is owed')

    # ---- K / V leads and the layer roots ----
    plans, P, lead_k, lead_v = pc_plans(pr)
    law = None
    if pr['kind'] == 'component':                           # the bench-fed image used the capacity screen's lead
        lead_k = KC.screen_36_capacity(T_MAX, P)['layer']['qk_start_after_prefetch_core']
    else:
        lk, lv, bad, nT, margins = law_check(pr, plans)
        if bad:
            raise ValueError(f'one calendar law per group does not hold for every context: {bad[:5]}')
        law = dict(contexts_checked=nT, lead_k_T8192=lead_k, lead_v_T8192=lead_v, lead_k=lk, lead_v=lv, margins=margins)
        lead_k, lead_v = max(lead_k, lk), max(lead_v, lv)
    att8192 = attention_calendar(T_MAX, pr)
    e_k = CMD_LEAD + 2
    if pr['kind'] == 'component':
        kgo_ev, d_v = start_qk - lead_k, KC._pv_start(T_MAX)    # layer_roots_from_link: kgo = start_qk - lead, vgo = kgo + PV
    else:
        kgo_ev = start_qk - lead_k - crossing_core(e_k + CAL_PIN_EDGES, pr) - 1 - pr['groups'] - 1
        d_v = att8192['PV_START'] + lead_k - lead_v - 2
    wdie = writer_die(_die_rs, pr.get('cal_deltas') or CAL_DELTAS_ZERO) if _die_rs and pr['kind'] == 'die' else None
    kvn_age = pr['kvn']
    if wdie and os.environ.get('OT_KV_WRITER_DIE', '0') == '1':   # KV-EMBWIN16: writer start on the die's KVN relays
        kvn_age = wdie['kvn_relays']
        wdie['writer_start_kvn_age'] = dict(ages_table=pr['kvn'], compiled=kvn_age)
    writer_ev = kvn[0]['rx_out'] + LR.D2D_OUT + kvn_age - LR.WRITER_T0 - pr['writer']
    rel = dict(ctrl_go=kgo_ev, kgo=kgo_ev, vgo=kgo_ev + d_v, attention_issue=run_ev - LR.ISSUE_TO_RUN - pr['att'],
               attention_run=run_ev - pr['att'], writer_start=writer_ev, link_start=LR.LINK_START,
               expected_quiet=st[0]['cyc'] + 1)
    lead = LR.START_LEAD - pr['start_relays']
    rel = {k: (v + lead if k != 'link_start' else v) for k, v in rel.items()}
    ends = [starts[1]] + [lay[s]['start'] - lay[s - 1]['start'] for s in range(2, 36)] + [lay[35]['cycles']]
    frame = [sum(ends[:s]) + (starts[0] if s == 0 else 0) for s in range(36)]   # token cycle of a stage's root 0
    align = None
    if pr['phase']:
        align = phase_align(pr, rel, frame, prog_cal['token_period'], law, lead_k, lead_v)
        d_v -= align['vgo_advance']
        rel['vgo'] -= align['vgo_advance']
    rows = []
    for s in range(1, 37):
        base = starts[0] if s == 1 else 0
        roots = {k: (v + base if k != 'link_start' else v) for k, v in rel.items()}
        if align:
            for k in LAUNCH_ROOTS:
                roots[k] -= align['stage_advance'][s - 1]
        roots['stage_end'] = ends[s - 1]
        rows.append(dict(stage=s, roots=roots))
    img = assemble_rows(rows, digest, epoch)
    if align:
        for e in img['events']:
            if e['kind'] in LAUNCH_ROOTS and e['token_cycle'] != frame[e['stage'] - 1] + rel[e['kind']] - align['stage_advance'][e['stage'] - 1]:
                raise ValueError(f'stage frame model differs from the layer image at S{e["stage"]}.{e["kind"]}')
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
    cd = pr.get('cal_deltas') or CAL_DELTAS_ZERO
    own_lead = cd['ctl_own_leave']                     # KV-CAL15: c32 drain guards 2 edges earlier -> leave +2
    own = [3, quiet36 + 1 + own_lead, img['token_core_cycles'], OWN_SEAL]
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

    # ---- phase legality of the launches at every token phase ----
    phase = None
    if pr['phase']:
        period = prog_cal['token_period']
        launches = [dict(stage=e['stage'], root=e['kind'], token_cycle=e['token_cycle']) for e in img['events']
                    if e['kind'] in LAUNCH_ROOTS]
        phase = phase_legality(pr, launches, period)
        phase['unpadded_counterfactual'] = {k: v for k, v in phase_legality(
            pr, launches, prog_cal.get('token_period_pad', {}).get('unpadded', period)).items() if k != 'launch_table'}
        phase['alignment'] = align
        if phase['outside_window'] or phase['hold_conflicts']:
            raise ValueError(f'phase launches illegal: {phase["outside_window"][:5]} {phase["hold_conflicts"][:5]}')

    # ---- attention control tile: N1 generator start and the service root's PV relay lead (KVJ-B note 10-17) ----
    # qkd_attn_cal_gen (KVJ-B 58f9ebdbb) is a CAL_GEN_LAT-edge pipeline started by the layer programme's stage-1
    # stage_start (registered: token cycle 1); the attention programme samples the calendar at its issue.  Both pulses
    # ride the same lprg -> attention control tile relays (pr['att']), so the margin is the root difference.
    issue1 = rows[0]['roots']['attention_issue']
    gen_go = STAGE_START_EDGE
    if issue1 - gen_go < CAL_GEN_LAT:
        raise ValueError(f'attention calendar generator go at {gen_go} is not {CAL_GEN_LAT} edges before the issue {issue1}')
    pv_starts = [attention_calendar(T, pr, service_end)['PV_START'] for T in sorted(set(LAW_TS) | {1, 2, 8192})]
    link_ages = (pr.get('link_ages') or {})
    pv_lead = link_ages.get('attention_to_pv', {}).get('edges')
    if pv_lead is not None and not 0 <= pv_lead < min(pv_starts):
        raise ValueError(f'service root PV_LEAD {pv_lead} must be below every PV_START (min {min(pv_starts)})')
    att_ctl = dict(cal_gen=dict(go='layer_programme stage_start of stage 1', go_token_cycle=gen_go, latency=CAL_GEN_LAT,
                                first_issue_token_cycle=issue1, margin=issue1 - gen_go - CAL_GEN_LAT,
                                relays='go and issue both cross lprg -> attention tile (%d edges): margin unchanged' % pr['att']),
                   service_root=dict(PV_LEAD=pv_lead, cls='MEASURED' if pv_lead is not None else 'PENDING',
                                     source='die ages link.attention_to_pv (attention control tile -> pvw_0/1 st relay edges)',
                                     pv_start_min=min(pv_starts), bound=f'0 <= PV_LEAD < {min(pv_starts)} (qkd_attn_service_root '
                                     'local_fault when PV_START_AGE <= PV_LEAD); start_pv leaves PV_LEAD edges early, the '
                                     'calendar words are unchanged',
                                     open=None if pv_lead is not None else 'the kvs13 plan has no service-root -> pvw st bus yet: '
                                     'price PV_LEAD from the static floorplan (KVJ-G) and recompile'))

    # ---- attention words ----
    att = dict(compiled_rx_cmd=LR.RX_CMD, compiled_tx_first=tx_first, compiled_end=tx_end, service_end=service_end,
               start_qk_run_age=start_qk - run_ev, law='calendar(T) = attention_calendar(T, profile, service_end): R stretched so '
               'PV_START + max(P0, P1, R) + 49 = service_end for every T in 1..8192',
               samples={}, control=att_ctl, retirement=retirement)
    for T in (1, 128, 1000, 2048, 4096, 6144, 8192):
        c = attention_calendar(T, pr, service_end)
        att['samples'][str(T)] = dict(cal=AC.hexcal(c), fields=c)
    if pr['kind'] == 'die':                                 # HKV-DIE3: every context vs the bound hub / pvfin refusals
        att['checks'] = attention_checks(pr, service_end, pr.get('fr_ofs'), Ts=sorted(set(range(1, 8193, 16)) | {8192}))

    # ---- boot bundle ----
    sfi_pw = sfi.PW
    images = [dict(target=1, program=layer_words, descriptors=[]), dict(target=2, program=writer_words, descriptors=[]),
              dict(target=3, program=own, descriptors=[]), dict(target=4, program=landing_words, descriptors=[]),
              dict(target=5, program=front_words, descriptors=[])] + \
             [dict(target=t_, program=ctrl_targets[t_], descriptors=[]) for t_ in (6, 7, 8, 9)] + \
             [dict(target=LINK_CFG_TARGET, program=link_words, descriptors=[]),        # KVJ-G2b: the HOST loader +
              dict(target=ES_CFG_TARGETS[0], program=es_pc, descriptors=[]),          # bundle encoder accept 10..13
              dict(target=ES_CFG_TARGETS[1], program=es_beat, descriptors=[])] + \
             ([dict(target=10, program=list(die_cfg_words), descriptors=[])] if die_cfg_words else []) + \
             [dict(target=0, program=prog[:sfi_pw], descriptors=prog[sfi_pw:])]
    mu = None
    if MU:              # MU-KV-BOOT 10-19 (OT_KV_MU=1): target 1 MU form + target 3 MU ownership roots (mu_calendar)
        mu = mu_images(layer_words, own, lead=own_lead, att_end=tx_end - LR.RX_CMD,
                       phase=None if not pr['phase'] else dict(PH0=pr['phase']['PH0'], lo=pr['phase']['SAFE_LOW_U'],
                                                               hi=pr['phase']['SAFE_HIGH_U'], groups=pr['groups']))
        layer_words, own = mu['layer'], mu['ownership']
        images[0] = dict(target=1, program=layer_words, descriptors=[])
        images[2] = dict(target=3, program=own, descriptors=[])
    bundle = PTF.encode_boot_bundle(epoch, images, mu=MU)
    if int(bundle['images'][-1]['digest'], 16) != digest:
        raise ValueError('HOST ISA image digest differs from the layer programme LP_DIGEST')
    die_rs = os.environ.get('OT_KV_EMB_FILL_RELAYS')      # KV-CAL15: the plan's relay_stages.json (case_kv/)
    fill = emb_fill(prog_cal, cd, die_emb_relays(die_rs) if die_rs else None)
    if os.environ.get('OT_KV_EMB_FILL_STRICT', '0') == '1' and fill['status'] != 'PASS':
        raise ValueError(f'embedding fill deadline: margin {fill["margin"]} (last join word {fill["last_word"]} + 1 > row_tx '
                         f'slot {fill["row_tx_slot"]}); embed window {fill["embed_window"]} -> {fill["embed_window_needed"]}')
    return dict(profile=pr, cal_deltas=cd, emb_fill=fill, writer_die=wdie, mu_frame=(mu or {}).get('frame'), link=dict(cmd_event=cmd_ev, run_event=run_ev, start_qk=start_qk, result_first_slot=res[0]['cyc'],
                                      token_cycles=prog_cal['token_cycles_through_L35'], token_period=prog_cal.get('token_period'),
                                      token_period_unpadded=prog_cal.get('token_period_pad', {}).get('unpadded')),
                leads=dict(k=lead_k, v=lead_v, kgo_event=kgo_ev, vgo_minus_kgo=d_v, e_k=e_k, e_v=e_v, start_lead=lead, law=law),
                layer=dict(rows=rows, words=layer_words, digest=digest, epoch=epoch, token_core_cycles=img['token_core_cycles'],
                           events=img['events']),
                writer=dict(slots=t, stop=stop, words=writer_words), ownership=dict(words=own, go='token start (assumed)'),
                groups=group, landing_words=landing_words, front_words=front_words, controller=ctrl, controller_targets=ctrl_targets,
                attention=att, phase=phase, images=images, bundle=bundle,
                # dispatcher target 11 (LINKCFG=1, order 1..9, 11, 0); in the HOST class-8 bundle (KVJ-G2b: the HOST
                # loader / program_target_frames accept targets 0..13; target 10 = pass 1 from the die plan)
                link_cfg=dict(target=LINK_CFG_TARGET, program=link_words, check=link_check),
                # dispatcher targets 12 / 13 (ESCFG=1, order 1..9, 11, 12, 13, 0): the KVJ-C3 PC chain root + join4_cal
                # calendar constants (kvjc3_pc_chain.boot_words at ctrl_lat ES_CFG_CTRL_LAT, relays 0); same HOST note
                es_cfg=dict(targets=list(ES_CFG_TARGETS), pc=es_pc, beat=es_beat, ctrl_lat=ES_CFG_CTRL_LAT, relay=es_relay, return_relay=es_return))


# ---- MU-KV-BOOT 10-19: the multi-user boot images (OT_KV_MU=1) ---------------------------------------------------------
MU = __import__('os').environ.get('OT_KV_MU', '0') == '1'


def mu_images(layer_words, own_words, receipt=False, lead=0, att_end=None, phase=None):
    """KV-PROG17 10-20: the frame compiler runs on THIS compile's attention busy end and phase-launch profile (PH0, SAFE
    window, lprg -> group relay edges); mu_calendar's module defaults are the committed 10-17 die report (groups 67), so a
    die whose relays moved got every user-0 launch judged on stale phases."""
    from tools.qwen_static_schedule import mu_calendar as MC
    keep = MC.KV_ATT_END, dict(MC.KV_PHASE)
    try:
        if phase is not None:
            MC.KV_PHASE.update(phase)
        return _mu_images(layer_words, own_words, receipt, lead, att_end)
    finally:
        MC.KV_ATT_END = keep[0]
        MC.KV_PHASE.clear()
        MC.KV_PHASE.update(keep[1])


def _mu_images(layer_words, own_words, receipt=False, lead=0, att_end=None):
    """the 4-user forms of targets 1 and 3 from the single-user ones: target 1 = rows + digest + epoch + the GAP[4][36]
    block compiled by mu_calendar (kv_frame_of_record on these rows) + seal at 470 (qkd_static_kv_layer_programme_mu,
    loaded through qkd_static_kv_boot_dispatch_mu); target 3 = enter 3, leave / deadline = the max over users
    (qkd_static_kv_ownership_calendar_mu re-arms on every user's go).  The single-user roots must be the ones the
    rows imply (enter 3, leave = stage-36 quiet + 1, deadline = token cycles)."""
    from tools.qwen_static_schedule import mu_calendar as MC
    # KV-PROG17 10-20: the attention busy run is run .. run + compiled_end - RX_CMD (qkd_native_attention_programme: a
    # second user's issue inside it is a sticky fault); 1784 is the priced tile (compiled_end 1786).  The r16 tile's
    # RETIRE_STATIC STATUS tail (+213) and TX shift (+1) extend it to 1998: the frame compiler must see the real span.
    if att_end is not None and att_end != MC.KV_ATT_END:
        if not attn_r16()['on']:
            raise ValueError(f'attention busy end {att_end} != mu_calendar.KV_ATT_END {MC.KV_ATT_END} without the r16 tile')
        MC.KV_ATT_END = att_end
    rows = MC.kv_rows_from_image(list(layer_words))
    if LINK_EMB_WIN or attn_r16()['on']:
        # KV-EMBWIN16 10-20: the filler first starts KV_FRAME_STARTS were searched on the priced-window (272) frame; on a
        # grown window the stage frame moves, so the same deterministic search (kv_frame_search seed 1) picks them here
        # KV-PROG17 10-20: OT_KV_MU_FRAME_F=3 = the r16 frame (one filler token a frame, fillers never overlap): with the
        # r16 STATUS tail the KV service window (2,003 edges) no longer fits beside u0 + a second filler (F 2 has no
        # frame: kv_frame_search fails), priced 9,300.6 vs 11,982.4 tok/s aggregate (u0 unchanged) -- COORD decision.
        F = int(os.environ.get('OT_KV_MU_FRAME_F', MC.KV_FRAME_F))
        ft = 1 if F > MC.KV_FRAME_F else None
        fs, _ = MC.kv_frame_search(rows, F, filler_tokens=ft)
        cal, gaps, starts, chk, per_user = MC.kv_frame_of_record(rows, F, tuple(fs), filler_tokens=ft)
    else:
        cal, gaps, starts, chk, per_user = MC.kv_frame_of_record(rows)
    own, per = MC.kv_ownership_roots_mu(rows, gaps)
    if list(own_words) != [3, per['leave_per_user'][0] + lead, per['deadline_per_user'][0], MC.KV_OWN_SEAL]:
        raise ValueError(f'single-user ownership roots {own_words} differ from the layer rows')
    if lead:                # KV-CAL15: the c32 guard lead on the MU leave root too (re-armed window: max over users + lead)
        own = list(own)
        own[1] += lead
        if not own[0] < own[1] < own[2]:
            raise ValueError(f'MU ownership roots {own} out of order with the c32 leave lead {lead}')
    out = dict(layer=MC.kv_layer_image_mu(list(layer_words), gaps), ownership=own, gaps=gaps, starts=starts, checks=chk)
    out['frame'] = None if not isinstance(cal, dict) else dict(F=cal['frame_tokens'], H=cal['H'], T=cal['T'], tokens_per_frame=cal['tokens_per_frame'],
                        aggregate_tok_s=round(cal['aggregate_tok_s'], 1), user_tok_s=[round(u['tok_s'], 1) for u in cal['users']],
                        first_starts=[u['first_start'] for u in cal['users']], att_end=MC.KV_ATT_END,
                        phase_groups=MC.KV_PHASE['groups'])
    if receipt:
        out['receipt'] = MC.kv_gap_receipt(list(layer_words))
    return out


def write_mu(layer_words, own_words, out, root=ROOT):
    """--mu-from: the MU boot images + receipt + the bench's start / event lists from a compiled die image directory"""
    from tools.qwen_static_schedule import mu_calendar as MC
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    m = mu_images(layer_words, own_words, receipt=True)
    rows = MC.kv_rows_from_image(list(layer_words))
    (out / 'target1.hex').write_text(''.join(f'{w:016x}\n' for w in m['layer']))
    (out / 'target3.hex').write_text(''.join(f'{w:016x}\n' for w in m['ownership']))
    H = m['receipt']['frame']['H']
    st2 = {u: [s + k * H for k in range(2) for s in ss] for u, ss in m['starts'].items()}     # two frames
    starts = sorted((s, u, i) for u, ss in st2.items() for i, s in enumerate(ss))
    (out / 'bench_starts.txt').write_text(''.join(f'{s} {u} {i}\n' for s, u, i in starts))
    ev = MC.kv_event_list(rows, m['gaps'], st2)
    (out / 'bench_events.txt').write_text(''.join(f'{c} {u} {s} {mask}\n' for c, u, s, mask in ev))
    # bench negative controls (NOT compiler output: hand-made violations of the compiler's assertions)
    g0 = [list(g) for g in m['gaps']]
    g0[0][5] = 7                                                      # user 0 gap non-zero
    (out / 'mut_u0gap.hex').write_text(''.join(f'{w:016x}\n' for w in MC.kv_layer_image_mu(list(layer_words), g0)))
    gc = [list(g) for g in m['gaps']]
    b1 = st2[1][0] + gc[1][0]                                         # user 1 stage 1 begin onto user 0's kgo edge
    cyc0 = [c for c, u, s, mk in ev if u == 0 and c > b1][0]          # first user-0 event after user 1's begin
    gc[1][0] = m['gaps'][1][0] + (cyc0 - b1)
    (out / 'mut_collide.hex').write_text(''.join(f'{w:016x}\n' for w in MC.kv_layer_image_mu(list(layer_words), gc)))
    (out / 'mut_sealwrong.hex').write_text(''.join(f'{w:016x}\n' for w in layer_words))   # single-user form (seal at 326)
    rec = dict(m['receipt'], sources=dict(layer_image_sha256=hashlib.sha256(bytes(json.dumps(list(layer_words)), 'ascii')).hexdigest(),
                                          compiler=[dict(path=p, sha256=sha(root / p)) for p in (
                                              'tools/qwen_static_schedule/mu_calendar.py', 'tools/qwen_static_schedule/mu_opcal.py',
                                              'tools/qwen_kv_die/kv_static_programme.py')]),
               bench=dict(frames=2, starts=len(starts), event_cycles=len(ev),
                          mutants=dict(mut_u0gap='GAP[0][5] = 7', mut_collide=f'GAP[1][0] + {cyc0 - b1}: user 1 stage 1 '
                                       f'begins on user 0 event cycle {cyc0}', mut_sealwrong='the 327-word single-user image')),
               ownership_target3=m['ownership'])
    (out / 'kv_gap_receipt.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    return rec


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


def priced_template(pr, root=ROOT, ages_path=None):
    """kv_static.template() with kv_static_ages.apply(die ages): every ECTL A takes QK_ISSUE_AGE = the die age (62, the
    far groups' K response; the kit's 34 is too short) and ROW_RETURN_LAT = RESPONSE_LAT + 7 of its own issuer"""
    import kv_static as K
    import kv_static_ages as KA
    ages = json.loads(Path(ages_path or root / AGES).read_text())
    g, _ = K.template(root)
    left = KA.apply(g, ages)
    ect = [i for i in g['instances'] if i['role'] == 'ectla']
    qk = sorted({i['parameters']['QK_ISSUE_AGE'] for i in ect})
    if len(ect) != 32 or qk != [pr['qk_age']]:
        raise ValueError(f'ECTL A QK_ISSUE_AGE {qk} on {len(ect)} instances, the compile used {pr["qk_age"]}')
    for i in ect:
        ki = next(j for j in g['instances'] if j['name'] == i['name'].replace('ectl_a_', 'ki_'))
        if i['parameters']['ROW_RETURN_LAT'] != ki['parameters']['RESPONSE_LAT'] + 7:
            raise ValueError(f'{i["name"]}: ROW_RETURN_LAT != RESPONSE_LAT + 7')
    return dict(graph=g, ectla=len(ect), QK_ISSUE_AGE=qk[0], unpriced_left=left)


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
    priced = None
    if r['profile']['kind'] == 'die':                   # the priced static-join template (coordinator 10-17 decision 1)
        priced = priced_template(r['profile'], root)
        (out / 'static_join.priced.json').write_text(json.dumps(priced.pop('graph'), indent=1) + '\n')
    (out / f'target{LINK_CFG_TARGET}.hex').write_text(''.join(f'{w:016x}\n' for w in r['link_cfg']['program']))
    for t, k in zip(ES_CFG_TARGETS, ('pc', 'beat')):
        (out / f'target{t}.hex').write_text(''.join(f'{w:016x}\n' for w in r['es_cfg'][k]))
    for im in r['images']:
        (out / f'target{im["target"]}.hex').write_text(''.join(f'{w:016x}\n' for w in im['program'] + im['descriptors']))
    vec = ''.join(f'{w:08x}' for w in reversed(r['layer']['words'][:324]))
    (out / 'layer_programme_image.svh').write_text(
        f'// GENERATED by tools/qwen_kv_die/kv_static_programme.py (profile {r["profile"]["kind"]}): do not edit\n'
        f"localparam [36*9*32-1:0] LP_ROOTS = {36*9*32}'h{vec};\n"
        f"localparam [63:0] LP_DIGEST = 64'h{r['layer']['digest']:016x};\n"
        f"localparam [15:0] LP_EPOCH = 16'd{r['layer']['epoch']};\n")
    report = dict(schema='opentallas.qwen_kv_static.programme_report.v1', status='COMPILED_NOT_QUALIFIED', mu_frame=r.get('mu_frame'),
                  profile=r['profile'], link=r['link'], leads=r['leads'], cal_deltas=r['cal_deltas'], emb_fill=r['emb_fill'],
                  layer_relative_roots=r['layer']['rows'][1]['roots'], stage1_roots=r['layer']['rows'][0]['roots'],
                  writer=dict(slots=r['writer']['slots'], stop=r['writer']['stop']), ownership=r['ownership'],
                  groups={k: {kk: vv for kk, vv in v.items() if kk not in ('landing_words', 'front_words')} for k, v in r['groups'].items()},
                  controller={str(pc): {k: v for k, v in c.items() if k != 'words'} for pc, c in r['controller'].items()},
                  attention=r['attention'], phase=r['phase'], priced_template=priced,
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
    ap.add_argument('--mu-from', type=Path, help='MU-KV-BOOT: write the 4-user target 1 / 3 images, receipt and bench '
                                                 'lists to --out from a compiled die directory (its target1.hex / target3.hex)')
    a = ap.parse_args()
    if a.mu_from:
        rd = lambda n: [int(x, 16) for x in (a.mu_from / n).read_text().split()]
        rec = write_mu(rd('target1.hex'), rd('target3.hex'), a.out)
        print(json.dumps(dict(frame=rec['frame'], checks=rec['checks'], ownership=rec['ownership_target3'], bench=rec['bench'])))
        return
    ages = json.loads(a.ages.read_text()) if a.profile == 'die' else None
    words = [int(x, 16) for x in a.program.read_text().split()] if a.program else None
    r = compile_all(profile(a.profile, ages), a.epoch, words)
    rep = write(r, a.out)
    print(json.dumps(dict(status=rep['status'], profile=a.profile, leads=rep['leads'], stage1=rep['stage1_roots'],
                          attention={k: rep['attention'][k] for k in ('compiled_rx_cmd', 'compiled_tx_first', 'compiled_end')},
                          boot=rep['boot']['words'], frames=rep['boot']['frames'], operations=rep['operations'],
                          phase_outside=None if rep['phase'] is None else len(rep['phase']['outside_window']),
                          ownership=r['ownership']['words'][:3], cal_deltas=r['cal_deltas'],
                          emb_fill={k: r['emb_fill'][k] for k in ('status', 'margin', 'last_word', 'row_tx_slot', 'embed_window_needed')})))


if __name__ == '__main__':
    main()
