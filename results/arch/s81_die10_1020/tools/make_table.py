# S81-DIE10: mu5k / mu5r GRT class table (json + md) from grt_class_<case>.json + GRT's own per-layer report.
import json, sys
from pathlib import Path
A = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
GRT = {'mu5k': dict(total=854368, M2=31574, M3=81322, M4=332457, M5=227272, M6=155182, M7=26561, maxH=353, maxV=357,
                    phy='REAL ot_hbm3e_phy_v41x_aw30_e8p5_k LEF (--macro-views)', runtime='01:26:22 GRT, 55.7 GB'),
       'mu5r': dict(total=4090822, M2=1038688, M3=554430, M4=1242834, M5=553686, M6=502034, M7=199150, maxH=435, maxV=624,
                    phy='stand-in rv_phy_hbm (pin-only)', runtime='4h43m GRT')}
LAYERS = ['M2', 'M3', 'M4', 'M5', 'M6', 'M7']
FIX = {
    'PHY': 'PHY ESCAPE BAND: registered n32s CTRL south-face pin order (max 149 um, 0 > 405) + 86.4 um M6/M7 escape band over the PHY body (Codex 7991d0177: M6 band count-only PASS 742 at 55%); full-U upper leg 408.4 > 405 needs one landed hop or a 4 um shorter U',
    'CTRL': 'RE-PLACE: real n32s CTRL body 388.8x324 centred in the 1062.5 um pair pitch, array +86.4 um north (mu6 plan) -> opens a CTRL<->PHY seam channel; per-pair cut 1244 -> 476 wires (n32s pinplan)',
    'svc_rs': 'WIDER CHANNELS + PIN REBALANCE: svc_rs face 6.7-8.2 pins/um > 6/um -> two-layer (M4+M6) face pins / face rebalance in the svc_rs kit (S81.BIND.SM.1); re-derive Codex --placefix (+70 um) jointly with the +86.4 CTRL shift (74 relay overlaps)',
    'frame': 'MORE LANDED LANES: frame-row lane channels carry the 276-bit xring/jw lanes on M4/M5 only; split each long lane into landed regions with M6/M7 forwarded half-cycle hops and spread the lane bundle over two channel rows (no single 9.6 um gcell column >55% tracks)',
    'slice_col': 'WIDER CHANNELS: slice-column side channels -> widen by one 43.2 um lattice pitch where the column pair carries >2 lanes, or move lane relays onto the column face band',
    'serdes_lk': 'none needed (overflow negligible)', 'gunit': 'none needed (negligible)', 'seq_host': 'none needed (small); keep the seqhost lane on its landed relay chain',
    'bk_topk': 'TOPK slot growth 324x540 -> 518.4x648 (06:29 decision) is area, not congestion; fold into mu7 repack',
}
tab = dict(schema='opentallas.s81_die10.grt_class_table.v1',
           method=('post-GRT guides of each run grt.odb (OpenROAD read-only dump, 26.6M/28.3M guides) rasterised on the 9.6 um GRT gcell '
                   'grid; capacity per gcell/layer = tracks (GRT track pitch) x (1 - layer adjustment) x (1 - macro OBS cover); M7 '
                   'blocked over macro footprints like M6 (GRT-0053 M7 resources == M6). The guide model over-counts (pin/via guides), '
                   'so every class number is also given CALIBRATED = model x (GRT layer overflow / model layer overflow).'),
           cases={})
md = ['# S81 mu5 GRT overflow class table (S81-DIE10, 10-20)', '',
      'Sources: ot-epyc7 /srv/opentallas-scratch/claude/s81-mu5/case_mu5k, case_mu5r (out/grt.odb, read-only); analysis '
      'die10_ana/{dump_guides.py,grt_class.py}. Signal layers M2-M7 only (`set_routing_layers -signal M2-M7`); macros '
      'block M2-M7, so all die signals route in the ~23% of the die not covered by macros; M8/M9 (2.08e9 track-gcells) '
      'carry 74 guides. ' + tab['method'], '']
