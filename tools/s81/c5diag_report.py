#!/usr/bin/env python3
"""c5 diagnosis (2026-10-13): congestion.json + CONGESTION.md from the per-case c5diag_congestion.py outputs.
usage: c5diag_report.py <c5 cong.json> <c3 cong.json> <chains dir (c5diag_chain_trace.py JSONs, <case>_<name>.json)> <out dir>"""
import glob, json, os, re, sys
from collections import Counter

c5f, c3f, chd, outd = sys.argv[1:5]
A, B = json.load(open(c5f)), json.load(open(c3f))
GRT = dict(c5=dict(total=1053305, M4=0, M5=74, M6=526533, M7=33139, M8=457718, M9=35841, max_h=565, max_v=180, wirelength_um=1677675129),
           c3=dict(total=830691, M4=0, M5=33, M6=399293, M7=32691, M8=362720, M9=35954, max_h=601, max_v=157))
T = GRT['c5']['total']
pc = lambda v, t=T: '%.1f%%' % (100.0 * v / t)


def classes(d):
    c = Counter()
    for r in d['by_region']:
        c['frame_* (128 field frames)' if r['name'].startswith('frame_') else r['name']] += r['overflow']
    return c


def slim(d, nb, full):
    o = {k: d[k] for k in ('case', 'gcell_um', 'grid', 'overflow_total', 'overflow_gcells', 'by_layer', 'unwrap_check', 'attribution_check',
                           'attributed_total', 'concentration', 'rects', 'focus', 'length_census', 'nets_def', 'guide')}
    o['region_classes'] = dict(classes(d).most_common())
    o['frames'] = d['frames']
    o['by_covering_instance'] = d['by_covering_instance'][:30]
    o['buses'] = d['buses'][:nb]
    o['pairs'] = d['pairs'][:20]
    o['hot_windows_480um'] = d['hot_windows_480um']
    if full:
        o['by_region'] = d['by_region']
        o['families'] = d['families'][:60]
        o['grid_480um'] = d['grid_480um']
        o['grid_480um_layers'] = d['grid_480um_layers']
        o['worst_util_480um'] = d['worst_util_480um']
        o['hops_over_limit'] = d['hops_over_limit']
        o['big_instances'] = d['big_instances']
    return o


chains = {}
for f in sorted(glob.glob(os.path.join(chd, '*.json'))):
    c = json.load(open(f))
    rows = c.pop('rows')
    c['from_pin'], c['to_pin'] = rows[0]['from_pin'], rows[-1]['to_pin']
    c['hops_over_500um'] = sum(r['manh'] > 500 for r in rows)
    c['relays'] = [[r['to'].split('.')[0], r['master'], r['x'], r['y'], r['manh']] for r in rows]
    chains[os.path.basename(f)[:-5]] = c
ca, cb = classes(A), classes(B)
cmp_regions = [dict(region=k, c5=ca.get(k, 0), c3=cb.get(k, 0), delta=ca.get(k, 0) - cb.get(k, 0)) for k in sorted(set(ca) | set(cb), key=lambda k: -ca.get(k, 0))]
cmp_rects = [dict(rect=k, box=v['rect'], c5=v['overflow'], c3=B['rects'][k]['overflow'], delta=v['overflow'] - B['rects'][k]['overflow'],
                  c5_util={l: round(a / max(1, b), 3) for l, (a, b) in v['demand_over_capacity'].items()},
                  c3_util={l: round(a / max(1, b), 3) for l, (a, b) in B['rects'][k]['demand_over_capacity'].items()}, c5_buses=v['buses'][:3])
             for k, v in A['rects'].items()]
bb = {r['name']: r for r in B['buses']}
cmp_buses = [dict(bus=r['name'], c5_bits=r['bits'], c5=r['overflow'], c3_bits=bb.get(r['name'], {}).get('bits'), c3=bb.get(r['name'], {}).get('overflow'))
             for r in A['buses'][:12]]
