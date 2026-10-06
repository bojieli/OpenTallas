#!/usr/bin/env python3
"""hfd_loader interim wrapper spec: unchanged ot_hbm_accel_loader_host (ENABLE 1, ND 2) on the die ports.
Host link h (r16g link_rtl): h[0:256) tx (loader -> host), h[256:512) rx (host -> loader), h[512] forwarded clock out,
h[513] forwarded clock in.  Host-side inputs packed in port order into rx, host-side outputs into tx; the loader
request slot 0 drives the cmdproc program-store write word on t_cmdproc[0:73) (req_v[0], req_addr[7:0],
req_wdata[63:0], the layout hfd_cmdproc reads from f_loader)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L  # noqa: E402

F = 'rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv'
pm = L.parse_module(F, 'ot_hbm_accel_loader_host', dict(ENABLE=1, ND=2))['ports']
b = dict(clk_host='clk', clk_mem='clk', rst_host_n='rst_n', rst_mem_n='rst_n')
rx, tx = 256, 0
for p, (d, w) in pm.items():
    if p in b:
        continue
    if p.startswith(('s_', 'h_')):
        if d == 'input':
            if rx + w <= 512:
                b[p] = f'die:h[{rx}:{rx + w}]'
                rx += w
            else:
                b[p] = 'cfg'
        else:
            b[p] = f'die:h[{tx}:{tx + w}]'
            tx += w
    elif d == 'input':
        b[p] = 'cfg'           # memory AXI m_* and response rsp_*: no die net (generator: the loader reaches only the host and the cmdproc)
    else:
        b[p] = 'fold'
assert tx <= 256, tx
b['req_v'] = 'open'
b['req_addr'] = 'open'
b['req_wdata'] = 'open'
eo = [('t_cmdproc', 0, 1, 'w_ld_req_v[0]'), ('t_cmdproc', 1, 9, 'w_ld_req_addr[7:0]'),
      ('t_cmdproc', 9, 73, 'w_ld_req_wdata[63:0]')]
spec = dict(master='hfd_loader', note=(
    'INTERIM: unchanged ot_hbm_accel_loader_host (ENABLE 1, ND 2; tapeout_hbm_loader_20261004 clock_r2_final '
    'not_met, host SS -3,672 ps at 1.0 ns, not adopted). Host AXI-lite slave s_*, host master h_* and DMA h_dma_* on '
    f'the host link (rx {rx - 256} of 256 b used, rest of the DMA inputs on the cfg chain; tx {tx} of 256 b); request '
    'slot 0 -> cmdproc program-store word t_cmdproc[72:0]; clk_host and clk_mem both on the die clock; memory AXI '
    'm_* and rsp_* have no die net (cfg chain / folded).'), instances=[dict(
        name='ld', module='ot_hbm_accel_loader_host', file=F, params=dict(ENABLE=1, ND=2), bind=b)], extra_out=eo)
spec['kept_out_regs'] = True  # one kept ot_hfd_oreg1 per die output bit (no merged output drivers)
Path(__file__).with_name('spec.json').write_text(json.dumps(spec, indent=1) + '\n')
print(rx - 256, tx)
