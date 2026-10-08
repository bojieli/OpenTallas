#!/usr/bin/env python3
"""Source-pinned cold-link provider component evidence, never overwrites runs."""
import hashlib,json,pathlib,subprocess,datetime,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
rtl=ROOT/'rtl/hbm_accel/collective_credit_20261007'
paths=[ROOT/p for p in ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv','rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv']]
paths += [rtl/n for n in ['ot_hbm_credit_secded_pkg.sv','ot_hbm_credit_rx.sv','ot_hbm_credit_source.sv','ot_hbm_link_session_coordinator.sv','ot_hbm_link_start_adapter.sv','ot_hbm_link_session_agent.sv','ot_hbm_link_management_cdc.sv','ot_hbm_initial_credit_ack_observer.sv','tb_hbm_link_session.sv']]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=ROOT/'results/rtl/hbm_collective_credit_20261007'/('session_'+stamp);out.mkdir()
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[pathlib.Path(__file__).resolve(), ROOT/'tools/hbm_collective_link_session_model.py']}
(out/'source_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tempfile.TemporaryDirectory(prefix='hbm-link-session-') as td:
 build=subprocess.run(['iverilog','-g2012','-s','tb_hbm_link_session','-o',td+'/gate.vvp',*map(str,paths)],capture_output=True,text=True)
 (out/'build.log').write_text(build.stdout+build.stderr)
 run=subprocess.run(['vvp',td+'/gate.vvp'],capture_output=True,text=True) if build.returncode==0 else None
 if run:(out/'simulation.log').write_text(run.stdout+run.stderr)
 passed=run is not None and run.returncode==0 and 'PASS cold-link provider' in run.stdout
 verdict={'status':'PASS_COMPONENT_ONLY' if passed else 'FAIL','build_exit':build.returncode,'simulation_exit':None if run is None else run.returncode,'scope':'Actual coordinator, two local agents, protected management CDCs, actual credit producer/source and initial ACK observers; native data endpoint quiet/flight and external PHY reset/quiesce acknowledgment are fixtures. Physical closure unqualified.'}
 (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n');print(json.dumps(dict(path=str(out.relative_to(ROOT)),**verdict)))
 if not passed:raise SystemExit(1)
