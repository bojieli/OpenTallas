#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/os.environ.get('PROBE_OUT','probe_load');OUT.mkdir(exist_ok=True)
V=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
src=[s.strip() for s in (ROOT/'rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines() if s.strip()]
src+=['rtl/qwen_split/qfd_sys_face.sv','rtl/qwen_split/qfd_embedding_word_provider.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies_mu.sv','rtl/qwen_split/qfd_sys_face_record_port.sv','rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv','rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv','rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv','rtl/test/qwen_dv/tb_gc3_cfg_load.sv']
src=list(dict.fromkeys(src))
for s in src:assert (ROOT/s).is_file(),s
(OUT/'source.sha256').write_text(''.join(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()+'  '+s+'\n' for s in src))
rows=[]
for name,bad in [('candidate',0),('missing_base',1)]:
 d=OUT/name;d.mkdir(exist_ok=True);img=ROOT/('cfg_candidate' if bad==0 else 'cfg_missing_base')
 cmd=[str(V),'--binary','--timing','-j','4','-O2','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','-Wno-WIDTH','-Wno-PINMISSING','--top-module','tb_gc3_cfg_load','--Mdir',str(d/'obj'),'-I'+str(img),'-I'+str(ROOT/'rtl/qwen_sys/d2d_static_20261015'),'-GBAD_BASE='+str(bad),*src]
 p=subprocess.run(cmd,text=True,capture_output=True);(d/'build.log').write_text(p.stdout+p.stderr)
 if p.returncode:
  print(p.stderr[-2400:]);raise SystemExit(p.returncode)
 p=subprocess.run([str(d/'obj/Vtb_gc3_cfg_load'),'+OT_ROM_DIR='+str(img)],text=True,capture_output=True);(d/'run.log').write_text(p.stdout+p.stderr)
 print(p.stdout)
 if p.returncode:raise SystemExit(p.returncode)
 rows.append(dict(case=name,exit=p.returncode,scope='realcfgROMloader andactualNU4controllerstores; OPSEGunboundhold remains'))
(OUT/'record.json').write_text(json.dumps(dict(status='CFG_LOADER_EXPECTATIONS_PASS',release_qualified=False,cases=rows),indent=2)+'\n')
