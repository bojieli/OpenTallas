"""Bounded connected SU lowering for the selected DS q_norm.ss record.

Only commands and pre-operation VM operands enter the DUT. Numerical products,
subtrees and R below are reference-only; no reducer operand or RF word is seeded.
The entire1280-word reduction runs on one real quarter, with its changed cost
reported explicitly. Full connected numerical qualification belongs to the caller.
"""
from __future__ import annotations

import hashlib
import math
import numpy as np


def lower(raw, q=0, rng=None, data=None, place=None, tag="", pad_zero=False,
          timing=None, expected_reduction_word=None, **unused):
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    from su_arith_compile import pack, physical_word
    import su_pretree_lower as PT
    from hdc_golden import mul

    _, unit, sut, desc = decode(raw)
    refusal = lambda why: dict(status="unsupported_lowering", reasons=[why], sut=sut,
                              lowering=dict(supported=False, owner="SU-LAYER-1021"))
    profile = dict.fromkeys(sut, 0)
    profile.update(red=1, red_sq=1, red_tree=1)
    if unit != 2 or sut != profile or set(desc) != {"A", "R"}:
        return refusal("bounded_sum_of_squares_A_to_R_profile_only")
    a, r = desc["A"], desc["R"]
    if (a.space != "VM" or a.fmt != "FP32" or a.n != 160 or a.m != 8
            or a.stride != 160 or (a.istride or 1) != 1 or a.base % 8
            or any(getattr(a, x) for x in ("lstride", "dyn_sel", "dyn_mul", "n_sel",
                                          "l1stride", "ibcast", "indexed"))):
        return refusal("bounded_1280_contiguous_FP32_operand_required")
    if (r.space != "VM" or r.fmt != "FP32" or r.n != 1 or r.m != 1
            or r.base % 8 or r.indexed or r.ibcast):
        return refusal("bounded_single_aligned_VM_R_destination_required")
    if q != 0:
        return refusal("bounded_complete_reduction_owned_by_quarter0")
    if timing != NativeTiming(18, 15):
        return refusal("selected_native_READ_RETURN18_WRITE_RETURN15_required")
    if data is None:
        return refusal("real_pre_operation_VM_words_required")
    addresses = list(range(a.base, a.base + 1280))
    missing = [x for x in addresses if x not in data]
    if missing:
        return refusal("missing_real_operand_words:" + str(len(missing)))
    before = np.asarray([data[x] for x in addresses], dtype=np.float32)
    if not np.isfinite(before).all():
        return refusal("bounded_finite_operand_profile_required")
    input_bits = before.view(np.uint32).copy()
    # Independent expected arithmetic, never encoded as a DUT operand.
    squared = np.asarray(mul(before, before), np.float32).view(np.uint32)
    if not np.isfinite(squared.view(np.float32)).all():
        return refusal("bounded_finite_square_profile_required")
    want = PT.golden("sum", squared)
    if expected_reduction_word is not None:
        supplied = int(expected_reduction_word, 16) if isinstance(expected_reduction_word, str) else int(expected_reduction_word)
        if supplied != want:
            raise ValueError("independent csum8 disagrees with authentic downstream R reference")

    class Lines(LI.QLine):
        def __init__(self):
            super().__init__()
            self.f["tree"] = {}

        def lines(self):
            end = max([max(x) for x in self.f.values() if x] or [0])
            values = []
            for edge in range(end + 1):
                word = self.f["control"].get(edge, 0)
                for key, width in (("vmr", 240), ("vmw", 312), ("rf", 54), ("red", 74)):
                    word = (word << width) | self.f[key].get(edge, 0)
                values.append(word | (self.f["tree"].get(edge, 0) << 2422))
            return values

    ql = Lines()
    place = place if place is not None else LI.Placement(q)
    fills, preload, reads = [], {}, []
    next_fill = [0] * 8
    for block in range(10):
        for sector in range(16):
            first = a.base + 128 * block + 8 * sector
            logical = first // 8
            port = sector % 8
            physical = place.get(logical, port, tag + ":A")
            if physical % 8 != port:
                return refusal("operand_VM_port_placement_conflict")
            edge = next_fill[port]
            next_fill[port] += 1
            ql.vmr(edge, port, physical, sector, block)
            fills.append((logical, edge))
            words = list(range(first, first + 8))
            reads.append(dict(logical_sector=logical, physical_sector=physical,
                              edge=edge, words=words, local_row=block, group=sector))
            if logical not in place.written:
                preload[physical] = words
    # Reads are issued only after every local fill has committed (including an
    # OLD-read guard); setup and all1280 operand identities are explicit.
    fill_last = max(edge for _, edge in fills) + timing.fill_commit
    setup = fill_last + 1
    first_issue = setup + 8
    # Existing selected lane profile: setup->lane result36 serial edges,
    # hence emit->result28; tree samples one edge after publication.
    issue_to_tree = LI.FIRST_OUT - LI.SETUP_TO_EMIT + 1
    tree_first = first_issue + issue_to_tree
    rf_addr = r.base & 255
    schedule = PT.Schedule()
    schedule.lower("sum", squared, 0x100 | rf_addr, tree_first)
    # Map the existing structural pair-first emission order to actual VM rows.
    block_edges = {}
    npairs = 5
    for pair in range(npairs):
        block_edges[tree_first + pair] = 2 * pair
        block_edges[tree_first + pair + PT.DEP] = 2 * pair + 1
    if set(block_edges) != set(schedule.tree):
        raise ValueError("pre-tree scheduler emission contract changed")
    # All four semantic readers qualify; point unused B/C/D readers at live A.
    terms = 0
    for role in range(4):
        for bit in range(7):
            terms |= (1 << bit) << (24 * (10 * role + bit))
    base = dict(no=1, ni=1280, ls=7, lvw=7, srcs=0, dst=0, co_dst=0,
                ld_c=terms, cp_m1=2, cm_m1=2)
    issue_edges, operand_events = [], []
    for tree_edge, block in sorted(block_edges.items()):
        edge = tree_edge - issue_to_tree
        row_address = physical_word(q, block)
        vb = sum(row_address << (24 * role) for role in range(4))
        ql.f["control"][edge] = pack(dict(base, emit=1, i_v=128 * block, vb=vb))
        ql.f["tree"][tree_edge] = PT.tree_cmd_word(0, 128)
        issue_edges.append(edge)
        operand_events.append(dict(block=block, issue_edge=edge, tree_edge=tree_edge,
                                   first_logical_word=a.base + 128 * block,
                                   words=128, local_row=block,
                                   arithmetic="real_lane_AA_FP32", tree_groups=[0, 1, 2, 3]))
    ql.f["control"][setup] = pack(dict(base, ld=1))
    ready = {}
    for edge, command in sorted(schedule.red.items()):
        op = command["op"]
        read = ([command["a"], command["b"]] if op in (2, 5)
                else [command["a"]] if op in (1, 3, 4) else [])
        if any(ready.get(addr, math.inf) > edge for addr in read):
            raise ValueError("reducer SRAM RAW reservation violated")
        ql.f["red"][edge] = PT.red_cmd_word(command)
        if op != 4:
            ready[command["d"]] = edge + PT.DEP
    export_edge, export_tag, schedule_want = schedule.exps[-1]
    if schedule_want != want:
        raise ValueError("lowered csum8 graph differs from independent reference")
    root = schedule.red[export_edge]["a"]
    # Selected die stree: leaf up + 14 up relays + root in/out +
    # 14 down relays + leaf down = 32 sampled stages. The older generic
    # su_red_carry_calendar is fixed to a different 36-stage RF route.
    rf_relay = 32
    rf_commit = export_edge + 12 + rf_relay + 1
    rf_plan = dict(events=[dict(kind="export", quarter=q,
        command_serial=export_edge, scalar_capture_serial=export_edge + 12,
        rf_write_pins_serial=export_edge + 12 + rf_relay,
        rf_commit_serial=rf_commit)])
    # Guard the RF SRAM OLD-read edge, then RF_LOCAL1 requires class5
    # exactly two edges ahead of the VM RF-sector drain.
    rf_read = rf_commit + 2
    drain_edge = rf_read + 2
    ql.put("rf", rf_read, 5 * 9, 9, 0x100 | (rf_addr & ~7))
    logical_r = r.base // 8
    physical_r = place.get(logical_r, 0, tag + ":R")
    if physical_r % 8:
        return refusal("RF_sector_drain_requires_VM_port0_placement")
    ql.vmw(drain_edge, 0, 1, 0, 0, physical_r, 1 << (rf_addr & 7))
    commit = drain_edge + timing.drain_done
    hold = pack(base)
    for edge in range(commit + 1):
        ql.f["control"].setdefault(edge, hold)
    lines = ql.lines()
    if len(lines) > LI.EDGES_MAX:
        return refusal("native_programme_capacity_exceeded")
    place.written.add(logical_r)
    pre_words = {str(addr): f"{int(bits):08x}" for addr, bits in zip(addresses, input_bits)}
    expected = [None] * 8
    expected[rf_addr & 7] = want
    return dict(status="emitted", reasons=[], ql=ql, lines=lines, fills=fills,
        drains=[(logical_r, commit)], preload=preload,
        data=pre_words, inputs_placeholder=False,
        expect=[dict(sector=physical_r, mask=1 << (rf_addr & 7), edge=commit,
                     words=list(range(r.base, r.base + 8)), value=expected)],
        setup_edge=setup, issue_edges=issue_edges, last_commit=commit,
        fill_sectors=len(preload), drain_sectors=1,
        sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, words=1280, issue_groups=10,
            execution_qualified=False, owner="SU-LAYER-1021", mode="single_quarter_serialized",
            source="su_pretree_lower + actual lane AA + selected stree RF calendar"),
        quarter_ownership=dict(quarter=q, words=1280, complete_record=True,
                               external_quarter_partial_values_injected=False),
        command_width=2470, tree_width=48,
        source_contract=dict(command_low_bits=2422,
            tree_group_fields=[[2422 + 12*g, 2433 + 12*g] for g in range(4)],
            selected_die="r15phaseall/die.v", selected_qcore="sucore_SW",
            RF_route="stl_SW.up -> stu_SW_00..13 -> str_C -> std_SW_00..13a/b -> stl_SW.rf_w* -> sucore_SW.rf_w*",
            RF_stage_counts=dict(leaf_up=1, up_relays=14, root=2,
                                 down_relays=14, leaf_down=1),
            RF_external_drive=False, collective_rr_external_drive=False,
            stage_definition="rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_stree.sv"),
        operand_events=operand_events,
        reducer_commands=[dict(edge=e, **c) for e, c in sorted(schedule.red.items())],
        rf_events=rf_plan["events"] + [dict(kind="class5_read", edge=rf_read, addr=rf_addr & ~7),
            dict(kind="RF_to_VM_drain", edge=drain_edge, vm_commit=commit)],
        read_footprint=reads,
        write_footprint=[dict(logical_word=r.base, logical_sector=logical_r,
                              physical_sector=physical_r, mask=1, edge=commit)],
        expected_post_state={str(r.base): f"{want:08x}"},
        expected_post_state_only=True,
        input_sha256=hashlib.sha256(input_bits.tobytes()).hexdigest(),
        expected_reference=dict(value=f"{want:08x}", role="comparison_only",
                                source="independent csum8(mul(original A,A)); downstream k10.A"),
        control_reservation=dict(first=0, last=commit, policy="exclusive_record"),
        timing_obligations=dict(issue_to_tree=issue_to_tree, tree_to_red=PT.PT_RED,
            reducer_RAW=PT.DEP, RF_relay=rf_relay, RF_export_to_commit=12 + rf_relay + 1,
            RF_LOCAL=1, serial_edges=commit + 1,
            stream_edges=math.ceil(4 * (commit + 1) / 3),
            old_price_preserved=False, connected_selected_case_RTL_required=True))
