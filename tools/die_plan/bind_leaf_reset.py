"""Explicit wavefront reset gates for native soft leaves; default has no rules.

An anchor is a declared hard-core row, never inferred from a leaf spelling.
The canonical binder still chooses its nearest existing wavefront tap.
"""

def selected(rules, type_name, hard_cores):
    out=[]
    known={h["inst"] for h in hard_cores}
    for rule in rules or []:
        if rule.get("type") != type_name:
            continue
        if set(rule) != {"type", "module", "ports", "anchors"}:
            raise ValueError("leaf reset rule requires exact type/module/ports/anchors")
        if not isinstance(rule["module"], str) or not rule["module"]:
            raise ValueError("leaf reset module must be explicit")
        ports=rule["ports"];anchors=rule["anchors"]
        if not isinstance(ports,list) or not ports or len(set(ports)) != len(ports) or not all(isinstance(x,str) and x for x in ports):
            raise ValueError("leaf reset ports must be unique explicit names")
        if not isinstance(anchors,dict) or not anchors:
            raise ValueError("leaf reset anchors must be explicit")
        if any(not isinstance(k,str) or not k or v not in known for k,v in anchors.items()):
            raise ValueError("leaf reset anchor must name an existing hard core")
        out.append(rule)
    modules=[r["module"] for r in out]
    if len(set(modules)) != len(modules):
        raise ValueError("duplicate leaf reset module rule")
    return out


def resolve(rules, module, leaf, port):
    for rule in rules:
        if rule["module"]==module and port in rule["ports"]:
            if leaf not in rule["anchors"]:
                raise ValueError(f"leaf reset has no declared anchor for {module}/{leaf}")
            return rule["anchors"][leaf]
    return None
