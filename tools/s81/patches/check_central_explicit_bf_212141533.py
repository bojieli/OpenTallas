import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path

base=Path('/srv/opentallas-scratch/claude/s81-dies')
sys.path.insert(0,str(base/'src_fe365cd13/tools'))
p=base/'generator_212141533.py'
spec=importlib.util.spec_from_file_location('central',p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.ROOT=base/'src_fe365cd13'
ap=m.die_options(argparse.ArgumentParser())
opts=['--gen','r8','--die','head','--pairs','696']
m.apply_options(ap.parse_args(opts))
legacy=m.bf_sites()
m.apply_options(ap.parse_args(opts+['--bf-pair-ranges','0:338']))
assert m.PAIRS==696 and m.BF_PAIRS==338 and m.NV_PAIRS==0
assert m.bf_sites()==set(range(338))
cap=m.capacity_report()
assert json.loads(json.dumps(cap))['bf_pair_ids']==list(range(338))
assert m.PAIRS==696 and m.BF_PAIRS==338
for bad in ['0:339,338:340','0:697','-1:3','3:3','0','']:
    try: m.parse_bf_pair_ranges(bad,696)
    except ValueError: pass
    else: raise AssertionError(bad)
m.apply_options(ap.parse_args(opts))
assert m.bf_sites()==legacy and m.BF_EXPLICIT_IDS is None
# Exercise the actual record-mode identity restoration without drawing an
# undersized physical head: substitute only build/STA-result bodies. The
# manifest -> configure -> typed IDs path remains the central implementation.
m.build=lambda: {}
m.finalize_r8=lambda model: None
m.record_b=lambda path,model: dict(pairs=m.PAIRS,bf=m.BF_PAIRS,ids=sorted(m.bf_sites()))
with tempfile.TemporaryDirectory(dir=base,prefix='identity_probe_') as temp:
    work=Path(temp); case=work/'case'; case.mkdir()
    (case/'manifest.json').write_text(json.dumps(dict(case='b',variant=dict(
        die='head',gen='r8',rev='r9',pairs=696,bf_pair_ids=list(range(338))))))
    out=work/'record.json'
    with contextlib.redirect_stdout(io.StringIO()):
        assert m.main(['record','--work',str(work),'--out',str(out)])==0
    record=json.loads(out.read_text())['cases']['case']
    assert record==dict(pairs=696,bf=338,ids=list(range(338))),record
print(json.dumps(dict(source_commit='212141533',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    fields=696,BF_double=338,ordinary=358,legacy_BF=len(legacy),
    capacity_identity_preserved=True,record_mode_identity_restored=True,
    defaults_reset=True,rejects_overlap_and_bounds=True,
    scope='fixed inventory and actual record identity path; build and STA-result bodies stubbed; no physical or engine qualification'),indent=2))
