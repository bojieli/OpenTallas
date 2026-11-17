from pathlib import Path
import json,os,sys,subprocess
r=Path('/tmp/token_ds_followthrough1116');src=r/'tapfix_source';a=json.loads((src/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(src),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_FRAME_SOURCE_ROOT=str(src),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN=str(src/'selected_plan.json'),OT_XS_ASB_SCHEDULE_DIR=str(r/'tapfix_profiles'),OT_BK_TX_FACE='2')
args=[sys.executable,str(r/'source/tools/s81_dv/dv_layer_compile.py'),'--layer','L0','--svc-timing-profile','closing_allq','--die-src',str(src),'--fixtures',str(r/'L0_fixture'),'--out',str(r/'tapfix_l0'),'--bound-data',str(r/'tapfix_bind_live'),'--bound-data-manifest','/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1/asbuilt_run.json']
(r/'tapfix_l0_command.json').write_text(json.dumps(dict(argv=args,env={k:v for k,v in os.environ.items() if k.startswith('OT_')},scope='actual source intake only; current bind records pending; no legacy/final transport borrowing'),indent=1)+'\n')
raise SystemExit(subprocess.call(args))
