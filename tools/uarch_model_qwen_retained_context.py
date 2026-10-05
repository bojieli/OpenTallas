"""Explicit opt-in composed model. Unified originals remain unchanged."""
import uarch_model_qwen_reset as unified_reset
from qwen_rom_retention_parent_launch import OUT,R
MODEL_EXTENSION='qwen-retained85-composed-context'

def qwen_rom_retained_context_price():
    record=R.obj(OUT/'model-r1.json')
    if record['selected_model_extension']!=MODEL_EXTENSION:raise ValueError('wrong extension')
    return dict(extension=MODEL_EXTENSION,baseline_import=unified_reset.baseline.__name__,
        price_function=unified_reset.qwen_rom_reset_context_price.__name__,selected_explicitly=True,
        source_matched_context=record,hardware_admission=False)
