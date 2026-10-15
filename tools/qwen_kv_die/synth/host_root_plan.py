#!/usr/bin/env python3
"""Stage the exact HOST root source and real SRAM views; never run synthesis.

The original 63-file rel.txt included simulation SRAM implementations from a
clock-loop testbench. Replace that file with canonical physical blackbox views
and pin matching TT liberty bytes from the selected immutable git revision.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = Path(__file__).with_name("host_root_original_rel.txt")
EXCLUDE = "rtl/hbm_accel/epilogue/tb_hbm_accel_clock_loops.sv"
TOP = "qkd_host_root_pt"
PARAMS = dict(NL=2, ENABLE_NATIVE=1, ENABLE_SERVICE=1, ENABLE_TOKEN=1)
MACROS = [
    ("physical/asap7_memory_macros", "ot_sram_1r1w_32x128_m1"),
    ("physical/asap7_memory_macros", "ot_sram_1r1w_1024x256_m2_r2c2"),
    ("physical/hbm_accel_macros", "ot_sram_1r1w_512x256_m1_r2c2"),
    # Required by the actual HOST peer-link s81ph SRAM wrapper.
    ("physical/asap7_memory_macros", "ot_sram_1r1w_512x128_m4_r2c2"),
]

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def modules(raw):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", raw.decode(), flags=re.S)
    return re.findall(r"\bmodule\s+(?:automatic\s+)?([A-Za-z_]\w*)", text)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--coordinator-lock", type=Path, required=True)
    ap.add_argument("--verilator", default="verilator")
    ap.add_argument("--lint", action="store_true", help="run Verilator frontend only; no synth")
    a = ap.parse_args()
    def guard():
        if json.loads(a.coordinator_lock.read_text())["owner"] != "codex":
            raise RuntimeError("COORD owner changed; stop")
    def call(argv):
        guard()
        return subprocess.run(argv, cwd=ROOT, capture_output=True)
    def git(*args):
        p = call(["git", *args])
        if p.returncode:
            raise RuntimeError(p.stderr.decode())
        return p.stdout
    revision = git("rev-parse", "--verify", a.revision+"^{commit}").decode().strip()
    rel = ORIGINAL.read_text().splitlines()
    if len(rel) != 63 or len(set(rel)) != 63 or rel.count(EXCLUDE) != 1:
        raise RuntimeError("original HOST source census differs")
    # Pin all 63 current source bytes, including the deliberately excluded bench.
    original = {p: git("show", revision+":"+p) for p in rel}
    files = {p: raw for p, raw in original.items() if p != EXCLUDE}
    physical = []
    for directory, name in MACROS:
        base = f"{directory}/{name}/{name}"
        bb, tt = base+"_bb.v", base+"_tt.lib"
        files[bb] = git("show", revision+":"+bb)
        files[tt] = git("show", revision+":"+tt)
        if modules(files[bb]) != [name] or b"blackbox" not in files[bb]:
            raise RuntimeError("canonical SRAM BB declaration differs: "+name)
        if not re.search(rb"cell\s*\(\s*"+name.encode()+rb"\s*\)", files[tt]):
            raise RuntimeError("actual TT library cell differs: "+name)
        physical.append(dict(module=name, blackbox=bb, tt_liberty=tt))
    owners = {}
    for path, raw in files.items():
        if path.endswith(".lib"):
            continue
        for module in modules(raw):
            if module in owners:
                raise RuntimeError("duplicate actual module "+module+": "+path+" / "+owners[module])
            owners[module] = path
    if TOP not in owners:
        raise RuntimeError("current HOST root module absent")
    out = a.out.resolve()
    if re.search(r"[\s;]", str(out)):
        raise RuntimeError("frontend output path must contain no whitespace or semicolon")
    def write(path, raw):
        guard();path.parent.mkdir(parents=True, exist_ok=True)
        guard();path.write_bytes(raw)
    for path, raw in files.items():
        write(out/"src"/path, raw)
    rtl = [str(Path("src")/p) for p in files if not p.endswith(".lib")]
    overrides = " ".join(f"-chparam {key} {value}" for key, value in PARAMS.items())
    frontend = "read_verilog -defer -sv "+" ".join(rtl)+"\n"+f"hierarchy -check -top {TOP} {overrides}\n"
    write(out/"frontend.ys", frontend.encode())
    libs = "\n".join(p["tt_liberty"] for p in physical)+"\n"
    write(out/"macro_tt_libraries.txt", libs.encode())
    manifest = dict(schema="opentallas.qwen-host-root-synthplan.v1", source_revision=revision,
        tool_sha256=digest(Path(__file__).read_bytes()),
        top=TOP, parameters=PARAMS, status="STAGED_STRICT_FRONTEND_REQUIRED", synthesis_executed=False,
        original_manifest=dict(path=str(ORIGINAL.relative_to(ROOT)), sha256=digest(ORIGINAL.read_bytes()),
            provenance="ssh ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-kvsys/hostsyn/rel.txt",count=63,
            current_source_sha256={p:digest(raw) for p,raw in original.items()}),
        excluded=[dict(path=EXCLUDE, reason="testbench simulation SRAM models; use canonical physical macros")],
        files_sha256={p:digest(raw) for p,raw in files.items()}, modules=owners, physical_macros=physical,
        frontend=dict(script="frontend.ys", sha256=digest(frontend.encode()),
            purpose="deferred actual parameter derivation and hierarchy check only; no synth/proc/mapping"),
        area=None, frame_fit=None,
        qualification="No area, physical fit, clock, timing or native parent qualification claim.")
    if a.lint:
        command=[a.verilator,"--lint-only","-Wno-fatal","--top-module",TOP,
            *[f"-G{key}={value}" for key,value in PARAMS.items()],
            *[str(out/p) for p in rtl]]
        p=call(command)
        log=p.stdout+p.stderr
        write(out/"verilator.log",log)
        errors=[line for line in log.decode().splitlines() if line.startswith("%Error")]
        absent=[line for line in errors if "Cannot find file containing module" in line or "MODNOTFOUND" in line or "MODMISSING" in line]
        version=call([a.verilator,"--version"]).stdout.decode().strip()
        warnings=Counter(line.split(":",1)[0] for line in log.decode().splitlines() if line.startswith("%Warning"))
        manifest["verilator"]=dict(command=command, version=version, exit_code=p.returncode, errors=errors, warnings=dict(warnings),
            absent_module_errors=absent, log_sha256=digest(log))
        manifest["status"]="PASS_VERILATOR_HIERARCHY_ONLY" if p.returncode==0 else "REFUSED_FRONTEND_ERRORS"
    write(out/"manifest.json",(json.dumps(manifest,indent=2)+"\n").encode())
    print(json.dumps({k:manifest[k] for k in ("status","source_revision","top","parameters","area")}))
    return 0 if manifest["status"]!="REFUSED_FRONTEND_ERRORS" else 2

if __name__=="__main__":
    raise SystemExit(main())
