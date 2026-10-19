#!/usr/bin/env python3
"""Mutate read-only audit inputs; proves candidate guards, never strict admission."""
import argparse,copy,hashlib,importlib.util,json,re,subprocess,tempfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--die-v',required=True);ap.add_argument('--contract',required=True);ap.add_argument('--bind-report',required=True);ap.add_argument('--source-root',required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--audit',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
script=Path(__file__).with_name('audit_unread_current_1019.py');sp=importlib.util.spec_from_file_location('audit',script);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
base=Path(a.die_v).read_text();c=json.loads(Path(a.contract).read_text());b=json.loads(Path(a.bind_report).read_text());audit=json.loads(Path(a.audit).read_text());entries=audit['entries'];records=[]
with tempfile.TemporaryDirectory(prefix='hbm-unread-negative-') as td:
 td=Path(td)
 def graph(text):
  p=td/'die.v';p.write_text(text);return mod.parse_die(p,c)
 inst,widths,outputs,reads,consumers,unread=graph(base)
 def change(text,n,p,new):
  pat=re.compile(r'(^  \w+(?: #\(.*\))? '+re.escape(n)+r' \(\n)(.*?)(^  \);)',re.M|re.S);m=pat.search(text);assert m,n
  block=m[2];patp=re.compile(r'(\.'+re.escape(p)+r'\()(.*)(\),?\n)');block,k=patp.subn(lambda m:m[1]+new+m[3],block);assert k==1,(n,p)
  return text[:m.start(2)]+block+text[m.end(2):]
 def remove_consumers(text,net):
  for v in consumers[net]:
   n,p=v['instance'],v['port'];expr=inst[n]['connections'][p]
   def zero(m):
    hi,lo=m[1],m[2];w=widths[net] if hi is None else 1 if lo is None else int(hi)-int(lo)+1
    return str(w)+"'d0"
   new=re.sub(re.escape(net)+r'(?:\[(\d+)(?::(\d+))?\])?',zero,expr)
   text=change(text,n,p,new)
  return text
 def run(name,text,kind='refuse',update=True,edit_report=None,target=None):
  d=td/'die.v';d.write_text(text);r=copy.deepcopy(b)
  if update:
   *_,us=mod.parse_die(d,c);r['die_sha256']=hashlib.sha256(d.read_bytes()).hexdigest();r['unread_bit_ranges']={n:mod.ranges(z) for n,z in us.items()};r['summary']['unread_net_bits']=sum(map(len,us.values()))
  if edit_report:edit_report(r)
  rp=td/'bind.json';rp.write_text(json.dumps(r));out=td/name
  cmd=['python',str(script),'--die-v',str(d),'--contract',a.contract,'--bind-report',str(rp),'--source-root',a.source_root,'--source-commit',a.source_commit,'--out',str(out)]
  q=subprocess.run(cmd,capture_output=True,text=True)
  if kind=='refuse':assert q.returncode!=0,(name,q.stdout)
  else:
   assert q.returncode==0,(name,q.stderr)
   row=next(x for x in json.loads((out/'audit.json').read_text())['entries'] if (x['instance'],x['port'])==target)
   assert not row['allowlist_candidate'],(name,row)
  records.append(dict(name=name,verdict='PASS',expected=kind,exit_code=q.returncode,detail=q.stderr.strip().splitlines()[-1] if q.stderr else 'mutated relay padding became unresolved'))
 run('stale_die_hash',base+'\n// mutation\n',update=False)
 def drift(r):
  n=next(iter(r['unread_bit_ranges']));r['unread_bit_ranges'][n]=[]
 run('strict_range_drift',base,edit_report=drift)
 pad=next(x for x in entries if x['classification']=='propagated_zero_padding');hop=pad['evidence'][1]['first_bit_proof']['hops'][-1];expr=hop['input_expression']
 ones=re.sub(r"(\d+)'d0",lambda m:m[1]+"'d"+str((1<<int(m[1]))-1),expr);assert ones!=expr
 run('zero_padding_to_one',change(base,hop['instance'],'i',ones),kind='unresolved',target=(pad['instance'],pad['port']))
 live=next(iter(re.findall(r'(\w+)\[',expr)));payload=re.sub(r"(\d+)'d0",lambda m:'{'+m[1]+'{'+live+'[0]}}',expr)
 run('zero_padding_to_payload',change(base,hop['instance'],'i',payload),kind='unresolved',target=(pad['instance'],pad['port']))
 aq=next(x for x in entries if x['classification']=='unused_alternate_representation')
 for port in ('q','e'):run('remove_aq_'+port,remove_consumers(base,inst[aq['instance']]['connections'][port]))
 sel=next(x for x in entries if x['classification']=='selector_optional_readback')
 for port in ('selected_line','selected_v'):run('remove_selector_'+port,remove_consumers(base,inst[sel['instance']]['connections'][port]))
 svg=next(x for x in entries if x['classification']=='duplicate_checker_feed')
 for port in ('sm_packet','sm_command','fault'):run('remove_svg_'+port,remove_consumers(base,inst[svg['instance']]['connections'][port]))
r=dict(schema='opentallas.hbm_unread_candidate_negatives_1019.v1',verdict='PASS',cases=records,count=len(records),scope='Candidate classifier negative proof only. Mutant input reports regenerate ranges using independent lightweight parser, not full strict binder. No admission/manifest changed.',source_audit_sha256=hashlib.sha256(Path(a.audit).read_bytes()).hexdigest())
Path(a.output).write_text(json.dumps(r,indent=1)+'\n');print('UNREAD_CANDIDATE_NEGATIVES_PASS',len(records))
