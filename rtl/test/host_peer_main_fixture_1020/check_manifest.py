from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[3];t=r/'rtl/test/host_peer_main_fixture_1020';d=json.loads((t/'manifest.json').read_text());missing=[];bad=[]
for x in d['files']:
 p=r/x['compiled_path']
 if not p.exists():missing.append(str(p))
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:bad.append(str(p))
assert not missing and not bad,{'missing':missing,'mismatch':bad}
print('PEER_FIXTURE_DEPENDENCIES PASS',len(d['files']),'shared',d['shared_main_files'],'historical',d['isolated_historical_dependencies'])

a=next(x for x in d['files']if x['historical_path'].endswith('/qkd_hr_core_peer_sram.v'));s=(r/a['compiled_path']).read_text().replace('module qkd_hr_core_peer_sram(', 'module qkd_hr_core_peer(').replace('qkd_host_peer_link_rr_sram u_rank__u_peer','qkd_host_peer_link_rr u_rank__u_peer');assert hashlib.sha256(s.encode()).hexdigest()==d['historical_top_sha256']
a=next(x for x in d['files']if x['historical_path'].endswith('/qkd_host_peer_link_rr_sram.sv'));s=(r/a['compiled_path']).read_text().replace('module qkd_host_peer_link_rr_sram #(', 'module qkd_host_peer_link_rr #(').replace('qkd_host_peer_link #(.MUT(MUT),.SAFE_SRAM(1))','qkd_host_peer_link #(.MUT(MUT))');assert hashlib.sha256(s.encode()).hexdigest()==d['historical_rr_sha256']
print('PEER_DERIVATIVE_BYTES PASS exact historical top+rr reverse-diff; no data edge insertion')
