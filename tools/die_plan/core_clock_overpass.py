"""Explicit S81 hard-child clock M6 overpass; data stays M5, default unchanged."""
import json
import re
from pathlib import Path


def _value(config, key):
    values=re.findall(r'^(?:override\s+)?export\s+'+re.escape(key)+r'\s*=\s*(.*?)\s*$',config,re.M)
    return values[-1] if values else None


def stage_clock_overpass(kit, top, parent_obs, pg_top, children):
    if top is None:return None
    kit=Path(kit)
    if top!='M6' or parent_obs!='M6' or pg_top!='M6':
        raise ValueError('clock_top M6 requires the existing declared parent OBS6 / real PG6 interface')
    if not children:raise ValueError('clock overpass requires explicit SIGNED hard children')
    config_path=kit/'config.mk';config=config_path.read_text()
    if _value(config,'MAX_ROUTING_LAYER')!='M5':
        raise ValueError('clock-only M6 overpass must retain data ceiling M5')
    child_obs={}
    for master in sorted({c['master'] for c in children}):
        text=(kit/'macros'/f'{master}.lef').read_text()
        obs=re.search(r'\bOBS\s+(.*?)\n\s*END\b',text,re.S)
        levels=[int(v) for v in re.findall(r'\bLAYER\s+M(\d+)\s*;',obs[1] if obs else '')]
        if not levels or max(levels)>=6:
            raise ValueError(f'{master}: clock M6 requires actual child OBS below M6')
        child_obs[master]='M'+str(max(levels))
    hook='''# Explicit reviewed S81 clock-resource event. Native data ceiling remains M5.
if {$::env(MAX_ROUTING_LAYER) ne "M5"} {error "OT_CLOCK_OVERPASS expected unchanged data M5"}
set_routing_layers -clock "$::env(MIN_CLK_ROUTING_LAYER)-M6"
puts "OT_CLOCK_OVERPASS data $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) clock $::env(MIN_CLK_ROUTING_LAYER)-M6; 0 added cycles"
'''
    pending={"clock_overpass.tcl":hook,
             "clock_overpass_audit.tcl":Path(__file__).with_name("core_clock_overpass_audit.tcl").read_text()}
    for var,name in (('PRE_GLOBAL_ROUTE_TCL','clock_overpass_grt_pre.tcl'),('PRE_DETAIL_ROUTE_TCL','clock_overpass_drt_pre.tcl'),
                     ('POST_DETAIL_ROUTE_TCL','clock_overpass_drt_post.tcl')):
        previous=_value(config,var)
        if previous and not re.fullmatch(r'/work/[A-Za-z0-9_./-]+',previous):
            raise ValueError(f'{var}: cannot preserve nonliteral previous hook {previous!r}')
        action='clock_overpass_audit.tcl' if var=='POST_DETAIL_ROUTE_TCL' else 'clock_overpass.tcl'
        pending[name]=(f'source {previous}\n' if previous else '')+f'source /work/{action}\n'
        config+=f'override export {var} = /work/{name}\n'
    receipt=dict(schema='opentallas.s81.clock_overpass.v1',clock_top='M6',data_top='M5',parent_obs='M6',pg_top='M6',
                 child_obs=child_obs,added_signal_cycles=0,
                 rule='explicit clock-only event; final native wire audit must reject nonclock data above M5')
    for name,text in pending.items():(kit/name).write_text(text)
    config_path.write_text(config)
    (kit/'clock_overpass.json').write_text(json.dumps(receipt,indent=1)+'\n')
    return receipt
