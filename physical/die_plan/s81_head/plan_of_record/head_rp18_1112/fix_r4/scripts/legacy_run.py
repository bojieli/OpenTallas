"""legacy_run.py REPO OLD_PLAN SCRIPT ARGS... : run a re-derive script (remap_start.py / head_reset_exports.py) with the
OLD plan's reset trees solved by the pre-fix rule (no IN-site exclusion), the new plan by the current tools.  The OLD
plan was solved and kitted by tools without reset_tree._is_in_site, so its relay identities must be read that way."""
import os, runpy, sys
repo, old = sys.argv[1], os.path.realpath(sys.argv[2])
sys.path.insert(0, repo + "/tools/die_plan")
import reset_tree as RT, schema as S
legacy = set()
_init = S.Plan.__init__
def init(self, raw, path=None, *a, **k):
    _init(self, raw, path, *a, **k)
    if path and os.path.realpath(str(path)) == old:
        legacy.add(id(self))
S.Plan.__init__ = init
_orig = RT._is_in_site
RT._is_in_site = lambda P, *a: False if id(P) in legacy else _orig(P, *a)
script = sys.argv[3]
sys.argv = [script] + sys.argv[4:]
runpy.run_path(script, run_name="__main__")
