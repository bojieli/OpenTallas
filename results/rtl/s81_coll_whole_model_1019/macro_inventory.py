"""Read-only exact LEF contact inventory from preserved git objects."""
from pathlib import Path
import collections,hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
WT=HERE.parents[2]
assert subprocess.check_output(['git','-C',str(WT),'rev-parse','--show-toplevel'],text=True).strip()==str(WT)
specs=[('HEAD','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2',10,128,512,552+1,512),
       ('HEAD','physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1',5,128,32,553,8),
       ('1298888bc','physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1',10,64,32,595,4)]
out=[]
for rev,base,n,bw,bd,lw,ld in specs:
    master=base.split('/')[-1]
    def read(ext):
        suffix=('_'+ext) if ext.endswith('.lib') else ('.'+ext)
        return subprocess.check_output(['git','-C',str(WT),'show',f'{rev}:{base}/{master}{suffix}'])
    raw=read('lef'); t=raw.decode(); w,h=map(float,re.search(r'SIZE\s+([\d.]+) BY ([\d.]+)',t).groups())
    contacts=collections.Counter(); pg=collections.Counter(); spans=collections.defaultdict(list)
    for pin,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1\n',t,re.S):
        power=bool(re.search(r'USE (POWER|GROUND)',body))
        for xs,ys,xe,ye in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body):
            x,y=(float(xs)+float(xe))/2,(float(ys)+float(ye))/2
            face=min({'W':x,'E':w-x,'S':y,'N':h-y},key=lambda f:{'W':x,'E':w-x,'S':y,'N':h-y}[f])
            (pg if power else contacts)[face]+=1
            if not power:spans[face].append(y if face in ('W','E') else x)
    row={'master':master,'source_ref':rev,'count':n,'dimensions_um':[w,h],
         'source_sha256':{ext:hashlib.sha256(read(ext)).hexdigest() for ext in ('lef','v','tt.lib','ff.lib')},
         'signal_clock_contacts_per_face':dict(contacts),'pg_contacts_per_face':dict(pg),
         'signal_contact_density_per_um':{f:c/(h if f in ('W','E') else w) for f,c in contacts.items()},
         'active_contact_spans_um':{f:[min(v),max(v)] for f,v in spans.items()},
         'raw_addressable_bits':n*bw*bd,
         'physical_array_bits_including_spares':n*130*520 if bw==128 and bd==512 else n*bw*bd,
         'logical_width':lw,'logical_depth':ld,
         'logical_bits':lw*ld if n!=10 or bw!=128 else 2*lw*ld,
         'clock_ports':re.findall(r'  PIN (\S+)\n\s+DIRECTION INPUT ;\n\s+USE CLOCK',t),
         'actual_array_escape_qualified':False}
    out.append(row)
(HERE/'macro_inventory.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k not in ('source_sha256',)} for r in out],indent=2))
