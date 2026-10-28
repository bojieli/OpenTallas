"""DIE-KV-6: bind.py (unchanged, imported) on the KV strap-form landed plan, recording for every type the BOUND
partition module text BEFORE the landing insertion (the base clock_landings.type_rtl receives). strap_lec.py builds its
base from gen_rtl.wrapper, which the KV plan cannot emit (KV buses bind to as-built leaves only via bind.py), so the KV
LEC uses this captured base: same master/gold construction (strap_lec.lec_type), different base source.
Also adds rtl/common/ot_dp_clk_landing_ca.sv to the binder lib list (bind.py adds only the old-ring files).
usage: bind_capture.py CAPTURE_DIR -- <bind.py args>"""
import sys, os
from pathlib import Path
here = Path(__file__).resolve().parents[2] / "tools" / "die_plan"
sys.path.insert(0, str(here))
import clock_landings as CL
import bind as BD
cap = Path(sys.argv[1]); cap.mkdir(parents=True, exist_ok=True)
args = sys.argv[sys.argv.index("--") + 1:]
_orig = CL.Landings.type_rtl
def type_rtl(self, tn, text, base=None, inst=None, depth=None):
    if inst is None and depth is None:
        (cap / f"{tn}.sv").write_text(text)
        (cap / f"{tn}.base").write_text(str(base or tn))
    try:
        return _orig(self, tn, text, base=base, inst=inst, depth=depth)
    except Exception as e:  # report the landing error of this type (bind.py records it as one EMIT error)
        print(f"TYPE_RTL_FAIL {tn} base={base}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        raise
CL.Landings.type_rtl = type_rtl
_exp = CL.expand_station_types
def expand_station_types(B, table):
    r = _exp(B, table)
    B.extra_lib.append(str(Path(B.base).resolve() / "rtl/common/ot_dp_clk_landing_ca.sv"))
    return r
CL.expand_station_types = expand_station_types
sys.exit(BD.main(args))