rec = dict(schema='opentallas.s81.c5_congestion_diagnosis.v1', date='2026-10-13', method=A['method'],
           grt_log=GRT, mapped_vs_grt={c: dict(mapped=d['overflow_total'], grt=GRT[c]['total'], missing=GRT[c]['total'] - d['overflow_total'])
                                       for c, d in (('c5', A), ('c3', B))},
           c5=slim(A, 40, True), c3=slim(B, 20, False), compare=dict(regions=cmp_regions, rects=cmp_rects, buses=cmp_buses), chains=chains)
os.makedirs(outd, exist_ok=True)
json.dump(rec, open(os.path.join(outd, 'congestion.json'), 'w'), indent=1)

L = []
w = L.append
w('# S81 die c5 (contract v13): where the GRT overflow sits\n')
w('2026-10-13. Run `/srv/opentallas-scratch/claude/s81-die-iter/c5` (EPYC1), reference c3 (v11). Numbers: `congestion.json`; '
  'tools `tools/s81/c5diag_*`. All values measured from `ckpt_grt.odb`, `route.guide`, `wirelength_grt.csv`, the placed DEF and LEFs.\n')
w('## Method and check\n')
w('- Overflow per gcell (9.6 um) and layer = unwrapped odb usage - raw tracks. The odb GCell grid stores usage = net usage + reductions in 8 bits, '
  'so it wraps where the overflow is worst; the net usage was rebuilt from the guides and used to unwrap it '
  '(c5: %d M6 and %d M8 gcells wrapped, 0 ambiguous).' % (A['unwrap_check']['M6']['gcells_wrapped'], A['unwrap_check']['M8']['gcells_wrapped']))
w('- Mapped total c5 %s of the GRT %s (%.2f%%); c3 %s of %s. M6 and M8 equal the GRT log exactly, guide usage equals the GRT demand exactly. '
  'Not mapped: %d (c5) on M5 / M7 / M9 in the non-preferred direction.' % (format(A['overflow_total'], ','), format(T, ','), 100.0 * A['overflow_total'] / T,
                                                                          format(B['overflow_total'], ','), format(GRT['c3']['total'], ','), T - A['overflow_total']))
w('- Net attribution: a gcell\'s overflow is split equally over the nets whose guides use that gcell\'s edge on that layer. '
  'A share is the family\'s share of the wires in overflowed gcells, not a causal proof.\n')
fr, rx = A['frames'], A['rects']
lp = fr['local_profile']
col = sum(sum(lp[l]['by_local_x_48um'][7:10]) for l in lp)
xl = A['focus']['xlane']['own_overflow']
qb = A['focus']['qbank_eb']['own_overflow']
cw, cw3 = chains.get('c5_wq_d_bit0'), chains.get('c3_wq_d_bit0')
st, pin = rx['vch_E_strip_N'], rx['ctrl_svc_pinch']
st3, pin3 = B['rects']['vch_E_strip_N'], B['rects']['ctrl_svc_pinch']
w('## Findings (measured; "reading" lines are inference)\n')
w('1. **Field frames: %s (%s), identical in c3 (%s).** Every one of the 128 frames holds %d..%d. x-lane relay -> slot-station buses '
  '(n_xa 283 b, n_xb 266 b) %s (%s); q-element -> qbank %s (%s). %s of it (%.0f%%) lies in the frame-local column x 336-480 um (the slot-station '
  'column), in rows at the slot pitch. Sample frame_20: overflow rows are 10-20 um tall at x 691-797 um; whole-frame demand / capacity M6 0.07, M8 0.03. '
  'Reading: pin-access rows under the station S-face pins, not a track shortage; v13 did not touch it.'
  % (format(fr['overflow'], ','), pc(fr['overflow']), format(B['frames']['overflow'], ','), fr['per_frame_min'], fr['per_frame_max'], format(int(xl), ','), pc(xl),
     format(int(qb), ','), pc(qb), format(col, ','), 100.0 * col / fr['overflow']))
