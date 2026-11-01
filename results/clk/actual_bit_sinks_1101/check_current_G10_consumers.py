from pathlib import Path
import json,copy,sys,time
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r/'tools/die_plan'))
import schema as S,gen_phys as G
raw=S.load(r/'current_C11G_plan.json');patches=json.load(open(r/'current_G10_clock_patch.json'))['patches'];rows=[]
for patch in patches:
 tn=patch['type'];p=S.Plan(copy.deepcopy(raw));assert p.types[tn]['clock']==patch['old_clock'],tn
 p.types[tn]['clock']=patch['replace_clock'];start=time.time()
 try:
  got=G.clock_pins(p,tn);want=[(a['name'],*a['xy'])for a in patch['new_clock_pins_snapped']]
  assert len(got)==len(want),(len(got),len(want))
  assert all(a[0]==b[0]and max(abs(a[1]-b[1]),abs(a[2]-b[2]))<1e-6 for a,b in zip(got,want)),(got,want)
  row=dict(type=tn,status='PASS',actual_generated_ports=len(got),exact_packet_locations=True,seconds=round(time.time()-start,2))
 except Exception as exc:row=dict(type=tn,status='FAIL',error=type(exc).__name__+': '+str(exc),seconds=round(time.time()-start,2))
 rows.append(row);print(row,flush=True)
 (r/'current_G10_consumer_receipt.json').write_text(json.dumps(dict(scope='Finite actual gen_phys.clock_pins consumers for exact currentG10 packet after source bit_sites=True; no clock/STA/source-reset/START event adoption',source_behavior='98e2b77ac actual per-bit station sink consumption',before_fix=dict(type='q_b012',error='explicit tap clk_t15 load0/1500 radius0/220 empty=True',cause='generic sink_sites used nominal FT station centerline'),rows=rows,release_qualified=False),indent=2))
if any(row['status']!='PASS'for row in rows):sys.exit(1)
