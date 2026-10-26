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
    if any(v for k, v in sut.items() if k not in allowed) or not sut["red"] or set(desc) not in ({"A", "R"},
                                                                                              {"A", "B", "R"}):
        return None
    if "B" in desc:                     # dot product: lane A*B (m1 1), B an ordinary vector operand
        if sut["m1"] != 1 or sut["red_sq"] or sut["red"] != 1 or desc["B"].ibcast:
            return None
        return "sum", 1, 0
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
                 fill_row0=0, edge0=0, b_base=None, pretree_profile=None):
    """Lane arithmetic -> pretree -> reducer -> EXPORT -> stree -> RF word rf_addr, programmed into ql from edge0.

    Returns dict(value, rf_commit, ...) or dict(refusal=why).  Every operand word enters through real VM fills of its
    own sectors (store rows fill_row0..); nothing is injected into the reducer / RF."""
    from hbm_layer_vehicle import layer_images as LI
    from su_arith_compile import pack, physical_word
    import su_pretree_lower as PT
    from hdc_golden import mul
    nb = -(-nwords // PT.BLOCK)
    addresses = list(range(a_base, a_base + nwords))
    if b_base is not None:
        addresses += list(range(b_base, b_base + nwords))
    if data is None or any(x not in data for x in addresses):
        return dict(refusal="missing_real_operand_words:" + str(sum(x not in (data or {}) for x in addresses)))
    before = np.asarray([data[x] for x in addresses[:nwords]], dtype=np.float32)
    bvals = None if b_base is None else np.asarray([data[x] for x in addresses[nwords:]], dtype=np.float32)
    if not np.isfinite(before).all() or (bvals is not None and not np.isfinite(bvals).all()):
        return dict(refusal="finite_operand_profile_required")
    if lane_m1 == 1:
        if bvals is None:
            return dict(refusal="lane_A_times_B_requires_B_operand")
        lane_x = np.asarray(mul(before, bvals), np.float32)
    elif lane_m1 == 2:
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
    srcs = [("A", a_base, fill_row0)] + ([] if b_base is None else [("B", b_base, fill_row0 + nb)])
    for block in range(nb):
        cnt = min(PT.BLOCK, nwords - PT.BLOCK * block)
        for role, rbase, row0 in srcs:
            if rbase % 8:
                return dict(refusal=f"operand_{role}_not_sector_aligned")
            for sector in range(-(-cnt // 8)):
                first = rbase + 128 * block + 8 * sector
                logical = first // 8
                port = sector % 8
                if logical in place.map and place.map[logical] % 8 != port:
                    return dict(refusal="operand_VM_port_placement_conflict")
                physical = place.get(logical, port, tag + ":" + role)
                edge = next_fill[port]
                next_fill[port] += 1
                ql.vmr(edge, port, physical, sector, row0 + block)
                fills.append((logical, edge))
                reads.append(dict(logical_sector=logical, physical_sector=physical, edge=edge, role=role,
                                  words=list(range(first, first + 8)), local_row=row0 + block, group=sector))
                if logical not in place.written:
                    preload[physical] = list(range(first, first + 8))
    setup = max(edge for _, edge in fills) + timing.fill_commit + 1
    first_issue = setup + 8
    issue_to_tree = LI.FIRST_OUT - LI.SETUP_TO_EMIT + 1
    tree_first = first_issue + issue_to_tree
    schedule = PT.Schedule(**({"pt_red": pretree_profile.tree_to_reducer} if pretree_profile else {}))
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
        if b_base is not None:
            vb = (vb & ~(0xffffff << 24)) | (physical_word(q, fill_row0 + nb + block) << 24)
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
    per_row = r.m > 1
    contiguous = a.m == 1 or a.stride == a.n or per_row
    if (a.space != "VM" or a.fmt != "FP32" or not contiguous or (a.istride or 1) != 1 or a.base % 8
            or (per_row and a.stride % 8)
            or any(getattr(a, x) for x in ("lstride", "dyn_sel", "dyn_mul", "n_sel", "l1stride", "ibcast", "indexed"))):
        return refusal("contiguous_aligned_FP32_operand_required")
    if (r.space != "VM" or r.fmt != "FP32" or r.n != 1 or r.indexed or r.ibcast
            or (per_row and (r.m != a.m or r.stride != 1 or (r.base & 7) + r.m > 8))):
        return refusal("single_VM_R_destination_or_one_RF_sector_of_row_results_required")
    if q != 0:
        return refusal("complete_reduction_owned_by_quarter0_stree")
    if not isinstance(timing, NativeTiming) or timing != NativeTiming(18, 15):
        return refusal("selected_native_READ_RETURN18_WRITE_RETURN15_required")
    nwords = a.n * a.m
    place = place if place is not None else LI.Placement(q)
    ql = TreeLines()
    rf_addr = r.base & 255
    bd = desc.get("B")
    if bd is not None and (bd.space != "VM" or bd.fmt != "FP32" or bd.n != a.n or bd.m != a.m or (bd.istride or 1) != 1
                           or bd.base % 8 or (per_row and bd.stride % 8) or (not per_row and a.m > 1 and bd.stride != bd.n)):
        return refusal("dot_product_B_must_match_A_layout")
    rows = ([(a.base + k * a.stride, a.n) for k in range(a.m)] if per_row else [(a.base, nwords)])
    brow = ([bd.base + k * bd.stride for k in range(a.m)] if per_row else [bd.base]) if bd is not None else None
    if expected_reduction_word is not None and not isinstance(expected_reduction_word, (list, tuple)):
        expected_reduction_word = [expected_reduction_word]
    cores, edge0, wants = [], 0, []
    for k, (row_base, row_words) in enumerate(rows):
        c = reduce_to_rf(ql, a_base=row_base, nwords=row_words, kind=kind, lane_m1=lane_m1, imm1=imm1,
                         rf_addr=rf_addr + k, q=q, data=data, place=place, tag=f"{tag}:row{k}", timing=timing,
                         edge0=edge0, b_base=None if brow is None else brow[k])
        if "refusal" in c:
            return refusal(c["refusal"])
        cores.append(c)
        wants.append(c["value"])
        # rows run strictly one after another (reducer scratch addresses and store rows are reused per row)
        edge0 = c["export_edge"] + 1
    for k, c in enumerate(cores[1:]):
        for e in range(cores[k]["setup"], c["setup"]):
            ql.f["control"].setdefault(e, cores[k]["hold"])
    core = dict(cores[-1], fills=[f for c in cores for f in c["fills"]],
                preload={s_: w for c in cores for s_, w in c["preload"].items()},
                reads=[x for c in cores for x in c["reads"]], issue_edges=[e for c in cores for e in c["issue_edges"]],
                operand_events=[x for c in cores for x in c["operand_events"]],
                reducer_commands=[x for c in cores for x in c["reducer_commands"]],
                input_bits=np.concatenate([c["input_bits"] for c in cores]), setup=cores[0]["setup"],
                hold=cores[0]["hold"])
    want = wants[0]
    if expected_reduction_word is not None:
        for k, sup in enumerate(expected_reduction_word):
            if sup is None:
                continue
            supplied = int(sup, 16) if isinstance(sup, str) else int(sup)
            if supplied != wants[k]:
                return refusal(f"golden_mismatch: independent reduction row {k} {wants[k]:08x} != downstream fixture "
                               f"R {supplied:08x}", "golden_mismatch")
    rf_commit = core["rf_commit"]
    rf_read = rf_commit + 2
    drain_edge = rf_read + 2
    ql.put("rf", rf_read, 5 * 9, 9, 0x100 | (rf_addr & ~7))
    logical_r = r.base // 8
    physical_r = place.get(logical_r, 0, tag + ":R")
    if physical_r % 8:
        return refusal("RF_sector_drain_requires_VM_port0_placement")
    rmask = ((1 << len(rows)) - 1) << (rf_addr & 7)
    ql.vmw(drain_edge, 0, 1, 0, 0, physical_r, rmask)
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
    for k, w in enumerate(wants):
        expected[(rf_addr & 7) + k] = w
    r0 = r.base - (r.base & 7)
    return dict(status="emitted", reasons=[], ql=ql, lines=lines, fills=core["fills"],
        drains=[(logical_r, commit)], preload=core["preload"], data=pre_words, inputs_placeholder=False,
        expect=[dict(sector=physical_r, mask=rmask, edge=commit, words=list(range(r0, r0 + 8)),
                     value=expected)],
        setup_edge=core["setup"], issue_edges=core["issue_edges"], last_commit=commit,
        fill_sectors=len(core["preload"]), drain_sectors=1, sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, words=nwords, rows=len(rows), issue_groups=len(core["issue_edges"]), kind=kind,
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
        rf_events=[c["rf_event"] for c in cores] + [dict(kind="class5_read", edge=rf_read, addr=rf_addr & ~7),
                   dict(kind="RF_to_VM_drain", edge=drain_edge, vm_commit=commit)],
        read_footprint=core["reads"],
        write_footprint=[dict(logical_word=r.base, logical_sector=logical_r, physical_sector=physical_r,
                              mask=rmask, edge=commit)],
        expected_post_state={str(r.base + k): f"{w:08x}" for k, w in enumerate(wants)}, expected_post_state_only=True,
        input_sha256=hashlib.sha256(core["input_bits"].tobytes()).hexdigest(),
        expected_reference=dict(value=[f"{w:08x}" for w in wants] if per_row else f"{want:08x}", role="comparison_only",
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
                              rf_local=rf_local, place=place, data=data, tag=tag,
                              su_options=dict(absent_readers_identity=True))
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


# ------------------------------------------------------------------------------------------------------------------
# SFU-lane lowering (TOK-FUNC2-HBM-SU 10-21): divider (M1 A/B, A/imm1) and S-stage exp / sigmoid / SiLU exist only in
# KIND>=1 lanes, i.e. quarter-local lanes 0..31 (ot_hbm_su_static_pgslice.sv:129 KIND=(L<32)?1:0, lane 0 FULL).
# A 128-element quarter block therefore issues as four 32-lane sub-issues: element 32s+t on lane t, its operand sector
# 4s+j filled into store group j (VM port j), O drained from group j.  Depths (ot_hbm_su_static_lane.sv, MLAT 4 /
# ALAT 3): divider 19 vs multiply 4 (+15); S exp 7*MLAT+8*ALAT+4 = 56, sigmoid/SiLU exp+ALAT+19 = 78.
SFU_LANES = 32
SFU_EXTRA = {0: 0, 1: 56, 4: 78, 5: 78}


def sfu_lane_golden(sut, ops):
    """vop_golden + the KIND-1 lane's divider and S stage (hdc_golden_v41 div / exp / sigmoid / silu forms)"""
    from hdc_golden import add, mul, to_bf16, exp
    from hdc_golden_v41 import div
    f = lambda u: np.uint32(u).view(np.float32)
    a, b, c, d = (ops.get(k) for k in "ABCD")
    aa = to_bf16(a) if sut["a_rnd"] else a.copy()
    if sut["a_relu"]:
        aa = np.where(np.signbit(aa), np.float32(0), aa).astype(np.float32)
    if sut["a_min"]:
        aa = np.minimum(aa, f(sut["imm3"])).astype(np.float32)
    cc = np.clip(c, -f(sut["imm3"]), f(sut["imm3"])) if (sut["c_clip"] and c is not None) else c
    x, m = aa.copy(), sut["m1"]
    if m in (1, 2, 3):
        x = mul(aa, b if m == 1 else aa if m == 2 else f(sut["imm1"]))
    elif m == 4:
        x = np.asarray(div(aa, b), np.float32)
    elif m == 5:
        x = np.asarray(div(aa, np.full_like(aa, f(sut["imm1"]))), np.float32)
    elif m == 6:
        x = np.maximum(aa, b).astype(np.float32)
    if sut["m2"]:
        x = mul(x, cc if sut["m2"] == 1 else f(sut["imm1"]))
    if sut["qm"]:
        raise ValueError("qm not in the SFU-lane profile")
    ad = sut["ad"]
    if ad:
        x = add(x, cc if ad == 2 else -b if ad == 3 else f(sut["imm2"]) if ad == 4 else d)
    s = sut["sfu"]
    if s in (2, 3, 6, 7):                      # FULL lane 0 scalar side pipe (ot_hbm_su_static_side.sv)
        from hdc_golden import rsqrt
        from hdc_golden_v41 import sqrt, softplus, sigmoid
        with np.errstate(all="ignore"):
            if s == 2:
                x = np.asarray(rsqrt(x), np.float32)
            elif s == 3:
                x = np.asarray(sqrt(x), np.float32)
            elif s == 6:
                x = np.asarray(sqrt(softplus(x)), np.float32)
            else:
                mag = np.asarray(sqrt(np.maximum(np.abs(x), np.float32(1e-6)).astype(np.float32)), np.float32)
                x = np.asarray(sigmoid(np.where(x < 0, -mag, mag).astype(np.float32)), np.float32)
    elif s == 1:
        x = np.asarray(exp(x), np.float32)
    elif s in (4, 5):
        den = add(np.asarray(exp(-x), np.float32), np.float32(1.0))
        x = np.asarray(div(x if s == 5 else np.ones_like(x), den), np.float32)
    e1 = sut["e1"]
    if e1 in (1, 3):
        x = mul(x, cc if e1 == 1 else f(sut["imm2"]))
    if e1 in (2, 4):
        x = add(x, cc if e1 == 2 else f(sut["imm2"]))
    if sut["e2"]:
        x = mul(x, b if sut["e2"] == 1 else f(sut["imm1"]))
    bits = np.asarray(x, np.float32).view(np.uint32).copy()
    if sut["rnd"]:
        bits = ((bits.astype(np.uint64) + 0x7fff + ((bits >> 16) & 1)) & 0xffff0000).astype(np.uint32)
    return bits


def sfu_profile(sut, desc, layout=False):
    """True for a single-row SU.VOP the 32-lane SFU layout lowers: it needs the divider and/or exp/sigmoid/SiLU
    (or, with layout=True, any elementwise / whole-reduction op on a tensor that lives in the SFU layout)"""
    if sut["qm"] or sut["b_half"] or sut["c_pair"] or sut["a_ind"] or sut["ad"] == 1 or sut["red_sq"]:
        return False
    if sut["sfu"] not in SFU_EXTRA:
        return False
    if not layout and sut["m1"] not in (4, 5) and not sut["sfu"]:
        return False
    if sut["red"]:
        if sut["red"] not in (1, 2) or "R" not in desc or desc["R"].n != 1 or desc["R"].m != 1:
            return False
        if sut["dst"] not in (0, 1) or (sut["dst"] == 1) != ("O" in desc):
            return False
    elif sut["dst"] != 1 or "O" not in desc:
        return False
    return "A" in desc and set(desc) <= set("ABCDOR")


def pretree_lower_blocks(sched, kind, blocks, tag, t0):
    """su_pretree_lower.Schedule.lower over explicit (words, count) blocks (32-lane sub-issues: a block's words >= its
    count are the pretree's padding); same pair-group emission, reducer graph and export"""
    import su_pretree_lower as PT
    nb = len(blocks)
    mx = 1 if kind == "max" else 0
    ext = PT.OP_MAX_EXT if mx else PT.OP_ADD_EXT
    tre = PT.OP_MAX_TREE if mx else PT.OP_ADD_TREE
    level, t = [], t0
    npairs = -(-nb // 2)
    for g0 in range(0, npairs, PT.DEP):
        P = min(PT.DEP, npairs - g0)
        for i in range(P):
            pi = g0 + i
            be, bo = 2 * pi, 2 * pi + 1
            ee, eo = t + i, t + i + PT.DEP
            blk, cnt = blocks[be]
            sched.tree[ee] = (mx, cnt, blk)
            v = PT.block_subtree(kind, blk, cnt)
            d = sched._new_addr()
            sched._red(ee + sched.pt_red, op=PT.OP_LOAD, a=0, b=0, d=d, tag=0, osel=1, lane=0x20)
            ready = ee + sched.pt_red + PT.DEP
            if bo < nb:
                blk, cnt = blocks[bo]
                sched.tree[eo] = (mx, cnt, blk)
                vo = PT.block_subtree(kind, blk, cnt)
                sched._red(eo + sched.pt_red, op=ext, a=d, b=0, d=d, tag=0, osel=1, lane=0x20)
                v = PT.fmax(v, vo) if mx else PT.fadd(v, vo)
                ready = eo + sched.pt_red + PT.DEP
            level.append((d, ready, v))
        t += PT.DEP + P
    last = 0
    while len(level) > 1:
        nl = []
        for i in range(0, len(level) - 1, 2):
            (xa, ra, va), (xb, rb, vb) = level[i], level[i + 1]
            e = sched._free_slot(max(ra, rb, last + 1))
            last = e
            d = sched._new_addr()
            sched._red(e, op=tre, a=xa, b=xb, d=d, tag=0, osel=0, lane=0)
            nl.append((d, e + PT.DEP, PT.fmax(va, vb) if mx else PT.fadd(va, vb)))
        if len(level) % 2:
            nl.append(level[-1])
        level = nl
    root, rr, val = level[0]
    e = sched._free_slot(max(rr, last + 1))
    sched._red(e, op=PT.OP_EXPORT, a=root, b=0, d=0, tag=tag, osel=0, lane=0)
    sched.exps.append((e, tag, val))
    return val


def lower_sfu_lanes(raw, q=0, data=None, place=None, tag="", timing=None, rf_local=None, layout=False,
                    expected_reduction_word=None, pretree_profile=None, **unused):
    """SU.VOP on the quarter's 32 KIND>=1 lanes: 32-element sub-issues, sector 4s+j <-> store group j / VM port j.

    Elementwise records: quarter q's share (as the 128-lane mapping), or -- layout=True / reductions -- the WHOLE
    record serialized on quarter q.  Reductions: every sub-issue's lane outputs enter the slice pretrees (count = the
    sub-issue's live lanes) -> reducer -> EXPORT -> stree -> RF -> class-5 RF-sector drain to R (as lower_reduce)."""
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    from su_arith_compile import pack, physical_word
    import su_pretree_lower as PT
    _, unit, sut, desc = decode(raw)
    refusal = lambda why, st="unsupported_lowering": dict(status=st, reasons=[why], sut=sut,
                                                          lowering=dict(supported=False, owner="TOK-FUNC2-HBM-SU"))
    if unit != 2 or not sfu_profile(sut, desc, layout=layout):
        return refusal("sfu_lane_profile_only")
    if q != 0 or not isinstance(timing, NativeTiming) or timing != NativeTiming(18, 15) or rf_local not in (0, 1):
        return refusal("selected_quarter0_native_timing_and_RF_LOCAL_required")
    red = sut["red"]
    n = desc["A"].n
    bcast = "B" in desc and desc["B"].ibcast
    for role, md in desc.items():
        if role == "R":
            if md.space != "VM" or md.fmt != "FP32" or md.indexed or md.ibcast:
                return refusal("single_VM_R_destination_required")
            continue
        if role == "B" and bcast:
            if md.m != 1 or md.indexed or md.base % 8 or md.space != "VM":
                return refusal("broadcast_B_must_be_one_sector_position0_VM_scalar")
            continue
        if (md.space != "VM" or md.fmt != "FP32" or md.m != 1 or md.n != n or (md.istride or 1) != 1 or md.ibcast
                or md.base % 8 or any(getattr(md, x) for x in ("lstride", "dyn_sel", "dyn_mul", "n_sel", "l1stride",
                                                                  "indexed"))):
            return refusal(f"contiguous_aligned_m1_operand_{role}_required", "v1_unsupported")
    if data is None:
        return refusal("real_pre_operation_VM_words_required")
    place = place if place is not None else LI.Placement(q)
    whole = bool(red or layout)
    owned = list(range(n)) if whole else [e for e in range(n) if (e // 128) % 4 == q]
    subs = (list(range(0, n, SFU_LANES)) if whole else
            sorted({(e // 128) * 128 + 32 * ((e % 128) // 32) for e in owned}))
    roles = [r for r in "ABCD" if r in desc and not (r == "B" and bcast)]
    vec_roles = roles + (["O"] if "O" in desc else [])
    for role in vec_roles:
        for st in subs:
            for j in range(4):
                if st + 8 * j >= n:
                    continue
                ls_ = (desc[role].base + st + 8 * j) // 8
                if ls_ in place.map and place.map[ls_] % 8 != j:
                    return refusal(f"operand_{role}_sector_placed_on_port_{place.map[ls_] % 8}_not_SFU_group_{j}",
                                   "v1_unsupported")
    ql = TreeLines()
    edge0, scalar_ready, pro_core, rf_b = 0, None, None, None
    if bcast:
        b = desc["B"]
        if b.base not in data:
            return refusal("broadcast_scalar_VM_word_unknown")
        rf_b = b.base & 255
        pro_core = reduce_to_rf(ql, a_base=b.base, nwords=1, kind="sum", lane_m1=0, imm1=0, rf_addr=rf_b, q=q,
                                data=data, place=place, tag=tag + ":Bxfer", timing=timing,
                                pretree_profile=pretree_profile)
        if "refusal" in pro_core:
            return refusal("broadcast_transfer: " + pro_core["refusal"])
        if pro_core["value"] != int(np.float32(data[b.base]).view(np.uint32)):
            return refusal("broadcast_transfer_changes_value (-0 through +0 pretree padding)")
        for e in range(0, max(ql.f["tree"]) + 1):
            ql.f["control"].setdefault(e, pro_core["hold"])
        scalar_ready = pro_core["rf_event"]["rf_write_pins_serial"]
        edge0 = 1
    for role in roles:
        for st in subs:
            for j in range(4):
                if st + 8 * j < n:
                    for w in range(desc[role].base + st + 8 * j, desc[role].base + st + 8 * j + 8):
                        data.setdefault(w, np.float32(0))      # words of a fetched sector beyond n: inactive pad
    rows, row_next = {}, 1 if bcast else 0
    fills, preload, next_fill, last_fill = [], {}, [edge0] * 8, -1
    for role in roles:
        for u, st in enumerate(subs):
            rows[(role, u)] = row_next
            row_next += 1
            for j in range(4):
                if st + 8 * j >= n:
                    continue
                first = desc[role].base + st + 8 * j
                ls_ = first // 8
                ps = place.get(ls_, j, f"{tag}:{role}")
                e = next_fill[j]
                next_fill[j] += 1
                ql.vmr(e, j, ps, j, rows[(role, u)])
                fills.append((ls_, e))
                last_fill = max(last_fill, e)
                if ls_ not in place.written:
                    preload[ps] = list(range(first, first + 8))
    if row_next + len(subs) > 512:
        return refusal("store_rows_exceeded")
    orow = {u: row_next + u for u in range(len(subs))}
    terms = 0
    for s_, role in enumerate("ABCDO"):
        if (role == "O" and "O" not in desc) or (role == "B" and bcast):
            continue
        for k in range(7):
            terms |= (1 << k) << (24 * (s_ * 10 + k))
    dst = 1 if "O" in desc else 0
    ctl = dict(no=1, ni=n, ls=5, lvw=5, srcs=(1 << 2) if bcast else 0, dst=dst, co_dst=dst, aind=0, cpair=0,
               cx_arnd=sut["a_rnd"], cx_arelu=sut["a_relu"], cx_amin=sut["a_min"], cx_cclip=sut["c_clip"],
               cx_imm3=sut["imm3"], cp_m1=sut["m1"], cp_imm1=sut["imm1"], cm_m1=sut["m1"], cm_m2=sut["m2"], cm_qm=0,
               cm_imm1=sut["imm1"], ca_ad=sut["ad"], ca_imm2=sut["imm2"], ci_sfu=sut["sfu"], cs_sfu=sut["sfu"],
               cs_e1=sut["e1"], cs_imm2=sut["imm2"], ce_e2=sut["e2"], ce_imm1=sut["imm1"], co_rnd=sut["rnd"],
               ld_c=terms)

    def vb_of(u):
        v = 0
        for s_, role in enumerate("ABCDO"):
            if role == "O":
                v |= (physical_word(q, orow[u]) if "O" in desc else 0) << (24 * s_)
            elif role == "B" and bcast:
                v |= rf_b << (24 * s_)
            elif role in desc:
                v |= physical_word(q, rows[(role, u)]) << (24 * s_)
            else:
                v |= physical_word(q, rows[(roles[0], u)]) << (24 * s_)
        return v
    setup = last_fill + timing.fill_commit + 1
    if bcast:
        setup = max(setup, scalar_ready + 4 + rf_local, max(ql.f["tree"]) + 1)
    extra = (15 if sut["m1"] in (4, 5) else 0) + SFU_EXTRA[sut["sfu"]]
    lat = LI.FIRST_OUT - LI.SETUP_TO_EMIT + extra
    # golden lane outputs (every element; the reducer takes out = rnd?(U))
    ops = {}
    for role in "ABCD":
        if role in desc:
            md = desc[role]
            if role == "B" and bcast:
                ops[role] = np.full(n, np.float32(data[md.base]), np.float32)
            else:
                ops[role] = np.array([data[md.base + e] for e in range(n)], np.float32)
    with np.errstate(all="ignore"):
        outbits = sfu_lane_golden(sut, ops)
    sched, want, rf_r = None, None, None
    if red:
        kind = "sum" if red == 1 else "max"
        if not np.isfinite(outbits[:n].view(np.float32)).all():
            return refusal("finite_lane_value_profile_required")
        blocks = []
        for st in subs:
            cnt = min(SFU_LANES, n - st)
            blocks.append(([int(x) for x in outbits[st:st + cnt]] + [0] * (PT.BLOCK - cnt), cnt))
        sched = PT.Schedule(**({"pt_red": pretree_profile.tree_to_reducer} if pretree_profile else {}))
        rf_r = desc["R"].base & 255
        tree_first = setup + LI.SETUP_TO_EMIT + lat + 1
        val = pretree_lower_blocks(sched, kind, blocks, 0x100 | rf_r, tree_first)
        want = PT.golden(kind, outbits[:n])
        if val != want:
            raise ValueError("32-lane pretree graph differs from the independent reduction")
        if expected_reduction_word is not None and int(expected_reduction_word) != want:
            return refusal(f"golden_mismatch: independent reduction {want:08x} != downstream fixture R "
                           f"{int(expected_reduction_word):08x}", "golden_mismatch")
        tree_of = pretree_blocks(len(subs), tree_first)
        issues = [None] * len(subs)
        for te, u in tree_of.items():
            issues[u] = te - (lat + 1)
            ql.f["tree"][te] = PT.tree_cmd_word(int(kind == "max"), blocks[u][1])
        rdy = {}
        for e_, c_ in sorted(sched.red.items()):
            op = c_["op"]
            rd = ([c_["a"], c_["b"]] if op in (2, 5) else [c_["a"]] if op in (1, 3, 4) else [])
            if any(rdy.get(x, math.inf) > e_ for x in rd):
                raise ValueError("reducer SRAM RAW reservation violated")
            if e_ in ql.f["red"]:
                raise ValueError("reducer command slot busy")
            ql.f["red"][e_] = PT.red_cmd_word(c_)
            if op != 4:
                rdy[c_["d"]] = e_ + PT.DEP
    else:
        issues = [setup + LI.SETUP_TO_EMIT + u for u in range(len(subs))]
    ql.f["control"][setup] = pack(dict(ctl, ld=1, vb=vb_of(0)))
    for u, st in enumerate(subs):
        ql.f["control"][issues[u]] = pack(dict(ctl, emit=1, i_v=st, vb=vb_of(u)))
    if bcast:
        for e in range(setup - 1 - rf_local, max(issues) + LI.FIRST_OUT + extra + 1):
            ql.put("rf", e, 9, 9, 256 | rf_b)
    drain_e, expect, drains, commits = [0] * 8, [], [], []
    if "O" in desc:
        o = desc["O"]
        for u, st in enumerate(subs):
            ready = issues[u] + lat + 1
            for j in range(4):
                lo = st + 8 * j
                if lo >= n:
                    continue
                m = [lo + t < n for t in range(8)]
                de = max(ready, drain_e[j])
                drain_e[j] = de + 1
                ls_ = (o.base + lo) // 8
                ps = place.get(ls_, j, f"{tag}:O")
                mask = sum(1 << t for t in range(8) if m[t])
                ql.vmw(de, j, 0, j, orow[u], ps, mask)
                c = de + timing.drain_done
                commits.append(c)
                drains.append((ls_, c))
                expect.append(dict(sector=ps, mask=mask, edge=c, words=list(range(o.base + lo, o.base + lo + 8)),
                                   value=[int(outbits[lo + t]) if m[t] else None for t in range(8)]))
    rf_events = [pro_core["rf_event"]] if pro_core else []
    if red:
        export_edge = sched.exps[-1][0]
        rf_commit = export_edge + 12 + 32 + 1
        rf_read = rf_commit + 2
        de = max(rf_read + 2, drain_e[0])
        rf_read = de - 2                       # RF_LOCAL: class-5 read exactly two edges ahead of the RF drain
        ql.put("rf", rf_read, 5 * 9, 9, 0x100 | (rf_r & ~7))
        r = desc["R"]
        lr = r.base // 8
        if lr in place.map and place.map[lr] % 8:
            return refusal("RF_sector_drain_requires_VM_port0_placement")
        pr = place.get(lr, 0, tag + ":R")
        ql.vmw(de, 0, 1, 0, 0, pr, 1 << (rf_r & 7))
        c = de + timing.drain_done
        commits.append(c)
        drains.append((lr, c))
        r0 = r.base - (r.base & 7)
        rv = [None] * 8
        rv[rf_r & 7] = want
        expect.append(dict(sector=pr, mask=1 << (rf_r & 7), edge=c, words=list(range(r0, r0 + 8)), value=rv))
        rf_events += [dict(kind="export", command_serial=export_edge, rf_commit_serial=rf_commit, rf_address=rf_r),
                      dict(kind="class5_read", edge=rf_read), dict(kind="RF_to_VM_drain", edge=de, vm_commit=c)]
    commit = max(commits)
    hold = pack(dict(ctl, vb=vb_of(0)))
    for e in range(0, commit + 1):
        ql.f["control"].setdefault(e, hold)
    # The pre-tree samples tree_cmd and lane ro_v at the same edge.  The
    # scheduler's slots include a publication edge that the KIND1 lanes do not
    # need: align their commands (including the scalar B transfer) one edge
    # earlier. The reducer consumes valid pulses, so advance its graph with the
    # pre-tree. Lane issues and guarded RF reads, drains and checks stay fixed.
    for field in ("tree", "red"):
        ql.f[field] = {edge - 1: word for edge, word in ql.f[field].items()}
    for event in rf_events:
        if event["kind"] == "export":
            for key in ("command_serial", "scalar_capture_serial", "rf_write_pins_serial", "rf_commit_serial"):
                if key in event:
                    event[key] -= 1
    lines = ql.lines()
    if len(lines) > LI.EDGES_MAX:
        return refusal("native_programme_capacity_exceeded")
    if pro_core:
        preload = {**preload, **pro_core["preload"]}
    pre_words = {str(w): f"{int(np.float32(data[w] if w in data else 0).view(np.uint32)):08x}"
                 for ws in preload.values() for w in ws}
    for ls_, _ in drains:
        place.written.add(ls_)
    post = {}
    if "O" in desc:
        for e in owned:
            post[str(desc["O"].base + e)] = f"{int(outbits[e]):08x}"
            data[desc["O"].base + e] = np.uint32(outbits[e]).view(np.float32)
    if red:
        post[str(desc["R"].base)] = f"{want:08x}"
    return dict(status="emitted", reasons=[], ql=ql, lines=lines,
        fills=(pro_core["fills"] if pro_core else []) + fills, drains=drains, preload=preload, data=pre_words,
        inputs_placeholder=False, expect=expect, setup_edge=setup, issue_edges=issues, last_commit=commit,
        fill_sectors=len(preload), drain_sectors=len(expect), sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, owner="TOK-FUNC2-HBM-SU", execution_qualified=False,
                      mode="KIND1 lanes 0..31 sub-issues" + (" + RF class-1 broadcast B" if bcast else "")
                           + (" + 32-lane pretree reduction" if red else "") + (" (SFU layout)" if layout else ""),
                      sub_issues=len(subs), extra_depth=extra, quarter_elements=len(owned), whole_record=whole),
        rf_events=rf_events,
        control_reservation=dict(first=0, last=commit, policy="exclusive_record"),
        expected_post_state=post, expected_post_state_only=True,
        expected_reference=dict(role="comparison_only", source="hdc_golden(+v41 div) KIND-1 lane model"
                                + (" + csum8/ordered max" if red else "")),
        source_contract=dict(lanes="quarter-local 0..31 (KIND 1/2)", divider_depth=19, exp_depth=56,
                             pretree_timing=pretree_profile.as_dict() if pretree_profile else None,
                             sigmoid_silu_depth=78, MLAT=4, ALAT=3, RF_LOCAL=rf_local, B_srcs_code=1 if bcast else 0),
        timing_obligations=dict(issue_to_output=lat, serial_edges=len(lines), stream_edges=math.ceil(4 * len(lines) / 3),
                                old_price_preserved=False, connected_selected_case_RTL_required=True))



# ------------------------------------------------------------------------------------------------------------------
# Scalar side-pipe records on words at ANY sector position (router_act, engram.rH/rK/gate): the side pipe exists only
# in quarter lane 0 (KIND 2) and a lane reads only its own bank, so every input word is moved laterally on real
# hardware: VM sector -> store group -> lane 8p+j copy op -> reducer LOAD of that lane's ro_x (red_cmd osel 0, lane
# 8p+j, at the lane output edge issue+28: su_top_compile's lane-operand rule) -> EXPORT -> stree -> RF word; lane 0 then
# takes each operand as an RF class stream (srcs 1), its side output goes back lane0 -> reducer -> EXPORT -> RF word
# (O.base+j) & 255, and one class-5 RF-sector drain writes all n outputs to their own sector positions.
SIDE_DEPTH = {2: 46, 3: 31, 6: 180, 7: 111}          # lane.sv H_RSQ / H_SQRT / H_SP / H_EG at MLAT 4, ALAT 3


def scalar_rf_profile(sut, desc):
    if sut["red"] or sut["qm"] or sut["b_half"] or sut["c_pair"] or sut["a_ind"] or sut["dst"] != 1 or sut["ad"] == 1:
        return False
    if sut["sfu"] not in SIDE_DEPTH or "O" not in desc or "A" not in desc or not set(desc) <= set("ABCDO"):
        return False
    n = desc["O"].n
    for md in desc.values():
        if (md.space != "VM" or md.fmt != "FP32" or md.m != 1 or md.n != n or (md.istride or 1) != 1 or md.ibcast
                or md.indexed or md.base // 8 != (md.base + n - 1) // 8):
            return False
    return 1 <= n <= 8


def lower_scalar_rf(raw, q=0, data=None, place=None, tag="", timing=None, rf_local=None, **unused):
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    from su_arith_compile import pack, physical_word
    import su_pretree_lower as PT
    _, unit, sut, desc = decode(raw)
    refusal = lambda why, st="unsupported_lowering": dict(status=st, reasons=[why], sut=sut,
                                                          lowering=dict(supported=False, owner="TOK-FUNC2-HBM-SU"))
    if unit != 2 or not scalar_rf_profile(sut, desc):
        return refusal("scalar_side_pipe_small_vector_profile_only")
    if q != 0 or not isinstance(timing, NativeTiming) or timing != NativeTiming(18, 15) or rf_local not in (0, 1):
        return refusal("selected_quarter0_native_timing_and_RF_LOCAL_required")
    if data is None:
        return refusal("real_pre_operation_VM_words_required")
    place = place if place is not None else LI.Placement(q)
    o = desc["O"]
    n = o.n
    roles = [r for r in "ABCD" if r in desc]
    o_rf = o.base & 255
    if (o_rf & 7) + n > 8:
        return refusal("outputs_must_share_one_RF_sector")
    # RF words for the moved inputs: role sectors away from the output sector
    in_rf = {}
    for k, r in enumerate(roles):
        base = ((o_rf & ~7) + 8 * (k + 1)) & 255
        in_rf[r] = [base + ((desc[r].base + j) & 7) for j in range(n)]
    ql = TreeLines()
    # 1. fills: each role's sector into the group of its VM port, row = role index
    fills, preload, lanes, next_fill = [], {}, {}, [0] * 8
    for k, r in enumerate(roles):
        md = desc[r]
        ls_ = md.base // 8
        port = place.map[ls_] % 8 if ls_ in place.map else 0
        ps = place.get(ls_, port, f"{tag}:{r}")
        ql.vmr(next_fill[port], port, ps, port, k)
        fills.append((ls_, next_fill[port]))
        next_fill[port] += 1
        if ls_ not in place.written:
            preload[ps] = list(range(8 * ls_, 8 * ls_ + 8))
        lanes[r] = [8 * port + ((md.base + j) & 7) for j in range(n)]
        for w in range(8 * ls_, 8 * ls_ + 8):
            data.setdefault(w, np.float32(0))
    S1 = max(e for _, e in fills) + timing.fill_commit + 1
    ident = 0
    for s_ in range(4):
        for b in range(7):
            ident |= (1 << b) << (24 * (s_ * 10 + b))
    copies = [(r, j) for r in roles for j in range(n)]
    max_lane = max(l for r in roles for l in lanes[r])
    copy_ctl = dict(no=1, ni=max_lane + 1, ls=7, lvw=7, srcs=0, dst=0, co_dst=0, ld_c=ident)
    ql.f["control"][S1] = pack(dict(copy_ctl, ld=1, vb=sum(physical_word(q, 0) << (24 * s_) for s_ in range(4))))
    exports, red_d, last_load = [], 0, 0
    for c, (r, j) in enumerate(copies):
        k = roles.index(r)
        issue = S1 + LI.SETUP_TO_EMIT + c
        vb = sum(physical_word(q, k) << (24 * s_) for s_ in range(4))
        ql.f["control"][issue] = pack(dict(copy_ctl, emit=1, vb=vb))
        load = issue + LI.FIRST_OUT - LI.SETUP_TO_EMIT
        ql.f["red"][load] = PT.red_cmd_word(dict(op=PT.OP_LOAD, a=0, b=0, d=red_d, tag=0, osel=0, lane=lanes[r][j]))
        ex = load + PT.DEP
        while ex in ql.f["red"]:
            ex += 1
        ql.f["red"][ex] = PT.red_cmd_word(dict(op=PT.OP_EXPORT, a=red_d, b=0, d=0, tag=0x100 | in_rf[r][j], osel=0,
                                               lane=0))
        exports.append(ex)
        red_d += 1
        last_load = load
    for e in range(S1, last_load + 1):
        ql.f["control"].setdefault(e, pack(dict(copy_ctl, vb=sum(physical_word(q, 0) << (24 * s_) for s_ in range(4)))))
    rf_ready = max(exports) + 12 + 32           # rf write pins of the last moved operand
    # 2. scalar side ops on lane 0, operands from the RF
    extra = (15 if sut["m1"] in (4, 5) else 0) + SIDE_DEPTH[sut["sfu"]]
    lat = LI.FIRST_OUT - LI.SETUP_TO_EMIT + extra
    srcs = sum(1 << (2 * "ABCD".index(r)) for r in roles)
    ctl = dict(no=1, ni=1, ls=0, lvw=0, srcs=srcs, dst=0, co_dst=0, aind=0, cpair=0,
               cx_arnd=sut["a_rnd"], cx_arelu=sut["a_relu"], cx_amin=sut["a_min"], cx_cclip=sut["c_clip"],
               cx_imm3=sut["imm3"], cp_m1=sut["m1"], cp_imm1=sut["imm1"], cm_m1=sut["m1"], cm_m2=sut["m2"], cm_qm=0,
               cm_imm1=sut["imm1"], ca_ad=sut["ad"], ca_imm2=sut["imm2"], ci_sfu=sut["sfu"], cs_sfu=sut["sfu"],
               cs_e1=sut["e1"], cs_imm2=sut["imm2"], ce_e2=sut["e2"], ce_imm1=sut["imm1"], co_rnd=sut["rnd"], ld_c=0)

    def vb_op(j):
        v = 0
        for s_, r in enumerate("ABCD"):
            v |= (in_rf[r][j] if r in roles else physical_word(q, 0)) << (24 * s_)
        return v
    S2 = max(last_load + 1, rf_ready + 4 + rf_local)
    ql.f["control"][S2] = pack(dict(ctl, ld=1, vb=vb_op(0)))
    W = LI.FIRST_OUT + 2 + rf_local + LI.SETUP_TO_EMIT   # next op's RF hold starts after this op's ends
    issues, out_ex = [], []
    for j in range(n):
        I = S2 + LI.SETUP_TO_EMIT + j * W
        issues.append(I)
        ql.f["control"][I] = pack(dict(ctl, emit=1, vb=vb_op(j)))
        for e in range(I - LI.SETUP_TO_EMIT - 1 - rf_local, I + LI.FIRST_OUT + 1):
            for r in roles:
                ql.put("rf", e, 9 * "ABCD".index(r), 9, 256 | in_rf[r][j])
        load = I + lat
        if load in ql.f["red"]:
            return refusal("reducer_slot_collision")
        ql.f["red"][load] = PT.red_cmd_word(dict(op=PT.OP_LOAD, a=0, b=0, d=red_d, tag=0, osel=0, lane=0))
        ex = load + PT.DEP
        while ex in ql.f["red"]:
            ex += 1
        ql.f["red"][ex] = PT.red_cmd_word(dict(op=PT.OP_EXPORT, a=red_d, b=0, d=0, tag=0x100 | (o_rf + j), osel=0,
                                               lane=0))
        out_ex.append(ex)
        red_d += 1
    end_ops = max(out_ex)
    for j, I in enumerate(issues):
        nxt = issues[j + 1] if j + 1 < n else end_ops + 1
        for e in range(I, nxt):
            ql.f["control"].setdefault(e, pack(dict(ctl, vb=vb_op(j))))
    for e in range(S2, issues[0]):
        ql.f["control"].setdefault(e, pack(dict(ctl, vb=vb_op(0))))
    rf_commit = end_ops + 12 + 32 + 1
    de = rf_commit + 4
    rf_read = de - 2
    ql.put("rf", rf_read, 5 * 9, 9, 0x100 | (o_rf & ~7))
    lo = o.base // 8
    if lo in place.map and place.map[lo] % 8:
        return refusal("RF_sector_drain_requires_VM_port0_placement")
    po = place.get(lo, 0, tag + ":O")
    mask = sum(1 << ((o.base + j) & 7) for j in range(n))
    ql.vmw(de, 0, 1, 0, 0, po, mask)
    commit = de + timing.drain_done
    for e in range(0, commit + 1):
        ql.f["control"].setdefault(e, pack(dict(ctl, vb=vb_op(n - 1))))
    lines = ql.lines()
    if len(lines) > LI.EDGES_MAX:
        return refusal("native_programme_capacity_exceeded")
    ops = {r: np.array([data[desc[r].base + j] for j in range(n)], np.float32) for r in roles}
    with np.errstate(all="ignore"):
        outbits = sfu_lane_golden(sut, ops)
    if not np.isfinite(outbits.view(np.float32)).all():
        return refusal("finite_side_output_required")
    pre_words = {str(w): f"{int(np.float32(data[w] if w in data else 0).view(np.uint32)):08x}"
                 for ws in preload.values() for w in ws}
    vals = [None] * 8
    post = {}
    for j in range(n):
        vals[(o.base + j) & 7] = int(outbits[j])
        post[str(o.base + j)] = f"{int(outbits[j]):08x}"
        data[o.base + j] = np.uint32(outbits[j]).view(np.float32)
    place.written.add(lo)
    return dict(status="emitted", reasons=[], ql=ql, lines=lines, fills=fills, drains=[(lo, commit)],
        preload=preload, data=pre_words, inputs_placeholder=False,
        expect=[dict(sector=po, mask=mask, edge=commit, words=list(range(8 * lo, 8 * lo + 8)), value=vals)],
        setup_edge=S1, issue_edges=issues, last_commit=commit, fill_sectors=len(preload), drain_sectors=1, sut=sut,
        native_timing=timing.as_dict(),
        lowering=dict(supported=True, owner="TOK-FUNC2-HBM-SU", execution_qualified=False,
                      mode="lane->reducer->stree->RF operand moves; lane0 side pipe on RF streams; RF-sector drain",
                      words=n, side_depth=extra),
        rf_events=[dict(kind="operand_exports", edges=exports), dict(kind="output_exports", edges=out_ex),
                   dict(kind="class5_read", edge=rf_read), dict(kind="RF_to_VM_drain", edge=de, vm_commit=commit)],
        control_reservation=dict(first=0, last=commit, policy="exclusive_record"),
        expected_post_state=post, expected_post_state_only=True,
        expected_reference=dict(role="comparison_only", source="hdc_golden / hdc_golden_v41 side-pipe forms"),
        source_contract=dict(lane_operand_rule="red_cmd osel0 lane L at the lane output edge (su_top_compile S+FO)",
                             side_lane="su_SW0 lane 0 KIND 2", RF_LOCAL=rf_local, side_depth=extra),
        timing_obligations=dict(serial_edges=len(lines), stream_edges=math.ceil(4 * len(lines) / 3),
                                old_price_preserved=False, connected_selected_case_RTL_required=True))


def move_words_to_rf(ql, *, words, rf_addrs, q, data, place, tag, timing, row0=0, edge0=0, red_d0=0):
    """Lateral move of VM words at any sector position into RF words on real hardware: VM sector -> store group of
    its VM port -> copy op (lanes 0..L live) -> reducer LOAD of lane L at the lane output edge -> EXPORT -> stree ->
    RF.  Returns the schedule facts (rf write pins of the last word, last LOAD edge, fills, preload)."""
    from hbm_layer_vehicle import layer_images as LI
    from su_arith_compile import pack, physical_word
    import su_pretree_lower as PT
    secs = sorted({w // 8 for w in words})
    fills, preload, row_of, next_fill = [], {}, {}, [edge0] * 8
    lane_of = {}
    for k, ls_ in enumerate(secs):
        port = place.map[ls_] % 8 if ls_ in place.map else 0
        ps = place.get(ls_, port, f"{tag}:mv")
        row_of[ls_] = row0 + k
        ql.vmr(next_fill[port], port, ps, port, row0 + k)
        fills.append((ls_, next_fill[port]))
        next_fill[port] += 1
        if ls_ not in place.written:
            preload[ps] = list(range(8 * ls_, 8 * ls_ + 8))
        for w in range(8 * ls_, 8 * ls_ + 8):
            data.setdefault(w, np.float32(0))
            lane_of[w] = 8 * port + (w & 7)
    S1 = max(e for _, e in fills) + timing.fill_commit + 1
    ident = 0
    for s_ in range(4):
        for b in range(7):
            ident |= (1 << b) << (24 * (s_ * 10 + b))
    ctl = dict(no=1, ni=max(lane_of[w] for w in words) + 1, ls=7, lvw=7, srcs=0, dst=0, co_dst=0, ld_c=ident)
    vb0 = sum(physical_word(q, row_of[secs[0]]) << (24 * s_) for s_ in range(4))
    ql.f["control"][S1] = pack(dict(ctl, ld=1, vb=vb0))
    exports, last_load, d = [], 0, red_d0
    for c, (w, ra) in enumerate(zip(words, rf_addrs)):
        issue = S1 + LI.SETUP_TO_EMIT + c
        vb = sum(physical_word(q, row_of[w // 8]) << (24 * s_) for s_ in range(4))
        ql.f["control"][issue] = pack(dict(ctl, emit=1, vb=vb))
        load = issue + LI.FIRST_OUT - LI.SETUP_TO_EMIT
        if load in ql.f["red"]:
            raise ValueError("reducer slot busy")
        ql.f["red"][load] = PT.red_cmd_word(dict(op=PT.OP_LOAD, a=0, b=0, d=d, tag=0, osel=0, lane=lane_of[w]))
        ex = load + PT.DEP
        while ex in ql.f["red"]:
            ex += 1
        ql.f["red"][ex] = PT.red_cmd_word(dict(op=PT.OP_EXPORT, a=d, b=0, d=0, tag=0x100 | ra, osel=0, lane=0))
        exports.append(ex)
        d += 1
        last_load = load
    for e in range(S1, last_load + 1):
        ql.f["control"].setdefault(e, pack(dict(ctl, vb=vb0)))
    return dict(rf_ready=max(exports) + 12 + 32, last_load=last_load, fills=fills, preload=preload, exports=exports,
                next_red_d=d, rows_used=len(secs))


def rows_bcast_profile(sut, desc):
    """per-row scalar broadcast B[r] (B stride 1, m rows) on short rows (<= 32 elements): swiglu class"""
    b = desc.get("B")
    if b is None or not b.ibcast or b.m < 2 or b.stride != 1 or b.indexed or "O" not in desc or sut["red"]:
        return False
    if sut["qm"] or sut["b_half"] or sut["c_pair"] or sut["a_ind"] or sut["ad"] == 1 or sut["dst"] != 1:
        return False
    if sut["sfu"] not in SFU_EXTRA or not set(desc) <= set("ABCDO"):
        return False
    n, m = desc["O"].n, desc["O"].m
    if n > SFU_LANES or b.m != m:
        return False
    for r_, md in desc.items():
        if r_ == "B":
            continue
        if (md.space != "VM" or md.fmt != "FP32" or md.n != n or md.m != m or (md.istride or 1) != 1 or md.ibcast
                or md.indexed or md.base % 8 or md.stride % 8 or md.stride < n):
            return False
    return True


def lower_rows_bcast(raw, q=0, data=None, place=None, tag="", timing=None, rf_local=None, **unused):
    from hbm_layer_vehicle import layer_images as LI
    from hbm_layer_vehicle.native_profile import NativeTiming
    from su_program_inventory import decode
    from su_arith_compile import pack, physical_word
    _, unit, sut, desc = decode(raw)
    refusal = lambda why, st="unsupported_lowering": dict(status=st, reasons=[why], sut=sut,
                                                          lowering=dict(supported=False, owner="TOK-FUNC2-HBM-SU"))
    if unit != 2 or not rows_bcast_profile(sut, desc):
        return refusal("per_row_broadcast_short_row_profile_only")
    if q != 0 or not isinstance(timing, NativeTiming) or timing != NativeTiming(18, 15) or rf_local not in (0, 1):
        return refusal("selected_quarter0_native_timing_and_RF_LOCAL_required")
    if data is None:
        return refusal("real_pre_operation_VM_words_required")
    place = place if place is not None else LI.Placement(q)
    o, b = desc["O"], desc["B"]
    n, m = o.n, o.m
    roles = [r_ for r_ in "ACD" if r_ in desc]
    # SFU-layout ports for every row sector (row sector j -> port j), checked before any placement
    for r_ in roles + ["O"]:
        md = desc[r_]
        for i in range(m):
            for j in range(-(-n // 8)):
                ls_ = (md.base + i * md.stride + 8 * j) // 8
                if ls_ in place.map and place.map[ls_] % 8 != j:
                    return refusal(f"operand_{r_}_row_sector_on_port_{place.map[ls_] % 8}_not_{j}", "v1_unsupported")
    rf_b = [((b.base + i) & 255) for i in range(m)]
    ql = TreeLines()
    mv = move_words_to_rf(ql, words=[b.base + i for i in range(m)], rf_addrs=rf_b, q=q, data=data, place=place,
                          tag=tag + ":B", timing=timing)
    row_next = mv["rows_used"]
    rows, fills, preload, next_fill, last_fill = {}, list(mv["fills"]), dict(mv["preload"]), [1] * 8, 0
    for r_ in roles:
        md = desc[r_]
        for i in range(m):
            rows[(r_, i)] = row_next
            row_next += 1
            for j in range(-(-n // 8)):
                first = md.base + i * md.stride + 8 * j
                ls_ = first // 8
                ps = place.get(ls_, j, f"{tag}:{r_}")
                e = next_fill[j]
                next_fill[j] += 1
                ql.vmr(e, j, ps, j, rows[(r_, i)])
                fills.append((ls_, e))
                last_fill = max(last_fill, e)
                if ls_ not in place.written:
                    preload[ps] = list(range(first, first + 8))
                for w in range(first, first + 8):
                    data.setdefault(w, np.float32(0))
    orow = {i: row_next + i for i in range(m)}
    if row_next + m > 512:
        return refusal("store_rows_exceeded")
    terms = 0
    for s_, r_ in enumerate("ABCDO"):
        if r_ == "B":
            continue
        for k in range(7):
            terms |= (1 << k) << (24 * (s_ * 10 + k))
    ctl = dict(no=1, ni=n, ls=5, lvw=5, srcs=1 << 2, dst=1, co_dst=1, aind=0, cpair=0,
               cx_arnd=sut["a_rnd"], cx_arelu=sut["a_relu"], cx_amin=sut["a_min"], cx_cclip=sut["c_clip"],
               cx_imm3=sut["imm3"], cp_m1=sut["m1"], cp_imm1=sut["imm1"], cm_m1=sut["m1"], cm_m2=sut["m2"], cm_qm=0,
               cm_imm1=sut["imm1"], ca_ad=sut["ad"], ca_imm2=sut["imm2"], ci_sfu=sut["sfu"], cs_sfu=sut["sfu"],
               cs_e1=sut["e1"], cs_imm2=sut["imm2"], ce_e2=sut["e2"], ce_imm1=sut["imm1"], co_rnd=sut["rnd"],
               ld_c=terms)

    def vb_of(i):
        v = 0
        for s_, r_ in enumerate("ABCDO"):
            if r_ == "O":
                v |= physical_word(q, orow[i]) << (24 * s_)
            elif r_ == "B":
                v |= rf_b[i] << (24 * s_)
            else:
                v |= physical_word(q, rows[(r_ if r_ in roles else roles[0], i)]) << (24 * s_)
        return v
    S2 = max(last_fill + timing.fill_commit + 1, mv["rf_ready"] + 4 + rf_local, mv["last_load"] + 1)
    ql.f["control"][S2] = pack(dict(ctl, ld=1, vb=vb_of(0)))
    extra = (15 if sut["m1"] in (4, 5) else 0) + SFU_EXTRA[sut["sfu"]]
    lat = LI.FIRST_OUT - LI.SETUP_TO_EMIT + extra
    W = LI.FIRST_OUT + 2 + rf_local + LI.SETUP_TO_EMIT
    issues = []
    for i in range(m):
        I = S2 + LI.SETUP_TO_EMIT + i * W
        issues.append(I)
        ql.f["control"][I] = pack(dict(ctl, emit=1, vb=vb_of(i)))
        for e in range(I - LI.SETUP_TO_EMIT - 1 - rf_local, I + LI.FIRST_OUT + 1):
            ql.put("rf", e, 9, 9, 256 | rf_b[i])
    for i, I in enumerate(issues):
        nxt = issues[i + 1] if i + 1 < m else I + 1
        for e in range(I, nxt):
            ql.f["control"].setdefault(e, pack(dict(ctl, vb=vb_of(i))))
    ops = {}
    for r_ in roles:
        md = desc[r_]
        ops[r_] = np.array([[data[md.base + i * md.stride + e] for e in range(n)] for i in range(m)], np.float32)
    ops["B"] = np.array([[data[b.base + i]] * n for i in range(m)], np.float32)
    with np.errstate(all="ignore"):
        outbits = np.stack([sfu_lane_golden(sut, {k: v[i] for k, v in ops.items()}) for i in range(m)])
    drain_e, expect, drains, commits, post = [0] * 8, [], [], [], {}
    for i in range(m):
        ready = issues[i] + lat + 1
        for j in range(-(-n // 8)):
            lo = 8 * j
            msk = [lo + t < n for t in range(8)]
            de = max(ready, drain_e[j])
            drain_e[j] = de + 1
            first = o.base + i * o.stride + lo
            ls_ = first // 8
            ps = place.get(ls_, j, f"{tag}:O")
            mask = sum(1 << t for t in range(8) if msk[t])
            ql.vmw(de, j, 0, j, orow[i], ps, mask)
            c = de + timing.drain_done
            commits.append(c)
            drains.append((ls_, c))
            expect.append(dict(sector=ps, mask=mask, edge=c, words=list(range(first, first + 8)),
                               value=[int(outbits[i][lo + t]) if msk[t] else None for t in range(8)]))
    commit = max(commits)
    for e in range(0, commit + 1):
        ql.f["control"].setdefault(e, pack(dict(ctl, vb=vb_of(m - 1))))
    lines = ql.lines()
    if len(lines) > LI.EDGES_MAX:
        return refusal("native_programme_capacity_exceeded")
    pre_words = {str(w): f"{int(np.float32(data[w] if w in data else 0).view(np.uint32)):08x}"
                 for ws in preload.values() for w in ws}
    for ls_, _ in drains:
        place.written.add(ls_)
    for i in range(m):
        for e in range(n):
            a_ = o.base + i * o.stride + e
            post[str(a_)] = f"{int(outbits[i][e]):08x}"
            data[a_] = np.uint32(outbits[i][e]).view(np.float32)
    return dict(status="emitted", reasons=[], ql=ql, lines=lines, fills=fills, drains=drains, preload=preload,
        data=pre_words, inputs_placeholder=False, expect=expect, setup_edge=S2, issue_edges=issues, last_commit=commit,
        fill_sectors=len(preload), drain_sectors=len(expect), sut=sut, native_timing=timing.as_dict(),
        lowering=dict(supported=True, owner="TOK-FUNC2-HBM-SU", execution_qualified=False,
                      mode="per-row B[r] lane->reducer->RF moves + KIND1 32-lane rows with class-1 RF stream",
                      rows=m, extra_depth=extra),
        rf_events=[dict(kind="B_exports", edges=mv["exports"])],
        control_reservation=dict(first=0, last=commit, policy="exclusive_record"),
        expected_post_state=post, expected_post_state_only=True,
        expected_reference=dict(role="comparison_only", source="hdc_golden(+v41) KIND-1 lane model, per-row B"),
        source_contract=dict(RF_LOCAL=rf_local, B_srcs_code=1, lanes="quarter-local 0..31"),
        timing_obligations=dict(serial_edges=len(lines), stream_edges=math.ceil(4 * len(lines) / 3),
                                old_price_preserved=False, connected_selected_case_RTL_required=True))
