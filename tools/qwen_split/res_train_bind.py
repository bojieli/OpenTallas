"""Swap the band result serializer to the adopted static train24 banks (Q-ATTN r3 decision 2026-10-15).

The legacy die master qfd_sp_res_ser (i / o / me_en / fault) reads a different bit order from the slab result bus
qfd_port_tiles_b.rq, so the rq -> i nets of die contracts c8..c17 were functionally wrong.  Each sp_res_ser_<b> becomes
qfd_sp_res_train_<b> (rtl/qwen_split/qfd_sp_res_train.sv -> qfd_res_train_static, BAND b, as join961t):
  rq [4424:0]  <- qfd_port_tiles_b.rq   (identical layout, results/arch/qwen_split_compute_1014/res_train_decision_1015/abi_check.py)
  rb [550:0]   -> sp_vector_memory.rb<b> (the legacy o word order {v, end, nul, row20, mask16, data512})
  fault        -> tt_ctlm.rf<b> (unchanged)
  ck + ck_bank0..23 on the band clock trunk (25 per-child entries), rst_n on the spine reset.
The legacy me_en enable bus is retired (the static train runs on its compiler command, it never waits).  The command
inputs train_start / train_count / capture_stride / payload_write have no compute-die producer yet (TT ME-issue
calendar, Q-FUNC): enumerated as open inputs, never tied.
"""
import hashlib
from pathlib import Path

from qwen_split.source_pin_plan import rtl_ports

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'rtl/qwen_split/qfd_sp_res_train.sv'
LEGACY = 'qfd_sp_res_ser'
BANDS = 3
CLOCKS = ['ck'] + [f'ck_bank{k}' for k in range(24)]
RENAME = {'i': 'rq', 'o': 'rb'}
COMMAND = ('train_start', 'train_count', 'capture_stride', 'payload_write')


def master(b):
    return f'qfd_sp_res_train_{b}'


def apply(model):
    by = {i.name: i for i in model['insts']}
    sers = {f'sp_res_ser_{b}': b for b in range(BANDS)}
    for n in sers:
        if n not in by or by[n].master != LEGACY:
            raise ValueError(f'res train bind needs the legacy {n} ({LEGACY})')
    ports = {b: rtl_ports(ROOT / SOURCE, master(b)) for b in range(BANDS)}
    for n, b in sers.items():
        by[n].master = master(b)
    out, retired = [], []
    for bus, c, nb, es in model['buses']:
        names = [i for i, _ in es]
        if not any(i in sers for i in names):
            out.append((bus, c, nb, es))
            continue
        if c == 'clock_trunk':
            e2 = []
            for i, p in es:
                if i in sers and p in ('ck', 'clk'):
                    e2 += [(i, q) for q in CLOCKS if (i, q) not in e2]
                elif i in sers and p.startswith('ck'):
                    if (i, p) not in e2:
                        e2.append((i, p))
                else:
                    e2.append((i, p))
            out.append((bus, c, nb, e2))
            continue
        if c == 'reset' or bus.startswith('rst_'):
            out.append((bus, c, nb, es))
            continue
        if any(i in sers and p == 'me_en' for i, p in es):
            retired.append(bus)
            continue
        es = [(i, RENAME.get(p, p)) if i in sers else (i, p) for i, p in es]
        for i, p in es:
            if i in sers:
                n_src = ports[sers[i]].get(p)
                if n_src is None:
                    raise ValueError(f'res train bind: {i}.{p} is not a source port')
                if n_src[0] != nb:
                    raise ValueError(f'res train bind: {bus} is {nb} b but {i}.{p} is {n_src[0]} b')
        out.append((bus, c, nb, es))
    model['buses'] = out
    conn = {}
    for bus, c, nb, es in model['buses']:
        for i, p in es:
            if i in sers:
                conn.setdefault(i, set()).add(p)
    for n, b in sers.items():
        unknown = sorted(conn.get(n, set()) - set(ports[b]))
        if unknown:
            raise ValueError(f'res train bind: {n} non-source endpoints {unknown}')
        need = {'rq', 'rb', 'fault', 'rst_n', *CLOCKS}
        if need - conn.get(n, set()):
            raise ValueError(f'res train bind: {n} missing {sorted(need - conn.get(n, set()))}')
    rec = dict(masters=[master(b) for b in range(BANDS)], source=SOURCE,
               source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
               core='rtl/qwen_split/qfd_res_train_static.sv',
               core_sha256=hashlib.sha256((ROOT / 'rtl/qwen_split/qfd_res_train_static.sv').read_bytes()).hexdigest(),
               decision='Q-ATTN r3 2026-10-15 res_train_decision_1015 (join961t)',
               retired=dict(master=LEGACY, buses=retired),
               open_inputs={n: sorted(p for p, (w, d) in ports[b].items() if d == 'input' and p not in conn[n])
                            for n, b in sers.items()},
               open_owner='train command fields from the TT ME-issue calendar (Q-FUNC); no compute-die producer yet',
               slot_um=[round(by['sp_res_ser_0'].w, 3), round(by['sp_res_ser_0'].h, 3)],
               slot_note='legacy res_ser slot kept; physical fit of 24 banks (~360k FF) not yet measured',
               qualified=False)
    model['res_train_bind'] = rec
    return rec


def install_masters(M, model, Master, partition_master):
    if 'res_train_bind' not in model:
        return
    from qwen_split.native_graph_bind import assign_pins, peer_map
    by = {i.name: i for i in model['insts']}
    peers = peer_map(model)
    for b in range(BANDS):
        assign_pins(M, model, Master, by[f'sp_res_ser_{b}'], master(b), SOURCE, peers, partition_master)
    M.pop(LEGACY, None)
    validate_case_masters(M, model)


def validate_case_masters(M, model):
    if not model.get('res_train_bind'):
        return
    if LEGACY in M:
        raise ValueError('res train bind: legacy qfd_sp_res_ser master still generated')
    for b in range(BANDS):
        mn = master(b)
        if mn not in M:
            raise ValueError(f'res train bind: {mn} missing from the generated masters')
        if set(M[mn].ports) != set(rtl_ports(ROOT / SOURCE, mn)):
            raise ValueError(f'res train bind: {mn} ports disagree with the actual RTL')
