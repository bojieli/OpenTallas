"""Insert engine-12 VM arm/fence commands using explicit operand ownership.

Bindings name every SU/HC job: {base_row, nrows, producers} or {give: true}.
Rows are whole 16-word VM rows. Producers are job IDs which write the armed
range. This compiler uses one counter slot at a time: the next arm waits for
the previous client job to finish. It rejects cycles rather than silently
allowing a producer to write before its range has been armed.
"""
from copy import deepcopy

VM_PORT = 12


def compact_arg(client, binding):
    if client not in ("su", "hc"):
        raise ValueError(f"invalid VM client {client}")
    if binding == {"give": True}:
        base16, count = 1023, 1023
    else:
        if set(binding) != {"base_row", "nrows", "producers"}:
            raise ValueError("operand binding requires base_row, nrows and producers, or give=true")
        base, nrows = binding["base_row"], binding["nrows"]
        if type(base) is not int or type(nrows) is not int:
            raise ValueError("VM rows must be integers")
        if base % 16 or not 0 <= base <= 16368 or not 1 <= nrows <= 1024 or base + nrows > 16384:
            raise ValueError("VM operand range must be aligned 16 rows and fit the 16384-row address space")
        base16, count = base // 16, nrows - 1
        if (base16, count) == (1023, 1023):
            raise ValueError("operand range collides with GIVE encoding")
        if not isinstance(binding["producers"], list) or not binding["producers"]:
            raise ValueError("armed range must name its producers; use GIVE for pre-existing operands")
    return (int(client == "hc") << 20) | (base16 << 10) | count


def insert_arms(program, bindings, npred=8, nops=128):
    """Return a topologically sorted program; never infer row addresses."""
    p = deepcopy(program)
    source = p["ops"]
    ids = [o["id"] for o in source]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate job ID")
    jobs = {o["id"]: o for o in source}
    expected = {o["id"] for o in source if o["eng"] in ("su", "hc")}
    if set(bindings) != expected:
        raise ValueError(f"operand bindings mismatch: missing={sorted(expected-set(bindings))} extra={sorted(set(bindings)-expected)}")
    deps = {o["id"]: {ids[i] for i in o["preds"]} for o in source}
    # Preserve in-order client consumption, not just data dependencies.
    previous = {}
    for o in source:
        old = previous.get(o["port"])
        if old:
            deps[o["id"]].add(old)
        previous[o["port"]] = o["id"]
    previous_client = None
    order = []
    for o in source:
        ident = o["id"]
        if ident in expected:
            binding = bindings[ident]
            arm = ident + ".vm_arm"
            if arm in jobs:
                raise ValueError(f"VM arm ID collision {arm}")
            arg = compact_arg(o["eng"], binding)
            jobs[arm] = dict(id=arm, eng="vm", port=VM_PORT, arg=arg, dur=1, ext=0,
                             client_job=ident, comp_cycles=0, comp_start=0)
            deps[arm] = {previous_client} if previous_client else set()
            deps[ident].add(arm)
            for producer in binding.get("producers", []):
                if producer not in deps or producer == ident:
                    raise ValueError(f"invalid producer {producer} for {ident}")
                deps[producer].add(arm)
            previous_client = ident
            order.append(arm)
        order.append(ident)
    if len(jobs) > nops:
        raise ValueError(f"{len(jobs)} commands exceed NOPS {nops}")
    sorted_ids, seen, visiting = [], set(), set()
    def visit(ident):
        if ident in visiting:
            raise ValueError(f"VM arm-before-write / single-slot ordering cycle at {ident}")
        if ident in seen:
            return
        visiting.add(ident)
        for pred in sorted(deps[ident]):
            visit(pred)
        visiting.remove(ident)
        seen.add(ident)
        sorted_ids.append(ident)
    for ident in order:
        visit(ident)
    indices = {ident: i for i, ident in enumerate(sorted_ids)}
    end = {}
    ops = []
    for ident in sorted_ids:
        o = jobs[ident]
        ps = sorted(indices[pred] for pred in deps[ident])
        if len(ps) > npred:
            raise ValueError(f"{ident} has {len(ps)} predecessors, exceeds {npred}")
        start = max([o["ext"]] + [end[pred] for pred in deps[ident]])
        end[ident] = start + o["dur"]
        o.update(op=indices[ident], preds=ps, start=start, end=end[ident])
        ops.append(o)
    p["priced_crit_end_before_vm_arms"] = p.get("crit_end")
    p.update(ops=ops, n_jobs=len(ops), crit_end=max(end.values(), default=0),
             max_start_drift=max((abs(o["start"] - o.get("comp_start", 0)) for o in ops if o["eng"] != "vm"), default=0), max_fanin=max((len(o["preds"]) for o in ops), default=0),
             makespan=max(end.values(), default=0), ports=sorted({o["eng"] for o in ops}),
             vm_arm_policy="single-slot; explicit producers; fenced before writes; client completion before reuse",
             vm_arm_max_live_slots=1, vm_arm_count=len(expected),
             vm_timing_scope="ASAP estimate only; native VM fence/landing latency must be measured")
    return p
