"""Bind exact parent elaboration aliases to native external or internal bit identities."""
import collections


def bind(mapping, native_parent, native_ports):
 if mapping.get('verdict')!='PASS':raise ValueError('parent alias map is not complete')
 public=collections.defaultdict(set);invalid=set()
 for port,labels in mapping['parent_public_ports'].items():
  vector=native_ports.get(port)
  if vector is None or len(vector)!=len(labels):
   invalid.update(x for x in labels if isinstance(x,int));continue
  for label,value in zip(labels,vector):
   if isinstance(label,int):public[label].add(value)
 domain=native_parent+'::alias::'+mapping['gold_source_sha256']
 ports={};failures={}
 for port,labels in mapping['parent_alias_bits'].items():
  vector=[]
  for label in labels:
   if isinstance(label,str):vector.append(None);continue
   choices=public.get(label,set())
   if len(choices)>1:
    failures[port]='parent public aliases resolve to conflicting native identities';break
   if choices:vector.append(next(iter(choices)))
   elif label in invalid:
    failures[port]='parent public alias has missing or mismatched native interface';break
   else:vector.append((domain,label))
  else:ports[port]=vector
 return ports,failures
