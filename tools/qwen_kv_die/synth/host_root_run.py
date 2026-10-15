#!/usr/bin/env python3
"""Run the immutable HOST root mapped-area candidate in ORFS; no physical claim.

Parent admission: 64 GiB / 2 threads. Docker limit: 60 GiB / 2 CPUs.
Preparation verifies every staged source/library SHA before creating scripts.
Execution requires --execute; this tool never changes RTL or replaces SRAMs.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

IMAGE="openroad/orfs:asap7lock"
TOP="qkd_host_root_pt"

def sha(raw):return hashlib.sha256(raw).hexdigest()

def cell_blocks(text):
    # Standard library cell blocks copied byte-for-byte into a single library.
    text=re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    result=[]
    for match in re.finditer(r"\bcell\s*\(\s*([^()]+?)\s*\)\s*\{",text):
        depth=1;end=match.end()
        for token in re.finditer(r'"(?:[^"\\]|\\.)*"|[{}]',text[end:]):
            if token.group()=="{":depth+=1
            elif token.group()=="}":depth-=1
            if depth==0:
                end+=token.end();break
        else:raise ValueError("unbalanced Liberty cell")
        result.append((match.group(1).strip('"'),text[match.start():end]))
    if not result:raise ValueError("no actual Liberty cells")
    return text,result

def report(out,plan,manifest,scale):
    generic=json.loads((out/"generic.json").read_text())["modules"][TOP]
    mapped=json.loads((out/"mapped.json").read_text())["modules"][TOP]
    clk_names={}
    for name,port in generic["ports"].items():
        if port["direction"]=="input":
            for n,bit in enumerate(port["bits"]):
                clk_names.setdefault(bit,name if len(port["bits"])==1 else f"{name}[{n}]")
    for name,net in sorted(generic["netnames"].items(),key=lambda v:len(v[0])):
        for n,bit in enumerate(net["bits"]):clk_names.setdefault(bit,f"{name}[{n}]")
    clocks=Counter();flops=Counter();latches=Counter()
    for cell in generic["cells"].values():
        typ=cell["type"]
        if typ.startswith(("$_DFF","$_SDFF")):
            bits=cell["connections"].get("C")
            if not bits or len(bits)!=1:raise ValueError("unresolved actual FF clock: "+typ)
            clocks[clk_names.get(bits[0],str(bits[0]))]+=1;flops[typ]+=1
        elif typ.startswith("$_DLATCH"):latches[typ]+=1
    stdareas={}
    for name,block in cell_blocks((out/"lib/all.lib").read_text())[1]:
        area=re.search(r"\barea\s*:\s*([0-9.eE+-]+)\s*;",block)
        if area:stdareas[name]=float(area.group(1))
    macroareas={};macrocounts={}
    for macro in manifest["physical_macros"]:
        name=macro["module"]
        block=dict(cell_blocks((plan/"src"/macro["tt_liberty"]).read_text())[1])[name]
        macroareas[name]=float(re.search(r"\barea\s*:\s*([0-9.eE+-]+)\s*;",block).group(1))
        macrocounts[name]=sum(c["type"]==name for c in mapped["cells"].values())
    std=Counter();unknown=Counter()
    for cell in mapped["cells"].values():
        typ=cell["type"]
        if typ in macroareas:continue
        if typ not in stdareas:unknown[typ]+=1
        else:std[typ]+=1
    if unknown:raise ValueError("unmapped/unknown actual cells: "+json.dumps(unknown))
    stdraw=sum(stdareas[t]*n for t,n in std.items())
    macroarea=sum(macroareas[t]*n for t,n in macrocounts.items())
    total=stdraw*scale+macroarea;frame=777.6*518.4
    result=dict(status="MAPPED_SOURCE_AREA_ONLY",qualified=False,source_revision=manifest["source_revision"],
        parameters=manifest["parameters"],standard_cell_count=sum(std.values()),macro_cell_count=sum(macrocounts.values()),
        macro_counts=macrocounts,macro_cell_area_um2=macroareas,standard_area_raw_library_units=stdraw,
        standard_library_area_scale_to_um2=scale,standard_area_um2=stdraw*scale,macro_area_um2=macroarea,total_cell_area_um2=total,
        frame_um=[777.6,518.4],frame_area_um2=frame,cell_area_over_frame=total/frame,
        ff_count=sum(flops.values()),ff_by_clock=dict(clocks),generic_ff_types=dict(flops),generic_latch_types=dict(latches),
        standard_library_sha256={p.name:sha(p.read_bytes()) for p in (out/"lib").glob("*.lib")},
        area_units="Canonical physical macro Liberty area uses um2 (scale1). RVT_TT standard-library area multiplied by explicit scale argument (default1 for ASAP7 1x area). No implicit dbu/LEF scale conversion.",
        limitations=["Cell area only; no placement/utilization/routing/clock-tree area","No timing, clock-phase, native bench or whole-HOST qualification","Original frontend diagnostics remain explicit in input manifest"])
    (out/"area.json").write_text(json.dumps(result,indent=2)+"\n")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan",type=Path,required=True);ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--coordinator-lock",type=Path)
    ap.add_argument("--stdlib-area-scale-to-um2",type=float,default=1.0)
    ap.add_argument("--execute",action="store_true");ap.add_argument("--inside-container",action="store_true")
    a=ap.parse_args();plan=a.plan.resolve();out=a.out.resolve()
    def guard():
        if a.coordinator_lock and json.loads(a.coordinator_lock.read_text())["owner"]!="codex":raise RuntimeError("COORD changed")
    def write(path,text):
        guard();path.parent.mkdir(parents=True,exist_ok=True);guard();path.write_text(text)
    def run(cmd,log,cwd=None):
        guard();p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
        write(log,p.stdout+p.stderr);return p
    manifest=json.loads((plan/"manifest.json").read_text())
    if manifest["top"]!=TOP or manifest["parameters"]!={"NL":2,"ENABLE_NATIVE":1,"ENABLE_SERVICE":1,"ENABLE_TOKEN":1}:raise ValueError("wrong actual root parameters")
    if manifest["status"]!="PASS_VERILATOR_HIERARCHY_ONLY":raise ValueError("actual Verilator hierarchy proof required")
    for path,digest in manifest["files_sha256"].items():
        if sha((plan/"src"/path).read_bytes())!=digest:raise ValueError("source bytes changed: "+path)
    if len(manifest["physical_macros"])!=4:raise ValueError("all four real physical macro views required")
    if a.stdlib_area_scale_to_um2<=0:raise ValueError("positive explicit standard area scale required")
    if not a.inside_container:
        image=IMAGE
        if a.execute:
            guard();probe=subprocess.run(["docker","image","inspect","--format","{{.Id}}",IMAGE],capture_output=True,text=True)
            if probe.returncode or not probe.stdout.strip().startswith("sha256:"):raise RuntimeError("cannot pin actual ORFS image ID")
            image=probe.stdout.strip()
        command=["docker","run","--rm","--cpus=2","--memory=60g","-e","OMP_NUM_THREADS=2",
            "-v",str(plan)+":/plan:ro","-v",str(out)+":/out","-v",str(Path(__file__).resolve())+":/host_root_run.py:ro",
            "-w","/plan",image,"bash","-lc",
            'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec python3 /host_root_run.py --inside-container --plan /plan --out /out --stdlib-area-scale-to-um2 "$1"',
            "host_root_run",str(a.stdlib_area_scale_to_um2)]
        write(out/"run_plan.json",json.dumps(dict(command=command,runner_sha256=sha(Path(__file__).read_bytes()),
            source_manifest_sha256=sha((plan/"manifest.json").read_bytes()),admission_gib=64,docker_gib=60,threads=2,executed=a.execute),indent=2)+"\n")
        if a.execute:
            p=run(command,out/"docker.log")
            if p.returncode:raise RuntimeError("actual mapped synth failed; inspect docker.log and per-step logs")
        return
    # Actual RVT_TT standard cells from the pinned ORFS image. No cell stubs.
    libroot=Path("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM")
    stems=["AO_RVT_TT_nldm_211120","INVBUF_RVT_TT_nldm_220122","OA_RVT_TT_nldm_211120","SIMPLE_RVT_TT_nldm_211120","SEQ_RVT_TT_nldm_220123"]
    libraries=[]
    for stem in stems:
        path=libroot/("asap7sc7p5t_"+stem+".lib")
        raw=path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+".gz").read_bytes())
        libraries.append(raw.decode());write(out/"lib"/(stem+".lib"),raw.decode())
    header,first=cell_blocks(libraries[0]);prefix=header[:header.index(first[0][1])]
    combined=prefix+"\n"+"\n".join(block for text in libraries for _,block in cell_blocks(text)[1])+"\n}\n"
    write(out/"lib/all.lib",combined)
    write(out/"lib/seq.lib",libraries[-1])
    rtl=[str(plan/"src"/p) for p in manifest["files_sha256"] if p.endswith((".sv",".v"))]
    for path in [*rtl,str(out)]:
        if re.search(r"[\s;]",path):raise ValueError("unsupported Yosys path whitespace/semicolon")
    read="read_verilog -defer -sv -DSYNTHESIS "+" ".join(rtl)+"\n"
    params=" ".join(f"-chparam {k} {v}" for k,v in manifest["parameters"].items())
    front=read+f"hierarchy -check -top {TOP} {params}\n"
    write(out/"frontend.ys",front)
    p=run(["yosys","-Q","-T","-s",str(out/"frontend.ys")],out/"frontend.log")
    if p.returncode:raise RuntimeError("strict deferred actual root frontend failed")
    # Derive the ACTUAL native-engine source at invalid native geometries.
    negatives=[]
    for name,qp,kv in [("wrong_qpipe",1,2),("wrong_kvhmax",2,8)]:
        script=read+f"hierarchy -check -top qkd_host_native_engine -chparam NATIVE_ROWS 1 -chparam HDMAX 128 -chparam QPIPE {qp} -chparam KVHMAX {kv}\n"
        write(out/(name+".ys"),script)
        p=run(["yosys","-Q","-T","-s",str(out/(name+".ys"))],out/(name+".log"))
        log=p.stdout+p.stderr
        if p.returncode==0 or ("$fatal" not in log and "native ingest requires full32-macro QPIPE2 provider" not in log):
            raise RuntimeError("actual native source guard negative did not fail specifically")
        negatives.append(dict(case=name,exit_code=p.returncode,log_sha256=sha(log.encode())))
    write(out/"source_guard_negatives.json",json.dumps(negatives,indent=2)+"\n")
    stats=" ".join("-liberty "+str(plan/"src"/m["tt_liberty"]) for m in manifest["physical_macros"])
    script=front+f"synth -top {TOP} -flatten\nwrite_json {out}/generic.json\n"+f"dfflibmap -liberty {out}/lib/seq.lib\nabc -liberty {out}/lib/all.lib\nopt_clean\ncheck\nwrite_json {out}/mapped.json\n"+f"tee -o {out}/mapped.stat stat -liberty {out}/lib/all.lib {stats}\n"
    write(out/"mapped.ys",script)
    p=run(["yosys","-Q","-T","-s",str(out/"mapped.ys")],out/"mapped.log")
    if p.returncode:raise RuntimeError("actual mapped synthesis failed")
    report(out,plan,manifest,a.stdlib_area_scale_to_um2)

if __name__=="__main__":main()
