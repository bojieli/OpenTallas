"""Exact R33 declared-to-runtime relative-path resolution, never a pin waiver."""
import copy,hashlib,json
from pathlib import Path
INPUT_FIELDS=('checkpoint_path','checkpoint_revision','checkpoint_index_sha256','checkpoint_initial_embedding','initial_versions','view_bindings','history_images','history_source_receipt','query_field_homes')

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def assert_runtime_provenance(declared,runtime,*,root):
    root=Path(root).resolve();expected=copy.deepcopy(declared['view_bindings']);resolved=[];checked={}
    for key,record in expected.items():
        path=Path(record['path'])
        if not path.is_absolute():
            actual=(root/path).resolve()
            try:actual.relative_to(root)
            except ValueError:raise ValueError('declared binding escapes committed source root')
            record['path']=str(actual);resolved.append(dict(key=key,declared_path=str(path),runtime_path=str(actual),sha256=record['sha256']))
    for name in INPUT_FIELDS:
        want=expected if name=='view_bindings' else declared[name]
        if runtime.get(name)!=want:raise ValueError('unexpected initialization source mutation '+name)
    for row in resolved:
        path=Path(row['runtime_path'])
        if str(path) not in checked:
            got=hashlib.sha256(path.read_bytes()).hexdigest()
            if got!=row['sha256']:raise ValueError('resolved source coefficient payload pin')
            checked[str(path)]=got
        elif checked[str(path)]!=row['sha256']:raise ValueError('inconsistent source alias payload pin')
    return dict(status='PASS_EXACT_R33_INITIALIZATION_PROVENANCE',declared_input_content_sha256=hashlib.sha256(canonical({k:declared[k] for k in INPUT_FIELDS})).hexdigest(),runtime_input_content_sha256=hashlib.sha256(canonical({k:runtime[k] for k in INPUT_FIELDS})).hexdigest(),source_owned_path_resolutions=len(resolved),verified_unique_coefficient_files=checked,resolved_bindings=resolved,all_other_source_fields_exact=True,hardware_qualified=False)
