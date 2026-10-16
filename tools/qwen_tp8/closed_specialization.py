"""Fail-closed source and physical identity for an explicit closed-view alias."""
import hashlib
import json
import re
from pathlib import Path


def verify(root, master):
    root = Path(root).resolve()
    profile = root / 'tools/qwen_tp8/profiles' / (master + '.json')
    d = json.loads(profile.read_text())
    if d.get('schema') != 'opentallas.qwen.closed-source-specialization.v1' or d.get('master') != master:
        raise ValueError('closed specialization: profile identity mismatch')
    from qwen_split.direct_up4 import source_contract
    contract = source_contract(root=root)
    if contract['master'] != master or contract['implementation_params'] != d['implementation_params']:
        raise ValueError('closed specialization: source parameter mismatch')
    if d['implementation_master'] != contract['implementation_master'] or len(d['modules']) != 14:
        raise ValueError('closed specialization: incomplete closed source closure')
    for name, rec in d['modules'].items():
        text = (root / rec['source']).read_text()
        bodies = re.findall(r'module\s+' + re.escape(name) + r'\b[\s\S]*?endmodule', text)
        if len(bodies) != 1 or hashlib.sha256(bodies[0].encode()).hexdigest() != rec['sha256']:
            raise ValueError(f'closed specialization: source module differs: {name}')
    view = root / d['view']
    for name, digest in d['view_sha256'].items():
        if hashlib.sha256((view / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'closed specialization: closed view differs: {name}')
    abstract = json.loads((view / 'abstract.json').read_text())
    if d['closed_record'] not in abstract.get('orfs_dir', ''):
        raise ValueError('closed specialization: wrong routed source record')
    return dict(status='exact_existing_elaboration', profile=str(profile.relative_to(root)),
                profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
                closed_source_commit=d['closed_source_commit'], closed_record=d['closed_record'],
                closed_record_sha256=d['view_sha256']['abstract.json'],
                implementation_params=d['implementation_params'], modules=d['modules'],
                view_sha256=d['view_sha256'], source_contract=contract,
                new_route_claim=False, whole_die_qualified=False)
