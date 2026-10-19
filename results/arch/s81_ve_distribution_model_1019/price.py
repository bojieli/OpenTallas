import gzip,hashlib,json,re,math
from pathlib import Path
P=Path(__file__).resolve().parent
root=Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM')
f=json.loads((P/'fixed_point.json').read_text()); want=f['added_by_master']; coeff={}; hashes={}
for corner in ('TT','FF'):
    table={}
    for family,date in [('SEQ','220123'),('SIMPLE','211120' if corner=='TT' else '250407'),('INVBUF','220122'),('AO','211120'),('OA','211120')]:
        stem=root/f'asap7sc7p5t_{family}_RVT_{corner}_nldm_{date}.lib'
        path=stem if stem.exists() else Path(str(stem)+'.gz')
        raw=path.read_bytes();txt=(gzip.decompress(raw) if path.suffix=='.gz' else raw).decode();hashes[str(path)]=hashlib.sha256(raw).hexdigest()
        # A cell body extends to the next cell; only scalar area and first pin cap used.
        starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',txt))
        for k,m in enumerate(starts):
            name=m.group(1)
            if name not in want:continue
            body=txt[m.end():starts[k+1].start() if k+1<len(starts) else len(txt)]
            area=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)',body).group(1));cap=None
            ck=re.search(r'\bpin\s*\(\s*CLK\s*\)\s*\{',body)
            if ck:cap=float(re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)',body[ck.end():]).group(1))
            table[name]=dict(area_um2=area,clock_cap_fF=cap,library=str(path))
    assert not(set(want)-set(table)),set(want)-set(table)
    coeff[corner]=table
out=dict(library_sha256=hashes,coefficient_by_corner=coeff,added_area_um2_by_corner={c:sum(want[m]*v['area_um2'] for m,v in t.items()) for c,t in coeff.items()},added_clock_cap_fF_by_corner={c:sum(want[m]*(v['clock_cap_fF'] or 0) for m,v in t.items()) for c,t in coeff.items()},added_clock_pins=f['added_by_role']['ff'],scope='Exact selected native master scalar areas/clock caps. Does not price CTS buffer/wire, routing or PG overhead; copies are analytical and unsynthesized.')
area=40683+out['added_area_um2_by_corner']['TT'];out['conditional_cts_base_plus_copies_um2']=area;out['one_square_band_40_to_60pct_side_um']=[math.sqrt(area/.6),math.sqrt(area/.4)];out['max_outline_manhattan_um_at_60pct']=2*math.sqrt(area/.6);out['universal_reach_405_square_max_std_at_60pct']=.6*(405/2)**2
(P/'price.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('library_sha256','coefficient_by_corner')},indent=2))
