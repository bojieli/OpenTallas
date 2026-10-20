#!/usr/bin/env python3
"""Package immutable census results without discarding the full reports."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
summary = {'source_commit':'49ac29c7e1fbce8855046901fcbd71864a1a227f',
           'source_sha256':hashlib.sha256((HERE / 'source_snapshot.sv').read_bytes()).hexdigest(),
           'native_status':'FAIL', 'qualified':False, 'jobs':[]}
for kind in ('t2', 't2c'):
    file = HERE / 'reports' / (kind + '_native_census.json')
    raw = file.read_bytes()
    report = json.loads(raw)
    by_family = collections.defaultdict(list)
    for v in report['violations']:
        driver = v['driver']
        family = re.sub(r'\[\d+\].*', '', driver.removeprefix('u_ot_pr_core.'))
        if driver in ('sw_v', 'se_v'):
            family = 'raw_valid_ports'
        elif driver.startswith('_'):
            family = 'combinational_predicates_and_decode'
        by_family[family].append(v)
    job = {k:report[k] for k in ('status','limit','roots_examined','max_dynamic_loads','role_errors')}
    job.update(variant=kind, full_report_sha256=hashlib.sha256(raw).hexdigest(),
               functional_pin_contract=report['functional_pin_contract'],
               pin_registration_contract=report['pin_registration_contract'], storage_contract=report['storage_contract'],
               constant_output_bits=len(report['constant_output_bits']),
               histogram=dict(collections.Counter(v['loads'] for v in report['violations'])),
               families={k:{'roots':len(v),'min_loads':min(x['loads'] for x in v),'max_loads':max(x['loads'] for x in v)} for k,v in by_family.items()},
               violations=report['violations'])
    summary['jobs'].append(job)
    with (file.with_suffix('.json.gz')).open('wb') as out:
        with gzip.GzipFile(filename='', mode='wb', fileobj=out, mtime=0) as stream:
            stream.write(raw)
    file.unlink()
(HERE / 'summary.json').write_text(json.dumps(summary,indent=2) + '\n')