if cw and cw3:
    w('2. **Strip W of sp_hc_s (x 16,800-17,312, y 14,083-24,000): %s (%s); c3 %s; +%s = the whole c5 - c3 increase (+%s).** '
      'The wq_d chain sp_hc_s -> sp_vm is %d hops x 4,096 b with a %.0f um path for a %.0f um direct distance (x %.2f): 12 dsfd_hstnv_4096 relays step N from '
      'y 18,483 to 23,630, then 20 step S to 15,779 in the same 201-um-wide column (x 17,004 / 17,010). c3: %d hops, %.0f um path, max hop %.0f um. '
      'Strip demand / capacity M6 %.2f, M8 %.2f. Reading: the out-and-back relay walk, not the SU or corridor outline, is what v13 added.'
      % (format(st['overflow'], ','), pc(st['overflow']), format(st3['overflow'], ','), format(st['overflow'] - st3['overflow'], ','),
         format(T - GRT['c3']['total'], ','), cw['hops'], cw['path_manh_um'], cw['direct_manh_um'], cw['detour'], cw3['hops'], cw3['path_manh_um'], cw3['max_hop_um'],
         st['demand_over_capacity']['M6'][0] / st['demand_over_capacity']['M6'][1], st['demand_over_capacity']['M8'][0] / st['demand_over_capacity']['M8'][1]))
w('3. **ctrl_SW / svc_SW gap (x 6,720-8,160, y 960-1,920): %s (%s); c3 %s.** n_rq_SW 10,912 b + n_rd_SW_r_data 8,192 b, svc_c <-> ctrl with no relay at '
  'either end, pin Manhattan 496 um, routed mean 1,122 / 1,068 um, max 3,130 um. Box demand / capacity M8 %.2f, M9 %.2f; M8 at 92-101 of 102 tracks in the '
  'gap rows y 1,190-1,526 across x 6,720-8,064.'
  % (format(pin['overflow'], ','), pc(pin['overflow']), format(pin3['overflow'], ','), pin['demand_over_capacity']['M8'][0] / pin['demand_over_capacity']['M8'][1],
     pin['demand_over_capacity']['M9'][0] / pin['demand_over_capacity']['M9'][1]))
w('4. 1 + 2 + 3 = %s. The v13 SU slot, SM column, both HC columns and the corridor hold %d, %d, %d and %d.'
  % (pc(fr['overflow'] + st['overflow'] + pin['overflow']), rx['su_v13']['overflow'], rx['sm_column_v13']['overflow'], rx['hc_column_all']['overflow'],
     rx['corridor_v13']['overflow']))
w('5. The unbuffered sp_hc_s hops of v11 / v12 are gone: every net on an sp_hc_s pin is <= %.0f um pin-to-pin (c3: %.0f um, %s bits over 500 um). '
  'What remains over 500 um pin-to-pin is in section d.\n' % (A['focus']['at_sp_hc_s']['manh_quantiles'][4], B['focus']['at_sp_hc_s']['manh_quantiles'][4],
                                                              format(B['focus']['at_sp_hc_s']['bits_over_hop_manh'], ',')))
w('Not determined: whether the element pins on these nets are registered inside the views (d lists pin-to-pin hops only); the 712 overflow GRT books on '
  'M5 / M7 / M9 outside M6..M9 preferred-direction edges; drivers of multi-sink nets (the generated LEFs declare every pin INOUT; output pin names o / do0 / fo0 / dq '
  'are assumed); the frame row structure at gcell level beyond frame_20 (the 128-frame profile is aggregate); hc_y lanes other than lane 0 (the walk follows '
  'a lane-local bit index); c4 (killed before GRT finished).\n')
w('## a) By layer\n')
w('| layer | dir | overflow | share | gcells | max per gcell | GRT log |\n|---|---|---:|---:|---:|---:|---:|')
for ln, d in (('M6', 'H'), ('M8', 'H'), ('M7', 'V'), ('M9', 'V'), ('M5', 'V'), ('M4', 'H')):
    v = A['by_layer'][ln]
    w('| %s | %s | %s | %s | %s | %d | %s |' % (ln, d, format(v['overflow'], ','), pc(v['overflow']), format(v['gcells'], ','), v['max'], format(GRT['c5'][ln], ',')))
