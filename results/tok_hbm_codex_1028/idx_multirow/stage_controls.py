"""Stage real source dependencies into an owned scratch runtime before ot-run."""
from pathlib import Path
import shutil
import sys
root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
files = list((root/'physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/index').rglob('*.sv'))
files += [root/p for p in ('rtl/hbm_next/idxn/ot_hnx_idxn_calendar.sv',
    'rtl/hbm_next/idxq/ot_hnx_idxq_qctl.sv',
    'rtl/hbm_next/idxq/ot_hnx_idxq_rootctl_static_am.sv', 'rtl/lib/ot_rst_relay.sv')]
for pattern in ('*256x256_m2_r2c2*/*.v', '*128x256_m1_r2c2*/*.v', '*32x64_m1*/*.v'):
    files += list((root/'physical/asap7_memory_macros_v2').glob(pattern))
for name in ('tb_idxqroot_service.sv', 'tb_idxq_delivered_reset.sv', 'run_root_service.sh', 'run_qctl_reset.sh'):
    files.append(Path(__file__).parent/name)
seen = set()
for source in files:
    if source.name in seen:
        raise ValueError(f'duplicate source basename: {source}')
    seen.add(source.name)
    shutil.copyfile(source, out/source.name)
print(f'staged {len(files)} source/runner files')
