"""Swap the compute-die link end to the static Q-LINK master qfd_d2d_static (main c43263b31).

The historical credit end qfd_d2d_rom (x3 / ea / eq / ar credits, single clock) and the SU-era x3 mux are retired:
native59 now drives the KN/Q record (x3 524 + identity 59 + generation 2) and its typed native548 words straight into
the static end, which owns the compiler slots (native tx / rx slot, kind, beat; kv_x3_slot) and the 583-bit PHY word
to ot_qkvd_ucie_x64_phy (phy_rst_n drives the PHY reset).  Two forwarded package bumps from the KV die (epoch strobe,
link reset) are qfd_sigbump hard-macro models.  Inputs with no compute-die producer (cfg_*, cal_start, the program
record, the STATUS/RESULT record) are enumerated, never tied.
"""
import hashlib
from pathlib import Path

from qwen_split.source_pin_plan import rtl_ports

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'qfd_d2d_static'
SOURCE = 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv'
BUMP = 'qfd_sigbump'
BUMP_WH = 43.176


def apply(model):
    by = {i.name: i for i in model['insts']}
    d2d = by['d2d_rom']
    if d2d.master != 'qfd_d2d_rom' or 'native59' not in by or 'ucie_kv' not in by:
        raise ValueError('static link bind needs the historical d2d_rom, native59 and ucie_kv')
    d2d.master = MASTER
    ports = rtl_ports(ROOT / SOURCE, MASTER)
    retire = {'x3_mux'}
    removed, kept, rst_bus, clk_bus = [], [], None, None
    for b, c, n, es in model['buses']:
        names = [i for i, _ in es]
        if c == 'clock_trunk' and 'd2d_rom' in names:
            clk_bus = b
            es = [(i, p) for i, p in es if i not in ('d2d_rom',) and i not in retire]
            kept.append((b, c, n, es))
            continue
        if (c == 'reset' or b.startswith('rst_')) and ('d2d_rom' in names or 'ucie_kv' in names):
            rst_bus = rst_bus or b
            es = [(i, p) for i, p in es if i not in ('d2d_rom', 'ucie_kv') and i not in retire]
            kept.append((b, c, n, es))
            continue
        if c in ('clock_trunk', 'reset'):
            kept.append((b, c, n, [(i, p) for i, p in es if i not in retire]))
            continue
        if 'd2d_rom' in names or any(i in retire for i in names) or \
                ('ucie_kv' in names and c != 'clock_trunk'):
            removed.append(b)
            continue
        kept.append((b, c, n, es))
    if clk_bus is None or rst_bus is None:
        raise ValueError('static link bind: d2d clock trunk / reset bus not found')
    model['insts'] = [i for i in model['insts'] if i.name not in retire]
    ph = by['ucie_kv']
    Inst = type(d2d)
    bumps = []
    for k, nm in enumerate(('bump_fwd_epoch', 'bump_fwd_lrst')):
        x = round(ph.x - 4.32 - (k + 1) * (BUMP_WH + 4.32), 4)
        model['insts'].append(Inst(nm, BUMP, x, round(ph.y + 30.0 + 60.0, 4), BUMP_WH, BUMP_WH, 'R0',
                                   kind=getattr(d2d, 'kind', None), region=getattr(d2d, 'region', None),
                                   domain=getattr(d2d, 'domain', None)))
        bumps.append(nm)
    clock_ports = [p for p in ports if p == 'ck' or p.startswith('ck_')]
    if clock_ports != ['ck'] or ports['ck'][0] != 1:
        raise ValueError('static link bind requires the source single scalar ck root')
    nat = 'native59'
    new = [('lnk_fdi_tx', 'spine_local', 583, [('d2d_rom', 'fdi_tx_flit'), ('ucie_kv', 'tx_flit')]),
           ('lnk_fdi_txv', 'spine_local', 1, [('d2d_rom', 'fdi_tx_v'), ('ucie_kv', 'tx_v')]),
           ('lnk_fdi_rx', 'spine_local', 583, [('ucie_kv', 'rx_flit'), ('d2d_rom', 'fdi_rx_flit')]),
           ('lnk_fdi_rxv', 'spine_local', 1, [('ucie_kv', 'rx_v'), ('d2d_rom', 'fdi_rx_v')]),
           ('lnk_fdi_up', 'spine_local', 1, [('ucie_kv', 'tx_up'), ('d2d_rom', 'fdi_tx_up')]),
           ('lnk_phy_rst', 'spine_local', 1, [('d2d_rom', 'phy_rst_n'), ('ucie_kv', 'rst_n')]),
           ('lnk_fwd_epoch', 'spine_local', 1, [('bump_fwd_epoch', 'o'), ('d2d_rom', 'fwd_epoch')]),
           ('lnk_fwd_lrst', 'spine_local', 1, [('bump_fwd_lrst', 'o'), ('d2d_rom', 'fwd_link_rst_n')])]
    for src, sp, dst, dp in [('d2d_rom', 'native_tx_slot', nat, 'tx_slot'), ('d2d_rom', 'native_tx_slot_kind', nat, 'tx_slot_kind'),
                             ('d2d_rom', 'native_tx_slot_beat', nat, 'tx_slot_beat'), (nat, 'native_tx_v', 'd2d_rom', 'native_tx_v'),
                             (nat, 'native_tx_payload', 'd2d_rom', 'native_tx_payload'),
                             ('d2d_rom', 'native_rx_v', nat, 'native_rx_v'), ('d2d_rom', 'rx_payload', nat, 'native_rx_payload'),
                             ('d2d_rom', 'native_rx_slot', nat, 'rx_slot'), ('d2d_rom', 'native_rx_slot_kind', nat, 'rx_slot_kind'),
                             ('d2d_rom', 'native_rx_slot_beat', nat, 'rx_slot_beat'), ('d2d_rom', 'kv_x3_slot', nat, 'kv_x3_slot'),
                             (nat, 'x3', 'd2d_rom', 'x3'), (nat, 'x3_identity', 'd2d_rom', 'x3_identity'),
                             (nat, 'x3_generation', 'd2d_rom', 'x3_generation')]:
        n = ports[sp][0] if src == 'd2d_rom' else ports[dp][0]
        new.append((f'lnk_{sp}', 'spine_local', n, [(src, sp), (dst, dp)]))
    out = []
    for b, c, n, es in kept:
        if b == clk_bus:
            es = es + [('d2d_rom', 'ck')]
        if b == rst_bus:
            es = es + [('d2d_rom', 'por_n'), ('d2d_rom', 'rst_n')]
        out.append((b, c, n, es))
    model['buses'] = out + new
    conn = {p for b, c, n, es in model['buses'] for i, p in es if i == 'd2d_rom'}
    unknown = sorted(conn - set(ports))
    if unknown:
        raise ValueError(f'static link bind: non-source endpoints {unknown}')
    rec = dict(master=MASTER, source=SOURCE, source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
               retired=dict(masters=['qfd_d2d_rom (credit link end)', 'ot_qfd_x3_mux_native'], instances=sorted(retire),
                            buses=removed),
               bumps=dict(instances=bumps, master=BUMP, note='package bump receivers = off-chip signals (allowed models)'),
               open_inputs=sorted(p for p, (n, d) in ports.items() if d == 'input' and p not in conn),
               open_owners='cfg_* (HOST config writes), cal_start (compute ROM sequencer layer start), prog_tx_* '
                           '(program record), status_epoch16 / vm_drained / collective_drained / collective_busy / '
                           'crom_fault / execution_active / admit_ready / result_* (Q-DVM, Q-COLL, Q-COMPUTE, Q-FUNC '
                           'per the Q-LINK RTL note): no producer port exists on the compute die yet',
               qualified=False)
    model['static_link_bind'] = rec
    return rec


