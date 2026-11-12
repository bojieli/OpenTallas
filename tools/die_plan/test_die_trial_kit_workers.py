"""DIE-PROTO-1 --kit-workers: per-type abstracts / STA stand-ins in a fork pool give the serial loop's exact output."""
import copy
import json
from pathlib import Path
import die_trial as T
import schema as S
HERE = Path(__file__).resolve().parent
PAIR = json.loads((HERE / 'examples/s81_pair/s81_pair_plan.json').read_text())


def _run(P, workers):
    old = T.KIT_WORKERS
    T.KIT_WORKERS = workers
    try:
        tns = sorted(P.types)
        ab = T.kit_map([(T.abstract_lef, (P, tn), dict(module_name=P.types[tn]['module'])) for tn in tns])
        si = T.kit_map([(T.standin_netlist, (P, tn), {}) for tn in tns])
    finally:
        T.KIT_WORKERS = old
    return ab, si


def test_kit_workers_identical_to_serial():
    P = S.Plan(copy.deepcopy(PAIR))
    assert len(P.types) > 1
    assert _run(P, 1) == _run(P, 4)


def test_kit_map_keeps_order_and_serial_default():
    assert T.KIT_WORKERS == 1
    calls = [(pow, (i, 2), {}) for i in range(9)]
    T.KIT_WORKERS = 3
    try:
        assert T.kit_map(calls) == [i * i for i in range(9)]
    finally:
        T.KIT_WORKERS = 1
    assert T._KIT_POOL is None
