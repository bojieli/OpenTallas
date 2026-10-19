"""Conservative finite abstraction of exact writer control, not memory qualification."""
import itertools,json,collections
initial={(0,0,0,0,0,t) for t in (0,1)}
seen=set(initial);todo=collections.deque(initial);edges=0
while todo:
 configured,fault,active,wq,ld,taint=s=todo.popleft()
 assert not(configured and wq),s
 assert not(ld and taint),s
 for reset,kind,start,stage_ok,done,bad_data in itertools.product((0,1),range(4),(0,1),(0,1),(0,1),(0,1)):
  # kind: 0 no cfg, 1 in-order table write, 2 in-order seal, 3 rejected cfg.
  we=kind!=0;accept=we and not active and not configured and not fault and kind!=3
  legal=start and configured and not active and not fault and not we and stage_ok
  cf=configured or (accept and kind==2)
  fl=fault or (we and (not accept or bad_data)) or (start and not legal)
  ac=1 if legal else (0 if done else active)
  nq=accept and kind==1;nl=legal
  nt=(1 if wq else 0) if start else taint
  if reset:cf=fl=ac=nq=nl=0 # macro Q remains arbitrary across reset
  ns=tuple(map(int,(cf,fl,ac,nq,nl,nt)));edges+=1
  if ns not in seen:seen.add(ns);todo.append(ns)
print(json.dumps(dict(verdict='PASS',reachable_abstract_states=len(seen),edges=edges,invariants=['configured implies no pending table write','ld implies preceding macro read was collision-free'],abstraction='Arbitrary early seal and arbitrary table validity; arbitrary completion and initial macro read data. More permissive than exact next_cfg and table checks. Reset clears control, never initializes macro Q.',scope='Control noninterference for arbitrary collided read Q only. Assumes writes themselves remain correct and one-edge read NBA semantics; physical dualclock contract remains OPEN.'),indent=2))
