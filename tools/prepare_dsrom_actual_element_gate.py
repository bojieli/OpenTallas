#!/usr/bin/env python3
"""Generate pinned actual-element differential sources only. No build/run entry point."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'results/rtl/dsrom_actual_element_prepare_20261001/model.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def load_sources():
    model=json.loads(MODEL.read_text()); sources={}
    for path,pin in model['source_pins'].items():
        data=subprocess.check_output(['git','show',model['source_commit']+':'+path],cwd=ROOT)
        if sha(data)!=pin['sha256']: raise ValueError('pin mismatch: '+path)
        sources[path]=data.decode()
    return sources

def replace_helpers(text):
    for name,body in [('ot_v41_ksadd',"\n assign {cout,s} = {1'b0,a} + {1'b0,b} + {{W{1'b0}},cin};\n"),('ot_v41_inc',"\n assign {co,y} = {1'b0,a} + {{W{1'b0}},inc};\n")]:
        matches=list(re.finditer(r'\bmodule\s+'+name+r'\b.*?\bendmodule\b',text,re.S))
        if len(matches)!=1: raise ValueError('helper count: '+name)
        m=matches[0]; start=text.index(');',m.start())+2; end=text.index('endmodule',start)
        text=text[:start]+body+text[end:]
    return text

def namespace(text,names,prefix):
    # Lex identifiers only: preserve comments/strings/DPI names and INSTANCE keys.
    pattern=r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\b[A-Za-z_][A-Za-z_0-9$]*\b'
    return re.sub(pattern,lambda m:prefix+m[0] if m[0] in names else m[0],text,flags=re.S)

def generate(sources):
    names=set(re.findall(r'^\s*module\s+(\w+)', '\n'.join(sources.values()),re.M))
    files={}
    for side in ('ref_','cand_'):
        for path,original in sources.items():
            text=replace_helpers(original) if side=='cand_' and path=='rtl/common/ot_prefix.sv' else original
            files[side+Path(path).name]=namespace(text,names,side)
    return files

def prepare(out):
    if out.exists(): raise FileExistsError(out)
    model=json.loads(MODEL.read_text())
    for path,pin in model['new_artifact_pins'].items():
        if sha((ROOT/path).read_bytes())!=pin: raise ValueError('artifact pin mismatch: '+path)
    sources=load_sources(); files=generate(sources)
    for path in ('rtl/test/tb_dsrom_actual_element_gate.sv','rtl/test/dsrom_actual_element_rom.cpp'):
        files[Path(path).name]=(ROOT/path).read_text()
    out.mkdir(parents=True)
    for name,text in files.items(): (out/name).write_text(text)
    receipt=dict(status='PREPARED_NOT_EXECUTED',model_sha256=sha(MODEL.read_bytes()),files_sha256={n:sha((out/n).read_bytes()) for n in files},execution_gate='Parent GO required; no execution implemented',future_runner_requirements=['Verify source/bench/model/ROM hashes; fresh directory; never overwrite failures','One encompassing cgroup for all build children and both cases: MemoryMax=4294967296 MemorySwapMax=0 CPUQuota=200% plus affinity to two CPUs; no uncapped fallback','Build hard aggregate deadline 600s, simulation hard aggregate deadline 60s; watchdog SIGKILL whole cgroup at deadline; no retries','Compile V41_RT with pinned Verilator5.050 --binary --timing -j2, --top-module tb_q then tb_bfcolumn serially; link dsrom_actual_element_rom.cpp; keep actual ot_hdc_cg logic','Require PASS marker and every coverage assertion; preserve all logs/version/cgroup memory.peak and memory.events','Negative control after separate parent review: actual common adder bit flip must produce explicit differential mismatch, not arbitrary compile/crash failure','Finite two-state comparison only; no fullfield/golden/timing/rate/adoption credit'])
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();prepare(a.out)
