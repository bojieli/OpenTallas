"""Explicit clock/reset pass-through interfaces; never registered data buses.

No implicit clk/rst tie is generated. Every per-instance pin must name an actual
infrastructure net and its real provider instance. Unused outputs require an
explicit inventory entry. Physical source/link validation remains in port-bind.
"""
import re,math
IDENT=re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
def type_ports(t):
 out=t.get('infra_ports',[]); seen=set()
 blocked={'clk','arst_n','rst_n','start_i'}|{b['name'] for b in t.get('buses',[])}|{p['name']+s for p in t.get('ft_slots',[]) for s in ('_i','_o')}
 for p in out:
  n=p.get('name','')
  if not IDENT.fullmatch(n) or n in seen or n in blocked: raise ValueError('invalid/duplicate infra port '+n)
  seen.add(n)
  if p.get('dir') not in ('in','out') or p.get('kind') not in ('clock','reset'): raise ValueError('infra interface must be clock/reset, explicit input/output: '+n)
  if not isinstance(p.get('leaf'),str) or '.' not in p['leaf']: raise ValueError('infra port lacks leaf: '+n)
  if len(p.get('xy_um',[]))!=2 or p.get('layer')!='M7': raise ValueError('infra port needs explicit M7 via-field position: '+n)
  w,h=t['outline_um'];x,y=p['xy_um']
  if not all(math.isfinite(v) for v in (x,y)) or not(0<=x<=w and 0<=y<=h):raise ValueError('infra pin outside type outline: '+n)
  if any(abs((v-.032)/.064-round((v-.032)/.064))>1e-5 for v in (x,y)):raise ValueError('infra pin not on symmetric M7 track: '+n)
 return out

def die_lines(P, provider_ports=None):
 expected={(pn,v['name']):v for pn,p in P.parts.items() for v in type_ports(P.types[p['type']])}
 if not expected:return [],[],{}
 I=P.raw.get('infrastructure') or {}; nets={}
 for n in I.get('nets',[]):
  if not IDENT.fullmatch(n.get('name','')) or n['name'] in nets or n.get('kind') not in ('clock','reset','clock_mesh'): raise ValueError('invalid infrastructure net')
  nets[n['name']]=dict(n,drivers=0,loads=0)
 if not nets:raise ValueError('active infrastructure ports require actual die infrastructure nets; implicit clk/rst ties forbidden')
 wires=['    wire infra_'+n+';' for n in nets]; instances=[]
 for c in I.get('instances',[]):
  if not IDENT.fullmatch(c.get('module','')) or not IDENT.fullmatch(c.get('inst','')):raise ValueError('invalid infrastructure provider instance')
  con=[]
  if provider_ports is not None:
   hp=provider_ports(c['module'])
   if hp is None or set(hp)!=set(c['bind']):raise ValueError('infrastructure provider source ports disagree: '+c['inst'])
   for pn, (dr,w) in hp.items():
    if c['bind'][pn]['dir']!={'input':'in','output':'out'}.get(dr) or w not in ('','[0:0]'):raise ValueError('infrastructure provider direction/width disagrees: '+c['inst']+'.'+pn)
  for p,b in sorted(c['bind'].items()):
   ref=b['signal']; dr=b['dir']
   if ref in ('root:clk','root:rst_n'):
    if dr!='in':raise ValueError('infrastructure provider drives die root')
    val=ref.split(':')[1]
   else:
    if ref not in nets or dr not in ('in','out'):raise ValueError('invalid provider pin binding '+p)
    nets[ref]['loads' if dr=='in' else 'drivers']+=1;val='infra_'+ref
   con.append('.'+p+'('+val+')')
  instances.append('    '+c['module']+' '+c['inst']+' ('+', '.join(con)+');')
 conn={};seen=set()
 for b in I.get('bindings',[]):
  key=(b.get('part'),b.get('port')); n=b.get('net')
  if key not in expected or key in seen or n not in nets:raise ValueError('unknown/duplicate infrastructure pin binding '+str(key))
  seen.add(key); v=expected[key]
  if nets[n]['kind'] not in (v['kind'],'clock_mesh' if v['kind']=='clock' else 'reset'):raise ValueError('infrastructure net kind disagrees with pin '+str(key))
  nets[n]['loads' if v['dir']=='in' else 'drivers']+=1
  conn.setdefault(key[0],[]).append((key[1],'infra_'+n))
 if seen!=set(expected):raise ValueError('unbound infrastructure pins: '+str(sorted(set(expected)-seen)[:8]))
 # An active core FT mesh output may feed its real planned clock-entry pin.
 # These are explicit physical clock nets, not implicit ties to the die root.
 if I.get('clock_tap_bindings'):
  import schema as S
  bytype={tn:{n for n,_,_ in S.tap_grid(P,tn)}|{n for n,_,_,_ in S.core_taps(P,tn)} for tn in {p['type'] for p in P.parts.values()}}
  tap_seen=set()
  for b in I['clock_tap_bindings']:
   key=(b['part'],b['port']);n=b['net']
   if key[0] not in P.parts or key[1] not in bytype[P.parts[key[0]]['type']] or key in tap_seen or n not in nets or nets[n]['kind'] not in ('clock','clock_mesh'):raise ValueError('invalid native clock-entry infrastructure binding '+str(key))
   tap_seen.add(key);nets[n]['loads']+=1;conn.setdefault(key[0],[]).append((key[1],'infra_'+n))
 for n,d in nets.items():
  if not d['drivers'] or (d['drivers']!=1 and d['kind']!='clock_mesh'):raise ValueError('infrastructure net drivers invalid: '+n)
  if not d['loads'] and not (d.get('unused') and d.get('owner_inventory')):raise ValueError('unconsumed active infrastructure net: '+n)
 return wires,instances,conn


def provider_ports(text, module, ansi_parser):
 """Actual clock exporters use non-ANSI root/tap headers; validate their declarations too."""
 have = ansi_parser(text, module)
 if have:
  return have
 clean = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
 m = re.search(r"\bmodule\s+"+re.escape(module)+r"\s*\((.*?)\)\s*;(.*?)\bendmodule\b", clean, re.S)
 if not m:
  return have
 names = [n.strip() for n in m[1].split(',')]
 if any(not IDENT.fullmatch(n) for n in names) or len(set(names)) != len(names):
  raise ValueError('invalid non-ANSI provider header '+module)
 out = {}
 for q in re.finditer(r"\b(input|output|inout)\s+(?:wire\s+)?(\[[^\]]+\])?\s*([^;]+);",m[2]):
  for name in q[3].split(','):
   name=name.strip()
   if name not in names or name in out:raise ValueError('provider direction declaration disagrees with header '+module)
   out[name]=(q[1],q[2] or '')
 if set(out)!=set(names):raise ValueError('provider port direction missing '+module)
 return out
