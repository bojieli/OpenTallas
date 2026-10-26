#!/usr/bin/env python3
"""slice5_partition.py -- QW-SLICE5 (LEAD3-QW, 10-19): partition plan for the qfd_dv_slice2_w / _e rebuild as a LANDED
parent of hardened sub-clusters (Q.STA.SLICE.2).

Why: the slice2_e / slice2_wh --cts gates of record FAILED structurally (MU-DQ-SLICEKC ref_gate/*-20261019-042253): the
whole slice core (decode + SU glue + VM + station + scalar + stream) stayed SOFT on one root ck_core = 173,895 flops, the
heads glue on ck_hd = 56,306, the face landings on ck_ef / ck_wf = 13.9k each spread over 2.46 mm; CTS and GRT killed
(rc 137); 1,491 stages > 500 um (pass chains pin register -> pin register across the 2.46-mm slice in ONE edge).

This script is the plan generator (no RTL, no kit): it reads the MEASURED flop census (yosys proc + memory -nomap, stat
-width, committed under results/arch/qw_slice5_1019/census/) and writes
  results/arch/qw_slice5_1019/partition.json   leaves, regions, sinks per root, floorplan rectangles, crossings
                                               (bits, reach, landing kind, edges), cut analysis, price
  results/arch/qw_slice5_1019/floorplan_sketch.png
Usage: python3 tools/qwen_dv/slice5_partition.py [--out results/arch/qw_slice5_1019]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / 'results/arch/qw_slice5_1019/census/stat_slice2_calr_a775ac6d8.txt'
LATTICE = 43.2
W, H = 2462.376, 2591.976               # the die slot of qfd_dv_slice2_{w,e} (dv2f14bn elements.lef; kept)
# ASAP7 signal pitches (um): M3 0.036, M4/M5 0.048, M6/M7 0.064 (tools/ref_tile/spread_face_pins.py)
TR = {'M2': 1 / 0.036, 'M3': 1 / 0.036, 'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064}
AVAIL = 0.5                             # usable share after PG / blockage / via (the project's cut rule of thumb)
CUT_LIMIT = (0.55, 0.60)
REACH = 405.0
CLK_GHZ = 1.2
TOK_RATE = 5141.0                       # TOKSIM-QW 10-19 22:00 (4d2842541), 1 user, tok/s
LAYERS = 36


# ---------------------------------------------------------------------------------------------- measured census
def census(path):
    txt = path.read_text()
    mods = {}
    for blk in re.split(r'\n=== ', txt):
        m = re.match(r'(\S+) ===', blk.strip('= \n'))
        if not m:
            continue
        name = m.group(1)
        ff, subs, ports, insub = 0, {}, 0, False
        for line in blk.splitlines():
            s = line.strip()
            if s.endswith('submodules'):
                insub = True
                continue
            mm = re.match(r'(\d+)\s+(\S+)$', s)
            if re.match(r'\d+ port bits', s):
                ports = int(s.split()[0])
            if not mm:
                continue
            n, t = int(mm.group(1)), mm.group(2)
            if insub:
                subs[t] = subs.get(t, 0) + n
                continue
            c = re.match(r'\$(a?l?dffe?|s?dffc?e?|adffe|sdffce|dffsre?|aldffe?)_(\d+)$', t)
            if c:
                ff += n * int(c.group(2))
        mods[name] = dict(ff=ff, subs=subs, ports=ports)
    memo = {}

    def tot(n):
        if n not in memo:
            m = mods.get(n)
            memo[n] = 0 if m is None else m['ff'] + sum(k * tot(s) for s, k in m['subs'].items())
        return memo[n]

    def find(suffix):
        hits = [n for n in mods if re.search(suffix, n)]
        assert len(hits) == 1, (suffix, hits)
        return hits[0]
    return mods, tot, find


def snap(v):
    return round(round(v / LATTICE) * LATTICE, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'results/arch/qw_slice5_1019'))
    a = ap.parse_args()
    out = Path(a.out)
    mods, tot, find = census(CENSUS)
    M = {k: find(v) for k, v in {
        'slice2': r'^qfd_dv_slice2$', 'su8': r'qfd_dv_su8_entries$', 'su_lane': r'^qfd_dv_su_lane$',
        'vreduce': r'ot_hdc_vreduce$', 'vm': r'qfd_dv_vm\\MUT', 'stn': r'qfd_dv_redstn2\\MUT', 'sc': r'qfd_dv_scalar2$',
        'amax': r'qfd_dv_amax_mu$', 'stm': r'qfd_dv_stream\\MUT', 'tld': r'qfd_dv_slice_tload\\SLICE',
        'heads': r'\\qfd_dv_heads$', 'xhead': r'ot_qfd_xhead$', 'tap': r'ot_qfd_xs_tap$', 'leaf': r'ot_qfd_xs_leaf$',
        'exp': r'^ot_hdc_sfu_exp_t$', 'rcp': r'^ot_hdc_sfu_rcp_t$', 'rsq': r'^ot_hdc_sfu_rsq_t$'}.items()}
    ff = {k: tot(v) for k, v in M.items()}
    loc = {k: mods[v]['ff'] for k, v in M.items()}
    ports = {k: mods[v]['ports'] for k, v in M.items()}
    lane_hard = ff['su_lane'] - loc['su_lane']                      # lane_h + 3 SFU leaves (closed views)
    su8_soft = ff['su8'] - 8 * ff['su_lane'] - ff['vreduce']        # SU control + RD relays
    census_rec = {
        'source': 'a775ac6d8 (QW-PARENT-PICKUP3 CALR base of QW-TLOAD2): qfd_dv_slice2 #(SU_TLS 1, SU_LT 1, MU_NU 4, '
                  'HD_W130 1, PRIVATE_CALR 1); yosys 0.68 proc + memory -nomap, stat -width (flop BITS, hierarchical)',
        'file': str(CENSUS.relative_to(ROOT)),
        'slice_total_ff': ff['slice2'],
        'by_child': {
            'slice glue (pin regs, decode, SETID, VM write merge, chains, status)': loc['slice2'],
            'su8 SU control + RD relays (soft)': su8_soft, 'ot_hdc_vreduce (soft)': ff['vreduce'],
            'qfd_dv_su_lane glue x8 (IREG/OREG, reset)': 8 * loc['su_lane'],
            'lane_h + exp/rcp/rsq leaves x8 (HARD, closed)': 8 * lane_hard,
            'qfd_dv_vm (soft + 22 SRAM)': ff['vm'], 'qfd_dv_redstn2 monolith (-> 8 x stnrgc)': ff['stn'],
            'qfd_dv_scalar2 (soft)': ff['sc'], 'qfd_dv_amax_mu (soft)': ff['amax'],
            'qfd_dv_stream (-> stream tile t2)': ff['stm'], 'qfd_dv_slice_tload (-> tload tile, 4 ROM)': ff['tld'],
            'ot_qfd_xs_tap (soft)': ff['tap'], 'ot_qfd_xhead x4 (soft)': 4 * ff['xhead'],
            'qfd_dv_heads local': loc['heads'], 'ot_qfd_xs_leaf x32 (HARD w130)': 32 * ff['leaf']},
        'soft_before': 'gate of record: ck_core 173,895 + ck_hd 56,306 + ck_ef/ck_wf 27,770 flops on 4 roots',
    }
    # ------------------------------------------------------------------------------------------ leaves
    # util 45 %, std area ~0.7 um2 per flop bit incl. logic (measured stnrgc: 7,425 um2 std / 10,808 sinks); a leaf's
    # outline = max(area at 45 %, perimeter for its pins at <= 5 pins/um on full faces), snapped to the 43.2 lattice.
    def outline(nff, npins, macro_um2=0.0, aspect=1.0):
        a = (nff * 0.7) / 0.45 + macro_um2 * 1.6
        side_a = a ** 0.5
        side_p = npins / (4 * 5.0)
        s = max(side_a, side_p, 86.4)
        return snap(s * aspect ** 0.5), snap(s / aspect ** 0.5)
    vm_macro = 10 * 174.744 * 70.488 + 8 * 94.824 * 41.064 + 4 * 172.824 * 41.064
    leaves = [
        # name, master, count, sinks (flop bits on the leaf's own centre-fed root), state, ports (estimate), note
        dict(name='stnrgc', master='qfd_dv_redstn2_region', count=8, sinks=10808, state='CLOSED (5fb7dcb72, TT +74.64 / FF +18.08)',
             wh=(151.2, 151.2), note='8 region leaves = the stnent arrangement (2x4, 64.8 gaps, 108 channel), absorbed into the slice regions r_st0..7'),
        dict(name='lane_h', master='qfd_dv_lane_h_safe2', count=8, sinks=None, state='CLOSED (e95c9709b TT +10.97 / FF +6.50)', wh=(172.8, 129.6)),
        dict(name='sfu_exp', master='ot_hdc_sfu_exp_t', count=8, sinks=ff['exp'], state='closed view', wh=(129.6, 151.2)),
        dict(name='sfu_rcp', master='ot_hdc_sfu_rcp_t', count=8, sinks=ff['rcp'], state='closed view', wh=(108.0, 129.6)),
        dict(name='sfu_rsq', master='ot_hdc_sfu_rsq_t', count=8, sinks=ff['rsq'], state='closed view', wh=(129.6, 151.2)),
        dict(name='xs_leaf', master='ot_qfd_xs_leaf (qfd_xs_leaf_w130m5)', count=32, sinks=ff['leaf'], state='STAND-IN (M5 re-kit of the closed w130 view owed)', wh=(129.6, 69.12)),
        dict(name='stream', master='qfd_dv_stream_t2 (QW-STREAM2)', count=1, sinks=ff['stm'], state='GATING (t2 / t2c, claude/qw-stream2-1019@532649182); STAND-IN until closed', wh=(302.4, 380.16)),
        dict(name='tload', master='qfd_dv_slice_tload_ns3 (QW-TLOAD2)', count=1, sinks=ff['tld'], state='GATING (ns3 / ns3b, claude/qw-tload2-1019); STAND-IN until closed', wh=(388.8, 216.0)),
        dict(name='suvm', master='qfd_dv_s5_suvm (NEW)', count=1, sinks=ff['vm'] + loc['su8'] + 600, state='NEW leaf: VM (22 SRAM) + SU issue control', ports=5198 + 600,
             wh=outline(ff['vm'] + loc['su8'] + 600, 5800, vm_macro, 1.0)),
        dict(name='lrly', master='qfd_dv_s5_lrly (NEW, 1 master x 8)', count=8, sinks=loc['su_lane'] + (su8_soft - loc['su8'] - 600) // 8, state='NEW leaf: one lane\'s RD relay stages + the qfd_dv_su_lane IREG/OREG/reset glue', ports=2 * ports['su_lane'],
             wh=outline(loc['su_lane'] + (su8_soft - loc['su8'] - 600) // 8, 2 * ports['su_lane'])),
        dict(name='red', master='qfd_dv_s5_red (NEW)', count=1, sinks=ff['vreduce'], state='NEW leaf: ot_hdc_vreduce SW 8 (R-ARITH csum8)', ports=ports['vreduce'] + 64,
             wh=outline(ff['vreduce'], ports['vreduce'] + 64)),
        dict(name='sc', master='qfd_dv_s5_sc (NEW)', count=1, sinks=ff['sc'], state='NEW leaf: qfd_dv_scalar2 (rsqrt inside; 17k = guidance, judged on spread)', ports=ports['sc'],
             wh=outline(ff['sc'], ports['sc'])),
        dict(name='ctl', master='qfd_dv_s5_ctl (NEW)', count=1, sinks=loc['slice2'] - 7400 + ff['amax'] + 1600, state='NEW leaf: decode / SETID / VM write merge / own AR+D2D word builder / gather / status + amax_mu (face pin regs move to the face strips)', ports=3600,
             wh=outline(loc['slice2'] - 7400 + ff['amax'] + 1600, 3600)),
        dict(name='xhead', master='qfd_dv_s5_xhead (NEW, 1 master x 4)', count=4, sinks=ff['xhead'], state='NEW leaf: ot_qfd_xhead (w130 config); pin-bound 7,546 pins -> 216 x 432 (5.8/um)', ports=ports['xhead'],
             wh=(216.0, 432.0)),
        dict(name='tap', master='qfd_dv_s5_tap (NEW)', count=1, sinks=ff['tap'] + loc['heads'], state='NEW leaf: ot_qfd_xs_tap + heads fault join; pin-bound 648 x 172.8', ports=ports['tap'],
             wh=(648.0, 172.8)),
        dict(name='frly', master='qfd_dv_s5_frly<W> (NEW, forwarded pass-lane relay station)', count=None, sinks=None,
             state='NEW leaf family: half-cycle forwarded relay stations of the W<->E pass chains (st, ch, hr, cmd, sc, ag, treq) and the N->S corridor (cw_s, rs_n); <= 405 um per hop', wh=(43.2, 129.6)),
        dict(name='face_land', master='LAND8 qfd_landh0d8_* / qfd_c_land_{w,r}258_narrow', count=None, sinks=None,
             state='CLOSED masters (182 slice<->slice face landings, plan 7811217d7)', wh=None),
    ]
    for lf in leaves:
        if lf.get('wh'):
            lf['wh'] = [float(lf['wh'][0]), float(lf['wh'][1])]
    # ------------------------------------------------------------------------------------------ floorplan (sketch)
    # bottom-left origin, role-oriented (dn face = x 0: the W master face; the E master is this plan mirrored MY).
    R = {
        'r_fw':  dict(rect=[0, 0, 259.2, 1296.0], what='dn face strip: 91/2 face landings (LAND8 + narrow pairs) of this master, pin registers, pass-lane launch/landing halves, rst_n face landing'),
        'r_fe':  dict(rect=[2203.2, 0, 2462.4, 1296.0], what='up face strip: the other face landings, pin registers, pass-lane halves'),
        'r_ch':  dict(rect=[259.2, 864.0, 2203.2, 1296.0], what='pass channel (std cells only): forwarded W<->E pass lanes st x2, ch x2, hr, cmd, sc x2, ag, treq (frly stations every <= 405 um)'),
        'r_st':  dict(rect=[302.4, 43.2, 1188.0, 540.0], what='station: 8 stnrgc leaves 2x4 (stnent geometry 885.6 x 496.8), regions r_st0..r_st7, rs_s from the S face directly above'),
        'r_stm': dict(rect=[1252.8, 43.2, 1987.2, 453.6], what='stream tile + tload tile (one region: tload joins the stream table-write port)'),
        'r_ctl': dict(rect=[1252.8, 496.8, 1641.6, 820.8], what='ctl leaf (decode, VM write merge, own AR/D2D words, gather, amax, status)'),
        'r_sc':  dict(rect=[1684.8, 496.8, 1987.2, 820.8], what='scalar leaf (psum / RB / argmax tree)'),
        'r_su':  dict(rect=[345.6, 1296.0, 2116.8, 1987.2], what='SU block 1771.2 x 691.2: 2 rows x (2 lane cells | centre 561.6 | 2 lane cells); centre = suvm + red; lane cell 302.4 x 345.6 = lane_h + exp/rcp/rsq + its lrly (lrly at the path midpoint: every hop <= 405 um)'),
        'r_vc':  dict(rect=[2116.8, 1296.0, 2203.2, 2160.0], what='N->S corridor E (std cells only, 86.4 um): forwarded cw_s2..3 + rs_n relays'),
        'r_vc2': dict(rect=[259.2, 1296.0, 345.6, 2160.0], what='N->S corridor W (86.4 um): forwarded cw_s0..1 relays'),
        'r_tap': dict(rect=[907.2, 1987.2, 1555.2, 2160.0], what='tap leaf 648 x 172.8 (pin-bound: 6,281 pins at 3.8/um) under the head band centre'),
        'r_hc':  dict(rect=[259.2, 2160.0, 2203.2, 2592.0], what='head band: 4 column regions r_hc0..3 (486 x 432): 8 xs_leaf 2x4 (259.2 x 276.5) + xhead leaf 216 x 432 (pin-bound); cw_n0..3 straight up to the N face'),
    }
    for k, r in R.items():
        x0, y0, x1, y1 = r['rect']
        r['w'], r['h'] = round(x1 - x0, 3), round(y1 - y0, 3)
        r['centre'] = [round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)]
    # ------------------------------------------------------------------------------------------ regions / roots
    regions = [
        dict(name='r_fw', leaves='face landings (W half), pin regs, frly launch', root_sinks='landing-tile clock pins + ~4k parent pin/landing flops (strip 259 x 1296; root at strip centre, <= 650 um)'),
        dict(name='r_fe', leaves='face landings (E half), pin regs, frly launch', root_sinks='as r_fw'),
        dict(name='r_st0..7', leaves='1 stnrgc each', root_sinks='1 leaf clock pin + its landing halves (stnent record: 1,129 landing flops total)'),
        dict(name='r_stm', leaves='stream + tload', root_sinks='2 leaf clock pins + landing halves'),
        dict(name='r_ctl', leaves='ctl', root_sinks='1 leaf pin + landing halves'),
        dict(name='r_sc', leaves='sc', root_sinks='1 leaf pin + landing halves'),
        dict(name='r_su', leaves='suvm, red, 8 lrly, 8 lane_h, 24 SFU', root_sinks='42 leaf clock pins (no soft parent flops); H-tree from the centre, parent-compensated entries; judged per linked pair (lrly<->suvm, lrly<->lane_h, lane_h<->SFU) at TT/FF <= 80'),
        dict(name='r_tap', leaves='tap', root_sinks='1 leaf pin + landing halves'),
        dict(name='r_hc0..3', leaves='xhead + 8 xs_leaf each', root_sinks='9 leaf pins + landing halves; column 486 x 432'),
        dict(name='frly hops', leaves='frly stations', root_sinks='forwarded clock with the data (neighbour-relative), landed where consumed'),
    ]
    # ------------------------------------------------------------------------------------------ crossings
    # kind: LAND = lp landing ring (E = K = 2, +3 edges); FWD = forwarded half-cycle relay lane + landing at the far end
    # (2.46 mm W->E or 2.2 mm N->S: ~6 hops <= 405 um, +3 edges); LOCAL = same region, plain registered hop (0 edges);
    # LOOSE = sticky status landing (lag only, never scheduled).
    def x(name, src, dst, bits, kind, edges, path, note=''):
        return dict(name=name, src=src, dst=dst, bits=bits, kind=kind, edges=edges, path=path, note=note)
    C = [
        # pass chains (one per slice hop of every serial pass)
        x('st_up pass', 'r_fw', 'r_fe', 1088, 'FWD', 3, 'pass', 'stream toward E5; FWD main: the stream tile only TAPS (landed copy) and INSERTS (merge at the out face); THRU fallback +6'),
        x('st_dn pass', 'r_fe', 'r_fw', 1088, 'FWD', 3, 'pass'),
        x('ch_up (outbound AR+D2D) pass', 'r_fe', 'r_fw', 1095, 'FWD', 3, 'pass', 'merge of own words at the out face (priority as qfd_dv_slice2: pass word wins, collision = sticky fault)'),
        x('ch_dn (return AR+D2D) pass', 'r_fw', 'r_fe', 1038, 'FWD', 3, 'pass'),
        x('hr pass', 'r_fw', 'r_fe', 453, 'FWD', 3, 'pass', 'pure pass; heads tap a landed copy'),
        x('cmd pass (SETID +1 at the out face)', 'r_fw', 'r_fe', 116, 'FWD', 3, 'pass', 'the out-face frly keeps a kept sid copy (1 edge as today: cmd_o is its own register)'),
        x('sc up/dn pass', 'r_fw', 'r_fe', 96, 'FWD', 3, 'pass', 'scalar ring pass + insert + tap: pass at the face, insert/tap landed to/from r_sc'),
        x('ag OR chain', 'r_fe', 'r_fw', 10, 'FWD', 3, 'pass', 'status OR: own term ORed at the out face (landed from r_ctl)'),
        x('treq row hop', 'r_fw', 'r_fe', 9, 'FWD', 3, 'pass'),
        # taps and inserts of the chains (off the pass path; on the consumer's path)
        x('cmd tap -> ctl', 'r_fw', 'r_ctl', 116, 'LAND', 3, 'tap'),
        x('cmd fields -> stnrgc / sc / stream / suvm (via ctl)', 'r_ctl', 'r_st,r_sc,r_stm,r_su', 4 * 120, 'LAND', 3, 'tap', 'decoded configs; stnent already lands cfg per region (+3 r1..7, record 3fb182a3d)'),
        x('st taps -> stream', 'r_fw,r_fe', 'r_stm', 2176, 'LAND', 3, 'tap'),
        x('stream inserts -> out faces', 'r_stm', 'r_fw,r_fe', 2176, 'LAND', 3, 'insert'),
        x('xw (SU x write) -> stream', 'r_su', 'r_stm', 8 + 192 + 256, 'LAND', 3, 'insert'),
        x('stream/tload table write -> VM', 'r_stm', 'r_su', 1051, 'LAND', 3, 'table', 'static exclusive table-write window (f16_calr_edges)'),
        x('xt (x beat) -> tap', 'r_stm', 'r_tap', 24 + 1024 + 2, 'LAND', 3, 'x', '1024 BF16 bits; the {bf16,16h0} expansion moves into the tap leaf'),
        x('hr tap -> tap/heads', 'r_fw', 'r_tap', 453, 'LAND', 3, 'x'),
        x('tap -> xhead columns', 'r_tap', 'r_hc0..3', 4 * 1100, 'LAND', 3, 'x', 'per column ~1,100 b (fill words + ctl); estimate from tap 6,281 ports'),
        x('cw_n0..3 -> N face', 'r_hc0..3', 'N face', 4 * 516, 'LOCAL', 0, 'x', 'xhead output flops beside the N face'),
        x('cw_s0..3 -> S face', 'r_hc0..3', 'S face', 4 * 516, 'FWD', 3, 'x', '2.2 mm N->S corridor r_vc (PARTITION.md 10-18 already owed +2-3 per x delivery)'),
        x('rs_s -> station', 'S face', 'r_st0..7', 1028, 'LAND', 3, 'mv', 'stnent: r0 lands, regions 1..7 +3 (already priced by QW-SLICE4)'),
        x('rs_n -> station', 'N face', 'r_st', 1028, 'FWD', 3, 'mv', '2.2 mm corridor; aligned with rs_s at the station (pad rs_s +3 or schedule)'),
        x('l9 in/out (neighbour L9 word)', 'r_fw', 'r_st', 2 * 514, 'LAND', 3, 'mv'),
        x('bt_q (BTAB -> station)', 'r_su', 'r_st0..7', 256 + 10, 'LAND', 3, 'mv', 'stnent presents bt_q per region at +3 (same landing, counted once)'),
        x('station results r_v/r_idx/r_last/r_d -> ctl', 'r_st', 'r_ctl', 522, 'LAND', 3, 'mv', 'to the VM write merge / own AR word / amax'),
        x('ctl -> VM w16 / w1 writes', 'r_ctl', 'r_su', 537 + 57, 'LAND', 3, 'mv'),
        x('ch return tap -> ctl (AR/D2D land, gather)', 'r_fw', 'r_ctl', 1038, 'LAND', 3, 'ar'),
        x('ctl own AR/D2D words -> out face merge', 'r_ctl', 'r_fe', 1095, 'LAND', 3, 'ar'),
        x('SU q/kv own D2D words -> ctl', 'r_su', 'r_ctl', 2 * (8 + 192 + 256), 'LAND', 3, 'ar'),
        x('red psum -> sc / VM (red_we/addr/data)', 'r_su', 'r_sc', 57, 'LAND', 3, 'norm'),
        x('SU RB scalar -> sc', 'r_su', 'r_sc', 33, 'LAND', 3, 'norm'),
        x('sc w1 (RB tap / root total) -> VM', 'r_sc', 'r_su', 57, 'LAND', 3, 'norm'),
        x('sc taps/inserts <-> faces', 'r_fw,r_fe', 'r_sc', 4 * 48, 'LAND', 3, 'norm'),
        x('amax <-> sc (am_v/idx/val/u)', 'r_ctl', 'r_sc', 59 + 60, 'LAND', 3, 'amax'),
        x('SU issue (p_re/p_idx, su_go) + progress', 'r_ctl', 'r_su', 11 + 50, 'LAND', 3, 'su'),
        x('lrly <-> suvm (RD relay stages)', 'r_su', 'r_su', 8 * 600, 'LOCAL', 0, 'su', 'inside r_su: the existing RD 2 relay stages ARE the reach stages (centre <= ~650 um)'),
        x('lrly <-> lane group', 'r_su', 'r_su', 8 * 1064, 'LOCAL', 0, 'su', 'lane_h ML 1 / RD 2 unchanged (closed lane_h binds)'),
        x('faults / status (stn, su, vm, sc, stm, tld, hd, port)', 'all', 'r_ctl', 8, 'LOOSE', 0, 'status', 'sticky; lag <= 6 edges/hop, never a scheduled value'),
        x('reset', 'rst_n face landing', 'every region', 1, 'RESET', 0, 'reset', 'lp reset runs (1-bit plain hops <= 405 um), per-region depth; release +4..+8 (boot only)'),
    ]
    # distances
    def cen(rn):
        rn = rn.split(',')[0].replace('0..7', '').replace('0..3', '')
        if rn.startswith('r_st'):
            rn = 'r_st'
        if rn.startswith('r_hc'):
            rn = 'r_hc'
        if rn in R:
            return R[rn]['centre']
        return {'N face': [1231.2, H], 'S face': [1231.2, 0.0], 'all': None, 'rst_n face landing': None}.get(rn)
    for c in C:
        a_, b_ = cen(c['src']), cen(c['dst'].split(',')[0])
        c['manhattan_um'] = None if (a_ is None or b_ is None) else round(abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]), 1)
        c['reach_ok'] = c['kind'] in ('FWD', 'LAND', 'LOOSE', 'RESET') or (c['manhattan_um'] or 0) <= 2 * REACH
    # ------------------------------------------------------------------------------------------ cut analysis
    def tracks(length, layers):
        return length * sum(TR[l] for l in layers) * AVAIL
    pass_bits = sum(c['bits'] for c in C if c['path'] == 'pass')
    cuts = []
    # (1) the W<->E pass channel: vertical cut line at x = 1231 through r_ch (all layers horizontal M2/M4/M6) plus the
    #     M6 over the stnrgc / stream children below it (children capped at M5)
    ch_h = R['r_ch']['h']
    cuts.append(dict(cut='W<->E pass channel (vertical cut, x mid)', bits=pass_bits + 1095,
                     tracks=round(tracks(ch_h, ['M4', 'M6']) + tracks(496.8, ['M6'])),
                     note='pass lanes + the ctl own-word lane to the out face (taps read the pass lanes in place); channel 432 um on M4+M6 + M6 over the station row'))
    # (2) N->S corridor r_vc (horizontal cut at y = 1700, vertical layers M3/M5/M7)
    cuts.append(dict(cut='N->S corridor (horizontal cut through r_vc + over the SU block on M7)', bits=4 * 516 + 1028,
                     tracks=round(tracks(R['r_vc']['w'] * 2, ['M3', 'M5', 'M7']) + tracks(R['r_su']['w'] * 0.25, ['M7'])),
                     note='two 86.4-um std-cell corridors beside the SU block + M7 over 1/4 of its width'))
    # (3) head band <- tap (horizontal cut y = 2160 over 1944 um, M3/M5/M7 in the channel row, M7 over children)
    cuts.append(dict(cut='head band / SU block boundary (y 2160)', bits=4 * 1100 + 453 + 4 * 516 + 1028,
                     tracks=round(tracks(R['r_hc']['w'], ['M5', 'M7'])),
                     note='tap -> columns, hr copy, cw_s and rs_n corridors leave downward'))
    # (4) SU block / south band boundary (y 1339): table writes, w16/w1, bt_q, issue, q/kv words, xw, norms
    su_bits = sum(c['bits'] for c in C if ('r_su' in c['src'] or 'r_su' in c['dst']) and c['kind'] != 'LOCAL')
    cuts.append(dict(cut='SU block <-> south band (y 1339, over the pass channel)', bits=su_bits,
                     tracks=round(tracks(R['r_su']['w'] * 0.5, ['M3', 'M5', 'M7'])),
                     note='crossings of r_su leave its S face over half its width'))
    # (5) face strips (each face: the die abstract today puts 5.7-5.9k pins on 1,256 um of the W/E faces)
    cuts.append(dict(cut='W (or E) face pins', bits=5884, tracks=round(1296 * TR['M4'] * 1.0 + 1296 * TR['M6'] * 1.0),
                     note='pins on M4 + M6 over 1,296 um (pin rule <= 6/um: 5884/1296 = 4.5/um)'))
    for c in cuts:
        c['ratio'] = round(c['bits'] / c['tracks'], 3)
        c['ok'] = c['ratio'] <= CUT_LIMIT[1]
    # ------------------------------------------------------------------------------------------ price
    # serial passes per layer of the dv chain (compiler to confirm): x broadcast 2 (attn in, FFN in), AR chain 2
    # (o-proj, down-proj), scalar ring 4 (2 RMSNorms x psum up + RB down); hops per pass 10 (7811217d7 face plan).
    hops = 10
    passes = dict(st=2, ch=2, sc=4)
    pass_cyc = 3 * hops * sum(passes.values())
    taps = dict(x=3 + 3 + 3 + 3 + 3, ar=3 + 3 + 3, mv=3 + 3 + 3, norm=3 + 3 + 3, table=0, su=3)
    # x: SU xw -> stream insert, st tap, xt -> tap, tap -> columns, cw_s corridor (S clusters);
    # ar: station r -> ctl, ctl -> out face, return tap -> ctl/VM; mv: rs_n corridor, station -> ctl, ctl -> VM;
    # norm: red -> sc, sc chain tap/insert, sc w1 -> VM; su: SU issue -> r_su (once per SU programme, not per op)
    tap_cyc = 2 * taps['x'] + 2 * taps['ar'] + 2 * taps['mv'] + 2 * taps['norm'] + taps['su']
    per_layer = pass_cyc + tap_cyc
    per_tok = per_layer * LAYERS
    tok_us = 1e6 / TOK_RATE
    price = dict(
        rule='landing E = K = 2: +3 edges; forwarded W<->E / N->S lane (2.2-2.46 mm, ~6 half-cycle hops <= 405 um) + far-end landing: +3',
        pass_chain_edges_per_slice_hop=3,
        pass_chain_note='physical floor: the flat slice crossed 2.46 mm pin register -> pin register in ONE edge (1,491 stages > 500 um in the gate); '
                        'in addition to the 7811217d7 face landing (+3/hop, already priced) unless the in-slice forwarded lane '
                        'continues the sender\'s ck_s and lands once at the receiver face (then the two merge: +3 total) -- kit decision',
        serial_passes_per_layer=passes, hops_per_pass=hops, pass_cycles_per_layer=pass_cyc,
        tap_insert_cycles_per_layer=tap_cyc, taps=taps,
        su_lane_path_cycles=0, su_lane_note='lanes stay in r_su: lane_h ML 1 / RD 2 unchanged (closed lane_h binds). FALLBACK (if r_su child-pair spread > 80): '
                                         'lane groups in own regions, lrly->suvm return landed: +3 per VM read round trip -> lane_h re-hardened at RD 2 + 3 (ML +3), ~+3 x SU ops/layer',
        station_cycles='stnent record: regions 1..7 +3 vs r0, reset +4 (QW-SLICE4, included in mv)',
        added_cycles_per_layer=per_layer, layers=LAYERS, added_cycles_per_token=per_tok,
        added_us_per_token=round(per_tok / (CLK_GHZ * 1e3), 2),
        token_us_ref=round(tok_us, 1), est_rate_loss_pct=round(100 * (per_tok / (CLK_GHZ * 1e3)) / tok_us, 2),
        thru_fallback='chains THROUGH the core tiles (stream t2 tile as is, ch merge in ctl): +6 per slice hop on st/ch/sc -> pass cycles x2',
        compiler='NOTICE lanes/QW-GEN3.md: exact per-op offsets come from the lp records of the kits; the per-layer composition here is the plan bound',
    )
    plan = dict(
        schema='opentallas.qwen_compute.slice5_partition.v1', lane='QW-SLICE5 (LEAD3-QW) 10-19',
        element='Q.STA.SLICE.2 qfd_dv_slice2_w / qfd_dv_slice2_e (critical prefix qfd_dv_slice2: no REVIEW / submit by the lane)',
        why='gates of record FAILED structurally (one 173,895-flop soft core root + 56,306 heads root, CTS/GRT rc 137)',
        census=census_rec, outline_um=[W, H], leaves=leaves, regions=regions, floorplan=R, crossings=C, cuts=cuts,
        price=price,
        layer_contract=dict(
            decision='ONE cluster level (coordinator 0gs(c), PARTITION.md 10-18 s7): children capped at M5, slice signals M2-M7, PG M7',
            consequence='the stnent CLUSTER (PG M7, straps M8) cannot nest under a hardened slice: its 8 stnrgc leaves + its lp regions / '
                        'landings (spec tools/landed_parent/specs/qfd_dv_stn_ent.json) are ABSORBED into the slice parent; stnent stays the '
                        'proof vehicle of that sub-arrangement. Likewise lane groups = lane_h + 3 SFU leaves directly (no qfd_dv_su_lane cluster); '
                        'heads = xhead leaf + 8 xs_leaf per column (no heads_w130 cluster).',
            alternative='die-placed wires-only slice parent folded by the GEN (KV-PVW qkd_pvw_die_t precedent, owner 0je): stnent / '
                        'lane / column clusters as die elements; needs a coordinator decision; same crossings and price'),
        lessons=[
            'stnent gate3 (QW-SLICE4 @805ddb993) FAIL clock_rule: regions r1..r7 = 122 landing-read sinks each, TT pin-flop spread 95-234 ps: '
            'the read halves sat away from the region clock entry. Rule for every region here: landing read halves FENCED beside the reader '
            'leaf, the region entry beside that leaf+halves mass (<= ~150 um), checked per region at the first gate image',
            'stnentb gate4 FAIL cts_run (fenced halves, 151.2 channel): fences must leave legal rows (DPL) -- size fences from the record flop count x 1.6'],
        build_steps=[
            '1 RTL: qfd_dv_s5_flat = wires-only flat parent (tools/qwen_dv/gen_slice5_flat.py) with leaves suvm, lrly x8, red, sc, ctl, '
            'xhead x4, tap, frly lanes + the closed leaves; lockstep vs qfd_dv_slice2 #(SU_LT 1, HD_W130 1, MU_NU 4, PRIVATE_CALR 1) at 0 offset (Verilator 5.050)',
            '2 lp.py spec (regions above; schedule reference for the ctl <-> SU / sc loops, ref_params = chain relay depths) -> qfd_dv_s5_lp + record (compiler offsets) + lockstep MUT0 PASS / MUT1,2,4 FAIL, audit PASS / unland FAIL',
            '3 new leaf kits (non-critical: gate + submit main + fallback in parallel): suvm, lrly, red, sc, ctl, xhead, tap, frly',
            '4 slice kits qfd_dv_slice2_w5 / _e5 (main, this floorplan) + _w5b / _e5b (fallback: r_su split into 2 lane-column regions with landed lrly returns '
            '+ lane_h RD+3 re-harden, wider 388.8 pass channel) with stand-ins (labelled) for stream / tload / xs_leaf m5 until closed; --cts --remote auto',
            '5 182 face landings (7811217d7) placed in r_fw / r_fe; ck_s_wi / ck_s_ei inputs per face group'],
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / 'partition.json').write_text(json.dumps(plan, indent=1) + '\n')
    sketch(R, C, out / 'floorplan_sketch.png')
    # summary
    print(f"census: slice {ff['slice2']:,} ff; soft before = 173,895 + 56,306 (+27.8k face) on 4 roots")
    for lf in leaves:
        print(f"  leaf {lf['name']:9s} x{lf['count']}  sinks {lf['sinks']}  {lf['state'][:60]}  wh {lf.get('wh')}")
    for c in cuts:
        print(f"  cut {c['cut'][:60]:60s} bits {c['bits']:6d} tracks {c['tracks']:6d} ratio {c['ratio']:.3f} {'OK' if c['ok'] else 'OVER'}")
    print(f"  price: pass {pass_cyc} + taps {tap_cyc} = {per_layer} cyc/layer, {per_tok} cyc/token, "
          f"{price['added_us_per_token']} us/token = {price['est_rate_loss_pct']} % of {price['token_us_ref']} us")


def sketch(R, C, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(8.6, 9))
    col = {'r_fw': '#c9daf8', 'r_fe': '#c9daf8', 'r_ch': '#fff2cc', 'r_vc': '#fff2cc', 'r_vc2': '#fff2cc', 'r_st': '#d9ead3', 'r_stm': '#ead1dc',
           'r_ctl': '#f4cccc', 'r_sc': '#f4cccc', 'r_su': '#d0e0e3', 'r_tap': '#fce5cd', 'r_hc': '#fce5cd'}
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for k, r in R.items():
        x0, y0, x1, y1 = r['rect']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col.get(k, '#eee'), ec='k', lw=0.8))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, k, ha='center', va='center', fontsize=8, weight='bold')
    # station leaves 2x4
    x0, y0 = 302.4, 43.2
    for i in range(4):
        for j in range(2):
            ax.add_patch(Rectangle((x0 + i * 216.0 + 32.4, y0 + j * (151.2 + 108.0) + 21.6), 151.2, 151.2, fc='#93c47d', ec='k', lw=0.4))
    # SU block: lane groups left/right, centre column
    sx0, sy0 = 345.6, 1296.0
    for j in range(2):
        for i in (0, 1, 4, 5):
            xx = sx0 + (i if i < 2 else i - 4 + 2) * 302.4 + (561.6 if i >= 4 else 0)
            ax.add_patch(Rectangle((xx, sy0 + j * 345.6), 302.4, 345.6, fc='#76a5af', ec='k', lw=0.4))
            ax.text(xx + 151, sy0 + j * 345.6 + 172, 'lane', ha='center', va='center', fontsize=6)
    ax.add_patch(Rectangle((sx0 + 2 * 302.4, sy0), 561.6, 691.2, fc='#a2c4c9', ec='k', lw=0.6))
    ax.text(sx0 + 2 * 302.4 + 280, sy0 + 345, 'suvm (22 SRAM)\n+ red', ha='center', va='center', fontsize=7)
    # heads columns
    for c in range(4):
        hx = 259.2 + c * 486.0
        ax.add_patch(Rectangle((hx + 21.6, 2181.6), 259.2, 276.48, fc='#f6b26b', ec='k', lw=0.4))
        ax.add_patch(Rectangle((hx + 270.0, 2160.0), 216.0, 432.0, fc='#ffd966', ec='k', lw=0.4))
        ax.text(hx + 151, 2320, f'8 xs_leaf', ha='center', fontsize=6)
        ax.text(hx + 378, 2350, f'xhead{c}', ha='center', fontsize=6, rotation=90)
    ax.add_patch(Rectangle((1252.8, 43.2), 302.4, 380.16, fc='#c27ba0', ec='k', lw=0.4))
    ax.text(1404, 233, 'stream', ha='center', fontsize=7)
    ax.add_patch(Rectangle((1598.4, 43.2), 388.8, 216.0, fc='#c27ba0', ec='k', lw=0.4))
    ax.text(1792, 150, 'tload (4 ROM)', ha='center', fontsize=7)
    ax.annotate('', xy=(2203, 1080), xytext=(259, 1080), arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax.text(1231, 1120, 'forwarded pass lanes st/ch/hr/cmd/sc/ag (+3/hop)', ha='center', fontsize=7)
    ax.annotate('', xy=(2160, 60), xytext=(2160, 2150), arrowprops=dict(arrowstyle='->', lw=1.0))
    ax.text(2140, 1700, 'cw_s / rs_n corridor', rotation=90, fontsize=6, ha='right')
    ax.set_xlim(-50, W + 50)
    ax.set_ylim(-50, H + 50)
    ax.set_aspect('equal')
    ax.set_title('QW-SLICE5 qfd_dv_slice2 landed parent: partition sketch (dn face = x 0; E master = MY)', fontsize=9)
    ax.set_xlabel('um')
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == '__main__':
    main()
