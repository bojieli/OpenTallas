"""Source-qualified V-CTL injection timing shared by compiler and replay.
Unversioned historical programmes retain six edges. XR2 adds its registered
classify stage; a new programme must name a qualified RTL SHA, also checked
against the reused simulator source inventory before a replay can PASS.
"""
import hashlib
from pathlib import Path

XR_PATH = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv"
QUALIFIED = {"cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3": 7}

def source_contract(tree, fallback):
    p = Path(tree) / XR_PATH
    if not p.exists(): p = Path(fallback) / XR_PATH
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha not in QUALIFIED:
        raise ValueError("unqualified XR injection timing for RTL SHA " + sha)
    return dict(xr_source_sha256=sha, v_ctl_inject=QUALIFIED[sha],
                basis="rstop iv/dl_vb -> xr vb/classify/ci_r -> rstop ci_q/ro: 7 registered edges")

def inject_cycles(schedule):
    c = schedule.get("timing_contract")
    if c is None: return 6   # byte-compatible interpretation of archived programmes
    sha = c.get("xr_source_sha256")
    if sha not in QUALIFIED or c.get("v_ctl_inject") != QUALIFIED[sha]:
        raise ValueError("unqualified or inconsistent XR timing contract")
    return c["v_ctl_inject"]

def check_run_source(contract, run):
    if contract is None: return
    inject_cycles({'timing_contract': contract})
    p = Path(run) / "sources.sha256"
    inventory = [line.split() for line in p.read_text().splitlines()]
    actual = {parts[0] for parts in inventory if len(parts) == 2 and parts[1].endswith(XR_PATH)}
    if actual != {contract["xr_source_sha256"]}:
        raise ValueError("replay XR timing contract does not match simulator sources: " + str(actual))
