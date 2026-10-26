#!/usr/bin/env python3
"""Extract exact selected tap module bodies (last preferred definition wins)."""
import json,pathlib,re,hashlib,sys
root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
m=json.load(open(root/'physical/die_plan/s81/bind/asbuilt_b178_coll.json'));mods={}
for f in m['prefer']:
 p=root/f
 if not p.is_file():continue
 for mt in re.finditer(r'\bmodule\s+(dsdv_eng_tap\w*|ot_rst_relay_bounded32)\b.*?\bendmodule',p.read_text(),re.S):mods[mt[1]]=(mt.group(),f)
assert 'dsdv_eng_tap_c' in mods and 'ot_rst_relay_bounded32' in mods
(out/'selected.sv').write_text('`timescale 1ns/1ps\n'+'\n'.join(v[0] for k,v in sorted(mods.items())))
(out/'selected_sources.json').write_text(json.dumps({k:dict(source=v[1],module_sha256=hashlib.sha256(v[0].encode()).hexdigest()) for k,v in sorted(mods.items())},indent=1)+'\n')
(out/'defines.txt').write_text('\n'.join(m['defines'])+'\n')
