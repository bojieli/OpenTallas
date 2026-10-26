#!/usr/bin/env python3
"""S81-RTLGAP/RG-HEAD (TOK.DS.BENCH.4.1, 10-21): the HEAD PRODUCER on the final-layer 72-frame stage die.

Binding (results/rtl/s81_rtlgap_head_1021/README.md; TOK-S81 PRODUCTION_BINDING 5377e6479 items 1-7):
  final FFN down/combine -> VS13 -> VP POST a0 = 1009, a1 = FFNC 448 (final_ffn.py, 9b2e70333: h written in place into the
  80 vn h stores) -> HEAD NORM on all 16 slices / 80 beat leaves (this family) -> vq BF16 XB beats -> the ONE head egress
  path (ot_s81sl_rstop_xo at s_0N -> ro_w -> lep pair A = the stage NEXT circuit) -> head die (S81.HEAD: rstop gather ->
  ot_s81_head_xb_replay -> native ROM head -> argmax -> token return).

Programme per tier engine (V north = N slices, V south = S slices; one CTL row an edge an engine):
  GAIN   a0 = HEADG 480 (leaf_rows: the released head-norm gains, 16 rows = 64 FP32 / leaf in element order, BOOT-resident:
         written once by CTL target-5 row writes, boot_gain_ctl(); no other writer) -> one CTL beat, slice mask = the 8
         slices of the tier, leaf mask 0x1F
  NORMR  a0 = GU_FFN 1008 = the SAME token's final-FFN pre row (dsdv_gunit_l5 CTL row R of the final FFN HC job; lease:
         from that write to the last head NORMR read -- the next token's attn HC writes GU_ATTN 1000, never 1008, and the
         next layer's FFN HC is a later token), a1 = EGRESS_FLAG 128 + 5 sid + k (vq header [20:13]: gather index
         [19:13] = 5 sid + k unchanged, [20] = 1 = head egress), n = 2 (BF16 family only), one CTL per leaf
  XFIN   go eps (CTL target 1) after the slice's 5 NORMRs (lower_norm_smoke order, beat bench g_b37 spacing)
  No HLOAD: POST leaves the final h resident in vn (vp header: POST "writes back in place into vn's h store").
Egress: the 80 flagged beats reach s_0N once each (bench tb_s81sl_rstop_xo R1: 80/80 exact, nothing on the other outward
ports) and leave on ro_w, one 80-beat lep TX window (lep / dsdv_mu_land NB 80) on pair A -> MU tag {user, pos} stamped,
so a stale same-index beat is rejected by the head die's landing.  Exclusive static admission: the compiler opens that
window only for this phase; no other s_0N ro_w source in it (rstop_xo faults on a collision).
Status PARTIAL: the 16-slice NX snake / rstd timing of the composed norm on the die is a plan value (xfin16 bench 234
edges), and the consumer is the head die (GAP_HEAD: no head-die netlist yet).

CLI:  python3 -I lower_head.py boot-gains --gains head_norm_w.f32 --out DIR   (5,120 little-endian FP32 = the released
      head norm weight) -> DIR/boot_gain_ctl.json: 1,280 CTL target-5 payloads {sid, leaf, row, payload} + their sha256
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import leaf_rows as LR  # noqa: E402

OPS = [r'^head\.hc_pre$', r'^head\.norm\.(sumsq|rsqrt|scale)$']
HEAD_GAIN = LR.REGIONS['HEADG'][0]          # 480
PRE_ROW = LR.GU_ROWS['ffn']                 # 1008: final FFN HC pre row (same token)
EGRESS_FLAG = 128                           # vq gidx bit 7 -> header [20]; ot_s81sl_rstop_xo forwards at s_0N
XO_SLICE = 'u_s_0N'                         # rstop_xo XO_SID 1 (column 0, tier N): lep pair A, stage NEXT circuit
VP_GAIN, VP_NORMR = 1, 7
BENCH = 'results/rtl/s81_rtlgap_head_1021/rstop_xo_bench'
GAP = dict(module='head die (S81.HEAD) + 16-slice norm composition on the die',
           port='rstop_xo s_0N ro_w -> lep pair A -> head die s_0N B',
           missing='egress RTL benched (ot_s81sl_rstop_xo, 80/80 exact on a 16-stop ring); the composed 16-slice NX snake '
                   '/ rstd timing on the die cut is a plan value (xfin16 234), and the head-die consumer (rstop gather -> '
                   'ot_s81_head_xb_replay -> ROM head) has no netlist (GAP_HEAD)')


def _dlc():
    import dv_layer_compile as D   # noqa: E402 (plugin runs inside the compiler)
    return D


def gain_rows(gains, sid, k):
    """the 16 HEADG rows of beat leaf (sid, k): row r word w = gain[320 sid + 64 k + 4 r + w] (element order, the vp GAIN
    layout: 16 rows = 64 FP32 gains -> vn wl rows 0..7), FP32 bits at data[32 w +: 32]"""
    out = []
    for r in range(16):
        d = 0
        for w in range(4):
            d |= (gains[320 * sid + 64 * k + 4 * r + w] & 0xFFFFFFFF) << (32 * w)
        out.append((HEAD_GAIN + r, d))
    return out


def row_write_body(row, data128, mask=0xF):
    """ot_s81sl_xr CTL target 5 body: [9:0] row, [13:10] word mask, [141:14] data (xr.sv rwb = body[141:14])"""
    return (row & 0x3FF) | (mask & 0xF) << 10 | (data128 & ((1 << 128) - 1)) << 14


def boot_gain_ctl(gains):
    """1,280 CTL payloads (16 slices x 5 leaves x 16 rows), one leaf each: the boot calendar issues them once (any order,
    one CTL an edge an engine); residency: HEADG is written by nothing else"""
    D = _dlc()
    assert len(gains) == 5120
    out = []
    for sid in range(16):
        for k in range(5):
            for row, d in gain_rows(gains, sid, k):
                out.append(dict(sid=sid, leaf=k, row=row, payload=D.ctl_payload(1 << sid, 5, 1 << k, row_write_body(row, d))))
    return out


def _line_w(die, D, col, tier):
    """edges for a beat injected at column col to reach column 0 on the tier line (rstop 2 / stop + link ages)"""
    t, c = 0, col
    while c > 0:
        cand = [L for k, L in die.links.items() if any(x[0] == f'u_s_{c}{tier}' for x in L['src'])
                and any(x[0] == f'u_s_{c - 1}{tier}' for x in L['dst'])]
        t += (max(L['age_edges'] for L in cand) if cand else 0) + D.RSTOP_HOP
        c -= 1
    return t


def lower(die, op, ctx):
    D = _dlc()
    name = op['op']
    if name != 'head.hc_pre':
        return dict(status='PARTIAL', unit='slice vp GAIN / NORMR + vn + xfin + vq (head norm, all 80 leaves)',
                    insts=[], rows=[], templates=[], events=[], bench=BENCH, gap=dict(GAP, missing='carried by the '
                    'head.hc_pre programme (lower_head): ' + GAP['missing']))
    t0 = int(ctx.get('t_issue', 0))
    sl = die.slices()
    templates, rows, events, plan = [], [], [], {}
    for eng, tier in ((D.ENG['VN'], 'N'), (D.ENG['VS'], 'S')):
        tier_sl = sorted((s for s in sl if s.endswith(tier)), key=lambda s: sl[s]['sid'])
        if not tier_sl:
            continue
        mask = 0
        for s in tier_sl:
            mask |= 1 << sl[s]['sid']
        t = t0
        ti = len(templates)
        templates.append((f'{tier}.head.GAIN', D.ctl_payload(mask, 0, 0x1F, D.vp_cmd(VP_GAIN, a0=HEAD_GAIN))))
        rows.append(dict(eng=eng, issue=t, arg=ti, what=f'head GAIN a0 {HEAD_GAIN} tier {tier}'))
        for s in tier_sl:
            events.append(dict(cycle=t + D.ctl_path(die, s)['edges'], inst=s, port=D.ctl_path(die, s)['entry_port'],
                               dir='in', kind='CTL', tag='head.GAIN', payload=f'template {ti}'))
        t += D.BEAT['gain_slot']
        for s in tier_sl:
            sid = sl[s]['sid']
            cp = D.ctl_path(die, s)
            go = []
            for k in range(5):
                ti = len(templates)
                templates.append((f'{s}.head.NORMR.k{k}', D.ctl_payload(
                    1 << sid, 0, 1 << k, D.vp_cmd(VP_NORMR, a0=PRE_ROW, a1=EGRESS_FLAG + 5 * sid + k, n=2))))
                rows.append(dict(eng=eng, issue=t, arg=ti, what=f'head NORMR {s} leaf {k} a1 {EGRESS_FLAG}+{5 * sid + k}'))
                events.append(dict(cycle=t + cp['edges'], inst=s, port=cp['entry_port'], dir='in', kind='CTL',
                                   tag=f'head.NORMR.k{k}', payload=f'template {ti}; hc_pre leaf row {PRE_ROW}'))
                go.append(t + cp['edges'])
                t += 1
            ti = len(templates)
            templates.append((f'{s}.head.XFIN_GO', D.ctl_payload(1 << sid, 1, 0, D.xfin_go(D.norm_eps_bits()))))
            rows.append(dict(eng=eng, issue=t, arg=ti, what=f'head XFIN_GO {s}'))
            events.append(dict(cycle=t + cp['edges'], inst=s, port=cp['entry_port'], dir='in', kind='CTL',
                               tag='head.XFIN_GO', payload=f'template {ti}'))
            t += 1
            plan[s] = dict(sid=sid, go=go, last_partial=go[-1] + D.BEAT['go_to_partial_normr'] + D.XFIN['dl'] +
                           D.XFIN['collector'])
    # plan-only egress edges (the composed 16-slice snake is not benched on the die): rstd after the LAST slice partial
    rstd = max(p['last_partial'] for p in plan.values()) + D.XFIN['last_partial_to_rstd'] if plan else 0
    for s, p in plan.items():
        tier, col = s[-1], int(s[4])
        for k in range(5):
            ring = rstd + D.BEAT['rstd_to_xq'] + 20 + 4 * k + D.XFIN['dl']       # vq XB step 20 + 4k (BF16 only)
            at = ring + (_line_w(die, D, col, 'N') if tier == 'N' else 4 + 2 + _line_w(die, D, col, 'N'))
            events.append(dict(cycle=at, inst=XO_SLICE, port='lep (outward line port) ro_w', dir='out', kind='XB',
                               tag=f'head.x beat {5 * p["sid"] + k} (src slice {s})', boundary='offdie', plan_only=True,
                               payload='normalized x BF16 (head producer)', gap=GAP['missing'],
                               observe='u_s_0N rstop_xo ro_w -> lep pair A (MU TX window, 80 beats) -> stage NEXT circuit'))
    return dict(status='PARTIAL', unit='slice vp GAIN / NORMR (a1 flag 128) + vn + xfin + vq -> rstop_xo s_0N egress',
                insts=sorted(plan), rows=rows, templates=templates, events=events, bench=BENCH, gap=GAP,
                head=dict(gain_row=HEAD_GAIN, pre_row=PRE_ROW, egress=XO_SLICE, flag=EGRESS_FLAG, beats=80,
                          rstd_plan=rstd, ctl_rows=len(rows), templates=len(templates)))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('boot-gains')
    b.add_argument('--gains', required=True)
    b.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    raw = Path(a.gains).read_bytes()
    assert len(raw) == 5120 * 4, f'{a.gains}: {len(raw)} bytes, want 5120 FP32'
    g = list(struct.unpack('<5120I', raw))
    ctl = boot_gain_ctl(g)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    doc = dict(schema='opentallas.s81_dv.head_gain_boot.v1', gains=str(a.gains), gains_sha256=hashlib.sha256(raw).hexdigest(),
               region=dict(name='HEADG', rows=list(LR.REGIONS['HEADG'])), n=len(ctl),
               ctl=[dict(c, payload=f'{c["payload"]:x}') for c in ctl])
    (out / 'boot_gain_ctl.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(f'HEAD_GAIN_BOOT {len(ctl)} CTL row writes -> {out / "boot_gain_ctl.json"}')


if __name__ == '__main__':
    main()
