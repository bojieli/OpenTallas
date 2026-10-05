#!/usr/bin/env python3
"""DS HBM accelerator: exact-lever composition for the HBM counterparts of the DS ROM levers (design record
results/rtl/dshbm_hbm_opt_20261005/).  Light: composes from committed records only.

Basis: the matched DS HBM reference (results/rtl/dshbm_matched_reference_20261005/composition.json; gate AR 474.808 us,
row corrected+wg+fused_su0.9; gate MTP step 1,050.638 us, row corrected+wg+su12).  Both gate rows include the expert
workgroup (L1) and have identical SM rows at 1.2 GHz.

(1) PIPELINED ISSUE (measured).  The PQ element (rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv) runs the busiest SM's op
    sequences with the PQ protocol (tools/dshbm_sm_pq_seq.py; records pq/*.json, bit-exact).  For every run of
    INDEPENDENT matvecs (the program's matvecs between two collective / local ops) the walk's charge (its xload + sm +
    barrier rows, re-walked here with dshbm_matched_reference.walk) is replaced by the measured PQ group: first op's
    x-load start -> last op's completion, + 1 handshake + one barrier (62 + 4).  Runs:
      GU      routed gate/up workgroup + shared-expert w1, w3 (40 MoE layers)      record pq wg
      W2      7 expert w2 matvecs (40 MoE layers)                                  record pq ar_l20 ops w2
      ATTN4   wq_a, wkv, compressor.wkv, indexer.weights_proj (4 layers)         record pq ar_l20 ops 1-4
      ATTN3   wq_a, wkv, indexer.weights_proj (4 layers): the measured prefix wq_a, wkv, compressor.wkv (its third
              op loads the same BF16 K 5,120 x as weights_proj does in these layers)
      ATTN2   wq_a, wkv (32 layers): the measured prefix wq_a, wkv
    The attention runs are flush groups of one op each in the walk (one barrier per op); under PQ they are one group
    with one barrier (their results all feed x_projections_gather).  Single-op groups are unchanged.
    A serial-protocol run of the same element (--serial) cross-checks that the PQ element's per-op cost equals the
    walk's (start-channel overhead).
(3) ACTIVATION DELIVERY (composed from the measured 1 beat/cycle x-write port): a FORMAT-MASKED x-write port packs
    only the op's used fragment fields of the active columns (block-dot 8 x 266 b for FP4, 4 x 266 b for FP8, BF16
    64 x 16 b) instead of the full 3,152-bit column fragment, so beats/address = ceil(active * used / 2048): P1 FP4 2,
    FP8 1, BF16 1 (as-built 2); P6 FP4 7, FP8 4, BF16 3 (as-built 10).  And a 4,096-bit port (as-built layout).
    The walk is re-run with every load = addresses x beats + 1 (the measured load law, sm_seq records).

    python3 tools/dshbm_hbm_opt_compose.py [--out results/rtl/dshbm_hbm_opt_20261005/composition.json]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_1m_allmeasured as A  # noqa: E402
import dshbm_chain_levers as CL  # noqa: E402
import dshbm_baseline_measure as DM  # noqa: E402
import dshbm_matched_reference as M  # noqa: E402

REC = ROOT / "results/rtl/dshbm_hbm_opt_20261005"
MREC = M.REC
F_SM = 1.2e9
BARRIER = M.BARRIER_SYNC + 4
XC = 3152
USED = dict(fp4=8 * 266, fp8=4 * 266, bf16=64 * 16)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


# ---------------------------------------------------------------------------------------------------------------------
def setup():
    prog = json.loads((A.BASE / "program.json").read_text())
    su1, su6, _, _ = A.su_tables()
    coll = A.Coll(A.load(M.INH / "collectives.json"))
    local = A.Local(A.load(M.INH / "local.json"))
    hbm = A.Hbm(A.load(M.INH / "hbm_streams.json"))
    smseq = M.SMSeq(sorted((MREC / "sm_seq").glob("*_nc8_a*.json")))
    m6 = MREC / "su_m6a5"
    s1 = CL.best_of([("dr", json.loads((m6 / "su_N1024_M256_b7r8m6a5_dpi_beh_su_cases_v2_ildr.json").read_text()))])
    s6 = CL.best_of([("dr", json.loads((m6 / "su_N1024_M256_b7r8m6a5_dpi_beh_su_cases_p6om_ildr.json").read_text()))])
    su12 = (CL.su_table_overlap(s1), CL.su_table_overlap(s6))
    fused = M.load_fused(MREC / "su_fused" / "fused.json")
    return dict(prog=prog, su1=su1, su6=su6, su12=su12, coll=coll, local=local, hbm=hbm, smseq=smseq, fused=fused)


def gate_rows(S, smseq=None):
    """The two gate rows of the matched reference: AR (corrected+wg+fused_su0.9) and MTP (corrected+wg+su12)."""
    smseq = smseq or S["smseq"]
    use = ("coll", "local", "hbm", "mixes")
    T = dict(A.TARGET)
    T12 = dict(T, su=1.2e9, du_ser=M.F_SER)
    ar, rows1 = M.walk(S["prog"], smseq, S["su1"], S["coll"], S["local"], S["hbm"], P=1, clk=T, use=use, wg=True,
                       fused=S["fused"])
    mm, rows6 = M.mtp(S["prog"], smseq, S["su12"][1], S["coll"], S["local"], S["hbm"], T12, use, True, None)
    return round(ar, 3), mm, rows1, rows6


# ---------------------------------------------------------------------------------------------------------------------
def sm_groups(rows):
    """Walk rows -> [(layer, tag, us)] per flush group (xload + sm + barrier rows)."""
    out, i = [], 0
    while i < len(rows):
        r = rows[i]
        if r["node"].startswith("xload:"):
            tag = r["node"][6:]
            assert rows[i + 1]["node"] == "sm:" + tag and rows[i + 2]["node"] == "barrier", (rows[i + 1], rows[i + 2])
            out.append((r["layer"], tag, r["us"] + rows[i + 1]["us"] + rows[i + 2]["us"]))
            i += 3
        else:
            i += 1
    return out


def pq_group(rec, first, last):
    """Measured PQ group cycles: first op's x-load start -> last op's completion (pins), exactness asserted."""
    assert rec["status"] == "pass" and rec["mismatching_ops"] == 0, rec.get("seq")
    ops = rec["ops"]
    for o in ops[first:last + 1]:
        assert o["exact"] and o["mismatches"] == 0 and o["results"] == o["rows"], o["tag"]
    return ops[last]["rtl"]["t_done"] - ops[first]["rtl"]["t_load0"]


def idx(rec, tag):
    return next(o["op"] for o in rec["ops"] if o["tag"] == tag)


ATTN = ("wq_a", "wkv", "compressor.wkv", "compressor.wkv|wgate", "indexer.weights_proj")


def item1(S, rows, recs, P):
    """Replace the walk's charge of every independent run by its measured PQ group."""
    l20, wg = recs["l20"], recs["wg"]
    k = dict(wq_a=idx(l20, "wq_a"), wkv=idx(l20, "wkv"), cw=idx(l20, "compressor.wkv"),
             wp=idx(l20, "indexer.weights_proj"), w2a=idx(l20, "expert slot 0 w2"), w2z=idx(l20, "expert slot 6 w2"))
    cyc = dict(ATTN2=pq_group(l20, k["wq_a"], k["wkv"]), ATTN3=pq_group(l20, k["wq_a"], k["cw"]),
               ATTN4=pq_group(l20, k["wq_a"], k["wp"]), W2=pq_group(l20, k["w2a"], k["w2z"]),
               GU=pq_group(wg, idx(wg, "routed gate/up workgroup (12 matrices)"), idx(wg, "expert slot 6 w3")))
    pq_us = {g: (c + M.HANDSHAKE + BARRIER) / F_SM * 1e6 for g, c in cyc.items()}
    groups = sm_groups(rows)
    by_layer = {}
    for L, tag, us in groups:
        by_layer.setdefault(L, []).append((tag, us))
    saved, n, detail = 0.0, {}, {}
    for L, lst in by_layer.items():
        attn = [(t, u) for t, u in lst if t.split()[0] in ATTN or t in ATTN]
        if len(attn) >= 2:
            g = {2: "ATTN2", 3: "ATTN3", 4: "ATTN4"}[len(attn)]
            if g == "ATTN3":
                assert [t for t, _ in attn] == ["wq_a", "wkv", "indexer.weights_proj"], attn
            d = sum(u for _, u in attn) - pq_us[g]
            saved += d; n[g] = n.get(g, 0) + 1; detail.setdefault(g, []).append(round(d, 4))
        for t, u in lst:
            g = "GU" if t == "routed gate/up workgroup" else "W2" if t == "expert slot 0 w2" else None
            if g:
                d = u - pq_us[g]
                saved += d; n[g] = n.get(g, 0) + 1; detail.setdefault(g, []).append(round(d, 4))
    per = {g: dict(layers=n.get(g, 0), pq_group_cycles=cyc[g], pq_group_us=round(pq_us[g], 4),
                   walk_minus_pq_us_each=sorted(set(detail.get(g, []))),
                   saved_us=round(sum(detail.get(g, [])), 3)) for g in cyc}
    return round(saved, 3), per


