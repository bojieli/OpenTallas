"""FLOW-GEN-2: the multirate runner's ADDR mutant edge comes from the programme (opt-in SU_MUT_ADDR_EDGE=auto)."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import su_mut_addr_edge as M  # noqa: E402

W = (M.LINE_BITS + 3) // 4


def mem(live, n=1100, other=True):
    rows = []
    for e in range(n):
        v = 0
        if other and e >= 3:
            v |= 1 << 5                                  # unrelated live bits on early lines
        if e in live:
            v |= 0x1e0 << M.FIELD_LSB
        rows.append(f"{v:0{W}x}")
    return "\n".join(rows) + "\n"


def vec(tmp_path, text):
    (tmp_path / "serial").mkdir(parents=True, exist_ok=True)
    (tmp_path / "serial" / "expected.mem").write_text(text)
    return tmp_path


def test_main_tb_matches_the_decoded_site():
    M.check_tb(M.TB.read_text())


def test_edge_follows_a_shifted_programme(tmp_path):
    assert M.edge(vec(tmp_path / "a", mem({1040, 1050}))) == 1040      # MLAT4: the TB default
    assert M.edge(vec(tmp_path / "b", mem({1041, 1050}))) == 1041      # m5w1 (REBAL-9): shifted by one


def test_fail_closed(tmp_path):
    with pytest.raises(M.EdgeError, match="never live"):
        M.edge(vec(tmp_path / "a", mem(set())))
    with pytest.raises(M.EdgeError, match="missing"):
        M.edge(tmp_path / "none")
    with pytest.raises(M.EdgeError, match="hex digits"):
        M.edge(vec(tmp_path / "b", "1f\n"))
    tb = M.TB.read_text()
    bad = tmp_path / "tb.sv"
    bad.write_text(tb.replace("line[QW+680+(1742-2-1200)+:24]", "line[QW+680+(1742-2-1201)+:24]"))
    with pytest.raises(M.EdgeError, match="site changed"):
        M.edge(vec(tmp_path / "c", mem({1041})), bad)
    bad.write_text(re.sub(r"localparam integer QW=\d+", "localparam integer QW=2400", tb))
    with pytest.raises(M.EdgeError, match="QW"):
        M.edge(vec(tmp_path / "d", mem({1041})), bad)
    r = subprocess.run([sys.executable, str(HERE / "su_mut_addr_edge.py"), str(tmp_path / "a")],
                       capture_output=True, text=True)
    assert r.returncode == 2 and r.stdout == "" and "SU_MUT_ADDR_EDGE FAIL" in r.stderr


def test_runner_opt_in_wiring():
    s = (HERE / "su_multirate_native_run.sh").read_text()
    # default: no plusarg, the TB's own 1040 (byte-identical command lines)
    assert 'mut_addr_mode=${SU_MUT_ADDR_EDGE:-tb}' in s
    assert '"$bin" +DIR="$out/vec" +MUT_$mut $( [ "$mut" = ADDR ] && [ -n "$mut_addr_arg" ] && echo "$mut_addr_arg" )' in s
    # auto: derived, fail closed before any binary runs
    assert 'mut_addr_edge=$(python3 tools/hbm_static/su_mut_addr_edge.py "$out/vec")' in s
    assert s.index("su_mut_addr_edge.py") < s.index('"$bin" +DIR="$out/vec" > "$out/positive.log"')