w('\nHorizontal M6 + M8 = %s. %d of 9.3 M gcells x 4 layers overflow; %d of the 480-um windows hold any; top 10 windows %.1f%%, top 20 %.1f%%.\n'
  % (pc(A['by_layer']['M6']['overflow'] + A['by_layer']['M8']['overflow']), A['overflow_gcells'], A['concentration']['windows_with_overflow'],
     100 * A['concentration']['top10_share'], 100 * A['concentration']['top20_share']))
w('## a) By region (generator `where()` names) and c3 comparison (e)\n')
w('| region | c5 overflow | share of 1,053,305 | c3 overflow | delta |\n|---|---:|---:|---:|---:|')
for r in cmp_regions:
    if max(r['c5'], r['c3']) >= 200:
        w('| %s | %s | %s | %s | %+d |' % (r['region'], format(r['c5'], ','), pc(r['c5']), format(r['c3'], ','), r['delta']))
f = A['frames']
w('\nField frames: %d frames, per frame min / median / max = %d / %d / %d (c3: %d / %d / %d). Top buses in the frames: %s. Under: %s.\n'
  % (f['frames'], f['per_frame_min'], f['per_frame_median'], f['per_frame_max'], B['frames']['per_frame_min'], B['frames']['per_frame_median'],
     B['frames']['per_frame_max'], ', '.join('%s %s' % (n, format(v, ',')) for n, v in f['buses'][:4]),
     ', '.join('%s %s' % (n, format(v, ',')) for n, v in f['covering'].items())))
w('Fixed boxes (same coordinates in both runs; util = guide demand / effective capacity of the box):\n')
w('| box | x0,y0,x1,y1 um | c5 | share | c3 | delta | c5 util M6/M7/M8/M9 | top buses (c5) |\n|---|---|---:|---:|---:|---:|---|---|')
for r in cmp_rects:
    u = r['c5_util']
    w('| %s | %s | %s | %s | %s | %+d | %.2f / %.2f / %.2f / %.2f | %s |'
      % (r['rect'], ','.join('%g' % v for v in r['box']), format(r['c5'], ','), pc(r['c5']), format(r['c3'], ','), r['delta'], u['M6'], u['M7'], u['M8'], u['M9'],
         '; '.join('%s %s' % (n, format(v, ',')) for n, v in r['c5_buses'])))
w('\n## a) Top 20 hot windows (480 x 480 um)\n')
w('| x um | y um | overflow | share | layers | region | top buses |\n|---|---|---:|---:|---|---|---|')
for h in A['hot_windows_480um']:
    w('| %g-%g | %g-%g | %s | %s | %s | %s | %s |' % (h['x'][0], h['x'][1], h['y'][0], h['y'][1], format(h['overflow'], ','), pc(h['overflow']),
                                                    ' '.join('%s %d' % kv for kv in h['layers'].items()), ', '.join(h['regions']),
                                                    '; '.join('%s %s' % (n, format(v, ',')) for n, v in h['buses'][:3])))
w('\n## b) Top 20 net families (bus = base name, digits -> #, relay-hop suffix dropped)\n')
w('| bus | driver -> sink kind | bits (hop-bits) | bus instances | overflow | share | bits on overflowed gcells | routed mean / max um | pin Manhattan mean / max um |\n|---|---|---:|---:|---:|---:|---:|---:|---:|')
for r in A['buses'][:20]:
    w('| %s | %s | %s | %d | %s | %s | %s | %.0f / %.0f | %.0f / %.0f |' % (r['name'], r['pair'], format(r['bits'], ','), r['bus_instances'], format(int(r['overflow']), ','),
                                                                     pc(r['overflow']), format(r['bits_on_overflowed_gcells'], ','), r['wl_mean'], r['wl_max'],
                                                                     r['manh_mean'], r['manh_max']))
