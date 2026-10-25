#!/usr/bin/env python3
"""KV-CORES 10-24: qkd_ahub re-floorplan PROPOSAL after GEOM-REVIEW FAIL 2026-10-24 19:44 (GPL blob, 12% util, one
897-ps corner clock tree, 412k flat instances > 400k cap).  NO P&R: this writes the plan + a render for GEOM REQ.

Root cause.  The KVG3 kit (gen_core_kit_kv.py) synthesised qkd_ahub FLAT (SYNTH_HIERARCHICAL 0, no macros): the four
ot_nhb_zh Z trees (8,342 flops each: the 128 x 32-b zm store + 16 read ports) and the ot_qkh_recip_leaf (8,994 flops)
were dissolved into one 407k-cell netlist.  The CLOSED composition of the same RTL (physical/ref_tile/qkd_ahub_sdw =
qkd_ahub_static_dw at 734.4 x 540) instantiates them as HARD children: ot_nhb_zh (ref_tile/ot_nhb_zh_m5, 151.2^2, M2-M5)
x4 and ot_qkh_recip_leaf (ref_tile/qkh_recip_ref, 216^2, M2-M6); its parent glue is only ~3.4k flops.
Flop accounting: flat 42.3k = 4 x 8,342 + 8,994 + ~0 (synthesis merges) ~ sdw 3,401 glue sinks.

Proposal = macro-composed core (owner rule 10-11 top-down hierarchy: replicated clusters hardened once):
  * children: 4 x ot_nhb_zh (one master, hardened once) + 1 x ot_qkh_recip_leaf, both existing views (must be RE-SIGNED
    with today's signoff.py: TT setup / FF hold 60/25 ps; NOT RUN yet);
  * parent glue ~30k cells (u_io, u_core_la decodes, pin flops, relays u_ri/u_ro/u_rx/u_ry, ot_rst_pipe) -> far under
    the 400k cap;
  * outline shrunk from 734.4 x 540 to W x H below, S-E corner kept in place in hub_C (ahub talks only S (ap/am to
    the ASTK stacks, hs from kvs_attn) and E (fr to pvfin)), so no link gets longer; the freed N/W L-strip returns to
    hub_C glue.  Pins re-assigned by core_pins_v37p.py on the new outline (same faces S / E; plan tool, KV-P);
  * clock (decision 5 + core-latency contract (e)): ck / rst_n at the S-face centre (COORD 10-24), one spine to a hub at the channel centre, 6 taps
    (5 child clk pins + 1 glue tap grid over the S band and the channel), each child's tap delayed so child flop latency
    (zh TT 246 / recip 224 ps measured inside) lands in one 20-ps window with the glue flops; published core latency =
    that window (core_latency.json), parent compensates with an early core tap.  No single corner tree over the core.

Usage: ahub_fp_proposal.py OUT_DIR   -> OUT_DIR/qkd_ahub_fp_proposal.json + .png
"""
import json, sys
from pathlib import Path

G = 8.64
W, H = 70 * G, 51 * G                         # 604.8 x 440.64 (old 734.4 x 540)
ZH, RC = 151.2, 216.0
BAND = 7 * G                                   # S glue band 60.48 (pin flops ap/am/hs, u_io, u_core decodes)
blocks = [
    # row A: MX -> zh inputs (LEF S face, 268 b) face UP into the A/B channel where u_core_la + u_ri sit; roots (64 b
    # + zerr 4) face DOWN to the S band (registered at the band, then ~170 um to u_core)
    dict(inst='g_zh[0].u_zh', master='ot_nhb_zh', x=3 * G, y=8 * G, w=ZH, h=ZH, orient='R180'),
    dict(inst='g_zh[1].u_zh', master='ot_nhb_zh', x=23 * G, y=8 * G, w=ZH, h=ZH, orient='MX'),
    # row B: R0 -> inputs (S) face DOWN into the same channel; roots (N) return down the W / middle side channels
    # (the closed qkd_ahub_sdw used the same MX-below / R0-above pairing around its core channel)
    dict(inst='g_zh[2].u_zh', master='ot_nhb_zh', x=3 * G, y=30.5 * G, w=ZH, h=ZH, orient='MY'),
    dict(inst='g_zh[3].u_zh', master='ot_nhb_zh', x=23 * G, y=30.5 * G, w=ZH, h=ZH, orient='R0'),
    # reciprocal leaf on the E side next to the fr export face; x pins (N, left corner) toward the channel / core,
    # y (S, right) down to the S band (RX_RLY 1 / RY_RLY 2 relays exist in the RTL)
    dict(inst='u_recip', master='ot_qkh_recip_leaf', x=43 * G, y=15.5 * G, w=RC, h=RC, orient='R0'),
]
regions = [
    dict(name='S glue band: ap/am/hs pin flops, u_io, zh[0..1] root landing (u_ro)', x=0, y=0,
         w=W, h=BAND),
    dict(name='A/B channel: u_core_la + u_ri write relays (4 x 268 b) -> zh inputs, rc_x relay', x=0, y=8 * G + ZH, w=42 * G,
         h=30.5 * G - 8 * G - ZH),
    dict(name='E column: fr export flops u_rw (145 b) at the E pins', x=W - 2 * G, y=BAND, w=2 * G, h=H - BAND),
]
# left-column zh mirrored in x (MY / R180) so every zh clk pin (LEF W face, y 148.4) sits on the column gap next to
# the spine; vertical flip (MX / R180) for row A so its inputs face the channel
def clk_xy(b):
    if b['master'] != 'ot_nhb_zh':
        return b['x'] - 1.0, b['y'] + 113.9
    fx = b['orient'] in ('MY', 'R180'); fy = b['orient'] in ('MX', 'R180')
    return (b['x'] + b['w'] + 1.0 if fx else b['x'] - 1.0), b['y'] + (b['h'] - 148.4 if fy else 148.4)


