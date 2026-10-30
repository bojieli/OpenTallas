from pathlib import Path
import json,gzip,collections
B=Path(__file__).parent;rows=json.load(open(B/'clock_sinks.json'));plans=json.load(gzip.open(B/'tree_packed_actual_pins.json.gz','rt'));screen=json.load(open(B/'packed_screen.json'));prop=json.load(open(B/'eight_entry_proposal.json'));byname={a['name']:a for a in rows};seen={};frames={}
for root,sl in plans.items():
 for leaf in sl['core_tree']['leaves']:
  for name in leaf['sinks']:
   assert name not in seen;seen[name]=root
 assert all(byname[n]['root']=='clk'if root.startswith('clk')else byname[n]['root']==root for l in sl['core_tree']['leaves']for n in l['sinks'])
 r=screen['roots'][root];frames[root]=dict(kind='RCLK'if root.startswith('clk')else'FCLK',sinks=r['sinks'],clock_cells=r['clock_cells'],input_slew_assumption_ps=20.,corners={c:dict(min_ps=v['min_ps'],mean_ps=v['mean_ps'],max_ps=v['max_ps'],slew_max_ps=v['slew_max_ps'],entry_wire_model=v['entry_wire_model'])for c,v in r['corners'].items()},actual_source_arrival_and_slew='UNBOUND: actual die/forwarded source receipt required',geometry_installed=False)
assert set(seen)==set(byname)
f=collections.Counter(a['root']for a in rows if a['master']=='DFFLQNx1_ASAP7_75t_R');assert f=={'clk':18}
receipt=dict(scope='Proposal clock-family/endpoints preservation, no physical netlist installation or new RTL proof claim',sinks=len(rows),original_family_counts=dict(collections.Counter(a['root']for a in rows)),missing=0,extra=0,duplicated=0,FCLK_owner_changes=0,RCLK_family='eight proposed real die-fed ports of the same RCLK family; actual entry phase still unqualified',falling_edge_RCLK_sinks=18,clock_inversion_change=0,existing_state_or_data_cycle_changes=0,clock_buffer_masters=sorted({n['master']for sl in plans.values()for n in sl['core_tree']['nodes']}))
(B/'functional_clock_receipt.json').write_text(json.dumps(receipt,indent=1));(B/'per_entry_frames.json').write_text(json.dumps(dict(scope='Uninstalled actual-pin/body-packed NLDM frame model; passive entry cost once, no measured source phase/STA',period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,old_nominal_RCLK_frame_ps={'TT':250,'FF':202.5},roots=frames),indent=1));print(receipt)