w('\nBy driver -> sink kind: ' + '; '.join('%s %s (%s)' % (r['name'], format(int(r['overflow']), ','), pc(r['overflow'])) for r in A['pairs'][:6]) + '.\n')
w('## c) The sp_hc_s buses y_d (8,192 b) and wq_d (4,096 b)\n')
fa, fb = A['focus'], B['focus']
w('| group | run | hop-bits | own overflow | share | overflow of the gcells they use | share | pin Manhattan p50 / p99 / max | routed p50 / p99 / max | bits > 500 um Manhattan | 2+ pin bits routed > 500 um |\n|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|')
for k in ('at_sp_hc_s', 'wq_d', 'hc_y', 'hc_chains', 'ctrl_svc', 'xlane', 'qbank_eb'):
    for c, d, t in (('c5', fa, T), ('c3', fb, GRT['c3']['total'])):
        v = d[k]
        w('| %s | %s | %s | %s | %s | %s | %s | %.0f / %.0f / %.0f | %.0f / %.0f / %.0f | %s | %s |'
          % (k, c, format(v['bits'], ','), format(int(v['own_overflow']), ','), pc(v['own_overflow'], t), format(v['overflow_of_those_gcells'], ','),
             pc(v['overflow_of_those_gcells'], t), v['manh_quantiles'][1], v['manh_quantiles'][3], v['manh_quantiles'][4], v['wl_quantiles'][1],
             v['wl_quantiles'][3], v['wl_quantiles'][4], format(v['bits_over_hop_manh'], ','), format(v['bits_over_hop_wl'], ',')))
w('\nGroups: at_sp_hc_s = every net on an sp_hc_s pin; wq_d / hc_y = the whole relay chains; hc_chains = both; ctrl_svc = n_rq/rd/wd_SW; '
  'xlane = n_xa/n_xb relay -> slot station; qbank_eb = q element -> qbank.\n')
w('Chain walks (one bit, placed DEF):\n')
w('| chain | run | hops | path um | direct um | path / direct | max hop um | hops > 500 um |\n|---|---|---:|---:|---:|---:|---:|---:|')
for k, c in chains.items():
    w('| %s -> %s | %s | %d | %.0f | %.0f | %.2f | %.0f | %d |' % (c['start'], c['end'], k.split('_')[0], c['hops'], c['path_manh_um'], c['direct_manh_um'], c['detour'],
                                                              c['max_hop_um'], c['hops_over_500um']))
H = A['hops_over_limit']
w('\n## d) Hops longer than 500 um (work list, sorted by bits x um)\n')
w('%s. 2-pin nets over 500 um pin-to-pin: %s bits; multi-sink nets: %s bits; 2-pin nets routed over 500 um: %s bits. '
  'Clock / reset distribution nets are marked ck.\n' % (H['note'], format(H['pin_manhattan']['bits_2pin'], ','), format(H['pin_manhattan']['bits_multi_sink'], ','),
                                                       format(H['routed_wl']['bits_2pin'], ',')))


def hops(title, rows, n=None):
    w('%s (%d rows%s):\n' % (title, len(rows), '' if n is None or len(rows) <= n else ', first %d shown, all in congestion.json' % n))
    w('| family | kinds | bits over / total | mean um | max um | bits x um | pin Manhattan mean | routed mean | no relay at either end | ck |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for r in rows[:n]:
        w('| %s | %s | %s / %s | %.0f | %.0f | %s | %.0f | %.0f | %s | %s |' % (r['name'], r['pair'], format(r['bits_over'], ','), format(r['bits_total'], ','), r['mean_um'],
                                                                           r['max_um'], format(int(r['bits_x_um']), ','), r['manh_mean'], r['wl_mean'],
                                                                           format(r['no_relay_end_bits'], ','), 'ck' if r['clock_or_reset_name'] else ''))
    w('')


hops('Pin-to-pin Manhattan > 500 um, 2-pin nets, by endpoint', H['pin_manhattan']['two_pin_by_endpoint'])
hops('Pin-to-pin Manhattan > 500 um, multi-sink nets, by endpoint', H['pin_manhattan']['multi_sink_by_endpoint'])
hops('Routed GRT length > 500 um, 2-pin nets, by bus', H['routed_wl']['two_pin_by_bus'], 45)
hops('Routed tree > 500 um, multi-sink nets, by bus (tree length, not a hop)', H['routed_wl']['multi_sink_tree_by_bus'], 15)
open(os.path.join(outd, 'CONGESTION.md'), 'w').write('\n'.join(L) + '\n')
print('wrote', outd, len(L), 'lines')
