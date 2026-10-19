import copy,json,sys
from pathlib import Path
from check_checkpoint_identity import check
from dft.liberty import read_liberty
from strict_contract import native_cells
p=Path(sys.argv[1]);out=Path(sys.argv[2]);load=lambda f:json.loads((p/f).read_text())
b=load('output/pre_native/raw.json');a=load('output/native/raw.json');bp=load('output/pre_native/positions.json');ap=load('output/native/positions.json');bc=next(iter(b['modules'].values()))['cells'];ac=next(iter(a['modules'].values()))['cells'];paths=sorted((p/'input/native_libs').glob('*_TT_*.lib*'));lib=read_liberty(paths);caps=native_cells(paths,used_masters={c['type'] for c in ac.values()});added=set(ac)-set(bc)
loadname=next(n for n in sorted(added) if ac[n]['type'].startswith('INV') and not ac[n]['connections']['Y']);master=ac[loadname]['type'];ip=next(q for q,d in ac[loadname]['port_directions'].items() if d=='input');op='Y';dataep=next((n,q,bs) for n,c in bc.items() for q,bs in c['connections'].items() if q=='D' and bs)
rows=[]
def run(name,change):
 aa=copy.deepcopy(a);ll=copy.deepcopy(lib);cc=copy.deepcopy(caps);pp=copy.deepcopy(ap);change(next(iter(aa['modules'].values())),ll,cc,pp)
 try:check(b,aa,bp,pp,ll,cc)
 except (ValueError,KeyError,TypeError) as e:rows.append(dict(control=name,verdict='REFUSED',reason=str(e)));return
 raise AssertionError('CONTROL ACCEPTED '+name)
run('connected_inverter_output',lambda m,l,c,p:m['cells'][loadname]['connections'].__setitem__(op,m['cells'][loadname]['connections'][ip]))
run('data_net_load',lambda m,l,c,p:m['cells'][loadname]['connections'].__setitem__(ip,dataep[2]))
run('enable_extra_native_pin',lambda m,l,c,p:l[master]['pins'].__setitem__('EN',dict(direction='input',function=None)))
run('latch_class',lambda m,l,c,p:l[master].__setitem__('latch',{'enable':'A'}))
run('unknown_master',lambda m,l,c,p:l.pop(master))
run('missing_native_pin',lambda m,l,c,p:m['cells'][loadname]['connections'].pop(ip))
run('invalid_cap_class',lambda m,l,c,p:c[master]['pins'][ip]['native_capacitance'].__setitem__('capacitance',0))
run('wrong_cap_unit',lambda m,l,c,p:c[master]['pins'][ip].__setitem__('capacitance_unit',['1','pf']))
run('nonidentity_function',lambda m,l,c,p:l[master]['pins'][op].__setitem__('function','0'))
run('original_data_rewire',lambda m,l,c,p:m['cells'][dataep[0]]['connections'].__setitem__(dataep[1],m['cells'][loadname]['connections'][ip]))
run('original_cell_move',lambda m,l,c,p:p['insts'][dataep[0]]['bbox'].__setitem__(0,p['insts'][dataep[0]]['bbox'][0]+1))
run('BTerm_geometry',lambda m,l,c,p:p['bterms'].pop(next(iter(p['bterms']))))
run('ordinary_net_metadata',lambda m,l,c,p:m['net_metadata'][str(dataep[2][0])].__setitem__('signal_type','CLOCK'))
out.write_text(json.dumps({'causal_controls':rows,'all_refused':True},indent=2)+'\n');print(json.dumps(rows,indent=2))
