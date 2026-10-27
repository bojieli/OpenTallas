"""DIAGNOSTIC ONLY (not a gate): run check.py with the schema errors recorded in a sidecar and then IGNORED, so the
geometry/abutment/cut/reach/latency/completeness checks still run on a plan whose new MU core types have no pin tables yet
(pins_file None = gap G3, HBM-KITS).  Usage: diag_check.py TOOLS_DIE_PLAN_DIR <check.py args...>"""
import sys, json, runpy, pathlib
tools = sys.argv[1]; sys.path.insert(0, tools)
import schema as S
_v = S.validate
def validate(raw):
    e = _v(raw)
    pathlib.Path('diag_schema_errors.json').write_text(json.dumps(e, indent=0))
    return []
S.validate = validate
sys.argv = [str(pathlib.Path(tools) / 'check.py')] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name='__main__')
