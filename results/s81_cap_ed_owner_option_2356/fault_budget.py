#!/usr/bin/env python3
"""Price the CAP_ED owner option (A) +1 fault-only visibility edge against the S81 capture-root phase-end fault check.

Contract (results/rtl/s81_slice_1017/SLICE_CONTRACT.md 4, ot_s81sl_cap_rt.sv): the capture-root fault is STICKY and
checked at PHASE END (F11 = next cfg_v), never timed.  Budget: an E-tree fault raised with an E word must be visible at
the capc5r `fault` pin no later than that word's own capture write leaves capc5r (the phase cannot end before its last
write), i.e. slack = data_edges(word -> cw pin) - fault_edges(fault -> fault pin) >= 0.

MEASURED here (iverilog, gold = main RTL, dut = -DOT_S81_CAP_ED_FACE_DELAYED_FAULT): cap_ed i_v -> o_v and
i_f -> o_f edge counts for D = 23 / 24 (directed pulse after priming).
READ from RTL (regex, fail closed): capc5r landing depths for e_v/e_f/f_o/sv_o and pad stages; cap_rt fault chain
lf_p -> fault_q -> fault_p (3 flops).  CITED: cap_rt data word E-port -> leaf write >= 43 edges (SLICE_CONTRACT 4,
cap_bench last-arrival -> leaf-write 43..94; lower bound used).
    python3 fault_budget.py [--repo .] [--gold-rev 3fc2fcf0d14] [--out DIR]
"""
import argparse, json, re, subprocess
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument('--repo', default='.'); ap.add_argument('--gold-rev', default='3fc2fcf0d14'); ap.add_argument('--out', default='fault_budget')
a = ap.parse_args()
w = Path(a.repo).resolve(); o = Path(a.out).resolve(); o.mkdir(parents=True, exist_ok=True)
ed = w / 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv'
gold = subprocess.check_output(['git', '-C', str(w), 'show', f'{a.gold_rev}:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv'],
                               text=True).replace('module ot_s81sl_cap_ed', 'module old_ot_s81sl_cap_ed')
(o / 'gold.sv').write_text(gold)
tb = '''`timescale 1ps/1ps
module lat #(parameter D=24, parameter G=0)();
reg clk=0,rst=0,iv=0,fi=0;wire ov,of;wire [31:0] ot,od;wire oe;integer e=0,t_in=-1,t_v=-1,t_f=-1;
generate if(G) old_ot_s81sl_cap_ed #(D) u(.clk(clk),.rst_n(rst),.i_v(iv),.i_t(32'h0),.i_d(32'h0),.i_e(1'b0),.i_f(fi),.o_v(ov),.o_t(ot),.o_d(od),.o_e(oe),.o_f(of));
else ot_s81sl_cap_ed #(D) u(.clk(clk),.rst_n(rst),.i_v(iv),.i_t(32'h0),.i_d(32'h0),.i_e(1'b0),.i_f(fi),.o_v(ov),.o_t(ot),.o_d(od),.o_e(oe),.o_f(of));
endgenerate
initial forever begin #416 clk=1;#417 clk=0;end
always @(posedge clk) begin e<=e+1; if(ov===1'b1&&t_v<0&&t_in>=0) t_v<=e-t_in; if(of===1'b1&&t_f<0&&t_in>=0) t_f<=e-t_in; end
initial begin repeat(4)@(negedge clk); rst=1; repeat(3*D+20)@(negedge clk);
 iv=1;fi=1;t_in=e; @(negedge clk); iv=0;fi=0; repeat(D+10)@(negedge clk);
 $display("LAT G=%0d D=%0d data_edges=%0d fault_edges=%0d",G,D,t_v,t_f); end
endmodule
module tb; lat#(23,1)a(); lat#(23,0)b(); lat#(24,1)c(); lat#(24,0)d(); initial #400000 $finish; endmodule
'''
(o / 'tb_lat.sv').write_text(tb)
files = [w / 'rtl/lib/ot_rst_relay.sv', w / 'rtl/hdc/ot_hdc_delay_rf.sv', ed, o / 'gold.sv', o / 'tb_lat.sv']
subprocess.run(['iverilog', '-g2012', '-DOT_S81_CAP_ED_FACE_DELAYED_FAULT', '-s', 'tb', '-o', str(o / 'sim')] + [str(f) for f in files], check=True)
log = subprocess.check_output(['vvp', '-n', str(o / 'sim')], text=True); (o / 'lat.log').write_text(log)
lat = {}
for g, d, dv, fv in re.findall(r'LAT G=(\d) D=(\d+) data_edges=(-?\d+) fault_edges=(-?\d+)', log):
    lat[('gold' if g == '1' else 'option', int(d))] = dict(data=int(dv), fault=int(fv))
