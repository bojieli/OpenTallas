"""Explicit selected local subtree extension; original unified model unchanged."""
import uarch_model_qwen_reset as unified_reset
from qwen_rom_local_subtree_context import OUT,R
MODEL_EXTENSION='qwen-selected-local-subtree-context'

def qwen_rom_local_context_price():
    return dict(extension=MODEL_EXTENSION,selected_explicitly=True,
        baseline_import=unified_reset.baseline.__name__,
        price_function=unified_reset.qwen_rom_reset_context_price.__name__,
        source_matched_context=R.obj(OUT/'model-r1.json'),hardware_admission=False)
