#!/usr/bin/env python3
"""Small source-bound storage arithmetic; no synthesis or physical qualification."""
import hashlib, json, math, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[5]
OUT = pathlib.Path(__file__).resolve().parent
def blob(rev, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{rev}:{path}'])
def digest(data): return hashlib.sha256(data).hexdigest()
def family(rev, base, name):
    p = f'{base}/{name}/{name}'
    lef = blob(rev, p + '.lef').decode()
    width, height = map(float, re.search(r'SIZE\s+([\d.]+) BY ([\d.]+)', lef).groups())
    faces = dict(W=0, E=0, interior=0)
    for pin in re.finditer(r'  PIN (\S+)\n(.*?)  END \1', lef, re.S):
        if not re.search(r'USE (SIGNAL|CLOCK)', pin[2]): continue
        for rect in re.finditer(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', pin[2]):
            x0,y0,x1,y1 = map(float, rect.groups())
            faces['W' if x0 == 0 else 'E' if abs(x1-width)<1e-6 else 'interior'] += 1
    return dict(revision=rev, path=p, width_um=width, height_um=height,
                area_um2=width*height, contacts=faces,
                contacts_per_full_face_um={k: v/height for k,v in faces.items() if k!='interior'},
                hashes={ext:digest(blob(rev,p+ext)) for ext in ('.json','.lef','.v','_bb.v','_tt.lib','_ff.lib','_ss.lib')})
small=family('b65718325','physical/asap7_memory_macros_v2','ot_sram_1r1w_32x64_m1')
deep=family('bc42f77a8','physical/asap7_memory_macros_v2','ot_sram_1r1w2c_128x64_m1')
legacy=family('53ccd5927','physical/asap7_memory_macros','ot_sram_1r1w_256x256_m2_r2c2')
# Each tuple: parallel logical stores, depth, width. Arrays with simultaneous independent
# read addresses are explicitly split; neither bandwidth nor port replication is free.
shapes=[('land_lvt_data',12,160,256),('probability_store',2,256,512),
        ('engine_staging',8,160,265),('write_requests',6,8,341),
        ('selection_rows',1,32,527),('pv_results',1,8,2120),('q_rows',1,16,512),
        ('merge_rings',20,8,528),('transposer_row_banks',128,16,18),
        ('stationary_mod8_banks',512,5,64)]
rows=[]
for name,n,d,w in shapes:
    f=deep if d>32 else small
    bank_depth=128 if d>32 else 32
    banks=n*math.ceil(d/bank_depth)*math.ceil(w/64)
    rows.append(dict(name=name,stores=n,depth=d,width=w,useful_bits=n*d*w,
                     candidate_master=pathlib.PurePosixPath(f['path']).name,
                     bank_count=banks,physical_bits=banks*bank_depth*64,
                     raw_area_um2=banks*f['area_um2'],clock_pins=banks*(2 if d>32 else 1)))
sources=['rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv','rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv']
primary=[r for r in rows if r['name'] not in ('merge_rings','transposer_row_banks','stationary_mod8_banks')]
single=[]
for r in primary:
    banks=r['stores']*math.ceil(r['depth']/32)*math.ceil(r['width']/64)
    single.append(dict(name=r['name'],bank_count=banks,physical_bits=banks*2048,
                       raw_area_um2=banks*small['area_um2'],clock_pins=banks))
result=dict(verdict='MODEL_ONLY_SEMANTICS_AND_FIT_OPEN',source_revision='53ccd5927',
 source_hashes={p:digest(blob('53ccd5927',p)) for p in sources},
 families=dict(single_clock_32=small,dual_clock_128=deep,legacy_256=legacy),
 pmem1_slice=primary, all_sram_alternative=rows,
 totals={k:sum(r[k] for r in primary) for k in ('useful_bits','bank_count','physical_bits','raw_area_um2','clock_pins')},
 all_sram_totals={k:sum(r[k] for r in rows) for k in ('useful_bits','bank_count','physical_bits','raw_area_um2','clock_pins')},
 single_clock_only_candidate=single,
 single_clock_only_totals={k:sum(r[k] for r in single) for k in ('bank_count','physical_bits','raw_area_um2','clock_pins')},
 distributed_compute_state_bits=dict(merge_pointer_rings=84480,transposer_rows=36864,stationary_lanes=163840),
 lattice_pitch_um=43.2, claimed_slot_um2=1491000,
 physical_qualification=False, added_edges=None,
 note='Counts are a banking candidate, not implemented wrappers. Data masks/repairs/collision/age/census remain proof obligations.')
result['totals']['lattice_cell_sum_um2']=result['totals']['bank_count']*43.2**2
(OUT/'model.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['totals'],indent=2))
