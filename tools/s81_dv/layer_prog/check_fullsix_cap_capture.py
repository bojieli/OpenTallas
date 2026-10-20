#!/usr/bin/env python3
"""Independent released-fixture golden check of real CAP and VP captures.

Reports component facts separately; consumer retirement is not established by
these observational monitors and can never yield full-stage qualification.
Run numerical golden construction on the fleet.
"""
import importlib.util
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

root, fixture, run, checker, output = map(Path, sys.argv[1:])
sys.argv = [str(checker), str(root), str(output), str(fixture)]
spec = importlib.util.spec_from_file_location('wqbp_fixture_golden', checker)
golden = importlib.util.module_from_spec(spec)
spec.loader.exec_module(golden)
_, gold, selfcheck = golden.build_golden()
log = (run/'diagnostic.log').read_text()
expected = {}
for dim in range(512):
    off = golden.storage_offset(dim)
    leaf = (off >> 6) % 5
    address = 64*((off >> 6)//5)+(off & 63)
    expected[leaf, address] = int(gold[dim]['bf16'])
observed, commits, faults = [], [], []
for line in log.splitlines():
    m = re.fullmatch(r'ACTUAL_CW t=(\d+) valid=([0-9a-f]+) addr=([0-9a-f]+) data=([0-9a-f]+)', line)
    if m:
        t, valid, addresses, values = (int(x, 10 if i == 0 else 16) for i,x in enumerate(m.groups()))
        for port in range(10):
            if (valid >> port) & 1:
                observed.append((t, port//2, (addresses >> (12*port)) & 4095, (values >> (32*port)) & 0xffffffff))
    m = re.fullmatch(r'VP_ACTUAL_COMMIT t=(\d+) leaf=(\d+) bank=(\d+) row=(\d+) mask=([0-9a-f]+) data=([0-9a-f]+) cwv=([01]+) collision=([01])',line)
    if m and int(m[7],2):
        t, leaf, bank, row = map(int,m.group(1,2,3,4))
        mask, data = int(m[5],16), int(m[6],16)
        if m[8] != '0': faults.append(line)
        for word in range(4):
            wm = (mask >> (32*word)) & 0xffffffff
            if wm:
                if wm != 0xffffffff: faults.append(line)
                commits.append((t,leaf,(row << 3)+(bank << 2)+word,(data >> (32*word)) & 0xffffffff))
    if 'CAP_LIFETIME ' in line and re.search(r'causes=(?!0000)[0-9a-f]+',line): faults.append(line)
    if 'FULLSIX_PREPARATORY_TRACE_END' in line and 'CAPfault=0 landfaults=0000 otherVPfaults=00000' not in line: faults.append(line)
count = Counter((leaf, address) for _,leaf,address,_ in observed)
bad_values = [row for row in observed if expected.get(row[1:3]) != row[3]]
missing = sorted(set(expected)-set(count))
extra = sorted(set(count)-set(expected))
duplicates = [list(k)+[v] for k,v in count.items() if v != 1]
expected_commits = Counter((t+5,leaf,address,value) for t,leaf,address,value in observed)
actual_commits = Counter(commits)
source_lines = [line for line in log.splitlines() if 'MISMATCH' in line or 'FULLSIX_SOURCE_CHECK' in line or 'FULLSIX_PREPARATORY_TRACE_END' in line]
terminals=re.findall(r'^FULLSIX_PREPARATORY_TRACE_END .*$',log,re.M)
source_checks=re.findall(r'^FULLSIX_SOURCE_CHECK errors=(\d+) rawwrites=(\d+) gathers=(\d+) epochs=(\d+)$',log,re.M)
simulator_exit=int((run/'simulator.exit').read_text())
terminal_ok=(len(terminals)==1 and source_checks==[('3','320','20','15')] and simulator_exit==1
             and 'RETAINED_CONTROL_MISMATCH gos15 ends1 gws1 macwrites40 lastcommit1260' in log
             and 'EPOCH_READ_COUNTS epoch=0 actual=21 expected=24' in log
             and 'EPOCH_READ_COUNTS epoch=14 actual=27 expected=24' in log)
golden_ok = (selfcheck['contract_rows']==512 and not selfcheck['contract_mismatch'] and not selfcheck['shard_bf16_mismatch'])
component_pass = terminal_ok and golden_ok and bool(observed) and not (bad_values or missing or extra or duplicates or faults or expected_commits != actual_commits)
result = dict(scope='CAP/CW/VP component only; consumer read/retirement/deadline proof OPEN',
              full_stage_qualified=False, component_capture_PASS=component_pass,
              fixture=str(fixture),fixture_meta_sha256=hashlib.sha256((fixture/'meta.json').read_bytes()).hexdigest(),
              golden_self_check=selfcheck, expected_rows=len(expected), cw_words=len(observed), vp_words=len(commits),
              missing=missing,extra=extra,duplicates=duplicates,bad_values=bad_values,
              missing_commits=list((expected_commits-actual_commits).elements()),extra_commits=list((actual_commits-expected_commits).elements()),
              faults=faults[:25], fault_observations=len(faults), source_assertions=source_lines,
              terminal_receipt_PASS=terminal_ok,simulator_exit=simulator_exit)
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('faults','golden_self_check')},indent=2))
sys.exit(0 if component_pass else 1)
