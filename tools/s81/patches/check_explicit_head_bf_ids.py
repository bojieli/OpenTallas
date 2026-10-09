import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, '/srv/opentallas-scratch/claude/s81-dies/src_fe365cd13/tools')
spec = importlib.util.spec_from_file_location('candidate', '/srv/opentallas-scratch/claude/s81-dies/generator_explicit_bf.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.ROOT = Path('/srv/opentallas-scratch/claude/s81-dies/src_fe365cd13')
p = m.die_options(argparse.ArgumentParser())
def options(extra):
    return p.parse_args(['--gen', 'r8', '--die', 'head', '--pairs', '696'] + extra)
m.apply_options(options([]))
legacy = m.bf_sites()
assert m.BF_PAIRS == round(696*519/2417)
m.apply_options(options(['--bf-pair-ranges', '0:338']))
assert m.PAIRS == 696 and m.BF_PAIRS == 338 and m.NV_PAIRS == 0
assert m.bf_sites() == set(range(338))
m.set_pairs(696)
assert m.BF_PAIRS == 338
capacity = m.capacity_report()
assert capacity['pairs'] == 696 and capacity['bf_double'] == 338
assert capacity['bf_pair_ids'] == list(range(338))
assert m.PAIRS == 696 and m.BF_PAIRS == 338 and m.bf_sites() == set(range(338))
for bad in ['0:339,338:340', '0:697', '-1:3', '3:3', '0', '']:
    try:
        m.parse_bf_pair_ranges(bad, 696)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)
m.apply_options(options([]))
assert m.bf_sites() == legacy and m.BF_EXPLICIT_IDS is None
print(json.dumps(dict(source_base='e2d9bbe58', inventory_pairs=696,
    explicit_BF_double=338, ordinary=358, legacy_BF=len(legacy),
    rejects_overlap_and_bounds=True, defaults_reset=True,
    scope='inventory-only; no route or real Markov engine qualification'), indent=2))
