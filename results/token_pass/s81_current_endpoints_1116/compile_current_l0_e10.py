#!/usr/bin/env python3
"""One genuine current S81 L0 compile; invoked only after strict bind records exist."""
from pathlib import Path
import json,hashlib,os,subprocess,sys
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116');s=r/'selected_source';code=r/'code';b=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1');manifest=b/'asbuilt_run.json';plan=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4tapfix1.json');out=r/'l0_current'
assert not out.exists(),'preserve prior verdicts'
for name in ['bind_report.json','bus_groups.json','bind_latency.json','bind_names.json','provenance_bind.json']:assert (b/'out'/name).is_file(),name
assert hashlib.sha256(plan.read_bytes()).hexdigest()=='819037bbe371ad99945d4a9b3f11a536060280b59bd1c4ac48167d9cf77b140d'
a=json.loads((s/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(s),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_FRAME_SOURCE_ROOT=str(s),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN=str(plan),OT_XS_ASB_SCHEDULE_DIR=str(r/'profiles'),OT_BK_TX_FACE='2',OT_GUNIT_BF_DEFINES='OT_GUNIT_BF_M1REG,OT_GUNIT_BF_C1REG,OT_GUNIT_BF_SVREG,OT_GUNIT_BF_FWPIPE',OT_S81_SELECTED_CHILD_FILES='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv')
args=[sys.executable,str(code/'tools/s81_dv/dv_layer_compile.py'),'--layer','L0','--svc-timing-profile','closing_allq','--die-src',str(code),'--fixtures',str(r/'L0'),'--out',str(out),'--bound-data',str(b/'out'),'--bound-data-manifest',str(manifest)]
(r/'compile_command.json').write_text(json.dumps(dict(argv=args,env={k:v for k,v in os.environ.items() if k.startswith('OT_')},scope='ONE genuine L0 static compile, no token/simulation/adoption claim'),indent=1)+'\n')
raise SystemExit(subprocess.call(args,cwd=code))
