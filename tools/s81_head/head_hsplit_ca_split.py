#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: count-aligned bind roles for the split host (sidecar transform, new file only).
host -> host_w (every CA record), host_e = sibling CA origin of host_w on the SAME start-tree parent (same START
arrival, same stages), frame clock region 'host'. Seam ports are synchronous (same clock region): not table ports."""
import json, sys, copy
src, dst = sys.argv[1], sys.argv[2]
s = json.load(open(src))
s['ports'] = [r for r in s['ports'] if not r['port'].startswith('host_l1')]
ca = s['count_aligned']
def ren(name, new):
    return new if name == 'host' else (name[:-len('->host')] + '->' + new if isinstance(name, str) and name.endswith('->host') else name)
def sub(o, new):
    if isinstance(o, dict): return {ren(k, new): sub(v, new) for k, v in o.items()}
    if isinstance(o, list): return [sub(v, new) for v in o]
    return ren(o, new) if isinstance(o, str) else o
added = {}
for key in ('parts', 'regions', 'frame_clock_regions'):
    d = ca[key]; v = d.pop('host')
    d['host_w'] = sub(v, 'host_w'); d['host_e'] = sub(v, 'host_e'); added[key] = 2
# region tag stays 'host' for frame clocks (both halves on one frame clock region)
ca['frame_clock_regions']['host_w'] = ca['frame_clock_regions']['host_e'] = 'host'
sp = ca['start_ports']
for k in [k for k in sp if k.endswith('->host')]:
    v = sp.pop(k); sp[ren(k, 'host_w')] = sub(v, 'host_w'); sp[ren(k, 'host_e')] = sub(v, 'host_e')
pins = ca['start_pins']
for k in [k for k in pins['ports'] if k.endswith('->host')]:
    v = pins['ports'].pop(k); pins['ports'][ren(k, 'host_w')] = sub(v, 'host_w'); pins['ports'][ren(k, 'host_e')] = sub(v, 'host_e')
tp = pins['type_pins']; v = tp.pop('hd_host'); tp['hd_host_w'] = dict(v); tp['hd_host_e'] = dict(v)
outs = []
for r in pins['die_outputs']:
    if r.get('dst_part') == 'host':
        outs.append(sub(r, 'host_w')); e = sub(r, 'host_e'); e['net'] = r['net'] + '_e'; outs.append(e)
    else: outs.append(r)
pins['die_outputs'] = outs
# raw START exports: by position (rst_start_raw_0 at x 635.6 = W; 1..3 at x >= 726 = E); filled by the raw-start step
for r in pins['reset_inputs']:
    if r.get('src_part') == 'host':
        r['src_part'] = 'host_w' if r['src_port'] == 'rst_start_raw_0' else 'host_e'
        r['net'] = r['net'].replace('wr_host__', 'wr_%s__' % r['src_part'])
for cp in ('collector',):
    pass
json.dump(s, open(dst, 'w'), indent=1)
print(json.dumps(dict(added=added, die_outputs=len(outs))))
