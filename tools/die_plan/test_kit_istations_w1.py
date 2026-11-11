"""DIE-QC-97 11-11: a 1-bit per_bit internal station flop is the scalar /q$ (no [0]); is_bits must place it FIRM.

a20 slw_fw_v3: OT_ISTATIONS missing 10 {u_ist_arl_wo_0/q$_DFF_P_ ...}; GPL then pulled u_ist_*_wo_1 back to the
launch (r2r ist_*_wo_1 -> bout_*_wo 556-585 um)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_istations as KI  # noqa: E402

SCALAR = r"} elseif {$W == 1 && [regexp {/q\\$} $nm]} { set b 0 } else { lappend is_miss $nm; continue }"
EQ = r"} elseif {[regexp {/eq\\$} $nm]} { set b $W"


def test_is_bits_matches_scalar_q_of_one_bit_station():
    src = Path(KI.__file__).read_text()
    lines = [x.strip() for x in src.splitlines()]
    i = lines.index(SCALAR)
    assert lines[i - 1] == EQ              # the scalar branch sits between the eq branch and the is_miss fallback
