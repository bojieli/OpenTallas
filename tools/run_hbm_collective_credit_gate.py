#!/usr/bin/env python3
"""Immutable minimum-component gate; new directory per invocation, no overwrite."""
import hashlib,json,pathlib,subprocess,datetime,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
rtl=ROOT/'rtl/hbm_accel/collective_credit_20261007'
paths=[rtl/n for n in ('ot_hbm_credit_secded_pkg.sv','ot_hbm_credit_rx.sv','ot_hbm_credit_source.sv','tb_hbm_credit.sv')]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=ROOT/'results/rtl/hbm_collective_credit_20261007'/stamp
out.mkdir()
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[pathlib.Path(__file__).resolve(), ROOT/'tools/hbm_collective_credit_protocol_model.py']}
(out/'source_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tempfile.TemporaryDirectory(prefix='hbm-credit-') as td:
 cmd=['iverilog','-g2012','-s','tb_hbm_credit','-o',td+'/gate.vvp',*map(str,paths)]
 build=subprocess.run(cmd,capture_output=True,text=True)
 (out/'build.log').write_text(build.stdout+build.stderr)
 run=subprocess.run(['vvp',td+'/gate.vvp'],capture_output=True,text=True) if build.returncode==0 else None
 if run:(out/'simulation.log').write_text(run.stdout+run.stderr)
 passed=run is not None and run.returncode==0 and 'PASS credit protocol' in run.stdout
 verdict={'status':'PASS_COMPONENT_ONLY' if passed else 'FAIL','build_exit':build.returncode,'simulation_exit':None if run is None else run.returncode,'scope':'single synchronous producer/consumer component; native queues, PHY transport, epoch/quiescence provider, CDC adapters and physical closure NOT qualified','source_sha256':'source_sha256.json'}
 (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
 print(json.dumps(dict(path=str(out.relative_to(ROOT)),**verdict)))
 if not passed:raise SystemExit(1)
