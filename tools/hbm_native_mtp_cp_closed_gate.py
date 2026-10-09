import argparse,json,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable output exists')
sources=json.loads((root/'results/rtl/hbm_token_fifo_reservation_20261009/native_mtp_sources.json').read_text())['sources']
sources=[x.replace('ot_dshbm_dspark_top_stop.sv','ot_dshbm_dspark_top_cp_stop.sv').replace('ot_hfd_mtp_core_stop.sv','ot_hfd_mtp_core_cp_stop.sv').replace('hfd_mtp_x_stop.sv','hfd_mtp_x_cp_stop.sv') for x in sources]
sources+=['physical/hbm_mtp/rtl/hfd_mtp_native_cp_stop.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20_protected.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue.sv','rtl/test/hbm_accel/tb_hbm_native_mtp_cp_closed_control.sv']
exe=a.work/'gate.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_mtp_cp_closed_control','-o',str(exe),*[str(root/s) for s in sources]],capture_output=True,text=True)
if b.returncode:
 a.out.write_text(json.dumps(dict(verdict='FAIL',phase='compile',output=b.stderr),indent=2)+'\n');raise SystemExit(b.returncode)
r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
rec=dict(schema='opentallas.hbm.native_mtp_cp_closed.rtl.v1',verdict='PASS' if r.returncode==0 else 'FAIL',returncode=r.returncode,output=r.stdout,source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources},facade_source_commit='9e6e2b20e',scope='minimum real40layer nativecontrol+guard+typedtwoCPbackend+finitehostqueue integration; synthetic kernelPC fixture and SM arithmetic/ready source; no fulltarget simulation or numerical claim')
a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2));raise SystemExit(r.returncode)
