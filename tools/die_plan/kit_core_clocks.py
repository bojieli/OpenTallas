"""Wire planned early-core clocks into the actual kit-only bound leaf pins.

The source bind remains unchanged. Each declared clock input has a real child
clock consumer before synthesis, preserving the planned ABI without keep cells.
"""
import re

def wire(bound, module, rows):
    ports = {}
    receipt = []
    consumers = set()
    for port, physical_inst, pin, _early, _insertion in rows:
        if pin == "*":
            raise ValueError(f"core clock {port}: explicit clock pin required")
        # The plan wrapper owns u_bound. Physical specialization may name it;
        # otherwise the binder's native leaf instances have their standard u_ prefix.
        candidates = ([physical_inst[len("u_bound."):]] if physical_inst.startswith("u_bound.")
                      else [physical_inst, "u_" + physical_inst])
        if all("." in local for local in candidates):
            # DIE-S81-47 svcrs 11-01: a core nested below the bound leaf (S81 svc attn hcores u_rsv.u_att...u_c) has no
            # bound-level instance to rewire in RTL text.  The plan port is still declared, and the CP2 early-core tap
            # form moves the core's clock pin onto it in the synthesized netlist (clock_taps.tcl, OT_CORE_TAPS =
            # core_taps.txt).  Leaf cores keep the RTL connection below.
            if port in ports and ports[port] != "input":
                raise ValueError(f"core clock {port}: conflicting port")
            if (physical_inst, pin) in consumers:
                raise ValueError(f"core clock {port}: duplicate consumer {physical_inst}.{pin}")
            consumers.add((physical_inst, pin))
            ports[port] = "input"
            receipt.append(dict(port=port, instance=physical_inst, pin=pin, previous_net=None,
                                hookup="netlist: clock_taps.tcl OT_CORE_TAPS"))
            continue
        found = []
        for local in candidates:
            if "." in local:
                continue
            pat = re.compile(r"^[ \t]+\w+(?:[ \t]+#\([^\n]*\))?[ \t]+" +
                             re.escape(local) + r"[ \t]*\(", re.M)
            found.extend((local, h) for h in pat.finditer(bound))
        if len(found) != 1:
            raise ValueError(f"core clock {port}: expected one bound leaf {physical_inst}, got {len(found)}")
        local, h = found[0]
        body_start = h.end()
        depth, body_end = 1, body_start
        while depth and body_end < len(bound):
            if bound[body_end] == "(":
                depth += 1
            elif bound[body_end] == ")":
                depth -= 1
            body_end += 1
        if depth:
            raise ValueError(f"core clock {port}: unclosed instance {local}")
        body_end -= 1
        original_body = bound[body_start:body_end]
        conn = re.compile(r"(\." + re.escape(pin) + r"\s*\()([^()]+)(\))")
        matches = list(conn.finditer(original_body))
        if len(matches) != 1:
            raise ValueError(f"core clock {port}: expected one {local}.{pin} connection")
        if (local, pin) in consumers:
            raise ValueError(f"core clock {port}: duplicate consumer {local}.{pin}")
        consumers.add((local, pin))
        prior = matches[0].group(2).strip()
        if port in ports and ports[port] != "input":
            raise ValueError(f"core clock {port}: conflicting port")
        ports[port] = "input"
        body = conn.sub(lambda m: m.group(1) + port + m.group(3), original_body, count=1)
        bound = bound[:body_start] + body + bound[body_end:]
        receipt.append(dict(port=port, instance=local, pin=pin, previous_net=prior))
    if ports:
        header = re.compile(r"(\bmodule\s+" + re.escape(module) + r"\s*(?:#\(.*?\)\s*)?\(\n)", re.S)
        if len(list(header.finditer(bound))) != 1:
            raise ValueError(f"core clocks: ambiguous header for {module}")
        declarations = "".join(f"    input wire {p},  // planned early-core clock\n" for p in ports
                               if not re.search(r"^\s*input\s+(?:wire\s+)?" + re.escape(p) + r"\s*[,)]", bound, re.M))
        bound = header.sub(lambda m: m.group(1) + declarations, bound, count=1)
    return bound, receipt
