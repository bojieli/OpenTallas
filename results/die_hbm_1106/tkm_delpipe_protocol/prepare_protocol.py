"""Prepare a fresh scratch directory; run native_v2_job.sh via ot-run32GB/4T."""
import argparse,hashlib,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--new',type=Path,required=True);p.add_argument('--dest',type=Path,required=True);a=p.parse_args()
old=a.old.read_bytes();new=a.new.read_bytes()
assert hashlib.sha256(old).hexdigest()=='2214efc605dac6ac80efbb29fe03a38486a272fde801af7e27ad1f48d27c62ff'
assert hashlib.sha256(new).hexdigest()=='101a04825316ac0e65b53059f74a282a82abf572ac692dc48c033a3a64c91fc0'
a.dest.mkdir(parents=True,exist_ok=True);assert not (a.dest/'gold.sv').exists(),'fresh evidence directory required'
(a.dest/'gold.sv').write_bytes(old.replace(b'ot_hgi_coll_tkm_tp192_root_core',b'OLD_tkm_tp192_root_core'))
(a.dest/'root.sv').write_bytes(old);(a.dest/'delpipe_v2.sv').write_bytes(new)
for n in ['tb_native_modes.sv','sram.v','native_v2_job.sh','reset_probe.py','reset_probe_job.sh','calendar_miter.py','calendar_job.sh']:shutil.copy2(Path(__file__).with_name(n),a.dest/n)
