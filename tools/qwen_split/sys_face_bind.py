"""Q-NETLIST 2026-10-16: bind the compute-die system face (rtl/qwen_split/qfd_sys_face.sv) and close every functional
input the strict die port-bind left open (r2b2: input_unconnected 71, all system-level producers of the join961 TOP).

* NEW master qfd_sys_face (instance sys_face): config ROM + boot / program replay + static T/L/E calendars + token loop +
  embedding-row RX + STATUS/RESULT + fab.  Its inputs are existing die outputs (D2D record ports and RX payload, the
  sequencer's dc / program_obs / descriptor_obs / cfg_image_ready, the TT's program_obs / control_stores_ready / head
  context, native59 / collective / D2D / result-train / constant-ROM faults, the collective's cmd_free); its outputs drive
  every open input of qfd_d2d_static, qfd_native59_compute_service, qfd_seq_su_static (dh), qfd_tt_ctlm_static_s
  (pw / kok / kwd / fab) and the embedding provider.
* embed_prov becomes qfd_embedding_word_provider (word_* row face; same core / embed / fault ports and outline).
* qfd_collective_static_io_production pkg_s[1:0] / die_ps = the TP8 rank straps (rank = 4 die_ps + pkg_s, differ per
  package position): three package strap bumps qfd_sigbump (off-chip signal, allowed hard-macro model).
New instances are placed AFTER the homes (place(), nearest free legal site to their peers) unless the homes file names
them; the receipt lists the chosen frames so the die lead can fold them into the next homes revision.
"""
import hashlib
import os
from pathlib import Path

from qwen_split.source_pin_plan import rtl_ports

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'qfd_sys_face'
SOURCE = 'rtl/qwen_split/qfd_sys_face.sv'
INST = 'sys_face'
WH = (302.4, 216.0)
PROV_MASTER = 'qfd_embedding_word_provider'
PROV_SOURCE = 'rtl/qwen_split/qfd_embedding_word_provider.sv'
BUMP = 'qfd_sigbump'
BUMP_WH = 43.176
STRAPS = [('bump_pkg_s0', 'pkg_s', 0), ('bump_pkg_s1', 'pkg_s', 1), ('bump_die_ps', 'die_ps', None)]
NEW_INSTS = [INST] + [s[0] for s in STRAPS]

# (sys_face port, peer instance, peer port): direction follows the sys_face RTL port
EDGES = [
    # static D2D end
    *[(p, 'd2d_rom', p) for p in ('cfg_tx_we', 'cfg_rx_we', 'cfg_addr', 'cfg_data', 'cal_start', 'cal_seg',
                                  'status_epoch16', 'vm_drained', 'collective_drained', 'collective_busy', 'crom_fault',
                                  'execution_active', 'admit_ready', 'result_v', 'result_done', 'result_fault',
                                  'result_cause', 'result_tag', 'result_gen', 'result_token', 'result_value', 'result_cycles',
                                  'prog_tx_observed_v', 'prog_tx_record', 'rx_payload', 'prog_rx_v', 'prog_witness_slot',
                                  'prog_auth_slot', 'prog_context_slot', 'emb_rx_v', 'emb_rx_slot')],
    ('d2d_fault', 'd2d_rom', 'fault'), ('d2d_epoch_abort', 'd2d_rom', 'epoch_abort'),
    # ROM sequencer
    ('seq_dc', 'seq_su', 'dc'), ('seq_program_obs', 'seq_su', 'program_obs'), ('seq_descriptor_obs', 'seq_su', 'descriptor_obs'),
    ('seq_cfg_image_ready', 'seq_su', 'cfg_image_ready'), ('seq_dh', 'seq_su', 'dh'),
    # ME controller
    ('tt_program_obs', 'tt_ctlm', 'program_obs'), ('tt_control_stores_ready', 'tt_ctlm', 'control_stores_ready'),
    ('tt_layer_context_v', 'tt_ctlm', 'layer_context_v'), ('tt_command_stage', 'tt_ctlm', 'command_stage'),
    ('tt_native_tok', 'tt_ctlm', 'native_tok'), ('tt_native_pos', 'tt_ctlm', 'native_pos'),
    ('tt_pw', 'tt_ctlm', 'pw'), ('tt_kok', 'tt_ctlm', 'kok'), ('tt_kwd', 'tt_ctlm', 'kwd'), ('tt_fab', 'tt_ctlm', 'fab'),
    # native59
    ('host_epoch_valid', 'native59', 'host_epoch_valid'), ('host_fused_capability', 'native59', 'host_fused_capability'),
    ('host_epoch', 'native59', 'host_epoch'), ('host_tag', 'native59', 'host_tag'), ('host_generation', 'native59', 'host_generation'),
    ('q_slot', 'native59', 'q_slot'), ('q_slot_beat', 'native59', 'q_slot_beat'), ('kv_word_slot', 'native59', 'kv_word_slot'),
    ('kv_word_index', 'native59', 'kv_word_index'), ('visibility_slot', 'native59', 'visibility_slot'),
    ('complete_slot', 'native59', 'complete_slot'), ('native_fault', 'native59', 'fault'),
    # embedding provider
    ('emb_word_v', 'embed_prov', 'word_v'), ('emb_word_data', 'embed_prov', 'word_data'), ('emb_word_token', 'embed_prov', 'word_token'),
    ('emb_word_index', 'embed_prov', 'word_index'), ('emb_word_scale', 'embed_prov', 'word_scale'),
    ('emb_word_epoch', 'embed_prov', 'word_epoch'), ('emb_expected_slot', 'embed_prov', 'expected_word_slot'),
    ('emb_expected_token', 'embed_prov', 'expected_token'), ('emb_expected_word', 'embed_prov', 'expected_word'),
    ('emb_expected_scale', 'embed_prov', 'expected_scale'), ('emb_expected_epoch', 'embed_prov', 'expected_epoch'),
    ('emb_fill_begin', 'embed_prov', 'fill_begin'), ('emb_fill_token', 'embed_prov', 'fill_token'),
    ('emb_fill_epoch', 'embed_prov', 'fill_epoch'), ('emb_core_epoch', 'embed_prov', 'core_epoch'),
    # fault / status sources
    ('io_cmd_free', 'io_collective', 'cmd_free'), ('io_fault', 'io_collective', 'fault'),
    ('io_shared_fault', 'io_collective', 'shared_fault'), ('res_issue_fault', 'res_train_issue', 'fault'),
]


