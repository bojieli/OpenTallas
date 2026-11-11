"""DIE-QC-97 11-11: a 1-bit per_bit internal station flop is the scalar /q$ (no [0]); is_bits must place it FIRM.

a20 slw_fw_v3: OT_ISTATIONS missing 10 {u_ist_arl_wo_0/q$_DFF_P_ ...}; GPL then pulled u_ist_*_wo_1 back to the
launch (r2r ist_*_wo_1 -> bout_*_wo 556-585 um).  The 1-bit bus port is a [1:0] vector (data bit 0 + eq bit 1), so
the following findBTerm "${bus}[0]" resolves (a20 geom: arl_wo[0], arl_wo[1])."""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_istations as KI  # noqa: E402


def _bit_chain():
    """the flop-name -> bit branch of proc is_bits, exactly as generated"""
    body = KI.TCL_HEAD[KI.TCL_HEAD.index("proc is_bits"):]
    lines = body.splitlines()
    i = next(k for k, x in enumerate(lines) if x.strip().startswith("if {[regexp {/q"))
    j = next(k for k in range(i, len(lines)) if "lappend is_miss $nm; continue" in lines[k])
    return "\n".join(lines[i:j + 1])


def _classify(cases):
    tcl = ("proc classify {nm W} {\n set b MISS; set is_miss {}\n foreach _ {1} {\n" + _bit_chain()
           + "\n }\n return $b\n}\n" + "".join(f"puts [classify {{{nm}}} {w}]\n" for nm, w in cases))
    out = subprocess.run([shutil.which("tclsh")], input=tcl, capture_output=True, text=True, check=True).stdout
    return out.split()


def test_is_bits_bit_of_station_flop_names():
    if shutil.which("tclsh") is None:
        return                                                   # no Tcl interpreter: text check below only
    cases = [("u_bound.u_ist_arl_wo_1/q$_DFF_P_", 1),          # 1-bit station: scalar q -> bit 0 (was MISS)
             ("u_bound.u_ist_arl_wo_1/eq$_DFF_P_", 1),         # its eq -> bit W
             ("u_bound.u_ist_ard_wo_0/q\\[75\\]$_DFF_P_", 512),  # escaped vector bit
             ("u_bound.u_ist_ard_wo_0/q[3]$_DFF_P_", 512),     # plain vector bit
             ("u_bound.u_ist_ard_wo_0/q$_DFF_P_", 512)]        # a scalar q on a wide station stays a miss
    assert _classify(cases) == ["0", "1", "75", "3", "MISS"]


def test_scalar_branch_text():
    assert "{$W == 1 && [regexp {/q\\$} $nm]} { set b 0 }" in _bit_chain()