def serial_check(rows, recs_serial):
    """PQ element in the serial protocol vs the walk's per-group charge (same groups): the PQ start channel's cost."""
    out = {}
    if not recs_serial:
        return None
    l20 = recs_serial["l20"]
    w2 = pq_group(l20, idx(l20, "expert slot 0 w2"), idx(l20, "expert slot 6 w2"))
    walk_w2 = next(u for _, t, u in sm_groups(rows) if t == "expert slot 0 w2")
    out["W2"] = dict(serial_pq_cycles=w2, serial_pq_plus_handshake_barrier_us=round((w2 + 1 + BARRIER) / F_SM * 1e6, 4),
                     walk_us=round(walk_w2, 4))
    wg = recs_serial["wg"]
    gu = pq_group(wg, idx(wg, "routed gate/up workgroup (12 matrices)"), idx(wg, "expert slot 6 w3"))
    walk_gu = next(u for _, t, u in sm_groups(rows) if t == "routed gate/up workgroup")
    out["GU"] = dict(serial_pq_cycles=gu, serial_pq_plus_handshake_barrier_us=round((gu + 1 + BARRIER) / F_SM * 1e6, 4),
                     walk_us=round(walk_gu, 4))
    return out


# ---------------------------------------------------------------------------------------------------------------------
NC = 8


