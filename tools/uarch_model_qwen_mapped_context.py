#!/usr/bin/env python3
"""Explicit source-qualified mapped Qwen context extension; no baseline mutation."""
import uarch_model_qwen_reset as unified_reset
from qwen_rom_mapped_root_pg_context import OUT, load
MODEL_EXTENSION='qwen-actual-mapped-root-pg'


def qwen_rom_mapped_context_price():
    record=load(OUT/'model-r1.json')
    if record['mapped_sha256']!='92b6cf36af938f89468c6ce07d7bd5624239172eecd914de3eb750ff435802a0':
        raise ValueError('different mapped context')
    return dict(extension=MODEL_EXTENSION,baseline_import=unified_reset.baseline.__name__,
        price_function=unified_reset.qwen_rom_reset_context_price.__name__,selected_explicitly=True,
        source_matched_context=record,hardware_admission=False)
