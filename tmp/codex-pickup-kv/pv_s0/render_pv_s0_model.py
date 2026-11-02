#!/usr/bin/env python3
"""Render PVPAIR kv3_pv_pair 380.16x190.08 current S0 clock + separate real FT model (no placement invented).
Inputs: pins.json (kit, md5 3004e1f8...), island_ft.json, current_S0_clock_model_render_view.json, SRAM LEF."""
import json, re, sys
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
IN = Path(sys.argv[1]); VIEW = Path(sys.argv[2]); OUT = Path(sys.argv[3])
pins = json.load(open(IN / 'pins.json')); ift = json.load(open(IN / 'island_ft.json')); m = json.load(open(VIEW))
lef = (IN / 'macros/ot_sram_1r1w_32x128_m1.lef').read_text()
sw, sh = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef).groups())
clkrect = list(map(float, re.search(r'PIN clk.*?LAYER (\w+) ;\s*RECT ([\d. ]+);', lef, re.S).group(2).split()))
clklayer = re.search(r'PIN clk.*?LAYER (\w+) ;', lef, re.S).group(1)
W, H = 380.16, 190.08; CORE = (4.32, 4.32, 375.84, 185.76)
C = dict(s0='#2a6fdb', s1='#e8871e', clk='#d62828', s1clk='#7a7a7a', ft='#8e44ad', rst='#2a9d8f', ink='#222', mute='#777')
assert len(pins) == 1668
fig = plt.figure(figsize=(20, 13), dpi=110)
gs = fig.add_gridspec(3, 3, height_ratios=[2.3, 1.15, 1.25], hspace=0.35, wspace=0.18)
ax = fig.add_subplot(gs[0, :])
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.6, ec=C['ink']))
ax.add_patch(Rectangle((CORE[0], CORE[1]), CORE[2]-CORE[0], CORE[3]-CORE[1], fill=False, lw=0.8, ls=':', ec=C['mute']))
face = [p for p in pins if p['face'] == 'S']; inter = [p for p in pins if p['face'] != 'S']
for sl, col in (('s0', C['s0']), ('s1', C['s1'])):
    xs = [p['x'] for p in face if p['bus'].startswith(sl + '__')]
    ax.vlines(xs, -4.5 if sl == 's0' else -9, 0 if sl == 's0' else -4.5, colors=col, lw=0.35)
    ax.text(-4, -2.2 if sl == 's0' else -6.8, f'{sl} face {len(xs)}', ha='right', va='center', fontsize=8, color=col)
ax.text(W/2, -12, f'face S: {len(face)} pins, all M5, y=0 (x {min(p["x"] for p in face):.2f}..{max(p["x"] for p in face):.2f}); '
        f'interior: {len(inter)} M5 pins; total {len(pins)}', ha='center', va='top', fontsize=9, color=C['ink'])
# S0 clock entry + reset + S1 unused
sty = {'s0__clk': (C['clk'], 'S0 clk (ACTIVE)'), 's1__clk': (C['s1clk'], 'S1 clk unused/unconstrained'),
       's0__rst_n': (C['rst'], 's0 rst_n'), 's1__rst_n': (C['rst'], 's1 rst_n')}
for p in inter:
    if p['bus'] in sty: ax.plot(p['x'], p['y'], marker='s', ms=7 if 'clk' in p['bus'] else 4, color=sty[p['bus']][0], mec='k', mew=0.4, zorder=5)
ax.annotate('S0 clock entry s0__clk[0] M5 (190.104, 95.04) .048x.48\n29770 FF + 8 SRAM clk pins; S1 clk 190.488 unused\n(cluster: see zoom A)',
            xy=(190.1, 95.04), xytext=(205, 120), fontsize=9, color=C['clk'], arrowprops=dict(arrowstyle='->', color=C['clk']))
# FT ports and arcs (connectivity only)
pp = {p['bus']: p for p in inter if p['bus'].startswith('ft_ck')}
for a in ift['arcs']:
    s, t = pp[a['source']], pp[a['sink']]
    ax.plot([s['x'], t['x']], [s['y'], t['y']], color=C['ft'], lw=1.4, zorder=4)
    for q, mk in ((s, '>'), (t, 'D')): ax.plot(q['x'], q['y'], marker=mk, ms=7, color=C['ft'], mec='k', mew=0.4, zorder=6)
    for c in a['cells']: ax.add_patch(Rectangle((c['x_um'], c['y_um']), 1.62, 0.27, fill=False, ec=C['ft'], ls='--', lw=0.8))
lbl = {0: 'FT0 ft_ck_i_0 -> mp_isl0_ck0 BUFx24 -> ft_ck_o_0 (zoom B)', 1: 'FT1 ft_ck_i_1 -> mp_isl1_ck0 || mp_isl1_ck1 BUFx24 -> ft_ck_o_1 (zoom C)'}
ax.annotate(lbl[0], xy=(268.9, 146.75), xytext=(222, 160), fontsize=9, color=C['ft'], arrowprops=dict(arrowstyle='->', color=C['ft']))
ax.annotate(lbl[1], xy=(109, 51.7), xytext=(20, 30), fontsize=9, color=C['ft'], arrowprops=dict(arrowstyle='->', color=C['ft']))
ax.text(W/2, H+3, 'NOT PLACED: no std cells / SRAM placement exists (AUTO macro placement). Dashed = island_ft.json declared fixed sites,\n'
        'applied by island_ft.tcl at floorplan (not an ODB placement). Old pin-doc S1 core_tree EXCLUDED (unapplied).',
        fontsize=8.5, va='bottom', ha='center', color=C['mute'])
