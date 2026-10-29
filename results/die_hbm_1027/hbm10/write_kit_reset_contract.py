"""DIE-HBM-10 (COORD f6eced6f9, FLOW-GEN-2 (c) mechanism): write KIT/reset_contract.json per HBM kit from the die
sequencer proof (physical/die_plan/hbm/reset_contract.json + receipt, branch claude/die-hbm-10-rst-1028).
Each kit gets modules = [its own DESIGN_NAME] (only if the die contract lists it) and a byte copy of the receipt, then
the kit is checked with lec.reset_contract_gate itself (must report used = 64, no refusal).
usage: write_kit_reset_contract.py REPO DIE_CONTRACT KIT [KIT ...]  -> one line per kit"""
import json, re, shutil, sys
from pathlib import Path
repo, dc, kits = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
sys.path.insert(0, str(repo / "tools/die_plan"))
import lec  # noqa: E402
C = json.loads(dc.read_text()); rc = dc.parent / C["proof"]["receipt"]
for k in map(Path, kits):
    m = re.search(r"^\s*export\s+DESIGN_NAME\s*\??=\s*(\S+)", (k / "config.mk").read_text(), re.M)
    top = m and m.group(1)
    if top not in C["modules"]:
        print(f"SKIP {k} top={top} (not in the die contract)"); continue
    kc = dict(C, modules=[top], kit_note=f"per-kit copy of {dc.name} (die hbm, DIE-HBM-10); receipt byte copy")
    (k / "reset_contract").mkdir(exist_ok=True)
    shutil.copyfile(rc, k / "reset_contract/receipt.txt")
    (k / "reset_contract.json").write_text(json.dumps(kc, indent=1) + "\n")
    rep = lec.reset_contract_gate(str(k), top, environ={})
    ok = rep["used"] == C["edges"] and "refused" not in rep
    print(("OK  " if ok else "FAIL"), k, top, "used", rep["used"], rep.get("refused", ""))
