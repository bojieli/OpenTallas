#!/bin/bash
# S-VM-CAPT-TIMELINE (claude 2026-10-16): does the DECISION B capture data half (ctrl_c/dsfd_capt_x8_x43.sv: fixed
# 3:4 transfer, words 1..2 serial edges EARLIER than the old row_local hold queue + ratio FIFO) violate the VM static
# capture lanes' timeline?  Builds tools/s81_ph/capc_split_bench.sh's runner unchanged (gather -> capture golden bench,
# reference capture = OLD timing, split candidate = NEW timing, word-sequence compare), then puts the production VM
# capture face logic behind BOTH t_vm buses: dsfd_vm_static_cap_ctl (flush from the side's own status lane) + 16 x
# dsfd_vm_static_cap_leaf PIPE 2 (CAP_PIPE 2, E 8).  Reports per side the sticky lane faults [0] range [1] alignment
# [2] alias [3] duplicate [4] two rows due, rows/words written, words lost, minimum row-write spacing per lane,
# same-edge write-bank collisions across lanes (bank = row[4:0] ^ {row[7:5],00}); and old-vs-new per-lane row
# sequences ({row, mask, data}) with the serial-edge delta.  Stimuli: tools/s81_vm/capt_timeline_stim.py (aligned).
# usage (source root): capt_timeline_bench.sh <out> "<cases>"   verdict "CAPT_TIMELINE PASS|FAIL"
set -eu
out=$1; cases=$2
mkdir -p "$out"
for c in $cases; do python3 tools/s81_vm/capt_timeline_stim.py $c $out/stim_$c.txt; done
sed '$d' tools/s81_ph/capc_split_bench.sh > $out/gen_split.sh
bash $out/gen_split.sh "$out"
python3 - "$out/split_runner.sh" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1]); s = p.read_text()
def one(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
one('    final begin\n', r'''    // ---------------- S-VM-CAPT-TIMELINE: VM static capture face logic behind old (side 0 = ref) and new (side 1 = dut)
    wire [13375:0] vin [0:1];
    assign vin[0] = rv; assign vin[1] = t_vm;
    wire [15:0] v_ov [0:1]; wire [223:0] v_row [0:1]; wire [255:0] v_m [0:1]; wire [8191:0] v_d [0:1]; wire [79:0] v_lf [0:1];
    wire [1:0] v_fl, v_sf;
    genvar vs, vg;
    generate for (vs = 0; vs < 2; vs = vs + 1) begin : vside
        wire rn;
        dsfd_vm_static_cap_ctl u_ctl (.ck(ckv[0]), .rst_n(rse[0]), .st_live(vin[vs][13312]), .st_drn(vin[vs][13314]),
            .st_flt(vin[vs][13315]), .rn(rn), .flush(v_fl[vs]), .s_flt(v_sf[vs]));
        for (vg = 0; vg < 16; vg = vg + 1) begin : ln
            dsfd_vm_static_cap_leaf #(.E(8), .PIPE(2)) u_l (.ck(ckv[0]), .rn(rn), .gid(4'(vg)), .f_c(vin[vs][832*vg +: 832]),
                .flush(v_fl[vs]), .o_v(v_ov[vs][vg]), .o_row(v_row[vs][14*vg +: 14]), .o_m(v_m[vs][16*vg +: 16]),
                .o_d(v_d[vs][512*vg +: 512]), .flt(v_lf[vs][5*vg +: 5]));
        end
    end endgenerate
    typedef struct { int e; bit [13:0] r; bit [15:0] m; bit [511:0] d; } vrow_t;
    vrow_t vq [0:1][0:15][$];
    int vk = 0, v_win [0:1], v_bank [0:1], v_b2b [0:1], v_mingap [0:1], v_last [0:1][0:15], v_flush_e [0:1], v_ffe [0:1];
    longint v_wi [0:1], v_wo [0:1];
    initial for (int s2 = 0; s2 < 2; s2++) begin v_win[s2] = 0; v_bank[s2] = 0; v_b2b[s2] = 0; v_mingap[s2] = 1 << 30;
        v_flush_e[s2] = -1000; v_ffe[s2] = -1; v_wi[s2] = 0; v_wo[s2] = 0; for (int g2 = 0; g2 < 16; g2++) v_last[s2][g2] = -1000; end
    always @(posedge ckv[0]) if (rse[0]) begin : vmon
        for (int s2 = 0; s2 < 2; s2++) begin
            bit [31:0] seen; seen = 0;
            if (v_fl[s2]) v_flush_e[s2] = vk;
            if (v_ffe[s2] < 0 && |v_lf[s2]) v_ffe[s2] = vk;
            for (int k = 0; k < 128; k++) v_wi[s2] += longint'(vin[s2][104*k]) + longint'(vin[s2][104*k+52]);
            for (int g2 = 0; g2 < 16; g2++) if (v_ov[s2][g2]) begin
                vrow_t x; bit [13:0] r; bit [4:0] b;
                r = v_row[s2][14*g2 +: 14];
                x.e = vk; x.r = r; x.m = v_m[s2][16*g2 +: 16]; x.d = v_d[s2][512*g2 +: 512];
                vq[s2][g2].push_back(x); v_wo[s2] += $countones(x.m);
                if (vk - v_last[s2][g2] < v_mingap[s2]) v_mingap[s2] = vk - v_last[s2][g2];
                if (vk - v_last[s2][g2] == 1) v_b2b[s2]++;
                v_last[s2][g2] = vk;
                if (vk - v_flush_e[s2] >= 0 && vk - v_flush_e[s2] <= 12) v_win[s2]++;
                b = r[4:0] ^ {r[7:5], 2'b00};
                if (seen[b]) v_bank[s2]++; seen[b] = 1'b1;
            end
        end
        vk++;
    end
    final begin : vfin
        int fb [0:1][0:4]; int sq = 0, rows0 = 0, rows1 = 0, dmn = 1 << 30, dmx = -(1 << 30);
        for (int s2 = 0; s2 < 2; s2++) begin
            for (int b = 0; b < 5; b++) begin fb[s2][b] = 0; for (int g2 = 0; g2 < 16; g2++) fb[s2][b] += v_lf[s2][5*g2+b]; end
        end
        for (int g2 = 0; g2 < 16; g2++) begin
            rows0 += vq[0][g2].size(); rows1 += vq[1][g2].size();
            if (vq[0][g2].size() != vq[1][g2].size()) begin sq++; if (sq < 5) $display("VMCAP_CMP MISMATCH lane %0d rows old %0d new %0d", g2, vq[0][g2].size(), vq[1][g2].size()); end
            else for (int i = 0; i < vq[0][g2].size(); i++) begin
                if (vq[0][g2][i].r !== vq[1][g2][i].r || vq[0][g2][i].m !== vq[1][g2][i].m || vq[0][g2][i].d !== vq[1][g2][i].d) begin
                    sq++; if (sq < 5) $display("VMCAP_CMP MISMATCH lane %0d row# %0d old %h/%h new %h/%h", g2, i, vq[0][g2][i].r, vq[0][g2][i].m, vq[1][g2][i].r, vq[1][g2][i].m); break; end
                if (vq[1][g2][i].e - vq[0][g2][i].e < dmn) dmn = vq[1][g2][i].e - vq[0][g2][i].e;
                if (vq[1][g2][i].e - vq[0][g2][i].e > dmx) dmx = vq[1][g2][i].e - vq[0][g2][i].e;
            end
        end
        for (int s2 = 0; s2 < 2; s2++)
            $display("VMCAP side=%s lanes_with_fault range=%0d align=%0d alias=%0d dup=%0d two_rows_due=%0d status_flt=%0d first_fault_edge=%0d rows=%0d words_in=%0d words_written=%0d words_lost=%0d min_row_gap=%0d back_to_back=%0d rows_in_flush_window=%0d bank_collisions=%0d",
                s2 ? "new" : "old", fb[s2][0], fb[s2][1], fb[s2][2], fb[s2][3], fb[s2][4], v_sf[s2], v_ffe[s2], s2 ? rows1 : rows0,
                v_wi[s2], v_wo[s2], v_wi[s2] - v_wo[s2], v_mingap[s2], v_b2b[s2], v_win[s2], v_bank[s2]);
        $display("VMCAP_CMP row_seq_mismatches=%0d rows_old=%0d rows_new=%0d serial_edge_delta_new_minus_old=%0d..%0d %s", sq, rows0, rows1,
            (rows0 > 0) ? dmn : 0, (rows0 > 0) ? dmx : 0,
            (sq == 0 && (|v_lf[1]) == 1'b0 && v_wi[1] == v_wo[1] && rows1 > 0) ? "VMCAP_PASS" :
            ((|v_lf[1]) == (|v_lf[0]) && fb[1][4] <= fb[0][4] && fb[1][2] <= fb[0][2]) ? "VMCAP_SAME_AS_OLD" : "VMCAP_WORSE");
    end
    final begin
''')
one('rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_split_candidate.sv $G/capc_shim.sv',
    'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_split_candidate.sv $G/vmcap.sv $G/capc_shim.sv')
one('cp rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv $G/rly.sv',
    "cp rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv $G/rly.sv\n"
    "{ echo '`timescale 1ns/1ps'; sed -n '/^module dsfd_vm_static_cap_ctl/,/^endmodule/p' rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_cap.sv;\n"
    "  cat rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_cap_leaf.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_capl_pre.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_capl_pipe.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_capl.sv; } > $G/vmcap.sv")
one('''  echo "$TAG $c: $(grep -h SUMMARY $OUT/run_${TAG}_$c.log)''', '''  echo "$TAG $c: $(grep -h '^VMCAP' $OUT/run_${TAG}_$c.log | tr '\\n' ' ') $(grep -h SUMMARY $OUT/run_${TAG}_$c.log)''')
p.write_text(s)
PY
bash "$out/split_runner.sh" "$out" vmcap "$cases"
