"""FLOW-FIX-0410: keep_regs_backport inserts the SYNTH_CANONICALIZE_TCL config line into a pre-hook flow by anchor."""
import subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keep_regs_backport as kb  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PRE_HOOK = "5e08582cb"          # main before 0d3958d56 (the hook)


def show(rev, rel):
    return subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def test_run_abi3_pre_hook_patched_once_and_idempotent():
    old = show(PRE_HOOK, kb.RUN)
    assert "keep_regs_config_lines" not in old
    new = kb.patch_run(old)
    compile(new, kb.RUN, "exec")
    assert new.count("def keep_regs_config_lines") == 1
    assert new.count("config.extend(keep_regs_config_lines(config))") == 1
    assert "\n\n\ndef design_nickname(" in new
    assert kb.patch_run(new) == new


def test_run_abi3_current_unchanged():
    cur = (ROOT / kb.RUN).read_text()
    assert kb.patch_run(cur) == cur


def test_smh_pre_hook_patched_once_and_idempotent():
    old = show(PRE_HOOK, kb.SMH)
    new = kb.patch_smh(old)
    compile(new, kb.SMH, "exec")
    assert new.count("export SYNTH_CANONICALIZE_TCL") == 1
    assert kb.patch_smh(new) == new
