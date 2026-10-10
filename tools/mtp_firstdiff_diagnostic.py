#!/usr/bin/env python3
"""Instrument the preserved two-stage campaign; never change engine RTL or its golden.

This is diagnosis of the original reduced vehicle, not a full-target exactness gate.
"""
import argparse
import json
import inspect
import sys
from pathlib import Path


def instrument(root):
    obj = root / "wf2/obj_stage2_wfc_w1_deep"
    bench = obj / "tb_dsrom_wavefront_array_stage2.sv"
    source = bench.read_text()
    anchor = "            // -- accounting and the lm_head logit check"
    assert source.count(anchor) == 1
    diag = '''            integer diag_pc = -1, diag_job = -1;
            string diag_path;
            always @(negedge clk) if (rst_n && job_pos <= 1) begin
                if (core.st == 6 && core.waited && (&core.idles) &&
                    (diag_pc != core.pc || diag_job != jobs)) begin
                    diag_pc = core.pc; diag_job = jobs;
                    diag_path = $sformatf("DIAG_DIR/rtl_n%0d_j%0d_pc%0d.hex", n, jobs, core.pc);
                    $writememh(diag_path, vm);
                    $display("DIAG node=%0d job=%0d pos=%0d pc=%0d cycle=%0d", n, jobs, job_pos, core.pc, cyc);
                end
            end
'''.replace("DIAG_DIR", str(root / "snapshots"))
    source = source.replace(anchor, diag + anchor)
    source = source.replace('$display("OUT_MISMATCH flit=%0d", op);',
                            '$display("OUT_MISMATCH flit=%0d rtl=%h gold=%h", op, tx_d[SK*FLIT +: FLIT], exo[op][FLIT-1:0]);')
    (root / "snapshots").mkdir(exist_ok=True)
    bench.write_text(source)
    old_root = "/srv/opentallas-scratch/codex/mtp-exact-ring14-cefb5aa18"
    command = [part.replace(old_root, str(root)) for part in json.loads((obj / "build_cmd.json").read_text())]
    (root / "diagnostic_build_cmd.json").write_text(json.dumps(command, indent=2) + "\n")


def golden(root):
    sys.path.insert(0, str(root / "src/tools"))
    import dsrom_wavefront_rtl_campaign as W
    A, P, I, V, G, np = W.A, W.P, W.I, W.V, W.G, W.np
    model = V.Model()
    layout = P.Layout(model, rollback_ring=True)
    A.place_head_parts(layout)
    base = P.Machine(layout, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    body = [list(range(14)), [14], [15], list(range(16, model.L))]
    plan = A.Plan(layout, body, 0, False, "relay")
    programs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    pipe = A.Pipeline(plan, programs, base)
    prep = json.loads((root / "wf2/prepare_stage2_deep.json").read_text())
    inject = [int(s, 16) for s in (root / "wf2/cfg_stage2_deep/inject.hex").read_text().splitlines()]
    snapshots = root / "golden_snapshots"
    snapshots.mkdir(exist_ok=True)
    source, start = inspect.getsourcelines(P.Machine.run)
    before = start + next(i for i, s in enumerate(source) if s.strip() == "f = prog[n]")
    current = {}
    def trace(frame, event, arg):
        if event == "line" and frame.f_code == P.Machine.run.__code__ and frame.f_lineno == before:
            pc = frame.f_locals["n"]
            mc = frame.f_locals["self"]
            G.bits(mc.vm[:plan.pb + A.PS]).astype("<u4").tofile(
                snapshots / f"gold_n{current['node']}_j{current['job']}_pc{pc}.bin")
        return trace
    cursor = 0
    for job, (token, pos) in enumerate(prep["jobs"][:2]):
        for mc in pipe.pk:
            mc.tokens = mc.tokens[:pos]
        rxw, rxb = prep["rxw"], plan.role(1)["rxb"]
        payload = inject[cursor + 1:cursor + 1 + rxw]
        words = [(flit >> (32 * lane)) & 0xffffffff for flit in payload for lane in range(16)]
        pipe.pk[1].vm[rxb:rxb + len(words)] = G.from_bits(np.asarray(words, dtype=np.uint32))
        cursor += rxw + 1
        for node, k in enumerate((1, 2)):
            current.update(node=node, job=job)
            sys.settrace(trace)
            try:
                pipe.pk[k].run(programs[k], token, pos)
            finally:
                sys.settrace(None)
            if k == 1:
                pipe.hop(1, 2)
        print(f"golden job {job} done", flush=True)
    (root / "golden_diagnostic_manifest.json").write_text(json.dumps({
        "source_commit": "cefb5aa18", "scope": "original reduced two-stage campaign14 diagnosis",
        "jobs": prep["jobs"][:2], "vm_words": plan.pb + A.PS,
        "programs": programs,
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("instrument", "golden"))
    parser.add_argument("root", type=Path)
    args, _ = parser.parse_known_args()
    (instrument if args.action == "instrument" else golden)(args.root)
