#!/usr/bin/env python3
"""Explicit additive selection of current Qwen physical reset construction."""
import hashlib
from pathlib import Path
import uarch_model_qwen_reset as unified_reset

MODEL_EXTENSION='qwen-current-physical-reset'


def qwen_rom_current_reset_price():
    from qwen_rom_current_reset_construction import price, ROOT, RESET
    model=price()
    paths=['tools/uarch_model.py','tools/uarch_model_qwen_reset.py',str(RESET/'model-r5.json')]
    model['unified_model_join']=dict(extension=MODEL_EXTENSION,selected_explicitly=True,
        baseline_import=unified_reset.baseline.__name__,baseline_price_function=unified_reset.qwen_rom_reset_context_price.__name__,
        historical_reset_record_preserved=True,
        originals_sha256={p:hashlib.sha256((ROOT/Path(p)).read_bytes()).hexdigest() for p in paths})
    return model
