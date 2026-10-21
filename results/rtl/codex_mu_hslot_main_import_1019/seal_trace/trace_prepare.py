from pathlib import Path
r=Path("src"); b=r/"rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_seq_host_mu.sv"
s=b.read_text();s=s.replace("    // the issuer of the real unit", """`ifdef PLAIN
    always @(posedge ck) if(`ISS.sc_v) $display("SEAL_TRACE cyc%0d in%0d ld%b row%h bad%0d ord%0d first%0d previssue%0d preveng%0d eq%0d",cyc,`ISS.sc_in,`ISS.sc_ld,`ISS.sc_row,`ISS.scan_bad,`ISS.ord_bad,`ISS.scan_first,`ISS.scan_pi,`ISS.scan_pe,`ISS.scan_eq);
    always @(posedge ck) if(`ISS.sc_fin) $display("SEAL_FINAL cyc%0d bad%0d ends%0d kits%0d native%0d maxdone%0d end%0d kit%0d",cyc,`ISS.scan_bad,`ISS.scan_ends,`ISS.scan_kits,`ISS.scan_native,`ISS.scan_max_done,`ISS.scan_end_cycle,`ISS.scan_kit_cycle);
`endif
    // the issuer of the real unit""")
(r/"rtl/dsrom_sys/s81_dv/unit/test/tb_trace.sv").write_text(s)
p=r/"rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_mu_bench.sh";s=p.read_text();s=s[:s.index("build mux; build plain")]+"build plain +define+PLAIN\nrun plain plain_ar ar_single\ncat \"$O/run_plain_ar.log\"\n";s=s.replace("$T/tb_dsdv_seq_host_mu.sv", "$T/tb_trace.sv").replace("+timeout=4000000","+timeout=4000")
(r/"rtl/dsrom_sys/s81_dv/unit/test/trace.sh").write_text(s)
