#!/usr/bin/env python3
"""Stage the exact native VMDQ mechanism+protocol gate; run via ot-run in OUT."""
import argparse,json,hashlib,shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();R=Path(__file__).resolve().parents[2];D=R/'rtl/hbm_accel/loader/service_native/split';T=R/'rtl/test/hbm_vmdel_payload_capture';a.out.mkdir(parents=True,exist_ok=True)
files={'native.sv':D/'ot_hbm_svc_vmdel_lane_n.sv','old_split.sv':D/'ot_hbm_svc_static_vm_delivery_split.sv','sram.v':R/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','capture_miter.sv':T/'capture_miter.sv','run_capture_proof.sh':T/'run.sh'}
for dst,src in files.items():shutil.copyfile(src,a.out/dst)
s=(D/'tb_hbm_svc_vmdel_lane_n_lockstep.sv').read_text()
for n,label in [(2,'b'),(4,'c')]:
 old=f'#(.NPC({n})) u_{label}';assert s.count(old)==1;s=s.replace(old,f'#(.NPC({n}),.PAYLOAD_BANK_CAPTURE(1)) u_{label}')
(a.out/'native_tb.sv').write_text(s)
(a.out/'manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.out.iterdir()if p.is_file()},indent=2)+'\n')
print('Staged. Run only via ot-run --dir OUT --mem 8 --threads 2 -- bash run_capture_proof.sh')
