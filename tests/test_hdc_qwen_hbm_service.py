"""Check finite shared-HBM service arbitration and response ownership."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
