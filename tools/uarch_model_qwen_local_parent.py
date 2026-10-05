"""Explicit whole-field local parent extension; no unified baseline mutation."""
import uarch_model_qwen_local_context as local
from qwen_rom_local_parent_composition import OUT,R
MODEL_EXTENSION='qwen-selected-local-parent-field'

def qwen_rom_local_parent_price():
    return dict(extension=MODEL_EXTENSION,selected_explicitly=True,
        baseline_import=local.unified_reset.baseline.__name__,
        local_context=local.qwen_rom_local_context_price(),
        whole_field_context=R.obj(OUT/'model-r1.json'),hardware_admission=False)
