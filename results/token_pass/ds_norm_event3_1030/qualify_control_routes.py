#!/usr/bin/env python3
import copy,json,sys
from pathlib import Path
from layer_prog.emitted_control_routes import ControlView
base=Path(sys.argv[1]);args=[
 '/srv/opentallas-scratch2/claude/codex-s81-inventory-1030/inventory.json',
 '/srv/opentallas-scratch2/claude/die-s81-34/ev3bind/out/bind_latency.json',
 '/srv/opentallas-scratch2/claude/codex-ds-native-1029/timing_current.json',
 '/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source',
 '/srv/opentallas-scratch2/claude/die-s81-34/h2bind/asbuilt_h2_frozen_d34.json']
v=ControlView(*args);paths=[v.path(sid)for sid in range(16)]
controls={}
def reject(name,fn):
 try:fn()
 except ValueError as e:controls[name]=str(e)
 else:raise ValueError('actual selected CTL control escaped: '+name)
bus=next(b for b in v.lanes if b['lane']=='xtier__seqhost__s_4N_C');old=bus['source_bits'][0]
bus['source_bits'][0]=['leaf',old[1],old[2],1]
reject('wrong_CTL_payload_bit',lambda:v.path(9));bus['source_bits'][0]=old
bus['bound_stages']+=1;reject('wrong_CTL_lane_age',lambda:v.path(9));bus['bound_stages']-=1
reject('missing_selected_local_receipt',lambda:ControlView(*args[:2]).path(9))
result=dict(schema='opentallas.s81.selected_emitted_CTL_routes.v1',status='PASS_SELECTED_EMITTED_CTL_TO_XR',
 source_top_sha256=v.die.die_sha,source_view_sha256=v.die.source_record['source_view_sha256'],
 source_parts={k:{'file':val['file'],'sha256':val['sha256']}for k,val in v.parts.items()},
 local_receipt_sha256=v.timing_sha256,local_source_sha256=v.local_source_sha256,
 paths=paths,checked_transport_fields=v.checked,controls_caught=controls,
 physical_START_qualified=False,global_exchange_qualified=False,full_token=False,
 source_adopted=False,added_rtl_cycles=0)
(base/'control_routes.json').write_text(json.dumps(result,indent=1)+'\n')
print(result['status'],len(paths),'minmaxCalendarToXR',min(x['calendar_command_to_XR_command_edges']for x in paths),max(x['calendar_command_to_XR_command_edges']for x in paths),'controls',len(controls))
