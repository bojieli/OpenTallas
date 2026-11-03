import sys,json,collections
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
D=g.Design('/srv/opentallas-scratch/claude/codex-sc49-actual-review-0441/sc_batch_buffer_geometry.tsv')
ids={c[6]:i for i,c in D.cells.items()}
rows=[]
for bit,name in [(44,'u.u_15645/Q$_DFF_P_'),(46,'u.u_15647/Q$_DFF_P_')]:
 cid=ids[name];src=g.ctr(D.cells[cid]);front=list(D.drives[cid]);seen=set(front);caps=set();ports=[];comb=set()
 while front:
  n=front.pop()
  for s in D.nets[n][2]:
   if s[0]=='p':ports.append(D.pin_by_k[s[1]]['name']);continue
   if s[2]:continue
   cc=D.cells[s[1]]
   if cc[0]=='S':caps.add(s[1]);continue
   if cc[0] in 'BLK':
    comb.add(s[1])
    for nn in D.drives.get(s[1],[]):
     if nn not in seen:seen.add(nn);front.append(nn)
 pin=next(p for p in D.pins if p['name']==f'dn_i[{bit}]')
 # exact backwards input trace of the launch FF until first sequential endpoint
 prior_ports=set();prior_regs=set();todo=[cid];seenb=set(todo)
 while todo:
  v=todo.pop()
  for ni,clk in D.cell_in.get(v,[]):
   if clk:continue
   r=D.nets[ni][1]
   if not r:continue
   if r[0]=='p':prior_ports.add(D.pin_by_k[r[1]]['name']);continue
   k=r[1]
   if D.cells[k][0]=='S':prior_regs.add(D.cells[k][6]);continue
   if D.cells[k][0]=='B' and k not in seenb:seenb.add(k);todo.append(k)
 captures=sorted([{'name':D.cells[k][6],'master':D.cells[k][1],'centre':list(g.ctr(D.cells[k])),'launch_capture_L1':sum(abs(a-b)for a,b in zip(src,g.ctr(D.cells[k])))}for k in caps],key=lambda x:x['launch_capture_L1'],reverse=True)
 rows.append({'public_pin':pin,'launch_name':name,'launch_kind':D.cells[cid][0],'launch_master':D.cells[cid][1],'launch_centre':src,'input_to_launch_L1':abs(pin['x']-src[0])+abs(pin['y']-src[1]),'pure_buffer_upstream_ports':sorted(prior_ports),'pure_buffer_upstream_other_registers':sorted(prior_regs),'first_registered_captures':captures,'first_registered_capture_count':len(caps),'downstream_public_ports_before_register':ports,'visited_combinational_cells':len(comb)})
print(json.dumps({'scope':'Read-only actual SC49 functional graph, no CAD/STA. Cell centres used for geometry rule, exact native pin-hop separately retained.','rows':rows},indent=1))
