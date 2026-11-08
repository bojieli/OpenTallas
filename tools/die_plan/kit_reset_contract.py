"""Stage a die's proven reset contract into a fresh core kit (FLOW-KITFAIL-1 10-29).

lec.py reads KIT/reset_contract.json (lec.reset_contract_gate) to use the die's PROVEN reset length as the LEC reset
window of no-reset constant base cases; without the file every kit LEC runs at the 4-edge default.  The die contracts
exist (physical/die_plan/{hbm,s81,qwen_kvsys}/reset_contract.json, COORD 10-27 / OWNER 10-29), but only the S81
legacy generator staged them: in the 36 h to 2026-10-29 18:5x, 42 of 49 kit LEC FAILs ran at 4 edges, including HBM
tops listed in the HBM contract (hnx r12 NOT EQUIVALENT 34 at 4 edges -> r13 EQUIVALENT under the 64-edge contract).

stage(kd, module, source, required_source=False):
  * required_source=True refuses a missing canonical file; it grants no module/reset authority;
  * otherwise no contract file, or `module` not listed in it -> None, the kit is untouched (4-edge LEC as before);
  * listed -> the contract must pass the SAME consumer kit LEC runs (lec.reset_contract_gate: schema, PASS proof with a
    CAUGHT mutant, receipt sha256, module listed); a refusal is a generation error (fail closed, nothing staged);
  * then reset_contract.json + its relative receipt are byte-copied into the kit -> {edges, module, sha256s} for
    freeze.json.  Same rule as gen_core_kit_legacy.stage_reset_contract (S81, 7ef3ed13a), shared here.
  * KW-FIX-35-RC 11-08: verify_staged() re-reads the KIT copy through the same gate after the copy (receipt present,
    sha256 equal, window granted); repair(KIT) re-stages a receipt a kit copy dropped (S81 bksel vJ/vK), no rebuild.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]
DIE_CONTRACT = {d: REPO / "physical/die_plan" / d / "reset_contract.json" for d in ("hbm", "s81", "s81_head", "qwen_kvsys", "qwen_compute")}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stage(kd, module, source, *, required_source=False):
    source = Path(source)
    if not source.is_file():
        if required_source:
            raise SystemExit(f"{module}: required canonical die reset contract is missing: {source}; "
                             "stage the contract metadata and receipt, or select an explicit nonrelease component proof")
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
    verify_staged(kd, module, edges=report["used"])
    return dict(edges=report["used"], module=module, die=c.get("die"), contract=str(source),
                contract_sha256=_sha(source), receipt_sha256=_sha(source.parent / receipt))


def verify_staged(kd, module, edges=None):
    """KW-FIX-35-RC 11-08: a staged kit must hold reset_contract.json AND its receipt (sha256 as recorded), and kit
    LEC's own gate, reading the kit alone, must grant the contract window to `module`.  Called by every stager after
    the copy; a kit that would LEC at the 4-edge default is a generation error, never a quiet fallback."""
    kd = Path(kd)
    if str(TOOL) not in sys.path:
        sys.path.insert(0, str(TOOL))
    import lec
    env = {}
    rep = lec.reset_contract_gate(kd, module, environ=env)
    if rep.get("refused") or (edges is not None and rep["used"] != edges):
        raise SystemExit(f"{module}: staged reset contract in {kd} does not verify "
                         f"({rep.get('refused') or 'window ' + str(rep['used']) + ' != ' + str(edges)})")
    return rep


def repair(kd, source=None):
    """Re-stage a kit's missing reset receipt from the die contract (no rebuild; the kit RTL/netlist is untouched).
    The kit's reset_contract.json must be byte-equal to the source contract, or at least carry the same receipt
    sha256 (a later contract revision that only lists more modules); the receipt copied in must hash to that value.
    New file only: an existing receipt path is unlinked first (kits may be hardlinked copies). -> report dict."""
    kd = Path(kd)
    kc_path = kd / "reset_contract.json"
    kc = json.loads(kc_path.read_text())
    if source is None:
        if kc.get("die") not in DIE_CONTRACT:
            raise SystemExit(f"{kd}: contract die {kc.get('die')!r} has no canonical source; pass --source")
        source = DIE_CONTRACT[kc["die"]]
    source = Path(source)
    sc = json.loads(source.read_text())
    want = kc["proof"]["receipt_sha256"]
    if sc["proof"].get("receipt_sha256") != want:
        raise SystemExit(f"{kd}: kit contract receipt sha {want[:12]} != source {source} "
                         f"{str(sc['proof'].get('receipt_sha256'))[:12]}")
    receipt = Path(kc["proof"]["receipt"])
    if receipt.is_absolute() or ".." in receipt.parts:
        raise SystemExit(f"{kd}: reset receipt must stay relative to the staged contract")
    src_r = source.parent / sc["proof"]["receipt"]
    if _sha(src_r) != want:
        raise SystemExit(f"{src_r}: receipt sha256 differs from the contract")
    dst = kd / receipt
    before = _sha(dst) if dst.is_file() else None
    if before != want:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        shutil.copyfile(src_r, dst)
    if str(TOOL) not in sys.path:
        sys.path.insert(0, str(TOOL))
    import lec
    top = lec.parse_config(str(kd))["DESIGN_NAME"] if (kd / "config.mk").is_file() else None
    rep = verify_staged(kd, top) if top in kc.get("modules", []) else None
    return dict(kit=str(kd), top=top, source=str(source), receipt=str(dst), receipt_sha256=want,
                copied=before != want, contract_sha256=_sha(kc_path), source_contract_sha256=_sha(source),
                contract_byte_equal=_sha(kc_path) == _sha(source), used=rep["used"] if rep else None)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="repair: re-stage a kit's reset contract receipt (KW-FIX-35-RC)")
    ap.add_argument("cmd", choices=("repair", "verify"))
    ap.add_argument("kit")
    ap.add_argument("--source", help="die reset_contract.json (default: the canonical one for the kit contract's die)")
    a = ap.parse_args()
    if a.cmd == "repair":
        print(json.dumps(repair(a.kit, a.source)))
    else:
        if str(TOOL) not in sys.path:
            sys.path.insert(0, str(TOOL))
        import lec
        top = lec.parse_config(a.kit)["DESIGN_NAME"]
        print(json.dumps(verify_staged(a.kit, top)))
