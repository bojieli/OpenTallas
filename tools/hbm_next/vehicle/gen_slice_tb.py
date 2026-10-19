#!/usr/bin/env python3
"""LAYERBENCH-HBM (10-18): slice testbench + replay-model generator for a cut d4g slice (cut_slice.py output).

  gen_slice_tb.py --boundary DIR/boundary.json --out DIR [--replay replay.json ...]
writes DIR/tb_slice.sv (module tb_hbm_slice) and, per --replay, DIR/replay/<name>/{hdr,val,msk}.mem + index.json.

REPLAY MODEL (the slice's neighbours, at their SCHEDULED cycles).  replay.json (opentallas.hbm_slice_replay.v1):
  {"events": [{"k": "D"|"C", "dom": "stream"|"serial"|"hbm", "cyc": int, "port": <boundary port>, "val": hex,
               "mask": hex (C only, default all ones), "rec": int (priced record i, optional), "src": str}]}
  cyc counts that domain's clock edges after its reset (dut.hb_ckgen__por_<dom>) releases (edge 0 = first edge with
  reset high).  D at cyc c: the input takes the value right after edge c (NBA), so the slice samples it at edge c+1 and
  holds it until the next D on that port (inputs start at 0 = a quiet neighbour).  C at cyc c: the output value the
  slice presents AT edge c (what a neighbour flop samples at edge c) must equal val under mask.  A C event with a rec
  is that record's static-schedule commit assertion: a mismatch at the scheduled cycle FAILS the record (no slack:
  fixed-delay schedule, no handshakes).
TB prints SLICE_CHECK_FAIL / SLICE_REC lines, SLICE_OUT first/last change cycle per output (measured activity span),
and SLICE_PASS (all checks met, drives applied) or SLICE_FAIL.  Plusargs: +REPLAY=<dir> (mem files), +CYCLES=<n>
stream edges after reset (default: last event + 64, or 2000 with no replay), +HBM_IMG_DIR=<dir> (DRAM model preload).
VM image / VM checks (backdoor, the producer records' state): M events {"k":"M","mem":"vm","bank","row","sector","val"}
(cyc 0 only: preloaded before reset release) write the bank's SRAM macro cells with the bank's own SECDED (39,32) check
bits (ot_vms_bank_q0_faces_body.sv: sector s -> bank s[2:0], quarter s[14:13], mirror s[15] -> macro C else A, row
s[12:3]; check bits in macro B); C events on port "vm:<sector hex>" compare that word's data cells.  Needs the VM bank
master built flat (run_slice_vehicle.sh NOHIER=hfd_vms_bank_native_q0_faces): a hier_block hides its internals.
Event header word (64 b): [63:62] kind 1=D 2=C 3=end, [61:60] dom 0 stream 1 serial 2 hbm, [59:44] port index
(inputs / outputs index spaces; C with bit 59 set = VM check {1, mirror, bank 3, row 10} at [59:44]), [43:32] rec+1 (0 = none), [31:0] cyc.
"""
import argparse, json, sys
from pathlib import Path

