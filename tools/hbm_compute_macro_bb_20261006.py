#!/usr/bin/env python3
"""Emit a physical-only symbol from matching real retained LEF and SS/FF views.
The symbol is backed by the actual macro timing libraries, not simulation RTL.
"""
import argparse,hashlib,json,re
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('macro_dir',type=Path);a=ap.parse_args();root=a.macro_dir
 manifest=root/'manifest.json';d=json.loads(manifest.read_text());name=d['macro']
 if not d['status'].startswith('REAL_'):raise ValueError('real retained views required')
 for f,h in d['files'].items():
  if hashlib.sha256((root/f).read_bytes()).hexdigest()!=h:raise ValueError('actual view hash mismatch: '+f)
 pins=set(re.findall(r'^  PIN (\S+)',(root/(name+'.lef')).read_text(),re.M))
 for cc in ['ss','ff']:
  lp=set(re.findall(r'\bpin\s*\(\s*"([^"]+)"\s*\)',(root/(name+'_'+cc+'.lib')).read_text()))
  if pins!=lp:raise ValueError('LEF/LIB pin mismatch: '+cc)
 declared=set();ports=[]
 def ident(v):return v if re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_$]*',v) else '\\'+v+' '
 for port,p in sorted(d['ports'].items()):
  declared.update(p['pins']);indices=[]
  for pin in p['pins']:
   m=re.fullmatch(re.escape(port)+r'\[(\d+)\]',pin)
   if m:indices.append(int(m.group(1)))
   elif pin!=port:raise ValueError('unrepresentable pin: '+pin)
  if indices:
   if len(indices)!=len(p['pins']) or set(indices)!=set(range(min(indices),max(indices)+1)):
    raise ValueError('sparse/mixed macro port: '+port)
   width=f'[{max(indices)}:{min(indices)}] '
  else:width=''
  ports.append(' '+p['direction'].lower()+' wire '+width+ident(port))
 if declared!=pins:raise ValueError('manifest does not cover actual macro pins')
 out=root/(name+'_bb.sv')
 if out.exists():raise ValueError('existing physical symbol preserved; do not overwrite')
 text='''// Physical macro symbol only. Link the accompanying actual retained LEF
// and SS/FF timing libraries. Use real engine RTL for functional simulation.
// Fixed hardened ABI; no shape parameters or guessed pins/clock/protection.
(* blackbox, keep_hierarchy *) module '''+ident(name)+' (\n'+',\n'.join(ports)+'\n);\nendmodule\n'
 out.write_text(text);d['files'][out.name]=hashlib.sha256(out.read_bytes()).hexdigest()
 d['physical_symbol']=dict(file=out.name,pins=len(pins),ports=len(ports),functional_simulation=False,backing='actual matching retained LEF and SS/FF LIBs; no new qualification')
 manifest.write_text(json.dumps(d,indent=2)+'\n');print(name,len(pins),'pins',len(ports),'ports')
if __name__=='__main__':main()
