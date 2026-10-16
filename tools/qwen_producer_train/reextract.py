#!/usr/bin/env python3
import pathlib,re,json,hashlib
D=pathlib.Path(__file__).resolve().parent;R=D.parents[1]
manifest=json.loads((D/'manifest.json').read_text());mapping=json.loads((D/'source_extraction.json').read_text())
for p,h in manifest['source_sha256'].items():
 assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
texts=[]
for name,p in mapping.items():
 s=(R/p).read_text();match=re.search(r'(?m)^module\s+'+re.escape(name)+r'\b.*?\bendmodule',s,re.S);assert match,name;texts.append(match[0])
result='\n'.join(texts);assert result==(D/'component_sources.sv').read_text()
assert result.replace('o_ov1 <= r_v && r_last;',"o_ov1 <= 1'b0; // MUTANT: drop actual producer burst marker")== (D/'mutant_sources.sv').read_text()
print('PASS exact source extraction and producer mutant')
