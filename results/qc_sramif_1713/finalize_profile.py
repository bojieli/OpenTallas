from pathlib import Path
import json,hashlib
p=Path('/srv/opentallas-scratch2/claude/codex-qc-sramif-1713')
for k in ('btab','prog'):
 d=p/(k+'_aspect_a1')
 if not d.exists():continue
 j=json.loads((d/'profile1713.json').read_text());ps=json.loads((d/'pins.json').read_text());out={'bs_q','fault'} if k=='btab' else {'p_q'}
 rows=[dict(name=x['bus']+(f"[{x['bit']}]" if x['bit'] is not None else ''),layer=x['layer'],x=x['x'],y=x['y'],face=x['face'],dir='out' if x['bus'] in out else 'in') for x in ps]
 (d/'target_native_pins.json').write_text(json.dumps(dict(schema='opentallas.core_pins.v1',core=j['module'],frame='core R0, origin (0,0)',source='NEW genuine equal-area profile1713; planned native signal pins; NOT SIGNED; must match actual final LEF',pins=rows),indent=1)+'\n')
 (d/'geom_review1713.json').write_text(json.dumps(dict(verdict='PASS FOR PLANNED GEOMETRY REVIEW ONLY; INDEPENDENT REVIEW REQUIRED BEFORE P&R',picture='aspect1713_plan.png',findings='Same-area R0 frame354.24x259.2. Four SRAMs at y30.24/86.4/142.56/198.72 with4.32um halos,6.456um clear inter-macro channels and wide bilateral IF/gather channels. South input strip4.32..25.92um and central clock access gap. Native pin catalogue preserves every source port/bit, .192um pitch on .048 track phase .012, S-M5 pins avoid BOTH VDD/VSS stripe rails; E-M4 pins preserve direction.12 regional clock banks outside halos; localCTS16sinks/35um diameter. No old shape RCX table transferred. PDN template unchanged, native actual PG/placement/F6 to be checked before CTS/GRT/route.',source_rtl_cycles_added=0,approval='/home/ubuntu/coord/qc-su-aspect-1713-impact.md'),indent=1)+'\n')
 manifest={str(x.relative_to(d)):hashlib.sha256(x.read_bytes()).hexdigest() for x in d.rglob('*') if x.is_file() and '/run/' not in str(x)}
 (d/'profile_input_manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
 print(d)
