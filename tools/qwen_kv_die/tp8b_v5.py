"""qwen-tp8 tp8b, contract v5 stage (die lead r8, 2026-10-13): the die generator follows contract v4 / v4b and the
coordinator decisions of 10-13, so a regenerated case IS the contract (no patch-only slots).

Called at the end of before_relays (after _tp8b_kv), i.e. on the final placement and before the relay plan:

  T7   stations / heads: x[508:0] -> x_d[507:0] (with the flow) + x_r (against it); the relay frames carry both
       (m['bus_pair'], _relays); rst_n on N beside ck; tile pin tap[507:0], station tap_r tied high at the die (decision
       b: ot_qwen_rom_tile_nk has no ready port)
  T8   qkd_cdc_wleaf 183.6 x 183.6, RTL ports (port split of the die bundles co / hi / ho / wi / wr / cf)
  T9   qkd_rhead cluster 691.2 x 453.6 (R0 / MX origin - 43.2), pins per v4; KV relays left inside a grown head are torn
  T10  qfd_sp_vector_memory = region envelope 4708.8 x 2347.92 at (13284.0, 17249.76); head root xw / xe = 508 + ready
  T12  qfd_sp_res_ser 777.6 x 518.4 + rst_n / me_en / fault
  T13  qfd_tt_up4 one cluster in tt_up4_0, tt_up4_1..3 removed, sel 26 b
  T14  the SU group (sp_su64_sfu, 8 cbuf_g, 8 crom_g, seq_su) follows the VM: SU abutted on the VM N face, the group
       mirrored above it (closed cbuf/crom masters MX; SU frame R0 with its N / S pin faces swapped: an MX master's M8 clock
       pins are not mirror-legal).  Cut reason: su_vm = 8,511 b; left at y 8.9-10.9 mm it needs 14.2 kb of vertical capacity at
       0.60 through the A|B channel (12.6 kb in all) for 6.3 mm, and every SU read pays ~15 stages each way
  T15  qfd_crom_g + 32.4 um N (194.376 x 550.776)
  T16  KV control strip = 32 x qkd_ctrl_pc (247.512 x 378) + qkd_ctrl_kc (kc async FIFO, 45.36 um, S end of every strip:
       one PC master, one pin plan); ot_hbm3e_phy re-pinned per PC (phy_repin): rsp_* of PC k faces leaf k, req_* at the
       S end beside the kc leaf
  T17  qfd_seq_su bundles (consumer side): ib dropped (the ME instruction is issued by the control tile: tt_ctlm.ib ->
       head root), dflt dropped (no link end on one die), dc 56 b / dh 187 b, cc 518 b valid only, cd = cd_d + cd_cr,
       cbr0..7 kept (8 producers; the cell owns the registered reducer)
  T18  reset: qkd_pll / qfd_clkrx are hard-macro abstracts; ot_qwen_sys_rst_seq is its own leaf (qkd_rstseq beside the
       PLL, qfd_rstseq beside the clock receiver); new reset nets rst_field (tiles, stations, heads) and rst_spine
       (res_ser, tt_up4, crom_g, cbuf_g) join the registered reset tree
Emission (masters / LEF / netlist): port kind 'pins' (explicit positions), PORT_SPLIT (a die bundle = several view ports,
LSB first), TIES (constants: straps, chain ends, tap_r), PHY pin groups ('*dfi:<group>').
"""
import json
import math
import copy
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'hier_contract'))

DW = 508
VM_ENV = dict(x=13284.0, y=17051.04, w=4838.4, h=2546.64)   # r11 / contract v5: VM slot change request v2 (VM3 10-13 18:08) ACCEPTED
VM_OBS_TOP = 9                         # r11: region / band clusters are M9-capped; the die keeps only its M8 / M9 PG straps there
import os as _os
SPLIT_COMPUTE = _os.environ.get('OT_TP8_SPLIT') == 'compute'
if SPLIT_COMPUTE:
    # owner 08:20 PT 10-14: distributed x slices adopted -> TRIMMED central VM (banks / SU ports / row reads), M7 cap, no
    # M8/M9 grant, no wall (compute-die contract v1; tools/qwen_split/compute_spine.py places it)
    VM_ENV = dict(VM_ENV, w=4708.8, h=2203.2)
    VM_OBS_TOP = 7
RHEAD_LAT_Y = 8.64                     # r11: legal origin lattice of the head frame in y (M6 nb pins + site rows; ot_mts::place)
HEAD_RROW = 0.0                        # r12: optional relay row between far and near head (34.56 fits the 73.5-um inter-engine slack)
                                       # but OFF: it moves the far-head pair from 466.75 to ~501 um (> 500 reach) and would need a relay
                                       # on far heads only (unequal ectl->head depth).  With the adopted pin plan the far pair is a
                                       # direct hop; its budget (o_ectl + 354.7 ps wire + s_head <= 683.3) is owed by ectl A/B
                                       # (o 258 ps > 220 defect) and the head pin flops
WCTL_H = 129.6                         # r11 / v5: closed qkd_kvwq_ctl_bin-sl2 is 172.8 x 129.6, N-aligned in the old 518.4 slot
SU_X = 16424.64                      # the VM stream's SU reservation column (el1011-qwen-tp8.log 04:20)
RHEAD_WH, RHEAD_OLD_W = (712.8, 453.6), 648.0   # coordinator 10-13: qkh_head_hs grant (v4 T9 was 691.2)
CDC_WH = 183.6
CROM_DH = 32.4
PC_H, KC_H, NPC = 378.0, 45.36, 32
# T21 (el1013-qwen-romio, coordinator 10-13): PHY abstracts re-shaped / RXD 512 / FDI on the W face (physical/
# qwen_missing_phy/tp8_1013, merged from codex/tp8-phy-prepared-1013); flit 1,043 b
HOST_PHY = ('ot_qfd_serdes_112g_x12_phy', 2320.056, 1563.570)
FDI_FW = 1043
FDI_BITS = 1 + 1 + FDI_FW + 1 + FDI_FW          # tx_up, tx_v, tx_flit, rx_v, rx_flit (clk / rst_n are their own pins)
FDI_Y0, FDI_STEP = 600.0, 0.048                 # W-face pin window of the abstract: 2,091 pins from y 600 at one M4 track
IO_STRIP_DX = 43.2                              # io_serdes_1 / _2 move W: 127.4-um FDI access strip W of the host PHY
IO_CLUSTERS = ('qfd_io_serdes', 'qfd_io_ucie')
# r9: CLOSED views the generator adopts pin for pin (outline checked, every 'face' / 'pins' port takes the view's own
# pin positions, a split bundle = its view ports LSB first): the relay plan, the contract and the case are then made
# on the real pins and tools/qwen_tp8/bind_real.py can drop the view's LEF in unchanged
ROOT = HERE.parents[1]
VIEWS = {
    'qfd_cst_s': 'physical/ref_tile/qfd_cst_s/views/qfd_cst_s',
    'qfd_cst_n': 'physical/ref_tile/qfd_cst_n/views/qfd_cst_n',
    'qfd_chead_e': 'physical/ref_tile/qfd_chead_e/views/qfd_chead_e',
    'qfd_chead_w': 'physical/ref_tile/qfd_chead_w/views/qfd_chead_w',
    'qkd_cdc_wleaf': 'physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf',
    'qkd_kvwq_leaf_s_w129_m': 'physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m',
    'qkd_kvwq_ctl_bin': 'physical/ref_tile/qkd_kvwq_ctl_bin/views/qkd_kvwq_ctl_bin',
    'ot_qfd_serdes_112g_x12_phy': 'physical/qwen_missing_phy/tp8_1013/ot_qfd_serdes_112g_x12_phy',
    'qkd_rstseq': 'physical/ref_tile/qkd_rstseq/views/qkd_rstseq',
    'qkd_ctrl_pc': 'physical/ref_tile/qkd_ctrl_pc/views/qkd_ctrl_pc',
    'qkd_ctrl_kc': 'physical/ref_tile/qkd_ctrl_kc/views/qkd_ctrl_kc',
    **{f'qkd_ectl_{q}': f'physical/ref_tile/qkd_ectl_{q}/views/qkd_ectl_{q}' for q in 'abc'},
    'qfd_su_cbuf_g': 'physical/ref_tile/qfd_su_cbuf_g_m5/views/ot_qfd_su_cbuf_g',
    'qfd_crom_g': 'physical/ref_tile/qfd_crom_g_m5/views/ot_qfd_crom_gr',
}
RSTSEQ_KV = 21.6
# T22b (el1013-qwen-kvcentre r3, 10-13 14:05; coordinator: merged KV sequencer slot): cluster 604.8 x 475.2, centred in x
# and S-aligned in the v4 slot 777.6 x 518.4 (the hub abuts below as before; 47.5 um open to the gateway above)
SEQ_WH, SEQ_OLD_W = (604.8, 475.2), 777.6
SEQ_BITS = dict(hc=182, tk=93, x3=525, attn_ret=521, o4_kvd=44, ares=520)     # x3 = r_x3_d 524 + cr, attn_ret = t_ar_d 520 + cr
SEQ_DROP = ('gq', 'gr')                                                        # no producer / consumer on one die
_VP = {}


def view_pins(master):
    """(w, h, {pin name: (face, layer, position along the face)}) of a closed view's LEF, or None when it is absent"""
    if master not in _VP:
        f = ROOT / VIEWS[master] / f'{Path(VIEWS[master]).name}.lef'
        if not f.exists():
            _VP[master] = None
            return None
        t = f.read_text()
        mm = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t)
        w, h = float(mm.group(1)), float(mm.group(2))
        out = {}
        for q in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$', t, re.M | re.S):
            r = re.search(r'LAYER (\S+) ;\s*\n\s*RECT ([-\d. ]+) ;', q.group(2))
            if not r or q.group(1) in ('VDD', 'VSS'):
                continue
            x0, y0, x1, y1 = map(float, r.group(2).split()[:4])
            if x0 <= 1e-6 and x1 < w / 2:
                fa, pos = 'W', (y0 + y1) / 2
            elif x1 >= w - 1e-6 and x0 > w / 2:
                fa, pos = 'E', (y0 + y1) / 2
            elif y0 <= 1e-6 and y1 < h / 2:
                fa, pos = 'S', (x0 + x1) / 2
            elif y1 >= h - 1e-6 and y0 > h / 2:
                fa, pos = 'N', (x0 + x1) / 2
            else:
                continue
            out[q.group(1)] = (fa, r.group(1), round(pos, 4))
        _VP[master] = (w, h, out)
    return _VP[master]


def adopt_view(M, master, split, rec, pw=None):
    q = M.get(master)
    if q is None:
        return
    vp = view_pins(master)
    if vp is None:
        rec[master] = 'view LEF not in this tree: generated pins kept'
        return
    w, h, P = vp
    if abs(q.w - w) > 0.03 or abs(q.h - h) > 0.03:
        rec[master] = f'outline differs: frame {q.w} x {q.h}, view {w} x {h}: generated pins kept'
        return
    done, kept = 0, []
    for p, sp in list(q.ports.items()):
        if sp[0] not in ('face', 'pins', 'area') or (sp[0] == 'area' and master not in ('qfd_su_cbuf_g', 'qfd_crom_g')):
            continue
        parts = split.get(master, {}).get(p) or [(p, (pw or {}).get((master, p)) or sp[1])]
        names = []
        for sub, nb in parts:
            names += [sub] if (nb == 1 and sub in P) else [f'{sub}[{b}]' for b in range(nb)]
        got = [P.get(n) for n in names]
        if any(g is None for g in got) or len({(g[0], g[1]) for g in got}) != 1:
            kept.append(p)
            continue
        q.ports[p] = ('pins', len(got), got[0][0], got[0][1], [g[2] for g in got], 1)
        done += 1
    rec[master] = dict(view=VIEWS[master], ports_on_view_pins=done, ports_kept_generated=kept)
SEL_BITS = 26
STATIONS = {'qfd_cst_s': dict(N=('a', 'in'), S=('b', 'out'), W=('tap', 'out')),
            'qfd_cst_n': dict(S=('b', 'in'), N=('a', 'out'), W=('tap', 'out')),
            'qfd_chead_w': dict(E=('e', 'in'), W=('w', 'out'), N=('n', 'out'), S=('s', 'out')),
            'qfd_chead_e': dict(W=('w', 'in'), E=('e', 'out'), N=('n', 'out'), S=('s', 'out'))}
SPLIT = {
    'qkd_cdc_wleaf': dict(
        co=[('l_v', 1), ('l_sec', 17), ('l_row', 8), ('l_data', 256), ('l_pop', 1)],
        hi=[('h_lv', 1), ('h_lsec', 17), ('h_lrow', 8), ('h_ldata', 256), ('h_hand', 1), ('h_wcon', 1), ('h_av', 1),
            ('h_atag', 9)],
        ho=[('h_cred', 3), ('h_wv', 1), ('h_wsec', 24), ('h_cv', 1), ('h_csec', 24), ('h_cdata', 256), ('h_ctag', 9),
            ('h_fault', 1)],
        wi=[('w_v', 1), ('w_sec', 24), ('w_data', 256), ('w_tag', 9)],
        wr=[('w_room', 1), ('wd_v', 1), ('wd_tag', 9)],
        cf=[('c_fault', 1)]),
    # closed qkd_kvwq_ctl_bin-sl1-ecdaf6345 (rtl/physical/ot_qwen_kv_slot_wrappers.sv)
    'qkd_kvwq_ctl_bin': dict(kvn=[('kvn_d', 1047), ('kvn_cr', 1)]),
    'qfd_seq_su': dict(cd=[('cd_d', 547), ('cd_cr', 1)]),
    'ot_qfd_x3_mux_native': dict(x3=[('x3_d', 512), ('x3_tag', 11), ('x3_v', 1)]),   # v1.3 x3 mux, x3 bundle LSB first
    'qfd_su_cbuf_g': dict(ck=[('clk', 1)], fa=[('f_re', 8), ('f_addr', 192), ('f_stage', 6)],
        fq=[('f_q', 512), ('f_fault', 1)], ctl=[('stage', 6), ('tok_start', 1), ('tpos', 18)],
        rdy=[('st_rdy', 1), ('st_rdy_stage', 6), ('fault', 1), ('fault_code', 2)],
        sa=[('crom_re', 8), ('crom_addr', 192), ('crom_stage', 6)], sq=[('crom_q', 512)]),
    'qfd_crom_g': dict(ck=[('clk', 1)], ra=[('crom_re', 8), ('crom_addr', 192), ('crom_stage', 6)],
        rq=[('crom_q', 512), ('fault', 1)]),
    # T22b: the merged sequencer's credit pins stand beside their words (with the flow _d, against it _cr)
    'qkd_seq': dict(r_x3=[('r_x3_d', 524), ('r_x3_cr', 1)], t_ar=[('t_ar_d', 520), ('t_ar_cr', 1)],
                    **{f'kvn_{st}': [(f'kvn_{st}_d', 1047), (f'kvn_{st}_cr', 1)] for st in ('WS', 'WN', 'ES', 'EN')}),
    # T21: the host PHY abstract's own FDI pins (physical/qwen_missing_phy/tp8_1013, flit 1,043 b at RXD 512)
    'ot_qfd_serdes_112g_x12_phy': dict(fdi=[('tx_up', 1), ('tx_v', 1), ('tx_flit', 1043), ('rx_v', 1), ('rx_flit', 1043)]),
}
# A head's ti word is driven by three real leaves. No frame or logic joins these bits:
# the die netlist connects each synthetic bus straight to these exact ti bits.
JOIN = {'qkd_rhead': {
    'ti_a': ('ti', list(range(4, 516))),
    'ti_b': ('ti', list(range(516, 1028))),
    'ti_cl': ('ti', list(range(4)) + list(range(1028, 1040))),
    'ti_q': ('ti', list(range(1040, 1559))),
}}

# SEAM between two CLOSED views (r8 check, coordinator 10-13): qkd_kvwq_ctl_bin packs f<g>[292:0] = {f_v, f_d 256, f_sec
# 24, f_lane 3, f_tag 9} and r<g>[1:0] = {r_v, r_bad} (MSB first), the leaf wrapper qkd_kvwq_leaf_s_w129_m takes c / n
# [292:0] = {tag 9, lane 3, sec 24, d 256, v} and dn / dp[1:0] = {bad, v}: the field ORDER is reversed.  The die net keeps
# the leaf order (the feed chain is leaf to leaf); at the control leaf's pins the die wires field to field: a
# permutation of the net, MSB first as (hi, lo) net slices.  No logic, no cycle; the wires cross inside one 14-um bundle.
PERM = {'qkd_kvwq_ctl_bin': dict(
    **{f'f{g}': [(0, 0), (256, 1), (280, 257), (283, 281), (292, 284)] for g in range(4)},
    **{f'r{g}': [(0, 0), (1, 1)] for g in range(4)})}
