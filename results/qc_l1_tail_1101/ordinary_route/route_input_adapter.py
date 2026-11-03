from pathlib import Path
import sys,json,hashlib
s=Path(sys.argv[1]);rec={}
for name,old,new in [
 ('detail_route.tcl','load_design 5_1_grt.odb 5_1_grt.sdc','load_design ../../../../../lvt_grt.odb ../../../../../lvt_grt.sdc'),
 ('fillcell.tcl','load_design 5_2_route.odb 5_1_grt.sdc','load_design 5_2_route.odb ../../../../../lvt_grt.sdc')]:
 p=s/name;t=p.read_text();assert t.count(old)==1,(name,'anchor');rec[name]=hashlib.sha256(t.encode()).hexdigest();p.write_text(t.replace(old,new,1))
m=s.parent/'Makefile';t=m.read_text();old='$(eval $(call do-copy,5_route,5_1_grt.sdc,,.sdc))';assert t.count(old)==1
new='.PHONY: do-5_route.sdc\ndo-5_route.sdc:\n\tcp /work/lvt_grt.sdc $(RESULTS_DIR)/5_route.sdc'
rec['Makefile']=hashlib.sha256(t.encode()).hexdigest();m.write_text(t.replace(old,new,1));print(json.dumps({'scope':'actual retained GRT input paths only; native route/fill/final unchanged','before':rec},indent=2))
