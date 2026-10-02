#!/usr/bin/env python3
"""Conservative visibility-owned source credits; no new publication seats inferred."""
from fractions import Fraction
import dsrom_capture_physical_shard_paths as P
FIELDS=[('stage',6),('rank',2),('expert',9),('phase',10),('key_word',32),('generation',32),('user',32),('xversion',32),('pc',14)]
def identity(ctx):
 if set(ctx)!=set(n for n,w in FIELDS):raise ValueError('full169 context required')
 for n,w in FIELDS:
  if type(ctx[n]) is not int or not 0<=ctx[n]<1<<w:raise ValueError('identity width')
 return tuple(ctx[n] for n,w in FIELDS)
class PublicationDebt:
 def __init__(self,ctx,capacity,credit_return_edges):
  if type(capacity) is not int or not 1<=capacity<=576:raise ValueError('explicit finite capacity')
  self.ctx=identity(ctx);self.capacity=capacity;self.delay=Fraction(credit_return_edges)
  if self.delay<=0:raise ValueError('positive returned credit/CDC required')
  self.debts={};self.next_issue=0;self.next_visible=0;self.last_issue=None;self.free_credit_after=[None]*capacity
 def issue(self,row,ctx,shard,edge,sink_reserved):
  edge=Fraction(edge)
  if identity(ctx)!=self.ctx or row!=self.next_issue or shard!=P.owner(row)['physical_shard'] or not sink_reserved:raise ValueError('source owner/order/seat')
  if self.last_issue is not None and edge<=self.last_issue:raise ValueError('II1 distinct accepted source edges')
  available=next((i for i,t in enumerate(self.free_credit_after) if t is None or edge>t),None)
  if available is None:return False
  self.free_credit_after.pop(available)
  self.debts[row]={'issue':edge,'reply':None,'visible':None};self.next_issue+=1;self.last_issue=edge;return True
 def reply(self,row,ctx,shard,edge):
  if identity(ctx)!=self.ctx or row not in self.debts or shard!=P.owner(row)['physical_shard']:raise ValueError('reply identity')
  d=self.debts[row];edge=Fraction(edge)
  if d['reply'] is not None or edge<=d['issue']:raise ValueError('duplicate/early reply')
  d['reply']=edge
 def visible(self,row,ctx,edge,exclusive_VM_lease):
  if identity(ctx)!=self.ctx or row not in self.debts or row!=self.next_visible or not exclusive_VM_lease:raise ValueError('causal ordered VM visibility')
  d=self.debts[row];edge=Fraction(edge)
  if d['reply'] is None or edge<=d['reply'] or d['visible'] is not None:raise ValueError('visibility must follow accepted reply and bridge')
  d['visible']=edge;self.next_visible+=1
 def return_credit(self,row,ctx,shard,edge):
  if identity(ctx)!=self.ctx or row not in self.debts or shard!=P.owner(row)['physical_shard']:raise ValueError('credit identity')
  d=self.debts[row];edge=Fraction(edge)
  if d['visible'] is None or edge<d['visible']+self.delay:raise ValueError('retain source debt through visibility and positive captured feedback')
  del self.debts[row];self.free_credit_after.append(edge)
