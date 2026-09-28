import subprocess
import sys

from tools.v41_single_user_region_candidate import ROOT, build


def test_candidate_regions_are_disjoint_and_within_single_user_capacity():
    rec = build()
    for case in rec["contexts"].values():
        assert case["index_highest_addressed_end_sector_from_region_base"] <= case["index_superblock_reserved_sectors_per_stack"]
        for scenario in case["scenarios"].values():
            for stack in scenario["stacks"].values():
                regions = stack["regions"]
                assert regions[0]["start_sector"] == 0
                assert all(a["end_sector_exclusive"] == b["start_sector"] for a,b in zip(regions,regions[1:]))
                assert stack["within_usable_stack"] and stack["within_physical_stack"]


def test_current_200k_tail_and_weight_truncation_are_visible():
    rec = build()
    assert rec["contexts"]["200000"]["index_highest_addressed_end_sector_from_region_base"] == 26664
    assert rec["contexts"]["200000"]["index_superblock_reserved_sectors_per_stack"] == 28288
    assert rec["contexts"]["1048576"]["index_superblock_reserved_sectors_per_stack"] == 139264
    assert rec["comparator_weight_sectors_per_stack_if_even_stripe"] > (1 << 24)
    assert "wq_addr[23:0]" in rec["service_gates"]["hbm_comparator_weights"]


def test_strict_service_gate_remains_blocked():
    p = subprocess.run([sys.executable, "tools/v41_single_user_region_candidate.py", "--require-service"],
                       cwd=ROOT, capture_output=True, text=True, check=False)
    assert p.returncode == 2
    assert '"placement_status": "candidate_for_root_review_not_configured_in_die"' in p.stdout
