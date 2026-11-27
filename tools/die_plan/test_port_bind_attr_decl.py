"""DIE-HEAD-7 10-28 (RM92 gate): nested_check resolves wires declared with a leading attribute ((* keep = 1 *) wire
rst_n_t<k>; the TILEIO local reset consumers u_rrl_<k> (ot_dp_rgate).q) and still catches width mismatches on them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import port_bind_gate as PBG  # noqa: E402

SRC = "module leaf (input wire clk, input wire d, output reg q);\nendmodule\n"


def _wr(decl):
    return {"w.sv": "module w (\n    input wire clk,\n    input wire d\n);\n" + decl +
            "    leaf u_l (.clk(clk), .d(d), .q(x));\nendmodule\n"}


def test_attribute_declared_wire_resolves():
    r = PBG.nested_check(_wr("    (* keep = 1 *) wire x;\n"), [SRC])
    assert r["verdict"] == "PASS", r


def test_attribute_declared_wire_width_still_checked():
    r = PBG.nested_check(_wr("    (* keep = 1 *) wire [1:0] x;\n"), [SRC])
    assert r["verdict"] == "FAIL" and r["width_mismatch"] == 1, r


def test_post_synth_selector_failure_uses_existing_port_bind_gate(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    synth = tmp_path / '1_2_yosys.v'
    synth.write_text('module dut (a); input a; endmodule\n')
    odb = tmp_path / '1_synth.odb'
    odb.write_bytes(b'saved synth')
    (tmp_path / 'budget.json').write_text('{"module": "dut"}')
    (tmp_path / 'port_bind_pins.json').write_text('[]')
    monkeypatch.setattr(PBG, 'check', lambda *args: {'verdict': 'PASS'})
    calls = []

    def fake_openroad(argv, **kwargs):
        calls.append(argv)
        assert argv[:2] == ['openroad', '-exit']
        assert kwargs['env']['OT_NATIVE_STAGE_SELECTOR_ODB'] == str(odb)
        script = Path(argv[2]).read_text()
        assert script.index('read_db') < script.index('CHECK_EXACT_SELECTOR')
        assert 'write_db' not in script
        return SimpleNamespace(returncode=16, stdout='OT_NATIVE_STAGE_SELECTOR SHADOWED stage:old\n')

    monkeypatch.setattr(PBG.subprocess, 'run', fake_openroad)
    assert PBG.main([str(synth), str(tmp_path)]) == 0
    assert not calls
    monkeypatch.setattr(PBG, '_NATIVE_STAGE_SELECTOR_TCL', 'CHECK_EXACT_SELECTOR\n')
    assert PBG.main([str(synth), str(tmp_path)]) == 1
    assert len(calls) == 1
    assert json.loads((tmp_path / 'port_bind.json').read_text())['native_selector_exit'] == 16
    assert odb.read_bytes() == b'saved synth'
