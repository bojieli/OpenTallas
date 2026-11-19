import importlib.util, math
from pathlib import Path

S = importlib.util.spec_from_file_location("brg", Path(__file__).with_name("bound_record_graph.py"))
B = importlib.util.module_from_spec(S); S.loader.exec_module(B)


def _chain(n):
    cells, ports = {}, {"y": {"direction": "output", "bits": [100 + n]}}
    for i in range(n):
        a = 1 if i == 0 else 100 + i
        cells[f"o{i}"] = {"type": "$_OR_", "connections": {"A": [a], "B": [2 + i], "Y": [101 + i]},
                          "port_directions": {"A": "input", "B": "input", "Y": "output"}}
    ports["y"]["bits"] = [100 + n]
    return cells, ports


def _eval(cells, ports, ins):
    prod = {c["connections"]["Y"][0]: c for c in cells.values()}
    def val(b):
        if b in ins: return ins[b]
        c = prod[b]; return val(c["connections"]["A"][0]) | val(c["connections"]["B"][0])
    return val(ports["y"]["bits"][0])


def _depth(cells, b):
    prod = {c["connections"]["Y"][0]: c for c in cells.values()}
    return 0 if b not in prod else 1 + max(_depth(cells, prod[b]["connections"][p][0]) for p in "AB")


def test_serial_or_chain_becomes_balanced_and_equivalent():
    n = 8
    cells, ports = _chain(n)
    old = _depth(cells, ports["y"]["bits"][0])
    nb, trees, rew = B.balance_chains(cells, ports, 500)
    assert trees == 1 and old == 8
    assert _depth(cells, ports["y"]["bits"][0]) == math.ceil(math.log2(n + 1))
    for k in range(n + 1):
        ins = {1: 0, **{2 + i: 0 for i in range(n)}}
        if k == 0: ins[1] = 1
        else: ins[1 + k] = 1
        assert _eval(cells, ports, ins) == 1
    assert _eval(cells, ports, {1: 0, **{2 + i: 0 for i in range(n)}}) == 0


def test_shared_interior_node_is_kept():
    cells, ports = _chain(6)
    ports["z"] = {"direction": "output", "bits": [103]}   # interior bit also an output: not absorbable
    B.balance_chains(cells, ports, 500)
    assert any(c["connections"]["Y"] == [103] for c in cells.values())
