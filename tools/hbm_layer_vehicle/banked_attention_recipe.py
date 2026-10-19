#!/usr/bin/env python3
"""Explicit fleet-only build/replay recipe; invoke only after chronology acceptance.

Hardware and compiler are separate immutable snapshots. This script is not an
admission wrapper: run it under ot-run --mem 64 --threads 16.
"""
import argparse, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--hardware-src',required=True);p.add_argument('--compiler-src',required=True)
p.add_argument('--bundle',required=True);p.add_argument('--kv',required=True);p.add_argument('--out',required=True)
p.add_argument('--accepted-source',required=True);a=p.parse_args()
hw=Path(a.hardware_src).resolve();compiler=Path(a.compiler_src).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
revision=(hw/'REV').read_text().strip();assert revision==a.accepted_source,'hardware source differs from explicitly accepted snapshot'
# Import the hardware snapshot's builder and its dependencies, never the compiler's.
sys.path.insert(0,str(hw/'tools/hbm_layer_vehicle'))
import smb_unit as S
assert S.ROOT.resolve()==hw
flags=['SMB_SRAMFIFO','SMB_ATTENTION','SMB_NATIVE_LANDING','SMB_NATIVE_RETURN','SMB_NATIVE_CACHE_SAFE','SMB_BANKED_CLASS']
exe=S.build(out,Path(a.bundle),flags)
manifest=dict(source_revision=revision,executable=str(exe),executable_sha256=S.sha(exe),defines=flags,id_cohort=1,
 timing=dict(native_padding=22,command_extra=4,calendar_extra=2,programme_done_extra=2,read_admission_calibration=7,actual_read_pin=8,actual_command_pin=11,busy=10),
 scope='flagged functional composition only; physical qualification remains OPEN')
mp=out/'hardware_manifest.json';mp.write_text(json.dumps(manifest,indent=2)+'\n')
env=dict(os.environ,HDC_V41_ARITH='chunk8')
for trial in ['kv8','kv4','wrong_row','read_early','descriptor_class','command_class']:
 mutation='' if trial in ('kv8','kv4') else trial
 cmd=[sys.executable,str(compiler/'tools/hbm_layer_vehicle/attention_prel_svg.py'),'--kv',a.kv,'--layer','2','--sm','2' if trial=='kv4' else '0','--work',str(out/'events'),'--name',trial,'--exe',str(exe),'--out',str(out/(trial+'.json')),'--mut',mutation,'--mixed-context','--native-profile','banked-class22','--native-padding','22','--command-extra','4','--calendar-extra','2','--programme-done-extra','2','--hardware-manifest',str(mp),'--service-build-revision',revision]
 r=subprocess.run(cmd,capture_output=True,text=True,env=env);(out/(trial+'.log')).write_text(r.stdout+r.stderr)
 if mutation:
  assert r.returncode!=0,trial+' escaped detection'
  # Nonzero alone is insufficient: retained first failure needs causal review.
  print(trial,'EXPECTED_NONZERO: inspect first retained hardware failure before accepting causality')
 else:assert r.returncode==0,trial+' positive failed'
print('POSITIVE_REPLAYS_PASS; NEGATIVE_CAUSAL_REVIEW_REQUIRED')