assert len(lat) == 4, log
# ---- downstream structure, read from RTL (fail closed)
c5 = (w / 'rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r.sv').read_text()
def land(sig):
    m = re.search(r'LANDING (\d+): ' + sig + r' .*\n(?:.*\n)*?.*ot_pl_land_n32_chunk_w #\(.*?\.D\((\d+)\)', c5)
    assert m, sig; return int(m.group(2))
ld_ev, ld_ef, ld_fo, ld_sv = land('e_v'), land('e_f'), land('f_o'), land('sv_o')
pad_f = int(re.search(r'ot_pl_pad #\(\.W\(1\), \.N\((\d+)\)\) u_osf', c5).group(1))
pad_v = int(re.search(r'ot_pl_pad #\(\.W\(6\), \.N\((\d+)\)\) u_osv', c5).group(1))
ed_d = int(re.search(r'#\(\.D\((\d+)\)\)\s*`endif\s*u_ed', c5).group(1))
rt = (w / 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv').read_text()
for pat in (r'lf_p <= \{e_f, w_f\}', r'always @\* lf_q = \|lf_p', r'lf_q \|\|', r'fault_p <= fault_q', r'assign fault = fault_p'):
    assert re.search(pat, rt), pat
rt_fault = 3          # lf_p, fault_q, fault_p (lf_q is combinational)
rt_data_min = 43      # SLICE_CONTRACT 4: last-arrival -> leaf-write 43..94 edges (cap_bench), lower bound
out = dict(schema='s81.cap_ed.fault_budget.v1', capc5r_ed_D=ed_d, measured_cap_ed=
           {f'{k[0]}_D{k[1]}': v for k, v in sorted(lat.items())},
           downstream=dict(landing_e_v=ld_ev, landing_e_f=ld_ef, landing_f_o=ld_fo, landing_sv_o=ld_sv, pad_fault=pad_f,
                           pad_cw=pad_v, cap_rt_fault_flops=rt_fault, cap_rt_data_to_leaf_write_min=rt_data_min))
rows = {}
for form in ('gold', 'option'):
    for d in (23, 24):
        L = lat[(form, d)]
        fault_total = L['fault'] + ld_ef + rt_fault + ld_fo + pad_f
        data_total = L['data'] + ld_ev + rt_data_min + ld_sv + pad_v
        rows[f'{form}_D{d}'] = dict(fault_edges_to_capc5r_pin=fault_total, data_edges_to_capc5r_cw_pin_min=data_total,
                                    slack_edges=data_total - fault_total, cap_ed_local_slack=L['data'] - L['fault'])
out['budget'] = rows
ok = (all(r['slack_edges'] >= 0 and r['cap_ed_local_slack'] >= 0 for r in rows.values())
      and all(lat[('option', d)]['fault'] == lat[('gold', d)]['fault'] + 1 for d in (23, 24))
      and all(lat[('option', d)]['data'] == lat[('gold', d)]['data'] == d for d in (23, 24)))
out['price'] = dict(fault_visibility_edges_added=1, data_edges_added=0)
out['verdict'] = 'PASS' if ok else 'FAIL'
(o / 'fault_budget.json').write_text(json.dumps(out, indent=1) + '\n')
r = rows[f'option_D{ed_d}']; g = rows[f'gold_D{ed_d}']
print(f"CAP_ED_FAULT_BUDGET {out['verdict']} capc5r D={ed_d}: cap_ed fault {lat[('gold',ed_d)]['fault']}->{lat[('option',ed_d)]['fault']} edges, "
      f"data {lat[('option',ed_d)]['data']} (unchanged); fault->capc5r pin {g['fault_edges_to_capc5r_pin']}->{r['fault_edges_to_capc5r_pin']} "
      f"vs word->cw pin >= {r['data_edges_to_capc5r_cw_pin_min']}; slack {g['slack_edges']}->{r['slack_edges']} edges (cap_ed local {g['cap_ed_local_slack']}->{r['cap_ed_local_slack']})")
raise SystemExit(0 if ok else 1)
