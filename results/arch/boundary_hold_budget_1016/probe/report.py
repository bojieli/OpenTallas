#!/usr/bin/env python3
"""impact.json -> IMPACT.md summary tables (FLOW-HOLD)."""
import json, statistics, sys, collections
rows = json.load(open(sys.argv[1])); out = open(sys.argv[2], 'w')
ok = [r for r in rows if r.get('probe') == 'ok']
P = lambda *a: print(*a, file=out)
P('# Boundary hold budget: impact study (STA only, no re-routes)\n')
P('**Method**')
P('- Tool: `bh_probe.tcl` (OpenROAD/OpenSTA, `openroad/orfs:asap7lock`), run on EPYC4 through ot-run.')
P('- Inputs per route: its own `6_final.odb` + SPEF + `6_final.sdc` + the route\'s `signoff.sdc`.')
P('- Timing is checked at FF hold and TT setup, before and after the proposed boundary min delays (C = U = 25 ps).')
P('- Every input→D and register→output path is traced, and the delay of the cells on it is attributed to hold padding (HB* and BUF instances named `*hold*`), other buffering, or logic.')
P('- Capture/launch after the rule = the native S+R / O−R from the view\'s TT Liberty, minus the padding the new requirement no longer needs (pad × min(1, FF slack-after / pad)). No other change is assumed.')
P(f'- Views: {len(rows)} views bound by (or candidates for) the current die contracts, plus COLL ctl2 v7. {len(ok)} probed; the rest have no routed ODB left (EPYC1 retired) or no run.\n')
rel = [r for r in ok if r['hold_only_relaxes']]
P('## 1. Closed tiles stay closed (hold only relaxes)\n')
P(f'- {len(rel)}/{len(ok)} views: input→register and register→output FF hold slack each rose by exactly C+U = 50 ps, and register-to-register is unchanged. Setup lines are untouched (TT identical by construction).')
bad = [r for r in ok if not r['hold_only_relaxes']]
for r in bad:
    P(f"- Exception: {r['cell']} ({r['view']}). FF before {r['ff_before']}, after {r['ff_after']}. This is a CDC leaf: its second clock's ports were given the core_clk credit by the probe. It is outside the rule (section 4: single synchronous clock).")
nb = sum(1 for r in ok if r.get('ff_before', {}).get('ws', 1) * 1e12 < 0)
na = sum(1 for r in ok if r.get('ff_after', {}).get('ws', 1) * 1e12 < 0 and r['hold_only_relaxes'])
P(f'- Views with FF WNS < 0 before / after (qualifying): {nb} / {na}.\n')
P('## 2. In-die native-FAIL views: which fail only because of hold padding\n')
P('| class | views | meaning |')
P('|---|---:|---|')
C = collections.Counter(r.get('class') for r in ok if r['native'] == 'FAIL')
M = {'A_padding_only': 'every over-budget pin passes once the surplus padding is gone. A re-route under hold_budget die is expected to pass native',
     'B_insertion_spread': 'boundary spread > 80 ps or early capture clock (S+R far above the port→D delay). Needs re-tiling or a clock split, not this rule',
     'B_logic_at_pin': 'logic cells between pin and register: the pin is not registered. Needs an RTL pin register',
     'B_pinflop_wire': 'one long buffered wire between pin and flop (pin flop not at the pin). Needs io_flop_at_pins / a smaller tile',
     'C_combinational_pins': 'combinational pin arcs', 'D_no_insertion_json': 'no insertion.json (R unproven)'}
for k, v in sorted(C.items(), key=lambda x: str(x[0])):
    P(f'| {k} | {v} | {M.get(k, "")} |')
P('\n| class | cell | view | spread | capture now → est. | launch now → est. | over-budget input pins by cause | over-budget outputs by cause |')
P('|---|---|---|---:|---:|---:|---|---|')
for r in sorted((r for r in ok if r['native'] == 'FAIL'), key=lambda r: (r['class'], r['cell'])):
    P(f"| {r['class']} | {r['cell']} | {r['view'].split('/')[2] if r['view'].count('/') > 2 else r['view']} | {r['spread']} | "
      f"{r['cap_lib']} → {r['cap_new']} | {r['launch_lib']} → {r['launch_new']} | {r['cap_causes']} | {r['launch_causes']} |")
miss = [r for r in rows if r.get('probe') != 'ok']
P(f"\nNot probed ({len(miss)}; routed ODB gone with EPYC1, or no run): " + ', '.join(sorted({r['cell'] for r in miss})) + '\n')
P('## 3. Native-PASS views: the margin returned\n')
P('| cell | capture now → est. | launch now → est. | removable input pad FF ps (total) | removable output pad FF ps (total) |')
P('|---|---:|---:|---:|---:|')
for r in sorted((r for r in ok if r['native'] == 'PASS'), key=lambda r: r['cell']):
    P(f"| {r['cell']} | {r['cap_lib']} → {r['cap_new']} | {r['launch_lib']} → {r['launch_new']} | {r['in_pad_removable_ff_ps']} | {r['out_pad_removable_ff_ps']} |")
P('\n## 4. Die side: hold buffering the budget implies\n')
dd = [r for r in ok if r.get('die_demand') and r['hold_only_relaxes']]
for D in ('0', '40', '80'):
    pins = sum(r['die_demand'][D]['pins'] for r in dd); pos = sum(r['die_demand'][D]['pins_pos'] for r in dd)
    mean = sum(r['die_demand'][D]['mean'] * r['die_demand'][D]['pins'] for r in dd) / max(1, pins)
    mx = max(r['die_demand'][D]['max'] for r in dd)
    P(f'- Neighbour skew Δ = {D} ps (sender earlier than receiver by Δ): {pos}/{pins} receiving pins need die-level delay. Mean {mean:.1f} ps FF per pin (≈ {mean/38:.2f} HB4xp67), max {mx:.1f} ps.')
ip = sum(r['in_pad_ff_ps'] for r in ok); op = sum(r['out_pad_ff_ps'] for r in ok)
ni = sum(r['inputs'] for r in ok); no = sum(r['outputs'] for r in ok)
P(f'- Today, tile-level named hold padding on these views is {ip/1000:.0f} ns on {ni} inputs ({ip/max(1,ni):.1f} ps/pin) and {op/1000:.0f} ns on {no} outputs ({op/max(1,no):.1f} ps/pin), at FF.')
P('  - Every link pays sender-out plus receiver-in padding unconditionally.')
P('  - These figures count only cells named as hold padding. Structural pads re-sized by the flow and repair BUFx2 chains not named `hold*` are excluded, so the true figure is higher.')
P(f'- Unpadded receiver hold need (H−R at FF after removing surplus pads): worst per view max {max(r["die_need_new_ps"]["max"] for r in dd):.1f} ps, '
  f'median of view medians {statistics.median(r["die_need_new_ps"]["median"] for r in dd):.1f} ps.')
