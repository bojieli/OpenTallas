"""lec.py records the sha256 of the netlist it proved, so the late-LEC export reader can check identity.
    python3 -m pytest -q tools/die_plan/test_lec_netlist_sha256.py"""
import hashlib
import importlib.util
from pathlib import Path

LEC = Path(__file__).resolve().parent / "lec.py"


def test_netlist_sha256_is_file_byte_sha(tmp_path):
    spec = importlib.util.spec_from_file_location("lec_mod_sha", LEC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    n = tmp_path / "6_final.v"
    n.write_bytes(b"module t; endmodule\n" * 300000)
    assert mod.netlist_sha256(n) == hashlib.sha256(n.read_bytes()).hexdigest()
