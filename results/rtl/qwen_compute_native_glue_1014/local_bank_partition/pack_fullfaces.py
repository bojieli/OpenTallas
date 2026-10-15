import json,re,pathlib,math,hashlib
R=pathlib.Path('/home/ubuntu/wt/q-compute-native-parents-1014'); O=pathlib.Path('/tmp/qce-tile-glue-packing')
f=json.loads((R/'physical/ref_tile/qfd_tile_nk_native/floorplan.json').read_text()); original=json.loads(json.dumps(f['blocks'])); blocks=json.loads(json.dumps(original))
for b in blocks:
 if b['master']=='ot_qwen_tile_node': b['x']=340.2;b['y']=410.4
 if b['master']=='ot_qwen_tile_rpair' and b['orient']=='MX': b['y']+=12.936
 if b['master']=='ot_qwen_tile_lsl_fp1':
  row=round((b['y']-328.32)/164.16);b['y']=[330.48,496.8,663.12,829.44][row]
banks=[]; P={"v16":{"outline_um":[21.6,21.6],"positions":{}}}
for name in ['h263','v263','h256','v256']:
 p=R/f'physical/ref_tile/qkh_packet_{name}/assigned_pins.json';P[name]=json.loads(p.read_text())
def bank(n,m,x,y,orient='R0',**kw):
 w,h=P[m]['outline_um']; b=dict(inst=n,master='qkh_packet_'+m,x=x,y=y,w=w,h=h,orient=orient,kind='proposed_bank',**kw);banks.append(b);return b
def pair(n,x,y,**kw):return [bank(n+'_lo','v263',x,y,**kw),bank(n+'_hi','v256',x+20.52,y,**kw)]
faces={}
for i,(n,y) in enumerate(zip(['n_a','n_b','n_y','t_out'],[350.136,420.336,490.536,841.536])):faces[n]=pair('face_'+n,46.44,y,purpose='existing native face register replacement')
faces['t_out'][0].update(x=5.4,y=591.136)
faces['t_out'][1].update(x=25.92,y=591.136)
faces['tap']=pair('face_tap',393.12,911.736,purpose='existing tap register replacement')
bank('strap','v16',393.12,983.016,purpose='existing tile_id register replacement')
rqr={}
for n,y in [('south',975.24),('north',309.96)]:rqr[n]=[bank(f'rqr_{n}_{i}','h256',25.92+70.2*i,y,purpose='existing 1024-bit RQR collector') for i in range(4)]
mqw=[bank('mq_wrom_'+str(i),'h256',25.92+70.2*i,642.6,purpose='existing unreset mq_wrom 256-bit lane capture')for i in range(4)]
s2w=[bank('s2_w_'+str(i),'v256',209.088,500.04+70.2*i,purpose='existing unreset s2_w 256 variable upper-halfword bits')for i in range(4)]
xdelay=[bank('xdelay_'+str(i),'h256',25.92+70.2*([3,2,1,0,0,1,2,3][i]),808.92 if i<4 else 476.28,used_bits=128,purpose='existing 128-bit x delay rung')for i in range(8)]
tx={}
for g in range(8):
 r=g%4
 if g<4:
  a=pair(f'tx{g}_r0',46.44,560.736+70.2*r,purpose='existing first TX rung')
  z=pair(f'tx{g}_r1',5.4,360.936+160*r,purpose='existing second TX rung')
 else:
  a=pair(f'tx{g}_r0',393.12,560.736+70.2*r,purpose='existing first TX rung')
  z=pair(f'tx{g}_r1',393.12,[350.136,420.336,490.536,841.536][r],purpose='existing second TX rung')
 tx[g]=(a,z)
# Joint channel-aware placement: keep all V bodies clear of the five H-bank bands.
for n,y in zip(['n_a','n_b','n_y','t_out'],[496.8,567.0,733.32,663.12]):
 for j,b in enumerate(faces[n]):b.update(x=5.4+20.52*j,y=y)
for j,b in enumerate(faces['tap']):b.update(x=393.12+20.52*j,y=980.64)
next(b for b in banks if b['inst']=='strap').update(y=1060.56)
for i,b in enumerate(s2w):b['y']=[500.04,570.24,663.12,733.32][i]
for g,(a,z) in tx.items():
 r=g%4
 for j,b in enumerate(a):b.update(x=(46.44 if g<4 else 393.12)+20.52*j,y=[496.8,567.0,663.12,733.32][r])
 for j,b in enumerate(z):b.update(x=(5.4 if g<4 else 393.12)+20.52*j,y=[330.48,400.68,829.44,899.64][r])
