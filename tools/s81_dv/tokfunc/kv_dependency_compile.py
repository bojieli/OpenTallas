#!/usr/bin/env python3
"""Complete only failed KV512 source dependencies; lint/elab, never simulate."""
import argparse,hashlib,json,re,subprocess,tarfile
from pathlib import Path
from configured_compile import spans

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['basis-archive','basis-receipt','manifest','dependency-tar','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False)
 m=json.loads(a.manifest.read_text());assert sha(a.manifest.read_bytes())=='34a21a361f81ee48901acd25ca4beee7458e8b5c62ed7baafe1fd459669ec145';assert m['source_ref']=='8a495768f02316a7a8ad2e2bafef2f4d3741b741'
 r=json.loads(a.basis_receipt.read_text());assert r['cases']['s0N_aggregate']['exit_code']==0 and r['cases']['ot_s81sl_slice_kv512']['exit_code']==1
 assert r['defines']==['DSFD_PQ_STATIC_X2','OT_COLL_NATIVE32','OT_COLL_NATIVE32_OFF','S81CTRL_SRAM_FIFO','S81CTRL_SRAM_P192','S81CTRL_NATIVE32']
 def unpack(path):
  d={}
  with tarfile.open(path) as t:
   for member in t.getmembers():
    if member.isdir():continue
    assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
    d[member.name]=t.extractfile(member).read()
  return d
 basis=unpack(a.basis_archive);assert {k:sha(v) for k,v in basis.items()}==r['staged_files_sha256']
 dep=unpack(a.dependency_tar);assert {k:sha(v) for k,v in dep.items()}==m['source_sha256'] and len(dep)==16
 pool={k[4:]:v for k,v in basis.items() if k.startswith('src/')};assert len(pool)==192 #191sources+unchanged0Ntop
 names={n for b in dep.values() for n,_,_ in spans(b.decode())};projections={}
 for rel,b in list(pool.items()):
  if rel in dep:continue
  text=b.decode();remove=[(n,lo,hi) for n,lo,hi in spans(text) if n in names]
  if remove:
   projections[rel]={'original_sha256':sha(b),'removed_bodies':{n:sha(text[lo:hi].encode()) for n,lo,hi in remove},'reason':'explicit selected16 production dependencies win, no selected body edit'}
   for n,lo,hi in reversed(remove):text=text[:lo]+''.join('\n' if c=='\n' else ' ' for c in text[lo:hi])+text[hi:]
   pool[rel]=text.encode()
 pool.update(dep)
 for rel,b in pool.items():
  dest=a.out/'src'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
 # Preserve original compilation-unit order and add only selected dependencies.
 oldroot=next(x for x in basis['compile.f'].decode().splitlines() if x.endswith('/src/top/s0N_aggregate.sv')).split('/src/top/')[0]
 units=[x[len(oldroot+'/src/'):] for x in basis['compile.f'].decode().splitlines() if x.startswith(oldroot+'/src/')]
 units=list(dict.fromkeys([*dep,*units]));assert 'top/s0N_aggregate.sv' in units
 includes=sorted({str((a.out/'src'/x).parent) for x in pool})
 lines=['+incdir+'+x for x in includes]+['+define+'+x for x in r['defines']]+[str(a.out/'src'/x) for x in units]
 (a.out/'compile.f').write_text('\n'.join(lines)+'\n')
 inventory={str(x.relative_to(a.out)):sha(x.read_bytes()) for x in a.out.rglob('*') if x.is_file()}
 receipt={'schema':'opentallas.s81.kv_dependency_compile.v1','status':'STAGED_KV_ONLY_COMPILE','selected_ref':m['source_ref'],'dependency_manifest_sha256':sha(a.manifest.read_bytes()),'dependency_tar_sha256':sha(a.dependency_tar.read_bytes()),'basis_receipt_sha256':sha(a.basis_receipt.read_bytes()),'basis_archive_sha256':sha(a.basis_archive.read_bytes()),'runner_sha256':sha(Path(__file__).read_bytes()),'basis_0N_result_preserved':r['cases']['s0N_aggregate'],'top':'ot_s81sl_slice_kv512','params':r['tops']['ot_s81sl_slice_kv512'],'defines':r['defines'],'dependency_source_sha256':m['source_sha256'],'projections':projections,'staged_files_sha256':inventory,'original_0N_rerun':False,'simulation_performed':False,'functional_qualified':False,'physical_qualified':False,'global_programme_qualified':False}
 def save():(a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
 save();print('STAGED_KV_ONLY',len(pool),'sourcefiles',flush=True)
 verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';argv=[str(verilator),'--lint-only','--timing','-Wno-fatal','-Wno-WIDTH','--top-module','ot_s81sl_slice_kv512','-Mdir',str(a.out/'kv_obj'),'-f',str(a.out/'compile.f')]
 receipt['argv']=argv;receipt['status']='KV_ONLY_ELABORATING';save()
 log=a.out/'kv_elab.log'
 with log.open('w') as f:result=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
 txt=log.read_text();receipt.update(status='KV_ONLY_SYNTAX_ELAB_EXIT0' if result.returncode==0 else 'KV_ONLY_COMPILE_ELAB_FAIL',exit_code=result.returncode,rawlog_sha256=sha(log.read_bytes()),warnings=[l for l in txt.splitlines() if l.startswith('%Warning')],errors=[l for l in txt.splitlines() if l.startswith('%Error')]);save();print(receipt['status'],flush=True);raise SystemExit(result.returncode)
if __name__=='__main__':main()