DOM = {"stream": 0, "serial": 1, "hbm": 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boundary", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--replay", action="append", default=[])
    ap.add_argument("--nev", type=int, default=0, help="event array depth (default: max replay events + 1, >= 16)")
    a = ap.parse_args()
    b = json.loads(Path(a.boundary).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ins = [e for e in b["inputs"] if e["driver"].split(".")[0] != "<die_pin>"]
    pins = {e["name"] for e in b["inputs"] if e["driver"].split(".")[0] == "<die_pin>"}
    outs = b["outputs"]
    maxw = max([e["width"] for e in ins + outs] + [1])
    iidx = {e["name"]: k for k, e in enumerate(ins)}
    oidx = {e["name"]: k for k, e in enumerate(outs)}
    width = {e["name"]: e["width"] for e in ins + outs}

    nev_max = 16
    for rp in a.replay:
        r = json.loads(Path(rp).read_text())
        name = Path(rp).stem if Path(rp).name != "replay.json" else Path(rp).parent.name
        ev = r["events"]
        vm = [e for e in ev if e["k"] == "M"]
        ev = [e for e in ev if e["k"] != "M"]
        if a.nev and len(ev) + 1 > a.nev:
            sys.exit(f"gen_slice_tb: replay {name} needs {len(ev) + 1} event slots, --nev={a.nev}; split the replay")
        if any(e.get("cyc", 0) != 0 or e.get("mem") != "vm" for e in vm):
            sys.exit("gen_slice_tb: only cyc-0 VM preload (M) events are supported")
        bad = [e for e in ev if not (e["port"] in (iidx if e["k"] == "D" else oidx) or
                                     (e["k"] == "C" and e["port"].startswith("vm:")))]
        if bad:
            sys.exit(f"gen_slice_tb: {len(bad)} events on ports not on the slice boundary, e.g. {bad[:3]}")
        ev = sorted(ev, key=lambda e: (DOM[e["dom"]], e["cyc"], e["k"]))
        d = out / "replay" / name
        d.mkdir(parents=True, exist_ok=True)
        hl, vl, ml = [], [], []
        for e in ev:
            k = 1 if e["k"] == "D" else 2
            if e["port"].startswith("vm:"):
                s = int(e["port"][3:], 16)
                pi = 0x8000 | ((s >> 15) & 1) << 14 | (s & 7) << 10 | ((s >> 3) & 0x3FF)
                width[e["port"]] = 256
            else:
                pi = iidx[e["port"]] if k == 1 else oidx[e["port"]]
            rec = (e.get("rec", -1) + 1) & 0xFFF
            hl.append(f"{(k << 62) | (DOM[e['dom']] << 60) | (pi << 44) | (rec << 32) | (e['cyc'] & 0xFFFFFFFF):016x}")
            w = width[e["port"]]
            v = int(e["val"], 16)
            if v >> w:
                sys.exit(f"gen_slice_tb: value wider than port {e['port']} ({w} b)")
            m = int(e.get("mask", "f" * ((w + 3) // 4)), 16) & ((1 << w) - 1)
            vl.append(f"{v:0{(maxw + 3) // 4}x}")
            ml.append(f"{m:0{(maxw + 3) // 4}x}")
        hl.append(f"{3 << 62:016x}")
        vl.append("0"); ml.append("0")
        (d / "hdr.mem").write_text("\n".join(hl) + "\n")
        (d / "val.mem").write_text("\n".join(vl) + "\n")
        (d / "msk.mem").write_text("\n".join(ml) + "\n")
        vlines = []
        for e in vm:
            s = int(e["sector"]) if not isinstance(e["sector"], str) else int(e["sector"], 16)
            assert (s & 7) == e["bank"] and ((s >> 3) & 0x3FF) == e["row"], e
            vlines.append(f"{(s >> 15) & 1:x} {s & 7:x} {(s >> 3) & 0x3FF:03x} {int(e['val'], 16):064x}")
        (d / "vm_pre.txt").write_text("\n".join(vlines) + ("\n" if vlines else ""))
        last = max([e["cyc"] for e in ev if e["dom"] == "stream"] + [0])
        (d / "index.json").write_text(json.dumps({"events": len(ev), "drives": sum(e["k"] == "D" for e in ev),
                                                  "checks": sum(e["k"] == "C" for e in ev), "vm_preload_words": len(vm), "last_stream_cyc": last,
                                                  "scope": r.get("scope", "unspecified"),
                                                  "qualifies_native_layer": False, "qualifies_native_chain": False,
                                                  "state_seed_provenance": r.get("state_seed_provenance", ["unspecified"]),
                                                  "records": sorted({e["rec"] for e in ev if "rec" in e})}, indent=1))
        nev_max = max(nev_max, len(ev) + 1)
    nev = a.nev or nev_max

    L = ["`timescale 1ns/1ps",
         f"// generated by tools/hbm_next/vehicle/gen_slice_tb.py for slice {b['slice_top']} ({b['instance_count']} die",
         f"// instances, verbatim from {Path(b['die_v']).name}); replay model semantics: see the generator docstring.",
         "module tb_hbm_slice;",
         f"    localparam integer MAXW = {maxw}, NEV = {nev};",
         "    reg refclk = 1'b0, por_n = 1'b0;",
         "    always #5 refclk = ~refclk;"]
    for e in ins:
        L.append(f"    reg [{e['width'] - 1}:0] {e['name']} = '0;")
    for e in outs:
        L.append(f"    wire [{e['width'] - 1}:0] {e['name']};")
    conns = []
    for e in b["inputs"]:
        n = e["name"]
        conns.append(f".{n}({'refclk' if n.endswith('refclk') else 'por_n' if n.endswith('por_n') else n})")
    conns += [f".{e['name']}({e['name']})" for e in outs]
    L.append(f"    {b['slice_top']} dut (\n        " + ",\n        ".join(conns) + ");")
    L += ["    wire ck0 = dut.hb_ckgen__pll_stream[0], ck1 = dut.hb_ckgen__pll_serial[0], ck2 = dut.hb_ckgen__pll_hbm[0];",
          "    wire rs0 = dut.hb_ckgen__por_stream[0], rs1 = dut.hb_ckgen__por_serial[0], rs2 = dut.hb_ckgen__por_hbm[0];",
          "    reg [63:0] hdr [0:NEV-1];",
          "    reg [MAXW-1:0] val [0:NEV-1];",
          "    reg [MAXW-1:0] msk [0:NEV-1];",
          "    integer cnt [0:2];",
          "    integer ptr [0:2];",
          "    integer drives = 0, checks = 0, fails = 0, rec_ok = 0, rec_fail = 0, cycles = -1, last_ev = 0;",
          "    integer expected_drives = 0, expected_checks = 0;",
          "    string rdir;",
          "    initial begin : LOAD",
          "        integer i;",
          "        for (i = 0; i < NEV; i = i + 1) hdr[i] = {2'd3, 62'd0};",
          "        cnt[0] = -1; cnt[1] = -1; cnt[2] = -1; ptr[0] = NEV; ptr[1] = NEV; ptr[2] = NEV;",
          "        if ($value$plusargs(\"REPLAY=%s\", rdir)) begin",
          "            $readmemh({rdir, \"/hdr.mem\"}, hdr); $readmemh({rdir, \"/val.mem\"}, val); $readmemh({rdir, \"/msk.mem\"}, msk);",
          "        end",
          "        for (i = NEV - 1; i >= 0; i = i - 1) if (hdr[i][63:62] == 2'd1 || hdr[i][63:62] == 2'd2) begin",
          "            if (hdr[i][63:62] == 2'd1) expected_drives = expected_drives + 1;",
          "            else expected_checks = expected_checks + 1;",
          "            ptr[hdr[i][61:60]] = i;",
          "            if (hdr[i][61:60] == 2'd0 && hdr[i][31:0] > last_ev) last_ev = hdr[i][31:0];",
          "        end",
          "        if (!$value$plusargs(\"CYCLES=%d\", cycles)) cycles = (rdir.len() > 0) ? last_ev + 64 : 2000;",
          "        $display(\"SLICE_START slice=%s replay=%s cycles=%0d\", \"" + b["slice_top"] + "\", rdir, cycles);",
          "        #100 por_n = 1'b1;",
          "    end",
          "    task automatic drive(input integer pi, input [MAXW-1:0] v);",
          "        case (pi)"]
    for k, e in enumerate(ins):
        L.append(f"            {k}: {e['name']} <= v[{e['width'] - 1}:0];")
    L += ["            default: $fatal(1, \"SLICE_FAIL bad input index %0d\", pi);",
          "        endcase",
          "    endtask",
          "    function automatic [MAXW-1:0] sample(input integer pi);",
          "        sample = '0;",
          "        case (pi)"]
    for k, e in enumerate(outs):
        L.append(f"            {k}: sample[{e['width'] - 1}:0] = {e['name']};")
    L += ["            default: ;",
          "        endcase",
          "    endfunction"]
    import re as _re
    banks = sorted((int(n[-1]), n) for n in b["instances"] if _re.match(r"^vmb_[A-Z]{2}\d$", n))
    L += ["    // VM bank backdoor (cells of the bank's real SRAM macro models; layout of ot_sram_1r1w_1024x256_m2_r2c2: MUX 2)",
          "    function automatic [6:0] vchk(input [31:0] d);",
          "        integer i, j, a0, b0, c0, n; reg [6:0] c, col; reg [31:0] rm;",
          "        begin",
          "            c = 0;",
          "            for (j = 0; j < 7; j = j + 1) begin",
          "                rm = 0; n = 0;",
          "                for (a0 = 0; a0 < 7; a0 = a0 + 1) for (b0 = a0 + 1; b0 < 7; b0 = b0 + 1) for (c0 = b0 + 1; c0 < 7; c0 = c0 + 1) begin",
          "                    if (n < 32) begin col = (7'd1 << a0) | (7'd1 << b0) | (7'd1 << c0); rm[n] = col[j]; end",
          "                    n = n + 1;",
          "                end",
          "                c[j] = ^(d & rm);",
          "            end",
          "            vchk = c;",
          "        end",
          "    endfunction",
          "    task automatic vm_cell(input integer bk, input integer mac, input integer a, input integer bit_i, input reg v);",
          "        case (bk)"]
    for bi, n in banks:
        L.append(f"            {bi}: case (mac) 0: dut.{n}.u_ot_pr_core.bank.u_a.arr[a/2][bit_i*2 + a%2] = v; "
                 f"1: dut.{n}.u_ot_pr_core.bank.u_b.arr[a/2][bit_i*2 + a%2] = v; "
                 f"default: dut.{n}.u_ot_pr_core.bank.u_c.arr[a/2][bit_i*2 + a%2] = v; endcase")
    L += ["            default: $fatal(1, \"SLICE_FAIL no VM bank %0d in the slice\", bk);",
          "        endcase",
          "    endtask",
          "    function automatic reg vm_get(input integer bk, input integer mac, input integer a, input integer bit_i);",
          "        vm_get = 1'b0;",
          "        case (bk)"]
    for bi, n in banks:
        L.append(f"            {bi}: vm_get = (mac == 0) ? dut.{n}.u_ot_pr_core.bank.u_a.arr[a/2][bit_i*2 + a%2] : "
                 f"dut.{n}.u_ot_pr_core.bank.u_c.arr[a/2][bit_i*2 + a%2];")
    L += ["            default: ;",
          "        endcase",
          "    endfunction",
          "    function automatic [MAXW-1:0] vm_rd(input integer mir, input integer bk, input integer row);",
          "        vm_rd = '0;",
          "        for (integer i = 0; i < 256; i = i + 1) vm_rd[i] = vm_get(bk, mir ? 2 : 0, row, i);",
          "    endfunction",
          "    integer vm_words = 0;",
          "    initial begin : VMPRE",
          "        integer fd, mir, bk, row; reg [255:0] dv; reg [6:0] ck;",
          "        #1;",
          "        if (rdir.len() > 0) begin",
          "            fd = $fopen({rdir, \"/vm_pre.txt\"}, \"r\");",
          "            if (fd != 0) begin",
          "                while ($fscanf(fd, \"%h %h %h %h\\n\", mir, bk, row, dv) == 4) begin",
          "                    for (integer i = 0; i < 256; i = i + 1) vm_cell(bk, mir ? 2 : 0, row, i, dv[i]);",
          "                    for (integer k = 0; k < 8; k = k + 1) begin",
          "                        ck = vchk(dv[k*32 +: 32]);",
          "                        for (integer j = 0; j < 7; j = j + 1) vm_cell(bk, 1, row, (mir ? 56 : 0) + k*7 + j, ck[j]);",
          "                    end",
          "                    vm_words = vm_words + 1;",
          "                end",
          "                $fclose(fd);",
          "            end",
          "            $display(\"SLICE_VM_PRELOAD words=%0d\", vm_words);",
          "        end",
          "    end",
          "    task automatic step(input integer d);",
          "        reg [MAXW-1:0] got;",
          "        integer p, rec;",
          "        cnt[d] = cnt[d] + 1;",
          "        while (ptr[d] < NEV && hdr[ptr[d]][63:62] != 2'd3 && hdr[ptr[d]][61:60] == d[1:0] && hdr[ptr[d]][31:0] <= cnt[d]) begin",
          "            p = ptr[d]; rec = hdr[p][43:32] - 1;",
          "            if (hdr[p][31:0] < cnt[d]) begin",
          "                $display(\"SLICE_CHECK_FAIL late event %0d dom %0d cyc %0d at %0d\", p, d, hdr[p][31:0], cnt[d]); fails = fails + 1;",
          "            end else if (hdr[p][63:62] == 2'd1) begin",
          "                drive(hdr[p][59:44], val[p]); drives = drives + 1;",
          "            end else begin",
          "                got = hdr[p][59] ? vm_rd(hdr[p][58], hdr[p][56:54], hdr[p][53:44]) : sample(hdr[p][59:44]); checks = checks + 1;",
          "                if (((got ^ val[p]) & msk[p]) != '0) begin",
          "                    fails = fails + 1;",
          "                    $display(\"SLICE_CHECK_FAIL out=%0d dom=%0d cyc=%0d rec=%0d\", hdr[p][59:44], d, cnt[d], rec);",
          "                    if (rec >= 0) begin rec_fail = rec_fail + 1; $display(\"SLICE_REC rec=%0d cyc=%0d FAIL\", rec, cnt[d]); end",
          "                end else if (rec >= 0) begin rec_ok = rec_ok + 1; $display(\"SLICE_REC rec=%0d cyc=%0d COMMIT_OK\", rec, cnt[d]); end",
          "            end",
          "            ptr[d] = ptr[d] + 1;",
          "        end",
          "    endtask",
          "    always @(posedge ck1) if (rs1) step(1);",
          "    always @(posedge ck2) if (rs2) step(2);"]
    # output activity (stream edges)
    for k, e in enumerate(outs):
        L.append(f"    reg [{e['width'] - 1}:0] po{k} = '0; integer f{k} = -1, l{k} = -1, n{k} = 0;")
    L += ["    always @(posedge ck0) if (rs0) begin",
          "        step(0);"]
    for k, e in enumerate(outs):
        L.append(f"        if ({e['name']} != po{k}) begin if (f{k} < 0) f{k} = cnt[0]; l{k} = cnt[0]; n{k} = n{k} + 1; po{k} = {e['name']}; end")
    L += ["        if (cnt[0] >= cycles) begin"]
    for k, e in enumerate(outs):
        L.append(f"            if (n{k} > 0) $display(\"SLICE_OUT {e['name']} first=%0d last=%0d changes=%0d\", f{k}, l{k}, n{k});")
    L += ["            if (drives != expected_drives || checks != expected_checks) begin",
          "                $display(\"SLICE_CHECK_FAIL incomplete replay drives=%0d/%0d checks=%0d/%0d\", drives, expected_drives, checks, expected_checks);",
          "                fails = fails + 1;",
          "            end",
          "            $display(\"SLICE_SUMMARY drives=%0d checks=%0d fails=%0d rec_commit_ok=%0d rec_fail=%0d stream_edges=%0d serial_edges=%0d hbm_edges=%0d\",",
          "                     drives, checks, fails, rec_ok, rec_fail, cnt[0], cnt[1], cnt[2]);",
          "            if (fails == 0) $display(\"SLICE_PASS\"); else $display(\"SLICE_FAIL\");",
          "            $finish;",
          "        end",
          "    end",
          "    initial begin #200000000; $display(\"SLICE_FAIL timeout (no stream reset release?)\"); $fatal(1, \"timeout\"); end",
          "endmodule", ""]
    (out / "tb_slice.sv").write_text("\n".join(L))
    print(f"TB {out / 'tb_slice.sv'}: {len(ins)} replay inputs, {len(outs)} checked outputs, MAXW {maxw}, NEV {nev}, "
          f"{len(a.replay)} replay set(s); die pins {sorted(pins)}")


if __name__ == "__main__":
    main()
