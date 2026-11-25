"""KV-HG-CDE: the checked-in qkd_ectl3_kiss_st_cols_pc.sv is exactly what gen_ectlk_pc.py makes from the checked-in sources, and the per-core
ports keep the old slices (q0 [511:0], q1 old [1023:256], q2 [767:0], q3 [1023:512])."""
import re
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent


def test_pc_file_is_generated_output():
    r = subprocess.run([sys.executable, "-I", str(D / "gen_ectlk_pc.py"), "--check", str(D / "qkd_ectlk_columns.sv"),
                        str(D / "qkd_ectl3_kiss_st_cols.sv"), str(D / "qkd_ectl3_kiss_st_cols_pc.sv")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_pc_ports_and_slices():
    t = (D / "qkd_ectl3_kiss_st_cols_pc.sv").read_text()
    for q, w in (("q0", 512), ("q1", 768), ("q2", 768), ("q3", 512)):
        assert len(re.findall(rf"input wire \[{w - 1}:0\] rsp_data_{q}\b", t)) == 3      # columns_pc, legacy_pc, wrapper_pc
    assert not re.search(r"rsp_data\[|\[1023:0\] rsp_data|compact_rsp_data", t)      # the quarters keep their own .rsp_data port
    assert "rsp_data[1023:256]" not in t
