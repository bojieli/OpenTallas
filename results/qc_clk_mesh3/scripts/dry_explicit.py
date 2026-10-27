"""R12 dry run of die_clock_mesh.build_explicit on r12_top_sites.json with the real QC plan (no PG, no route). UNCHECKED."""
import sys, json, collections
from pathlib import Path
sys.path.insert(0, "/w/die_plan")
import schema as S
import die_clock_mesh as DCM
P = S.Plan(S.load(sys.argv[1]), Path(sys.argv[1]))
spec = json.loads(Path(sys.argv[2]).read_text())
try:
    cells, nets, ports, M = DCM.build_explicit(spec, P=P, ndr="16w")
    print(json.dumps(dict(verdict="BUILT", cells=len(cells), nets=len(nets), ports=len(ports),
                          errors=M.get("meta", {}).get("errors") or M.get("errors"))[:3000]))
except SystemExit as e:
    msg = str(e)
    print("SYSTEMEXIT", msg[:3000])
except Exception as e:  # noqa
    import traceback; traceback.print_exc()
