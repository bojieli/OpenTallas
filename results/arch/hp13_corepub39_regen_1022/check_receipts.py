"""Check current canonical sources, or an explicitly isolated selected-source fixture."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,tempfile
REPO=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent

def check(root):
    s=importlib.util.spec_from_file_location("tt_source_local",REPO/"tools/qwen_split/tt_source_local.py")
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    r=root/PACKET.relative_to(REPO)
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

p=argparse.ArgumentParser(description=__doc__)
g=p.add_mutually_exclusive_group()
g.add_argument("--source-root",type=Path,help="Explicit source-complete selected GEN envelope root")
g.add_argument("--selected-readset",action="store_true",help="Isolate archived selected bytes; never qualifies current canonical RTL")
a=p.parse_args()
if a.selected_readset:
    with tempfile.TemporaryDirectory(prefix="hp13-selected-source-") as temp:
        root=Path(temp)
        shutil.copytree(PACKET,root/PACKET.relative_to(REPO))
        manifest=json.loads((PACKET/"SELECTED_SOURCE_ARCHIVE.json").read_text())
        for row in manifest["files"]:
            src=REPO/row["archive_path"]
            assert hashlib.sha256(src.read_bytes()).hexdigest()==row["sha256"]
            target=root/row["canonical_path"];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,target)
        print("SELECTED_READSET_ONLY: canonical main qualification is not claimed")
        check(root)
else:
    check((a.source_root or REPO).resolve())
