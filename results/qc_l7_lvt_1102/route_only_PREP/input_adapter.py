from pathlib import Path
import sys,json,hashlib
p=Path(sys.argv[1])/'detail_route.tcl';s=p.read_text();old='load_design 5_1_grt.odb 5_1_grt.sdc';assert s.count(old)==1
new='load_design ../../../../../../work/LVT_DATA_GEOMETRY_CHECKPOINT.odb ../../../../../../work/constraint.sdc'
p.write_text(s.replace(old,new,1))
print(json.dumps({'scope':'input-only exact native saved LVT geometry+unchanged actual finalGRTSDC; full original detail_route body retained','before_sha256':hashlib.sha256(s.encode()).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
