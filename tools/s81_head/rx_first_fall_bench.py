from pathlib import Path
import subprocess,json,argparse,hashlib
a=argparse.ArgumentParser(description='544bit four-bank HEAD RX edge/phase proof and mechanism mutants');a.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);a.add_argument('--out',type=Path,required=True);a=a.parse_args();w=a.root.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
phases=[-90,-1,0,1,83.3,166.6];modes={'positive':None,'mut_rise':'OT_HEAD_RXCAP_MUT_RISE','mut_tail':'OT_HEAD_RXCAP_MUT_TAIL_FALL','mut_bit':'OT_HEAD_RXCAP_MUT_TOPBIT'};results=[]
for mode,define in modes.items():
 for phase in phases:
  name=f'{mode}_{phase}'.replace('-','m').replace('.','p');b=o/(name+'.vvp');log=o/(name+'.log')
  args=['iverilog','-g2012','-s','tb',f'-Ptb.PHASE_PS={phase}','-o',str(b),str(w/'rtl/dsrom_sys/s81_head/test/tb_s81hd_rx_first_fall.sv'),str(w/'rtl/dsrom_sys/s81_head/ot_s81hd_pma_rx_capture.sv'),str(w/'rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv')]
  if define:args.insert(1,'-D'+define)
  c=subprocess.run(args,capture_output=True,text=True);(o/(name+'.compile.log')).write_text(c.stdout+c.stderr)
  if c.returncode:raise RuntimeError('compile '+name+': '+c.stderr[-1500:])
  p=subprocess.run(['vvp',str(b)],capture_output=True,text=True);log.write_text(p.stdout+p.stderr)
  rows=[x for x in p.stdout.splitlines() if x.startswith('RXCAP_RESULT')]
  if len(rows)!=1:raise RuntimeError(name+' missing actual result')
  passed=p.returncode==0 and 'errors=0 ' in rows[0]
  if passed!=(mode=='positive'):raise RuntimeError(name+' unexpected verdict: '+rows[0])
  if mode!='positive' and (p.returncode!=1 or 'RXCAP_FAIL' not in p.stdout):raise RuntimeError(name+' mutant did not fail its actual assertion')
  results.append(dict(mode=mode,phase_ps=phase,rc=p.returncode,result=rows[0]));print(name,rows[0],flush=True)
(o/'result.json').write_text(json.dumps(dict(scope='544bit4bank exact capture cut; source-labelled phase/reset proof; no fullPHY or physical timing claim',positive_cases=6,mutant_cases=18,results=results),indent=1)+'\n')
