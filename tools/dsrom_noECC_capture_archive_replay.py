#!/usr/bin/env python3
"""Regenerate retained reports/models without executing STA or synthesis."""
import gzip,hashlib,json,tempfile
from pathlib import Path
from dsrom_noECC_capture_terminal import archive,OUT as CAPTURE
from dsrom_noECC_boundary_loads import build as loads
from dsrom_noECC_slew_enable_diagnosis import build as diagnose,OUT as DIAG

def verify_archive(base,manifest):
    for name,expected in json.loads((base/manifest).read_text()).items():
        if hashlib.sha256((base/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Retained input changed: '+name)
def exact(value,path):
    data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if data!=path.read_bytes():raise ValueError('Regeneration mismatch: '+str(path))

def replay():
    verify_archive(CAPTURE,'terminal_hashes.json')
    with tempfile.TemporaryDirectory(prefix='dsrom-noECC-static-replay-') as tmp:
        root=Path(tmp);work=root/'capture';work.mkdir()
        for path in (CAPTURE/'terminal_r4').rglob('*'):
            if not path.is_file():continue
            rel=path.relative_to(CAPTURE/'terminal_r4')
            if path.suffix=='.gz':rel=rel.with_suffix('')
            dest=work/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
        out=root/'regenerated';out.mkdir()
        exact(archive(work,out),CAPTURE/'priced_terminal.json')
        if (out/'terminal_hashes.json').read_bytes()!=(CAPTURE/'terminal_hashes.json').read_bytes():raise ValueError('Archive changed')
        exact(loads(),CAPTURE/'boundary_loads.json')
        probe=root/'probe';probe.mkdir()
        for name in ('record.json','probe.tcl'):(probe/name).write_bytes((DIAG/'terminal'/name).read_bytes())
        (probe/'probe.log').write_bytes(gzip.decompress((DIAG/'terminal/probe.log.gz').read_bytes()))
        exact(diagnose(probe),DIAG/'model.json')
    return dict(status='BYTE_IDENTICAL_STATIC_REPLAY',models=3,terminal_archive_hashes_identical=True,STA_executed=False,synthesis_executed=False,PnR_admitted=False)
if __name__=='__main__':print(json.dumps(replay(),indent=2))
