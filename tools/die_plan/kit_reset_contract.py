"""Stage a die's proven reset contract into a fresh core kit (FLOW-KITFAIL-1 10-29).

lec.py reads KIT/reset_contract.json (lec.reset_contract_gate) to use the die's PROVEN reset length as the LEC reset
window of no-reset constant base cases; without the file every kit LEC runs at the 4-edge default.  The die contracts
exist (physical/die_plan/{hbm,s81,qwen_kvsys}/reset_contract.json, COORD 10-27 / OWNER 10-29), but only the S81
legacy generator staged them: in the 36 h to 2026-10-29 18:5x, 42 of 49 kit LEC FAILs ran at 4 edges, including HBM
tops listed in the HBM contract (hnx r12 NOT EQUIVALENT 34 at 4 edges -> r13 EQUIVALENT under the 64-edge contract).

stage(kd, module, source):
  * no contract file, or `module` not listed in it -> None, the kit is untouched (4-edge LEC as before);
  * listed -> the contract must pass the SAME consumer kit LEC runs (lec.reset_contract_gate: schema, PASS proof with a
    CAUGHT mutant, receipt sha256, module listed); a refusal is a generation error (fail closed, nothing staged);
  * then reset_contract.json + its relative receipt are byte-copied into the kit -> {edges, module, sha256s} for
    freeze.json.  Same rule as gen_core_kit_legacy.stage_reset_contract (S81, 7ef3ed13a), shared here.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]
DIE_CONTRACT = {d: REPO / "physical/die_plan" / d / "reset_contract.json" for d in ("hbm", "s81", "qwen_kvsys")}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stage(kd, module, source):
    source = Path(source)
    if not source.is_file():
        return None
    try:
        c = json.loads(source.read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"{module}: unreadable die reset contract {source}: {e}")
    if module not in c.get("modules", []):
        return None
    if str(TOOL) not in sys.path:
        sys.path.insert(0, str(TOOL))
    import lec
    report = lec.reset_contract_gate(source.parent, module, environ={"OT_LEC_RESET_CONTRACT": str(source)})
    if report.get("refused"):
        raise SystemExit(f"{module}: die reset contract {source} refused: {report['refused']}")
    receipt = Path(c["proof"]["receipt"])
    if receipt.is_absolute() or ".." in receipt.parts:
        raise SystemExit(f"{module}: reset receipt must stay relative to the staged contract")
    kd = Path(kd)
    (kd / receipt).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source.parent / receipt, kd / receipt)
    shutil.copyfile(source, kd / "reset_contract.json")
    return dict(edges=report["used"], module=module, die=c.get("die"), contract=str(source),
                contract_sha256=_sha(source), receipt_sha256=_sha(source.parent / receipt))
