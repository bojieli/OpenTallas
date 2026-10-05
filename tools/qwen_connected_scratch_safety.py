"""Add scratch fault/drain observability to the actual connected TC assembly.

Original source is retained. This installs no engines, storage, ports or clocks.
Loaded reduction timing remains unqualified until the combined physical run.
"""
import hashlib
import json
from pathlib import Path

BASE = Path('rtl/model/qwen_hbm_matrix_tc_factory_20261003')
OUT = Path('rtl/model/qwen_hbm_matrix_tc_safety_20261003')
MODEL = Path('results/uarch/qwen_connected_scratch_safety_20261003/model.json')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def generate(root, out=OUT):
    root = Path(root).resolve()
    out = root / out
    if out.exists():
        raise ValueError('new additive output required')
    book = json.loads((root / BASE / 'ports.json').read_text())
    top = book['top'] + '.sv'
    old_path = str(BASE / top)
    source = (root / old_path).read_bytes()
    if digest(source) != book['source_sha256'][old_path]:
        raise ValueError('actual base source pin changed')
    model = json.loads((root / MODEL).read_text())
    if model['base_sha256'] != digest(source):
        raise ValueError('model before build: source changed')
    text = source.decode()
    old = 'assign local_shared_router_drained=kv_shared_drained;'
    endpoint = ' || (|source_owner_fault)),'
    if text.count(old) != 1 or text.count(endpoint) != 1:
        raise ValueError('actual safety join anchor changed')
    text = text.replace(old, 'assign local_shared_router_drained=kv_shared_drained && (&scratch_drained);')
    text = text.replace(endpoint, ' || (|source_owner_fault) || (|scratch_fault)),')
    new_path = str(out.relative_to(root) / top)
    deps = (root / BASE / 'sources.f').read_text().splitlines()
    if deps[-1] != old_path:
        raise ValueError('selected top ordering changed')
    deps[-1] = new_path
    book['source_sha256'].pop(old_path)
    book['source_sha256'][new_path] = digest(text.encode())
    book['scratch_safety_model_sha256'] = digest((root / MODEL).read_bytes())
    book['scratch_safety_join'] = {
        'drained': 'kv_shared_drained && (&scratch_drained)',
        'endpoint_fault': 'existing endpoint faults || (|scratch_fault)',
        'added_state_bits': 0, 'added_pipeline_cycles': 0,
        'loaded_timing_qualified': False,
    }
    out.mkdir(parents=True)
    (out / top).write_text(text)
    (out / 'sources.f').write_text('\n'.join(deps) + '\n')
    (out / 'ports.json').write_text(json.dumps(book, indent=2) + '\n')
    (out / 'pin_driver.cpp').write_bytes((root / BASE / 'pin_driver.cpp').read_bytes())
    return out

if __name__ == '__main__':
    print(generate(Path(__file__).resolve().parents[1]))
