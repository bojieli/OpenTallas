"""Rehashed synthetic controls of verifier semantics, never original artifacts."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0, str(Path.cwd()/'tools'))
from qwen_hbm_complete_verify_terminal import verify
ARCHIVE = Path('results/rtl/qwen_hbm_complete_20261001/actual_two_token_terminal_r1')

def replace_raw(directory, name, data):
    receipt=json.loads((directory/'receipt.json').read_text())
    raw=data.encode()
    payload=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw
    (directory/name).write_bytes(payload)
    receipt['artifacts_sha256'][name]=hashlib.sha256(payload).hexdigest()
    if name in receipt['original_raw_sha256']:
        receipt['original_raw_sha256'][name]['sha256']=hashlib.sha256(raw).hexdigest()
    (directory/'receipt.json').write_text(json.dumps(receipt))

results={}
for control in ['read_before_publication','terminal_fulltoken_RTL_true']:
    with tempfile.TemporaryDirectory(prefix='w19-terminal-control-') as temporary:
        root=Path(temporary)
        directory=root/ARCHIVE.name
        shutil.copytree(ARCHIVE,directory)
        shutil.copytree(ARCHIVE.parent/'actual_token0_complete_r1',root/'actual_token0_complete_r1')
        if control=='read_before_publication':
            name='token1_execution.json.gz'
            token=json.loads(gzip.decompress((directory/name).read_bytes()))
            events=token['memory_events']
            index=next(i for i,row in enumerate(events) if row['event']=='persistent_KV_read' and row['positions']==2)
            events[index-1],events[index]=events[index],events[index-1]
            replace_raw(directory,name,json.dumps(token))
        else:
            terminal=json.loads((directory/'terminal.json').read_text())
            terminal['fulltoken_RTL']=True
            replace_raw(directory,'terminal.json',json.dumps(terminal))
            lines=(directory/'run.log').read_text().splitlines()
            lines[-1]=json.dumps(terminal)
            replace_raw(directory,'run.log','\n'.join(lines)+'\n')
        try:
            verify(directory)
            results[control]={'verifier_accepts':True,'scope':'Synthetic self-rehashed artifacts, not pinned production evidence'}
        except ValueError as error:
            results[control]={'verifier_accepts':False,'error':str(error)}
print(json.dumps(results,indent=2))
