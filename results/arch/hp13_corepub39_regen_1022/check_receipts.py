from pathlib import Path
import importlib.util,json,tempfile
root=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location("tt_source_local",root/"tools/qwen_split/tt_source_local.py")
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=Path(__file__).resolve().parent
for stage in [1,2]:
 p=r/f"LOCAL_AVAILABILITY_p{stage}.json";row=json.loads(p.read_text())
 age,source=m.source_local_edges(root,row["master"],p)
 assert age==1+stage
 print("TYPED_LOCAL_AGE_PASS",stage,age,row["rtl_sha256"])
 for field,value in [("rtl_sha256","0"*64),("source_local_edges",4),("master","wrong_master")]:
  bad=dict(row);bad[field]=value
  with tempfile.NamedTemporaryFile(mode="w",suffix=".json") as f:
   json.dump(bad,f);f.flush()
   try:m.source_local_edges(root,row["master"],f.name)
   except (ValueError,KeyError):print("TYPED_LOCAL_NEGATIVE_CAUGHT",stage,field)
   else:raise AssertionError(field)
