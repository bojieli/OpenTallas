#!/usr/bin/env python3
"""DRIVE-S81-IDX4 (10-20): add the two --idxrd 4 die hooks to bind_table_p4l3_mu.json (idempotent).
  dsdv_slice_iq        = dsdv_slice with module ot_s81sl_slice_iq (+ iq [512:0] = 2 x 276 lanes, framing-aware split of bo)
  dsfd_bk_selector_vm  = dsfd_bk_selector with module dsdv_bk_sel_vm (+ vi_idx landed lane; ca / cb rank-tree child
                         lanes and vm_fault as die top ports)
dv_plan --idxrd 4 places s_3S / bk_sel on these masters; --idxrd 0 / 3 plans never reference them."""
import copy, json, sys
from pathlib import Path
p = Path(sys.argv[1] if len(sys.argv) > 1 else 'results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json')
t = json.loads(p.read_text())
M = t['masters']
s = copy.deepcopy(M['dsdv_slice'])
s['module'] = 'ot_s81sl_slice_iq'
s['ref'] = 'DRIVE-S81-IDX4 rtl/dsrom_sys/s81_dv/idx/dsdv_idx_bsplit.sv (ot_s81sl_slice unchanged inside)'
s['ports']['iq.o'] = {'hb': 1, 'lanes': [{'split': [['iq', 0, 0, 276]]}, {'split': [['iq', 276, 0, 237]]}]}
s['port_note'] = ('--idxrd 4 s_3S: iq = the index frames (types 4 / 8 / 10) of the band-port-B stream, split by '
                  'dsdv_idx_bsplit (bo keeps every other frame for the svc entry; +1 edge on both)')
M['dsdv_slice_iq'] = s
b = copy.deepcopy(M['dsfd_bk_selector'])
b['module'] = 'dsdv_bk_sel_vm'
b['ref'] = 'DRIVE-S81-IDX4 rtl/dsrom_sys/s81_dv/idx/dsdv_bk_sel_vm.sv (dsdv_idx_vmux + dsdv_bk_sel unchanged)'
b['ports']['vi_idx.i'] = {'port': 'vi_idx', 'lane': 276, 'land': True}
b['top_ports'] = [{'port': 'ca', 'dir': 'input', 'bits': 276}, {'port': 'cb', 'dir': 'input', 'bits': 276},
                  {'port': 'vm_fault', 'dir': 'output', 'bits': 1}]
b['port_note'] = ('--idxrd 4 bk_sel: vi_s (column-4 rung) + vi_idx (score-chain tail is_tail) + ca / cb (rank-tree child '
                  'lanes, die ports: lower_bk shard_tree) merged by dsdv_idx_vmux into dsdv_bk_sel vi_s (+2 edges); '
                  'vm_fault = die status port')
M['dsfd_bk_selector_vm'] = b
rw = t['rtl_widths']
rw['ot_s81sl_slice_iq'] = dict(rw['ot_s81sl_slice'], iq=513)
rw['dsdv_bk_sel_vm'] = dict(rw['dsdv_bk_sel'], vi_idx=276, ca=276, cb=276, vm_fault=1)
for m in ('dsdv_slice_iq', 'dsfd_bk_selector_vm'):
    if m not in t['status_fault_masters']:
        t['status_fault_masters'].append(m)
p.write_text(json.dumps(t, indent=1) + '\n')
print('ok', p)
