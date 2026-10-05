"""Restore exact source-bound auxiliary/seeded inputs; never overwrite a file.
Released weight shards are external. This is archive infrastructure, not a
numerical executor, a checkpoint converter or physical qualification.
"""
import argparse,hashlib,json,tarfile
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1<<20):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--restore',action='store_true');a=p.parse_args()
    pins=json.loads((a.package/'archive_sha256.json').read_bytes());inventory=json.loads((a.package/'input_inventory.json').read_bytes())
    for name in ('input_inventory.json','provider-inputs.tar'):
        if digest(a.package/name)!=pins[name]['sha256']:raise ValueError('immutable input archive '+name)
    with tarfile.open(a.package/'provider-inputs.tar','r') as tar:
        for row in inventory['files']:
            path=Path(row['path']);member=tar.getmember(row['tar_member'])
            if not member.isfile() or member.size!=row['bytes'] or row['expected_sha256'] is None:raise ValueError('source-bound regular archive member')
            if path.exists():
                if not path.is_file() or digest(path)!=row['expected_sha256']:raise ValueError('existing input differs; never overwritten '+str(path))
            elif a.restore:
                path.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256()
                with tar.extractfile(member) as source,path.open('xb') as target:
                    while chunk:=source.read(1<<20):h.update(chunk);target.write(chunk)
                if h.hexdigest()!=row['expected_sha256']:raise ValueError('restored input SHA mismatch '+str(path))
            else:
                raise ValueError('required input absent; use explicit --restore '+str(path))
    print(json.dumps(dict(status='SOURCE_INPUT_ARCHIVE_VERIFIED',restore=a.restore,inputs=len(inventory['files']),full_token_GO=False,hardware_qualified=False)))
if __name__=='__main__':main()
