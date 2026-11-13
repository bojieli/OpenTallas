"""Source and delay identity regressions for frozen split-lane references."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E
from split_source_guard import (SourceGuardError, logical_graph_fingerprint,
                                source_rules_fingerprint, validate_guard)


def _cell(path, module, ports, dirs, params=None):
    return SimpleNamespace(path=path, module=module, params=params or {}, ports=ports,
                           dirs=dirs, kind="leaf", ytype=None, yparams={})


class _Graph:
    def __init__(self, cells, sources):
        self.sources = sources
        self.kind = ["transport" if c.module == "delay" else "leaf" for c in cells]
        self.dirs = [c.dirs for c in cells]
    def source(self, net):
        return ("const", net, "literal") if isinstance(net, str) else self.sources[net]


def binder(base, order=("src", "pipe", "sink"), offset=0):
    n = lambda v: v + offset
    cells = dict(src=_cell("u_src", "source", {"q": [n(10), n(11)]}, {"q": "output"}, {"N": 2}),
                 pipe=_cell("u_pipe", "delay", {"d": [n(10), n(11)], "q": [n(20), n(21)], "clk": [n(30)]},
                            {"d": "input", "q": "output", "clk": "input"}, {"D": 2}),
                 sink=_cell("u_sink", "sink", {"d": [n(20), n(21)], "clk": [n(30)], "rst_n": [n(31)]},
                            {"d": "input", "clk": "input", "rst_n": "input"}))
    flat = [cells[k] for k in order]
    ci = {k: order.index(k) for k in order}
    sources = {n(10): ("pin", ci["src"], "q", 0, 0), n(11): ("pin", ci["src"], "q", 1, 0),
               n(20): ("pin", ci["src"], "q", 0, 2), n(21): ("pin", ci["src"], "q", 1, 2),
               n(30): ("clock", "core"), n(31): ("reset", "low", 0)}
    top = {"clk": ("input", [n(30)]), "rst_n": ("input", [n(31)]), "out": ("output", [n(20), n(21)])}
    ab = dict(rtl_roots=["rtl"], files=[], prefer=[], transport=[dict(module="delay", map={"q": "d"}, stages=2)])
    return SimpleNamespace(F=SimpleNamespace(cells=flat, top_ports=top), G=_Graph(flat, sources),
                           ab=ab, base=str(base), extra_lib=[], ci=ci, n=n)


@pytest.fixture
def b(tmp_path):
    root = tmp_path / "rtl"; root.mkdir()
    (root / "a.sv").write_text(
        "module source(input [1:0] a, output [1:0] q); assign q=a; endmodule\n"
        "module delay(input clk, input [1:0] d, output [1:0] q); assign q=d; endmodule\n"
        "module sink(input clk, rst_n, input [1:0] d); endmodule\n")
    (root / "defs.svh").write_text("`define SOURCE_WIDTH 2\n")
    return binder(tmp_path)


def reference(b):
    path = Path(b.base) / "rtl/a.sv"
    sources = [dict(file="rtl/a.sv", module=m, kind="module",
                    sha256=hashlib.sha256(E.module_body(path, m).encode()).hexdigest())
               for m in ("source", "delay", "sink")]
    sources.append(dict(file="rtl/defs.svh", module=None, kind="include",
                        sha256=hashlib.sha256((Path(b.base) / "rtl/defs.svh").read_bytes()).hexdigest()))
    return dict(source_graph_sha256=logical_graph_fingerprint(b),
                source_rules_sha256=source_rules_fingerprint(b), rtl_sources=sources)


def test_clean_source_guard_passes_and_none_is_noop(b):
    result = validate_guard(reference(b), b)
    assert result["enabled"] and result["module_receipts"] == 3 and result["include_receipts"] == 1
    assert validate_guard(None, b) == {"enabled": False}


def test_reordered_sci_and_renumbered_nets_keep_symbolic_graph(b):
    changed = binder(b.base, order=("sink", "src", "pipe"), offset=10000)
    assert logical_graph_fingerprint(b) == logical_graph_fingerprint(changed)
    assert validate_guard(reference(b), changed)["enabled"]


@pytest.mark.parametrize("mutation", ["delay", "source_bit", "connection", "clock", "reset"])
def test_actual_source_or_delay_change_rejects_frozen_graph(b, mutation):
    ref = reference(b); ci = b.ci["src"]
    if mutation == "delay": b.G.sources[b.n(20)] = ("pin", ci, "q", 0, 3)
    if mutation == "source_bit": b.G.sources[b.n(20)] = ("pin", ci, "q", 1, 2)
    if mutation == "connection": b.F.cells[b.ci["sink"]].ports["d"][0] = b.n(10)
    if mutation == "clock": b.G.sources[b.n(30)] = ("clock", "other_domain")
    if mutation == "reset": b.G.sources[b.n(31)] = ("reset", "low", 1)
    with pytest.raises(SourceGuardError, match="source_graph_sha256"): validate_guard(ref, b)


def test_changed_transport_rules_reject_even_if_graph_cache_is_stale(b):
    ref = reference(b)
    b.ab["transport"][0]["stages"] = 3
    with pytest.raises(SourceGuardError, match="source_rules_sha256"): validate_guard(ref, b)


@pytest.mark.parametrize("op", ["or", "and"])
def test_reducer_enumeration_order_is_stable_but_delay_and_multiplicity_are_not(b, op):
    ci = b.ci["src"]
    x = ("pin", ci, "q", 0, 2); y = ("pin", ci, "q", 1, 3)
    b.G.sources[b.n(20)] = (op, [x, (op, [y, ("const", "1", "literal")], 1)], 2)
    first = logical_graph_fingerprint(b)
    b.G.sources[b.n(20)] = (op, [(op, [("const", "1", "literal"), y], 1), x], 2)
    assert logical_graph_fingerprint(b) == first
    b.G.sources[b.n(20)] = (op, [(op, [("const", "1", "literal"), y], 1), x], 3)
    assert logical_graph_fingerprint(b) != first
    b.G.sources[b.n(20)] = (op, [x, x, (op, [y, ("const", "1", "literal")], 1)], 2)
    assert logical_graph_fingerprint(b) != first


def test_constant_diagnostic_location_does_not_change_source_function(b):
    b.G.sources[b.n(20)] = ("const", "0", "literal")
    first = logical_graph_fingerprint(b)
    b.G.sources[b.n(20)] = ("const", "0", "localparam(u_other)")
    assert logical_graph_fingerprint(b) == first
    b.G.sources[b.n(20)] = ("const", "1", "literal")
    assert logical_graph_fingerprint(b) != first


def test_changed_systemverilog_module_body_fails_even_when_interface_graph_is_unchanged(b):
    ref = reference(b); path = Path(b.base) / "rtl/a.sv"
    path.write_text(path.read_text().replace("assign q=a;", "assign q=~a;"))
    with pytest.raises(SourceGuardError, match="body changed"): validate_guard(ref, b)


def test_changed_include_and_missing_file_fail(b):
    ref = reference(b); header = Path(b.base) / "rtl/defs.svh"
    header.write_text("`define SOURCE_WIDTH 3\n")
    with pytest.raises(SourceGuardError, match="body changed"): validate_guard(ref, b)
    header.unlink()
    with pytest.raises(SourceGuardError, match="missing reference RTL"): validate_guard(ref, b)


def test_new_duplicate_in_same_root_cannot_silently_replace_selected_master(b):
    ref = reference(b)
    (Path(b.base) / "rtl/0_duplicate.sv").write_text("module source(input [1:0] a, output [1:0] q); assign q=~a; endmodule\n")
    with pytest.raises(SourceGuardError, match="selected module file changed"): validate_guard(ref, b)


def test_preferred_file_change_is_a_rules_mismatch(b):
    ref = reference(b); b.ab["prefer"] = ["rtl/a.sv"]
    with pytest.raises(SourceGuardError, match="source_rules_sha256"): validate_guard(ref, b)


def test_json_rule_files_hash_content_not_location_or_compression_metadata(b):
    base = Path(b.base)
    (base / "a.json").write_text('{"one":1,"two":2}')
    (base / "b.json").write_text('{ "two": 2, "one": 1 }')
    (base / "c.json.gz").write_bytes(gzip.compress(b'{"two":2,"one":1}', mtime=0))
    b.ab["compose"] = "a.json"; first = source_rules_fingerprint(b)
    b.ab["compose"] = "b.json"; assert source_rules_fingerprint(b) == first
    b.ab["compose"] = "c.json.gz"; assert source_rules_fingerprint(b) == first
    (base / "c.json.gz").write_bytes(gzip.compress(b'{"two":3,"one":1}', mtime=0))
    assert source_rules_fingerprint(b) != first
    b.ab["compose"] = "missing.json"
    with pytest.raises(SourceGuardError, match="missing source-rule"): source_rules_fingerprint(b)


def test_physical_split_metadata_is_not_a_logical_rule_change(b):
    first = source_rules_fingerprint(b)
    b.ab.update(plan_cells="new_plan_cells.json", clock_landing_table="new_sidecar.json", map={"parts": {"a": "A0"}})
    assert source_rules_fingerprint(b) == first


def test_unsupported_source_descriptor_fails_closed(b):
    b.G.sources[b.n(20)] = ("unknown_future_tag", 99)
    with pytest.raises(SourceGuardError, match="unsupported logical source"): logical_graph_fingerprint(b)


def test_reference_cannot_omit_rtl_closure(b):
    ref = reference(b); ref["rtl_sources"] = []
    with pytest.raises(SourceGuardError, match="nonempty rtl_sources"): validate_guard(ref, b)
