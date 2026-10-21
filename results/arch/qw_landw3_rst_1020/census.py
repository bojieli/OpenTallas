# QW-LANDW3 pre-gate native census of the RSL=1 masters (mapped ORFS synth, transparent all-driver <=32 incl. reset,
# textbook hf/depth at 32).  Reuses the qw_landw_fan32_1020 synth/audit helpers unchanged.  Run from the source root.
import pathlib,subprocess,os,json,hashlib,re,concurrent.futures
r=pathlib.Path.cwd();a=r/'results/arch/qw_landw_fan32_1020/synth';o=r/'results/arch/qw_landw3_rst_1020/census';o.mkdir(parents=True,exist_ok=True)
subprocess.run(['python3',str(a/'prepare.py')],check=True)
K=[('qfwd_landh0d8g_107_ew_52x52','qfd_landh0d8g_107_EW_52x52'),('qfwd_landh0d8gn_107_ew_52x52','qfd_landh0d8gn_107_EW_52x52'),
   ('qfwd_landh0d8g_116_ew_52x52','qfd_landh0d8g_116_EW_52x52'),('qfwd_landh0d8gn_116_ew_52x52','qfd_landh0d8gn_116_EW_52x52')]
env=dict(os.environ,SRC=str(r),SYNTH_TIMEOUT='unlimited',OT_ORFS_CORNER_OVERRIDE='TC')
def one(kt):
 kit,top=kt;lab=kit
 p=subprocess.run(['bash',str(a/'ref_synth.sh'),str(r/'physical/ref_tile'/kit/'kit.env'),lab,str(r/'native_synth_out'),'floorplan'],env=env)
 paths=list((r/'native_synth_out'/lab).glob('**/1_2_yosys.raw.v'))
 if len(paths)!=1:return dict(kit=kit,top=top,synth_rc=p.returncode,error='no mapped netlist')
 d=paths[0].parent
 for fn in ['flatten.py','audit.py','constant_roles.py']:(d/fn).write_text((a/fn).read_text())
 for fn in ['constant_roles.py','flatten.py']:
  with(d/(fn+'.log')).open('w')as f:subprocess.run(['docker','run','--rm','--network','none','-v',str(d)+':/out','-e','OT_NATIVE_TOP='+top,'openroad/orfs:asap7lock','python3','/out/'+fn],stdout=f,stderr=subprocess.STDOUT,check=True)
 q=subprocess.run(['python3','audit.py'],cwd=d,env=dict(os.environ,OT_NATIVE_TOP=top),text=True,capture_output=True)
 j=json.loads((d/'native32.json').read_text())
 t=subprocess.run(['python3','tools/textbook_lint.py','check','--netlist',str(paths[0]),'--out',str(d/'textbook_depth.json'),'--set','hf_report=32','hf_max=32','hf_port_refuse=32','hf_reset_refuse=32','hf_refuse=32'],text=True,capture_output=True)
 (d/'textbook_depth.log').write_text(t.stdout+t.stderr)
 rows=json.loads((d/'all_roots.json').read_text())
 rst=[x for x in rows if x['root'].startswith('input:rs[')]+[x for x in rows if re.search(r'rs0c?\b|rs0c?\$|rs1',x['root'])][:24]
 od=o/kit;od.mkdir(exist_ok=True)
 for fn in ['native32.json','lib_roles.json','textbook_depth.json','textbook_depth.log']:
  if (d/fn).exists():(od/fn).write_text((d/fn).read_text())
 res=dict(kit=kit,top=top,synth_rc=p.returncode,audit_rc=q.returncode,over32=j['over32_non_tie'],maximum=j['max_non_tie'],ff=j['ff'],cells=j['cells'],
  textbook_rc=t.returncode,textbook_tail=t.stdout[-600:],reset_roots=rst,mapped_sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest())
 (od/'reset_roots.json').write_text(json.dumps(rst,indent=1)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='reset_roots'}),flush=True);return res
with concurrent.futures.ThreadPoolExecutor(4) as ex:R=list(ex.map(one,K))
(o/'summary.json').write_text(json.dumps(R,indent=1)+'\n')
ok=all(x.get('over32')==0 and x.get('synth_rc')==0 for x in R);print('LANDW3_CENSUS',('PASS' if ok else 'FAIL'));raise SystemExit(0 if ok else 1)
