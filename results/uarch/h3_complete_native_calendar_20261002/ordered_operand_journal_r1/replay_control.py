"""Replay retained actual provider events; no checkpoint/RTL job or Git lookup."""
import gzip,hashlib,importlib.util,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
spec=importlib.util.spec_from_file_location('calendar_control',ROOT/'tools/h3_complete_native_calendar.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
record=json.loads(gzip.decompress((BASE/'actual_disk_operand_control.json.gz').read_bytes()))
provenance=json.loads((BASE/'journal_path_and_join_handoff.json').read_bytes())
for name,pin in provenance['source_pins'].items():
    if hashlib.sha256((BASE/'source_inputs'/name).read_bytes()).hexdigest()!=pin['sha256']:
        raise ValueError('provider source byte pin changed: '+name)
proof=c.verify_ds_operand_journal(record['program'],'template',record['reference'],record['binding'],record['events'],translation=record['translation'])
if proof!=record['proof']:raise ValueError('actual operand control replay changed')
print('PASS_ACTUAL_DISK_OPERAND_JOURNAL_SOURCE_SPAN_REPLAY')
print(json.dumps(dict(sector32=proof['sector32_transactions'],scratch64=proof['scratch64_transactions'],peak_tags=proof['peak_live_provider_tags'],reverse_drained=proof['matching_reverse_drained'],production_unknown=provenance['remaining_unknown_shared_calls'],new_cost_charges=proof['additional_provider_RF_C0_I64_charge']),sort_keys=True))
