#!/usr/bin/env python3
"""d4f die-net over-reach census (coordinator / DIE-FLOW 10-17): every die net whose placed driver->farthest-load
Manhattan span exceeds the planning hop (405 um) is classified by what fixes it:
  RELAY   p2p / multicast data bus  -> forwarded-clock relay stations (relay layer; equal-age per bus)
  RESET   reset / por / rst_n nets  -> regional synchronous reset tree (H-NETLIST reset forest, DIE-CLOCK regions)
  CONFIG  static config / programme (ot_hbm_su_programme / ot_static_program_target / cfg_* / strap-like)
                                    -> registered config chain (one register per hop, load-time; no timing on the hot path)
  STATUS  status / fault / done back to host / vm_status (slow, registered at both ends) -> registered status chain
  TOP     die-level inputs (top_inputs: clocks/resets from ckgen pins) -> clock/reset distribution (DIE-CLOCK)
The die_relay_stations exporter relays RELAY + STATUS (it skips su_programme drivers and rst/reset ports); CONFIG and RESET
need their own structure.  Prints counts by class and by (driver master.port -> load master) and writes JSON.
    d4f_overreach.py CASE_DIR CONTRACT [--hop 405] [--out FILE]"""
import argparse, collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_relay_pass as RP  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('case'); ap.add_argument('contract'); ap.add_argument('--hop', type=float, default=405.0); ap.add_argument('--out')
a = ap.parse_args()
C = json.loads(Path(a.contract).read_text())
pl, nets, directions, top_inputs = RP.load_case(Path(a.case), C)
def cls(dmas, dport, n):
    p = dport.lower()
    if n in top_inputs: return 'TOP'
    if re.search(r'(^|_)(rst|reset|por)(_|n|$)|rst_n|_rstn', p): return 'RESET'
    if dmas in ('ot_hbm_su_programme', 'ot_static_program_target', 'ot_hbm_static_cfg_collar') or re.match(r'(cfg|io_cfg|desc|prog|strap)', p): return 'CONFIG'
    if re.search(r'(status|fault|_done$|done_|vmstat)', p): return 'STATUS'
    return 'RELAY'
cnt = collections.Counter(); bits = collections.Counter(); grp = collections.Counter(); worst = {}
for n, ends in nets.items():
    if len(ends) < 2: 
        continue
    drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']; lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
    if n in top_inputs:
        d0 = None; span = max(RP.md(x[2], y[2]) for x in lds for y in lds) if len(lds) > 1 else 0.0; key = ('TOP', n.split('[')[0], '')
    elif len(drv) == 1 and lds:
        d0 = drv[0]; span = max(RP.md(d0[2], l[2]) for l in lds)
    else:
        continue
    if span <= a.hop:
        continue
    if d0 is not None:
        dm = pl[d0[0]]['master']; k = cls(dm, RP.base(d0[1]), n)
        key = (k, f'{dm}.{RP.base(d0[1])}', ','.join(sorted({pl[l[0]]['master'] for l in lds}))[:120])
    else:
        k = 'TOP'
    cnt[k] += 1; grp[key] += 1
    if span > worst.get(k, (0, ''))[0]: worst[k] = (round(span, 1), n)
out = dict(hop_um=a.hop, nets_over=sum(cnt.values()), by_class=dict(cnt), worst=worst,
           top_groups=[dict(cls=k[0], driver=k[1], loads=k[2], nets=v) for k, v in grp.most_common(60)])
print(json.dumps({k: out[k] for k in ('hop_um', 'nets_over', 'by_class', 'worst')}))
for g in out['top_groups'][:25]:
    print(g)
if a.out: Path(a.out).write_text(json.dumps(out, indent=1))
