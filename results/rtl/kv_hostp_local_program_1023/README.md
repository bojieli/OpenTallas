# Selected KV host local program path

This evidence tests the alleged loss of PW/DW writes at the START-only HC station. It is a minimum mechanism simulation, not a full host, die, token, clock, or physical qualification.

The selected `e33504a6f` obsx source is byte-identical to main `59c4ffb8c` (SHA256 `2af36794ec613b8ceeabe20e4bd8d46093c064ae920ee50c3b27d23e75965841`). Its target-0 loader drives pr143; the actual qkd_host_ctl captures it and assigns raw_hc={pr_q,start,gen,token,pos}. The obsx output explicitly splices raw_hc[181:39] with transport_hc[38:0]. Only START enters the credit station. The original capture_localprogram source documents this division. Sending every local PW/DW through that station would spend broadcast credits without corresponding returns.

The bench uses the actual target-aware SRAM loader, real macro model, qkd_host_ctl, ot_qfd_pkgctl and qkd_host_hc_station, with the exact two obsx wiring expressions. It installs and externally authorizes all 1024 program words and eight descriptor words, checks every word/address at the HC output, the 1032-edge contiguous replay, the actual footer, stale-epoch rejection, and absence of broadcast credit consumption. It is derived from the existing production loader bench. `check_source.py` guards exact source hashes and obsx wiring. Mutant 1 removes the local upper-HC bypass; mutant 2 feeds all local traffic into the START-only station.

Other reviewed ties are not established defects: observed host MODE is 0; pr_re/tok_valid/users_done/arr_fault belong to its MODE1 array interface. st_h_bvalid.in_d=0 is a dummy valid-only channel payload whose out_d is unused. The selected queue sets RMW_EN=0 and documents that reads are absent and RMW descriptors fault; its i_rv/i_rd ties follow that contract. These observations do not clear unrelated native fanout, unregistered-pin, geometry, or full host integration failures.

Run `bash results/rtl/kv_hostp_local_program_1023/run.sh` from a source-matching repository root on the fleet with Verilator5.050.

Actual run: gold2 unit `oth-ubuntu-3245827-1792753212`, Verilator5.050, terminal exit0. Baseline PASS; both causal mutants caught. Raw m0/m1/m2 logs and fleet transport receipt are retained. The initial stdin-fed launcher unit4094515 exited without executing a bench; it is not used as evidence.