taps = [dict(name=f"tap->{b['inst']}/clk", x=clk_xy(b)[0], y=clk_xy(b)[1])
        for b in blocks] + [dict(name='glue tap grid (S band + channel)', x=W / 2, y=BAND / 2)]   # fed off the spine foot
# COORD spot-check 10-24: ck / rst_n move from the S-E corner to the S-face centre (between the ap and hs groups); the
# clock is centre-fed: S-centre pin -> one spine up the zh0/zh1 column gap -> hub at the A/B channel centre -> taps
CK = (21.5 * G, 0.0)                         # 185.76: S face, centre of the zh column gap / channel hub x
HUB = (21.5 * G, 8 * G + ZH + (30.5 * G - 8 * G - ZH) / 2)     # channel centre (185.76, 241.92)
pins = dict(S=dict(groups=['am0..3 (144)', 'ap0..3 (172)', 'ck + rst_n (S centre, x ~186)', 'hf', 'hs_* (166)'],
                   count=484),
            E=dict(groups=['fr_epoch', 'fr_rz (128)', 'fr_valid'], count=145))


def spine_d(t):
    """Manhattan distance from a tap to the clock spine (S-centre pin -> channel hub, vertical at CK x)."""
    return abs(t['x'] - CK[0]) + max(0.0, t['y'] - HUB[1])


def check():
    f = []
    for i, a in enumerate(blocks):
        assert 0 <= a['x'] and a['x'] + a['w'] <= W and 0 <= a['y'] and a['y'] + a['h'] <= H, a['inst']
        for b in blocks[i + 1:]:
            ox = min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x'])
            oy = min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y'])
            gap = max(-ox, -oy)
            assert gap >= 2 * G - 1e-6, (a['inst'], b['inst'], gap)
    macro = sum(b['w'] * b['h'] for b in blocks)
    std = 30e3 * 0.11                            # ~30k glue cells x ~0.11 um2 (flat-run average cell area)
    return dict(outline_um=[W, H], area_um2=round(W * H), macro_area_um2=round(macro),
                macro_fraction=round(macro / (W * H), 3), glue_std_area_um2_est=round(std),
                glue_util_est_over_free=round(std / (W * H - macro), 3),
                old=dict(outline_um=[734.4, 540.0], area_um2=396576, flat_cells=406723, util=0.119))


