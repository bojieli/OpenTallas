"""Selected DS L0 scalar/broadcast lowering; never supplies runtime data.

The emitted programme is a candidate until its VM-to-RF bridge is bound and
qualified. Input VM data are owned by prior producers; fixture O is check-only.
No internal rr_w* replay is a connected producer.
"""
from __future__ import annotations

from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle.native_profile import NativeTiming


def _fields():
    from su_arith_generate import FIELDS
    widths = dict(FIELDS)
    offsets = {}
    pos = 0
    for name, width in reversed(FIELDS):
        offsets[name] = pos
        pos += width
    def get(word, name):
        return (word >> offsets[name]) & ((1 << widths[name]) - 1)
    def put(word, name, value):
        if not 0 <= value < 1 << widths[name]:
            raise ValueError((name, value))
        mask = ((1 << widths[name]) - 1) << offsets[name]
        return (word & ~mask) | (value << offsets[name])
    return get, put


def lower_broadcast(raw, *, q, timing, rf_address, scalar_ready, rf_local,
                    place=None, data=None, tag="", su_options=None):
    """Compile VM scalar B -> RF class1 -> SU, with explicit ingress obligation.

    scalar_ready is the serial edge at which the real bridge presents rr_wv;
    qcore_r5 captures its input at +1 and commits at +2. Read starts at +3
    to avoid OLD-read overlap. rf_local is the actual selected slice parameter.
    Nonuniform strides remain refused; no lane arithmetic is emulated here.
    """
    import su_program_inventory as I
    if not isinstance(timing, NativeTiming):
        raise TypeError("explicit selected NativeTiming required")
    if not 0 <= rf_address < 256 or rf_local not in (0, 1) or scalar_ready < 0:
        raise ValueError("invalid RF slot/age")
    _, unit, sut, desc = I.decode(raw)
    b = desc.get("B")
    if unit != 2 or b is None or not b.ibcast or b.indexed or b.space != "VM":
        return dict(status="unlowered", reasons=["requires uniform VM B broadcast"])
    if b.m != 1 or sut["red"]:
        return dict(status="unlowered", reasons=["outer-varying broadcast/reducer calendar"])
    # The existing compiler emits A/C/D fills, arithmetic and O drains, while
    # refusing B's repeated non-sector addresses. Replace only that refusal.
    res = LI.su_record(raw, q=q, place=place, data=data, tag=tag, timing=timing, **(su_options or {}))
    allowed = lambda reason: (reason.startswith("operand B group ") or
                              reason == "operand B broadcast/strided: needs RF-broadcast (srcs) calendar")
    remaining = [r for r in res.get("reasons", []) if not allowed(r)]
    if remaining or "ql" not in res:
        return dict(status="unlowered", reasons=remaining or res.get("reasons", []))
    get, put = _fields()
    old = res["ql"]
    # Start after real RF capture/commit, and leave room for the leading read.
    shift = max(0, scalar_ready + 4 + rf_local - res["setup_edge"])
    ql = LI.QLine()
    for field, commands in old.f.items():
        ql.f[field] = {edge + shift: value for edge, value in commands.items()}
    for edge, word in list(ql.f["control"].items()):
        terms = get(word, "ld_c") & ~(((1 << 240) - 1) << 240)
        vb = (get(word, "vb") & ~(((1 << 24) - 1) << 24)) | (rf_address << 24)
        srcs = (get(word, "srcs") & ~(3 << 2)) | (1 << 2)
        ql.f["control"][edge] = put(put(put(word, "ld_c", terms), "vb", vb), "srcs", srcs)
    first = res["setup_edge"] + shift
    end = max(res["issue_edges"]) + shift + LI.FIRST_OUT
    # Match whole-top production compiler: RF class held across operation.
    for edge in range(first - 1 - rf_local, end + 1):
        ql.put("rf", edge, 9, 9, 256 | rf_address)
    # Backend controls remain live through arithmetic and drain; reserve them
    # exclusively, including zero-valued cycles (never OR another record).
    hold = ql.f["control"][first]
    hold = put(put(hold, "ld", 0), "emit", 0)
    last = res["last_commit"] + shift + 1
    for edge in range(first, last + 1):
        ql.f["control"].setdefault(edge, hold)
    # OLD-read correction: output DRAIN must follow lane SRAM write.
    ql.f["vmw"] = {e + 1: v for e, v in ql.f["vmw"].items()}
    expect = [dict(x, edge=x["edge"] + shift + 1) for x in res["expect"]]
    return dict(status="candidate_requires_binding", reasons=[], ql=ql,
                lines=ql.lines(), preload=res["preload"], expect=expect,
                commands=[dict(kind="vm_scalar_to_rf", source_word=b.base,
                               rf_address=rf_address, rr_wa=rf_address >> 3,
                               select_word=b.base & 7, quarter=q,
                               capture_serial_edge=scalar_ready,
                               producer="runtime VM read; no injected scalar")],
                vm_reads=[(s, e + shift) for s, e in res["fills"]] + [(b.base >> 3, None)],
                vm_writes=[(s, e + shift + 1) for s, e in res["drains"]],
                issue_edges=[e + shift for e in res["issue_edges"]],
                reservations=[dict(resource="SU_control", first=first, last=last),
                              dict(resource="RF_sector", address=rf_address >> 3,
                                   first=scalar_ready, last=last)],
                last_commit=last, inputs_placeholder=res["inputs_placeholder"],
                qualifies_native_layer=False, qualifies_native_chain=False,
                binding_obligations=["VM scalar producer -> RF ingress with reserved rr arbitration",
                                     "real scalar readiness and actual RF_LOCAL parameter",
                                     "native arithmetic/VM numerical witness"])


def runtime_gather(raw, *, timing):
    """Describe a runtime index read followed by A[base + I*dyn_mul].

    No index value or fixture-resolved A address is accepted by this API.
    The actual indexed descriptor, not captured fixture desc, is authoritative.
    """
    import su_program_inventory as I
    _, unit, sut, desc = I.decode(raw)
    a, index, out = (desc.get(k) for k in ("A", "I", "O"))
    if (unit != 2 or a is None or index is None or out is None or not a.indexed
            or any(x.space != "VM" for x in (a, index, out))):
        return dict(status="unlowered", reasons=["requires VM indexed scalar A/I/O"])
    if a.n != 1 or a.m != 1 or index.n != 1 or out.n != 1:
        return dict(status="unlowered", reasons=["only selected scalar gather interface implemented"])
    if not isinstance(timing, NativeTiming):
        raise TypeError("explicit selected NativeTiming required")
    return dict(status="candidate_requires_binding", commands=[
        dict(kind="runtime_indexed_scalar", index_word=index.base, source_base=a.base,
             index_multiplier=a.dyn_mul, destination_word=out.base,
             index_source="live IDX.TOPK VM write", output_source="live runtime VM read")],
        events=[], reservations=[dict(resource="VM_runtime_scalar", exclusive=True)],
        address_expression="source_base + U32(VM[index_word]) * index_multiplier",
        reasons=[], binding_obligations=["runtime VM scalar engine instantiated on selected VM calendar ports",
                                        "IDX.TOPK commit -> index read dependency",
                                        "masked output write with actual fixed return ages"],
        qualifies_native_layer=False, qualifies_native_chain=False)