def _bus_of(model, by, inst, port):
    """the existing functional bus carrying (inst, port) whole, or None; a port already split into slice aliases fails"""
    al = {a for a, (r, bits) in model.get('port_join', {}).get(by[inst].master, {}).items() if r == port}
    for k, (b, c, n, es) in enumerate(model['buses']):
        if any(i == inst and p in al for i, p in es):
            raise ValueError(f'sys face bind: {inst}.{port} is split into aliases on bus {b}')
        if c in ('clock_trunk', 'reset'):
            continue
        if (inst, port) in es:
            return k
    return None


def apply(model):
    by = {i.name: i for i in model['insts']}
    for need in ('d2d_rom', 'seq_su', 'tt_ctlm', 'native59', 'embed_prov', 'io_collective', 'res_train_issue'):
        if need not in by:
            raise ValueError(f'sys face bind: die instance {need} missing')
    if by['d2d_rom'].master != 'qfd_d2d_static':
        raise ValueError('sys face bind needs the static D2D end (static_link_bind)')
    sf = rtl_ports(ROOT / SOURCE, MASTER)
    prov = rtl_ports(ROOT / PROV_SOURCE, PROV_MASTER)
    by['embed_prov'].master = PROV_MASTER
    Inst = type(by['seq_su'])
    ref = by['native59']
    # provisional sites (place() re-sites them on the final homes)
    model['insts'].append(Inst(INST, MASTER, ref.x, ref.y, WH[0], WH[1], 'R0', kind=getattr(ref, 'kind', None),
                               region=getattr(ref, 'region', None), domain=getattr(ref, 'domain', None)))
    io = by['io_collective']
    for nm, _, _ in STRAPS:
        model['insts'].append(Inst(nm, BUMP, io.x, io.y, BUMP_WH, BUMP_WH, 'R0', kind=getattr(io, 'kind', None),
                                   region=getattr(io, 'region', None), domain=getattr(io, 'domain', None)))
    by = {i.name: i for i in model['insts']}
    peer_ports = {}
    added, appended = [], []
    for sp, inst, pp in EDGES:
        if sp not in sf:
            raise ValueError(f'sys face bind: {sp} not a qfd_sys_face port')
        pm = by[inst].master
        pr = prov if inst == 'embed_prov' else rtl_ports(ROOT / _src_of(model, inst), pm)
        if pp not in pr:
            raise ValueError(f'sys face bind: {inst}.{pp} not in the {pm} RTL')
        if pr[pp][0] != sf[sp][0]:
            raise ValueError(f'sys face bind: width {inst}.{pp} {pr[pp][0]} vs sys_face.{sp} {sf[sp][0]}')
        k = _bus_of(model, by, inst, pp)
        if k is not None:
            if sf[sp][1] == 'output':
                raise ValueError(f'sys face bind: {inst}.{pp} already driven')
            b, c, n, es = model['buses'][k]
            model['buses'][k] = (b, c, n, es + [(INST, sp)])
            appended.append(b)
        else:
            model['buses'].append((f'sf_{sp}', 'spine_local', sf[sp][0], [(INST, sp), (inst, pp)] if sf[sp][1] == 'output'
                                   else [(inst, pp), (INST, sp)]))
            added.append(f'sf_{sp}')
        peer_ports[sp] = inst
    # constant-ROM group fault codes -> crom_fault_code[2g+1:2g]
    alias = model.setdefault('port_join', {}).setdefault(MASTER, {})
    for g in range(8):
        a = f'crom_fault_code__{2 * g}_{2 * g + 1}'
        alias[a] = ('crom_fault_code', [2 * g, 2 * g + 1])
        model['buses'].append((f'sf_crom_fc_{g}', 'spine_local', 2, [(f'crom_g_{g}', 'fault_code'), (INST, a)]))
        added.append(f'sf_crom_fc_{g}')
    # rank straps
    ia = model['port_join'].setdefault(io.master, {})
    for nm, port, bit in STRAPS:
        p = port if bit is None else f'{port}__{bit}_{bit}'
        if bit is not None:
            ia[p] = (port, [bit])
        model['buses'].append((f'sf_strap_{nm}', 'spine_local', 1, [(nm, 'o'), ('io_collective', p)]))
        added.append(f'sf_strap_{nm}')
    # clock / reset: the D2D end's trunk and reset
    for k, (b, c, n, es) in enumerate(model['buses']):
        if c == 'clock_trunk' and ('d2d_rom', 'ck') in es:
            model['buses'][k] = (b, c, n, es + [(INST, 'ck')])
        elif (c == 'reset' or b.startswith('rst')) and ('d2d_rom', 'rst_n') in es:
            model['buses'][k] = (b, c, n, es + [(INST, 'rst_n')])
    conn = {p for b, c, n, es in model['buses'] for i, p in es if i == INST}
    conn = {alias.get(p, (p, None))[0] for p in conn}
    open_in = sorted(p for p, (n, d) in sf.items() if d == 'input' and p not in conn)
    if open_in:
        raise ValueError(f'sys face bind: qfd_sys_face inputs left open {open_in}')
    rec = dict(master=MASTER, source=SOURCE, source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
               provider=dict(master=PROV_MASTER, source=PROV_SOURCE), straps=[s[0] for s in STRAPS],
               added_buses=added, appended_buses=sorted(set(appended)), new_instances=NEW_INSTS, frames=None,
               qualified=False, note='NEW unclosed parent; site from place() unless the homes file names it')
    model['sys_face_bind'] = rec
    return rec


