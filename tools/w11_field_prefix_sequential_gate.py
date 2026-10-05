#!/usr/bin/env python3
"""Bounded three-leaf sequential integration gate; no live source substitution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import time
ROOT = Path(__file__).resolve().parents[1]
PIN = "4e38326d6f361bc85e660f48c59c355e2bb95274"
SOURCES = {'rtl/common/ot_prefix.sv': '01de55a0d8c474008eb4446e41e00788d466b5dfb2e2e8d85a0b70ff931f8cfc', 'rtl/hdc/ot_hdc_delay.sv': '7b37c18daacc0e2c592dc3acf1e65e2225a69697a39de9c1e4d2fc22421cb688', 'rtl/v41rom/ot_v41_bmul2.sv': '15015cbd92c76526298c6647561f530499ee678e7bbe656bcc689fa40bb7c1e6', 'rtl/v41rom/ot_v41_bterm.sv': 'f682643c486d2bd9f2725f780bec982e3495b02ce52450bec07e7e892b05053b', 'rtl/v41rom/ot_v41_bterm2_w10.sv': 'c0ce5e3c2590bb74682a0217f2b4faf98545ff61fbb7e319796d30b21970a32e', 'rtl/v41rom/ot_v41_fadd.sv': 'ba36ce3f0a3605c1ea5cad6aabf5fef09220637cdaef9a8a5f1bf3ff1b33f504'}
TB = "rtl/test/tb_w11_field_prefix_sequential_gate.sv"
HARNESS = "rtl/test/w11_field_prefix_sequential_gate.cpp"
TOOL = "tools/w11_field_prefix_sequential_gate.py"
TEST = "tests/test_w11_field_prefix_sequential_gate.py"
SEEDS = (0x12345678, 0x9e3779b9, 0xc001d00d)
ADD = "    assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};\n"
INC = "    assign {co, y} = {1'b0, a} + {{W{1'b0}}, inc};\n"
def digest(raw): return hashlib.sha256(raw).hexdigest()
def pinned_sources():
    out = {}
    for path, expected in SOURCES.items():
        raw = subprocess.check_output(["git", "show", PIN + ":" + path], cwd=ROOT)
        if digest(raw) != expected: raise ValueError("source pin mismatch: " + path)
        out[path] = raw.decode()
    return out

def replace_body(text, name, body):
    start = text.index("module " + name + " ")
    signature_end = text.index(");\n", start) + 3
    end = text.index("endmodule", signature_end)
    return text[:signature_end] + body + text[end:]

def substitute(text):
    return replace_body(replace_body(text, "ot_v41_ksadd", ADD), "ot_v41_inc", INC)

def namespace(text, names, prefix):
    pattern = re.compile(r"\b(?:" + "|".join(map(re.escape, names)) + r")\b")
    return pattern.sub(lambda m: prefix + m[0], text)

def generated(sources, variant="candidate"):
    if variant not in ("reference", "candidate", "carry_mutant", "increment_mutant", "mul_sum_mutant", "reset_mutant"):
        raise ValueError("unknown variant")
    names = [n for s in sources.values() for n in re.findall(r"^\s*module\s+(\w+)", s, re.MULTILINE)]
    if len(names) != len(set(names)): raise ValueError("duplicate modules")
    texts = dict(sources)
    if variant != "reference": texts["rtl/common/ot_prefix.sv"] = substitute(texts["rtl/common/ot_prefix.sv"])
    if variant == "carry_mutant":
        texts["rtl/common/ot_prefix.sv"] = texts["rtl/common/ot_prefix.sv"].replace(ADD, ADD.replace("{{W{1'b0}}, cin}", "{(W+1){1'b0}}"))
    if variant == "increment_mutant":
        texts["rtl/common/ot_prefix.sv"] = texts["rtl/common/ot_prefix.sv"].replace(INC, INC.replace("{{W{1'b0}}, inc}", "{(W+1){1'b0}}"))
    if variant == "mul_sum_mutant":
        texts["rtl/common/ot_prefix.sv"] = texts["rtl/common/ot_prefix.sv"].replace(ADD, ADD.replace(";", " ^ {{W{1'b0}}, (W == 12)};"))
    if variant == "reset_mutant":
        # Deliberately bad consumer reset is a negative control, NOT the candidate.
        p = "rtl/v41rom/ot_v41_fadd.sv"
        old = "y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;"
        if texts[p].count(old) != 1: raise ValueError("reset mutant shape changed")
        texts[p] = texts[p].replace(old, old.replace("32'd0", "32'd1"))
    prefix = "field_ref_" if variant == "reference" else "field_sim_"
    return {p: namespace(s, names, prefix) for p, s in texts.items()}

def limited_child(): resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
def run_command(command, log, timeout):
    started = time.monotonic()
    with log.open("x") as stream:
        child = subprocess.Popen(["/usr/bin/time", "-v", *command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                 preexec_fn=limited_child, start_new_session=True)
        try: rc = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL); child.wait()
            raise RuntimeError("bounded command timed out: " + str(log))
    rss=re.search(r"Maximum resident set size \(kbytes\): (\d+)",log.read_text())
    return dict(command=command, returncode=rc, max_rss_kib=int(rss[1]) if rss else None, elapsed_seconds=round(time.monotonic()-started,3),
                log=str(log), log_sha256=digest(log.read_bytes()))

def resources(work_parent):
    mem = {l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.split(':')[0] in ('MemAvailable','MemTotal')}
    disk = shutil.disk_usage(work_parent);load = os.getloadavg()
    check = dict(memory=mem, disk_free_bytes=disk.free, load_average=list(load), workers=2,
                 child_address_space_bytes=4*1024**3, build_timeout_seconds=180, simulation_timeout_seconds=30)
    if mem['MemAvailable']<16*1024**3 or disk.free<2*1024**3 or load[0]>64:
        raise RuntimeError("insufficient bounded local resource headroom")
    return check

def run_gate(work, output, random_cycles=8192):
    work=work.resolve();output=output.resolve()
    if work.exists() or output.exists(): raise ValueError("fresh work and record required; failed verdicts never overwritten")
    if not 1<=random_cycles<=32768: raise ValueError("random-cycle cap 1..32768")
    src=pinned_sources(); preflight=resources(work.parent)
    work.mkdir();output.parent.mkdir(parents=True,exist_ok=True)
    record=dict(schema="opentallas.w11.field_prefix_sequential_gate.v1",status="RUNNING",source_commit=PIN,
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256=SOURCES,gate_sha256={p:digest((ROOT/p).read_bytes()) for p in (TB,HARNESS,TOOL,TEST)},
                preflight=preflight,simulator=subprocess.check_output(['verilator','--version'],text=True).strip(),
                compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                parameters=dict(fadd_CUT=379,fadd_LAT=8,bmul_LAT=5,bterm_TW=17,bterm_LAT=11),
                seeds=list(SEEDS),random_cycles_per_seed=random_cycles,runs=[],
                candidate_change="Only common ot_v41_ksadd/inc bodies replaced with W+1-bit additions; all modules namespaced. Consumer and CSA/delay text exact after reversing namespace.",
                semantics="Verilator two-state default-zero unreset state, identical both sides; compare ALL leaf outputs on every clock and every asynchronous reset, including invalid payload/errors/unreset tags. Independent valid LAT8/11 and unreset tag LAT11 scoreboards; bmul LAT5 checked by directed fault/payload and bubble fault masking (no valid output port).",
                formal_common_prefix_required_separately=True,formal_owner="Hubble",sequential_formal_proof=False,
                all_input_equivalence=False,golden_arithmetic_qualification=False,field_wrapper_qualification=False,
                full_die_qualification=False,live_substitution=False,adoption=False,hardware_credit=False)
    names=[n for s in src.values() for n in re.findall(r'^\s*module\s+(\w+)',s,re.MULTILINE)]
    ref=generated(src,'reference');candidate=generated(src)
    # Enforce inverse namespace identity for all unchanged consumer/dependency files.
    for p,s in candidate.items():
        back=s
        for n in names: back=re.sub(r'\bfield_sim_'+re.escape(n)+r'\b',n,back)
        if back != (substitute(src[p]) if p=='rtl/common/ot_prefix.sv' else src[p]):
            raise ValueError('candidate changed outside helper bodies: '+p)
    def write_set(directory, texts):
        directory.mkdir();paths=[]
        for p,s in texts.items():
            target=directory/Path(p).name;target.write_text(s);paths.append(str(target))
        return paths
    reference_files=write_set(work/'reference',ref)
    try:
        for variant in ('candidate','carry_mutant','increment_mutant','mul_sum_mutant','reset_mutant'):
            vd=work/variant;files=write_set(vd,generated(src,variant))
            entry=dict(variant=variant,generated_sha256={p:digest(s.encode()) for p,s in generated(src,variant).items()},simulations=[])
            record['runs'].append(entry)
            command=['verilator','--cc','--exe','--build','-j','2','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT','-Wno-UNUSED',
                     '--top-module','tb_w11_field_prefix_sequential_gate','--prefix','Vgate','-Mdir',str(vd/'obj'),
                     *reference_files,*files,str(ROOT/TB),str(ROOT/HARNESS),'-CFLAGS','-O1 -std=c++17']
            entry['build']=run_command(command,vd/'build.log',180)
            if entry['build']['returncode']: raise RuntimeError('build failed: '+variant)
            for seed in SEEDS if variant=='candidate' else SEEDS[:1]:
                simulation=run_command([str(vd/'obj/Vgate'),str(seed),str(random_cycles)],vd/('seed_'+str(seed)+'.log'),30)
                results=[l[7:] for l in Path(simulation['log']).read_text().splitlines() if l.startswith('RESULT ')]
                if len(results)!=1: raise RuntimeError('missing structured simulation verdict')
                simulation['result']=json.loads(results[0]);entry['simulations'].append(simulation)
                wanted='PASS' if variant=='candidate' else 'FAIL';rc=0 if variant=='candidate' else 1
                if simulation['returncode']!=rc or simulation['result']['status']!=wanted: raise RuntimeError('unexpected verdict: '+variant)
                expected_property={'carry_mutant':'fadd_tuple_every_sample','increment_mutant':'bterm_tuple_every_sample',
                                   'mul_sum_mutant':'bmul_tuple_every_sample','reset_mutant':'fadd_tuple_every_sample'}
                if variant!='candidate' and simulation['result']['first_mismatch']['property']!=expected_property[variant]:
                    raise RuntimeError('mutant failed for unrelated reason')
        if pinned_sources()!=src: raise RuntimeError('reference pins changed')
        record['status']='PASS_BOUNDED_DIRECTED_RANDOM_SEQUENTIAL_GATE'
    except Exception as exc:
        record['status']='FAIL';record['error']=str(exc);raise
    finally:
        with output.open('x') as f: f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--random-cycles',type=int,default=8192);a=p.parse_args();print(run_gate(a.work,a.output,a.random_cycles)['status'])
