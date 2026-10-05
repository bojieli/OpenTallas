"""Pure source preflight for published D1 fixture prerequisites; no external ROOT."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'results/uarch/w17_D1_portable_successor_20261002'
def validate(root=ROOT):
    manifest=json.loads((root/'results/uarch/w17_D1_portable_successor_20261002/prerequisite_manifest.json').read_text())
    if manifest['source_pin']!='4e38326d6f361bc85e660f48c59c355e2bb95274':raise ValueError('source pin')
    for name,row in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('prerequisite path escape')
        if not path.is_file() or path.stat().st_size!=row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('missing/drifted prerequisite '+name)
    return dict(verdict='PASS_SELF_CONTAINED_MATERIALIZED_PREREQUISITES',files=len(manifest['files']),bytes=manifest['total_bytes'],private_ROOT_reads=False,compiler_invocations=0,simulations=0)
if __name__=='__main__':print(json.dumps(validate(),indent=2))
