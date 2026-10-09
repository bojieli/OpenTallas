#!/usr/bin/env python3
"""hfd_coll interim wrapper spec: unchanged ot_hbm_accel_tu_endpoint (Dirac/ITEM9 own the RTL and its routes; nothing
of theirs is launched or touched) on the r16g die ports.  r16g coll_rtl / link_rtl bindings:
  f_su_q (1024) -> inj_data = OR of the four quarters (hgi-takeover 2026-10-09: each SU quarter drives 0 unless it owns
                  the requested flit; contract in spec['contracts']; was: SW only, 3,072 dropped bits)
  t_su_q (580)  <- del_flit[q*545 +: 545], del_valid[q], inj_idx (32), inj_rd (2)
  f_cmdproc 25  -> rank[7:0], pf[15:0], go;  t_cmdproc 33 <- fault, stat_credit_stall[31:0]
  llk_* (976)   tx [0,487) <- {rx_credit, ph_tx_flit, ph_tx_v} striped over S0..S4, N0..N3; rx [487,974) ->
                  {sw_cr_ret, ph_rx_flit, ph_rx_v}; 974 / 975 forwarded clocks
  pll_* / por_* <- the block clock (kept inverter) / the synchronised reset
The die gives the collective block NO reference clock or reset input (it is the PLL owner; H11 top I/O): the
wrapper adds input pins refclk and por (generator-side defect)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L  # noqa: E402

F = 'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv'
PRM = dict(ENABLE=1, RXAW=4, QAW=4, TXAW=4)
pm = L.parse_module(F, 'ot_hbm_accel_tu_endpoint', PRM)['ports']
LK = ['S0', 'S1', 'S2', 'S3', 'S4', 'N0', 'N1', 'N2', 'N3']


def stripe(order, base, width=487):
    """bind successive RTL ports to the concatenated stripe [base, base+width) of every link port."""
    out, cur = {}, 0
    for nm in order:
        w = pm[nm][1]
        parts, a = [], cur
        while a < cur + w:
            k, off = divmod(a, width)
            n = min(width - off, cur + w - a)
            parts.append(f'llk_{LK[k]}[{base + off}:{base + off + n}]')
            a += n
        out[nm] = 'die:' + '+'.join(parts)
        cur += w
    assert cur <= width * len(LK)
    return out


b = dict(clk='clk', rst_n='rst_n', pclk='clk', prst_n='rst_n')
b['inj_data'] = {'or': [f'die:f_su_{q}[0:1024]' for q in ('SW', 'NW', 'SE', 'NE')]}
b['rank'] = 'die:f_cmdproc[0:8]'
b['pf'] = 'die:f_cmdproc[8:24]'
b['go'] = 'die:f_cmdproc[24:25]'
b['fault'] = 'die:t_cmdproc[0:1]'
b['stat_credit_stall'] = 'die:t_cmdproc[1:33]'
b.update(stripe(['ph_tx_v', 'ph_tx_flit', 'rx_credit'], 0))
b.update(stripe(['ph_rx_v', 'ph_rx_flit', 'sw_cr_ret'], 487))
Q = ['SW', 'NW', 'SE', 'NE']
b['del_flit'] = 'die:' + '+'.join(f't_su_{q}[0:545]' for q in Q)
b['del_valid'] = 'die:' + '+'.join(f't_su_{q}[545:546]' for q in Q)
b['inj_idx'] = [f'die:t_su_{q}[546:578]' for q in Q]
b['inj_rd'] = [f'die:t_su_{q}[578:580]' for q in Q]
eo = [(f'por_{d}', 0, 1, 'rst_s[1]') for d in ('stream', 'link', 'serial', 'hbm')]
spec = dict(master='hfd_coll', clock='refclk', rst='por', extra_inputs=['refclk', 'por'],
            clock_out_ports=['pll_stream', 'pll_link', 'pll_serial', 'pll_hbm'], note=(
    'INTERIM, REDUCED: unchanged ot_hbm_accel_tu_endpoint with FIFO depths RXAW = QAW = TXAW = 4 (16 entries); at the '
    'RTL defaults (RXAW 8, QAW 6, TXAW 6) its flop FIFOs hold ~2.5 Mb, more std-cell area than the 1.96 mm2 slot: the '
    'endpoint needs SRAM FIFOs before a full-depth view exists. pclk = clk (the PHY clock is the link clock region '
    'outside this block). Extra pins refclk / por: the die has no clock / reset input for its PLL owner.'),
    instances=[dict(name='ep', module='ot_hbm_accel_tu_endpoint', file=F, params=PRM, bind=b)], extra_out=eo)
spec['contracts'] = {'ep.inj_data': 'SU-quarter ownership: for the inject index inj_idx (broadcast to all four quarters on '
                    't_su_q[546:580]) exactly the quarter holding that flit drives its 1024-bit f_su_q (hfd_su t_coll); '
                    'the other three drive 0, so the OR is the owner data (SU obligation; hbm-forks notified).'}
# the 9 x 487 b link stripes carry 4,376 b of TX / RX: 7 b of N3 per direction are spare lanes of the uniform link width
spec['ties'] = {'die:llk_N3[967:974]': dict(**{'class': 'by_design'}, reason='spare RX lanes: 9 x 487 b uniform stripes hold 4,376 b'),
                'die:llk_N3[480:487]': dict(**{'class': 'by_design'}, reason='spare TX lanes: 9 x 487 b uniform stripes hold 4,376 b')}
spec['kept_out_regs'] = True  # one kept ot_hfd_oreg1 per die output bit (no merged output drivers)
spec['face_stages'] = 5  # owner margin-first rule 2026-10-06: pin flop + 4 stages each face (1.4 mm views; 3 left -198 ps on qm_pd55)
# keep the hand-added physical keys of the committed spec (port_stages / share_tree, hbm-coll-rtl)
_old = Path(__file__).with_name('spec.json')
if _old.exists():
    for _k in ('port_stages', 'port_stages_basis', 'share_tree'):
        _v = json.loads(_old.read_text()).get(_k)
        if _v is not None:
            spec[_k] = _v
Path(__file__).with_name('spec.json').write_text(json.dumps(spec, indent=1) + '\n')
