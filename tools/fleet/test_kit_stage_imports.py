"""KIT-STAGE-IMPORT-1124: ot-push-main refuses a push that makes a kit-staged tools/die_plan module import a sibling staging does not copy"""
import importlib.machinery, importlib.util, os, pathlib, subprocess as S, sys, tempfile

H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import kit_stage_imports as K  # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
SIGNOFF = ('SIGNOFF_BUNDLE = ("signoff.py", "sdc_lint.py")\nOPTIONAL_SIGNOFF_BUNDLE = ()\n'
           'KIT_TOOL_DEPENDENCIES = {"kit_preflight.py": ("sdc_lint.py",)}\n'
           'def copy_signoff_bundle(d, source=None, extra=()):\n    pass\n')
GEN = 'from signoff import copy_signoff_bundle\ndef stage(kd):\n    copy_signoff_bundle(kd, extra=("kit_preflight.py",))\n'
PRE_OK = "import sys\ndef main():\n    print('ok')\n"
PRE_BAD = "import sys\ndef main():\n    import kit_define_parity\n    print(kit_define_parity.lines())\n"
PRE_GUARD = "def main():\n    try:\n        import kit_define_parity\n    except ImportError:\n        kit_define_parity = None\n"


def sh(*a, cwd=None):
    return S.run(a, cwd=cwd, env=ENV, capture_output=True, text=True, check=True).stdout.strip()


def repo(tmp, pre):
    r = tmp / "r"; dp = r / "tools" / "die_plan"; dp.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", str(r))
    (dp / "signoff.py").write_text(SIGNOFF); (dp / "gen_phys.py").write_text(GEN); (dp / "sdc_lint.py").write_text("import gen_phys\n")
    (dp / "kit_preflight.py").write_text(PRE_OK); (dp / "kit_define_parity.py").write_text("def lines():\n    return []\n")
    sh("git", "add", "-A", cwd=r); sh("git", "commit", "-qm", "base", cwd=r)
    (dp / "kit_preflight.py").write_text(pre)
    sh("git", "commit", "-qam", "change", cwd=r)
    return r


def test_new_unstaged_sibling_import_is_refused_and_preexisting_pairs_are_not(tmp_path):
    r = repo(tmp_path, PRE_BAD)
    assert K.staging(K.Rev(str(r), "HEAD")).keys() == {"signoff.py", "sdc_lint.py", "kit_preflight.py"}
    new = K.new_pairs(str(r), "HEAD~1", "HEAD")
    assert len(new) == 1 and "kit_preflight.py:3 imports kit_define_parity" in new[0], new
    assert ("sdc_lint.py", "gen_phys") in K.pairs(str(r), "HEAD~1")          # pre-existing pair: reported, never a delta refusal
    assert K.main([str(r), "--base", "HEAD~1"]) == 1


def test_staged_sibling_or_guarded_import_passes(tmp_path):
    r = repo(tmp_path, PRE_GUARD)
    assert K.new_pairs(str(r), "HEAD~1", "HEAD") == []
    dp = r / "tools" / "die_plan"
    (dp / "kit_preflight.py").write_text(PRE_BAD)
    (dp / "signoff.py").write_text(SIGNOFF.replace('("sdc_lint.py",)', '("sdc_lint.py", "kit_define_parity.py")'))
    sh("git", "commit", "-qam", "stage it", cwd=r)
    assert K.new_pairs(str(r), "HEAD~2", "HEAD") == []


def test_ot_push_main_refuses_exit_6_and_pushes_nothing(tmp_path):
    ld = importlib.machinery.SourceFileLoader("ot_push_main_ksi", str(H / "ot-push-main"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_push_main_ksi", ld)); ld.exec_module(m)
    r = repo(tmp_path, PRE_BAD)
    o = tmp_path / "o.git"
    sh("git", "init", "-q", "--bare", "-b", "main", str(o))
    sh("git", "remote", "add", "origin", str(o), cwd=r); sh("git", "push", "-q", "origin", "HEAD~1:refs/heads/main", cwd=r)
    p = S.run([sys.executable, "-I", str(H / "ot-push-main"), "--no-test"], cwd=r, env=dict(ENV, OT_STATUS_POST="0"), capture_output=True, text=True)
    assert p.returncode == 6 and "REFUSED KIT-STAGE-IMPORT" in p.stdout and "kit_define_parity" in p.stdout, p.stdout + p.stderr
    assert sh("git", "rev-parse", "main", cwd=o) == sh("git", "rev-parse", "HEAD~1", cwd=r)
    old = os.getcwd(); os.chdir(r)
    try:
        assert m.kit_stage_refusal(["tools/fleet/x.py"], "HEAD~1") == ""          # no die_plan .py touched: not run
    finally:
        os.chdir(old)
