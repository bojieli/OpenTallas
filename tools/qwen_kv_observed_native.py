"""Prepared opt-in observation interface for a fresh qualified successor only."""
from h3_qwen_bounded_native import *
import os
from qwen_kv_observation_adapter import observed_storage

# Defaults to the original class. No enabled adapter is attached to existing jobs.
if os.environ.get('OT_QWEN_OBSERVE_KV') == '1':
    class TiledMachine(TiledMachine):
        def __init__(self, native, provider):
            super().__init__(native, provider)
            capture = os.environ['OT_QWEN_KV_CAPTURE_DIR']
            self.memory = observed_storage(BoundKVStorage, capture, enabled=True, native=native)(self.p)

        def run(self, token, position, observer=None):
            result = super().run(token, position, observer)
            self.memory.finish_observation()
            return result
