#!/usr/bin/env python3
"""hfd_vm wrapper spec: the VM / activation-multicast root has no RTL top.  This thin registered top instantiates the
existing x staging / multicast root ot_hbm_die_vm_multicast_root (Codex, physical/hbm_die_abstracts_20261006/
memory_control; 22 x ot_sram_1r1w_128x256_m1_r2c2, sim receipt vm_root_receipt.json) and binds it to the r16g die
ports:  SU(SW) -> VM write word (f_su_SW[2047:0] + f_su_NW[14:0] = wr_data 2063, then wr_v / bank / addr / owner on
f_su_NW), read request on f_su_SE, the four taps (one per stack) on the x trunks x*[2062:0] (x*[2067:2063] are the
segment's forwarded clocks), handshake / status to t_su_SW.  The reverse tap ACKs have no die net (cfg chain).
The other VM die ports (publication of SU activations, query to the tiles, index top-k in, quantiser and router
feeds) have no RTL: one placeholder register stage each (wrapper extra_out), marked in the view note."""
import json
from pathlib import Path

b = dict(clk='clk', por_n='rst_n')
b['wr_data'] = 'die:f_su_SW[0:2048]+f_su_NW[0:15]'
o = 15
for nm, w in (('wr_v', 1), ('wr_bank', 1), ('wr_addr', 7), ('wr_owner', 192), ('wr_ACK_ready', 1)):
    b[nm] = f'die:f_su_NW[{o}:{o + w}]'
    o += w
o = 0
for nm, w in (('rd_v', 1), ('rd_bank', 1), ('rd_addr', 7), ('rd_owner', 192)):
    b[nm] = f'die:f_su_SE[{o}:{o + w}]'
    o += w
b['tap_ready'] = 'const:15'
b['tap_ACK_v'] = 'cfg'
b['tap_ACK_owner'] = 'cfg'
b['tap_data'] = 'die:' + '+'.join(f'x{q}[0:2063]' for q in ('SW', 'NW', 'SE', 'NE'))
o = 0
for nm, w in (('wr_ready', 1), ('wr_ACK_v', 1), ('rd_ready', 1), ('native_release', 1), ('drained', 1),
              ('fault', 1), ('tap_v', 4), ('wr_ACK_owner', 192), ('tap_owner', 768)):
    b[nm] = f'die:t_su_SW[{o}:{o + w}]'
    o += w
# placeholder publication registers (no VM RTL behind these die ports): one register stage from the nearest input
eo = []
for src, dst in (('SW', 'SE'), ('SE', 'SW'), ('NW', 'NE'), ('NE', 'NW')):
    lo = o if dst == 'SW' else 0
    eo.append((f't_su_{dst}', lo, 2048, f'i_f_su_{src}[{2047 - lo}:0]'))
    eo.append((f'q{dst}', 0, 512, f'i_i{dst}[511:0]'))
    eo.append((f'q{dst}', 512, 580, f'i_f_su_{dst}[2047:1980]'))
eo.append(('t_quant', 0, 1024, 'i_f_su_NE[1023:0]'))
eo.append(('t_router', 0, 512, 'i_f_su_NE[1535:1024]'))
F = 'physical/hbm_accel_die_views/vm/rtl/ot_hbm_die_vm_multicast_root.sv'
spec = dict(master='hfd_vm', note=(
    'Thin registered VM top (no VM RTL exists): the x staging / multicast root ot_hbm_die_vm_multicast_root (22 SRAM '
    'macros, Codex component, sim receipt) on the four x trunks; the SU publication, tile query, quantiser and router '
    'feeds are ONE placeholder register stage each (no VM function behind them).'),
    instances=[dict(name='mr', module='ot_hbm_die_vm_multicast_root', file=F, params=dict(ENABLE=1), bind=b)],
    extra_out=eo)
Path(__file__).with_name('spec.json').write_text(json.dumps(spec, indent=1) + '\n')
