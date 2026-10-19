"""Exact R0 abstract transforms at PROPOSED origins; not a routed access test."""
import gzip, hashlib, json, pathlib, collections
P = pathlib.Path(__file__).resolve().parent
abstracts = json.load(gzip.open(P.parent/'qwen_a0_ownership_1019/native_abstracts.json.gz'))
origins = json.loads((P/'inherited_origins.json').read_text())['children']
region = [129.6, 349.92, 1166.4, 393.12]
def distance(a,b):
    return max(a[0]-b[2],b[0]-a[2],0)+max(a[1]-b[3],b[1]-a[3],0)
def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
rows=[]
for child in origins:
    name=child['name']; x,y=child['at']
    master='ot_qwen_tile_node' if name=='node' else ('ot_qwen_tile_romleaf' if name.startswith('rom') else 'ot_qwen_tile_lsl_fp1')
    a=abstracts['masters'][master]
    assert a['size_um']==child['size']
    def transform(box):
        r=box['rect_um'];return [r[0]+x,r[1]+y,r[2]+x,r[3]+y]
    shapes=[{'layer':s['layer'],'rect_um':transform(s)} for s in a['obs']]
    pins=[]
    for pin,info in a['pins'].items():
        boxes=[{'layer':s['layer'],'rect_um':transform(s)} for s in info['shapes']]
        pins.append({'pin':pin,'direction':info['direction'],'signal_type':info['signal_type'],
                     'shapes':boxes,'minimum_L1_to_region_um':min((distance(s['rect_um'],region) for s in boxes),default=None)})
    rows.append({'child':name,'master':master,'orientation':'R0_MODEL_ASSUMPTION',
                 'origin_um':[x,y],'OBS_intersection_area_with_region_um2':sum(overlap(s['rect_um'],region) for s in shapes),
                 'transformed_OBS_sha256':hashlib.sha256(json.dumps(shapes,sort_keys=True).encode()).hexdigest(),
                 'transformed_OBS_count':len(shapes),'pins':pins})
with gzip.open(P/'transformed_pins.json.gz','wt') as f:json.dump(rows,f)
summary={'status':'PROPOSED_ORIGIN_TRANSFORMS_NOT_PLACED_OR_ROUTED',
         'native_abstract_odb_sha256':abstracts['odb_sha256'],'region_um':region,
         'children':[{'child':r['child'],'OBS_count':r['transformed_OBS_count'],
                      'OBS_region_intersection_um2':r['OBS_intersection_area_with_region_um2'],
                      'signal_pins':sum(p['signal_type']=='SIGNAL' for p in r['pins']),
                      'PG_pins':sum(p['signal_type'] in ('POWER','GROUND') for p in r['pins']),
                      'max_signal_minimum_L1_to_band_um':max(p['minimum_L1_to_region_um'] for p in r['pins'] if p['signal_type']=='SIGNAL')}for r in rows],
         'qualified':{'route_around_OBS':False,'PG_terminal_binding':False,'PG_via_access':False,'parent_face_access':False,'copy_placement':False},
         'single_common_D_star_extreme_copy_min_radius_um':(region[2]-region[0])/2,
         'extreme_star_fails_405_um':(region[2]-region[0])/2>405,
         'important':'Nearest rectangle L1 is a necessary lower bound, not a routed path. Paths crossing a macro or PG/OBS remain unqualified.'}
(P/'geometry_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
