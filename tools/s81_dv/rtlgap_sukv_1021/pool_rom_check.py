#!/usr/bin/env python3
"""Fail closed unless all eight selected exp case tables are immutable and initialized."""
import json,sys
j=json.load(open(sys.argv[1]));rows=[]
for m,v in j['modules'].items():
 for n,c in v.get('cells',{}).items():
  if c['type']=='$mem_v2' and 'u_exp' in n and 'proc_rom' in n:
   p=c['parameters']
   assert int(p['WR_PORTS'],2)==0 and int(p['WIDTH'],2) in (61,64) and int(p['SIZE'],2)==256,(m,n)
   assert len(p['INIT'])==int(p['WIDTH'],2)*256 and set(p['INIT'])<=set('01'),(m,n,'unknown init')
   rows.append(m+'/'+n)
assert len(rows)==8,rows
print('POOL_ROM_PASS immutable fully initialized SFU tables8; mutable memories retained')
