#!/usr/bin/env python3
"""Stage source-bound ORDER behavioral qualification in an isolated fleet run."""
import argparse
import gzip
from pathlib import Path
import shutil
import subprocess

ap=argparse.ArgumentParser()
ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--mutant',type=int,choices=[0,1,2],default=0)
args=ap.parse_args()
root=Path(__file__).resolve().parents[2]
out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
packet=root/'results/arch/host6_order_codex_1020'
(out/'original.v').write_bytes(gzip.decompress((packet/'original.v.gz').read_bytes()))
files={
 'qkd_hr_core_order_n32.sv':'rtl/qwen_sys/host_order_codex_1020/qkd_hr_core_order_n32.sv',
 'macro.v':'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v',
 'textbook_lint.py':'tools/textbook_lint.py',
 'host_order_bench.py':'tools/qwen_kv_die/host_order_bench.py',
 'host_order_models.py':'tools/qwen_kv_die/host_order_models.py',
 'host_order_prepare_models.sh':'tools/qwen_kv_die/host_order_prepare_models.sh',
}
for name in ['canonical_ASR_normalized.v','canonical_DFF_normalized.v']:
    files[name]='results/rtl/qwen_kv_die/canonical_seq_coupon_1020/formal_compatible/'+name
for destination,source in files.items():shutil.copyfile(root/source,out/destination)
subprocess.run(['docker','run','--rm','-v',str(out)+':/work','-w','/work',
                'openroad/orfs:asap7lock','bash','host_order_prepare_models.sh'],check=True)
raise SystemExit(subprocess.run(['python3','host_order_bench.py','--mutant',str(args.mutant)],cwd=out).returncode)
