"""E2BIG-1121 (FAIL-CLASS a2e8efcde6): run_item sends one ssh argument per FLOW_REFRESH_FILES entry; each must stay
under MAX_ARG_STRLEN (128 KiB) with a long real kit path (the whole set in one argument was 128,437+ chars and every
launch failed with OSError Errno 7 Argument list too long: ssh at flow_files_refresh)."""
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def test_refresh_commands_fit_one_argument():
    kit = "/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/private/LANE/t_1/gen/t"
    for ent in KW.FLOW_REFRESH_FILES:
        assert len("bash -c " + shlex.quote(KW.flow_files_refresh_cmd(kit, kit + "/../..", [ent]))) < 100_000, ent


def test_run_item_refreshes_one_file_per_command():
    src = Path(KW.__file__).read_text()
    assert "flow_files_refresh_cmd(K, None if core else W, [_ent])" in src
    assert "remote(flow_files_refresh_cmd(K, None if core else W))" not in src
