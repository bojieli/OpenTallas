"""Choose the existing insertion-band policy from the staged clock contract.

A promised core-tree model keeps its own policy.  An ordinary typed hard core
publishes measured insertion for compensation at its parent tap (COORD 10-24);
the partition insertion target is not an extra intrinsic-core constraint.
"""
import json
from pathlib import Path


def band_policy(kit):
    kit = Path(kit)
    path = kit / "master_slice.json"
    master = json.loads(path.read_text()) if path.is_file() else {}
    if "core_tree" in master:
        tree = master["core_tree"]
        if not isinstance(tree, dict):
            raise ValueError("invalid core_tree clock model")
        policy = tree.get("model_qualification", {}).get("band_policy", "gate")
        if policy not in ("gate", "info"):
            raise ValueError("invalid model_qualification band_policy")
        return policy
    import signoff
    return "info" if signoff.hard_core_latency_contract({"kit": str(kit)}) else "gate"
