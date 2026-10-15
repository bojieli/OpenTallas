#!/usr/bin/env python3
"""Build the ref-flow-1011 gate validation kits from today's jobs: the RTL / views AT THE JOB'S COMMIT are copied
into physical/ref_tile/<name>/src/ (so the kit routes exactly what the job routed), the outline from the job's port
contract (physical/s81_ph_views/ports/<die>/<master>/ports.json) or die area, pins 'auto' (in S, out N, clk/rst W).
    build_val.py            -> physical/ref_tile/val_*/ + tools/ref_tile/examples/val_*.json, then ref_tile.py gen
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
J = Path.home() / ".local/state/closure_loop/jobs"
CASES = [
    # name, expect, job, top, extra sources, die/master (s81 ports contract) or (w, h), clock, resets, macros
    ("val_bad_su9eff", "FAIL synth_smoke (yosys SHARE stall, 3.5 h in the loop)", "s81su-tkv0-9eff3d007-tc-pd45",
     "dsfd_su_t_kv0", ["rtl/dsrom_sys/s81_suhc/hier/dsfd_su_tiles.sv"], ("contract", "dsfd_su_t_kv0"), "ck", ["rst_n"], []),
    ("val_bad_ctile5db", "FAIL synth_smoke (yosys SHARE stall, 4 h+)", "s81hc-ctile-5db4c7ec6-tc-h900",
     "ot_s81_hc_ctile", ["rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctile.sv"], ("contract_hcc9", "ot_s81_hc_ctile"), "clk", ["rst_n"], []),
    ("val_bad_kvw", "FAIL textbook.high_fanout (port rn 3,418 loads; EARLY_FAIL_SETUP)", "hgi_dma_kvw_b-ebb3d0692-tc-cl",
     "ot_hgi_dma_kvw", ["rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw.sv"], (280.0, 280.0), "clk", [],
     [("physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2", 2)]),
    ("val_good_cbq0", "PASS/WARN (CLOSED TT +112 / FF +3.6)", "dsfd_coll_cbq0-cbh-bf0080873-tc-cl-p3",
     "dsfd_coll_cbq0", ["rtl/dsrom_sys/s81_ph/coll/dsfd_coll_cbh.sv"], ("contract_cbh", "dsfd_coll_cbq0"), "ck", ["rst_n"], []),
    ("val_good_clt6", "PASS/WARN (CLOSED; logic_depth 703 ps refuse-tier, WARN in the gate)", "s81vm-clt6-dc9e98d04-tc-rd",
     "dsfd_vm_clt", ["rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv"], ("contract_vm28", "dsfd_vm_clt"), "ck", ["rst_n"], []),
]


def show(commit, path):
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main():
    import re
    for name, expect, job, top, extra, geo, clk, rst, macros in CASES:
        j = json.loads((J / f"{job}.json").read_text())
        c, commit = j["spec"]["stages"]["route"]["cmd"], j["spec"]["source"]["commit"]
        m = re.search(r"SRCS='([^']*)'", c) or re.search(r'SRCS="([^"]*)"', c)
        srcs = (m.group(1).split() if m else []) + extra
        kd = ROOT / "physical/ref_tile" / name
        out = []
        for s in srcs:
            b = show(commit, s)
            if b is None:
                continue
            p = kd / "src" / s
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
            out.append(str(p.relative_to(ROOT)))
        if isinstance(geo[0], str):
            pj = json.loads(show(commit, f"physical/s81_ph_views/ports/{geo[0]}/{geo[1]}/ports.json"))
            w, h = pj["w_um"], pj["h_um"]
        else:
            w, h = geo
        # resets: whatever reset-named ports the top has
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import textbook_lint as TL
        mods = TL.rtl_modules([(ROOT / f).read_text(errors="replace") for f in out])
        dirs = TL.module_port_dirs(mods[top])
        rst = [p for p in dirs if re.fullmatch(r"(rst_n|rst|rn|reset_n|arst_n)", p)]
        spec = {"name": name, "top": top, "kind": "tile", "sources": out, "clock_port": clk, "reset_ports": rst,
                "outline": {"w": w, "h": h}, "pg_layer": "M6", "pins": "auto",
                "macros": [{"view": v, "count": n} for v, n in macros],
                "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 64},
                "validation": {"expect": expect, "job": job, "commit": commit},
                "job": {"owner": "Claude:ref-flow-1011", "branch": "claude/ref-flow-1011", "tag": "val",
                        "no_bench_reason": "gate validation only"}}
        p = ROOT / f"tools/ref_tile/examples/{name}.json"
        p.write_text(json.dumps(spec, indent=1) + "\n")
        print(name, top, len(out), "sources", w, "x", h, "->", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
