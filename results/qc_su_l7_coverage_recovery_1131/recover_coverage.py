"""Offline recovery ONLY after the immutable native GRT writer has terminated."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('kit',type=Path);p.add_argument('--writer-terminal-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
k=a.kit.resolve();o=a.out.resolve()
assert o!=k and not o.exists(),'fresh distinct recovery output required'
receipt=json.loads(a.writer_terminal_receipt.read_text())
assert isinstance(receipt.get('rc'),int) and receipt.get('end'),'actual terminal writer receipt required'
assert (k/'native_grt.rc').read_text().strip()=='0','native GRT failed; no coverage recovery qualification'
assert (k/'combined_post.rc').read_text().strip()=='0','post census failed'
assert 'COMBINED_GRT_POST ' in (k/'combined_post.log').read_text(),'post census completion marker missing'
raw=k/'combined_clock_census.tsv';data=raw.read_text();lines=data.splitlines()
head=['class','net','degree','special','guides','special_wires'];literal='\\t'
assert lines and lines[0]==literal.join(head),'exact known literal-tab header required'
assert '\t' not in data,'mixed literal/actual delimiters ambiguous'
rows=[];counts={'CLOCK':0,'SIGNAL':0}
for no,line in enumerate(lines[1:],2):
 fields=line.split(literal)
 assert len(fields)==len(head),f'ambiguous row{no}:column count'
 cl,net,degree,special,guides,sw=fields
 assert cl in {'CLOCK','SIGNAL','POWER','GROUND','RESET','ANALOG','SCAN','TIEOFF'},f'unknown class row{no}'
 assert net and all(x.isdecimal() for x in (degree,special,guides,sw)),f'malformed row{no}'
 if cl in counts and int(degree)>1:
  counts[cl]+=1
  assert int(special)==0 and int(sw)==0 and int(guides)>0,f'actual DB routing coverage fail row{no}'
 rows.append(fields)
assert all(counts.values()),'missing connected class'
o.mkdir()
normalized=o/'combined_clock_census.tsv';normalized.write_text('\t'.join(head)+'\n'+''.join('\t'.join(x)+'\n'for x in rows))
for name in ('run','combined_pre_census.tsv','clock_roots.tsv','clock_pin_coverage.tsv'):
 src=k/name
 if src.exists():(o/name).symlink_to(src,target_is_directory=src.is_dir())
consumer=k/'verify_guides.py';assert consumer.is_file()
rc=subprocess.run([sys.executable,str(consumer),str(o)]).returncode
rec={'schema':'opentallas.literal_tsv_recovery.v1','method':'exact literal separator/schema-only normalization; no CAD/routing/flag/source modification','original_raw':str(raw),'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'normalized_sha256':hashlib.sha256(normalized.read_bytes()).hexdigest(),'writer_terminal_receipt':str(a.writer_terminal_receipt),'actual_writer_rc':receipt['rc'],'outer_failure_preserved':True,'connected_classes':counts,'consumer':str(consumer),'consumer_sha256':hashlib.sha256(consumer.read_bytes()).hexdigest(),'consumer_rc':rc,'rows':len(rows),'scope':'coverage artifact recovery only; no TT/FF/DRT/EQ/source qualification'}
(o/'normalization_receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
assert rc==0,'pure coverage consumer failed; retain failed recovery'
