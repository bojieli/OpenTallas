#!/usr/bin/env python3
"""Prepare PD2 on the complete pinned B2d3 event, with unresolved gates retained.

No partial transplantation from the obsolete 648-square bank plan. Produces a
candidate only; its seven core-face, epoch-source and PG/capacity blockers stay
open. Region and landing compose runs are deliberately separate from staging.
"""
import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from s81_phy_clock_keepouts import apply

PLAN = "physical/die_plan/s81/b2d3_0733/die_plan_b2d3.json.gz"
EVENT = "physical/die_plan/s81/b2d3_0733/event_ledger.json"


def stage(repo, rev, base_dir, out, density=False):
    out.mkdir(parents=True,exist_ok=False)
    def read(path):
        return subprocess.check_output(["git","-C",str(repo),"show",rev+":"+path])
    sha = subprocess.check_output(["git","-C",str(repo),"rev-parse",rev]).decode().strip()
    data = gzip.decompress(read(PLAN)); raw=json.loads(data); event=json.loads(read(EVENT))
    bk=next(p for p in raw["partitions"] if p["name"]=="bk_sel")
    typ=raw["partition_types"][bk["type"]]
    qs=[h for h in typ["hard_cores"] if ".g_q[" in h["inst"]]
    if len(qs)!=4 or any(h["outline_um"] != [864.0,483.84] for h in qs):
        raise ValueError("source is not the approved four-quarter R864 bank")
    if event.get("added_source_cycles")!=2 or not typ.get("internal_stations"):
        raise ValueError("source lacks the two-edge materialized bank transport")
    for p in base_dir.iterdir():
        if p.name in {"cores","core_conns.json"} or p.name.startswith("die_plan"):
            continue
        (out/p.name).symlink_to(p.resolve())
    cores=out/"cores";cores.mkdir()
    for p in (base_dir/"cores").iterdir():
        if p.name!="bksel_q_r864":(cores/p.name).symlink_to(p.resolve())
    qdir=cores/"bksel_q_r864";qdir.mkdir()
    for name in ["dsdv_bksel_q.json","dsdv_bksel_q.lef"]:
        (qdir/name).write_bytes(read("physical/die_plan/s81/cores/bksel_q_r864/"+name))
    (out/"core_conns.json").write_bytes(read("physical/die_plan/s81/b2d1_1026/core_conns_b2d1.json"))
    path=out/"die_plan_pd2_b2_candidate.json"
    raw,phy=apply(raw,path,density)
    path.write_text(json.dumps(raw,indent=1)+"\n")
    report=dict(status="CANDIDATE_NOT_BUILDABLE",source_rev=sha,source_plan=PLAN,
                source_sha256=hashlib.sha256(data).hexdigest(),parts=len(raw["partitions"]),
                types=len(raw["partition_types"]),bank_q_outline_um=[864,483.84],phy_clock=phy,
                preserved_blockers={k:event.get(k) for k in ["remaining_g0c_failures","epoch_source_blocker",
                  "capacity_blocker","additional_open_work"]},
                cycles="B2d3 existing +2 bank source edges preserved; PD2 landings and ROWX transport still require reprice")
    (out/"source_composition.json").write_text(json.dumps(report,indent=1)+"\n")
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--rev",default="12a0c04f0")
    ap.add_argument("--base-dir",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--density",action="store_true",help="use measured sink-density PHY candidate (15 taps, no empty drops)")
    a=ap.parse_args();r=stage(a.repo,a.rev,a.base_dir,a.out,a.density)
    print(json.dumps({k:v for k,v in r.items() if k not in ["phy_clock","preserved_blockers"]}))


if __name__=="__main__":main()
