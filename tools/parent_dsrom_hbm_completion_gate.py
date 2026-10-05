#!/usr/bin/env python3
"""Reproduce legacy simulation-column write completion; no hardware qualification."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN="d2c28c279c4b8df731f9c4937e790831529a954b"
SOURCE="rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv"
BENCH="results/quality/parent_dsrom_hbm_completion_review_20261001/tb.sv"
def main(out):
 raw=subprocess.check_output(["git","show",PIN+":"+SOURCE],cwd=ROOT);tb=(ROOT/BENCH).read_bytes()
 out.mkdir(parents=True,exist_ok=False)
 with tempfile.TemporaryDirectory(prefix="dsrom-completion-") as temp:
  t=Path(temp);(t/"source.sv").write_bytes(raw);(t/"tb.sv").write_bytes(tb)
  c=subprocess.run(["iverilog","-g2012","-s","tb","-o",str(t/"sim"),str(t/"tb.sv"),str(t/"source.sv")],capture_output=True,text=True)
  assert c.returncode==0,c.stderr
  r=subprocess.run(["vvp",str(t/"sim")],capture_output=True,text=True,timeout=15);assert r.returncode==0,r.stdout+r.stderr
 m=re.search(r"now_ps=(\d+) column_ps=(\d+) required_burst_complete_ps=(\d+)",r.stdout);assert m
 now,column,complete=map(int,m.groups());assert column<=now<complete
 receipt=dict(verdict="PASS_REPRODUCED_LEGACY_EARLY_COMPLETION",source_commit=PIN,source_path=SOURCE,source_sha256=hashlib.sha256(raw).hexdigest(),bench_sha256=hashlib.sha256(tb).hexdigest(),observed_done_and_visibility_ps=now,column_ps=column,CWL_ps=6250,burst_ps=1024,earliest_burst_completion_ps=complete,early_completion_ps=complete-now,persistent_KV_qualified=False,physical_latency_qualified=False,scope="One sector in unchanged simulation-only HBM model; excludes full mux/service/refresh/contention trajectory and physical hardware. Existing done signifies legacy column issue, not CWL+burst visibility.")
 (out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 (out/"compile.log").write_text(c.stdout+c.stderr);(out/"run.log").write_text(r.stdout+r.stderr);print(json.dumps(receipt))
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--out",type=Path,required=True);main(a.parse_args().out)
