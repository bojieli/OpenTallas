"""KV-KITS-3 10-27: the UCIe PHY abstract (tools/qwen_kv_die/phy_gen.py) carries the declared line side (die-plan
bump_ports link_v/link_flit/far_v/far_flit) in LEF, LIB and blackbox, with the FDI pins unchanged."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "qwen_kv_die"))
import phy_gen  # noqa: E402

NAME = phy_gen.NAME


def _lef_pins(text):
    return dict(re.findall(r"  PIN (\S+)\n(?:.*\n){4}      LAYER \S+ ;\n      RECT ([^;]+);", text))


def test_line_side_in_all_views(tmp_path):
    for pg in ("M4", "M6"):
        d = tmp_path / pg
        sheet = phy_gen.generate(d, pg_access_layer=pg)
        v = d / NAME
        lef = (v / f"{NAME}.lef").read_text()
        pins = _lef_pins(lef)
        for p in ("link_v", "far_v", "link_flit[0]", "link_flit[582]", "far_flit[0]", "far_flit[582]",
                  "tx_flit[0]", "rx_flit[582]", "clk", "rst_n"):
            assert p in pins, p
        assert sheet["pins"]["signal_pins"] == 1171 and sheet["pins"]["line_pins"] == 2 + 2 * 583
        # top edge, no overlap, inside the macro, FDI block unchanged at x0 276.384
        xs = sorted(float(r.split()[0]) for r in pins.values() if r.split()[0] != "0.500")
        assert abs(xs[0] - 276.384) < 1e-6 and xs[-1] + 0.024 < 777.6 - 2.0
        assert all(b - a >= 0.192 - 1e-6 for a, b in zip(xs, xs[1:]))
        lib = (v / f"{NAME}_tt.lib").read_text()
        for b in ("bus (far_flit)", "bus (link_flit)", "pin (far_v)", "pin (link_v)"):
            seg = lib.split(b, 1)[1].split("\n    }", 1)[0]
            assert "timing ()" not in seg, b          # line side is untimed
        bb = (v / f"{NAME}_bb.v").read_text()
        assert "input wire [582:0] far_flit" in bb and "output wire [582:0] link_flit" in bb


def test_views_match_committed():
    """the committed views are generator output (regenerate, do not hand-edit)."""
    import tempfile
    for rel, pg in (("physical/qwen_kv_die_phy", "M4"), ("physical/die_plan/qwen_kvsys/cores/sys_c_views_m6", "M6")):
        with tempfile.TemporaryDirectory() as t:
            phy_gen.generate(Path(t), pg_access_layer=pg)
            for f in (f"{NAME}.lef", f"{NAME}_tt.lib", f"{NAME}_ff.lib", f"{NAME}_bb.v"):
                assert (Path(t) / NAME / f).read_text() == (ROOT / rel / NAME / f).read_text(), (rel, f)
