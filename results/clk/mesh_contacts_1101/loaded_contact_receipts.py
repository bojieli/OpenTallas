from pathlib import Path
import sys,json,re,collections
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-contacts-1101/tools/die_plan');import die_sta as D
r=Path(__file__).resolve().parent;forms={}
for form in ['near','east']:
 o=r/f'loaded_mesh_contact_{form}';nets,_=D.spef_split(o/'route.spef');n=nets['mesh_contact'];a=collections.defaultdict(set)
 for x,y,_ in n.res:a[x].add(y);a[y].add(x)
 seen={'mesh_contact'};todo=list(seen)
 for x in todo:
  for y in a[x]:
   if y not in seen:seen.add(y);todo.append(y)
 required=['M0_0:Y','M0_1:Y','L_clk:A','mesh_contact'];assert all(x in seen for x in required)
 counts=list(map(int,re.findall(r'Number of violations = (\d+)',(o/'route.log').read_text())));assert counts[-1]==0
 forms[form]=dict(drc=0,iteration_counts=counts,connected_actual_terminals=required,resistor_edges=len(n.res),Rsum_ohm=sum(v for _,_,v in n.res),Cwire_ff=sum(v for _,_,v in n.caps)*1000)
receipt=dict(verdict='ACTUAL_FIXED_MESH_DRIVER_AND_BUFFER_INPUT_CONTACT_PASS',forms=forms,source_class='cfffa2617+a7c19acdf+b1306a118',scope='Two actual union-sited BUFx24 driverY + actual BUFx4f/A buffer prototype load via explicit M8/M9 PG-gap conductor and pin stairs. Same net, no load BTerm alias. Current G core/partition/old clock geometry exactly matches E. This is a local physical buffer contact component, not a qualified native macro or complete current clock event.',release_qualified=False,remaining=['Actual current N1 complete fanout integration queued separately','108 native child K hooks unimplemented; G10 station input ports/reset/START/whole-feed/CA timing not adopted','No source-global phase or analog whole-mesh timing claim'],handled_failures=[dict(attempt='loaded east intel2',result='NOT RUN SSH255 before admission',handled='identical reviewed inputs staged epyc2 after failure, admitted unit269144 completedexit0'),dict(attempt='both successful variants iter0',result='3 DRC markers',handled='normal DRT repaired all byiter1; no input/rule change')])
(r/'loaded_contact_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
