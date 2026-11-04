"""Install a pinned LEC tool only in a new, not yet physically built wave attempt."""
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage(kit, tool, meta, runner=None, template=None):
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
    runner_update = None
    if runner is not None and template is not None:
        import kit_resume
        runner, template = Path(runner), Path(template)
        if runner.resolve() != (kit.parent / 'run_kit.sh').resolve():
            runner_update = dict(adapted=False, reason='non-TYPE runner; normal full rebuild/ECO fallback')
        else:
            if sha(template) != meta['runner_template_sha256']:
                raise ValueError('runner template differs from pinned scheduler snapshot')
            if sha(Path(kit_resume.__file__)) != meta['resume_helper_sha256']:
                raise ValueError('resume adapter differs from pinned scheduler snapshot')
            before = runner.read_text()
            after, reason = kit_resume.adapt_type_runner(before, template.read_text())
            runner_update = dict(adapted=after != before, reason=reason,
                generated_sha256=sha(runner), normalized_sha256=hashlib.sha256(kit_resume.runner_norm(before).encode()).hexdigest(),
                template_sha256=sha(template), helper_sha256=meta['resume_helper_sha256'])
            if after != before:
                runner.write_text(after)
            runner_update['sha256'] = sha(runner)
    old = sha(kit / 'lec.py')
    update = dict(kind='future-kit-lec', source_commit=meta['commit'],
                  sha256=meta['sha256'], generated_sha256=old,
                  source_receipt_present=rec is not None, runner_update=runner_update)
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
    print(json.dumps(stage(sys.argv[1], sys.argv[2], json.loads(Path(sys.argv[3]).read_text()), *(sys.argv[4:6]))))
