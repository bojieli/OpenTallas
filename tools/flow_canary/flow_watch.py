"""Which changed paths count as a FLOW change for one die (shared by canary_gate, autopilot provenance and trigger).

A path is a flow change for die D when it matches canaries.json "watch", matches no "watch_exclude" (tests, docs,
test data, examples, systemd units, evidence logs, the canary spec itself), and -- when it lies under a die plan tree
physical/die_plan/<P>/ -- P is one of D's own plan trees ("die_plans").  Another die's plan files never hold a row:
AUTOPILOT-FIX 10-25 21:22, a qwen_kvsys/cores/harden edit held every frozen QC and S81-HEAD row as "flow changed".
die=None (no die known) or a die missing from "die_plans" keeps every die plan tree (fail closed).
"""
import fnmatch

PLAN_ROOT = "physical/die_plan/"


def _plan_dirs(spec, die):
    if die is None:
        return None
    plans = (spec.get("die_plans") or {}).get(die)
    return None if plans is None else set(plans)


def flow_paths(paths, spec, die=None):
    """sorted unique paths of `paths` that are flow changes for `die` under canaries.json `spec`"""
    watch = spec.get("watch") or []
    exclude = spec.get("watch_exclude") or []
    own = _plan_dirs(spec, die)
    out = set()
    for p in paths:
        if not any(fnmatch.fnmatch(p, w) for w in watch) or any(fnmatch.fnmatch(p, x) for x in exclude):
            continue
        if own is not None and p.startswith(PLAN_ROOT) and p[len(PLAN_ROOT):].split("/", 1)[0] not in own:
            continue
        out.add(p)
    return sorted(out)


# Ignore only known metadata/admission fields. Any future implementation field
# stays in the contract automatically rather than silently bypassing the gate.
REFERENCE_METADATA = {"why", "golden", "mem_gb", "threads"}

def reference_contract(spec, die):
    item = next((c for c in spec.get("canaries", []) if c.get("die") == die), None)
    if item is None:
        return None
    return {key: value for key, value in item.items() if key not in REFERENCE_METADATA}

def spec_flow_changed(before, after, die):
    """Unknown references stay conservative; resource/baseline edits are not flow edits."""
    a, b = reference_contract(before, die), reference_contract(after, die)
    if a is None or b is None:
        return True
    ignored = {"canaries", "die_plans", "note"}
    extra_a = {k: v for k, v in before.items() if k not in ignored}
    extra_b = {k: v for k, v in after.items() if k not in ignored}
    return a != b or extra_a != extra_b or before.get("watch") != after.get("watch") or \
        before.get("watch_exclude") != after.get("watch_exclude") or \
        _plan_dirs(before, die) != _plan_dirs(after, die)
