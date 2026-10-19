#!/usr/bin/env python3
"""Fail closed for exact explicit-boundary native characterization inputs."""
import argparse,hashlib,json,re
from pathlib import Path

def verify(config,receipt,source):
 r=json.loads(receipt.read_text());s=config.read_text()
 assert r.get('physical_wrapper') is True and r.get('useful_cones') is True
 assert r['core_top']==r['public_top']+'__safe_core'
 assert hashlib.sha256(source.read_bytes()).hexdigest()==r['emitted_sha256'],'changed explicit-boundary source'
 def field(key):
  vals=re.findall(r'^(?:override\s+)?export\s+'+re.escape(key)+r'\s*[:?]?=\s*(.*?)\s*$',s,re.M)
  assert len(vals)==1,'ambiguous/missing config field '+key
  return vals[0]
 assert field('OT_PIN_REGS')=='0','double input/output wrapping refused'
 assert field('OT_RST_LAND')=='0','double reset landing refused'
 assert field('DESIGN_NAME')==r['public_top'],'wrong wrapper top'
 assert source.name in field('VERILOG_FILES'),'explicit source absent from config'
 assert r['manifest']['production_origin_bound'] is False,'not a production adoption API'
 return {'status':'PASS','source_sha256':r['emitted_sha256'],'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'contract':'exact source input1/output1/reset2; automatic wrapping OFF; no production adoption'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True,type=Path);ap.add_argument('--receipt',required=True,type=Path);ap.add_argument('--source',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 out=verify(a.config,a.receipt,a.source);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