def static_intervals(fmt, act):
    """Bit intervals of the beat space a format-masked x write fills under the STATIC leaf map (no mux): BF16 lanes of
    column n at n*1024; block-dot block J of column n at (J div 4)*NC*1064 + n*1064 + (J mod 4)*266 (FP8 uses J < 4,
    FP4 both halves)."""
    if fmt == "bf16":
        return [(0, act * 1024)]
    iv = [(0, act * 1064)]
    if fmt == "fp4":
        iv.append((NC * 1064, NC * 1064 + act * 1064))
    return iv


def static_beats(fmt, act, port):
    groups = set()
    for a, b in static_intervals(fmt, act):
        groups.update(range(a // port, (b - 1) // port + 1))
    return len(groups)


def masked_smseq(S, mode):
    """smseq with every x load re-priced: addresses x beats + 1 (the measured law: one beat a cycle, + 1 cycle)."""
    sm = copy.deepcopy(S["smseq"])
    tab = {}
    for (P, fmt, K, R), v in sm.op.items():
        if v["load"] is None:
            continue
        old_beats = 2 if P == 1 else 10
        addrs = v["beats"] // old_beats
        assert addrs * old_beats + 1 == v["load"], ((P, fmt, K, R), v)
        act = 6 if P == 6 else 1
        if mode == "masked":
            nb = -(-act * USED[fmt] // 2048)
        elif mode in ("masked_static", "masked_static_wide4096"):
            nb = static_beats(fmt, act, 4096 if mode.endswith("4096") else 2048)
        elif mode == "wide4096":
            nb = -(-act * XC // 4096)
        elif mode == "masked_wide4096":
            nb = -(-act * USED[fmt] // 4096)
        else:
            raise ValueError(mode)
        v["load"] = addrs * nb + 1
        v["beats"] = addrs * nb
        tab[f"P{P} {fmt} K{K} R{R}"] = dict(addresses=addrs, beats_per_address=nb, as_built=old_beats, load=v["load"])
    return sm, tab


# ---------------------------------------------------------------------------------------------------------------------
def load_recs(d, suffix):
    out = {}
    for key, name in (("l20", "ar_l20"), ("wg", "wg"), ("l20_6", "p6_l20"), ("wg_6", "p6_wg")):
        p = d / f"{name}_{suffix}.json"
        if p.exists():
            out[key] = json.loads(p.read_text())
    return out


def joint_records(terminal_path, layouts_path, production_dir):
    """Join actual PQ+XMAP timings to unchanged retained sequence descriptors.

    No numeric inputs are regenerated. Layout source hashes must match all four
    retained fixture files; the changed packed activation image is intentional.
    """
    import copy
    terminal = json.loads(terminal_path.read_text())
    layouts = json.loads(layouts_path.read_text())
    retained_path = production_dir / 'retained_artifacts.json'
    retained = json.loads(retained_path.read_text())
    fixtures = {Path(f['dir']).name: {Path(p['path']).name: p['sha256']
                for p in f['files']} for f in retained['fixtures']}
    assert terminal['status'] == 'pass' and terminal['source_stable']
    assert terminal['one_compiled_executable'] and not terminal['generated_numeric_inputs']
    assert not terminal['full_token_measured'] and not terminal['SS_FF_admitted']
    records, cases = {}, {}
    for case, entry in terminal['results'].items():
        r = entry['result']
        assert entry['exit'] == 0 and r['returncode'] == 0
        if case == 'stress_negative_fp4':
            assert not r['exact'] and r['accepted'] and r['negative']
            continue
        assert r['exact'] and r['beat_counts_exact'] and not r['negative']
        assert not r['mismatching_rows'] and not r['unexpected_rows']
        p6 = case.startswith('p6_')
        fixture = case + '_haz1_g0'
        layout = layouts[f'a{6 if p6 else 1}/{fixture}/layout.json']
        assert all(layout['source_sha256'][name] == fixtures[fixture][name]
                   for name in ('seq.hex', 'lines.hex', 'x.hex', 'out.txt'))
        base = json.loads((production_dir/'pq'/f'{case}_f{6 if p6 else 1}.json').read_text())
        assert len(base['ops']) == len(r['ops']) == len(layout['ops'])
        joint_sources = {p.split('/source/')[-1]: h for p, h in r['source_sha256'].items()}
        # XMAP changes the parent/leaf and bench, but not arithmetic or PQ issue.
        shared = {p: h for p, h in base['source_sha256'].items()
                  if p in joint_sources and not p.endswith('/ot_hbm_accel_sm_pq.sv')}
        assert shared and all(joint_sources[p] == h for p, h in shared.items())
        adapted = copy.deepcopy(base)
        for b, j, l, dst in zip(base['ops'], r['ops'], layout['ops'], adapted['ops']):
            assert b['op'] == j['op'] == l['op'] and b['fmt'] == j['fmt'] == l['fmt']
            assert b['x_addresses'] == j['addresses'] == l['addresses']
            assert j['complete'] == j['timing']['results'] == b['rows']
            assert j['fault'] == j['timing']['fault'] == 0 and j['beats_exact']
            assert j['timing']['lines'] == b['lines'] and j['consumed'] == b['rtl']['consumed']
            dst['rtl'] = j['timing']
        adapted['total_cycles'] = r['total_cycles']
        records[case] = adapted
        cases[case] = dict(PQ_cycles=base['total_cycles'], joint_cycles=r['total_cycles'],
                           fewer_cycles=base['total_cycles']-r['total_cycles'],
                           ops=len(r['ops']), fixture_sha256=layout['source_sha256'])
    assert len(cases) == 8
    return records, dict(cases=cases, negative_expected_failure=True,
                        inputs={rel(p): sha(p) for p in (terminal_path, layouts_path, retained_path)})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rec", type=Path, default=REC)
    ap.add_argument("--out", type=Path, default=REC / "composition.json")
    ap.add_argument('--joint-record', type=Path)
    ap.add_argument('--joint-layouts', type=Path)
    ap.add_argument('--paired-record', type=Path)
    ap.add_argument('--combined-record', type=Path)
    a = ap.parse_args()
    S = setup()
    ar0, mm0, rows1, rows6 = gate_rows(S)
    gate = json.loads((MREC / "composition.json").read_text())["gate"]
    assert abs(ar0 - gate["AR_us"]) < 0.01 and abs(mm0["step_us"] - gate["MTP_step_us"]) < 0.01, (ar0, mm0["step_us"])
    out = dict(schema="opentallas.dshbm.hbm_opt.v1", basis=dict(record=rel(MREC / "composition.json"),
               gate_AR_us=ar0, gate_MTP_step_us=mm0["step_us"], tau=mm0["tau"], MTP_tok_s=mm0["mtp_tok_s"]))
    # (1) pipelined issue
    pqd = a.rec / "pq"
    rp, rs = load_recs(pqd, "f1"), load_recs(pqd, "f1s")
    r6p, r6s = load_recs(pqd, "f6"), load_recs(pqd, "f6s")
    i1 = {}
    if rp.get("l20") and rp.get("wg"):
        s1, per1 = item1(S, rows1, rp, 1)
        i1["AR"] = dict(saved_us=s1, AR_us=round(ar0 - s1, 3), gain_pct=round(100 * s1 / ar0, 2), groups=per1,
                        serial_protocol_check=serial_check(rows1, rs))
    if r6p.get("l20_6") and r6p.get("wg_6"):
        s6, per6 = item1(S, rows6, dict(l20=r6p["l20_6"], wg=r6p["wg_6"]), 6)
        step = mm0["step_us"] - s6
        i1["MTP"] = dict(saved_us=s6, step_us=round(step, 3), tok_s=round(mm0["tau"] * 1e6 / step, 1),
                         gain_pct=round(100 * s6 / mm0["step_us"], 2), groups=per6,
                         serial_protocol_check=serial_check(rows6, dict(l20=r6s.get("l20_6"), wg=r6s.get("wg_6")))
                         if r6s.get("l20_6") else None)
    out["item1_pipelined_issue"] = i1
    if a.joint_record:
        assert a.joint_layouts
        joint, scope = joint_records(a.joint_record, a.joint_layouts, a.rec)
        projection = {}
        for name, rows, keys, P, old in (
            ('AR', rows1, ('ar_l20', 'wg'), 1, ar0),
            ('MTP', rows6, ('p6_l20', 'p6_wg'), 6, mm0['step_us'])):
            saved, groups = item1(S, rows, dict(l20=joint[keys[0]], wg=joint[keys[1]]), P)
            projection[name] = dict(total_replacement_saved_us=saved,
                incremental_vs_measured_PQ_us=round(saved-i1[name]['saved_us'], 3),
                remaining_target_clock_us=round(old-saved, 3), groups=groups)
        out['joint_PQ_XMAP'] = dict(**scope, target_clock_projection=projection,
            accounting='REPLACE the same PQ groups once; do not add standalone item3 estimates or separate issue/layout savings',
            measured_scope='eight minimum-component P1/P6 sequences, not a full-token execution',
            bench_clock_ns=1, projection_clock_hz=F_SM,
            class_proxy='historical ATTN3 representative prefix retained; all-layer group substitution is modeled coverage',
            SS_FF_admitted=False, adopted=False, full_token_gain_measured=False,
            qualified_headline_rate=None, Qwen_provider_bound=False, Qwen_opt3_enabled=False)
    if a.paired_record:
        assert 'joint_PQ_XMAP' in out
        paired = json.loads(a.paired_record.read_text())
        fixture_path = a.paired_record.parent/'fixture.json'
        fixture = json.loads(fixture_path.read_text())
        controls_path = a.paired_record.parent/'changed_hook_cases.json'
        controls = json.loads(controls_path.read_text())
        assert paired['status'] == 'pass' and paired['runtime_returncode'] == 0
        assert not paired['mismatches'] and not paired['extra']
        assert paired['original_output_rows'] == paired['actual_output_rows'] == 86
        assert fixture['baseline_result_sha256'] == sha(pqd/'ar_l20_f1.json')
        assert len(fixture['composite_descriptors']) == 28
        assert fixture['logical_op_labels'][24:27] == [[24,25], [26,27], [28,29]]
        assert len(paired['ops']) == 28
        for op, desc in enumerate(fixture['composite_descriptors']):
            actual = paired['ops'][str(op)]
            assert actual['fault'] == 0 and actual['results'] == desc[0]
            assert actual['lines'] == actual['consumed'] == desc[4]
        first, last = fixture['w2_groups'][0], fixture['w2_groups'][-1]
        assert paired['ops'][str(last)]['t_done']-paired['ops'][str(first)]['t_load0'] == paired['paired_w2_cycles']
        assert paired['incremental_cycles_saved'] == paired['baseline_pq_w2_cycles']-paired['paired_w2_cycles']
        assert all(c['pass_check'] and c['runtime_returncode'] == 0 for c in controls.values())
        assert controls['ordinary_flag_off']['faults'] == [0]
        assert controls['illegal_pair_shape']['faults'] == [1]
        assert controls['ordinary_flag_off']['executable_sha256'] == controls['illegal_pair_shape']['executable_sha256']
        ar_joint = out['joint_PQ_XMAP']['target_clock_projection']['AR']
        w2 = ar_joint['groups']['W2']
        assert w2['layers'] == 40
        assert w2['pq_group_cycles'] == paired['baseline_pq_w2_cycles'] == fixture['baseline_w2_cycles']
        saved = (paired['baseline_pq_w2_cycles']-paired['paired_w2_cycles'])*w2['layers']/F_SM*1e6
        assert saved > 0
        old_ar = ar_joint['remaining_target_clock_us']
        new_ar = old_ar-saved
        gain = 100*(old_ar/new_ar-1)
        out['paired_W2_increment'] = dict(
            inputs={rel(p):sha(p) for p in (a.paired_record, fixture_path, controls_path,
                    a.paired_record.parent/'source_pin.json', a.paired_record.parent/'source.commit')},
            baseline='source-matched joint PQ+XMAP; W2 group unchanged from production PQ',
            measured_component_old_cycles=paired['baseline_pq_w2_cycles'],
            measured_component_new_cycles=paired['paired_w2_cycles'],
            measured_component_saved_cycles=paired['incremental_cycles_saved'],
            authoritative_exposed_W2_groups=w2['layers'],
            target_clock_hz=F_SM, target_period_ns=1e9/F_SM,
            incremental_AR_projection_us=saved, prior_joint_AR_projection_us=old_ar,
            candidate_AR_projection_us=new_ar, projected_per_user_rate_gain_pct=gain,
            model_one_percent_threshold_met=gain>=1,
            accounting='Replace W2 interval only, forty times; unchanged handshake/barrier once; no analytic partial-wave saving added',
            actual_combined_PQ_XMAP_PACK_measured=False, MTP_increment_us=None,
            full_token_gain_measured=False, physical_ss_ff_qualified=False,
            adopted=False, qualified_headline_rate=None,
            next_integration='Rawls combined configuration must bind actual PACK caller and measure interaction; Erdos component gate is not that combined run')
        if a.combined_record:
            combined = json.loads(a.combined_record.read_text())
            parent = a.combined_record.parent.parent
            summary_path, terminal_path = parent/'summary.json', parent/'terminal.json'
            summary = json.loads(summary_path.read_text())
            terminal = json.loads(terminal_path.read_text())
            assert summary['result_sha256'] == sha(a.combined_record)
            assert terminal['status'] == 'pass' and terminal['driver_exit'] == 0 and terminal['source_stable']
            assert summary['flags'] == dict(ENABLE=1, PQ_ENABLE=1, PACK_W2=1, XMAP=1)
            assert combined['status'] == 'pass' and combined['accepted'] and combined['beat_counts_exact']
            assert not combined['mismatches'] and not combined['extra']
            assert combined['original_output_rows'] == combined['actual_output_rows'] == 86
            assert len(combined['ops']) == len(combined['activation_loads']) == 28
            assert summary['original_inputs']['fixture.json'] == sha(fixture_path)
            baseline_joint = joint['ar_l20']
            assert summary['baseline_PQ_XMAP_total_cycles'] == baseline_joint['total_cycles']
            assert combined['total_cycles'] == summary['total_cycles']
            assert summary['actual_joined_cycle_saving'] == baseline_joint['total_cycles']-combined['total_cycles'] == paired['incremental_cycles_saved']
            assert combined['paired_w2_cycles'] == paired['paired_w2_cycles'] == summary['paired_W2_cycles']
            for op, (desc, load) in enumerate(zip(fixture['composite_descriptors'], combined['activation_loads'])):
                actual = combined['ops'][str(op)]
                assert actual['results'] == desc[0] and actual['fault'] == 0
                assert actual['lines'] == actual['consumed'] == desc[4]
                assert load['op'] == op and load['original_ids'] == fixture['logical_op_labels'][op]
                assert actual['xload_beats'] == load['actual_beats'] == load['expected_beats']
            assert combined['ops'][str(last)]['t_done']-combined['ops'][str(first)]['t_load0'] == paired['paired_w2_cycles']
            inc = out['paired_W2_increment']
            inc['actual_combined_PQ_XMAP_PACK_measured'] = True
            inc['combined_measurement'] = dict(
                inputs={rel(p):sha(p) for p in (a.combined_record, summary_path, terminal_path)},
                source_commit=summary['source_main_commit'], active_columns=summary['active_columns'],
                baseline_component_total_cycles=baseline_joint['total_cycles'],
                candidate_component_total_cycles=combined['total_cycles'],
                actual_component_saved_cycles=summary['actual_joined_cycle_saving'],
                original_row_ids_preserved=True, exact_rows=86, exact_activation_beats=True,
                scope='simultaneous three-lever L20 P1 minimum component; forty-layer exposure remains modeled, not actual full-token execution')
            inc['next_integration'] = 'P1 combined interaction is measured; P6 PACK exposure and contextual physical closure remain unmeasured. No same-case replay required.'
    # Production records may be composed without rerunning the numeric gates.
    # Keep their benchmark clock and measured scope separate from this target
    # clock program projection and the independent, unmeasured layout forecast.
    production_result = a.rec / 'result.json'
    if production_result.exists():
        r = json.loads(production_result.read_text())
        join_path = a.rec / 'DS1M_sequence_source_join.json'
        join = json.loads(join_path.read_text())
        assert sha(A.BASE/'program.json') == join['source_program_sha256']
        assert len(r['table']) == 12
        assert all(t['status'] == 'pass' and t['mismatching_ops'] == 0 for t in r['table'])
        assert r['negative']['mismatching_ops'] == 13
        out['production_measurement_scope'] = dict(
            result=rel(production_result), result_sha256=sha(production_result),
            source_join=rel(join_path), source_join_sha256=sha(join_path),
            authoritative_program=rel(A.BASE/'program.json'),
            authoritative_program_sha256=sha(A.BASE/'program.json'),
            numerical_gate=r['numerical_gate'], negative_gate=r['negative_gate'],
            source_commit=r['source_commit'], positive_sequences=12,
            negative_mismatching_ops=13, bench_clock_ns=r['bench_clock_ns'],
            projection_clock_hz=F_SM,
            original_supervisor_exit=r['supervisor_exit'],
            original_supervisor_error_class=r['supervisor_error_class'],
            hydration_failure_log=rel(a.rec/'compose.log'),
            hydration_failure_log_sha256=sha(a.rec/'compose.log'),
            hydration='tracked original program metadata restored with source-join SHA; no simulation or input regeneration',
            interpretation='measured production component cycles, substituted into the same source-program target-clock model; not integrated full-token measurements',
            dependency_coverage='L20 group/source join and retained class sequences; historical ATTN3 representative-prefix substitution retained explicitly',
            new_layout_or_wave_measurements_included=False,
            actual_combined_config_measured=False, SS60_FF25_qualified=False,
            candidate_adopted=False, qualified_headline_rate=None,
            Qwen_provider_bound=False, Qwen_opt3_enabled=False,
            Qwen_DS_layout_savings_transfer=False,
            provider_risks='native/fused VM service unresolved; finite-Q actual cost stays separate, not replaced by a wide-port assumption')
    # (3) activation delivery
    i3 = {}
    for mode in ("masked", "masked_static", "wide4096", "masked_wide4096", "masked_static_wide4096"):
        sm, tab = masked_smseq(S, mode)
        ar, mm, _, _ = gate_rows(S, sm)
        i3[mode] = dict(AR_us=ar, AR_saved_us=round(ar0 - ar, 3), MTP_step_us=mm["step_us"],
                        MTP_saved_us=round(mm0["step_us"] - mm["step_us"], 3), MTP_tok_s=mm["mtp_tok_s"], loads=tab)
    out["item3_activation_delivery"] = i3
    if production_result.exists():
        out['item3_interpretation'] = 'unchanged analytical beat-law sensitivity ONLY; no actual layout-ON measurement or cross-target credit'
    out["inputs"] = {rel(p): sha(p) for p in sorted(pqd.glob("*.json"))} if pqd.exists() else {}
    out["tool_sha256"] = {rel(Path(__file__)): sha(Path(__file__))}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("inputs",)}, indent=1)[:6000])


if __name__ == "__main__":
    main()
