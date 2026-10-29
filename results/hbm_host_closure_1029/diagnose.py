import json,pathlib,collections,sys
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);d=json.load(open(p));h=[];rows=[]
for e in d['unproven_points']:
 if e['status']!='differs':continue
 assert e['point'].startswith('ff:u_dut.u_fcore.u_link.u_core.u_codec.q_pin[')
 assert e['cone_support_count']==2 and set(e['cone_unmatched'])=={'gold_only','gate_only'}
 g=[i.split(':',1)[1]for i in e['cone_state_keys']if i.startswith('gold_only:')];t=[i.split(':',1)[1]for i in e['cone_state_keys']if i.startswith('gate_only:')];assert len(g)==len(t)==1
 assert any('.g_bank['+str(n)+'].u_store.u_native.dout[' in g[0] for n in (0,1))
 h.append(['gate',t[0],['eq','gold',g[0],0]]);rows.append(dict(compare_point=e['point'],gold_register=g[0],gate_register=t[0]))
assert len(h)==122 and len({i[1]for i in h})==122 and len({i[2][2]for i in h})==122
(out/'untrusted_sram_dout_hints.json').write_text(json.dumps(h,indent=2)+'\n')
r=dict(verdict='UNPROVEN_PRESERVED',counts=d['counts'],seconds=d['t_total_s'],failure_classes={'q_pin_122':'Eachnextstatecone depends only on oneunmatchedgoldSRAMdout andoneanonymousgateFF; proposing122untrustedbijectionhints, NOT claimingfunctional equivalence','epoch_abort':'solverundecided,901support,3goldXsources','p_tx_v_and_rx_v':'solverundecided,898support,nomissingstatekeys'},hint_count=122,hints_validated=False,next_gate='Everyhintmustpass existingLECinduction; --reuse originalAIGs inNEWout avoidsregeneration. NoXwaiver/resetchange allowed.3controlconesremainproofgate.',pairs=rows)
(out/'diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items()if k!='pairs'})
