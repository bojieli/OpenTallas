#!/usr/bin/env python3
"""DIE-HBM-97/HBM-TAPS 2026-11-11 (COORD 11-10 21:01 ruling (3)): next HBM plan event on top of ftres+PGR.  DO_NOT_COUNT.

  python3 -I mk_plan_taps_cyc.py BASE_DIR OUT_DIR IN_DIR       (OUT_DIR = a fresh full copy of BASE_DIR)

IN_DIR holds read-only copies (sha256 recorded in the event):
  DIE-RECHECK-TAPS.tsv            hub ~/coord/lanes copy (DIE-RECHECK-1, k_die 0.845)
  expx_signoff.json, s3q_signoff.json          the two signed records (intel1, read-only copies)
  expx_face_shell.json, s3q_face_shell.json    the kits' face shells (signal input buses, passthrough pins)

(1) PER-CORE EARLY TAPS (METHODOLOGY 12.3 v5.0): every core tap (kind core, type clock.core_taps 'early') of a module in
    the table gets insertion_ps / insertion_ff_ps = the MEASURED pin-register insertion of its signed (or NEAR-CLOSE) view
    and an insertion_basis naming the view; gen_phys / plan_gen_rules.core_io_insertion then give early_tap_ps =
    TT - common (250) on the die side and the same value to the core kit IO vclk (--io-insertion plan).  One value per
    module (core_io_insertion() refuses disagreeing taps).  Measured beats Rule A's 12.9d model and older measured taps
    (the signed view is the one the die uses).  Partition type q_mca: its own clock.insertion_ps / insertion_ff_ps
    (the vsN4 form).  vsN4 keeps form C 380 (its plan form; the formB view describes another form).  Listed, not set:
    q3bc body_ctl (early tap 454 > T/2 416.5, the Rule A guard: die-owner form) and ot_smh_static_front_w (SF-SPLIT W
    half is not a plan core; no plan tap).
(2) PIN CYCLES: +1 input relay stage after the face flop (kit --face-in-stage BUSRE=1, face_shell in_stages) on the
    failing signal input buses of ot_hbm_su_pg_lane_exp_x_core and ot_hidx_s3_q = the signed record's STD_MIN_START
    port list minus clock/reset passthrough pins and minus parent-tied ID straps (plan parent_id_straps: constant,
    no die hold race).  Carried as event core_kit_args + corelat/cycles_hbmtaps_1111.tsv + compiler_core_delta
    pending_not_folded (die_plan.json has no core-cycle field; kshare_pc_1109 precedent).
No RTL / pin table / outline / station / lane change in die_plan.json.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

BASE_SHA = "8955a4efd6351a63ad1a1f737f43c5743bd7fd059c03ad570df1f7f7f6981a93"
TSV_SHA = "26d6663607007ff6810da631cb4c80f641759f3e14c33df06be62dc0ff1ee0c6"
EV = "hbm-taps-cycles-1111"
TAG = "DIE-HBM-97/HBM-TAPS 11-11 (COORD 11-10 21:01 ruling 3)"
COMMON, PERIOD = 250.0, 833.0

# module -> exact TSV design string chosen (where a module has 2 rows, the reason is in WHY)
TAPS = {
    "ot_q2nf_rest": "ot_q2nf_rest split kit_bd2 (vG2 row select on bd half)",
    "ot_hgi_sfu_opsb_output": "ot_hgi_sfu_opsb_output",
    "ot_hfd_coll_q3_vm_core": "ot_hfd_coll_q3_vm_core",
    "ot_hbm_idx_rootctl_static_am": "ot_hbm_idx_rootctl_static_am",
    "ot_hbm_su_pg_lane1p_core": "ot_hbm_su_pg_lane1p_core L1P-HS (D2L + HB4 pad per zero-logic hop, COORD structural form)",
    "ot_hbm_hc_bank128_pair_first_core": "ot_hbm_hc_bank128_pair_first_core",
    "ot_hbm_su_pg_lane1_core": "ot_hbm_su_pg_lane1_core",
    "ot_q2nf_qout": "ot_q2nf_qout",
    "hfd_ep_static": "hfd_ep_static",
    "ot_hbm_accel_smh_xs": "ot_hbm_accel_smh_xs",
    "ot_hgi_sm_xload_cl2_bfqg": "ot_hgi_sm_xload_cl2_bfqg",
    "ot_hbm_su_static_sfustore_hw": "ot_hbm_su_static_sfustore_hw",
    "ot_hgi_sm_xload_cl2_ctlx": "ot_hgi_sm_xload_cl2_ctlx",
    "ot_svgr_bk": "ot_svgr_bk",
    "ot_hbm_host_cp_rxs": "ot_hbm_host_cp_rxs",
    "ot_hbm_sm_vm_wr_q_t_lanes4": "ot_hbm_sm_vm_wr_q_t_lanes4",
    "ot_svgr_own": "ot_svgr_own",
    "ot_hbm_accel_smh_pt_e": "ot_hbm_accel_smh_pt_e",
    "ot_hbm_su_static_cxport_ij_q": "ot_hbm_su_static_cxport_ij_q",
    "ot_hbm_su_pcol_l": "ot_hbm_su_pcol_l",
    "ot_hbm_svc_sm_xcal_rel_t": "ot_hbm_svc_sm_xcal_rel_t",
    "ot_hbm_su_pcol_s": "ot_hbm_su_pcol_s",
    "ot_hbm_su_pg_lane_exp_x_core": "ot_hbm_su_pg_lane_exp_x_core",
    "ot_hbm_svc_pc_ctrl_leaf_cfg_h9b": "ot_hbm_svc_pc_ctrl_leaf_cfg_h9b",
    "ot_hfd_coll_q3_qcol4": "ot_hfd_coll_q3_qcol4",
    "ot_hfd_coll_q3_edge_link": "ot_hfd_coll_q3_edge_link",
    "ot_hnx_idxn_keybuf_slice": "ot_hnx_idxn_keybuf_slice",
    "ot_hgi_coll_inj_idx_join_rg": "ot_hgi_coll_inj_idx_join_rg",
    "ot_hgi_sfu_split3_lane_core_fr": "ot_hgi_sfu_split3_lane_core_fr",
    "ot_hidx_s3_q": "ot_hidx_s3_q",
    "ot_hfd_coll_q2_hard_v8g__reduce": "ot_hfd_coll_q2_hard_v8g__reduce",
    "ot_hbm_svc_vmdel_lane_n": "ot_hbm_svc_vmdel_lane_n",
    "ot_hgi_sfu_split3_lane_core_ex": "ot_hgi_sfu_split3_lane_core_ex",
    "ot_hbm_hc_bank128_pair_core": "ot_hbm_hc_bank128_pair_core#250.56x267.84/10ac9d744407ff50",
}
WHY = {
    "ot_hfd_coll_q3_vm_core": "SIGNED view used; NEAR-CLOSE vL repeater pitch 484.4/388.1 is 1.8 ps lower",
    "ot_hbm_idx_rootctl_static_am": "SIGNED view rootctl_E_so used; NEAR-CLOSE e1 ECO2 461.9/370.1 replaces it only if it becomes the counted view",
    "ot_hbm_su_pg_lane1p_core": "L1P-HS (HBM-COLLECT-1 READY-COUNT 11-10 17:52, the counted form); D2L 421.6/332.9 not used",
    "ot_hbm_hc_bank128_pair_core": "two SIGNED pin variants 291.6/234.5 (10ac9d74) and 290.1/234.1 (7eaeff6b): one value per module "
                                   "(core_io_insertion), the larger one; spread 1.5 ps",
    "ot_q2nf_rest": "NEAR-CLOSE split kit_bd2 (the only measured ot_q2nf_rest view)",
}
TYPES = {"q_mca": "q_mca"}                       # partition type -> TSV design (type clock.insertion_ps form)
KEEP = {"vsN4": "form C insertion 380 (plan form, DIE-HBM-97/VSN4 basis) kept; the TSV row is form B (362.1/284.6), "
                "a different form, not the plan's kit"}
LISTED = {
    "ot_hfd_coll_q3_body_ctl q3bc_CF2 build": "early tap 454.3 > T/2 416.5: Rule A guard (a tap moved by more than half "
                                             "a cycle changes the related edge) -> die-owner form, not planned",
    "ot_smh_static_front_w SF-SPLIT W half (COORD form b)": "SF-SPLIT W half is not a core of this plan (plan has "
                                                           "ot_smh_static_front, Rule A listed multi-tree): no plan tap",
}
CYCLE_CORES = {"ot_hbm_su_pg_lane_exp_x_core": ("expx_signoff.json", "expx_face_shell.json", -42.7),
               "ot_hidx_s3_q": ("s3q_signoff.json", "s3q_face_shell.json", -39.0)}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def core_of(t, tp):
    nm = str(tp.get("name", ""))
    for hc in t.get("hard_cores", []) or []:
        if nm == hc["inst"] or nm.startswith(hc["inst"] + "."):
            return hc
    return None


def strip(t):
    w = json.loads(json.dumps(t))
    ck = w.get("clock") or {}
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") == "core":
            for k in ("insertion_ps", "insertion_ff_ps", "insertion_basis"):
                tp.pop(k, None)
    return w


def main(base, out, ind):
    base, out, ind = Path(base), Path(out), Path(ind)
    bp, op = base / "die_plan.json", out / "die_plan.json"
    raw = bp.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA, "base plan sha changed"
    assert op.read_bytes() == raw, "OUT_DIR must be a fresh copy of BASE_DIR"
    assert sha(ind / "DIE-RECHECK-TAPS.tsv") == TSV_SHA, "tap table changed"
    P0 = json.loads(raw)
    assert (json.dumps(P0, indent=1) + "\n").encode() == raw, "base serialization is not indent=1"
    P = json.loads(raw)
    assert float(P["clock"]["common_latency_ps"]) == COMMON
    rows = {}
    for ln in (ind / "DIE-RECHECK-TAPS.tsv").read_text().splitlines():
        f = ln.split("\t")
        if len(f) >= 11 and f[0] == "hbm":
            rows[f[1]] = dict(label=f[2], tt=float(f[4]), ff=float(f[5]), e_tt=float(f[6]), e_ff=float(f[7]),
                              xc=f[8], ph=f[9], view=f[10])
    assert len(rows) == 42, len(rows)
    used = set(TAPS.values()) | set(TYPES.values()) | set(LISTED)
    vs = [k for k in rows if k.startswith("vsN4")]
    assert len(vs) == 1
    covered = used | set(vs) | {"ot_hfd_coll_q3_vm_core vL repeater pitch", "ot_hbm_idx_rootctl_static_am e1 ECO2",
                                "ot_hbm_su_pg_lane1p_core D2L (D2 physical + LID_COPY)",
                                "ot_hbm_hc_bank128_pair_core#250.56x267.84/7eaeff6b21f398a7"}
    assert covered == set(rows), sorted(set(rows) ^ covered)
    table = []
    pt = P["partition_types"]
    for mod, dkey in TAPS.items():
        r = rows[dkey]
        assert r["e_tt"] > 40 and r["e_tt"] <= PERIOD / 2, (mod, r)
        assert 0 < r["ff"] <= r["tt"]
        n, olds, types_ = 0, set(), set()
        basis = (f"{TAG}: measured {r['label']} view {r['view']} pin-register insertion TT {r['tt']:g} / FF {r['ff']:g} "
                 f"(lanes/DIE-RECHECK-TAPS.tsv, e_tt {r['e_tt']:g}, early tap {r['tt'] - COMMON:.1f})"
                 + (f"; {WHY[mod]}" if mod in WHY else ""))
        for tn, t in pt.items():
            ck = t.get("clock") or {}
            for tp in ck.get("taps", []) or []:
                if tp.get("kind") != "core":
                    continue
                hc = core_of(t, tp)
                if ((hc or {}).get("module") or tp.get("budget_owner")) != mod:
                    continue
                assert ck.get("core_taps") == "early", (mod, tn)
                olds.add((tp.get("insertion_ps"), tp.get("insertion_ff_ps"), (tp.get("insertion_basis") or
                          ("plan tap note: " + (tp.get("note") or "")[-90:]))[:160]))
                tp["insertion_ps"], tp["insertion_ff_ps"], tp["insertion_basis"] = r["tt"], r["ff"], basis
                n += 1
                types_.add(tn)
        assert n > 0, f"{mod}: no plan core tap"
        table.append(dict(module=mod, design=dkey, label=r["label"], view=r["view"], tt=r["tt"], ff=r["ff"],
                          e_tt=r["e_tt"], early_tap_ps=round(r["tt"] - COMMON, 1), taps=n, types=sorted(types_),
                          before=sorted([list(o) for o in olds], key=str), note=WHY.get(mod, "")))
    for tn, dkey in TYPES.items():
        r = rows[dkey]
        ck = pt[tn]["clock"]
        assert not pt[tn].get("hard") and "insertion_basis" not in ck and float(ck.get("insertion_ps", COMMON)) == COMMON
        before = [ck.get("insertion_ps"), ck.get("insertion_ff_ps")]
        ck["insertion_ps"], ck["insertion_ff_ps"] = r["tt"], r["ff"]
        ck["insertion_basis"] = (f"{TAG}: measured {r['label']} partition view {r['view']} pin-register insertion TT "
                                 f"{r['tt']:g} / FF {r['ff']:g} (e_tt {r['e_tt']:g}); die tap delay absorbs early_tap_ps "
                                 f"{r['tt'] - COMMON:.1f} (12.3 v5.0, vsN4 form)")
        table.append(dict(type=tn, design=dkey, label=r["label"], view=r["view"], tt=r["tt"], ff=r["ff"], e_tt=r["e_tt"],
                          early_tap_ps=round(r["tt"] - COMMON, 1), before=before))
    # agreement per module (plan_gen_rules.core_io_insertion contract) and preservation
    for row in table:
        if "module" not in row:
            continue
        seen = set()
        for tn, t in pt.items():
            for tp in (t.get("clock") or {}).get("taps", []) or []:
                if tp.get("kind") == "core" and ((core_of(t, tp) or {}).get("module") or tp.get("budget_owner")) == row["module"]:
                    seen.add((tp["insertion_ps"], tp["insertion_ff_ps"]))
        assert seen == {(row["tt"], row["ff"])}, (row["module"], seen)
    for k in P0:
        if k != "partition_types":
            assert json.dumps(P0[k], sort_keys=True) == json.dumps(P[k], sort_keys=True), k
    for tn in P0["partition_types"]:
        a, b = strip(P0["partition_types"][tn]), strip(pt[tn])
        if tn in TYPES:
            for k in ("insertion_ps", "insertion_ff_ps", "insertion_basis"):
                a["clock"].pop(k, None); b["clock"].pop(k, None)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), f"type {tn} changed beyond the event keys"
    data = (json.dumps(P, indent=1) + "\n").encode()
    op.write_bytes(data)
    with gzip.GzipFile(str(out / "die_plan.json.gz"), "wb", compresslevel=9, mtime=0) as g:
        g.write(data)
    aff = sorted(tn for tn in P0["partition_types"]
                 if json.dumps(P0["partition_types"][tn], sort_keys=True) != json.dumps(pt[tn], sort_keys=True))

    # ---------------------------------------------------------------- (2) pin cycles on the two cores
    cyc, tsv = {}, ["core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote"]
    for mod, (so_f, fs_f, dh) in CYCLE_CORES.items():
        so, fs = json.loads((ind / so_f).read_text()), json.loads((ind / fs_f).read_text())
        assert fs["module"] == mod and fs["latency"]["in_cycles"] == 1
        ff = so["corners"]["ff"]
        st = ff["std_min_start"]
        assert st["other"] == 0 and st["reg"] == 0 and st["port"] > 0, st
        failing = sorted(set(st["ports"]))
        passthru = set(fs["passthrough"])
        straps = set()
        for t in pt.values():
            for hc in t.get("hard_cores", []) or []:
                if hc.get("module") == mod:
                    straps |= set((hc.get("parent_id_straps") or {}).keys())
        sig_in = sorted(n for n, d in fs["dirs"].items() if d == "input" and n not in passthru and fs["keep"].get(n, 0) > 0)
        stage = [n for n in failing if n in sig_in and n not in straps]
        not_staged = {n: ("clock/reset passthrough (face reset relay / pass-through): not a data stage" if n in passthru
                          else "parent-tied ID strap (plan parent_id_straps): constant, no die hold race" if n in straps
                          else "not a kept signal input") for n in failing if n not in stage}
        assert set(stage) | set(not_staged) == set(failing)
        rx = "^(" + "|".join(stage) + ")$"
        bits = sum(int(fs["keep"][n]) for n in stage)
        cyc[mod] = dict(record=dict(file=so_f, sha256=sha(ind / so_f), std_min_start=st, hold_wns_ff=ff["std_wns_min"],
                                    hold_nviol_ff=ff["std_nviol_min"], overlay=ff["overlay"]),
                        face_shell=dict(file=fs_f, sha256=sha(ind / fs_f), in_buses=fs["in_buses"], in_bits=fs["in_bits"]),
                        die_hold_ff_nominal_dierecheck=dh, staged_buses=stage, staged_bits=bits, not_staged=not_staged,
                        kit_arg=["--face-in-stage", f"{rx}=1"], in_cycles_after=2, out_cycles_after=1)
        tsv.append(f"{mod}\t\t{','.join(stage)}\tport\t1\t{TAG}: +1 input relay stage after the face flop "
                   f"(kit --face-in-stage, face_shell in_extra_stages) on the signed record's failing port-start hold "
                   f"inputs ({st['port']:g} violators, FF WNS {ff['std_wns_min']:g}); DIE-RECHECK die hold {dh:g} nominal")
        for n, why in not_staged.items():
            tsv.append(f"{mod}\t\t{n}\tport\t0\t{TAG}: {why}")
    (out / "corelat").mkdir(exist_ok=True)
    (out / "corelat" / "cycles_hbmtaps_1111.tsv").write_text("\n".join(tsv) + "\n")
    cd = json.loads((base / "compiler_core_delta.json").read_text())
    cd.setdefault("pending_not_folded", {})[EV] = (
        "ot_hbm_su_pg_lane_exp_x_core: +1 on every staged signal input (corelat/cycles_hbmtaps_1111.tsv) -> S2 extra SU "
        "+1 per SU record (max lane leg; bound = expected); ot_hidx_s3_q: +1 on cw/thr/ties/in_line -> S2 extra IDX +1 per "
        "IDX record (serial IDX chain, like HBM-31).  Folds into S2 extra at the TOK-VERIFY-1 reschedule; ext census regen "
        "with --core-lat corelat/*.tsv.")
    (out / "compiler_core_delta.json").write_text(json.dumps(cd, indent=1) + "\n")

    kit_args = {row["module"]: ["--io-tt-ps", f"{row['tt']:g}", "--io-ff-ps", f"{row['ff']:g}"] for row in table if "module" in row}
    for mod, c in cyc.items():
        kit_args[mod] = kit_args[mod] + c["kit_arg"]
    ev = dict(schema="opentallas.hbm_plan_event.v1", event=EV, by="DIE-HBM-97/HBM-TAPS", do_not_count=True,
              ruling="COORD 2026-11-10 21:01 RULING (3) + DIE-HBM-97 brief: per-core tap table from lanes/DIE-RECHECK-TAPS.tsv "
                     "and +1 pin cycles on su_pg_lane_exp_x / hidx_s3_q in the next HBM event after ftres+PGR",
              base_plan=str(bp), base_sha256=BASE_SHA, plan=str(op), plan_sha256=hashlib.sha256(data).hexdigest(),
              tool="mk_plan_taps_cyc.py", tool_sha256=sha(Path(__file__)),
              inputs={p.name: sha(p) for p in sorted(ind.iterdir()) if p.is_file()},
              taps=table, kept=KEEP, listed=LISTED, affected_types=aff,
              affected_cores=sorted(r["module"] for r in table if "module" in r),
              tap_types=sorted(r["type"] for r in table if "type" in r),
              core_kit_args=kit_args, pin_cycles=cyc, rtl_change="core face shell only (two cycle cores, kit-generated)",
              die_plan_change="clock insertion keys only (core taps + q_mca type)", data_cycles=0,
              serialization="json indent=1 newline (base style)")
    (out / "taps_cyc_1111_event.json").write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps(dict(plan_sha256=ev["plan_sha256"], modules=len(ev["affected_cores"]),
                          taps=sum(r.get("taps", 0) for r in table), types=len(aff),
                          cycles={m: (len(c["staged_buses"]), c["staged_bits"]) for m, c in cyc.items()})))


if __name__ == "__main__":
    main(*sys.argv[1:4])
