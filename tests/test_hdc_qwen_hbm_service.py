"""Check finite shared-HBM service arbitration and response ownership."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mixed_owner_four_stack_record_is_current():
    from tools.rtl_hdc_qwen_hbm_mixed_service import run

    current = run()
    recorded = json.loads((ROOT / "results/rtl/qwen_o4_hbm_mixed_service.json").read_text())
    assert current == recorded


def test_full_token_owner_regions_fault_closed(tmp_path):
    image = tmp_path / "region_guard.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_hbm_region_guard",
                    "-o", str(image),
                    "rtl/hdc/hbm/ot_hdc_qwen_hbm_regions.sv",
                    "rtl/hdc/hbm/ot_hdc_qwen_hbm_region_guard.sv",
                    "rtl/test/tb_hdc_qwen_hbm_region_guard.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen HBM region guard checks=18 layer=35 user=1" in run.stdout


def test_pc_slice_fairness_credits_and_write_completion(tmp_path):
    image = tmp_path / "pc_service.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_pc_service",
                    "-o", str(image),
                    "rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv",
                    "rtl/test/tb_hdc_qwen_pc_service.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen PC service fair=6 finite=2 backpressure=1 write_done=1" in run.stdout


def test_four_stack_pc_ownership_and_response_routes(tmp_path):
    image = tmp_path / "hbm_service.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_hbm_service",
                    "-o", str(image),
                    "rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv",
                    "rtl/hdc/hbm/ot_hdc_qwen_hbm_service.sv",
                    "rtl/test/tb_hdc_qwen_hbm_service.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen four-stack service PCs=0,31,32,127 response_owner=1 region_fault=1" in run.stdout


def test_independent_scale_base_rotates_to_physical_pc(tmp_path):
    image = tmp_path / "lane_map.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_pc_lane_map",
                    "-o", str(image),
                    "rtl/hdc/hbm/ot_hdc_qwen_pc_lane_map.sv",
                    "rtl/test/tb_hdc_qwen_pc_lane_map.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen PC lane map scale_base=456 source_lanes=0,63 PCs=72,7" in run.stdout


def test_full_token_sector_regions_fit_four_stacks(tmp_path):
    image = tmp_path / "regions.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_hbm_regions",
                    "-o", str(image),
                    "rtl/hdc/hbm/ot_hdc_qwen_hbm_regions.sv",
                    "rtl/test/tb_hdc_qwen_hbm_regions.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen HBM regions 36 layers 283 users 32-bit sectors" in run.stdout


def test_packed_kv_bridge_maps_logical_words_into_shared_pc_page(tmp_path):
    image = tmp_path / "kv_pc.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_kv_pc_adapter",
                    "-o", str(image),
                    "rtl/hdc/hbm/ot_hdc_qwen_kv_pc_adapter.sv",
                    "rtl/test/tb_hdc_qwen_kv_pc_adapter.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen packed-KV bridge PC map 32B sectors page=262144 tag=25" in run.stdout


def test_packed_kv_write_waits_for_shared_pc_completion_before_read(tmp_path):
    image = tmp_path / "kv_shared.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_kv_shared_service",
                    "-o", str(image),
                    "rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv",
                    "rtl/hdc/hbm/ot_hdc_qwen_kv_pc_adapter.sv",
                    "rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv",
                    "rtl/test/tb_hdc_qwen_kv_shared_service.sv"], cwd=ROOT, check=True)
    run = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                         text=True, check=True)
    assert "PASS Qwen shared KV RMW read-after-write" in run.stdout
