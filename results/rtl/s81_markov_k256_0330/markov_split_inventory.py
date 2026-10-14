from pathlib import Path
import subprocess,json,hashlib
r=Path('/var/tmp/s81rom2250/src');out=r/'results/rtl/s81_markov_k256_0330/inventory_split';out.mkdir(parents=True,exist_ok=True)
files=[r/x for x in ['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/experimental/dsrom_markov_20261008/ot_s81_markov_k256_native.sv']]
for top in ['ot_s81_markov_ctl_native','ot_s81_markov_mul_native']+[f'ot_s81_markov_chunk{k}_native'for k in range(8)]+['ot_s81_markov_pair_native','ot_s81_markov_fold_native','ot_s81_markov_join_native']:
 ys='read_verilog -sv -DSYNTHESIS '+' '.join(map(str,files))+'\n'
 if top=='ot_dsrom_markov_row':ys+='chparam -set K 256 -set PINREG 1 -set RINGDLY 0 -set CUT 511 -set SPLIT9 1 ot_dsrom_markov_row\n'
 if top=='ot_v41_fadd':ys+='chparam -set CUT 511 -set SPLIT9 1 ot_v41_fadd\n'
 ys+=f'synth -top {top} -flatten -noabc\nrename -top {top}\nstat\nwrite_json {out/top}.json\n';p=out/f'{top}.ys';p.write_text(ys)
 with (out/f'{top}.log').open('w')as f:rc=subprocess.run(['yosys','-s',str(p)],stdout=f,stderr=subprocess.STDOUT).returncode
 print(top,rc,flush=True)
 if rc:print((out/f'{top}.log').read_text()[-1800:],flush=True);continue
 j=json.load(open(out/f'{top}.json'))['modules'][top];types={};sinks=0
 for c in j['cells'].values():
  t=c['type'];types[t]=types.get(t,0)+1
  if 'DFF'in t.upper():sinks+=len(c['connections'].get('Q',[]))
 rec={'top':top,'stage':'generic synthesis; native physical clock/slot/ETM/throughput still owed','flop_bits':sinks,'cells_by_type':types,'ports':{p:{'direction':v['direction'],'bits':len(v['bits'])}for p,v in j['ports'].items()},'source_sha256':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}}
 (out/f'{top}_receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('sinks',sinks,'cells',len(j['cells']),flush=True)
