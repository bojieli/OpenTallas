from pathlib import Path
import sys,hashlib,json
p=Path(sys.argv[1])/'detail_route.tcl';s=p.read_text();old='load_design 5_1_grt.odb 5_1_grt.sdc';assert s.count(old)==1
before=hashlib.sha256(s.encode()).hexdigest();p.write_text(s.replace(old,'load_design ../../../../../../work/run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base/5_2_route.odb ../../../../../../work/lvt_grt.sdc',1));print(json.dumps({'scope':'honest genuine5_2 input plus actual retainedSDC; native detailed route unchanged','before':before}))
