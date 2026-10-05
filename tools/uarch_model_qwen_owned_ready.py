"""Explicit owned-launch model extension; unified baseline stays unchanged."""
import uarch_model_qwen_local_parent as parent
from qwen_rom_owned_ready_context import price
MODEL_EXTENSION='qwen-owned-ready-parent-context'

def qwen_rom_owned_ready_price():
    return dict(extension=MODEL_EXTENSION,selected_explicitly=True,
                parent=parent.qwen_rom_local_parent_price(),owned_ready=price()[0],
                hardware_admission=False)


def qwen_rom_parallel_owner_price():
    from qwen_rom_parallel_owner_screen import price as service_price
    return dict(extension='qwen-parallel-owner-source-screen',selected_explicitly=True,
                parent=qwen_rom_owned_ready_price(),service=service_price(),
                hardware_admission=False)
