"""Actual32SM source inventory and finite-wait failure witnesses; no RTL run."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,sys
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];MAIN=Path(sys.argv[sys.argv.index('--source-root')+1]) if '--source-root' in sys.argv else (ROOT if (ROOT/'tools/h4_hbm_w19_pc10_endpoints.py').is_file() else Path('/home/ubuntu/OpenTallas'))
spec=importlib.util.spec_from_file_location('finite_source_wait',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
path=MAIN/'results/uarch/h4_hbm_w19_pc10_endpoints_20261002/directory_r3.json.gz'
raw=path.read_bytes();directory=json.loads(gzip.decompress(raw))
sources={p.name[:-3]:gzip.decompress(p.read_bytes()) for p in BASE.glob('ot_gpu*.sv.gz')}
proof=c.derive_h1_production_wait_obligations(sources,directory['rank_die_SM'])
proof['endpoint_directory_input']={'path':str(path.relative_to(MAIN)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
proof['finite_owner_source_interfaces']={'H1':'rf_owner_grant/shared_owner_grant and unconstrained sink ready inputs',
 'C0':'source-tag/version/home software scoreboard; physical arbiter and reverse endpoint not implemented here',
 'V1':'SerializedOwner response_stall_bound is an explicit input; CPU counter does not prove physical ready bound',
 'L2':'selected16KiB/die exclusion uninstalled; source_connected_RTL=False',
 'no_external_provider_omitted_as_free':'C0/GU/KV/matrix/DS alias and contender mapping must be installed at shared host/L2 ports'}
p=BASE/'wait_obligations.json';data=(json.dumps(proof,sort_keys=True,indent=2)+'\n').encode()
if '--verify' in sys.argv:
 if p.read_bytes()!=data:raise ValueError('source finite wait replay changed')
elif p.exists():raise ValueError('fresh source wait evidence required')
else:p.write_bytes(data)
print(json.dumps({'status':proof['status'],'SMs':3072,'RF_request_port_endpoints':9216,'shared_request_port_endpoints':3072,'source_leaf_read_edges':3,'source_leaf_write_edges':2,'unbounded_RF_self_loops':len(proof['unbounded_reachable_credit_hold_witnesses']),'hardware_qualified':False},sort_keys=True))