PHY_PC = (('rsp_v', 1), ('rsp_rdy', 1), ('rsp_beat', 4), ('rsp_tag', 16), ('rsp_data', 256))          # 278 b per PC
PHY_REQ = (('req_v', 1), ('req_rdy', 1), ('req_we', 1), ('req_len', 5), ('req_tag', 16), ('req_addr', 31),
           ('req_wdata', 256))                                                                          # 311 b
PC_PHY_Y = 175.92          # PC-leaf local y of the centre of its PHY slice (E face)
STEP = 0.096


def joined_expr(values):
    """Exact per-bit join rendered as contiguous net slices (MSB first)."""
    assert set(values) == set(range(max(values) + 1)), 'incomplete port join'
    runs = []
    for bit in range(max(values), -1, -1):
        mm = re.fullmatch(r'(.*)\[(\d+)\]', values[bit])
        assert mm, values[bit]
        name, index = mm.group(1), int(mm.group(2))
        if runs and runs[-1][0] == name and index == runs[-1][2] - 1:
            runs[-1][2] = index
        else:
            runs.append([name, index, index])
    return '{' + ', '.join(f'{nm}[{hi}:{lo}]' if hi != lo else f'{nm}[{hi}]' for nm, hi, lo in runs) + '}'


def _snap(y):
    return round(0.012 + 0.048 * round((y - 0.012) / 0.048), 3)


def phy_groups():
    """{group: [(pin base, bit)]} in bus-bit order: PC k = rsp_* of PC k, 'req' = the shared request port"""
    g = {}
    for k in range(NPC):
        g[str(k)] = [(b, k * n + j) for b, n in PHY_PC for j in range(n)]
    g['req'] = [(b, j) for b, n in PHY_REQ for j in range(n)]
    return g


def phy_pin_y():
    """PHY-local y of every signal pin after the per-PC re-pin.  The PHY sits 71.28 um above its strip's S end; PC leaf k
    spans strip y KC_H + 378 k .. + 378; its PHY slice is centred PC_PHY_Y above the leaf's S edge."""
    off = KC_H - 71.28
    y = {}
    for k in range(NPC):
        n = sum(b for _, b in PHY_PC)
        lo = off + PC_H * k + PC_PHY_Y - n * STEP / 2
        for i, (b, j) in enumerate(phy_groups()[str(k)]):
            y[(b, j)] = _snap(lo + i * STEP)
    for i, (b, j) in enumerate(phy_groups()['req']):
        y[(b, j)] = _snap(4.0 + i * STEP)
    return y


_PHY_FIXED = {}


