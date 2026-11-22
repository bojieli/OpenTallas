"""RESUME-STAGE-1122: the stage-resume release after AUTO-GEOM must not rename res['stage'] (run() names it after every step),
or chain_after_geom sees 'resume_release' instead of 'geom' and a resumed private kit never starts its chain."""
import ast
import inspect

import kit_wave as KW


def _run_item_tree():
    return ast.parse(inspect.getsource(KW.run_item))


def test_resume_release_only_through_the_stage_keeping_helper():
    src = inspect.getsource(KW.run_item)
    # the only direct run("resume_release", ...) call is inside the helper
    assert src.count('run("resume_release"') == 1
    helper = next(n for n in ast.walk(_run_item_tree()) if isinstance(n, ast.FunctionDef) and n.name == "resume_release")
    body = ast.get_source_segment(src, helper)
    assert 'run("resume_release"' in body and 'res["stage"] = st' in body


def test_both_resume_paths_call_the_helper_before_the_chain():
    src = inspect.getsource(KW.run_item)
    assert src.count("resume_release(svc['kit'])") == 1
    assert src.count("resume_release(K)") == 1
    for call in ("resume_release(svc['kit'])", "resume_release(K)"):
        i = src.index(call)
        assert src.index("return chain_after_geom(rc)", i) > i
