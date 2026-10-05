"""Small full64-tile directed control, never a full-token checkpoint launch."""
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
path=BASE/'actual_group128_execution.json.gz'
verify='--verify' in sys.argv
if path.exists() and not verify:raise ValueError('fresh control output required; retain old verdicts')
spec=importlib.util.spec_from_file_location('group_control_test',ROOT/'tests/test_h3_complete_native_calendar.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
result=t.FiniteCalendarTests().group_execution_fixture(capture_journals=True)
if 'error' in result:raise ValueError(result['error'])
raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode();encoded=gzip.compress(raw,mtime=0)
if verify:
    if encoded!=path.read_bytes():raise ValueError('executed source/control journal replay changed')
else:path.write_bytes(encoded)
print('PASS_EXECUTED64_TILES_REAL_DISK_PROVIDER')
print(json.dumps(dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,tiles=result['tiles_executed'],movements=result['actual_shared_movements'],primitive_scalars=result['executed_primitive_scalars'],leases=result['control_source_leases'],RF_peak=result['peak_RF_vectors'],SW_sector_ticks=result['actual_serial_sector_service_software_ticks'],production_unknown=result['production_unknown_shared_calls']),sort_keys=True))
