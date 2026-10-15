#!/usr/bin/env python3
"""Exact continuous full-width epoch proof; no physical timing claim."""
import hashlib,json,pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
files=[root/p for p in ['rtl/dsrom_sys/s81_static_net/test/tb_r2l_epoch64.sv','rtl/dsrom_sys/s81_static_net/ot_s81_r2l_epoch64.sv','rtl/dsrom_sys/s81_static_net/ot_s81_r2l_groups64.sv','rtl/dsrom_sys/s81_static_net/ot_s81_static_ratio_cross.sv','rtl/dsrom_sys/s81_static_net/gen/dsfd_r2l_vr_512x1__hcol.sv']]
rows=[]
cases=[('phase_%d_%d'%(w,r),dict(WPH=w,RPH=r),True) for w in range(3) for r in range(4)]
cases += [('first_last_one',dict(NFRAME=1),True),('first_last_two',dict(NFRAME=2),True),('wrong_payload_group7',dict(MUT=1),False),('wrong_epoch_group7',dict(MUT=2),False),('lost_epoch_group7',dict(STOP=1),False)]
with tempfile.TemporaryDirectory(prefix='s81-r2l-epoch-') as td:
 for label,params,expected in cases:
  out=pathlib.Path(td)/'sim'
  subprocess.run(['iverilog','-g2012','-s','tb_r2l_epoch64']+['-Ptb_r2l_epoch64.'+k+'='+str(v) for k,v in params.items()]+['-o',str(out)]+list(map(str,files)),check=True,cwd=root)
  p=subprocess.run(['vvp',str(out)],capture_output=True,text=True,cwd=root)
  ok=(p.returncode==0)==expected
  rows.append(dict(case=label,parameters=params,expected_pass=expected,returncode=p.returncode,accepted=ok,stdout=p.stdout,stderr=p.stderr))
  print(label,'PASS' if ok else 'FAIL',p.stdout.splitlines()[0] if p.stdout else '')
receipt=dict(scope='functional RTL only; exact PLL tick ratios; independent production clock entries idealized by testbench sources',files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},cases=rows,passed=all(x['accepted'] for x in rows))
p=root/'results/arch/s81_r2l_groups_1417/epoch_functional.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(0 if receipt['passed'] else 1)
