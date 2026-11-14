"""WF-1 11-14: in-place patch tools never touch sha-pinned snapshots."""
import inplace_patch_guard as G


def test_pinned_snapshot_files_are_never_patchable():
    base = "/srv/x/items/leaf/attempt_26"
    for p in (base + "/future_lec/run_kit_template.sh", base + "/future_lec/lec.py", base + "/future_lec/TOOL.json",
              "/srv/x/future_lec/kit_resume.py", "/a/b/run_kit_template.sh", "/a/.future_lec-abc/run_kit_template.sh"):
        assert not G.is_patchable(p), p


def test_normal_kit_runners_and_scripts_are_patchable():
    for p in ("/srv/x/items/leaf/attempt_9/gen/leaf/run_kit.sh", "/srv/x/src/tools/die_plan/gen_phys.py",
              "/srv/x/items/leaf/attempt_9/gen/leaf/lec_async.sh", "/srv/x/kit/grt183_make.sh"):
        assert G.is_patchable(p), p


def test_backups_and_temp_files_are_skipped():
    for p in ("/k/run_kit.sh.bak-wf1-1114s", "/k/run_kit.sh.wf1new", "/k/x.orig"):
        assert not G.is_patchable(p), p


def test_filter_patchable():
    assert G.filter_patchable(["/k/run_kit.sh", "/k/future_lec/run_kit_template.sh"]) == ["/k/run_kit.sh"]
