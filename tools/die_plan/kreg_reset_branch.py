"""Place-aware nested reset copies without changing registered assertion or release age."""
import re
from collections import defaultdict

from reset_consumers import _calls


class KregBranchError(ValueError):
    pass


IDENTIFIER = re.compile(r"[a-zA-Z_]\w*\Z")


def _name(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise KregBranchError(f"invalid reset branch name {value!r}")
    return value


def _port(instance, pin):
    row = instance["ports"].get(pin)
    if row is None:
        raise KregBranchError(f"missing reset branch port {pin}")
    return row


def _kreg(calls, name):
    inst = calls.get(_name(name))
    if inst is None or inst["module"] != "ot_hdc_v41x_kreg":
        raise KregBranchError(f"{name} does not name a native KREG")
    params = re.sub(r"\s+", "", inst["params"] or "")
    if params not in (".R(1),.W(1)", ".W(1),.R(1)") or _port(inst, "d")[0] != "1'b1":
        raise KregBranchError(f"{name} is not an asynchronous one-bit release register")
    return inst


def _source(expr, scalar, aliases):
    # The native flattened RTL sometimes fans one scalar out through a vector
    # concatenation before selecting a static bit. Every selected term must be
    # the same scalar before the consumer may use a same-edge replica.
    def unindexed(value):
        return re.sub(r"\[0\]$", "", value.strip())
    if unindexed(expr) == scalar:
        return True
    match = re.fullmatch(r"(\w+)\[(\d+)\]", expr)
    rows = aliases.get(match[1], ()) if match else ()
    if len(rows) != 1:
        return False
    terms = rows[0].strip("{}").split(",")
    return int(match[2]) < len(terms) and all(unindexed(term) == scalar for term in terms)


def apply(text, spec):
    names = _calls(text)
    root_name = spec["driver"]
    root = _kreg(names, root_name)
    old_input = _port(root, "rst_n")[0]
    if old_input != spec["expected_reset_input"]:
        raise KregBranchError(f"{root_name} reset input differs from the declared parent event")
    clock = _port(root, "clk")[0]
    _name(clock)
    scalar = _name(_port(root, "q")[0])
    root_net = f"{scalar}[0]"
    symbols = {root_name: root_net}
    edits = []
    created = []
    used = set(names)
    existing_words = set(re.findall(r"\b[A-Za-z_]\w*\b", text))
    aliases = defaultdict(list)
    for net, alias in re.findall(r"(?m)^\s*assign\s+(\w+)\s*=\s*([^;]+);", text):
        aliases[net].append(alias.strip())

    def append(name, module, connection):
        name = _name(name)
        if name in used or name+"_q" in existing_words:
            raise KregBranchError(f"reset branch symbol already exists: {name}")
        used.add(name)
        output = name+"_q"
        created.extend((f"    wire {output};",
                         f"    (* keep, dont_touch *) {module} {name} ({connection}, .{'Y' if module.startswith('BUF') else 'q'}({output}));"))
        return output

    for branch in spec["branches"]:
        name = branch["name"]
        if branch["parent"] not in symbols:
            raise KregBranchError(f"{name} has a missing or forward reset branch parent")
        parent = symbols[branch["parent"]]
        symbols[name] = append(name, "BUFx4f_ASAP7_75t_R", f".A({parent})")

    drivers = {}
    for entry in spec["local_drivers"]:
        name = entry["name"]
        inst = _kreg(names, name)
        old, lo, hi = _port(inst, "rst_n")
        if name in drivers or old not in (scalar, root_net) or _port(inst, "clk")[0] != clock:
            raise KregBranchError(f"{name} no longer shares the declared native reset and clock")
        parent = symbols.get(entry["branch"])
        if parent is None:
            raise KregBranchError(f"{name} has no declared reset branch")
        drivers[name] = _name(_port(inst, "q")[0])
        edits.append((lo, hi, parent))

    consumers = set()
    for replica in spec["replicas"]:
        name = replica["name"]
        driver = replica["old_driver"]
        parent = symbols.get(replica["branch"])
        if parent is None or driver not in drivers or not replica["sinks"]:
            raise KregBranchError(f"{name} has no validated native driver/branch/sinks")
        output = append(name, "ot_hdc_v41x_kreg #(.R(1), .W(1))",
                        f".clk({clock}), .d(1'b1), .rst_n({parent})")
        for sink in replica["sinks"]:
            target = _name(sink["inst"])
            inst = names.get(target)
            if target in consumers or inst is None or inst["module"] != sink["module"]:
                raise KregBranchError(f"{target} is an ambiguous or changed hard reset sink")
            old, lo, hi = _port(inst, "rst_n")
            if not _source(old, drivers[driver], aliases):
                raise KregBranchError(f"{target} no longer consumes reset from {driver}")
            edits.append((lo, hi, output))
            consumers.add(target)
    end = list(re.finditer(r"(?m)^\s*endmodule\b", text))
    if len(end) != 1:
        raise KregBranchError("expected one selected bound module")
    at = end[0].start()
    edits.append((at, at, "\n"+"\n".join(created)+"\n"))
    for lo, hi, replacement in sorted(edits, reverse=True):
        text = text[:lo]+replacement+text[hi:]
    return text, {
        "form": "kreg_branch",
        "driver": root_name,
        "copies": len(spec["replicas"]),
        "transparent_branches": len(spec["branches"]),
        "consumers": len(consumers),
        "unchanged_registered_cycles": True,
    }
