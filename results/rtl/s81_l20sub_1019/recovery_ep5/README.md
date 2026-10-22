# L20 reader recovered campaign, 2026-10-19

Source branch claude/s81-l20sub-1019 at 2a74f347f, RTL 04e86d694. Existing ep8 disk-full build objects and matching source were copied to ep5 and incrementally rebuilt by the existing S81-MUBUF3 job oth-ubuntu-1776074-1792474573. No simulation was relaunched by this evidence pickup. Recovery wrapper reports RECOVERY_ALL_EXPECTED_PASS and exit 0.

Base campaign passes six valid scenarios and rejects fail_late. L20 N=87382, P=3 measures hdr_to_last=16895 cycles (priced value), end_to_last=16830. Six mutants are rejected: lane hash, returned-rk slice, neighbouring scale lane, part-1 beat timing, swallowed response, and ignored open-lane specification. The campaign returns FAIL for each intentional mutant while the raw executable exits 0; admission uses the TB verdict, not executable exit status. Each witness contains the captured campaign verdict followed by its actual simulator output. Source digests and source verification retained alongside campaign logs.

This qualifies reader correctness/throughput. Physical gate, PNG review, utilization <=60%, clock spread <=80ps TT/FF and closure remain required. No route submission or physical approval is claimed.