def _phy_fixed_pins():
    """PHY-local y of the abstract's clk / rst_n pins (W face of the unflipped macro)"""
    if not _PHY_FIXED:
        f = ROOT / 'physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy.lef'
        t = f.read_text() if f.exists() else ''
        for pn in ('clk', 'rst_n'):
            mm = re.search(rf'  PIN {pn}\n(.*?)  END {pn}\n', t, re.S)
            r = mm and re.search(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', mm.group(1))
            if r:
                _PHY_FIXED[pn] = (float(r.group(2)) + float(r.group(4))) / 2
    return _PHY_FIXED


def phy_repin(text):
    """the ot_hbm3e_phy abstract LEF with every signal pin moved to its per-PC y (x extent, layer, width kept)"""
    ys = phy_pin_y()

    def one(pm):
        name, body = pm.group(1), pm.group(2)
        if 'USE POWER' in body or 'USE GROUND' in body:
            return pm.group(0)
        mm = re.match(r'^(.*)\[(\d+)\]$', name)
        key = (mm.group(1), int(mm.group(2))) if mm else (name, 0)
        if key not in ys:
            return pm.group(0)

        def rect(rm):
            x0, y0, x1, y1 = (float(rm.group(i)) for i in range(1, 5))
            hw = (y1 - y0) / 2
            return f'RECT {x0:.3f} {ys[key] - hw:.3f} {x1:.3f} {ys[key] + hw:.3f}'
        return f'  PIN {name}\n' + re.sub(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', rect, body) + f'  END {name}\n'
    return re.sub(r'  PIN (\S+)\n(.*?)  END \1\n', one, text, flags=re.S)


def _pack(L, items, keep=()):
    """items [(port, span_um, want centre)] -> {port: centre}: in order of `want`, no overlap, 2 um apart, clear of the
    `keep` intervals, inside [4, L - 4]"""
    out, cur = {}, 4.0
    its = sorted(items, key=lambda t: t[2])
    for p, sp, want in its:
        lo = max(cur, want - sp / 2)
        for _ in range(len(keep) + 1):
            hit = [k for k in keep if k[0] < lo + sp + 2.0 and lo - 2.0 < k[1]]
            if not hit:
                break
            lo = max(k[1] for k in hit) + 2.0
        out[p] = lo
        cur = lo + sp + 2.0
    hi = L - 4.0
    for p, sp, want in reversed(its):
        if out[p] + sp > hi:
            out[p] = hi - sp
            for _ in range(len(keep) + 1):
                hit = [k for k in keep if k[0] < out[p] + sp + 2.0 and out[p] - 2.0 < k[1]]
                if not hit:
                    break
                out[p] = min(k[0] for k in hit) - 2.0 - sp
        hi = out[p] - 2.0
        if out[p] < 2.0:
            raise ValueError(f'v5 pin plan: {p} does not fit ({L:.1f} um face, {len(items)} groups)')
    return {p: out[p] + sp / 2 for p, sp, _ in its}


def apply(v, m, G):
    S = v.SHAVE
    by = {i.name: i for i in m['insts']}
    rec = m.setdefault('tp8b_v5', {})
    ties = m.setdefault('ties', [])            # (inst, port, bits, value)
    pair = m.setdefault('bus_pair', {})
    split = m.setdefault('port_split', {})
    split.update({k: dict(q) for k, q in SPLIT.items()})
    m['port_join'] = {name: dict(parts) for name, parts in JOIN.items()}
    B = list(m['buses'])

    def drop_insts(names):
        names = set(names)
        m['insts'] = [i for i in m['insts'] if i.name not in names]

    # ---------------------------------------------------------------- T13 tt_up4: one cluster, sel 26 b
    ug = [i.name for i in m['insts'] if i.master == 'qfd_tt_up4_g']
    drop_insts(ug)
    # r9: a removed cell leaves a multi-pin net (clock, reset) by its own pin only; its 2-pin data buses go with it
    # (run b2 dropped the whole net: clk_r22 / clk_r96 = 199 + 136 sinks, tt_ctlm, tt_up4_0 and the VM without a clock)
    ugs = set(ug)
    B = [(b, c, SEL_BITS if b == 'o4_sel' else n, [x for x in e if x[0] not in ugs]) for b, c, n, e in B
         if c in ('clock_trunk', 'reset') or not any(x[0] in ugs for x in e)]
    rec['tt_up4'] = dict(removed=ug, sel_bits=SEL_BITS)

    # ---------------------------------------------------------------- T17 seq_su bundles
    nb = []
    for b, c, n, e in B:
        if b in ('seq_ib', 'd2d_flt'):
            continue
        if b == 'seq_d2d':
            n = 56
        elif b == 'd2d_seq':
            n = 187
        elif b in ('coll_seq', 'coll_seq_x'):
            n = 518
        nb.append((b, c, n, e))
    B = nb
    B.append(('tt_ib', 'tree_spine', 380, [('tt_ctlm', 'ib'), ('sp_vector_memory', 'ib')]))
    rec['seq_su'] = dict(dropped=['seq_ib', 'd2d_flt'], dc=56, dh=187, cc=518, cd='cd_d[546:0] + cd_cr',
                         ib='tt_ctlm.ib[379:0] -> sp_vector_memory.ib (head root)')

    # ---------------------------------------------------------------- T22b merged KV sequencer slot
    sq = by.get('seq')
    if sq is not None:
        B = [(b, c, SEQ_BITS.get(b, n), e) for b, c, n, e in B if b not in SEQ_DROP]
        old = [sq.x, sq.y, sq.w, sq.h]
        sq.x = round(sq.x + (SEQ_OLD_W - SEQ_WH[0]) / 2, 4)
        sq.w, sq.h = SEQ_WH
        rec['seq'] = dict(old=old, new=[sq.x, sq.y, sq.w, sq.h], dropped=list(SEQ_DROP), bits=SEQ_BITS,
                          x3_credits=40, note='ROM-side words on N beside the gateway, quadrant words W / E, hub S, '
                          'host words (hc 182 b / tk 93 b / kst) on E at the S end: the hub abuts the whole S face')

    # ---------------------------------------------------------------- T10 / T14 VM envelope, SU group follows
    vm, su = by['sp_vector_memory'], by['sp_su64_sfu']
    grp = [i for i in m['insts'] if i.name == 'seq_su' or i.master in ('qfd_su_cbuf_g', 'qfd_crom_g')]
    old = dict(vm=[vm.x, vm.y, vm.w, vm.h], su=[su.x, su.y])
    # r10: a variant column pitch (OT_TP8_TILE) moves the spine with the W field: the VM / SU reservation follows it
    dxs = round((v.KV_TILE_W - 394.848) * (v.COLS / 2 - 1) + (v.TILE_BODY_W - 311.04), 4)      # = the shift of column 23's station
    vm.x, vm.y, vm.w, vm.h = round(VM_ENV['x'] + dxs, 4), VM_ENV['y'], VM_ENV['w'], VM_ENV['h']
    su_new = (round(SU_X + dxs, 4), round(VM_ENV['y'] + VM_ENV['h'], 4))
    dx = su_new[0] - su.x
    for i in grp:
        d = su.y - (i.y + i.h)                       # gap below the SU (old), kept above it (new)
        if i.master == 'qfd_crom_g':
            i.h = round(i.h + CROM_DH, 4)            # T15: grows N, away from the buffer rows
        i.x, i.y = round(i.x + dx, 4), round(su_new[1] + su.h + d, 4)
        if i.master in ('qfd_su_cbuf_g', 'qfd_crom_g'):
            i.orient = 'MX'
            g = int(i.name.rsplit('_', 1)[1])
            if i.master == 'qfd_su_cbuf_g':
                ties += [(i.name, 'grp', 3, g), (i.name, 'f_lat', 5, 8)]
                # Final far-ROM latency is set after relay allocation from both legs (base tile = 8 edges).
            else:
                ties += [(i.name, 'crom_lb', 6, 8 * g)]
    su.x, su.y = su_new[0], su_new[1]
    v.SU_VM_NORTH = True
    v.WALL_AVOID = not SPLIT_COMPUTE   # r9: the VM region spans the spine: planned paths go round walls (_relays); split: M7-cap VM, no wall
    ck = by.get('clk_rx')
    bl = by.get('sp_band_lanes_1')
    if ck is not None and bl is not None:
        # the clock receiver leaves the strip under the VM's centre relief bays for the W sub-column
        ck.x, ck.y = round(bl.x, 4), round(v.up(bl.y + bl.h + 43.2, v.GY), 4)
    rec['real_rom_ports'] = dict(crom_strobe_to_q_edges=8, cbuf_far_latency='8 + outgoing relays + returning relays',
                                 unconnected_outputs={'qfd_crom_g': ['fault_code[1:0]']},
                                 clock_pin='ck die bundle -> clk real pin', orientation='MX')
    rec['vm'] = dict(old=old, envelope=VM_ENV, su=[su.x, su.y, 'SU R0 with N/S swapped; closed cbuf/crom MX'], group=sorted(i.name for i in grp),
                     clk_rx=[ck.x, ck.y] if ck is not None else None)

    # ---------------------------------------------------------------- T12 res_ser cluster slot
    for i in m['insts']:
        if i.master == 'qfd_sp_res_ser':
            i.w, i.h = 777.6, 518.4
    for k, i in enumerate(sorted((i for i in m['insts'] if i.master == 'qfd_sp_res_ser'), key=lambda i: i.name)):
        B += [(f'o4_me_en_rs{k}', 'spine_local', 1, [('tt_ctlm', f'mer{k}'), (i.name, 'me_en')]),
              (f'rs_fault_{k}', 'spine_local', 1, [(i.name, 'fault'), ('tt_ctlm', f'rf{k}')])]

    # ---------------------------------------------------------------- T8 cdc_wleaf, T9 rhead
    for i in m['insts']:
        if i.master == 'qkd_cdc_wleaf':
            i.w = i.h = CDC_WH
        elif i.master == 'qkd_rhead':
            if i.orient in ('R0', 'MX'):
                i.x = round(i.x + i.w + (RHEAD_OLD_W - i.w) - RHEAD_WH[0], 4)
            i.w, i.h = RHEAD_WH
        elif i.master == 'qkd_kvwq_ctl_bin' and i.h > WCTL_H + 1.0:
            # v5: the closed sl2 view; N-aligned (keeps the kvn / f3 hops), the freed 388.8 um takes the f0 / f1 relays
            top = i.y + i.h
            i.w, i.h = 172.8, WCTL_H
            i.y = round(v.dn(top - WCTL_H, v.GY), 4)
    # r11 (chain r10a real case FAIL: 'no legal, non-overlapping origin for ectl_WS_2'): the head frame's legal origins are
    # an 8.64-um lattice in y; a head half a step off was snapped up, its neighbour down, and the 131.76-um ectl gap
    # closed to 125.28.  Every engine is packed on the lattice here: heads 1 / 0 downward from the ectl, 2 / 3 upward.
    eng = {}
    for i in m['insts']:
        if i.master == 'qkd_rhead':
            st, e, h = i.name.split('_')[1:4]
            eng.setdefault((st, e), {})[int(h)] = i
    L = RHEAD_LAT_Y
    lat_moves = 0
    for (st, e), hd in sorted(eng.items()):
        ec = by.get(f'ectl_{st}_{e}')
        if ec is None or len(hd) != 4:
            continue
        o = sorted(hd.values(), key=lambda q: q.y)
        lo = [q for q in o if q.y < ec.y]
        hi = [q for q in o if q.y > ec.y]
        lim = ec.y - 2.16
        for k, q in enumerate(reversed(lo)):
            y = math.floor((lim - q.h) / L + 1e-9) * L
            lat_moves += abs(y - q.y) > 1e-6
            q.y = round(y, 4)
            lim = q.y - 2.16 - (HEAD_RROW if k == 0 and len(lo) == 2 else 0.0)
        lim = ec.y + ec.h + 2.16
        for k, q in enumerate(hi):
            y = math.ceil(lim / L - 1e-9) * L
            lat_moves += abs(y - q.y) > 1e-6
            q.y = round(y, 4)
            lim = q.y + q.h + 2.16 + (HEAD_RROW if k == 0 and len(hi) == 2 else 0.0)
    # r12: the relay rows must not push an engine into its neighbour (heads of one stack column, sorted by y)
    col = {}
    for i in m['insts']:
        if i.master == 'qkd_rhead':
            col.setdefault((i.name.split('_')[1], round(i.x, 1)), []).append(i)
    clash = []
    for k_, hs in col.items():
        hs.sort(key=lambda q: q.y)
        for a_, b_ in zip(hs, hs[1:]):
            if a_.y + a_.h + 2.16 > b_.y + 1e-6:
                clash.append((a_.name, b_.name, round(b_.y - a_.y - a_.h, 3)))
    if clash:
        raise RuntimeError(f'r12 head relay rows: {len(clash)} head overlaps, first {clash[:3]}')
    rec['rhead_lattice'] = dict(lattice_y=L, heads_moved=int(lat_moves), relay_row_um=HEAD_RROW)

    # ---------------------------------------------------------------- r9 pin alignment at the die (pin_align FAIL classes)
    # (1) the attention stack is as tall as the head column it serves (4 engines x (4 heads + ectl) = 8,164.8 um; the
    #     7,817-um frame put the engine ports at a 1,954-um pitch against the heads' 2,041: head nb words 16-374 um off
    #     their abutted ports, the last head past the frame)
    grown = {}
    for a_ in m['insts']:
        if a_.master in ('qkd_astk', 'qkd_astk_n'):
            st = a_.name.split('_', 1)[1]
            top = max((i.y + i.h for i in m['insts'] if i.master == 'qkd_rhead' and i.name.startswith(f'head_{st}_')), default=None)
            if top is not None and top - a_.y > a_.h + 1e-3:
                grown[a_.name] = [a_.h, round(top - a_.y, 4)]
                a_.h = round(top - a_.y, 4)
    # (2) write-queue leaf under its CDC leaf: both views are closed and neither orders its pins (w / wi 290 b, jog to 94
    #     um in a 2.16-um gap).  FIX AT DIE: the leaf is mirrored in x and re-seated (x offset 38.016 inside the CDC
    #     span, mirror image on the E side) and the stack's 10.8 um of slack per PC goes between the two (gap 8.64 um):
    #     160 crossing wires on 272 tracks = 0.59
    reseat = 0
    cdcs = {i.name: i for i in m['insts'] if i.master == 'qkd_cdc_wleaf'}
    for i in m['insts']:
        if i.master != 'qkd_kvwq_leaf_s_w129_m':
            continue
        c_ = cdcs.get('cdc_' + i.name.split('_', 1)[1])
        if c_ is None or not (0.0 <= c_.y - (i.y + i.h) <= 12.0):
            continue
        i.orient = {'MX': 'R180', 'R180': 'MX', 'R0': 'MY', 'MY': 'R0'}[i.orient]
        off = LEAF_DX if c_.orient in ('MY', 'R180') else round(c_.w - i.w - LEAF_DX, 4)
        i.x = round(c_.x + off, 4)
        i.y = round(c_.y - LEAF_GAP - i.h, 4)
        reseat += 1
    rec['pin_align_die'] = dict(astk_height=grown, kvwq_leaf_reseated=reseat, leaf_dx=LEAF_DX, leaf_gap=LEAF_GAP)

    # ---------------------------------------------------------------- T16 KV control strips
    strips = [i for i in m['insts'] if i.master in ('qkd_ctrl', 'qkd_ctrl_n')]
    v.PIN_POS_EXTRA = dict(getattr(v, 'PIN_POS_EXTRA', None) or {})
    pys = phy_pin_y()
    gy = {g: sum(pys[q] for q in l) / len(l) for g, l in phy_groups().items()}
    rec['ctrl'] = {}
    for cs in strips:
        st = cs.name.split('_', 1)[1]
        ph = by[f'phy_{st}']
        if ph.orient in ('MX', 'R180') or abs((ph.y - cs.y) - 71.28) > 1e-3:
            raise ValueError(f'v5 ctrl: {ph.name} {ph.orient} at dy {ph.y - cs.y:.3f}: the per-PC PHY pin plan assumes '
                             f'an unflipped PHY 71.28 um above the strip end')
        px = ph.x + ph.w - 0.096 if ph.orient == 'MY' else ph.x + 0.096
        kc = v.Inst(f'ctrlkc_{st}', 'qkd_ctrl_kc', cs.x, cs.y, cs.w, round(KC_H - S, 4), cs.orient, kind=cs.kind,
                    region=cs.region, domain=cs.domain)
        new = [kc]
        for k in range(NPC):
            new.append(v.Inst(f'ctrlpc_{st}_{k}', 'qkd_ctrl_pc', cs.x, round(cs.y + KC_H + PC_H * k, 4), cs.w,
                              round(PC_H - S, 4), cs.orient, kind=cs.kind, region=cs.region, domain=cs.domain))
            v.PIN_POS_EXTRA[(ph.name, f'*dfi:{k}')] = (px, ph.y + gy[str(k)])
            ties.append((f'ctrlpc_{st}_{k}', 'pc', 5, k))
        # Closed controller leaves occupy their actual outlines inside the inherited strip pitches.
        for leaf in new:
            view = view_pins(leaf.master)
            if view is not None:
                lw, lh = view[:2]
                if lw > leaf.w + 0.03 or lh > leaf.h + 0.03:
                    raise ValueError(f'controller closed view {leaf.master} does not fit strip slot')
                if ph.x > cs.x:
                    leaf.x = round(leaf.x + leaf.w - lw, 4)
                leaf.w, leaf.h = lw, lh
        v.PIN_POS_EXTRA[(ph.name, '*dfi:req')] = (px, ph.y + gy['req'])
        # r10: the PHY's own clock / reset pins (real abstract, not re-pinned): the reset tree ended its branch at
        # the instance centre, 1.7 mm from the pin (pinreg audit of run g0: 4 reset nets over 500 um)
        for pn_, yy_ in _phy_fixed_pins().items():
            v.PIN_POS_EXTRA[(ph.name, pn_)] = (px, ph.y + yy_)
        ties.append((f'ctrlpc_{st}_{NPC - 1}', 'rqi', 311, 0))          # request chain end: idle
        nb = []
        for b, c, n, e in B:
            if not any(x[0] == cs.name for x in e):
                nb.append((b, c, n, e))
                continue
            if c == 'phy_dfi':
                continue
            e2 = []
            for inst, port in e:
                if inst != cs.name:
                    e2.append((inst, port))
                    continue
                mm = re.fullmatch(r'c(\d+)([io])', port)
                if mm:
                    e2.append((f'ctrlpc_{st}_{mm.group(1)}', 'c' + mm.group(2)))
                elif port in ('kc', 'ck', 'rsi'):
                    e2.append((kc.name, port))
                elif port == 'pll_hbm':
                    e2 += [(kc.name, 'pll_hbm')]
                elif port == 'hrst':
                    e2 += [(kc.name, 'hrst')]
                else:
                    raise ValueError(f'v5 ctrl: {cs.name}.{port} on {b} has no leaf port')
            if b.startswith('clk_hbm_'):
                e2 += [(f'ctrlpc_{st}_{k}', 'hclk') for k in range(NPC)]
            elif b.startswith('rst_hbm_'):
                e2 += [(f'ctrlpc_{st}_{k}', 'h_arst_n') for k in range(NPC)]
            nb.append((b, c, n, e2))
        B = nb
        for k in range(NPC):
            B.append((f'dfi_{st}_{k}', 'phy_dfi', 278, [(f'ctrlpc_{st}_{k}', 'phy'), (ph.name, f'*dfi:{k}')]))
            up = f'ctrlpc_{st}_{k - 1}' if k else kc.name
            B.append((f'kcc_{st}_{k}', 'hbm_cdc', 33, [(up, 'kco'), (f'ctrlpc_{st}_{k}', 'kci')]))
            B.append((f'rqc_{st}_{k}', 'hbm_cdc', 311, [(f'ctrlpc_{st}_{k}', 'rqo'), (up, 'rqi')]))
        B.append((f'dfi_{st}_req', 'phy_dfi', 311, [(kc.name, 'req'), (ph.name, '*dfi:req')]))
        drop_insts([cs.name])
        m['insts'] += new
        rec['ctrl'][st] = dict(strip=[cs.x, cs.y, cs.w, cs.h], kc=kc.name, pc=NPC)
    by = {i.name: i for i in m['insts']}

    # g7 measured hot cut: x3 shares a 260-um window beside the PLL with kvn and embedding (0.676).
    # Give that word a separate western lane; the next build still judges every adjacent cut and hop.
    pll_lane = by.get('pll')
    if pll_lane is not None:
        v.DIE_LANE_WINDOWS = {'x3': dict(x=round(pll_lane.x - 216.0, 4),
                                          y0=round(pll_lane.y - 50.0, 4),
                                          y1=round(pll_lane.y + pll_lane.h + 50.0, 4))}
        rec['die_lane_windows'] = v.DIE_LANE_WINDOWS

    # ---------------------------------------------------------------- T18 reset sequencer leaves, new reset nets
    # qwen-split compute die (2026-10-14): no PLL on this die; the KV/system die forwards clock + reset over the D2D bump
    # pair (r22k ckb_rom / rs_bump), so the compute reset leaf qfd_rstseq takes rst_fwd_s from the bump synchroniser
    pll, ck = by.get('pll'), by['clk_rx']
    rr = v.Inst('rstseq_rom', 'qfd_rstseq', round(v.up(ck.x + ck.w + 4.32, v.GX), 4), ck.y, 54.0 - S, 54.0 - S,
                kind='ctl', region='hub', domain='stream_1p2')
    if pll is not None:
        # r9: qkd_rstseq is the CLOSED leaf (qkd_rstseq-kc1-b4a0a3156, 21.6 x 21.6); its reset input is por_n (PLL lock)
        rk = v.Inst('rstseq', 'qkd_rstseq', round(v.dn(pll.x - RSTSEQ_KV - 4.32, v.GX), 4), pll.y, RSTSEQ_KV, RSTSEQ_KV,
                    kind='ctl', region='kv_centre', domain=pll.domain)
        split.setdefault('qkd_rstseq', {})['rsi'] = [('por_n', 1)]
        m['insts'] += [rk, rr]
    else:
        m['insts'] += [rr]
    nb, ckr = [], False
    for b, c, n, e in B:
        if b == 'rst_fwd_s':
            e = [('rstseq', 'rso_fwd'), ('rstseq_rom', 'rsi')] if pll is not None else [('rs_bump', 'rso_f'), ('rstseq_rom', 'rsi')]
        else:
            e = [('rstseq', p) if (i, p[:4]) == ('pll', 'rso_') else ('rstseq_rom', p) if (i, p[:4]) == ('clk_rx', 'rso_')
                 else (i, p) for i, p in e]
        if b == 'clk_core_c' and pll is not None:
            e = e + [('rstseq', 'ck')]
        if re.fullmatch(r'clk_r\d+', b) and not ckr:
            e, ckr = e + [('rstseq_rom', 'ck')], True
        nb.append((b, c, n, e))
    B = nb
    if pll is not None:
        B.append(('pll_lock', 'spine_local', 1, [('pll', 'lock'), ('rstseq', 'rsi')]))
    # r9: the two ROM-side reset roots (seq_su, tt_ctlm) are resets like rst_field / rst_spine: class 'reset', so a root
    # farther than the reach from its sink becomes a registered repeater tree (_reset_tree), not a 1-b data relay chain
    # (run b2: rst_seq_ctlm, 17 data relays, ended on tt_ctlm's area pin at the block centre: no relay site in reach)
    B = [(b, 'reset' if b in ('rst_seq', 'rst_seq_ctlm', 'rst_fwd_s') else c, n, e) for b, c, n, e in B]
    field = [(i.name, 'rst_n') for i in m['insts'] if i.master in STATIONS or i.master == 'qfd_tile_nk']
    spine = [(i.name, 'rst_n') for i in m['insts'] if i.master in ('qfd_sp_res_ser', 'qfd_tt_up4', 'qfd_crom_g',
                                                                    'qfd_su_cbuf_g')
             or (SPLIT_COMPUTE and i.master.startswith('qfd_port_tiles_'))]   # v1.3: static slab RTL has rst_n
    B += [('rst_field', 'reset', 1, [('rstseq_rom', 'rso_f')] + field),
          ('rst_spine', 'reset', 1, [('rstseq_rom', 'rso_s')] + spine)]
    rec['reset'] = dict(rst_field=len(field), rst_spine=len(spine), leaves=(['rstseq'] if pll is not None else []) + ['rstseq_rom'])

    # ---------------------------------------------------------------- T21 ROM IO
    # (a) host SerDes = the re-shaped abstract, E edge kept; its FDI pins are on the W face, so the two SerDes clusters W
    #     of it move IO_STRIP_DX further W: the freed strip holds the last relays of host_fdi (2,089 b at FW 1,043)
    hp = by.get('serdes_host')
    io_rec = dict(host=None, pairs=[])
    if hp is not None and hp.master == HOST_PHY[0]:
        old = [hp.x, hp.y, hp.w, hp.h]
        xe = hp.x + hp.w
        hp.w, hp.h = HOST_PHY[1], HOST_PHY[2]
        hp.x = round(v.dn(xe - hp.w, v.GX), 4)
        moved = []
        for i in m['insts']:
            if i.master == 'qfd_io_serdes' and i.x < hp.x:
                i.x = round(i.x - IO_STRIP_DX, 4)
                moved.append(i.name)
        strip = hp.x - max(i.x + i.w for i in m['insts'] if i.master == 'qfd_io_serdes' and i.x < hp.x)
        v.HOST_FDI_DROP_X = round(hp.x - strip / 2, 3)
        B = [(b, c, FDI_BITS if b == 'host_fdi' else n, e) for b, c, n, e in B]
        io_rec['host'] = dict(old=old, new=[hp.x, hp.y, hp.w, hp.h], moved_w=moved, dx=IO_STRIP_DX, strip_um=round(strip, 3),
                              fdi_bits=FDI_BITS, fdi='W face M4 y 600-700.344')
    # (b) the link clusters' words: c / r = data + valid with the flow, credit against it (a paired bus: the credit rides
    #     the word's relay frames); + rst_n (reset tree rst_io) and fault (to the crossing FIFO block)
    ion = {i.name: i for i in m['insts'] if i.master in IO_CLUSTERS}
    nb = []
    for b, c, n, e in B:
        if c == 'io' and len(e) == 2 and any(x[0] in ion and x[1] in ('c', 'r') for x in e):
            # the die bundle keeps its port name (the IO pin plans of the base generator are keyed by it); the view ports
            # are its split: <p> = {<p>_v, <p>_d[n-1:0]}, <p>_r = <p>_cr
            (i0, p0), (i1, p1) = e
            nb.append((b, c, n + 1, [(i0, p0), (i1, p1)]))
            nb.append((b + '_cr', c, 1, [(i1, p1 + '_r'), (i0, p0 + '_r')]))
            pair[b] = b + '_cr'
            for i_, p_ in e:
                mn = next(q.master for q in m['insts'] if q.name == i_)
                split.setdefault(mn, {})[p_] = [(p_ + '_d', n), (p_ + '_v', 1)]
                split.setdefault(mn, {})[p_ + '_r'] = [(p_ + '_cr', 1)]
                if (mn, p_, n) not in io_rec['pairs']:
                    io_rec['pairs'].append((mn, p_, n))
        else:
            nb.append((b, c, n, e))
    B = nb
    if ion:
        B.append(('rst_io', 'reset', 1, [('rstseq_rom', 'rso_io')] + [(k, 'rst_n') for k in sorted(ion)]))
        for k, nm in enumerate(sorted(ion)):
            B.append((f'io_flt_{k}', 'io', 1, [(nm, 'fault'), ('io_xfifo', f'lf{k}')]))
    rec['io'] = io_rec

    # ---------------------------------------------------------------- T7 station word: _d / _r pairs, tap, tie
    nb, npair = [], 0
    for b, c, n, e in B:
        if c in ('corridor', 'head_chain') and len(e) == 2:
            (i0, p0), (i1, p1) = e
            nb.append((b, c, DW, [(i0, p0 + '_d'), (i1, p1 + '_d')]))
            nb.append((b + '_rdy', c, 1, [(i1, p1 + '_r'), (i0, p0 + '_r')]))
            pair[b] = b + '_rdy'
            npair += 1
        elif c == 'tap' and len(e) == 2:
            (i0, p0), (i1, p1) = e
            s_, t_ = ((i0, p0), (i1, p1)) if by[i0].master in STATIONS else ((i1, p1), (i0, p0))
            nb.append((b, c, DW, [(s_[0], 'tap_d'), (t_[0], 'tap')]))
            ties.append((s_[0], 'tap_r', 1, 1))
        else:
            nb.append((b, c, n, e))
    B = nb
    rec['station_word'] = dict(pairs=npair, data_bits=DW, tap_r_tied_high=sum(1 for t in ties if t[1] == 'tap_r'))

    # ---------------------------------------------------------------- Real ectl leaves (qkd_ectl3 exact wiring)
    old_ec = {i.name: i for i in m['insts'] if i.master == 'qkd_ectl'}
    leaves = {}
    for nm, ec in old_ec.items():
        _, st, eng = nm.split('_')
        cfg = (int(eng) << 2) | ('WS', 'WN', 'ES', 'EN').index(st)
        # Mirror the whole three-leaf row, preserving its local A|B|C order.
        offset = 0.0
        leaves[nm] = {}
        for part, width in zip('abc', (254.88, 254.88, 138.24)):
            x = ec.x + (648.0 - offset - width if ec.orient in ('MY', 'R180') else offset)
            it = v.Inst(nm + '_' + part, 'qkd_ectl_' + part, round(x, 4), ec.y,
                        width, 129.6, ec.orient, kind=ec.kind, region=ec.region, domain=ec.domain)
            leaves[nm][part] = it.name
            m['insts'].append(it)
            ties.append((it.name, 'cfg', 5, cfg))
            offset += width
    nb = []
    equal_groups = m.setdefault('relay_equal_groups', {})
    for bid, cls, bits, eps in B:
        src = [(i, p) for i, p in eps if i in old_ec]
        if src and src[0][1] in ('t0', 't1'):
            assert len(src) == 1 and bits == 1559, (bid, bits, src)
            nm, t = src[0]
            equal_groups[bid] = [bid + '_' + suffix for suffix in ('a', 'b', 'cl', 'q')]
            for suffix, part, port, width in (('a', 'a', t + '_row', 512), ('b', 'b', t + '_row', 512),
                                              ('cl', 'b', t + '_cl', 16), ('q', 'c', t + '_q', 519)):
                ends = [(leaves[nm][part], port)] + [(i, 'ti_' + suffix) for i, p in eps if i != nm]
                nb.append((bid + '_' + suffix, cls, width, ends))
        else:
            ends = []
            for i, port in eps:
                if i not in old_ec:
                    ends.append((i, port))
                elif port in ('ck', 'rst_n'):
                    ends += [(leaves[i][q], port) for q in 'abc']
                else:
                    part = 'a' if port in ('rq', 'rs') else 'c'
                    ends.append((leaves[i][part], port))
            nb.append((bid, cls, bits, ends))
    for nm, parts in leaves.items():
        a, b, c = (parts[q] for q in 'abc')
        for tag, width, ends in (('rs_ab', 513, [(a, 'rs_o'), (b, 'rs_i')]),
                                 ('rvm_ab', 1, [(a, 'rvm_o'), (b, 'rvm_i')]),
                                 ('x_ba', 52, [(b, 'x_o'), (a, 'x_i')]),
                                 ('x_cb', 52, [(c, 'x_o'), (b, 'x_i')]),
                                 ('rsv_bc', 1, [(b, 'rsv_o'), (c, 'rsv_i')])):
            nb.append((nm + '_' + tag, 'stack_local', width, ends))
    drop_insts(old_ec)
    B = nb
    rec['ectl_leaves'] = dict(slots=len(old_ec), leaves=3 * len(old_ec), cfg='{engine[2:0], stack[1:0]}',
                             exact_reference='rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv:qkd_ectl3',
                             head_word='{C.q[518:0], B.cl[15:4], B.row, A.row, B.cl[3:0]}')
    m['buses'] = B

    # ---------------------------------------------------------------- KV relays inside a moved / grown block are torn
    torn = _tear_overlapped(v, m)
    rec['torn_kv_chains'] = torn
    if torn:
        m.setdefault('tp8b_kv', {}).setdefault('torn_chains', []).extend(torn)

    # ---------------------------------------------------------------- qwen-split compute die: contract slot table
    if getattr(G, 'TP8', None) and G.TP8.get('split') == 'compute':
        sys.path.insert(0, str(HERE.parent / 'qwen_split'))
        import compute_spine as _CS
        rec['split_compute'] = _CS.place(v, m, G)
        B = m['buses']
    # ---------------------------------------------------------------- overlap / outline gate
    ins = sorted(m['insts'], key=lambda i: i.x)
    ov = []
    for a_ in range(len(ins)):
        p = ins[a_]
        for b_ in range(a_ + 1, len(ins)):
            q = ins[b_]
            if q.x >= p.x + p.w - 1e-3:
                break
            if q.y < p.y + p.h - 1e-3 and p.y < q.y + q.h - 1e-3:
                ov.append((p.name, q.name))
    W, H = m['die']['w'], m['die']['h']
    out = [i.name for i in ins if i.x < -1e-3 or i.y < -1e-3 or i.x + i.w > W + 1e-3 or i.y + i.h > H + 1e-3]
    rec.update(n_overlaps=len(ov), overlaps=ov[:20], outside=out[:20])
    if ov or out:
        raise SystemExit(f'tp8b v5: {len(ov)} overlaps {ov[:8]}, {len(out)} outside {out[:6]}')
    # SPEC F2: the 33-mm reticle axis is W-E; area alone cannot admit F1 or a grown slot.
    area = W * H / 1e6
    rec['reticle'] = dict(width_um=W, height_um=H, area_mm2=area,
                          limits=dict(width_um=33000.0, height_um=26000.0, area_mm2=858.0))
    if W > 33000.0 + 1e-6 or H > 26000.0 + 1e-6 or area > 858.0 + 1e-6:
        raise SystemExit(f'tp8b v5: die {W:.3f} x {H:.3f} um ({area:.6f} mm2) exceeds '
                         'SPEC F2 33000 x 26000 um / 858 mm2 reticle')

    peers = {}
    for b, c, n, e in m['buses']:
        if c in ('clock_trunk', 'reset'):
            continue
        for j, (i, p) in enumerate(e):
            peers.setdefault((i, p.lstrip('*')), []).extend(x[0] for q, x in enumerate(e) if q != j)
    _wrap(v, m, G, peers)
    # r9: a kept KV chain with a hop over the reach on the FINAL pins (a leaf re-seated, a view's real pins adopted) is
    # handed to the relay plan whole, like a chain with a relay inside a block
    pos = G._pin_pos(v, m)
    from pair_check import Gate
    clock_net = {(i, p.lstrip('*')): re.sub(r'_r\d+$', '', b)
                 for b, c, n, es in m['buses'] if c == 'clock_trunk' for i, p in es}
    pair_gate = Gate(default_um=G.RELAY_REACH_UM, buses=m['buses'], clock_net=clock_net)
    by_final = {i.name: i for i in m['insts']}
    far = set()
    for b, c, n, e in m['buses']:
        if c.endswith('@kv') and len(e) == 2:
            (xa, ya), (xb, yb) = pos(*e[0]), pos(*e[1])
            (ia, pa), (ib, pb) = e
            limit = pair_gate.limit(ia, by_final[ia].master, pa, ib, by_final[ib].master, pb)
            if abs(xa - xb) + abs(ya - yb) > min(G.RELAY_REACH_OK, limit - 10.0):
                far.add(b.split('__r')[0])
    if far:
        t2 = _tear_overlapped(v, m, far)
        rec['torn_kv_chains_over_reach'] = t2
        m.setdefault('tp8b_kv', {}).setdefault('torn_chains', []).extend(t2)
    # A rebuilt chain must also put its first/last relay inside the measured real endpoint reach.
    # The interim relay has the pair gate's documented default residual; only exact view-bound limits tighten it.
    tight = dict(getattr(v, 'TERMINAL_TIGHT', {}))
    for b, c, n, es in m['buses']:
        if len(es) != 2 or c in ('clock_trunk', 'reset') or c.endswith('@kv'):
            continue
        (ia, pa), (ib, pb) = es
        for endpoint, outgoing in ((es[0], True), (es[1], False)):
            inst, port = endpoint
            master = by_final[inst].master
            limit = (pair_gate.limit(inst, master, port, '__relay__', '__relay__', 'b') if outgoing else
                     pair_gate.limit('__relay__', '__relay__', 'a', inst, master, port))
            if 0 < limit < G.RELAY_REACH_OK:
                tight[tuple(endpoint)] = min(tight.get(tuple(endpoint), float('inf')), max(1.0, limit - 10.0))
    v.TERMINAL_TIGHT = tight
    rec['pair_terminal_limits'] = {f'{i}.{p}': d for (i, p), d in sorted(tight.items())}
    return rec


ALIGN_GAP_UM = 30.0
LEAF_DX, LEAF_GAP = 38.016, 8.64     # kvwq leaf under its CDC leaf (see apply(): pin alignment at the die)


def align_abutted(v, model, M, pw, split, rec):
    """r9 (coordinator 2026-10-13, die pin-readiness audit / tools/hier_contract/pin_align.py): two blocks that face
    each other across less than ALIGN_GAP_UM exchange a bundle PIN TO PIN: the follower's port takes, bit for bit, the
    anchor's pin positions (no jog, bit order kept), so nothing has to be jogged in a channel that is not there.
    Anchor = the closed view (VIEWS), else the master with more instances, else the driver; a follower that is a closed
    view is never moved (both closed: reported as a pin re-plan candidate, reroute_reason die_window).  A follower port
    is moved only when every instance pair asks for the same master-local positions."""
    byi = {i.name: i for i in model['insts']}
    count = {}
    for i in model['insts']:
        count[i.master] = count.get(i.master, 0) + 1
    tabs = {}

    def pins_of(mn):
        if mn not in tabs:
            mst = M[mn]
            t = {}
            for nm, layer, r in v.pin_rects(mst, 1, {q: pw.get((mn, q), 0) for q in mst.order}):
                mm = re.fullmatch(r'(.*)\[(\d+)\]', nm)
                base, k = (mm.group(1), int(mm.group(2))) if mm else (nm, 0)
                t.setdefault(base, {})[k] = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, layer)
            tabs[mn] = t
        return tabs[mn]

    def to_die(i, x, y):
        return (i.x + (i.w - x if i.orient in ('MY', 'R180') else x), i.y + (i.h - y if i.orient in ('MX', 'R180') else y))

    def to_local(i, X, Y):
        x, y = X - i.x, Y - i.y
        return (i.w - x if i.orient in ('MY', 'R180') else x, i.h - y if i.orient in ('MX', 'R180') else y)
    want, both_closed, skipped = {}, {}, {}
    for b, c, n, e in model['buses']:
        if len(e) != 2 or c.split('@')[0] in ('clock_trunk', 'reset') or c == 'phy_dfi':
            continue
        (ia, pa), (ib, pb) = e
        if ia not in byi or ib not in byi or pa.startswith('*') or pb.startswith('*'):
            continue
        A, B = byi[ia], byi[ib]
        if A.master not in M or B.master not in M:
            continue
        gx = max(A.x - (B.x + B.w), B.x - (A.x + A.w))
        gy = max(A.y - (B.y + B.h), B.y - (A.y + A.h))
        ox = min(A.x + A.w, B.x + B.w) - max(A.x, B.x)
        oy = min(A.y + A.h, B.y + B.h) - max(A.y, B.y)
        if 0.0 <= gx <= ALIGN_GAP_UM and oy > 0:
            axis = 'x'
        elif 0.0 <= gy <= ALIGN_GAP_UM and ox > 0:
            axis = 'y'
        else:
            continue
        rank = lambda i_, drv: (0 if i_.master in VIEWS and view_pins(i_.master) else 1, -count[i_.master], 0 if drv else 1)   # noqa: E731
        (an, ap_), (fo, fp) = ((A, pa), (B, pb)) if rank(A, True) <= rank(B, False) else ((B, pb), (A, pa))
        if fo.master in VIEWS and view_pins(fo.master):
            both_closed.setdefault((an.master, ap_, fo.master, fp), []).append(b)
            continue
        if ap_ in PERM.get(an.master, {}) or fp in PERM.get(fo.master, {}):
            continue
        src = pins_of(an.master).get(ap_)
        if not src or len(src) < n or any(k not in src for k in range(n)):
            skipped[(fo.master, fp)] = f'anchor {an.master}.{ap_} has {len(src or ())} of {n} pins'
            continue
        if axis == 'x':
            fdie = 'W' if fo.x >= an.x + an.w - 1e-6 else 'E'
        else:
            fdie = 'S' if fo.y >= an.y + an.h - 1e-6 else 'N'
        fl = fdie
        if fo.orient in ('MY', 'R180'):
            fl = {'E': 'W', 'W': 'E'}.get(fl, fl)
        if fo.orient in ('MX', 'R180'):
            fl = {'N': 'S', 'S': 'N'}.get(fl, fl)
        # the anchor's pins must stand on its face toward the follower
        edge = {'W': an.x + an.w, 'E': an.x, 'S': an.y + an.h, 'N': an.y}[fdie]
        pos, ok = [], True
        for k in range(n):
            X, Y = to_die(an, src[k][0], src[k][1])
            if abs((X if axis == 'x' else Y) - edge) > 1.0:
                ok = False
                break
            lx, ly = to_local(fo, X, Y)
            pos.append(round(ly if axis == 'x' else lx, 4))
        if not ok:
            skipped[(fo.master, fp)] = f'{an.master}.{ap_} is not on the face toward {fo.master}'
            continue
        L = fo.h if axis == 'x' else fo.w
        if min(pos) < 0.05 or max(pos) > L - 0.05:
            skipped[(fo.master, fp)] = f'{an.master}.{ap_} pins run past the {fo.master} face ({min(pos):.2f}..{max(pos):.2f} of {L:.2f})'
            continue
        want.setdefault((fo.master, fp), set()).add((fl, src[0][2], tuple(pos), an.master + '.' + ap_))
    done = {}
    for (mn, p), opts in sorted(want.items()):
        if len({(o[0], o[2]) for o in opts}) != 1:
            skipped[(mn, p)] = f'{len(opts)} different positions asked by its instances'
            continue
        fl, layer, pos, who = next(iter(opts))
        lay_ = layer if layer in ('M4', 'M5', 'M6', 'M7') and (layer in ('M5', 'M7')) == (fl in 'NS') else ('M5' if fl in 'NS' else 'M4')
        # every pin on the follower's own track lattice (the anchor's pins are on ITS lattice in ITS frame: up to half a
        # pitch apart, 24-32 nm): a master with pins off one lattice has no legal origin (track-lattice gate)
        off_, pt_ = v.TRK[lay_]
        sn = [round(off_ + round((q_ - off_) / pt_) * pt_, 4) for q_ in pos]
        if len(set(sn)) != len(sn):
            skipped[(mn, p)] = f'{who}: two pins fall on one {lay_} track of the follower'
            continue
        M[mn].ports[p] = ('pins', len(sn), fl, lay_, sn, 1)
        done[f'{mn}.{p}'] = who
    rec.update(aligned=done, skipped={f'{k[0]}.{k[1]}': q for k, q in sorted(skipped.items()) if f'{k[0]}.{k[1]}' not in done},
               both_closed={f'{k[0]}.{k[1]} -> {k[2]}.{k[3]}': len(q) for k, q in sorted(both_closed.items())})


def _tear_overlapped(v, m, over=()):
    """a kept KV chain ('<cl>@kv' segments, relays as placed on the KV die) with a relay frame inside a block of this
    die is handed to _relays whole (its relays dropped, one bus source -> sink of the plain class)"""
    blocks = [i for i in m['insts'] if not i.master.startswith(('qkd_rly', 'qfd_rly'))]
    BK = 500.0
    grid = {}
    for i in blocks:
        for gx in range(int(i.x // BK), int((i.x + i.w) // BK) + 1):
            for gy in range(int(i.y // BK), int((i.y + i.h) // BK) + 1):
                grid.setdefault((gx, gy), []).append(i)
    bad = set()
    for r in m['insts']:
        if not r.master.startswith('qkd_rly'):
            continue
        for gx in range(int(r.x // BK), int((r.x + r.w) // BK) + 1):
            for gy in range(int(r.y // BK), int((r.y + r.h) // BK) + 1):
                for i in grid.get((gx, gy), ()):
                    if i.x < r.x + r.w - 1e-3 and r.x < i.x + i.w - 1e-3 and i.y < r.y + r.h - 1e-3 and r.y < i.y + i.h - 1e-3:
                        bad.add(r.name)
    over = set(over)          # r9: chains named by the caller (a hop over the reach after a pin / slot move)
    if not bad and not over:
        return []
    rl = {i.name for i in m['insts'] if i.master.startswith('qkd_rly')}
    chains = {}
    for j, (b, c, n, e) in enumerate(m['buses']):
        if c.endswith('@kv') and len(e) == 2:
            chains.setdefault(b.split('__r')[0], []).append(j)
    torn, drop_b, drop_i, add = [], set(), set(), []
    for b0, idxs in sorted(chains.items()):
        mem = {x[0] for j in idxs for x in m['buses'][j][3]}
        if not (mem & bad) and b0 not in over:
            continue
        segs = sorted((m['buses'][j] for j in idxs), key=lambda s_: (int(s_[0].split('__r')[1]) if '__r' in s_[0] else 0))
        torn.append(b0)
        drop_b |= set(idxs)
        drop_i |= mem & rl
        add.append((b0, segs[0][1][:-3], segs[0][2], [segs[0][3][0], segs[-1][3][-1]]))
    left = bad - drop_i
    if left:
        raise SystemExit(f'tp8b v5: {len(left)} kept KV relays inside a block belong to no 2-pin chain: {sorted(left)[:6]}')
    m['buses'] = [b for j, b in enumerate(m['buses']) if j not in drop_b] + add
    # multi-pin nets (clock trunks) lose the dropped relays
    m['buses'] = [(b, c, n, [x for x in e if x[0] not in drop_i]) if len(e) != 2 else (b, c, n, e) for b, c, n, e in m['buses']]
    m['insts'] = [i for i in m['insts'] if i.name not in drop_i]
    return torn


DEOVERLAP_PARENTS = ('qfd_sp_vector_memory_par',)


def _deoverlap_faces(mst, pin_rects, gap=0.5):
    """Move only the movable 'face' groups that actually overlap another pin (rect level) to the nearest free span of
    their own face edge / layer; every other pin stays where it is.  Fails closed."""
    eps = 1e-6

    def edge(r):
        x0, y0, x1, y1 = r
        return ('E' if x1 >= mst.w - eps else 'W' if x0 <= eps else 'N' if y1 >= mst.h - eps else
                'S' if y0 <= eps else None)

    def rects(only=None, skip=None):
        wm = {p: (sp[1] if (only is None or p == only) and p != skip else 0) for p, sp in mst.ports.items()}
        return pin_rects(mst, 1, wm)

    def overlapping_ports():
        by = {}
        for nm, layer, r in rects():
            by.setdefault(layer, []).append((r, nm.rsplit('[', 1)[0]))
        bad = set()
        for layer, rs in by.items():
            rs.sort()
            for i, ((x0, y0, x1, y1), p) in enumerate(rs):
                for (u0, v0, u1, v1), q in rs[i + 1:]:
                    if u0 >= x1:
                        break
                    if p != q and v0 < y1 and y0 < v1:
                        bad.add((p, q))
        return bad

    moved = []
    for _ in range(64):
        # pairs of two non-face (fragment / explicit) pins are not this pass's: the case's PIN_OVERLAP gate counts the
        # emitted widths and stays the verdict
        bad = {pq for pq in overlapping_ports() if any(mst.ports.get(x, ('x',))[0] == 'face' for x in pq)}
        if not bad:
            return moved
        cand = sorted({p for pq in bad for p in pq if mst.ports.get(p, ('x',))[0] == 'face' and p not in moved},
                      key=lambda p: mst.ports[p][1])
        if not cand:
            raise ValueError(f'{mst.name}: overlapping pins {sorted(bad)[:4]} have no movable face group')
        p = cand[0]
        sp = mst.ports[p]
        mine = rects(only=p)
        f, layer = sp[2], mine[0][1]
        ax = (1, 3) if f in 'EW' else (0, 2)
        a = min(r[ax[0]] for _, _, r in mine); b = max(r[ax[1]] for _, _, r in mine)
        along = mst.h if f in 'EW' else mst.w
        occ = sorted((r[ax[0]] - gap, r[ax[1]] + gap) for nm, l, r in rects(skip=p) if l == layer and edge(r) == f)
        free, cur = [], 1.0
        for lo, hi in occ:
            if lo > cur:
                free.append((cur, lo))
            cur = max(cur, hi)
        free.append((cur, along - 1.0))
        span = b - a
        best = None
        for lo, hi in free:
            if hi - lo < span:
                continue
            x = min(max(a, lo), hi - span)
            if best is None or abs(x - a) < abs(best - a):
                best = x
        if best is None:
            raise ValueError(f'{mst.name}: no free {span:.2f}-um span on {f} {layer} for {p}')
        mst.ports[p] = sp[:4] + (sp[4] + (best - a),) + sp[5:]
        moved.append(p)
    raise ValueError(f'{mst.name}: pin re-pack did not converge')


def _wrap(v, m, G, peers):
    import contract_v4_tp8 as V4
    base_m, base_pw, base_pr, base_case = v.masters, v.port_widths, v.pin_rects, v.case_real
    ties = m['ties']
    split = m['port_split']
    join_plan = m.get('port_join', JOIN)
    S = v.SHAVE
    plan_cache = {}

    def lay(f):
        return 'M5' if f in 'NS' else 'M4'

    def replan(model, M, inst_name, ports=None, skip=(), keep_extra=None):
        """single-instance master: the named face ports (default: all with a die peer) go to the die face toward their
        peer, ordered by the peer's projection; the instance orientation is applied (MX: N <-> S, MY: E <-> W)"""
        it = next(i for i in model['insts'] if i.name == inst_name)
        mst = M[it.master]
        if inst_name not in plan_cache:
            byi = {i.name: i for i in model['insts']}
            want = {}
            for p, sp in mst.ports.items():
                if sp[0] != 'face' or p in skip or (ports is not None and p not in ports):
                    continue
                pp = [byi[x] for x in peers.get((inst_name, p), ()) if x in byi and not x.startswith('rly_')]
                if not pp:
                    continue
                o = pp[0]
                ox, oy = o.x + o.w / 2, o.y + o.h / 2
                dxo = max(it.x - ox, 0.0, ox - (it.x + it.w))
                dyo = max(it.y - oy, 0.0, oy - (it.y + it.h))
                if dyo >= dxo:
                    f, a = ('N' if oy > it.y + it.h / 2 else 'S'), ox - it.x
                else:
                    f, a = ('E' if ox > it.x + it.w / 2 else 'W'), oy - it.y
                # die face / die-local coordinate -> master face / master-local coordinate
                if it.orient in ('MX', 'R180'):
                    f = {'N': 'S', 'S': 'N'}.get(f, f)
                    if f in 'EW':
                        a = it.h - a
                if it.orient in ('MY', 'R180'):
                    f = {'E': 'W', 'W': 'E'}.get(f, f)
                    if f in 'NS':
                        a = it.w - a
                want[p] = (f, a)
            plan_cache[inst_name] = want
        want = plan_cache[inst_name]
        for f in 'NSEW':
            L = mst.w if f in 'NS' else mst.h
            mine = [p for p, (ff, _) in want.items() if ff == f]
            if not mine:
                continue
            keep = [(sp[4] - sp[1] * 0.048 * sp[5] / 2, sp[4] + sp[1] * 0.048 * sp[5] / 2)
                    for p, sp in mst.ports.items() if sp[0] == 'face' and sp[2] == f and p not in want]
            keep += list((keep_extra or {}).get(f, ()))
            items = [(p, mst.ports[p][1] * 0.048, min(max(want[p][1], 4.0), L - 4.0)) for p in mine]
            for p, c in _pack(L, items, keep).items():
                mst.ports[p] = ('face', mst.ports[p][1], f, lay(f), round(c, 4), 1)

    def add_face(mst, port, bits, f, centre, pitch=1, layer=None):
        if port in mst.ports:
            mst.ports.pop(port)
            mst.order[:] = [q for q in mst.order if q != port]
        mst.face(port, bits, f, layer or lay(f), centre, pitch)

    def masters(model, k=1, port_bits=None):
        # Legacy frame clock planning cannot mirror M8 pins; these two frames are
        # replaced by closed M5 pins below, so construct their disposable frame R0.
        frame_model = dict(model)
        frame_model['insts'] = [copy.copy(i) if i.master in ('qfd_su_cbuf_g', 'qfd_crom_g', 'qfd_tile_nl', 'qfd_sp_vector_memory_par')
                                or (SPLIT_COMPUTE and i.master.startswith('qfd_port_tiles_')) else i
                                for i in model['insts']]
        for i in frame_model['insts']:
            if i.master in ('qfd_su_cbuf_g', 'qfd_crom_g') or (SPLIT_COMPUTE and i.master.startswith('qfd_port_tiles_')):
                # Native source-exact static slab pins and49clock entries are
                # rebuilt by final(); legacy M8 mirror planning is disposable.
                i.orient = 'R0'
            elif i.master == 'qfd_tile_nl':
                i.master = 'qfd_tile_nk'  # base frame shape; actual node-less ports below
        # Legacy frame constructors use the historical VM spelling. Generate only
        # its disposable geometric frame, then expose the NEW parallel source master.
        parallel_vm = any(i.master == 'qfd_sp_vector_memory_par' for i in model['insts'])
        if parallel_vm:
            for i in frame_model['insts']:
                if i.master == 'qfd_sp_vector_memory_par':
                    i.master = 'qfd_sp_vector_memory'
        frame_bits = dict(port_bits or {})
        if parallel_vm:
            frame_bits.update({('qfd_sp_vector_memory', p): n
                for (mst, p), n in (port_bits or {}).items() if mst == 'qfd_sp_vector_memory_par'})
        M = base_m(frame_model, k, frame_bits)
        if parallel_vm:
            vm_frame = M.pop('qfd_sp_vector_memory')
            vm_frame.name = 'qfd_sp_vector_memory_par'
            vm_frame.note += ' | NEW PAR_RB=1 source specialization; geometric frame only, no inherited physical view'
            M[vm_frame.name] = vm_frame
        byi = {i.name: i for i in model['insts']}
        Master = type(next(iter(M.values())))
        # Every real leaf master uses the same outline as its placed instance.
        for mn in ('qkd_kvwq_ctl_bin', 'qkd_ctrl_pc', 'qkd_ctrl_kc'):
            q = M.get(mn)
            it = next((i for i in model['insts'] if i.master == mn), None)
            if q is not None and it is not None:
                q.w, q.h = it.w, it.h
        # ---- T7 stations / heads / tile
        for cell, faces in STATIONS.items():
            q = M.get(cell)
            if q is None:
                continue
            for f, (b, d) in faces.items():
                L = q.w if f in 'NS' else q.h
                sl = V4.band(L, DW + 3)
                mid = (DW + 3) // 2
                data = sl[:mid] + sl[mid + 2:-1]
                if b in q.ports:
                    q.ports.pop(b)
                    q.order[:] = [x for x in q.order if x != b]
                q.ports[b + '_d'] = ('pins', DW, f, lay(f), data, 1)
                q.ports[b + '_r'] = ('pins', 1, f, lay(f), [sl[-1]], 1)
                q.order += [b + '_d', b + '_r']
                if f == 'N':
                    q.ports['rst_n'] = ('pins', 1, 'N', 'M5', [sl[mid + 1]], 1)
                    q.order.append('rst_n')
        # ---- split compute C7: distributed x slice masters (compute_spine._dvm instances; generated pins on the same
        # 2-track slot grid as the station family, the die assigns them in OUT/pins)
        if SPLIT_COMPUTE and _os.environ.get('OT_SPLIT_DVM', '1') != '0':
            sys.path.insert(0, str(HERE.parent / 'qwen_split'))
            import compute_spine as _CS
            byi_ = {}
            for i in model['insts']:
                byi_.setdefault(i.master, i)

            def mk_ports(q, spec):
                for f, items in spec.items():
                    L = q.w if f in 'NS' else q.h
                    n = sum(b_ + 1 for _, b_ in items)
                    sl = V4.band(L, n + 2)
                    k_ = 1
                    for nm, b_ in items:
                        q.ports[nm + '_d' if b_ > 1 else nm] = ('pins', b_, f, lay(f), sl[k_:k_ + b_], 1)
                        q.order.append(nm + '_d' if b_ > 1 else nm)
                        k_ += b_
                        if b_ > 1:
                            q.ports[nm + '_r'] = ('pins', 1, f, lay(f), [sl[k_]], 1)
                            q.order.append(nm + '_r')
                        k_ += 1
            for mn, flow in (('qfd_xcst_s', 'S'), ('qfd_xcst_n', 'N')):
                it = byi_.get(mn)
                if it is None:
                    continue
                q = Master(mn, it.w, it.h, 3, 'DVM corridor station (rtl/qwen_sys/dvm_20261014 ot_qfd_xslice_slots.sv)')
                mk_ports(q, {'N': [('a', _CS.XCOR_D)], 'S': [('b', _CS.XCOR_D)], 'W': [('tap', DW)]})
                q.ports['rst_n'] = ('pins', 1, 'E', 'M4', [V4.snap(q.h / 2)], 1)
                q.order.append('rst_n')
                M[mn] = q
            for mn in ('qfd_xcol_w', 'qfd_xcol_e'):
                it = byi_.get(mn)
                if it is None:
                    continue
                q = Master(mn, it.w, it.h, 7, 'DVM column cluster: ot_qfd_xhead + 8 x qfd_xs_leaf (two write chains), M7 cap')
                mk_ports(q, {'N': [('n', _CS.XCOR_D)], 'S': [('s', _CS.XCOR_D)], 'W': [('w', _CS.XHEAD_D)],
                             'E': [('e', _CS.XHEAD_D)]})
                q.ports['rst_n'] = ('pins', 1, 'N', 'M5', [V4.snap(q.w - 2.0)], 1)
                f_out, f_in = ('E', 'W') if mn.endswith('_w') else ('W', 'E')
                q.ports['fault'] = ('pins', 1, f_out, 'M4', [V4.snap(2.0)], 1)
                q.ports['fault_i'] = ('pins', 1, f_in, 'M4', [V4.snap(2.0)], 1)
                q.order += ['rst_n', 'fault', 'fault_i']
                M[mn] = q
            it = byi_.get('qfd_xs_tap')
            if it is not None:
                q = Master('qfd_xs_tap', it.w, it.h, 7, 'DVM x tap at the VM write face (ot_qfd_xs_tap + go/ib, two head words)')
                mk_ports(q, {'W': [('sw', _CS.TAP_SW)], 'N': [('hw', _CS.XHEAD_D)], 'E': [('he', _CS.XHEAD_D)],
                             'S': [('aw', _CS.TAP_AW), ('gi', _CS.TAP_GI), ('xpf', _CS.TAP_PF)]})
                for nm in ('sw', 'aw', 'gi', 'xpf'):
                    q.ports[nm] = q.ports.pop(nm + '_d'); q.ports.pop(nm + '_r')
                    q.order[:] = [x for x in q.order if x not in (nm + '_d', nm + '_r')] + [nm]
                q.ports['fault'] = ('pins', 1, 'E', 'M4', [V4.snap(2.0)], 1)
                q.ports['rst_n'] = ('pins', 1, 'E', 'M4', [V4.snap(4.0)], 1)
                q.ports['hw_f'] = ('pins', 1, 'E', 'M4', [V4.snap(6.0)], 1)
                q.ports['he_f'] = ('pins', 1, 'E', 'M4', [V4.snap(8.0)], 1)
                q.order += ['fault', 'rst_n', 'hw_f', 'he_f']
                # Real native216 tap: all S-face groups need disjoint ranges,
                # and the replacement master must retain its actual clock pin.
                # aw was previously packed as a data/ready pair before removal,
                # overlapping gi after its width changed; assign exact windows.
                q.ports['aw'] = ('face', _CS.TAP_AW, 'S', 'M5', 50.0, 2)
                q.ports['gi'] = ('face', _CS.TAP_GI, 'S', 'M5', 111.0, 2)
                q.ports['xpf'] = ('face', _CS.TAP_PF, 'S', 'M5', 155.0, 2)
                q.face('ck', 1, 'N', 'M5', 12.96, 1)
                M['qfd_xs_tap'] = q
            # f45805040 static die wrappers expose data and faults only.  The
            # compiler reserves slots; no ready pin survives in the abstract.
            for mn in ('qfd_xcst_n','qfd_xcst_s','qfd_xcol_e','qfd_xcol_w','qfd_xs_tap'):
                q = M.get(mn)
                if q is not None:
                    for pn in list(q.ports):
                        if pn.endswith('_r'):
                            q.ports.pop(pn)
                    q.order[:] = [pn for pn in q.order if pn in q.ports]
        t = M.get('qfd_tile_nk')
        if t is not None:
            sp = t.ports['tap']
            t.ports['tap'] = (sp[0], DW) + tuple(sp[2:])
            add_face(t, 'rst_n', 1, sp[2], sp[4] - 30.0, 2)
            if any(i.master == 'qfd_tile_nl' for i in model['insts']):
                nt = Master('qfd_tile_nl', t.w, t.h, t.obs_top, t.note + ' | real node-less tile')
                nt.ports = {p: sp for p, sp in t.ports.items() if p not in ('n_a', 'n_b', 'n_y')}
                nt.order = [p for p in t.order if p in nt.ports]
                M['qfd_tile_nl'] = nt
        # ---- T8 cdc_wleaf
        q = M.get('qkd_cdc_wleaf')
        if q is not None:
            sc = CDC_WH / q.w
            q.w = q.h = CDC_WH
            for p, sp in list(q.ports.items()):
                if sp[0] == 'face':
                    q.ports[p] = sp[:4] + (min(round(sp[4] * sc, 4), CDC_WH - sp[1] * 0.048 * sp[5] / 2 - 1.0),) + sp[5:]
        # ---- T9 rhead cluster
        q = M.get('qkd_rhead')
        if q is not None:
            r = Master('qkd_rhead', RHEAD_WH[0], RHEAD_WH[1], 7, q.note + ' | contract v4 T9: hardened-once cluster 691.2 x '
                       '453.6 (16 x ot_qkh_lane8 + ot_qkh_ktree, 43.2-um centre relay channel)')
            x = 217.0
            for p, pitch in (('rst_n', 2), ('e', 2), ('s', 2), ('ti', 2)):
                n = q.ports[p][1]
                r.face(p, n, 'S', 'M5', x + n * 0.048 * pitch / 2, pitch)
                x += n * 0.048 * pitch + 2.0
            assert x <= 475.2, x
            r.face('nb', q.ports['nb'][1], 'E', 'M6', 226.8, 2)
            # M5 and M7 have incompatible mirrored x residues (2*12 vs 2*16 nm mod16).
            # The unclosed head clock port follows its S-word M5 lattice; parent internal cap stays M7.
            r.face("ck", 1, "N", "M5", 356.4, 1)
            M['qkd_rhead'] = r
            # r9: the engine-control leaf's head pins follow the head's S-face window.  An ectl serves 2 heads below
            # (far, near) and 2 above (near, far); a far head's e / s / ti pin is one head (457.9 um) away, so its ectl
            # pin must stand straight above / below it (run b2: 150 / 138 / 105 um of x offset = 608 / 596 / 564 um pin
            # to pin on 192 nets).  The near heads' e / s pins sit beside the far ones (11 / 7 um).
            ec = M.get('qkd_ectl')
            if ec is not None:
                dx = RHEAD_WH[0] - RHEAD_OLD_W           # head-local x - dx = ectl-local x (both orientations)
                xe, xs, xt = (round(r.ports[p][4] - dx, 4) for p in ('e', 's', 'ti'))
                for p, c in (('e0', xe), ('e3', xe), ('s0', xs), ('s3', xs), ('t0', xt), ('t1', xt),
                             ('e1', xe - 11.0), ('e2', xe - 11.0), ('s1', xe - 7.0), ('s2', xe - 7.0)):
                    sp = ec.ports[p]
                    ec.ports[p] = sp[:4] + (round(c, 4),) + sp[5:]
        # ---- T22b merged KV sequencer (cluster 604.8 x 475.2, leaves M5, parent M6 / M7)
        q, it = M.get('qkd_seq'), byi.get('seq')
        if q is not None and it is not None and abs(it.w - SEQ_WH[0]) < 0.1:
            r = Master('qkd_seq', SEQ_WH[0], SEQ_WH[1], 7, q.note + ' | contract v5 T22b: merged-die sequencer cluster '
                       '604.8 x 475.2 (core + 4 xs + 4 fan leaves M5, parent wires M6 / M7); gq / gr / rf / tf / d2df / '
                       't_flt dropped; hc 182 b / tk 93 b raw step pins; x3 one pool of 40 credits')
            nbits = lambda p: (SEQ_BITS.get({'r_x3': 'x3', 't_ar': 'attn_ret', 'r_kvd': 'o4_kvd', 'ar': 'ares'}.get(p, p))
                               or (q.ports[p][1] if p in q.ports else 1))
            PB = dict(r_sd=56, t_ds=187, t_pw=75, kst=10, hf=1, hs=1)

            def run(face, at, names, step=1, pitch=2):
                # consecutive face groups from `at` (step +1: upward, -1: downward along the face), 2.0 um apart
                for p in names:
                    n = PB.get(p) or nbits(p)
                    span = n * 0.048 * pitch
                    c = at + step * span / 2
                    r.face(p, n, face, lay(face), round(c, 4), pitch)
                    at += step * (span + 2.0)
                return at
            eg = byi.get('embgw')
            lo = (eg.x - it.x) if eg is not None and eg.y > it.y else SEQ_WH[0] / 2
            hi = (eg.x + eg.w - it.x) if eg is not None and eg.y > it.y else SEQ_WH[0] / 2
            # N: ROM-side words on either side of the gateway (W of it the two 0.5-kb words, E of it the control words)
            e1 = run('N', lo - 1.5, ('t_ar', 'r_x3'), -1)
            assert e1 >= 1.0, e1
            e2 = run('N', hi + 3.0, ('r_sd', 'r_kvd', 't_ds', 't_pw'))
            r.face('ck', 1, 'N', 'M7', round(e2 + 6.0, 4), 1)
            assert e2 + 8.0 <= SEQ_WH[0], e2
            # W / E: quadrant words, the S quadrant's below the N quadrant's; E starts above the host words
            # (r10 run g2: with the two 1-kb kvn words low on the face both took the row gap under the host, beside the
            # host link: cut 0.64 at x 16,650 -- they stay at the top of the face as on the v4 frame, the attention
            # words below them)
            for f, y0 in (('W', 6.0), ('E', 6.0)):
                if f == 'E':
                    y0 = run('E', y0, ('tk', 'hc', 'kst')) + 6.0
                y1 = run(f, y0, (f'af_{f}S', f'mf_{f}S', f'af_{f}N', f'mf_{f}N', f'aq_{f}N', f'aq_{f}S'))
                y2 = run(f, SEQ_WH[1] - 4.0, (f'kc_{f}S', f'kc_{f}N', f'kvn_{f}S', f'kvn_{f}N'), -1)
                assert y2 >= y1 + 4.0, (f, y1, y2)
            # S: the hub's words (ar follows the hub's ao pins: align_abutted), reset beside them
            ah, hub = byi.get('ahub'), M.get('qkd_ahub')
            if ah is not None and hub is not None and hub.ports.get('ao', ('',))[0] == 'face' and hub.ports['ao'][2] == 'N':
                d = it.x - ah.x                       # hub-local x - d = sequencer-local x (the cluster is narrower)
                ao = hub.ports['ao']
                c = ao[4] - d
                assert c - ao[1] * 0.048 * ao[5] / 2 >= 1.0, c
                r.face('ar', ao[1], 'S', 'M5', round(c, 4), ao[5])
                hx = ao[4] + ao[1] * 0.048 * ao[5] / 2 + 3.0
                for k_, p_ in enumerate(('hf', 'hs')):          # single wires: both ends at one x inside the cluster's span
                    add_face(hub, p_, 1, 'N', round(hx + 2.0 * k_, 4), 1)
                    r.face(p_, 1, 'S', 'M5', round(hx + 2.0 * k_ - d, 4), 1)
            else:
                run('S', 30.0, ('hf', 'hs', 'ar'), pitch=1)
            r.face('rst_n', 1, 'S', 'M5', 100.0, 1)
            M['qkd_seq'] = r
            # the host's step words leave on its E face too (its N face is abutted by the hub: no relay site in front),
            # below the ingest words; one relay beside the hub joins the two E faces
            hm = M.get('qkd_host')
            if hm is not None:
                occ = [sp[4] - sp[1] * 0.048 * sp[5] / 2 for p_, sp in hm.ports.items()
                       if sp[0] == 'face' and sp[2] == 'E' and p_ not in ('hc', 'tk', 'kst')]
                at = min(occ, default=hm.h - 6.0) - 4.0
                for p_, n_ in (('hc', 182), ('tk', 93), ('kst', 10)):
                    span = n_ * 0.096
                    add_face(hm, p_, n_, 'E', round(at - span / 2, 4), 2)
                    at -= span + 2.0
        for mn in ('qkd_astk', 'qkd_astk_n'):
            q = M.get(mn)
            hh = {round(i.h, 4) for i in model['insts'] if i.master == mn}
            if q is not None and len(hh) == 1:
                q.h = hh.pop()
        # ---- T12 res_ser
        q = M.get('qfd_sp_res_ser')
        if q is not None:
            q.w, q.h = 777.6, 518.4
            add_face(q, 'rst_n', 1, 'N', 392.0, 1)
            # r9: me_en on E beside the head leaf (the N face is abutted by the port slab: run f2 found no relay site in
            # reach of an N-face pin at x 396)
            add_face(q, 'me_en', 1, 'E', 330.0, 1)
            add_face(q, 'fault', 1, 'E', 360.0, 1)
        # ---- T13 tt_up4 / tt_ctlm sel, rst_n; T15 crom; cbuf rst_n
        for mn in ('qfd_tt_up4', 'qfd_tt_ctlm'):
            q = M.get(mn)
            if q is not None and 'sel' in q.ports:
                sp = q.ports['sel']
                q.ports['sel'] = (sp[0], SEL_BITS) + tuple(sp[2:])
        q = M.get('qfd_tt_up4')
        if q is not None:
            add_face(q, 'rst_n', 1, 'N', 176.0, 1)
        q = M.get('qfd_crom_g')
        if q is not None:
            q.h = round(next(i.h for i in model['insts'] if i.master == 'qfd_crom_g'), 4)
            add_face(q, 'rst_n', 1, 'N', 180.0, 1)
        q = M.get('qfd_su_cbuf_g')
        if q is not None:
            add_face(q, 'rst_n', 1, 'N', 185.0, 1)
        M.pop('qfd_tt_up4_g', None)
        # The closed ROM views own their pin plans. Static straps are die constants.
        for mn, straps in (('qfd_su_cbuf_g', (('grp', 3), ('f_lat', 5))),
                           ('qfd_crom_g', (('crom_lb', 6), ('fault_code', 2)))):
            q = M.get(mn)
            if q is not None:
                for pn, width in straps:
                    add_face(q, pn, width, 'N' if mn == 'qfd_crom_g' else 'S', 4.0 + width, 1)
        # ---- T16 control strip leaves
        cs = M.get('qkd_ctrl')
        note = 'KV control strip leaf (contract v5 T16, el1013-qwen-kvstrips 08:06)'
        pc = Master('qkd_ctrl_pc', cs.w if cs is not None else 247.512, PC_H - S, 5, note + ': per-PC controller = head + '
                    'pcport KVW 2 + kcmd tap, PC id as a strap; registers at every pin')
        pc.face('ci', 319, 'W', 'M4', 161.27 - KC_H, 1)
        pc.face('co', 294, 'W', 'M4', 300.25 - KC_H, 1)
        pc.face('phy', 278, 'E', 'M4', PC_PHY_Y, 2)
        pc.face('kci', 33, 'S', 'M5', 40.0, 2)
        pc.face('kco', 33, 'N', 'M5', 40.0, 2)
        pc.face('rqo', 311, 'S', 'M5', 150.0, 2)
        pc.face('rqi', 311, 'N', 'M5', 150.0, 2)
        pc.face('pc', 5, 'W', 'M4', 20.0, 2)
        pc.area('hclk', 1, pc.w / 2, pc.h / 2, 1)
        pc.area('h_arst_n', 1, pc.w / 2 + 1.6, pc.h / 2, 1)
        M['qkd_ctrl_pc'] = pc
        kc = Master('qkd_ctrl_kc', pc.w, KC_H - S, 5, note + ': kc async FIFO (core -> hclk), HBM clock / reset entry, '
                    'PHY request port')
        kc.face('kc', 33, 'S', 'M5', 123.76, 1)
        kc.face('kco', 33, 'N', 'M5', 40.0, 2)
        kc.face('rqi', 311, 'N', 'M5', 150.0, 2)
        kc.face('req', 311, 'E', 'M4', 22.0, 1)
        kc.area('ck', 1, 196.0, 10.0, 1)
        kc.area('rsi', 1, 198.0, 10.0, 1)
        kc.area('pll_hbm', 1, 200.0, 10.0, 1)
        kc.area('hrst', 1, 202.0, 10.0, 1)
        M['qkd_ctrl_kc'] = kc
        M.pop('qkd_ctrl', None)
        M.pop('qkd_ctrl_n', None)
        # ---- T18 reset sequencer leaves; PLL lock
        rk = Master('qkd_rstseq', RSTSEQ_KV, RSTSEQ_KV, 5, 'ot_qwen_sys_rst_seq (KV centre): PLL lock in (por_n), one '
                    'registered reset root per quadrant + centre + forward; closed leaf qkd_rstseq-kc1-b4a0a3156 (its '
                    'boot_* / link_up / soft_rst / rst_st ports have no die net yet: open item, kvcentre)')
        rk.face('ck', 1, 'N', 'M5', RSTSEQ_KV / 2, 1)
        rk.face('rsi', 1, 'W', 'M4', RSTSEQ_KV / 2, 1)
        for j, p in enumerate(('rso_WS', 'rso_WN', 'rso_ES', 'rso_EN', 'rso_c', 'rso_fwd')):
            rk.face(p, 1, 'E' if j % 2 else 'S', 'M4' if j % 2 else 'M5', 3.0 + 3.0 * j, 1)
        M['qkd_rstseq'] = rk
        rr = Master('qfd_rstseq', 54.0 - S, 54.0 - S, 5, 'ot_qwen_sys_rst_seq (ROM side): forwarded reset in, roots for '
                    'seq_su, tt_ctlm, the tile field and the spine blocks')
        rr.face('ck', 1, 'N', 'M5', 27.0, 1)
        rr.face('rsi', 1, 'W', 'M4', 27.0, 1)
        for j, p in enumerate(('rso_seq', 'rso_ctlm', 'rso_f', 'rso_s', 'rso_io')):
            rr.face(p, 1, 'E' if j % 2 else 'S', 'M4' if j % 2 else 'M5', 12.0 + 8.0 * j, 1)
        M['qfd_rstseq'] = rr
        q = M.get('qkd_pll')
        if q is not None and 'lock' not in q.ports:
            q.area('lock', 1, q.w / 2, q.h / 2 + 8.0, 1)
        # ---- T21 ROM IO: paired link words, cluster rst_n / fault, host PHY abstract outline + W-face FDI
        iorec = (model.get('tp8b_v5') or {}).get('io') or {}
        io_pairs(model, M)
        for mn in IO_CLUSTERS:
            q = M.get(mn)
            if q is not None:
                add_face(q, 'fault', 1, 'N', 120.0, 1)
                add_face(q, 'rst_n', 1, 'N', 122.0, 1)
        q = M.get('qfd_io_xfifo')
        if q is not None:
            for j_ in range(sum(1 for i in model['insts'] if i.master in IO_CLUSTERS)):
                add_face(q, f'lf{j_}', 1, 'N', 4.0 + 2.0 * j_, 1)
        q = M.get(HOST_PHY[0])
        if q is not None and iorec.get('host'):
            h = Master(HOST_PHY[0], HOST_PHY[1], HOST_PHY[2], q.obs_top, q.note + ' | contract v5 T21: re-shaped abstract '
                       '(physical/qwen_missing_phy/tp8_1013), RXD 512, FDI on the W face M4')
            h.face('clk', 1, 'W', 'M4', FDI_Y0 + 0.012, 1)
            h.face('rst_n', 1, 'W', 'M4', FDI_Y0 + FDI_STEP + 0.012, 1)
            h.face('fdi', FDI_BITS, 'W', 'M4', FDI_Y0 + 2 * FDI_STEP + FDI_BITS * FDI_STEP / 2, 1)
            for p in q.order:
                if p not in h.ports and p in q.ports and p not in ('fdi', 'clk', 'rst_n'):
                    h.ports[p] = q.ports[p]
                    h.order.append(p)
            M[HOST_PHY[0]] = h
        # ---- T14: the mirrored group keeps R0; its N / S pin faces swap (same x)
        for mn in ('qfd_sp_su64_sfu',):
            q = M.get(mn)
            if q is None:
                continue
            for p, sp in list(q.ports.items()):
                if sp[0] == 'face' and sp[2] in 'NS' and p not in ('va', 'vq'):
                    q.ports[p] = sp[:2] + ('S' if sp[2] == 'N' else 'N',) + sp[3:]
        # ---- T10 / T14 / T17: VM region, SU, seq_su, control tile: pins toward their peers on the final placement
        vmm = M.get(byi['sp_vector_memory'].master)
        if vmm is not None:
            vi, si = byi['sp_vector_memory'], byi['sp_su64_sfu']
            sx, sy = VM_ENV['w'] / vmm.w, VM_ENV['h'] / vmm.h
            n = Master(vmm.name, VM_ENV['w'], VM_ENV['h'], VM_OBS_TOP, vmm.note + ' | contract v4 T10: region of hardened '
                       'leaves 4708.8 x 2347.92; pins toward their peers (faces provisional until the leaves close)')
            for p in dict.fromkeys(vmm.order):
                sp = vmm.ports.get(p)
                if sp is None or p in ('xw', 'xe', 'ckx'):
                    continue
                if sp[0] == 'area':
                    n.ports[p] = (sp[0], sp[1], round(sp[2] * sx, 3), round(sp[3] * sy, 3)) + tuple(sp[4:])
                else:
                    n.ports[p] = sp
                n.order.append(p)
            # C4 split compute + distributed x slices: the trimmed VM has no x head-root words (xw / xe) and no ib
            # (the tree top's go / ib goes to the x tap); compute_spine._dvm re-routes those buses
            dvm = SPLIT_COMPUTE and _os.environ.get('OT_SPLIT_DVM', '1') != '0'
            if not dvm:
                for p in ('xw', 'xe'):
                    n.face(p + '_d', DW, 'S', 'M5', 0.0, 1)
                    n.face(p + '_r', 1, 'S', 'M5', 0.0, 1)
                if 'ib' not in n.ports:
                    n.face('ib', 380, 'S', 'M5', 0.0, 1)
                else:
                    n.ports['ib'] = ('face', 380) + tuple(n.ports['ib'][2:])
            elif 'ib' in n.ports:
                n.ports.pop('ib')
                n.order[:] = [x for x in n.order if x != 'ib']
            M[vmm.name] = n
            # ready pins ride beside their data group: planned as one group, then split
            replan(model, M, 'sp_vector_memory', skip=('sa', 'sq') + (() if dvm else ('xw_r', 'xe_r')),
                   keep_extra={'N': [(si.x - vi.x - 4.0, si.x + si.w - vi.x + 4.0)]})
            for p in (() if dvm else ('xw', 'xe')):
                d = n.ports[p + '_d']
                n.ports[p + '_r'] = ('face', 1, d[2], d[3], round(d[4] + DW * 0.048 / 2 + 0.6, 4), 1)
            # split compute C9 (compute lead r3): the attention-return word from the link adapter (N die edge) enters the
            # trimmed VM on its N face at the E end, beyond the SU seam, the constant group and the x tap (one vertical
            # run up the spine's E channel).  The peer-facing replan left it on the S face (C3: 22 relay stages around
            # the VM / SU block; every stage is one cycle of the attention layer, LINK.md fit)
            if SPLIT_COMPUTE and 'ar' in n.ports and _os.environ.get('OT_SPLIT_VM_AR_N', '1') != '0':
                sp = n.ports['ar']
                n.ports['ar'] = ('face', sp[1], 'N', 'M5', round(n.w - 100.0, 4), 1)
                n.ports['ar_cr'] = ('face', 1, 'N', 'M5', round(n.w - 100.0 + sp[1] * 0.048 / 2 + 0.6, 4), 1)
                if 'ar_cr' not in n.order:
                    n.order.append('ar_cr')
        for inst, mn, kw in (('seq_su', 'qfd_seq_su', {}),
                             ('sp_su64_sfu', 'qfd_sp_su64_sfu', dict(ports=('si', 'sd', 'acc', 'q', 'eq', 'ea', 'ecr'))),
                             ('tt_ctlm', 'qfd_tt_ctlm', None)):
            q = M.get(mn)
            if q is None or inst not in byi:
                continue
            if mn == 'qfd_seq_su':
                for p in ('ib', 'dflt'):
                    if p in q.ports:
                        q.ports.pop(p)
                        q.order[:] = [x for x in q.order if x != p]
                for p, nbit in (('dc', 56), ('dh', 187), ('cc', 518)):
                    q.ports[p] = ('face', nbit) + tuple(q.ports[p][2:])
            if mn == 'qfd_tt_ctlm':
                q.face('ib', 380, 'N', 'M5', 0.0, 1)
                for j in range(3):
                    q.face(f'mer{j}', 1, 'W', 'M4', 0.0, 1)
                    q.face(f'rf{j}', 1, 'W', 'M4', 0.0, 1)
                add_face(q, 'rsi', 1, 'W', 944.0, 1)     # r9: reset entry at the W face (was an area pin at the centre)
                kw = dict(ports=tuple(p for p in q.ports if 'sp_vector_memory' in peers.get((inst, p), ())
                                      or 'xs_tap' in peers.get((inst, p), ()) or p.startswith(('mer', 'rf'))))
            replan(model, M, inst, **kw)
        if SPLIT_COMPUTE and _os.environ.get('OT_SPLIT_LINK_WORDS', '1') != '0':
            # split compute C10 (compute lead r3): link words at the real RTL widths (compute_spine.LINK_BITS) and the
            # two word credits as their own 1-b pins beside their words (qfd_d2d_rom = romlink + llr)
            lb = dict(x3=524, ar=520, fdi=1169, kvd=44)
            d2 = M.get('qfd_d2d_rom')
            if d2 is not None:
                for p_, nb_ in lb.items():
                    if p_ in d2.ports:
                        d2.ports[p_] = (d2.ports[p_][0], nb_) + tuple(d2.ports[p_][2:])
                for p_, w_ in (('x3', 'x3_cr'), ('ar', 'ar_cr')):
                    sp = d2.ports[p_]
                    d2.ports[w_] = ('face', 1, sp[2], sp[3], round(sp[4] + sp[1] * 0.048 * sp[5] / 2 + 0.6, 4), 1)
                    if w_ not in d2.order:
                        d2.order.append(w_)
            ph_ = M.get('ot_qkvd_ucie_x64_phy')
            if ph_ is not None and 'fdi' in ph_.ports:
                ph_.ports['fdi'] = (ph_.ports['fdi'][0], 1169) + tuple(ph_.ports['fdi'][2:])
            su_ = M.get('qfd_sp_su64_sfu')
            if su_ is not None and 'q' in su_.ports:
                sp = su_.ports['q']
                su_.ports['q'] = (sp[0], 524) + tuple(sp[2:])
                if sp[0] == 'face':
                    su_.ports['q_cr'] = ('face', 1, sp[2], sp[3], round(sp[4] + 524 * 0.048 * sp[5] / 2 + 0.6, 4), 1)
                    if 'q_cr' not in su_.order:
                        su_.order.append('q_cr')
            sq_ = M.get('qfd_seq_su')
            if sq_ is not None and 'kvd' in sq_.ports:
                sq_.ports['kvd'] = (sq_.ports['kvd'][0], 44) + tuple(sq_.ports['kvd'][2:])
            vmm_ = M.get(byi['sp_vector_memory'].master)
            if vmm_ is not None and 'ar' in vmm_.ports:
                vmm_.ports['ar'] = (vmm_.ports['ar'][0], 520) + tuple(vmm_.ports['ar'][2:])
        # v1.2 (compute lead r4, 21:4x): contract straps are REAL pins of the receiving master.  C14's abstracts had no
        # tile_id / sidx / tids / b0 / lnk pins at all, so the case silently dropped those die connections; every strap
        # port of the ties list that the master model lacks gets a face group in the nearest free window of the face
        # that carries the master's rst_n, and (compute_spine TIE_SELF) its two 1-b tie_hi / tie_lo outputs beside it.
        _CSm = sys.modules.get('compute_spine')
        if _CSm is not None and SPLIT_COMPUTE:
            tie_ports = {}
            mof = {i.name: i.master for i in model['insts']}
            for inst, port, bits, val in model.get('ties', []):
                mn_ = mof.get(inst)
                if (mn_, port) in _CSm.STRAP_PORTS:
                    tie_ports.setdefault(mn_, {})[port] = max(bits, tie_ports.get(mn_, {}).get(port, 0))

            def _spans(q_, side):
                out = []
                for p_, sp in q_.ports.items():
                    if sp[0] == 'face' and sp[2] == side:
                        hw = sp[1] * 0.048 * sp[5] / 2
                        out.append((sp[4] - hw, sp[4] + hw))
                    elif sp[0] == 'pins' and sp[2] == side:
                        out += [(x - 0.05, x + 0.05) for x in sp[4]]
                return sorted(out)

            def _free(q_, side, length, near, gap=1.0):
                lim = q_.w if side in 'NS' else q_.h
                occ = _spans(q_, side)
                cands, lo = [], 2.0
                for a, b in occ + [(lim - 2.0, lim)]:
                    if a - gap - lo >= length:
                        c = min(max(near, lo + length / 2), a - gap - length / 2)
                        cands.append((abs(c - near), c))
                    lo = max(lo, b + gap)
                if not cands:
                    raise RuntimeError(f'{q_.name}: no free {length:.2f}-um window on face {side} for a strap group')
                return round(min(cands)[1], 4)

            for mn_, need in sorted(tie_ports.items()):
                q = M.get(mn_)
                if q is None:
                    continue
                rs = q.ports.get('rst_n')
                if rs is None or rs[0] not in ('face', 'pins'):
                    if mn_ in _CSm.TIE_SELF:
                        raise RuntimeError(f'{mn_}: tie_hi / tie_lo need a face rst_n to sit beside')
                    continue          # its strap pins come from the closed view's plan in final() (band_lanes b0 / lnk)
                side, layer = rs[2], rs[3]
                near = rs[4] if rs[0] == 'face' else rs[4][0]
                groups = [(p_, n_) for p_, n_ in sorted(need.items()) if p_ not in q.ports]
                if mn_ in _CSm.TIE_SELF and not ('tie_hi' in q.ports and 'tie_lo' in q.ports):
                    groups += [('tie_hi', 1), ('tie_lo', 1)]
                for p_, n_ in groups:
                    # rst_n's face first, then the other faces (xcol: its 64.8-um N face is full of n_d / n_r / rst_n)
                    for side_ in [side] + [f_ for f_ in 'EWSN' if f_ != side]:
                        lay_ = layer if side_ in (side,) or (side_ in 'NS') == (side in 'NS') else ('M5' if side_ in 'NS' else 'M4')
                        try:
                            c = _free(q, side_, n_ * 0.096, near if side_ == side else (q.w if side_ in 'NS' else q.h) / 2)
                        except RuntimeError:
                            continue
                        side, layer, near = side_, lay_, c
                        break
                    else:
                        raise RuntimeError(f'{mn_}: no face has a free {n_ * 0.096:.2f}-um window for strap {p_}')
                    q.ports[p_] = ('face', n_, side, layer, c, 2)
                    if p_ not in q.order:
                        q.order.append(p_)
        final(model, M, k)
        return M

    def io_pairs(model, M):
        """T21: a link word's credit pin stands beside the word on the same face (wherever the word's pin plan put it)"""
        for mn, p, n in ((model.get('tp8b_v5') or {}).get('io') or {}).get('pairs', ()):
            q = M.get(mn)
            if q is None or p not in q.ports:
                continue
            sp = q.ports[p]
            q.ports[p] = (sp[0], n + 1) + tuple(sp[2:])
            if sp[0] == 'face':
                add_face(q, p + '_r', 1, sp[2], sp[4] + (n + 1) * 0.048 * sp[5] / 2 + 0.6, 1, layer=sp[3])

    def final(model, M, k=1):
        """the pin rules with the last word (also run again after every other pin-plan wrapper: v.V5_FINAL_MASTERS)"""
        Master = type(next(iter(M.values())))
        for mn in ('qkd_ectl_a', 'qkd_ectl_b', 'qkd_ectl_c'):
            vp = view_pins(mn)
            if vp is None:
                raise RuntimeError(f'{mn}: real leaf view missing')
            w, h, pp = vp
            q = Master(mn, w, h, 5, 'Closed ectl leaf, exact qkd_ectl3 wiring')
            names = {}
            for pn, (face, layer, pos) in pp.items():
                mm = re.fullmatch(r'(.*)\[(\d+)\]', pn)
                base, bit = (mm.group(1), int(mm.group(2))) if mm else (pn, 0)
                names.setdefault(base, {})[bit] = (face, layer, pos)
            for pn, positions in names.items():
                got = [positions[j] for j in range(max(positions) + 1)]
                assert len({g[:2] for g in got}) == 1, (mn, pn)
                q.ports[pn] = ('pins', len(got), got[0][0], got[0][1], [g[2] for g in got], 1)
                q.order.append(pn)
            M[mn] = q
        M.pop('qkd_ectl', None)
        q = M.get('qkd_rhead')
        if q is not None and 'ti' in q.ports:
            sp = q.ports.pop('ti')
            q.order[:] = [p for p in q.order if p != 'ti']
            assert sp[0] == 'face' and sp[1] == 1559, sp
            ref = Master(q.name, q.w, q.h, q.obs_top, q.note)
            ref.ports, ref.order = {'ti': sp}, ['ti']
            rects = base_pr(ref, 1, {'ti': 1559})
            positions = [(r[0] + r[2]) / 2 if sp[2] in 'NS' else (r[1] + r[3]) / 2 for _, _, r in rects]
            for pn, (_, bits) in join_plan['qkd_rhead'].items():
                q.ports[pn] = ('pins', len(bits), sp[2], sp[3], [round(positions[j], 4) for j in bits], 1)
                q.order.append(pn)
        io_pairs(model, M)
        vrec = model.setdefault('tp8b_v5', {}).setdefault('views', {})
        if k == 1:
            pw1 = v.port_widths(model, 1)
            for mn in VIEWS:
                adopt_view(M, mn, split, vrec, pw1)
            # die lead r12 (2026-10-14): ADOPTED as the die's pin assignment for the UN-CLOSED head parent (top-down pin
            # assignment, owner 10-13 18:22): head ti / e / s pins stand straight above / below the real ectl A / B / C leaf
            # pins (g9: all 128 unrepaired te / ts paths and the 315 over-reach hops were 422-432 um of x offset between the
            # far head's pin and its ectl pin).  OT_TP8_ECTL_PIN_REPLAN_CANDIDATE=0 restores the legacy pins (diagnostic).
            import os
            if os.environ.get('OT_TP8_ECTL_PIN_REPLAN_CANDIDATE', '1') != '0':
                from qwen_tp8.ectl_pin_replan_candidate import apply as head_pin_candidate
                head_pin_candidate(model, M)
            align_abutted(v, model, M, pw1, split, model['tp8b_v5'].setdefault('pin_align', {}))
            # Actual R0 band leaves: each hard child clock enters at its
            # measured physical pin, not an arbitrary parent-center M8 pin.
            band = M.get('qfd_sp_band_lanes')
            if band is not None and SPLIT_COMPUTE:
                for j in range(16):
                    x = (25.92, 311.04, 596.16)[j % 3] + 97.02
                    y = 25.92 + 177.12 * (j // 3) + 151.158
                    band.ports[f'ck_l{j}'] = ('xy', 1, 'M5', [(round(x,4),round(y,4))], 1)
                    if f'ck_l{j}' not in band.order:
                        band.order.append(f'ck_l{j}')
                band.ports['ck'] = ('pins', 1, 'N', 'M5', [440.652], 1)
                band.ports['rst_n'] = ('pins', 1, 'S', 'M5', [20.028], 1)
                band.ports['b0'] = ('pins', 1, 'S', 'M5', [25.02], 1)
                band.ports['lnk'] = ('pins', 6, 'S', 'M5', [round(32.028+.096*j,4) for j in range(6)], 1)
                # Two4096-bit registered word faces fit at every second track,
                # below the native12pins/um limit; old single-track pads do not.
                band.ports['tw'] = ('face', 4096, 'N', 'M5', 650.0, 2)
                band.ports['ty'] = ('face', 4096, 'N', 'M5', 230.0, 2)
                # Real registered core face, toward the upper leaves in the
                # channel east of the slab stack. Legacy M8 area pads are not
                # a legal parent contract.
                band.w,band.h=881.28,1131.84
                for pn,n,centre in (('tt',1538,750.0),('pw',513,520.0),('c',26,430.0),('f',1,460.0)):
                    band.ports[pn]=('face',n,'E','M4',centre,2)
                    if pn not in band.order:band.order.append(pn)
                band.order = list(dict.fromkeys(band.order + ['b0','lnk']))
                band.obs_top = 7  # actual native cluster signalsM2-M7/PGM7, not a leaf-only M6 draft
            # v1.3 (compute lead r4): the tile parents' clock entries at their CLOSED children's measured clock-pin XY
            # (results/arch/qwen_compute_child_clocks_1014/entries.json, same form as the band leaves above), not 15
            # coincident centre pins; every master's port order de-duplicated (a port listed twice wrote its pins twice)
            if SPLIT_COMPUTE:
                ej = Path(__file__).resolve().parents[2] / 'results/arch/qwen_compute_child_clocks_1014/entries.json'
                ents = json.loads(ej.read_text())['masters'] if ej.exists() else {}
                for tn in ('qfd_tile_nk', 'qfd_tile_nl'):
                    tm = M.get(tn)
                    if tm is None or tn not in ents:
                        continue
                    for pn, ch in ents[tn]['children'].items():
                        if pn in tm.ports or pn in tm.order:
                            _sn = lambda z: round(0.012 + round((z - 0.012) / 0.048) * 0.048, 4)   # M5 / M4 track lattice
                            tm.ports[pn] = ('xy', 1, 'M5', [(_sn(ch['at'][0]), _sn(ch['at'][1]))], 1)
                            if pn not in tm.order:
                                tm.order.append(pn)
                # the x tap keeps its OFFICIAL pin plan (f757 / c15 preflight, the DVM kit physical/ref_tile/qfd_xs_tap
                # is gated on it): the C16 auto-face pass put gi / xpf on top of sw (221 overlapping M4 pins)
                tj = Path(__file__).resolve().parents[2] / 'results/arch/qwen_split_compute_1014/c15_preflight/qfd_xs_tap.json'
                tq = M.get('qfd_xs_tap')
                if tq is not None and tj.exists():
                    for pn, rec_ in json.loads(tj.read_text())['ports'].items():
                        if pn not in tq.ports and pn not in tq.order:
                            continue
                        lo_, hi_ = rec_['range_um']
                        n_ = rec_['bits']
                        pos_ = [round(lo_ + (hi_ - lo_) * j / (n_ - 1), 4) for j in range(n_)] if n_ > 1 else [lo_]
                        tq.ports[pn] = ('pins', n_, rec_['face'], rec_['layer'], pos_, 1)
                if any(i.master == 'ot_qfd_x3_mux_native' for i in model['insts']):
                    xm = Master('ot_qfd_x3_mux_native', 129.6, 129.6, 5, 'static x3 mux (kit qfd_x3_mux_nativer, CLOSED)')
                    xm.face('q', 524, 'W', 'M4', 64.8, 2)
                    xm.face('x3', 524, 'E', 'M4', 64.8, 2)
                    xm.ports['ck'] = ('pins', 1, 'N', 'M5', [V4.snap(40.0)], 1)
                    xm.ports['rst_n'] = ('pins', 1, 'N', 'M5', [V4.snap(50.0)], 1)
                    xm.order += ['ck', 'rst_n']
                    M['ot_qfd_x3_mux_native'] = xm
            if SPLIT_COMPUTE:
                from qwen_split.source_pin_plan import apply as source_pin_plan
                source_pin_plan(M)
            if model.get('direct_up4'):
                from qwen_split.direct_up4 import install_leaf_master, partition_master, MASTER, VIEW
                VIEWS[MASTER] = VIEW
                install_leaf_master(M, model, Master, view_pins(MASTER))
                band = M.get('qfd_sp_band_lanes')
                if band is not None and 'pw_l0' in band.ports:
                    # Source-exact ABI includes quarter outputs AND legacy
                    # outputs. Partition only connected real quarter bits.
                    rects=v.pin_rects(band,1,{p:sp[1] for p,sp in band.ports.items()})
                    partition_master(band,join_plan['qfd_sp_band_lanes'],rects)
                elif band is not None and 'pw' in band.ports:
                    # Four true registered quarter-valid outputs avoid an
                    # unrelayed long fanout from the legacy single valid pin.
                    pwsp=band.ports.pop('pw');band.order[:]=[p for p in band.order if p!='pw']
                    for l in range(4):
                        centre=pwsp[4]+(l-1.5)*(129*.096+.384)
                        band.face(f'pw_l{l}',129,pwsp[2],pwsp[3],centre,2)
                    fsp=band.ports.pop('f');band.order[:]=[p for p in band.order if p!='f']
                    if fsp[0]=='face':
                        band.face('f_up',4,fsp[2],fsp[3],fsp[4],2)
                    elif fsp[0]=='pins':
                        band.ports['f_up']=('pins',4,fsp[2],fsp[3],[fsp[4][0]+.096*l for l in range(4)],1)
                        band.order.append('f_up')
                    else:
                        raise ValueError('band quarter fault requires a real face pin')
                    rects = v.pin_rects(band, 1, {p:sp[1] for p,sp in band.ports.items()})
                    partition_master(band, join_plan['qfd_sp_band_lanes'], rects)
            if model.get('native_control_contract'):
                from qwen_split.native_control_contract import install_master as install_native_control
                install_native_control(M, model, Master)
            if model.get('native_static_io_bind'):
                from qwen_split.native_static_io_bind import install_master as install_static_io
                install_static_io(M, model, Master)
            if model.get('native_graph_bind'):
                from qwen_split.native_graph_bind import install_masters as install_native_graph
                install_native_graph(M, model, Master, v.pin_rects)
            if model.get('static_link_bind'):
                from qwen_split.static_link_bind import install_masters as install_static_link
                from qwen_split.direct_up4 import partition_master as _pm
                install_static_link(M, model, Master, _pm)
            if model.get('res_train_bind'):
                from qwen_split.res_train_bind import install_masters as install_res_train
                from qwen_split.direct_up4 import partition_master as _pm2
                install_res_train(M, model, Master, _pm2)
            # An added source tap can fragment already-connected non-native
            # consumers (slab tc and X tap gi). Preserve their exact real pin
            # rectangles while exposing the same numeric aliases on every peer.
            from qwen_split.direct_up4 import partition_master as _fragment_master
            for name_, aliases_ in model.get('port_join', {}).items():
                q_ = M.get(name_)
                if q_ is None:
                    continue
                pending_ = {a_: rb_ for a_, rb_ in aliases_.items() if rb_[0] in q_.ports}
                if pending_:
                    rects_ = v.pin_rects(q_, 1, {p_: sp_[1] for p_, sp_ in q_.ports.items()})
                    _fragment_master(q_, pending_, rects_)
            for mst_ in M.values():
                mst_.order[:] = list(dict.fromkeys(mst_.order))
            # Q-COMPUTE-DIE r8 (C22s): NEW unclosed parents whose face groups were laid out by several passes (default
            # faces, replan, link-word widening, native ports) can end with groups on top of each other (C22s:
            # qfd_sp_vector_memory_par write_commit_mask over ar[377..], 145 pairs). Top-down pin assignment owns
            # these pins: re-pack movable face groups along each face (fixed 'pins' fragments stay), fail closed.
            for name_ in DEOVERLAP_PARENTS:
                if name_ in M:
                    _deoverlap_faces(M[name_], v.pin_rects)

    v.V5_FINAL_MASTERS = final
    # split compute C17: band_lanes may be placed MX (band 0 stack mirrored); its clock pins are the closed native view's
    # real pins set in final(), so the generic mirror clock-pin relocation must not run for it
    v.MIRROR_CK_FINAL = (('qfd_sp_band_lanes',) + tuple(f'qfd_sp_res_train{suffix}_{b}' for suffix in ('', '_par') for b in range(3))) if SPLIT_COMPUTE else ()

    def port_widths(model, k=1):
        w = base_pw(model, k)
        byi = {i.name: i for i in model['insts']}
        live = {}
        for bid, cls, bits, eps in model['buses']:
            n = bits if k == 1 else max(1, math.ceil(bits / k))
            for inst, port in eps:
                key = (byi[inst].master, port.lstrip('*'))
                live[key] = max(live.get(key, 0), n)
        for inst, port, bits, val in ties:
            if inst in byi:
                key = (byi[inst].master, port)
                live[key] = max(live.get(key, 0), bits)
        for i_ in model['insts']:
            if i_.master in model.get('tie_self', []):
                live[(i_.master, 'tie_hi')] = live[(i_.master, 'tie_lo')] = 1
        # a port without a die net on THIS die is not emitted (the KV-die widths carried D2D faces: qkd_seq rf / tf)
        return {key: live[key] for key in set(w) | set(live) if key in live}

    def pin_rects(mst, k, wmap):
        mine = {p: sp for p, sp in mst.ports.items() if sp[0] in ('pins', 'xy')}
        if mine:
            cp = type(mst)(mst.name, mst.w, mst.h, mst.obs_top, mst.note)
            cp.ports = {p: sp for p, sp in mst.ports.items() if p not in mine}
            cp.order = [p for p in mst.order if p not in mine]
            out = base_pr(cp, k, wmap)
            depth = 0.192
            for p in dict.fromkeys(q for q in mst.order if q in mine):
                if mine[p][0] == 'xy':
                    _, n0, layer, poss, _ = mine[p]
                    exact = getattr(mst, 'assigned_fragment_rects', {}).get(p)
                    if exact is not None:
                        if len(exact) != n0:
                            raise ValueError(f'{mst.name}.{p}: incomplete assigned fragment rectangles')
                        out.extend((f'{p}[{i}]', L, r) for i, (L, r) in enumerate(exact[:wmap.get(p, n0)]))
                        continue
                    for i, (x, y) in enumerate(poss[:wmap.get(p, n0)]):
                        # >= the layer's min area (M5 2000 nm2): a 24 x 24 nm interior square had no DRT access
                        # point (C19s DRT-0073 on every interior clock entry); 24 x 96 nm along the preferred direction
                        hx, hy = (.012, .048) if layer in ('M1', 'M3', 'M5', 'M7', 'M9') else (.048, .012)
                        out.append((f'{p}[{i}]', layer, (x-hx,y-hy,x+hx,y+hy)))
                    continue
                _, n0, f, layer, poss, _ = mine[p]
                n = min(wmap.get(p, n0), len(poss))
                for i in range(n):
                    pos = poss[i]
                    hw = 0.012
                    r = {'W': (0.0, pos - hw, depth, pos + hw), 'E': (mst.w - depth, pos - hw, mst.w, pos + hw),
                         'S': (pos - hw, 0.0, pos + hw, depth), 'N': (pos - hw, mst.h - depth, pos + hw, mst.h)}[f]
                    out.append((f'{p}[{i}]', layer, r))
        else:
            out = base_pr(mst, k, wmap)
        sp_ = split.get(mst.name)
        if sp_ and k == 1 and getattr(v, 'EMIT_SPLIT', False):
            ren = {}
            for bundle, parts in sp_.items():
                j = 0
                for pn, nb in parts:
                    for b in range(nb):
                        vp = view_pins(mst.name) if mst.name in VIEWS else None
                        scalar = nb == 1 and vp is not None and pn in vp[2]
                        ren[f'{bundle}[{j}]'] = pn if scalar else f'{pn}[{b}]'
                        j += 1
                if j == 1:
                    ren[bundle] = parts[0][0]            # a 1-bit bundle emitted without an index
            out = [(ren.get(nm, nm), layer, r) for nm, layer, r in out]
        if k == 1 and getattr(v, 'EMIT_SPLIT', False):
            if mst.name in VIEWS:
                vp = view_pins(mst.name)
                if vp is not None:
                    out = [(nm[:-3] if nm.endswith('[0]') and nm[:-3] in vp[2] else nm, layer, r) for nm, layer, r in out]
            for pn, (real, bits) in join_plan.get(mst.name, {}).items():
                ren = {f'{pn}[{j}]': f'{real}[{bit}]' for j, bit in enumerate(bits)}
                out = [(ren.get(nm, nm), layer, r) for nm, layer, r in out]
        return out

    def write_netlist(model, k, path, top='qfd_die'):
        stages = model.get('r21_stage_of', {})
        for group, names in model.get('relay_equal_groups', {}).items():
            depths = {name: max(0, stages.get(name, 1) - 1) for name in names}
            if len(set(depths.values())) != 1:
                raise RuntimeError(f'{group}: split head word has unequal added relay depths: {depths}; structural pads required')
        for j, (inst, port, bits, val) in enumerate(ties):
            if port == 'f_lat':
                g = int(inst.rsplit('_', 1)[1])
                val = 8 + max(0, stages.get(f'o4_cf_a_{g}', 1) - 1) + max(0, stages.get(f'o4_cf_q_{g}', 1) - 1)
                if val > 31:
                    raise RuntimeError(f'{inst}: measured far-ROM latency {val} exceeds f_lat[4:0]')
                ties[j] = (inst, port, bits, val)
            elif port == 'lnk' and inst.startswith('sp_band_lanes_'):
                # split compute C11: the band's relay stages toward the tree top (its control word tt_lc<b>)
                b_ = int(inst.rsplit('_', 1)[1])
                val = max(0, stages.get(f'tt_lc{b_}', 1) - 1)
                if val > 63:
                    raise RuntimeError(f'{inst}: {val} relay stages exceed lnk[5:0]')
                ties[j] = (inst, port, bits, val)
        byi = {it.name: it for it in model['insts']}
        conns = {it.name: [] for it in model['insts']}
        joined = {}
        phyb = {}                                   # phy instance -> {pin base: {bit: expr}}
        V = [f'// tools/qwen_kv_die/tp8b_v5.py: die-level nets only (k = {k}); constants = straps, chain ends, tap_r',
             f'module {top} ();']
        groups = phy_groups()
        phyn = [p[0] for p in v.phy_pins()]

        def phy_all(inst, net):
            for i, pn in enumerate(phyn):
                mm = re.match(r'^(.*)\[(\d+)\]$', pn)
                b, j = (mm.group(1), int(mm.group(2))) if mm else (pn, 0)
                phyb.setdefault(inst, {}).setdefault(b, {})[j] = f'{net}[{i}]'
        for bid, cls, bits, eps in model['buses']:
            n = bits if k == 1 else max(1, math.ceil(bits / k))
            net = f'n_{bid}'
            V.append(f'  wire [{n - 1}:0] {net};')
            for inst, port in eps:
                if port.lstrip('*').startswith('dfi:') and byi[inst].master == 'ot_hbm3e_phy' and k == 1:
                    # r10: the star is gone on some paths (run r10a: '.dfi:0(...)' in die.v, STA-0171)
                    for i, (b, j) in enumerate(groups[port.lstrip('*')[4:]]):
                        phyb.setdefault(inst, {}).setdefault(b, {})[j] = f'{net}[{i}]'
                elif port == '*dfi' and k == 1:
                    phy_all(inst, net)
                else:
                    pn = port.lstrip('*')
                    parts = split.get(byi[inst].master, {}).get(pn) if k == 1 else None
                    perm = PERM.get(byi[inst].master, {}).get(pn) if k == 1 else None
                    join = join_plan.get(byi[inst].master, {}).get(pn) if k == 1 else None
                    if join:
                        real, indexes = join
                        assert len(indexes) == n, (inst, pn, n)
                        vals = joined.setdefault((inst, real), {})
                        for j, bit in enumerate(indexes):
                            assert bit not in vals, (inst, real, bit)
                            vals[bit] = f'{net}[{j}]'
                    elif perm:
                        conns[inst].append(f'.{pn}({{' + ', '.join(
                            f'{net}[{hi}:{lo}]' if hi != lo else f'{net}[{hi}]' for hi, lo in perm) + '})')
                    elif parts:
                        j = 0
                        for sub, nb in parts:
                            conns[inst].append(f'.{sub}({net}[{j + nb - 1}:{j}])')
                            j += nb
                    else:
                        conns[inst].append(f'.{pn}({net})')
        for (inst, real), vals in joined.items():
            assert set(vals) == set(range(max(vals) + 1)), (inst, real, 'incomplete join')
            conns[inst].append(f'.{real}({joined_expr(vals)})')
        tie_self = set(model.get('tie_self', []))
        tied = set()
        for inst, port, bits, val in ties:
            if inst not in conns:
                continue
            if byi[inst].master in tie_self and (byi[inst].master, port) in sys.modules['compute_spine'].STRAP_PORTS:
                # v1.2: every strap bit from the instance's own TIEHI / TIELO outputs (MSB first)
                hi, lo = f'tih_{inst}', f'til_{inst}'
                conns[inst].append(f'.{port}({{' + ', '.join(f'{hi}[0]' if (val >> b) & 1 else f'{lo}[0]' for b in range(bits - 1, -1, -1)) + '})')
                tied.add(inst)
            else:
                conns[inst].append(f".{port}({bits}'h{val:x})")
        for inst in sorted(tied):
            conns[inst] += [f'.tie_hi(tih_{inst}[0])', f'.tie_lo(til_{inst}[0])']
            V.append(f'  wire [0:0] tih_{inst};')
            V.append(f'  wire [0:0] til_{inst};')
        for inst, d in phyb.items():
            for b, bits_ in sorted(d.items()):
                hi = max(bits_)
                if hi == 0 and not any(pn.startswith(b + '[') for pn in phyn):
                    conns[inst].append(f'.{v.esc(b)}({bits_[0]})')
                else:
                    cat = ', '.join(bits_.get(j, "1'b0") for j in range(hi, -1, -1))
                    conns[inst].append(f'.{v.esc(b)}({{{cat}}})')
        for it in model['insts']:
            V.append(f'  {it.master} {it.name} (' + ', '.join(conns[it.name]) + ');')
        V.append('endmodule\n')
        Path(path).write_text('\n'.join(V))
        if model.get('master_params'):
            Path(str(path)+'.params.json').write_text(json.dumps({'masters':model['master_params']},indent=2)+'\n')

    base_phy = v.phy_pins

    def phy_pins():
        ys = phy_pin_y()
        out = []
        for pn, yc in base_phy():
            mm = re.match(r'^(.*)\[(\d+)\]$', pn)
            key = (mm.group(1), int(mm.group(2))) if mm else (pn, 0)
            out.append((pn, ys.get(key, yc)))
        return out

    def case_real(model, work):
        v.EMIT_SPLIT = True
        try:
            r = base_case(model, work)
        finally:
            v.EMIT_SPLIT = False
        f = Path(work) / 'phy_ew.lef'
        if f.exists():
            f.write_text(phy_repin(f.read_text()))
        return r

    v.masters, v.port_widths, v.pin_rects, v.write_netlist, v.phy_pins, v.case_real = \
        masters, port_widths, pin_rects, write_netlist, phy_pins, case_real
