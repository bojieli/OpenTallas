"""Reserve the FUSED micro-op scratch against a vehicle's whole VM footprint."""
from pathlib import Path
import json


def reserve(meta, vm0, vmw, reserved=(), words=16384, vm_words=1 << 18):
    import numpy as np
    used = np.zeros(vm_words, dtype=bool)
    initial = np.frombuffer(vm0, '<u4')[:vm_words]
    used[:initial.size] |= initial != 0
    writes = np.frombuffer(vmw, '<u4').reshape(-1, 2)[:, 0]
    used[writes[writes < vm_words]] = True
    for record in meta['records']:
        for operand in record['eff'].values():
            base, n, m, stride, inner, space = operand[:6]
            if space != 'VM' or base >= vm_words:
                continue
            # Reserve the enclosing interval, including zero-valued inputs and holes.
            end = base + (max(m, 1) - 1) * stride + (max(n, 1) - 1) * max(inner, 1) + 1
            used[base:min(end, vm_words)] = True
    for address in reserved:
        used[address] = True
    best = (0, 0)
    i = 0
    while i < vm_words:
        if used[i]:
            i += 1
            continue
        end = i
        while end < vm_words and not used[end]:
            end += 1
        base = (i + 255) & ~255
        best = max(best, (end - base, base))
        i = end
    if best[0] < words:
        raise ValueError(f'no {words}-word FUSED scratch region in {vm_words}-word VM; largest aligned gap {best}')
    base = best[1]
    assert base + words <= vm_words and not used[base:base + words].any()
    return dict(base=base, words=words, vm_words=vm_words)


def bind_mtp_directory(directory):
    """Add only the proven scratch binding to an existing immutable golden export."""
    directory = Path(directory)
    meta_path = directory / 'meta.json'
    meta = json.loads(meta_path.read_text())
    if meta.get('schema') != 'opentallas.hgi_e2e.export_mtp.v1':
        raise ValueError('scratch binding requires an MTP export')
    plan = reserve(meta, (directory / 'vm0.bin').read_bytes(), (directory / 'vmw.bin').read_bytes())
    host_path = directory / 'host.mem'
    host = host_path.read_text().splitlines()
    if len(host) <= 97:
        raise ValueError('MTP host image has no scratch binding words')
    host[96:98] = [f'{plan["base"]:08x}', f'{plan["words"]:08x}']
    meta['fused_scratch'] = plan
    meta_path.write_text(json.dumps(meta, indent=1, default=int) + '\n')
    host_path.write_text('\n'.join(host) + '\n')
    return plan


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    print(json.dumps(bind_mtp_directory(args.directory), sort_keys=True))
