#!/usr/bin/env python3
"""DIE-QC-43 QC plan event qc43: plan_straps (DIE-QC-40, sha256 6d5b996f...) + landing_relay_start_copy on the 35
ring-START types (Codex 447404f/ef874 option, default OFF elsewhere) + Codex physical-only macro delta c5547024f
(30 types / 418 existing native SRAM/ROM hard_cores, core_pg_connect).  Writes OUT; copy macro_pins/ next to it.
usage: compose_qc43.py PLAN_STRAPS RING_TYPES.json MACRO_DELTA.json OUT"""
import json,sys,hashlib
src,ring,delta,out=sys.argv[1:5]
P=json.load(open(src));R=json.load(open(ring));D=json.load(open(delta))
for tn,v in sorted(R.items()):
    t=P['partition_types'][tn]; assert 'landing_relay_start_copy' not in t, tn; t['landing_relay_start_copy']=v
for tn,d in sorted(D.items()):
    t=P['partition_types'][tn]; assert not t.get('hard_cores'), tn
    t['hard_cores']=list(d['hard_cores']); t['core_pg_connect']=d['core_pg_connect']
open(out,'w').write(json.dumps(P,indent=2)+'\n')
print(out, hashlib.sha256(open(out,'rb').read()).hexdigest())
