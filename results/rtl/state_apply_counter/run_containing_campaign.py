"""Replay the full ABI3 microsequencer campaign with the isolated apply candidate."""
from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('campaign', ROOT/'tools/rtl_abi3_campaign.py')
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
campaign.RTL_SOURCES = tuple(
    'results/rtl/state_apply_counter/candidate.sv'
    if p == 'rtl/abi3/ot_a3_state_controller.sv' else p
    for p in campaign.RTL_SOURCES
)
result = campaign.run(ROOT/'build/state_apply_counter_containing')
result['candidate_scope'] = 'Isolated overlapping apply pipeline; production state controller unchanged.'
result['source_sha256']['results/rtl/state_apply_counter/run_containing_campaign.py'] = campaign.sha256_file(Path(__file__))
output = ROOT/'results/rtl/state_apply_counter/containing_campaign.json'
output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
for case in result['cases']:
    print(case['name'], case['status'])
raise SystemExit(0 if result['status']=='pass' else 1)
