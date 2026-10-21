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


def lower_norm_rs(raw, q=0, data=None, place=None, tag="", timing=None,
                  side_profile=None, side_source_path=None, any_immediates=False, **unused):
    """One scalar FULL-lane operation; require the repaired selected side ABI.

    side_profile is source provenance supplied by the integrator, never a DUT
    input. The old selected fixed3/3 SIDE is explicitly unsupported at lane4/3.
    """
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    from su_arith_compile import pack, physical_word
    from hdc_golden import add, rsqrt, z
    _, unit, sut, desc = decode(raw)
    refusal = lambda why: dict(status="unsupported_lowering", reasons=[why], sut=sut,
                              lowering=dict(supported=False, owner="SU-LAYER-1021"))
    profile = dict.fromkeys(sut, 0)
    profile.update(m1=5, ad=4, sfu=2, dst=1, imm1=1151336448, imm2=507307272)
    if any_immediates:      # TOK-FUNC2-HBM-SU: same datapath, the record's own immediates in cp/cm_imm1 / ca_imm2
        profile.update(imm1=sut["imm1"], imm2=sut["imm2"])
    if unit != 2 or sut != profile or set(desc) != {"A", "O"}:
        return refusal("bounded_scalar_divimm_addimm_rsqrt_profile_only")
    if q != 0:
        return refusal("rsqrt_requires_selected_quarter0_FULL_lane0")
    if side_profile != (4, 3):
        return refusal("actual_selected_SIDE_MLAT4_ALAT3_source_required_old_fixed3_3_mismatches9edges")
    from pathlib import Path
    if side_source_path is None:
        return refusal("actual_scoped_SIDE_source_path_required")
    try:
        scoped = Path(side_source_path).read_text()
    except OSError:
        return refusal("actual_scoped_SIDE_source_unreadable")
    side_decl = "module ot_hbm_su_static_side__d4g_pgslice #(parameter integer MUT=0, MLAT=3, ALAT=3) ("
    side_call = "ot_hbm_su_static_side__d4g_pgslice #(.MLAT(MLAT), .ALAT(ALAT)) u_side("
    if scoped.count(side_decl) != 1 or scoped.count(side_call) != 1:
        return refusal("actual_scoped_SIDE_parameters_not_propagated")
    if timing != NativeTiming(18, 15):
        return refusal("selected_native_READ_RETURN18_WRITE_RETURN15_required")
    for md in desc.values():
        if (md.space != "VM" or md.fmt != "FP32" or md.n != 1 or md.m != 1
                or md.base % 8 or any(getattr(md, k) for k in
                ("stride", "istride", "lstride", "dyn_sel", "dyn_mul", "n_sel",
                 "l1stride", "ibcast", "indexed"))):
            return refusal("bounded_aligned_single_scalar_VM_descriptor_required")
    a, o = desc["A"], desc["O"]
    if data is None or a.base not in data:
        return refusal("actual_pre_operation_scalar_A_word_required")
    x = np.float32(data[a.base])
    if not np.isfinite(x):
        return refusal("finite_scalar_operand_required")
    imm1 = np.uint32(sut["imm1"]).view(np.float32)
    imm2 = np.uint32(sut["imm2"]).view(np.float32)
    with np.errstate(all="ignore"):
        argument = add(z(np.float32(x / imm1)), imm2)
        expected = np.float32(rsqrt(argument))
    if not np.isfinite(expected):
        return refusal("finite_rsqrt_reference_required")
    place = place if place is not None else LI.Placement(q)
    src_sector = place.get(a.base // 8, 0, tag + ":A")
    dst_sector = place.get(o.base // 8, 0, tag + ":O")
    if src_sector % 8 or dst_sector % 8:
        return refusal("scalar_FULL_lane0_requires_VM_port0_placement")
    ql = LI.QLine()
    ql.vmr(0, 0, src_sector, 0, 0)
    setup = timing.fill_commit + 1
    issue = setup + LI.SETUP_TO_EMIT
    vb = sum(physical_word(q, 0) << (24*k) for k in range(4))
    vb |= physical_word(q, 1) << 96
    ctl = dict(no=1, ni=1, ls=0, lvw=0, vb=vb, srcs=0, dst=1, co_dst=1,
        cp_m1=5, cm_m1=5, cp_imm1=sut["imm1"], cm_imm1=sut["imm1"],
        ca_ad=4, ca_imm2=sut["imm2"], ci_sfu=2, cs_sfu=2)
    # Existing light issue-to-pin28, divider19 replaces multiply4 (+15),
    # scalar rsqrt side depth1+9*4+3*3=46. One extra edge guards OLD SRAM.
    latency = LI.FIRST_OUT - LI.SETUP_TO_EMIT + (19 - 4) + (1 + 9*4 + 3*3)
    drain = issue + latency + 1
    commit = drain + timing.drain_done
    for e in range(commit + 1):
        ql.f["control"][e] = pack(dict(ctl, ld=int(e == setup), emit=int(e == issue)))
    ql.vmw(drain, 0, 0, 0, 1, dst_sector, 1)
    words = list(range(a.base, a.base + 8))
    pre = {} if a.base // 8 in place.written else {src_sector: words}
    input_data = {str(w): f"{int(np.float32(data.get(w, 0)).view(np.uint32)):08x}" for w in words}
    place.written.add(o.base // 8)
    want = int(expected.view(np.uint32))
    return dict(status="emitted", reasons=[], ql=ql, lines=ql.lines(),
        fills=[(a.base // 8, 0)], drains=[(o.base // 8, commit)], preload=pre,
        data=input_data, inputs_placeholder=False,
        expect=[dict(sector=dst_sector, mask=1, edge=commit,
            words=list(range(o.base, o.base + 8)), value=[want] + [None]*7)],
        setup_edge=setup, issue_edges=[issue], last_commit=commit,
        fill_sectors=len(pre), drain_sectors=1, sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, owner="SU-LAYER-1021", execution_qualified=False,
            mode="actual_quarter0_FULL_lane0_divider_add_rsqrt"),
        read_footprint=[dict(logical_word=a.base, logical_sector=a.base // 8,
            physical_sector=src_sector, edge=0, local_row=0)],
        write_footprint=[dict(logical_word=o.base, logical_sector=o.base // 8,
            physical_sector=dst_sector, edge=commit, mask=1, local_row=1)],
        expected_post_state={str(o.base): f"{want:08x}"}, expected_post_state_only=True,
        expected_reference=dict(role="comparison_only", source="NumPy IEEE DIV + hdc_golden add/rsqrt"),
        control_reservation=dict(first=0, last=commit, policy="exclusive_record"),
        source_contract=dict(lane="su_SW0.g_lane[0] FULL", side_MLAT=4, side_ALAT=3,
            side_repair_required=True, scalar_external_drive=False,
            scoped_source_sha256=hashlib.sha256(scoped.encode()).hexdigest()),
        timing_obligations=dict(issue_to_output=latency, divider=19, rsqrt=46,
            serial_edges=commit+1, stream_edges=math.ceil(4*(commit+1)/3),
            old_price_preserved=False, connected_selected_case_RTL_required=True))


# ------------------------------------------------------------------------------------------------------------------
# TOK-FUNC2-HBM-SU (10-21): profile-general versions of the two selected lowerings above, opt-in (layer_images
# --su-lower2).  Same RTL paths (real lane arithmetic -> pretree -> reducer -> stree RF -> RF-sector VM drain; FULL
# lane0 divider/add/SIDE rsqrt); only the record shape is generalised.  For the selected L0 q_norm.ss / q_norm.rs
# records they emit exactly the lines of lower() / lower_norm_rs() (checked by test_su_lower2).
def pretree_blocks(nb, t0):
    """tree emission edge of every block, exactly su_pretree_lower.Schedule.lower's pair-group order"""
    import su_pretree_lower as PT
    edges, t = {}, t0
    npairs = -(-nb // 2)
    for g0 in range(0, npairs, PT.DEP):
        P = min(PT.DEP, npairs - g0)
        for i in range(P):
            pi = g0 + i
            edges[t + i] = 2 * pi
            if 2 * pi + 1 < nb:
                edges[t + i + PT.DEP] = 2 * pi + 1
        t += PT.DEP + P
    return edges


def reduce_profile(sut, desc):
    """(kind, lane_m1, imm1) of a whole-record SU reduction to one R word, or None"""
    allowed = {"red", "red_sq", "red_tree", "red_whole", "m1", "imm1"}
    if any(v for k, v in sut.items() if k not in allowed) or not sut["red"] or set(desc) != {"A", "R"}:
        return None
    if sut["red"] not in (1, 2):
        return None
    kind = "sum" if sut["red"] == 1 else "max"
    if sut["red_sq"]:
        if sut["m1"] or kind != "sum":
            return None
        return kind, 2, 0
    if sut["m1"] not in (0, 3) or (sut["m1"] == 0 and sut["imm1"]):
        return None
    return kind, sut["m1"], sut["imm1"]


class TreeLines:
    """quarter command lines with the 48-bit pretree field above the 2422-bit base line (lower()'s layout)"""

    def __new__(cls):
        from hbm_layer_vehicle import layer_images as LI

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
        return Lines()


def reduce_to_rf(ql, *, a_base, nwords, kind, lane_m1, imm1, rf_addr, q, data, place, tag, timing,
                 fill_row0=0, edge0=0):
    """Lane arithmetic -> pretree -> reducer -> EXPORT -> stree -> RF word rf_addr, programmed into ql from edge0.

    Returns dict(value, rf_commit, ...) or dict(refusal=why).  Every operand word enters through real VM fills of its
    own sectors (store rows fill_row0..); nothing is injected into the reducer / RF."""
    from hbm_layer_vehicle import layer_images as LI
    from su_arith_compile import pack, physical_word
    import su_pretree_lower as PT
    from hdc_golden import mul
    nb = -(-nwords // PT.BLOCK)
    addresses = list(range(a_base, a_base + nwords))
    if data is None or any(x not in data for x in addresses):
        return dict(refusal="missing_real_operand_words:" + str(sum(x not in (data or {}) for x in addresses)))
    before = np.asarray([data[x] for x in addresses], dtype=np.float32)
    if not np.isfinite(before).all():
        return dict(refusal="finite_operand_profile_required")
    if lane_m1 == 2:
        lane_x = np.asarray(mul(before, before), np.float32)
    elif lane_m1 == 3:
        lane_x = np.asarray(mul(before, np.uint32(imm1).view(np.float32)), np.float32)
    else:
        lane_x = before.copy()
    if not np.isfinite(lane_x).all():
        return dict(refusal="finite_lane_value_profile_required")
    lane_bits = lane_x.view(np.uint32)
    want = PT.golden(kind, lane_bits)
    fills, preload, reads = [], {}, []
    next_fill = [edge0] * 8
    for block in range(nb):
        cnt = min(PT.BLOCK, nwords - PT.BLOCK * block)
        for sector in range(-(-cnt // 8)):
            first = a_base + 128 * block + 8 * sector
            logical = first // 8
            port = sector % 8
            physical = place.get(logical, port, tag + ":A")
            if physical % 8 != port:
                return dict(refusal="operand_VM_port_placement_conflict")
            edge = next_fill[port]
            next_fill[port] += 1
            ql.vmr(edge, port, physical, sector, fill_row0 + block)
            fills.append((logical, edge))
            reads.append(dict(logical_sector=logical, physical_sector=physical, edge=edge,
                              words=list(range(first, first + 8)), local_row=fill_row0 + block, group=sector))
            if logical not in place.written:
                preload[physical] = list(range(first, first + 8))
    setup = max(edge for _, edge in fills) + timing.fill_commit + 1
    first_issue = setup + 8
    issue_to_tree = LI.FIRST_OUT - LI.SETUP_TO_EMIT + 1
    tree_first = first_issue + issue_to_tree
    schedule = PT.Schedule()
    schedule.lower(kind, lane_bits, 0x100 | rf_addr, tree_first)
    block_edges = pretree_blocks(nb, tree_first)
    if set(block_edges) != set(schedule.tree):
        raise ValueError("pre-tree scheduler emission contract changed")
    terms = 0
    for role in range(4):
        for bit in range(7):
            terms |= (1 << bit) << (24 * (10 * role + bit))
    base = dict(no=1, ni=nwords, ls=7, lvw=7, srcs=0, dst=0, co_dst=0, ld_c=terms, cp_m1=lane_m1, cm_m1=lane_m1)
    if imm1:
        base.update(cp_imm1=imm1, cm_imm1=imm1)
    mx = int(kind == "max")
    issue_edges, operand_events = [], []
    for tree_edge, block in sorted(block_edges.items()):
        edge = tree_edge - issue_to_tree
        cnt = min(PT.BLOCK, nwords - PT.BLOCK * block)
        vb = sum(physical_word(q, fill_row0 + block) << (24 * role) for role in range(4))
        ql.f["control"][edge] = pack(dict(base, emit=1, i_v=128 * block, vb=vb))
        ql.f["tree"][tree_edge] = PT.tree_cmd_word(mx, cnt)
        issue_edges.append(edge)
        operand_events.append(dict(block=block, issue_edge=edge, tree_edge=tree_edge, words=cnt,
                                   first_logical_word=a_base + 128 * block, local_row=fill_row0 + block,
                                   arithmetic=f"real_lane_m1_{lane_m1}_FP32"))
    ql.f["control"][setup] = pack(dict(base, ld=1))
    ready = {}
    for edge, command in sorted(schedule.red.items()):
        op = command["op"]
        rd = ([command["a"], command["b"]] if op in (2, 5) else [command["a"]] if op in (1, 3, 4) else [])
        if any(ready.get(x, math.inf) > edge for x in rd):
            raise ValueError("reducer SRAM RAW reservation violated")
        if edge in ql.f["red"]:
            raise ValueError("reducer command slot busy")
        ql.f["red"][edge] = PT.red_cmd_word(command)
        if op != 4:
            ready[command["d"]] = edge + PT.DEP
    export_edge, _, schedule_want = schedule.exps[-1]
    if schedule_want != want:
        raise ValueError("lowered reduction graph differs from independent reference")
    rf_relay = 32
    rf_commit = export_edge + 12 + rf_relay + 1
    hold = pack(base)
    return dict(value=want, rf_commit=rf_commit, export_edge=export_edge, setup=setup, hold=hold,
                fills=fills, preload=preload, reads=reads, issue_edges=issue_edges, operand_events=operand_events,
                reducer_commands=[dict(edge=e, **c) for e, c in sorted(schedule.red.items())],
                input_bits=before.view(np.uint32).copy(), issue_to_tree=issue_to_tree,
                rf_event=dict(kind="export", quarter=q, command_serial=export_edge,
                              scalar_capture_serial=export_edge + 12, rf_write_pins_serial=export_edge + 12 + rf_relay,
                              rf_commit_serial=rf_commit, rf_address=rf_addr))


def lower_reduce(raw, q=0, data=None, place=None, tag="", timing=None, expected_reduction_word=None, **unused):
    """One whole reduction (sum / sum of squares / max of A*imm) of a contiguous VM operand to one VM R word.

    Lanes: real FP32 lane arithmetic (AA square, A*imm1 or A) on 128-word issue blocks; the slice pre-trees take each
    block's csum8 subtree (or ordered max), the quarter reducer joins them (su_pretree_lower), EXPORT -> selected stree
    -> RF -> class-5 RF-sector drain to VM (as lower()).  No reducer operand / RF word is injected."""
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    import su_pretree_lower as PT

    _, unit, sut, desc = decode(raw)
    refusal = lambda why, st="unsupported_lowering": dict(status=st, reasons=[why], sut=sut,
                                                          lowering=dict(supported=False, owner="TOK-FUNC2-HBM-SU"))
    prof = reduce_profile(sut, desc) if unit == 2 else None
    if prof is None:
        return refusal("whole_reduction_A_to_R_profile_only")
    kind, lane_m1, imm1 = prof
    a, r = desc["A"], desc["R"]
    contiguous = a.m == 1 or a.stride == a.n
    if (a.space != "VM" or a.fmt != "FP32" or not contiguous or (a.istride or 1) != 1 or a.base % 8
            or any(getattr(a, x) for x in ("lstride", "dyn_sel", "dyn_mul", "n_sel", "l1stride", "ibcast", "indexed"))):
        return refusal("contiguous_aligned_FP32_operand_required")
    if (r.space != "VM" or r.fmt != "FP32" or r.n != 1 or r.m != 1 or r.indexed or r.ibcast):
        return refusal("single_VM_R_destination_required")
    if q != 0:
        return refusal("complete_reduction_owned_by_quarter0_stree")
    if not isinstance(timing, NativeTiming) or timing != NativeTiming(18, 15):
        return refusal("selected_native_READ_RETURN18_WRITE_RETURN15_required")
    nwords = a.n * a.m
    place = place if place is not None else LI.Placement(q)
    ql = TreeLines()
    rf_addr = r.base & 255
    core = reduce_to_rf(ql, a_base=a.base, nwords=nwords, kind=kind, lane_m1=lane_m1, imm1=imm1, rf_addr=rf_addr,
                        q=q, data=data, place=place, tag=tag, timing=timing)
    if "refusal" in core:
        return refusal(core["refusal"])
    want = core["value"]
    if expected_reduction_word is not None:
        supplied = int(expected_reduction_word, 16) if isinstance(expected_reduction_word, str) else int(expected_reduction_word)
        if supplied != want:
            return refusal(f"golden_mismatch: independent reduction {want:08x} != downstream fixture R {supplied:08x}",
                           "golden_mismatch")
    rf_commit = core["rf_commit"]
    rf_read = rf_commit + 2
    drain_edge = rf_read + 2
    ql.put("rf", rf_read, 5 * 9, 9, 0x100 | (rf_addr & ~7))
    logical_r = r.base // 8
    physical_r = place.get(logical_r, 0, tag + ":R")
    if physical_r % 8:
        return refusal("RF_sector_drain_requires_VM_port0_placement")
    ql.vmw(drain_edge, 0, 1, 0, 0, physical_r, 1 << (rf_addr & 7))
    commit = drain_edge + timing.drain_done
    for edge in range(commit + 1):
        ql.f["control"].setdefault(edge, core["hold"])
    lines = ql.lines()
    if len(lines) > LI.EDGES_MAX:
        return refusal("native_programme_capacity_exceeded")
    place.written.add(logical_r)
    pre_words = {str(w): f"{int(np.float32((data[w] if w in data else 0)).view(np.uint32)):08x}"
                 for ws in core["preload"].values() for w in ws}
    expected = [None] * 8
    expected[rf_addr & 7] = want
    r0 = r.base - (r.base & 7)
    return dict(status="emitted", reasons=[], ql=ql, lines=lines, fills=core["fills"],
        drains=[(logical_r, commit)], preload=core["preload"], data=pre_words, inputs_placeholder=False,
        expect=[dict(sector=physical_r, mask=1 << (rf_addr & 7), edge=commit, words=list(range(r0, r0 + 8)),
                     value=expected)],
        setup_edge=core["setup"], issue_edges=core["issue_edges"], last_commit=commit,
        fill_sectors=len(core["preload"]), drain_sectors=1, sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, words=nwords, issue_groups=len(core["issue_edges"]), kind=kind,
                      lane_m1=lane_m1, execution_qualified=False, owner="TOK-FUNC2-HBM-SU",
                      mode="single_quarter_serialized",
                      source="su_pretree_lower + actual lane arithmetic + selected stree RF calendar"),
        quarter_ownership=dict(quarter=q, words=nwords, complete_record=True,
                               external_quarter_partial_values_injected=False),
        command_width=2470, tree_width=48,
        source_contract=dict(command_low_bits=2422, selected_qcore="sucore_SW",
            RF_route="stl_SW.up -> stu_SW_00..13 -> str_C -> std_SW_00..13a/b -> stl_SW.rf_w* -> sucore_SW.rf_w*",
            RF_external_drive=False, collective_rr_external_drive=False),
        operand_events=core["operand_events"], reducer_commands=core["reducer_commands"],
        rf_events=[core["rf_event"], dict(kind="class5_read", edge=rf_read, addr=rf_addr & ~7),
                   dict(kind="RF_to_VM_drain", edge=drain_edge, vm_commit=commit)],
        read_footprint=core["reads"],
        write_footprint=[dict(logical_word=r.base, logical_sector=logical_r, physical_sector=physical_r,
                              mask=1 << (rf_addr & 7), edge=commit)],
        expected_post_state={str(r.base): f"{want:08x}"}, expected_post_state_only=True,
        input_sha256=hashlib.sha256(core["input_bits"].tobytes()).hexdigest(),
        expected_reference=dict(value=f"{want:08x}", role="comparison_only",
                                source=f"independent {'csum8' if kind == 'sum' else 'ordered max'} of lane values"),
        control_reservation=dict(first=0, last=commit, policy="exclusive_record"),
        timing_obligations=dict(issue_to_tree=core["issue_to_tree"], tree_to_red=PT.PT_RED, reducer_RAW=PT.DEP,
            RF_relay=32, RF_export_to_commit=45, RF_LOCAL=1, serial_edges=commit + 1,
            stream_edges=math.ceil(4 * (commit + 1) / 3), old_price_preserved=False,
            connected_selected_case_RTL_required=True))


def rsqrt_profile(sut, desc):
    prof = dict.fromkeys(sut, 0)
    prof.update(m1=5, ad=4, sfu=2, dst=1, imm1=sut["imm1"], imm2=sut["imm2"])
    return sut == prof and set(desc) == {"A", "O"}


def lower_rsqrt(raw, q=0, data=None, place=None, tag="", timing=None, side_profile=None, side_source_path=None,
                **unused):
    """lower_norm_rs for any divisor / epsilon immediates: the FULL lane0 divider + add + SIDE rsqrt datapath takes
    them from the cp/cm_imm1 and ca_imm2 control fields; latency does not depend on them."""
    res = lower_norm_rs(raw, q, data=data, place=place, tag=tag, timing=timing, side_profile=side_profile,
                        side_source_path=side_source_path, any_immediates=True)
    if res.get("status") == "emitted":
        res["lowering"] = dict(res["lowering"], generalised_by="TOK-FUNC2-HBM-SU",
                               immediates=dict(imm1=res["sut"]["imm1"], imm2=res["sut"]["imm2"]))
    return res


def lower_bcast(raw, q=0, data=None, place=None, tag="", timing=None, rf_local=None, **unused):
    """Elementwise SU.VOP whose B operand is ONE VM scalar broadcast to every lane (q_norm.y / kv_norm.y class).

    Real on-chip path, one SU programme:
      prologue  VM sector of B -> store group 0 lane 0 (B word at sector position 0) -> lane copy (m1 0) -> slice
                pretree (cnt 1: csum8 of [x] = x for x != -0) -> reducer LOAD/EXPORT -> stree -> RF word b.base & 255
      main      idx_layer_lower_1021.lower_broadcast: A/C/D fills, B from the RF as a class-1 stream (srcs B = 1,
                vb_B = RF address, B lane terms 0), arithmetic, O drains.
    The B value is never injected: it is whatever the producer record wrote to VM (place.written) or a pre-layer image."""
    from hbm_layer_vehicle import idx_layer_lower_1021 as IX
    from hbm_layer_vehicle.native_profile import NativeTiming
    from hbm_layer_vehicle import layer_images as LI
    from su_program_inventory import decode
    _, unit, sut, desc = decode(raw)
    refusal = lambda why: dict(status="v1_unsupported", reasons=[why], sut=sut,
                              lowering=dict(supported=False, owner="TOK-FUNC2-HBM-SU"))
    b = desc.get("B")
    if unit != 2 or b is None or not b.ibcast or b.space != "VM" or b.indexed or b.m != 1:
        return refusal("uniform_VM_scalar_B_broadcast_required")
    if sut["red"] or sut["b_half"] or "O" not in desc:
        return refusal("elementwise_broadcast_to_O_profile_only")
    if b.base % 8:
        return refusal("broadcast_scalar_must_sit_at_sector_position0_for_lane0_pretree_transfer")
    for role, md in desc.items():
        if role == "B":
            continue
        if (md.space != "VM" or md.fmt != "FP32" or md.m != 1 or (md.istride or 1) != 1 or md.ibcast
                or any(getattr(md, x) for x in ("lstride", "dyn_sel", "dyn_mul", "n_sel", "l1stride", "indexed"))):
            return refusal(f"contiguous_m1_operand_{role}_required")
    if q != 0 or not isinstance(timing, NativeTiming) or timing != NativeTiming(18, 15) or rf_local not in (0, 1):
        return refusal("selected_quarter0_native_timing_and_RF_LOCAL_required")
    if data is None or b.base not in data:
        return refusal("broadcast_scalar_VM_word_unknown")
    place = place if place is not None else LI.Placement(q)
    for role, md in desc.items():           # words of a fetched operand sector outside the operand = inactive pad
        if role in "ACD":
            for w in range((md.base // 8) * 8, -(-(md.base + md.n) // 8) * 8):
                data.setdefault(w, np.float32(0))
    rf_addr = b.base & 255
    pro = TreeLines()
    core = reduce_to_rf(pro, a_base=b.base, nwords=1, kind="sum", lane_m1=0, imm1=0, rf_addr=rf_addr, q=q,
                        data=data, place=place, tag=tag + ":Bxfer", timing=timing)
    if "refusal" in core:
        return refusal("broadcast_transfer: " + core["refusal"])
    scalar = np.uint32(core["value"])
    if int(scalar) != int(np.float32(data[b.base]).view(np.uint32)):
        return refusal("broadcast_transfer_changes_value (-0 through +0 pretree padding)")
    # lane copy control held until its ro_x is taken by the pretree
    tree_edges = sorted(pro.f["tree"])
    for e in range(0, tree_edges[-1] + 1):
        pro.f["control"].setdefault(e, core["hold"])
    scalar_ready = core["rf_event"]["rf_write_pins_serial"]
    main = IX.lower_broadcast(raw, q=q, timing=timing, rf_address=rf_addr, scalar_ready=scalar_ready,
                              rf_local=rf_local, place=place, data=data, tag=tag)
    if main.get("status") != "candidate_requires_binding":
        return dict(refusal("; ".join(main.get("reasons", ["broadcast main op unlowered"]))),
                    status="unsupported_lowering" if any("unsupported" in x or "native_" in x
                                                         for x in main.get("reasons", [])) else "v1_unsupported")
    ql = main["ql"]
    if LI.calendar_collision(ql, pro, 0, exclusive_controls=True):
        return refusal("broadcast_transfer_collides_with_main_calendar")
    if "tree" not in ql.f:
        ql.f["tree"] = {}
    for fld, cmds in pro.f.items():
        for e, v in cmds.items():
            ql.f[fld][e] = ql.f[fld].get(e, 0) | v
    main_lines = TreeLines()
    main_lines.f = ql.f
    # expected O (independent hdc_golden lane model) with the broadcast scalar
    o = desc["O"]
    n = o.n
    ops = {}
    for role in "ACD":
        if role in desc:
            md = desc[role]
            ops[role] = np.array([data[md.base + j] for j in range(n)], np.float32)
    ops["B"] = np.full(n, scalar.view(np.float32), np.float32)
    bits = LI.vop_golden(sut, ops)
    outv = {o.base + j: int(v) for j, v in enumerate(bits)}
    expect = []
    for x in main["expect"]:
        expect.append(dict(x, value=[outv.get(w) for w in x["words"]]))
    preload = dict(main["preload"])
    preload.update(core["preload"])
    # pre-operation snapshot BEFORE the in-place O update (O may alias A); expected outputs never seed M
    pre_words = {str(w): f"{int(np.float32((data[w] if w in data else 0)).view(np.uint32)):08x}"
                 for ws in preload.values() for w in ws}
    for w, v in outv.items():
        data[w] = np.uint32(v).view(np.float32)
    lines = main_lines.lines()
    if len(lines) > LI.EDGES_MAX:
        return refusal("native_programme_capacity_exceeded")
    last = main["last_commit"]
    return dict(status="emitted", reasons=[], ql=main_lines, lines=lines,
        fills=core["fills"] + [f for f in main["vm_reads"] if f[1] is not None],
        drains=main["vm_writes"], preload=preload, data=pre_words, inputs_placeholder=main["inputs_placeholder"],
        expect=expect, setup_edge=core["setup"], issue_edges=core["issue_edges"] + main["issue_edges"],
        last_commit=max(x["edge"] for x in expect) if expect else last,
        fill_sectors=len(preload), drain_sectors=len(expect), sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, owner="TOK-FUNC2-HBM-SU", execution_qualified=False,
                      mode="VM_scalar->lane0->pretree->reducer->stree->RF class1 broadcast",
                      main="idx_layer_lower_1021.lower_broadcast", rf_address=rf_addr),
        rf_events=[core["rf_event"]] + main["commands"],
        reservations=main["reservations"] + [dict(resource="RF_word", address=rf_addr,
                                                  first=core["rf_commit"], last=last)],
        control_reservation=dict(first=0, last=last, policy="exclusive_record"),
        expected_post_state={str(w): f"{v:08x}" for w, v in outv.items()}, expected_post_state_only=True,
        expected_reference=dict(role="comparison_only", source="hdc_golden vop_golden with broadcast B"),
        source_contract=dict(selected_qcore="sucore_SW", RF_LOCAL=rf_local, B_srcs_code=1,
                             RF_route="stl_SW.up -> stu_SW_00..13 -> str_C -> std_SW_00..13a/b -> sucore_SW.rf_w*",
                             RF_external_drive=False),
        timing_obligations=dict(scalar_ready_serial=scalar_ready, rf_commit=core["rf_commit"],
                                serial_edges=len(lines), stream_edges=math.ceil(4 * len(lines) / 3),
                                old_price_preserved=False, connected_selected_case_RTL_required=True))
