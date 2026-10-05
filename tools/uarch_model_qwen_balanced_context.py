"""Explicit current successor clock construction, including failed fit gates."""
import uarch_model_qwen_retained_context as retained
from qwen_rom_balanced_successor_clock import OUT,R
MODEL_EXTENSION='qwen-selected-successor-clock-construction'

def qwen_rom_balanced_context_price():
    return dict(extension=MODEL_EXTENSION,selected_explicitly=True,
        baseline_import=retained.unified_reset.baseline.__name__,
        retained_context=retained.qwen_rom_retained_context_price(),
        clock_construction=R.obj(OUT/'model-r1.json'),
        admission_decision=R.obj(OUT/'admission-decision-r1.json'),hardware_admission=False)