def install_masters(M, model, Master, partition_master):
    if 'static_link_bind' not in model:
        return
    from qwen_split.native_graph_bind import assign_pins, peer_map
    by = {i.name: i for i in model['insts']}
    assign_pins(M, model, Master, by['d2d_rom'], MASTER, SOURCE, peer_map(model), partition_master)
    q = Master(BUMP, BUMP_WH, BUMP_WH, 3, 'package signal bump receiver (hard-macro model)')
    q.ports['o'] = ('pins', 1, 'N', 'M5', [round(.012 + round((BUMP_WH / 2 - .012) / .048) * .048, 4)], 1)
    q.order.append('o')
    M[BUMP] = q
    # the KV-link PHY on its real abstract pins (die.v names tx_flit / rx_flit / tx_v / rx_v / tx_up / clk / rst_n)
    from qwen_split.native_static_io_bind import phy_master
    M['ot_qkvd_ucie_x64_phy'] = phy_master(Master, 'ot_qkvd_ucie_x64_phy', 'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy')
    M.pop('qfd_d2d_rom', None)
    M.pop('ot_qfd_x3_mux_native', None)
    validate_case_masters(M, model)


def validate_case_masters(M, model):
    """Refuse a case whose source graph and actual generated master set diverge."""
    if not model.get('static_link_bind'):
        return
    required = {MASTER, BUMP, 'ot_qkvd_ucie_x64_phy'}
    missing = required - set(M)
    retired = {'qfd_d2d_rom', 'ot_qfd_x3_mux_native'} & set(M)
    if missing or retired:
        raise ValueError(f'static link physical master contract: missing={sorted(missing)} retired={sorted(retired)}')
    source_ports = rtl_ports(ROOT / SOURCE, MASTER)
    if set(M[MASTER].ports) != set(source_ports):
        raise ValueError('static link physical master ports disagree with the actual RTL')
    phy = M['ot_qkvd_ucie_x64_phy']
    for p, n in [('clk', 1), ('rst_n', 1), ('tx_flit', 583), ('rx_flit', 583),
                 ('tx_v', 1), ('rx_v', 1), ('tx_up', 1)]:
        if p not in phy.ports or phy.ports[p][1] != n:
            raise ValueError(f'static link physical PHY contract: {p} needs {n} actual pins')
