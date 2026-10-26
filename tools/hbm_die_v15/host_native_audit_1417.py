#!/usr/bin/env python3
"""Audit exact closed ingress boundary without promoting it to native complete."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import native_pin_audit as audit
import pinreg_audit as pinreg
VIEW='physical/ref_tile/hbm_host_static_ingress_ref/views/ot_hbm_host_static_ingress'
CELL='ot_hbm_host_static_ingress'
v=ROOT/VIEW; lib=pinreg.parse_lib(v/f'{CELL}_tt.lib')
refs=pinreg.clock_refs(lib,json.loads((v/'insertion.json').read_text()),'tt')
metrics=pinreg.pin_metrics(lib,refs)
rec=audit.audit_one((str(ROOT),CELL,VIEW))
rec['capture_failures']=[dict(pin=n,ps=m['inp']) for n,m in metrics.items() if m['dir']=='input' and m['inp'] is not None and m['inp']>190]
rec['launch_failures']=[dict(pin=n,ps=m['out']) for n,m in metrics.items() if m['dir']=='output' and m['out'] is not None and m['out']>220]
rec['source_sha256']=hashlib.sha256((ROOT/'rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv').read_bytes()).hexdigest()
rec['view_sha256']={n:hashlib.sha256((v/n).read_bytes()).hexdigest() for n in [f'{CELL}.lef',f'{CELL}_tt.lib',f'{CELL}_ff.lib','insertion.json']}
rec['scope']='Source-exact CLOSED child; routed timing stands, native parent/die adoption refused by failing boundary gates.'
rec['routed_evidence']=dict(job='hbm_host_static_ingress_ref-pinff1-144ac577a',TT_ps=103.14,FF_ps=20.27,DRC=0,record_commit='55ae56d3d',main_merge='81b2dbfea')
rec['classified_defects']=[dict(kind='launch',inferred_cause='post-flop routing/load; all public outputs are FF Q',pins=rec['launch_over'],worst_ps=rec['launch_ps'],budget_ps=220),dict(kind='capture_read_decode',inferred_cause='ARVALID/ARADDR equality decode/status mux precedes response-data flops in RTL',pins=13,budget_ps=190),dict(kind='capture_write_handshake',inferred_cause='AWVALID/WVALID handshake precedes holding-state flop in RTL',pins=2,budget_ps=190),dict(kind='reset_recovery',inferred_cause='asynchronous rst_n reaches resettable sinks',pins=1,budget_ps=190)]
rec['next']='Source owner to build explicit request landing and safe response/payload stage; isolate valid/reset control, preserve real accepted transactions and reprove timing, exact programme and mutants. No unchanged route or SDC relaxation.'
out=ROOT/'results/arch/hbm_die_v15/views_v5/host_ingress_native_1417.json'
out.write_text(json.dumps(rec,indent=1)+'\n')
print(json.dumps({k:rec[k] for k in ['pass','launch_ps','capture_ps','launch_over','capture_over','comb_pins']}))