ax.set_xlim(-42, W + 8); ax.set_ylim(-20, H + 16); ax.set_aspect('equal')
ax.set_title('kv3_pv_pair 380.16 x 190.08 um (core R0 frame) - current S0 clock model + separate real FT scope', fontsize=12, pad=30)
ax.set_xlabel('x (um)'); ax.set_ylabel('y (um)'); ax.tick_params(labelsize=8)
# zooms
def zoom(axz, x0, x1, y0, y1, title, keys):
    for p in inter:
        if p['bus'] in keys:
            w, h = p.get('size', [0.048, 0.48])
            col = sty[p['bus']][0] if p['bus'] in sty else C['ft']
            axz.add_patch(Rectangle((p['x']-w/2, p['y']-h/2), w, h, color=col))
            axz.text(p['x'], p['y']+h/2+0.06*(y1-y0)/1.5, p['bus'], rotation=90, ha='center', va='bottom', fontsize=7.5, color=col)
    axz.set_xlim(x0, x1); axz.set_ylim(y0, y1); axz.set_title(title, fontsize=9.5); axz.tick_params(labelsize=7)
za = fig.add_subplot(gs[1, 0]); zoom(za, 189.9, 190.7, 94.6, 96.1, 'A: S0/S1 clock + reset entry (true pin sizes)', sty.keys())
za.text(189.92, 94.65, 'S0 .048x.48 ACTIVE; S1 .048x.48 native unused\nrst_n .024x.192', fontsize=7.5, color=C['ink'])
for ax_, a, (x0, x1, y0, y1) in ((fig.add_subplot(gs[1, 1]), ift['arcs'][0], (266.5, 271.5, 146.2, 147.5)), (fig.add_subplot(gs[1, 2]), ift['arcs'][1], (105.8, 112.4, 51.2, 52.4))):
    zoom(ax_, x0, x1, y0, y1, f"{'B' if a['k']==0 else 'C'}: FT{a['k']} {a['source']} -> {a['sink']} ({a['role']})", [a['source'], a['sink']])
    for c in a['cells']:
        ax_.add_patch(Rectangle((c['x_um'], c['y_um']), 1.62, 0.27, fill=False, ec=C['ft'], ls='--', lw=1))
        ax_.text(c['x_um']+0.81, c['y_um']-0.05, c['name'] + '\n(declared site)', ha='center', va='top', fontsize=7, color=C['ft'])
# inventory panel: SRAMs true size, not placed
iv = fig.add_subplot(gs[2, 0:2])
for i, (nm, mt) in enumerate(m['macro_clock_consumers'].items()):
    x = (i % 4) * (sw + 4); y = (1 - i // 4) * (sh + 6)
    iv.add_patch(Rectangle((x, y), sw, sh, fc='#eef2f7', ec=C['ink'], lw=0.8))
    iv.add_patch(Rectangle((x+clkrect[0], y+clkrect[1]), 0.6, 0.6, color=C['clk']))
    iv.text(x + sw/2, y + sh/2, nm.replace('.u_slice.', '.').replace('.u_mem', ''), ha='center', va='center', fontsize=7.5)
iv.set_xlim(-2, 4*(sw+4)); iv.set_ylim(-3, 2*(sh+6)); iv.set_aspect('equal'); iv.tick_params(labelsize=7)
iv.set_title(f'INVENTORY (not placed): 8 x ot_sram_1r1w_32x128_m1 {sw:.3f} x {sh:.3f} um (true scale), clk pin {clklayer} rect {clkrect} (red, enlarged)', fontsize=9.5)
tx = fig.add_subplot(gs[2, 2]); tx.axis('off')
fb = m['ff_consumers_by_top_instance_and_master']
txt = [ 'S0 clock model (mapped 1_synth_odb.v, pre-CTS)',
  f"FF on s0__clk[0]: {m['ff_clock_consumer_count']}",
  f"  DFFHQNx1 {m['ff_master_counts']['DFFHQNx1_ASAP7_75t_R']} / DFFASRHQNx1 {m['ff_master_counts']['DFFASRHQNx1_ASAP7_75t_R']}",
  f"  u_s0 {fb['u_s0/DFFHQNx1_ASAP7_75t_R']+fb['u_s0/DFFASRHQNx1_ASAP7_75t_R']}  u_s1 {fb['u_s1/DFFHQNx1_ASAP7_75t_R']+fb['u_s1/DFFASRHQNx1_ASAP7_75t_R']}",
  'SRAM clk pins on s0__clk[0]: 8 (u_s0 x4, u_s1 x4)',
  f"other clock nets: {len(m['other_clock_nets'])}; S1 instance pins: {m['unused_S1_connected_instance_pins']}",
  'SDC: create_clock clk 833 ps on s0__clk; no S1 clock',
  f"REQUIREMENT ONLY: >= {m['minimum_nonempty_FF_leaf_groups_at1500']} nonempty 1500-FF leaf groups",
  '  (ceil(29770/1500); not actual CTS, no latency credited)',
  '', 'Separate real FT scope (not S0 sinks):',
  '4 physical ports / 3 BUFx24 (mapped netlist):',
  '  mp_isl0_ck0 A=ft_ck_i_0 Y=ft_ck_o_0',
  '  mp_isl1_ck0 A=ft_ck_i_1 Y=ft_ck_o_1',
  '  mp_isl1_ck1 A=ft_ck_i_1 Y=ft_ck_o_1__p1',
  '   (__p1 joined to ft_ck_o_1 by ot_ft_short at FP)',
  'guards: raw PASS, ODB PASS, island_ft PASS3']
tx.text(0, 1, '\n'.join(txt), va='top', family='monospace', fontsize=8.6, color=C['ink'])
fig.savefig(OUT, bbox_inches='tight'); print(OUT)