def _src_of(model, inst):
    from qwen_split.native_graph_bind import INST as NG_INST, MASTER as NG_MASTER
    rev = {v: k for k, v in NG_INST.items()}
    if inst in rev and rev[inst] in NG_MASTER:
        return NG_MASTER[rev[inst]][1]
    return dict(d2d_rom='rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv',
                tt_ctlm='rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_static_s.sv',
                io_collective='rtl/physical/ot_qfd_collective_static_io_production.sv',
                res_train_issue='rtl/qwen_split/qfd_res_train_issue.sv')[inst]


def place(model, homes_named=()):
    """Re-site the new instances on the final (post-homes) floorplan, unless the homes named them."""
    rec = model.get('sys_face_bind')
    if not rec:
        return None
    from qwen_split.native_graph_bind import _free_site
    by = {i.name: i for i in model['insts']}
    others = [i for i in model['insts'] if i.name not in NEW_INSTS or i.name in homes_named]
    keep = model['insts']
    frames = {}
    try:
        model['insts'] = others
        d2d, nat, emb = by['d2d_rom'], by['native59'], by['embed_prov']
        if INST not in homes_named:
            # default (die lead 10-16 00:4x): the free lower spine, just south of native59 / embed_prov (the provider row
            # face is the widest bus, 0.6 kb); OT_SPLIT_SYSFACE_XY=x,y (um, centre) overrides
            tx, ty = emb.x + emb.w / 2, min(nat.y, emb.y) - WH[1] / 2 - 21.6
            if os.environ.get('OT_SPLIT_SYSFACE_XY'):
                tx, ty = (float(v) for v in os.environ['OT_SPLIT_SYSFACE_XY'].split(','))
            x, y = _free_site(model, WH, (tx, ty), model['die'])
            by[INST].x, by[INST].y = x, y
            model['insts'] = model['insts'] + [by[INST]]
        io = by['io_collective']
        for nm, _, _ in STRAPS:
            if nm in homes_named:
                continue
            x, y = _free_site(model, (BUMP_WH, BUMP_WH), (io.x - BUMP_WH, io.y + io.h / 2), model['die'])
            by[nm].x, by[nm].y = x, y
            model['insts'] = model['insts'] + [by[nm]]
    finally:
        model['insts'] = keep
    for nm in NEW_INSTS:
        i = by[nm]
        frames[nm] = [round(i.x, 4), round(i.y, 4), i.w, i.h, i.orient, 'homes' if nm in homes_named else 'place()']
    rec['frames'] = frames
    return frames


def install_masters(M, model, Master, partition_master):
    if 'sys_face_bind' not in model:
        return
    from qwen_split.native_graph_bind import assign_pins, peer_map
    by = {i.name: i for i in model['insts']}
    peers = peer_map(model)
    assign_pins(M, model, Master, by[INST], MASTER, SOURCE, peers, partition_master)
    if BUMP not in M:
        q = Master(BUMP, BUMP_WH, BUMP_WH, 3, 'package signal bump receiver (hard-macro model)')
        q.ports['o'] = ('pins', 1, 'N', 'M5', [round(.012 + round((BUMP_WH / 2 - .012) / .048) * .048, 4)], 1)
        q.order.append('o')
        M[BUMP] = q
    M.pop('qkd_embedding_static_core_provider', None)
