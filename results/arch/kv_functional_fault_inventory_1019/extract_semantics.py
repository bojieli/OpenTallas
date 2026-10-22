#!/usr/bin/env python3
"""Preserve actual selected-source evidence, without changing any source."""
import gzip,hashlib,json,pathlib,re
P=pathlib.Path('/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict')
O=pathlib.Path(__file__).parent
pb=json.loads((P/'port_bind_v2.json').read_text())
names={'qkd_host_root_admission','qkd_host_rank_services_admission','qkd_host_service_guard','qkd_host_control_packet_admission','qkd_host_packet_bundle_admission','qkd_host_fullcontrol_observed','qkd_host_tp8_coordinator','qkd_host_peer_rank_codec','qkd_host_record_port','qkd_host_ctrl_token_service_packet_collected','qkd_host_peer_root_mux','qkd_host_rx_class_admission','qkd_host_native_token_endpoint_cancel','qkd_host_ctl_service_pins','qkd_ctrl_kc','qkd_d2d_cal_seq_pin_bc','ot_qfd_land','qkd_kvs_ctl','qkd_kvs_pc','qkd_kvs_pc_h','qkd_kvs_grp','qkd_kvs_grp_h'}
rows=[]; snaps={}
W=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub')
paths=set(pb['rtl_files'])
paths.update(str(W/rec['rtl']) for rec in pb['masters'].values() if not rec['rtl'].startswith('/'))
for sub in ['host_20261013','host_integrated_20261014','context_transport_20261014']:
 paths.update(str(p) for p in (W/'rtl/qwen_sys'/sub).glob('*.sv'))
for fn in sorted(paths):
 p=pathlib.Path(fn)
 if not p.exists():continue
 t=p.read_text()
 found=set(re.findall(r'\bmodule\s+(\w+)',t))&names
 if not found:continue
 digest=hashlib.sha256(p.read_bytes()).hexdigest();snaps[str(p)]=t
 for m in sorted(found):
  match=re.search(r'\bmodule\s+'+m+r'\b.*?\bendmodule\b',t,re.S)
  assert match
  start=t[:match.start()].count('\n')+1
  rows.append(dict(module=m,path=str(p),sha256=digest,start_line=start,end_line=start+match.group().count('\n'),text=match.group()))
(O/'semantic_sources.json').write_text(json.dumps({'evidence_only':True,'modules':rows,'missing_requested_modules':sorted(names-{r['module'] for r in rows})},indent=2)+'\n')
with gzip.open(O/'selected_sources.json.gz','wt') as f:json.dump(snaps,f)
print('semantic modules',len(rows),'missing',sorted(names-{r['module'] for r in rows}))
