import pathlib,json,gzip,collections
r=pathlib.Path(__file__).parent
for mode in ['r7w','ovl']:
 f=json.loads(gzip.decompress((r/f'kv_d2d_{mode}_faces.json.gz').read_bytes()));j=json.load(open(r/f'{mode}.roles.json'));bs={x[0]:x for x in f['bterms']};rows=[];groups=collections.defaultdict(list)
 for o in j['output_ownership']:
  name=o['port'];key=f'{name}[{o["bit"]}]';key=key if key in bs else name
  assert key in bs,(key,o)
  rects=bs[key][4];faces=set()
  for layer,(x0,y0,x1,y1) in rects:
   distances=dict(W=abs(x0-f['die'][0]),E=abs(x1-f['die'][2]),S=abs(y0-f['die'][1]),N=abs(y1-f['die'][3]));faces.add(min(distances,key=distances.get))
  row=dict(o,name=key,rects=rects,faces=sorted(faces));rows.append(row)
  if o['source_driver'][1].startswith('DFF'):groups[tuple(o['source_driver'])].append(row)
 summary=[]
 for driver,ports in groups.items():
  faces=sorted(set(x for p in ports for x in p['faces']));rects=[box for p in ports for layer,box in p['rects']];span=max(b[2]for b in rects)-min(b[0]for b in rects)+max(b[3]for b in rects)-min(b[1]for b in rects)
  summary.append(dict(driver=driver,ports=[p['name']for p in ports],faces=faces,rectangle_manhattan_span_um=span))
 out=dict(original_face_dump_sha256=f['source_sha256'],all_output_ports_resolved=len(rows),distinct_boundary_FFs=len(groups),crossface_shared_FFs=[g for g in summary if len(g['faces'])>1],max_pin_rectangle_span_um=max(x['rectangle_manhattan_span_um']for x in summary),groups=summary,output_ownership=rows,qualified=False)
 (r/f'{mode}.fixed_face.json').write_text(json.dumps(out,indent=2)+'\n');print(mode,{k:v for k,v in out.items()if k not in ('groups','output_ownership','crossface_shared_FFs')},'crossface',len(out['crossface_shared_FFs']))
