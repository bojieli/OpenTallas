import argparse,json,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable output exists')
sources=json.loads((root/'results/rtl/hbm_token_fifo_reservation_20261009/native_mtp_sources.json').read_text())['sources']
sources=[x.replace('ot_dshbm_dspark_top_stop.sv','ot_dshbm_dspark_top_cp_stop.sv').replace('ot_hfd_mtp_core_stop.sv','ot_hfd_mtp_core_cp_stop.sv').replace('hfd_mtp_x_stop.sv','hfd_mtp_x_cp_stop.sv') for x in sources]
sources+=['physical/hbm_mtp/rtl/hfd_mtp_native_cp_stop.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend_mx1.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join_mx1.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue_mx1.sv','rtl/test/hbm_accel/tb_hbm_native_mtp_cp_closed_control_mx1.sv']
cases=[]
for mutant in (0,1):
 actual=list(sources)
 if mutant:
  changed=a.work/'wrong_job.sv';original=(root/'rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend_mx1.sv').read_text();needle='cpl_job=raw[232:201]';assert needle in original;changed.write_text(original.replace(needle,"cpl_job=raw[232:201]^32'd1"));actual[actual.index('rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend_mx1.sv')]=str(changed)
 exe=a.work/f'gate{mutant}.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_mtp_cp_closed_control_mx1','-o',str(exe),*[str(root/s) for s in actual]],capture_output=True,text=True)
 if b.returncode:
  a.out.write_text(json.dumps(dict(verdict='FAIL',phase='compile',output=b.stderr),indent=2)+'\n');raise SystemExit(b.returncode)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(mutant=mutant,returncode=r.returncode,output=r.stdout))
ok=cases[0]['returncode']==0 and cases[1]['returncode']!=0
rec=dict(schema='opentallas.hbm.native_mtp_cp_closed_mx1.rtl.v1',verdict='PASS' if ok else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources},facade_source_commit='9e6e2b20e',scope='MX1 drainedreset twice, actual native40layer197facade/guard/plainfloptypedbackend/twoCP/finitehostqueue; synthetic kernelPCfixture and SM arithmetic, no productionnumerical claim; no controlECC/mirrors/resetepochs')
a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2));raise SystemExit(0 if ok else 1)