# Speculative full-word face masters: data pins are a frozen proposal, not routed LEFs.
for n,W in [('v514',514),('v508',508)]:
 P[n]={'outline_um':[21.6,75.6],'positions':{'d':{'layer':'M4','xy_um':[[0.096,round((5.4+64.8*i/(W-1)-0.012)/0.048)*0.048+0.012]for i in range(W)]},'q':{'layer':'M4','xy_um':[[21.504,round((5.4+64.8*i/(W-1)-0.012)/0.048)*0.048+0.012]for i in range(W)]},'clk':{'layer':'M5','xy_um':[[4.968,0.096]]},'rst_n':{'layer':'M5','xy_um':[[9.708,0.096]]}}}
banks[:]=[b for b in banks if not b['inst'].startswith('face_')]
for n,x,center,ori in [('n_a',5.4,637.404,'R0'),('n_b',32.4,693.420,'R0'),('n_y',5.4,749.436,'MY'),('t_out',32.4,805.404,'MY'),('tap',422.28,721.404,'MY')]:
 faces[n]=[bank('face_'+n,'v508'if n=='tap'else'v514',x,round((center-37.8)/0.048)*0.048,orient=ori,purpose='SPECULATIVE fullword face ABI pending actual build')]
for g,(a,z) in tx.items():
 if g<4:
  for j,b in enumerate(a):b['x']=59.4+20.52*j
  for j,b in enumerate(z):b['x']=59.4+20.52*j
for g,y in [(6,847.8),(7,918.0)]:tx[g][0][1].update(x=367.2,y=y)
for n in ['v514','v508']:P[n]=json.loads((R/f'physical/ref_tile/qwen_glue_{n}/assigned_pins.json').read_text())
for n in ['v514','v508']:P['qwen_glue_'+n]=P[n]
for bs in faces.values():bs[0]['master']=bs[0]['master'].replace('qkh_packet_','qwen_glue_')
mqw[0].update(master='qkh_packet_v256',x=5.4,y=529.2,w=15.12,h=64.8)
xdelay[3].update(master='qkh_packet_v256',x=5.4,y=792.648,w=15.12,h=64.8)
def transform(b,p):
 x,y=p
 if b['orient'] in ['MY','R180']:x=b['w']-x
 if b['orient'] in ['MX','R180']:y=b['h']-y
 return [round(b['x']+x,6),round(b['y']+y,6)]
def bp(b,port,i):return transform(b,P[b['master'].removeprefix('qkh_packet_')]['positions'][port]['xy_um'][i])
def pp(pair,port,i):return bp(pair[0],port,i) if len(pair)==1 or i<263 else bp(pair[1],port,i-263)
def lef(b):
 p=R/b['view']/(b['master']+'.lef');s=p.read_text(); out={}
 for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1\n',s,re.S):
  rs=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body)
  if rs:
   # Prefer actual boundary access rectangle over internal access jog.
   rr=min(rs,key=lambda r:min(float(r[0]),float(r[1]),abs(b['w']-float(r[2])),abs(b['h']-float(r[3]))))
   x0,y0,x1,y1=map(float,rr);out[name]=transform(b,[(x0+x1)/2,(y0+y1)/2])
 return out
lp={b['inst']:lef(b) for b in blocks}; legs=[]; details=[]
def leg(n,pts,scope):
 vals=[]
 for tag,a,b in pts:
  d=abs(a[0]-b[0])+abs(a[1]-b[1]);vals.append(d);details.append(dict(leg=n,bit=tag,source_xy=a,sink_xy=b,manhattan_um=round(d,6)))
 j=max(range(len(vals)),key=vals.__getitem__);legs.append(dict(name=n,scope=scope,count=len(vals),max_um=round(vals[j],6),worst_bit=pts[j][0],pass_500=max(vals)<=500))
ports=json.loads((R/'results/arch/qwen_split_compute_1014/c17_source_pins/qfd_tile_nk.json').read_text())['ports']
for n,bs in faces.items():
 p=ports[n];lo,hi=p['range_um'];N=p['bits'];pinport='d' if p['direction']=='input'else'q'
 leg('face_'+n,[(i,[0 if p['face']=='W'else 449.28,lo+(hi-lo)*i/(N-1)],pp(bs,pinport,i))for i in range(N)],'actual parent assigned pin to proposed bank')
node=next(b for b in blocks if b['master']=='ot_qwen_tile_node');np=lp[node['inst']]
for n,npn in [('n_a','a'),('n_b','b'),('n_y','y'),('t_out','t_out')]:
 leg(n+'_bank_node_data',[(i,pp(faces[n],'q'if n in ['n_a','n_b']else'd',i),np[f'{npn}[{i}]'])for i in range(512)],'actual transformed node data pin; metadata semantics remain source work')
