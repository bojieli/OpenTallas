"""Install a pinned LEC tool only in a new, not yet physically built wave attempt."""
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage(kit, tool, meta):
    kit, tool = Path(kit), Path(tool)
    if any((kit / n).exists() for n in ('run', 'lec', 'lec_async.pid', 'lec_async.ready')):
        raise ValueError('physical/proof state already exists; live or resumed kit is never modified')
    if sha(tool) != meta['sha256']:
        raise ValueError('staged tool hash differs from scheduler snapshot')
    receipt = kit / 'PROVENANCE.json'
    rec = json.loads(receipt.read_text()) if receipt.exists() else None
    if rec is not None:
        if rec.get('schema') != 'opentallas.kit_provenance.v1':
            raise ValueError('unsupported existing source receipt')
        files = rec.get('files') or {}
        for name, digest in files.items():
            target = kit / name
            target.resolve().relative_to(kit.resolve())
            if sha(target) != digest:
                raise ValueError('source receipt differs: ' + name)
        if 'lec.py' not in files:
            raise ValueError('existing source receipt incomplete')
    old = sha(kit / 'lec.py')
    update = dict(kind='future-kit-lec', source_commit=meta['commit'],
                  sha256=meta['sha256'], generated_sha256=old,
                  source_receipt_present=rec is not None)
    # An old generator may have no source receipt. Record the tool truthfully;
    # never manufacture a source-qualified provenance claim for that case.
    if rec is not None:
        original = kit / 'PROVENANCE.generated.json'
        with original.open('x') as f:
            f.write(json.dumps(rec, indent=1) + '\n')
        update['generated_receipt_sha256'] = sha(original)
    shutil.copyfile(tool, kit / 'lec.py')
    (kit / 'LEC_TOOL.json').write_text(json.dumps(update, indent=1) + '\n')
    if rec is not None:
        rec['files']['lec.py'] = meta['sha256']
        rec['tool_update'] = update
        temporary = receipt.with_suffix('.new')
        temporary.write_text(json.dumps(rec, indent=1) + '\n')
        temporary.replace(receipt)
    return update



if __name__ == '__main__':
    import sys
    print(json.dumps(stage(sys.argv[1], sys.argv[2], json.loads(Path(sys.argv[3]).read_text()))))
