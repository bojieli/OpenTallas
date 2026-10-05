#!/usr/bin/env python3
"""Additive deterministic verification; original native VM tool/evidence unchanged."""
import argparse,hashlib,importlib.machinery,json,subprocess,sys,types
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'results/uarch/dsrom_field_native_VM_join_20261003'
OUT=ROOT/'results/uarch/dsrom_field_native_VM_join_verify_r2_20261003'

def generated_cache(path):
 p=PurePosixPath(path)
 return '__pycache__' in p.parts or p.suffix=='.pyc'

def census(entries):
 return {p:h for p,h in entries.items() if not generated_cache(p)}

def check(entries,root=ROOT):
 for p,h in entries.items():
  if generated_cache(p):raise ValueError('generated cache in successor census '+p)
  if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('changed source/artifact '+p)

def source_replay():
 # A fresh process and get_code override prohibit both reading and writing
 # cache, including spec_from_file_location nested provider imports.
 def source_code(loader,name):
  path=loader.get_filename(name)
  return compile(loader.get_data(path),path,'exec',dont_inherit=True)
 importlib.machinery.SourceFileLoader.get_code=source_code
 sys.dont_write_bytecode=True
 path=ROOT/'tools/dsrom_field_native_VM_join.py'
 module=types.ModuleType('frozen_original_native_VM');module.__file__=str(path)
 exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),module.__dict__)
 actual=json.dumps(module.generate(),sort_keys=True,indent=2)+'\n'
 if actual!=(OLD/'model.json').read_text():raise ValueError('native VM model regeneration differs')

def verify():
 # Authenticate the immutable failed records as history, then require each
 # successor census to equal their exact cache-only projection.
 check(json.loads((OUT/'verification_pins.json').read_text()))
 check(json.loads((OUT/'evidence_manifest.json').read_text()))
 for name in ('source_pins.json','manifest.json'):
  original=json.loads((OLD/name).read_text());successor=json.loads((OUT/name).read_text())
  if successor!=census(original):raise ValueError('non-cache census changed '+name)
  check(successor)
 # No existing in-memory project imports or cached modules enter replay.
 subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--source-replay'],check=True)
 print('PASS deterministic source/artifact census and byte-identical original model; NO HARDWARE ADMISSION')

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--verify',action='store_true');g.add_argument('--source-replay',action='store_true',help=argparse.SUPPRESS)
 a=p.parse_args();source_replay() if a.source_replay else verify()
