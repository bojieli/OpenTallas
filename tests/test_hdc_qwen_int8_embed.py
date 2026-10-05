"""RTL gates for the deployed INT8 embedding arithmetic and reduced core path."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_int8_embedding_decoder_is_bit_exact():
    run = subprocess.run([sys.executable, str(ROOT / "tools/rtl_hdc_qwen_int8_embed_decode.py")],
                         cwd=ROOT, capture_output=True, text=True, check=True)
    assert "vectors=1796 mismatches=0" in run.stdout


@pytest.mark.skipif(not (ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors").exists(),
                    reason="reduced Qwen checkpoint missing")
def test_int8_embedding_core_writes_exact_fp32_row():
    run = subprocess.run([sys.executable, str(ROOT / "tools/rtl_hdc_qwen_int8_embed_core.py")],
                         cwd=ROOT, capture_output=True, text=True, check=True)
    assert "bad=0 writes=128 code_reads=8 scale_reads=1 fault=0" in run.stdout
