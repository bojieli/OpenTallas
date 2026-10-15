"""Replay clock admission on the terminal glue23 IDX-credit circuit and a local KV credit.

Executes the actual final clock-admission block; the stale-map version assigns
common clocks and aliases the IDX circuit to the ordinary KV circuit.
"""
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict
import re
import os


def test_terminal_glue23_late_forwarded_credit_keeps_its_own_circuit():
    source = Path(os.environ.get('HBM_FORWARD_SOURCE', str(Path(__file__).parents[1] / 'tools/hbm_accel_die_fp.py'))).read_text()
    start = source.index('        dom_of = {}\n', source.index('def build_r25gq_net'))
    stop = source.index('        old_order = list(buses)', start)
    import textwrap
    code = compile(textwrap.dedent(source[start:stop]), '<actual die final clock admission>', 'exec')
    # Names, widths and layout are from glue23_p2/model.pkl, terminal 2026-10-14.
    idx = 'wq8113_idx_key_credit_SW_0_1_t3'
    local = 'wq8732_kq0_SW_15'
    fwd_bus = 'idx_key_credit_SW_0_1_t3'
    local_bus = 'kq0_SW_15'
    insts = [SimpleNamespace(name=idx, master='hfd_stn_q2W'),
             SimpleNamespace(name=local, master='hfd_stn_q2W'),
             SimpleNamespace(name='source', master='hfd_idx_score')]
    env = dict(re=re, insts=insts, base={}, V={'fwd_master_split': True},
               ck_sinks=defaultdict(list), rs_sinks=defaultdict(list),
               fcl_={}, fclk_new_={fwd_bus: (1, 1, 0)},
               stnf_={'hfd_stn_q2W': {'a': 'E', 'b': 'W'}}, phys_rec={},
               new_rl={idx: fwd_bus, local: local_bus},
               buses=[(fwd_bus, 'index_native', 2, [('source','b'),(idx,'a')]),
                      (local_bus,'kv_credit',2,[('source','k'),(local,'a')])])
    exec(code, env)
    clocks = [x for es in env['ck_sinks'].values() for x in es]
    assert (idx, 'ck') not in clocks, 'forwarded credit must use the clock carried in its two-bit bus'
    assert (local, 'ck') in clocks, 'ordinary KV credit still needs the common clock'
    assert insts[0].master == 'hfd_stn_q2WF'
    assert insts[1].master == 'hfd_stn_q2W'