for c in ('mu5k', 'mu5r'):
    r = json.load(open(A / f'grt_class_{c}.json')); g = GRT[c]
    scale = {L: (g[L] / r['layers'][L]['model_overflow']) if r['layers'][L]['model_overflow'] else 0 for L in LAYERS}
    def cal(layers):
        return int(round(sum(layers.get(L, 0) * scale[L] for L in LAYERS)))
    regions = {}
    for k, v in sorted(r['by_region'].items(), key=lambda kv: -kv[1]['total']):
        regions[k] = dict(view=r['class_view_status'].get(k), model=v['total'], calibrated=cal(v['layers']),
                          share=round(cal(v['layers']) / g['total'], 3),
                          over_block=v['over_block'], open_channel=v['open_channel'],
                          over_relay_h=v.get('over_relay_h', 0), over_relay_1b=v.get('over_relay_1b', 0), over_landing=v.get('over_frame_landing', 0),
                          layers_calibrated={L: int(round(v['layers'].get(L, 0) * scale[L])) for L in LAYERS}, fix=FIX.get(k, ''))
    zones = {k: dict(model=v['total'], calibrated=cal(v['layers'])) for k, v in r['by_zone'].items()}
    nets = sorted(((k, sum(v.values())) for k, v in r['net_class_in_overflow'].items()), key=lambda kv: -kv[1])[:12]
    hot = [dict(x_mm=h['x_mm'], y_mm=h['y_mm'], calibrated=cal(h['layers']), layers_calibrated={L: int(round(h['layers'].get(L, 0) * scale[L])) for L in LAYERS},
                classes=h['classes'], nets=list(h['guide_net_classes'])[:5]) for h in r['hot_tiles'][:12]]
    stat = {k: v for k, v in r['by_status'].items()}
    st_tot = sum(stat.values()) or 1
    phy = next(iter(r['phy_north_cut_rows'].values()))
    tab['cases'][c] = dict(grt=g, layer_scale=scale, regions=regions, zones=zones, view_status_model_share={k: round(v / st_tot, 3) for k, v in stat.items()},
                           net_classes_in_overflowed_gcells=nets, hot_tiles_1mm=hot, phy_north_cut_rows=phy, phy_faces=r['phy_face'])
    md += [f'## {c}: GRT total {g["total"]:,} (max H {g["maxH"]} / V {g["maxV"]}), PHY = {g["phy"]}, {g["runtime"]}', '',
           'Per layer (GRT): ' + ', '.join(f'{L} {g[L]:,}' for L in LAYERS), '',
           '| region (nearest big block) | view | calibrated overflow | share | M2 | M3 | M4 | M5 | M6 | M7 | over block | open channel | over relays/landings |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for k, v in regions.items():
        lc = v['layers_calibrated']; m = v['model'] or 1
        md.append(f"| {k} | {v['view']} | {v['calibrated']:,} | {v['share']:.1%} | " + ' | '.join(f'{lc[L]:,}' for L in LAYERS) +
                  f" | {v['over_block'] / m:.0%} | {v['open_channel'] / m:.0%} | {(v['over_relay_h'] + v['over_relay_1b'] + v['over_landing']) / m:.0%} |")
    md += ['', 'Zones (calibrated): ' + ', '.join(f'{k} {v["calibrated"]:,}' for k, v in zones.items()) +
           f'. Model overflow by view status: ' + ', '.join(f'{k} {v:.0%}' for k, v in tab['cases'][c]['view_status_model_share'].items()), '',
           'Net classes of guides through overflowed gcells (guide count): ' + ', '.join(f'{k} {n:,}' for k, n in nets), '',
           '| hot 1 mm tile x,y (mm) | calibrated | worst layers | dominant regions | nets |', '|---|---:|---|---|---|']
    for h in hot[:8]:
        wl = ', '.join(f'{L} {n:,}' for L, n in sorted(h['layers_calibrated'].items(), key=lambda kv: -kv[1])[:3])
        md.append(f"| {h['x_mm'][0]:.0f}-{h['x_mm'][1]:.0f}, {h['y_mm'][0]:.0f}-{h['y_mm'][1]:.0f} | {h['calibrated']:,} | {wl} | " +
                  ', '.join(list(h['classes'])[:3]) + ' | ' + ', '.join(h['nets'][:4]) + ' |')
    md += ['', 'PHY north-face cut rows (vertical layers, demand/capacity along the 8.5 mm face; row k = k x 9.6 um above the PHY; '
           'blocked = fraction of the row under a macro, ctrl = under a CTRL):', '',
           '| row | y um | M3 | M5 | M7 | blocked | ctrl |', '|---:|---:|---:|---:|---:|---:|---:|']
    for row in phy[:10]:
        md.append(f"| {row['row']} | {row['y_um']:.0f} | " + ' | '.join(str(row.get(L, {}).get('ratio')) for L in ('M3', 'M5', 'M7')) +
                  f" | {row['blocked_frac']} | {row['ctrl_frac']} |")
    md.append('')
md += ['## PHY face cut vs track (inputs: Codex codex/s81-mu6-realctrl-1020@2c1992f60)', '',
       '- Real PHY face: 1,244 bits per controller pair over a 531.25 um pair window (16 pairs, 19,904 bits). Stand-in CTRL E-face funnel: max 631 um, 9,952 bits > 405 um.',
       '- n32s CTRL registered south-face pin order: per-pair horizontal cut 1,244 -> 476 wires; PHY escape max 149 um, 0 bits > 405.',
       '- M6 escape band 86.4 um: native raw 1,350 / 55% = 742 count-only PASS (alternating 675/371 FAIL); 129.6 um envelope 1,012/556 count-only; north guard 250.96; full-U upper leg 408.4 > 405 (FAIL by 3.4 um).',
       '- M7 two-leg 2,488 per pair vs native 4,565 (count-only), alternating 2,282 FAIL. Actual M3/M5 pin via 4/2 cuts, native PG + track assignment and electrical proof still owed.',
       '- Measured here (mu5k, real PHY): the ring rows directly north of the PHY are mostly under CTRL stand-ins / relays (see blocked/ctrl columns): the PHY bits must pass through gaps in the CTRL row -> this is the CTRL seam, not a lack of tracks over the 8.5 mm face (M7 at row 1 is almost unused).', '']
md += ['## Structural fix per class (no reruns)', '']
for k, f in FIX.items():
    md.append(f'- **{k}**: {f}')
md += ['- **relay lanes (relay_h / relay_1b / landings in channels)**: overflow sits over or next to the 3,113 dvrlyh + 5,137 rly_1 '
       'stations in 1-gcell-wide channels -> LANE CHANNEL WIDTH = ceil(bits x 1.82 / tracks per um) (55% rule) per channel, '
       'stations staggered (no two 276-bit stations in the same gcell column), and long lanes moved to M6/M7 between landed regions.',
       '- **all classes**: signal layers capped at M7 while macros block M2-M7 and M8/M9 stay empty: open M8 (and M9) as a '
       'die-level signal layer for the long landed lanes (repeater/hop cells already in channels); this is the largest '
       'track supply left (2.08e9 track-gcells vs 0.55e9 M6+M7).', '']
json.dump(tab, open(OUT / 'grt_class_table.json', 'w'), indent=1)
(OUT / 'grt_class_table.md').write_text('\n'.join(md) + '\n')
print('TABLE_DONE', OUT)
