"""diagnostic only: bind.py bind --all-gaps, dumping each type body before landing emission (live registered relays)."""
import runpy, sys
from pathlib import Path
S = Path(sys.argv[1]); PRE = Path(sys.argv[2]); PRE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(S / "tools/die_plan"))
import clock_landings as CL
orig = CL.Landings.type_rtl
def wrap(self, tn, txt, *a, **k):
    (PRE / f"{tn}.sv").write_text(txt)
    return orig(self, tn, txt, *a, **k)
CL.Landings.type_rtl = wrap
sys.argv = ["bind.py"] + sys.argv[3:]
runpy.run_path(str(S / "tools/die_plan/bind.py"), run_name="__main__")