def render(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.add_patch(Rectangle((0, 0), 734.4, 540, fill=False, ls=':', ec='grey'))
    ax.text(734.4 - 4, 540 - 12, 'old 734.4 x 540 outline (flat 407k, FAIL)', ha='right', color='grey', fontsize=8)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec='black'))
    for r in regions:
        ax.add_patch(Rectangle((r['x'], r['y']), r['w'], r['h'], fc='#cfe8cf', ec='green', alpha=.6))
        ax.text(r['x'] + 3, r['y'] + r['h'] / 2, r['name'], fontsize=6.5, va='center',
                rotation=90 if r['w'] < 30 else 0)
    for b in blocks:
        c = '#9ec5fe' if b['master'] == 'ot_nhb_zh' else '#fdd49e'
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fc=c, ec='navy'))
        ax.text(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2, f"{b['inst']}\n{b['master']}\n{b['w']}^2 {b['orient']}",
                ha='center', va='center', fontsize=8)
        if b['master'] == 'ot_nhb_zh':      # LEF: input pins S x 32-96, roots N x 87-100, clk W top (MX: swapped)
            fy = b['orient'] in ('MX', 'R180'); fx = b['orient'] in ('MY', 'R180')
            yi, yo = (b['y'] + b['h'] - 1, b['y'] + 1) if fy else (b['y'] + 1, b['y'] + b['h'] - 1)
            X = (lambda u: b['x'] + b['w'] - u) if fx else (lambda u: b['x'] + u)
            ax.plot([X(32), X(96)], [yi, yi], color='red', lw=3)
            ax.plot([X(87), X(100)], [yo, yo], color='purple', lw=3)
        else:                                # x N x 1-13, y S x 193-208
            ax.plot([b['x'] + 1, b['x'] + 13], [b['y'] + b['h'] - 1] * 2, color='red', lw=3)
            ax.plot([b['x'] + 193, b['x'] + 208], [b['y'] + 1] * 2, color='purple', lw=3)
    ck = CK
    ax.plot([ck[0], HUB[0]], [ck[1], HUB[1]], color='darkorange', lw=2.5)
    for t in taps:
        y0 = min(max(t['y'], 0), HUB[1])
        ax.plot([HUB[0], t['x'], t['x']], [y0, y0, t['y']], color='orange', lw=.9, ls='--')
        ax.plot(t['x'], t['y'], 'o', color='orange', ms=5)
    ax.plot(*ck, 's', color='orange', ms=9); ax.plot(*HUB, 'D', color='darkorange', ms=8)
    ax.text(ck[0] + 4, ck[1] + 8, 'ck / rst_n (S centre)', color='darkorange', fontsize=8)
    far = max(spine_d(t) for t in taps)
    ax.text(HUB[0] + 4, HUB[1] + 6, f'clock spine {HUB[1]:.0f} um + hub; max spine->tap {far:.0f} um', fontsize=7,
            color='darkorange')
    ax.plot([0, W], [-3, -3], color='crimson', lw=5)
    ax.text(W / 2, -16, 'S face 484 pins: am0..3 | ap0..3 | ck rst_n | hf | hs_* (to ASTK stacks / kvs_attn)', ha='center',
            fontsize=8)
    ax.plot([W + 3, W + 3], [0, H], color='olivedrab', lw=5)
    ax.text(W + 10, H / 2, 'E face 145 pins: fr_* to pvfin', rotation=90, va='center', fontsize=8)
    s = check()
    ax.set_title(f"qkd_ahub PROPOSAL (KV-CORES 10-24): macro-composed, {W:.1f} x {H:.2f} um "
                 f"({s['area_um2']} um2, macros {s['macro_fraction']:.0%}); red = child inputs, purple = child "
                 f"outputs, orange = clock taps", fontsize=9)
    ax.set_xlim(-20, 760); ax.set_ylim(-30, 560); ax.set_aspect('equal')
    fig.tight_layout(); fig.savefig(out, dpi=130)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    s = check()
    plan = dict(schema='opentallas.kv.core_fp_proposal.v1', core='qkd_ahub', status='PROPOSAL (no P&R before GEOM PASS)',
                summary=dict(s, clock=dict(pin_xy=CK, hub_xy=HUB, spine_um=HUB[1],
                             max_spine_to_tap_um=round(max(spine_d(t) for t in taps), 1))),
                blocks=blocks, regions=regions, clock_taps=taps, pins=pins,
                reuse_views={'ot_nhb_zh': 'physical/ref_tile/ot_nhb_zh_m5/views/ot_nhb_zh',
                             'ot_qkh_recip_leaf': 'physical/ref_tile/qkh_recip_ref/views/ot_qkh_recip_leaf'},
                prior_closed_composition='physical/ref_tile/qkd_ahub_sdw (qkd_ahub_static_dw 734.4 x 540, same children)',
                open_items=['re-sign ot_nhb_zh_m5 + qkh_recip_ref views with current signoff.py (NOT RUN)',
                            'kit generator: SYNTH_HIERARCHICAL + blackbox children + MACRO_PLACEMENT_TCL from blocks[]',
                            'KV-P: shrink hub_C slot ahub to this outline (S-E corner fixed) + core_pins_v37p re-pin',
                            'clock: per-child tap delay balance to one 20-ps window; publish core latency'])
    (out / 'qkd_ahub_fp_proposal.json').write_text(json.dumps(plan, indent=1) + '\n')
    render(out / 'qkd_ahub_fp_proposal.png')
    print(json.dumps(s))


if __name__ == '__main__':
    main()
