"""Read-only native OpenDB POWER/GROUND master-terminal census.

Every instance's master terminal is the universe; net membership is not.
No global_connect, connect, repair, or write_db is performed.
"""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import odb

source = Path('/input/6_final.odb')
expected_sha = 'bf7fa57ad65ec1759e593b00b4629c9c211bf6498273a5b637b75bef6d6d1b36'
actual_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert actual_sha == expected_sha, (actual_sha, expected_sha)
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
counts = collections.Counter()
masters = {}
violations = []
inst_count = 0
with gzip.open('/out/terminals.tsv.gz', 'wt') as stream:
    stream.write('instance\tmaster\tmterm\tsignal_type\texpected_net\tactual_net\tstatus\n')
    for inst in block.getInsts():
        inst_count += 1
        master = inst.getMaster()
        pg = [m for m in master.getMTerms() if str(m.getSigType()) in ('POWER', 'GROUND')]
        masters.setdefault(master.getName(), {'instances': 0, 'pg_mterms': {m.getName(): str(m.getSigType()) for m in pg}})['instances'] += 1
        if not pg:
            counts['instances_without_pg_mterms'] += 1
        for mt in pg:
            typ = str(mt.getSigType())
            expected = 'VDD' if typ == 'POWER' else 'VSS'
            it = inst.findITerm(mt.getName())
            net = it.getNet() if it is not None else None
            actual = net.getName() if net is not None else ''
            status = 'PASS' if actual == expected else ('MISSING_ITERM' if it is None else 'UNBOUND' if net is None else 'WRONG_NET')
            counts[typ] += 1
            counts[status] += 1
            row = [inst.getName(), master.getName(), mt.getName(), typ, expected, actual, status]
            stream.write('\t'.join(row) + '\n')
            if status != 'PASS':
                violations.append(row)
report = {'source_commit': '0ecc0c258', 'final_odb_sha256': actual_sha,
          'verdict': 'PG_HOLD' if violations or counts['instances_without_pg_mterms'] else 'PG_TERMINAL_BINDING_PASS',
          'instance_count': inst_count, 'counts': dict(counts), 'masters': masters,
          'violations': violations,
          'scope': 'Every POWER/GROUND native master terminal on every final-ODB instance, independently of net membership. Terminal binding only; does not prove physical contact or parent PG.'}
Path('/out/census.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: report[k] for k in ('verdict','instance_count','counts','final_odb_sha256')}, sort_keys=True))
