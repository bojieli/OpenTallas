from pathlib import Path
import json,math,re
r=Path(__file__).resolve().parent;baseline=json.load(open(r/'joint_base_nodes.json'));oldr=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-clock-sparse/results/die_hbm_1031/codex_clock_feed_probes/measured/NE_B');out={}
for v in ['north','east']:
 d=r/f'joint_NE_B_{v}';scope=json.load(open(d/'scope.json'));assert re.findall(r'Number of violations = (\d+)\.',(d/'route.log').read_text())[-1]=='0';rec=dict(scope=scope,corners={},verdict='LOCAL_JOINT_CLOCK_CONE_PASS (DRC0, real source + real prefix + three native START CLK loads)',production_gate='BLOCKED actual whole mesh/source/new station taps + real core views')
 for c in ['TT','FF']:
  old={z[1]+'/'+z[0]:list(map(float,z[2:])) for line in (oldr/f'old_arr_{c}.txt').read_text().splitlines() if (z:=line.split())};rows={z[0]:list(map(float,z[1:])) for line in (d/f'joint_arr_{c}.txt').read_text().splitlines() if (z:=line.split())};base=baseline[c]['r833_2'];y=old['ck_r833_2/Y'];nodes={}
  for n,vals in rows.items():
   if n not in ['R/Y','P1/Y','P2/Y','P3/A'] and not n.endswith('/CLK'):continue
   # Propagated clock readout uses waveform {0,416.5}; remove nominal falling-edge phase.
   nodes[n]=dict(rise_late_ps=base['node_late_ps']+vals[0]-y[3],rise_early_ps=base['node_early_ps']+vals[1]-y[4],rise_slew_ps=vals[2],fall_late_ps=base['node_fall_late_ps']+vals[3]-416.5-y[0],fall_early_ps=base['node_fall_early_ps']+vals[4]-416.5-y[1],fall_slew_ps=vals[5])
  assert all(math.isfinite(z) for node in nodes.values() for z in node.values())
  source_cal=json.load(open(oldr/f'calibration_{c}.json'));assert abs(rows['ck_r833_2/A'][2]-source_cal['target_A_rise_slew_ps'])<.1
  rec['corners'][c]=dict(nodes=nodes,old_B_P2_late_ps=baseline[c]['NE_hub/P2']['node_late_ps'],P2_late_delta_vs_old_B_ps=nodes['P2/Y']['rise_late_ps']-baseline[c]['NE_hub/P2']['node_late_ps'],source_A_rise_slew_ps=rows['ck_r833_2/A'][2],clock_waveform_fall_offset_removed_ps=416.5)
 out[v]=rec
(r/'joint_clock_receipts.json').write_text(json.dumps(out,indent=2))
for v,j in out.items():print(v,{c:dict(P2=q['nodes']['P2/Y']['rise_late_ps'],delta=q['P2_late_delta_vs_old_B_ps'],FFCLK=[z['rise_late_ps'] for n,z in q['nodes'].items() if n.endswith('/CLK')]) for c,q in j['corners'].items()})
