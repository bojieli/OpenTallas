"""GENBUG-5: sibling instances of one elaborated module with fewer flops than their twin (Yosys opt_merge folded an
intentionally duplicated register bank; KV kv3_hg/hgi ti_b 6 banks in RTL, 3 in the netlist)."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

RTLIL = """attribute \\top 1
module \\top_part
  cell \\wrap \\u_bound
  end
end
module \\wrap
  cell \\stage \\u_h0
  end
  cell \\stage \\u_h1
  end
  cell $_NOT_ $auto$x
  end
end
module \\stage
end
"""


def _kit(tmp_path, merged):
    b = tmp_path / "k" / "run" / "results" / "asap7" / "dp_k" / "base"
    b.mkdir(parents=True)
    (b / "1_1_yosys_canonicalize.rtlil").write_text(RTLIL)
    v = []
    for h in (0, 1):
        if merged and h == 1:
            continue
        v += [f"  DFFHQNx1_ASAP7_75t_R \\u_bound.u_h{h}.ti_b[{i}]$_DFF_P_  (" for i in range(32)]
    (b / "1_2_yosys.v").write_text("\n".join(v) + "\n")
    return tmp_path / "k"


def _run(k):
    return subprocess.run([sys.executable, "-I", str(HERE / "merged_replica_census.py"), str(k)],
                          capture_output=True, text=True).stdout


def test_merged_twin_is_reported(tmp_path):
    out = _run(_kit(tmp_path, True))
    assert "modules_with_short_siblings 1\tflops_missing_in_short_siblings 32" in out, out
    assert "stage\tinsts 2\tshort 1\tfull_flops 32\tmissing 32\tregs ti_b:32" in out, out


def test_kept_twins_are_clean(tmp_path):
    out = _run(_kit(tmp_path, False))
    assert "modules_with_short_siblings 0\tflops_missing_in_short_siblings 0" in out, out
