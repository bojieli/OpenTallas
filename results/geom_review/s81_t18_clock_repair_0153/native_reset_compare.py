import sys,json,pathlib,copy
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055');O=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-t18-source-0210');O.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'src/tools/die_plan'));import schema as S,reset_tree as RT,taps as T
p=json.load(open(R/'src/physical/die_plan/s81/plan_source39_deadrefreshed_clk28.json'));tn='slice_station__t18';P=S.Plan(p)
a=RT.for_type(P,tn)
print('old',len(a['relays']),len(a['taps']),RT.release_clocks(a))
for t in P.types[tn]['clock']['taps']:
 if t['name']=='clk_t16':print('oldxy',t['xy']);t['xy']=[197.088,294.112]
b=RT.for_type(P,tn)
for name,obj in [('old_reset',a),('new_reset',b)]: (O/(name+'.json')).write_text(json.dumps(obj,indent=1)+'\n')
def graph(t):return [(x['q'],x['d']) for x in t['relays']]
print('new',len(b['relays']),len(b['taps']),RT.release_clocks(b),'samegraph',graph(a)==graph(b));print('changedcoords',[(x['q'],x['xy'],y['xy']) for x,y in zip(a['relays'],b['relays']) if x['xy']!=y['xy']]);print('taps',a['taps']==b['taps'])
(O/'plan_candidate.json').write_text(json.dumps(p,separators=(',',':'))+'\n')
