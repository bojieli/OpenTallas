"""KIT-COMMON-1117: every kit generator stages the one shared helper list (tools/die_plan/kit_common_files.py).

11-17: the legacy-profile and QC core kits lacked hold_sdc_guard.tcl (only gen_phys copied it) and died at 5_1_grt.
This test makes that class impossible: every gen_*kit*.py in the repo is a WRITER that reads the list, a DELEGATE
that names the writer it runs, or EXEMPT with a reason.  A new generator fails here until it is classified."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import kit_common_files as K  # noqa: E402

# writer -> how it reads the list (text that must be in its source)
WRITERS = {
    "tools/die_plan/gen_phys.py": "kit_common_files.stage(kd)",
    "tools/die_plan/core_flow.py": "kit_common_files.stage(kd)",
    "tools/ref_tile/ref_tile.py": "tools/die_plan/kit_common_files.py",
    "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py": "tools/die_plan/kit_common_files.py",
    "physical/die_plan/hbm/cores/harden/gen_core_kit.py": "tools/die_plan/kit_common_files.py",
    "physical/die_plan/s81/cores/eng/gen_core_kit.py": "tools/die_plan/kit_common_files.py",
    "physical/die_plan/s81/cores/svc/gen_core_kit_s81.py": "tools/die_plan/kit_common_files.py",
}
# generator -> (writer it runs, text in its source that shows it)
DELEGATES = {
    "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py": ("tools/die_plan/core_flow.py", "core_flow.apply("),
    "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py": ("tools/die_plan/core_flow.py", "core_flow.apply("),
    "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py": ("tools/die_plan/core_flow.py", "core_flow.apply("),
    "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm_rw.py": ("physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py", "gen_core_kit_hbm"),
    "physical/die_plan/hbm_arch_cores/sm/gen_sm_kit.py": ("physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py", "gen_core_kit_hbm"),
    "tools/hbm_coll_static/gen_coll_q2_lp_kit.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/hbm_die_v16/gen_hbm_lane_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/qwen_split/gen_fwd_lane_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/qwen_split/gen_land8_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/qwen_split/gen_land8w_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/s81_ctrl/gen_dvrly_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/s81_ctrl/gen_dvrlyh_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile"),
    "tools/s81_static_control/gen_host_c_sliced_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile.py"),
    "tools/s81_static_control/gen_host_sd_sliced_kits.py": ("tools/ref_tile/ref_tile.py", "ref_tile.py"),
}
EXEMPT = {
    "results/path_s81_codex_pd14_1027/gen_phy_kits.py": "writes kit_rtl.f RTL lists via bind.py kit-rtl, no P&R kit",
    "results/arch/part_capacity_1024/vehicle/gen_kits.py": "archived 10-24 ref_route.sh capacity experiment, no core flow",
}


def _text(rel):
    p = REPO / rel
    if p.is_file():
        return p.read_text(errors="replace")
    r = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{rel}"], capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"{rel} not readable in this checkout")
    return r.stdout


def _generators():
    r = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True)
    if r.returncode:
        pytest.skip("not a git checkout")
    return sorted(f for f in r.stdout.split()
                  if re.search(r"(^|/)gen_[^/]*kit[^/]*\.py$", f) and not re.search(r"(^|/)test_", f)
                  and "/legacy/profiles/" not in f)


def test_sources_exist():
    for name in K.FILES:
        assert K.source(name).is_file(), name


def test_stage_copies_all(tmp_path):
    assert K.stage(tmp_path) == sorted(K.FILES)
    for name in K.FILES:
        assert (tmp_path / name).read_bytes() == K.source(name).read_bytes()


def test_guard_listed_and_sourced_by_shared_tools():
    assert "hold_sdc_guard.tcl" in K.FILES
    assert "hold_sdc_guard.tcl" in (HERE / "core_final_repair.tcl").read_text()


def test_every_generator_is_classified():
    gens = _generators()
    known = set(WRITERS) | set(DELEGATES) | set(EXEMPT)
    missing = [g for g in gens if g not in known]
    assert not missing, ("new kit generator(s): stage tools/die_plan/kit_common_files.py (WRITERS) or name the writer "
                         f"they run (DELEGATES): {missing}")


def test_writers_read_the_list():
    for rel, needle in WRITERS.items():
        t = _text(rel)
        assert needle in t and ".stage(" in t, rel
        if rel.startswith("tools/die_plan/"):
            for name in K.FILES:     # no private copy left (it would drift again)
                assert not re.search(r'copyfile\([^\n]*kd / "%s"\)' % re.escape(name), t), (rel, name)


def test_delegates_run_a_writer():
    for rel, (writer, needle) in DELEGATES.items():
        assert writer in WRITERS, (rel, writer)
        assert needle in _text(rel), rel


def test_core_flow_kit_has_every_file(tmp_path, monkeypatch):
    """the QC / KV / legacy path: a kit staged by core_flow.apply holds every listed helper"""
    import core_flow
    monkeypatch.setattr(core_flow, "stage_grt183", lambda kd: None)
    try:
        core_flow.apply(tmp_path, {}, "kl_t")
    except Exception:
        pass   # the later config work needs a real kit; the helpers are staged first
    for name in K.FILES:
        assert (tmp_path / name).is_file(), name


def test_gen_phys_kit_has_every_file():
    """the type-kit path: write_type_kit calls the same stage() (checked on source: a type kit needs a full plan)"""
    t = (HERE / "gen_phys.py").read_text()
    a = t.index("\ndef write_type_kit(")
    b = t.find("\ndef ", a + 1)
    assert "kit_common_files.stage(kd)" in t[a:b if b > 0 else None]


def test_stage_carries_the_gen_env_cell_waiver_into_the_kit(tmp_path):
    """FABLE-FLOW-1555 G: the wave's OT_CELL_WAIVER (gen env) must reach /work/CELL_WAIVER, the file native_cell_cap.tcl reads in the job"""
    import kit_common_files as KCF
    import cap_estimate as CE
    for env, want in (({"OT_CELL_WAIVER": "r703"}, "r703"), ({}, ""), ({"OT_CELL_WAIVER": "please"}, ""), ({"OT_CELL_WAIVER": " r576 "}, "r576")):
        kd = tmp_path / ("k" + str(abs(hash(str(env)))))
        kd.mkdir()
        assert KCF.stage_cell_waiver(kd, env) == want
        assert (kd / "CELL_WAIVER").exists() == bool(want)
        assert CE.cell_waiver(kit=kd, env={}) == want
    tcl = (Path(KCF.__file__).with_name("native_cell_cap.tcl")).read_text()
    assert "/work/CELL_WAIVER" in tcl and "OT_CELL_WAIVER" in tcl