for b in blocks:
 if b['master']!='ot_qwen_tile_rpair':continue
 idx=int(re.search(r'g_rb\[(\d+)\]',b['inst'])[1]);group='south'if idx<3 else'north';p=lp[b['inst']]
 leg('rp'+str(idx)+'_to_rqr_'+group,[(i,p[f'r_q[{i}]'],bp(rqr[group][i//256],'d',i%256))for i in range(1024)],'actual transformed ROM return pin; existing OR logic remains to qualify')
for g,(a,z) in tx.items():
 leg(f'tx{g}_r0_r1',[(i,pp(a,'q',i),pp(z,'d',i))for i in range(390)],'proposed existing rung to rung')
 b=next(b for b in blocks if b['master']=='ot_qwen_tile_lsl_fp1'and f'g_sl[{g}]'in b['inst']);p=lp[b['inst']]
 names=[f'x_d[{i}]'for i in range(128)]+[f'w_d[{i}]'for i in range(256)]+[f'split_d[{i}]'for i in range(4)]+['first_d','v_d']
 leg(f'tx{g}_r1_to_lsl',[(i,pp(z,'q',i),p[n])for i,n in enumerate(names)],'actual transformed LSL ingress pin')
for group,bs in rqr.items():
 leg(f'rqr_{group}_to_mq_wrom',[(i,bp(bs[i//256],'q',i%256),bp(mqw[i//256],'d',i%256))for i in range(1024)],'exact source wrom_q=gs_q|gn_q to unreset mq_wrom')
leg('mq_wrom_to_s2_w',[(i,bp(mqw[i//256],'q',i%256),bp(s2w[i//256],'d',i%256))for i in range(1024)],'exact ROM-mode upper16-bit mapping; lower16 zero; group mask/select logic pending')
for g,(a,z) in tx.items():
 pts=[]
 for gl in range(8):
  weight=(gl//2)*16+g*2+gl%2
  for k in range(16):
   src=weight*16+k;dst=128+gl*32+16+k
   pts.append((f'{src}:{dst}',bp(s2w[src//256],'q',src%256),pp(a,'d',dst)))
 leg(f's2_w_to_tx{g}_r0',pts,'exact G4 HIER2 W16 source mapping; lower16 of each TX weight constant0')
# Three existing128-bit captures use spare physical bank bits, preserving individual capture edges.
xl_bank=xdelay[0];mqx_bank=xdelay[6];s2x_bank=tx[1][0][1]
xl_bank['spare_payload']='xl_q[127:0] in bank[255:128]; IREG1'
mqx_bank['spare_payload']='mq_x[127:0] in bank[255:128]'
s2x_bank['spare_payload']='s2_x[127:0] in bank[255:128]; TXr0 high payload occupies[126:0]'
leg('tap_to_xl_q',[(i,pp(faces['tap'],'q',380+i),bp(xl_bank,'d',128+i))for i in range(128)],'exact production IREG1 unreset xl_q capture')
leg('xl_q_to_xdelay0',[(i,bp(xl_bank,'q',128+i),bp(xdelay[0],'d',i))for i in range(128)],'exact IREG1 then existing u_xm stage0')
leg('xdelay7_to_mq_x',[(i,bp(xdelay[7],'q',i),bp(mqx_bank,'d',128+i))for i in range(128)],'existing unreset mq_x <= x_q')
leg('mq_x_to_s2_x',[(i,bp(mqx_bank,'q',128+i),bp(s2x_bank,'d',128+i))for i in range(128)],'existing unreset s2_x <= mq_x')
for g,(a,z) in tx.items():
 leg(f's2_x_to_tx{g}_r0',[(f'{32*w+j}:{32*w+k}',bp(s2x_bank,'q',128+32*w+j),pp(a,'d',32*w+k))for w in range(4)for k in range(32)for j in range(k+1)],'existing rounded/masked x path; conservative prefix-adder inputbit<=outputbit dependencies, control sources pending')
for i in range(7):leg(f'xdelay_{i}_{i+1}',[(k,bp(xdelay[i],'q',k),bp(xdelay[i+1],'d',k))for k in range(128)],'proposed existing x-delay rung to rung')
allb=blocks+banks; overlaps=[]; halo=[]
for i,a in enumerate(allb):
 for b in allb[i+1:]:
  dx=max(a['x']-b['x']-b['w'],b['x']-a['x']-a['w'],0);dy=max(a['y']-b['y']-b['h'],b['y']-a['y']-a['h'],0)
  if dx==0 and dy==0:overlaps.append([a['inst'],b['inst']])
  if dx<5.4-1e-6 and dy<5.4-1e-6:halo.append([a['inst'],b['inst'],round(dx,6),round(dy,6)])
report=dict(status='GEOMETRY_CANDIDATE_NOT_QUALIFIED',outline_um=[449.28,1442.88],metric='Manhattan pin center distance; no obstacle detour/timing qualification',original_children=original,candidate_children=blocks,banks=banks,bank_count=len(banks),body_overlaps=overlaps,halo_5p4_violations=halo,boundary_violations=[b['inst']for b in allb if b['x']<0 or b['y']<0 or b['x']+b['w']>449.280001 or b['y']+b['h']>1442.880001],legs=legs,unresolved=['Bank routes are RUNNING, not CLOSED; current pins are frozen plan, not final routed LEF.','Reset warmup and existing unreset payload semantics require source-qualified comparison.','No inference that hardening all bank boundaries preserves arithmetic/metadata or source structure.','RQR-to-TX relation reported as geometric envelope; exact decode dependencies and intermediate combinational placement are unqualified.','Unbanked issue/address/control/fault glue still needs independent clock-root analysis.','Parent ck_node and modified LSL row clock entries must be transformed to new exact child positions.','NL has no node; reuse of NK candidate needs independent NL source and pin binding.'])
(O/'fullface_candidate.json').write_text(json.dumps(report,indent=2)+'\n');(O/'fullface_per_bit_distances.json').write_text(json.dumps(details,separators=(',',':'))+'\n')
print(json.dumps({k:report[k]for k in ['bank_count','body_overlaps','halo_5p4_violations','boundary_violations']},indent=2));print('failed legs:');print(json.dumps([x for x in legs if not x['pass_500']],indent=2));print('exact max',max((x for x in legs if 'envelope'not in x['name']),key=lambda x:x['max_um']))
report['diagnostic_envelopes']=[x for x in report['legs']if 'envelope'in x['name']]
report['legs']=[x for x in report['legs']if 'envelope'not in x['name']]
report['clock_entries']=[{'inst':b['inst'],'master':b['master'],'orient':b['orient'],'clk_xy_um':lp[b['inst']]['clk']}for b in blocks]
report['source_files_sha256']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/'physical/ref_tile/qfd_tile_nk_native/floorplan.json',R/'results/arch/qwen_split_compute_1014/c17_source_pins/qfd_tile_nk.json',R/'rtl/hdc/ot_qwen_w12_matvec.sv',R/'rtl/hdc/ot_qwen_rom_tile_w12.sv']+[R/f'physical/ref_tile/qkh_packet_{n}/assigned_pins.json'for n in ['h263','h256','v263','v256']]+[R/b['view']/(b['master']+'.lef')for b in blocks]}
report['unresolved']=[x for x in report['unresolved']if not x.startswith('RQR-to-TX')]
report['unresolved']+=['RQR→mq_wrom→s2_w→TXr0 contains TWO existing captures (ot_qwen_w12_matvec.sv743–774). Operand register placement and clock partition remain outside this requested59-bank inventory. Diagnostic RQR→TX envelopes are not direct timing legs and do not establish failure.','At least mq_wrom1024, variable s2_w1024, mq_x128 and s2_x128 register bits remain to inventory against synthesized sink names. Constant/unused payload pruning must be measured, not guessed.','V bank PG2 successor has unchanged d/q XY; planned clk coordinate changes need binding to actual CLOSED successor. V16 pin coordinates unavailable here, so only its21.6×21.6 body is reserved.']
report['known_leg_max_um']=max(x['max_um']for x in report['legs'])
report['known_legs_over_500']=[x for x in report['legs']if not x['pass_500']]
(O/'fullface_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
report['scope']='NK fixed-outline internal data-bank packing extended through actual operand captures; not physical/source qualification'
report['clock_root_partition']={'existing_closed_child_roots':14,'proposed_bank_roots':67,'residual_glue_roots':1,'total_if_all_banks_adopted':82,'qualification':'candidate independent roots only; synthesized residual sink count and parentCTS not measured'}
report['proposed_bank_clock_entries']=[{'inst':b['inst'],'master':b['master'],'clk_xy_um':transform(b,P[b['master'].removeprefix('qkh_packet_')]['positions']['clk']['xy_um'][0]) if 'clk'in P[b['master'].removeprefix('qkh_packet_')]['positions']else None}for b in banks]
report['capture_inventory']=[{'name':'RQR gs_q/gn_q','count':2,'width':1024,'banks':8,'reset':'none','data':'OR of source rpair returns within SB logical group; capture every edge'},{'name':'mq_wrom','count':1,'width':1024,'banks':4,'reset':'none','data':'wrom_q=gs_q|gn_q, capture every edge'},{'name':'s2_w','count':1,'logical_width':2048,'variable_width':1024,'banks':4,'reset':'none','data':'32-bit weight word lower16 constant0; upper16 equals mq_wrom16 when group enabled and ROM source selected, otherwise0 (KV_SLICE0)','controls':['s1b_gm[3:0]','s1b_wsrc']},{'name':'u_xm','count':8,'width':128,'banks':8,'reset':'ot_hdc_delay internal exact reset behavior must be preserved','data':'128-bit registered delay each edge'},{'name':'xl_q (IREG1), mq_x, s2_x','count':3,'width':128,'additional_banks':0,'reset':'none','data':'use spare upper128 bits of xdelay0, xdelay6, tx1_r0_hi respectively'},{'name':'TX','count':16,'width':390,'banks':32,'reset':'ot_qwen_tx_ff resets only v (bit389), other bits unreset','data':'128 x bits,256 weight bits,4 split bits,first,v; W upper16 variable/lower16constant0','control_pending':['s2_gm[3:0]','s2_round','s2_v','s2_first','s2_tag split bits']}]
report['exact_lane_mapping']={'parameters':{'G':4,'W':16,'HIER':2,'GL':4,'WCONV':1,'IREG':1,'XTX':2},'mq_wrom_index':'16*((gl//2)*16+g*2+(gl%2))+k','s2_w_logical_index':'32*((gl//2)*16+g*2+(gl%2))+16+k','tx_r0_index':'128+32*gl+16+k','gl_range':[0,7],'k_range':[0,15],'s2_w_compact_bank':'source_index//256','s2_w_compact_bit':'source_index%256'}
report['unresolved']=['These are geometric Manhattan center distances; obstacle detours, actual extracted RC, STA, DRC and residual-clock CTS remain unqualified.','Control endpoints for s1b_gm/s1b_wsrc (weight gating), s2_gm/s2_round (x gating/rounding), six TX metadata bits and all instruction/address/fault/reset metadata need actual source-root inventory and positions. Existing register edges may not be removed or assumed constant without synthesized evidence.','The67-bank layout includes exact ROM operand and x payload captures, but does not claim that all15037 original glue clock sinks are partitioned. Measure residual synthesized sinks.','Source registers mq_wrom/s2_w/xl_q/mq_x/s2_x are unreset, TX resets only valid. Generic packet-master reset-all-data behavior needs an explicitly priced warmup contract and source exactness/negative controls.','V bank PG2 successor d/q are unchanged; this report hashes current assigned pins and records current clk4.968. Adoption requires actual CLOSED matching master views.','V16 fixed pin manifest unavailable here: its21.6square body is reserved, but strap pin reaches remain unmeasured.','All relocated RPAIR/LSL/node child clock entries in candidate must be exported into actual parent manifest. No parent physical qualification is implied.','Independent NL source/face binding is not performed; NL has no node and its omitted face/control logic must be inventoried separately.']
(O/'fullface_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print('FINAL',json.dumps({'banks':len(banks),'known_legs':len(report['legs']),'max_um':report['known_leg_max_um'],'overlaps':len(overlaps),'halo_failures':len(halo),'known_failed_legs':report['known_legs_over_500']}))

report['speculative_face_master_pins']={n:P[n]for n in ['v514','v508']}
report['clock_root_partition'].update(proposed_bank_roots=62,total_if_all_banks_adopted=77)
report['unresolved'].append('Fullword face masters are speculative21.6x75.6 pin proposals, not CLOSED; source/gate/route/nativeTT required.')
(O/'fullface_candidate.json').write_text(json.dumps(report,indent=2)+'\n')

(O/'speculative_fullface_pins.json').write_text(json.dumps({n:P[n]for n in ['qwen_glue_v514','qwen_glue_v508']},indent=2)+'\n')

report['source_files_sha256'].update({str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/f'physical/ref_tile/qwen_glue_{n}/assigned_pins.json'for n in ['v514','v508']]})
report['face_pin_basis']='Actual committed frozen source manifest674d57420; master physical routes pending'
report['speculative_face_master_pins']={n:P[n]for n in ['qwen_glue_v514','qwen_glue_v508']}
(O/'fullface_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'frozen_source_fullface_pins.json').write_text(json.dumps({n:P[n]for n in ['qwen_glue_v514','qwen_glue_v508']},indent=2)+'\n')
