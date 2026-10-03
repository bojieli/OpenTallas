"""Instantiate the existing ten KV handlers on the actual connected RTL top.

Euclid/Claude own the simulator and clock pump; Sagan owns payload-to-W2 and
the sector authority. This glue does not launch a simulator or drive fences,
consumer completion, metadata receipts or endpoint quiescence from Python.
"""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_kv_controller import KVControllerPort
from tools.gpu_sys.canonical_qwen_kv_ports import KVHandlers

ROOT=Path(__file__).resolve().parents[2]
TOP='ot_gpu_qwen_kv_connected_ports'


def source_files(root=ROOT):
    root=Path(root)
    base=root/'rtl/model/qwen_kv_connections_20261003'
    return [root/'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv'] + [
        base/(name+'.sv') for name in (
            'ot_gpu_qwen_kv_shared_router', 'ot_gpu_qwen_kv_state_observer',
            'ot_gpu_qwen_kv_metadata_join', 'ot_gpu_qwen_kv_reader_services',
            TOP)]


class ConnectedKVHandlers:
    """Use the already-running, explicitly ENABLE=1 connected hierarchy.

    Existing get/set/settle/tick ports keep the canonical command interface.
    The enclosing hierarchy's shared services, W2 observation and real native
    parent/reverse/drain ports supply every causal input. No extra byte store.
    """
    def __init__(self, ports, authority):
        self.controller=KVControllerPort(ports,authority)
        self.service=KVHandlers(authority,self.controller.handlers)
        self.handlers=self.service.handlers
