#!/usr/bin/env python3
"""H-NETLIST 0600 2026-10-16: retire VM client/group ports that have no static producer on the v16 die.

RTL (rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv):
  SW  NC 3->2   former client1 (DMA record "1") retired; clients 0 ARGMAX, 1 IDX (was 2); replay code 3->2
  NW  NC 3->0   former CP/FMV/FUSED record clients retired (no cq/cr ports); replay code 3->0
  NE  RG 5->4, WG 3->2   legacy HC read group3 / write group2 retired (hc_NE uses its LG pair slots);
                         COLL read group 4->3; bank master = SE shape (hfd_vms_bank_native_q1, sid port)
Spec edits (idempotent): new region vm_retire_0600.json (re-states the SW IDX client edges), NE COLL group in
vm_compact_0253.json, calendar field widths in complete_host_targets_2330.py (run it after this script).
Compiler: tools/hbm_static/vm_abi_remap_0600.py maps native-compact-0253 calendars to this ABI (cycles unchanged).
"""
import json
from pathlib import Path
SP = Path(__file__).resolve().parent / 'v16_specs'
B = 'H-NETLIST 0600 VM client retirement: SW local client IDX moved from client 2 to client 1 (NC 3->2)'
s = dict(region='vm_retire_0600', author='Claude H-NETLIST 0600', instances=[], clocks=[], straps=[], gaps=[],
         drop_v15_edges=['idx_cq', 'idx_cr'],
         edges=[dict(src=['hb_idx', 'cq', 0, 338], dst=['hb_vms_SW', 'cq', 338, 676], bits=338, clock='stream', basis=B),
                dict(src=['hb_vms_SW', 'cr', 274, 548], dst=['hb_idx', 'cr', 0, 274], bits=274, clock='stream', basis=B)],
         notes=[__doc__])
(SP / 'vm_retire_0600.json').write_text(json.dumps(s, indent=1) + '\n')
p = SP / 'vm_compact_0253.json'
c = json.loads(p.read_text())
for e in c['edges']:
    if e['src'] == ['hb_coll_NE', 'vm_rq', 0, 136]:
        e['dst'] = ['hb_vms_NE', 'rq', 408, 544]
        e['basis'] = 'H-NETLIST 0600: NE RG5->4 (legacy HC group3 retired); COLL is read group 3'
    if e['dst'] == ['hb_coll_NE', 'vm_rr', 0, 2056]:
        e['src'] = ['hb_vms_NE', 'rr', 6168, 8224]
        e['basis'] = 'H-NETLIST 0600: NE RG5->4 (legacy HC group3 retired); COLL is read group 3'
p.write_text(json.dumps(c, indent=1) + '\n')
for name in ('sm_vm', 'smvm_0030'):
    p = SP / f'{name}.json'
    d = json.loads(p.read_text())
    d['gaps'] = [g for g in d.get('gaps', []) if g['id'] != 'G-SMVM-VMCLIENT']
    p.write_text(json.dumps(d, indent=1) + '\n')
print('vm_retire_0600 applied')
