#!/usr/bin/env python3
"""KV-CORES 10-24: give a core kit generated before befed6a747 the typed core contract that newer kits carry
(KIT/core.json with boundary_role + clock_contract hard_core_latency, KIT/boundary_guard_context.json), written by the
SAME gen_core_kit_kv.write_core_contract from the core's kv_core_rtl.py record.  No RTL / SDC / netlist / timing change:
the files only declare which ports are clocks / unused clock aliases / resets (face_guard skips them; data pins still
need their boundary registers) and that the core publishes its measured insertion (COORD 10-24 ruling).
Refuses when the kit's freeze.json clocks differ from the record's clock ports (wrong record).

    retrofit_contract.py KITDIR CORE_RTL_JSON
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_kv as g  # noqa: E402


def main():
    kd, cjp = Path(sys.argv[1]), Path(sys.argv[2])
    cj = json.loads(cjp.read_text())
    fz = json.loads((kd / "freeze.json").read_text())
    clks, rsts = g.core_clocks_resets(cj)
    if fz.get("module") != cj.get("module") or sorted(fz.get("clocks") or []) != sorted(clks):
        raise SystemExit(f"retrofit: kit {fz.get('module')} clocks {fz.get('clocks')} != record {cj.get('module')} {clks}")
    for f in ("core.json", "boundary_guard_context.json"):
        if (kd / f).exists():
            raise SystemExit(f"retrofit: {kd / f} exists (kit already typed)")
    g.write_core_contract(kd, cj, clks, rsts)
    (kd / "contract_retrofit.json").write_text(json.dumps(dict(
        tool="retrofit_contract.py (KV-CORES 10-24)", core_rtl_json=str(cjp), clocks=clks, resets=rsts), indent=1) + "\n")
    print(json.dumps(dict(kit=str(kd), clocks=clks, resets=len(rsts))))


if __name__ == "__main__":
    main()
