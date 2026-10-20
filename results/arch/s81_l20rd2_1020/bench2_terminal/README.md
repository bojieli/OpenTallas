# L20RD2 original bench2 terminal evidence

Read-only collection 2026-10-20 08:12 PT. Original client2218953/unit1592497 terminal exit1 at07:47. **IDXRD_CAMPAIGN FAIL**: 15 finite cases, 2 named-positive failures. This packet does not qualify a source32 successor, native results, physical gate, or parent schedule. No Claude worktree/git/source edits or new fleet jobs.

Original Verilator5.050 build uses MUT=0, SRAM_MACRO=1. All21 original pre-build SHA entries match remote src2 at collection. Reader RTL SHA774bda8fc3ac135fc0ec9f8b9d7648b4e110e7a461d18f65c219fa707f2ab20f; testbench3ec23d4e384ff7f2483f03e464f2d393f9c5e5f7bdbec71f01e67b401efaa9eb. Only reader RTL differs from prior bench1(d8833814...). Source is an exact uncommitted snapshot, no fabricated commit binding.

- Sequential N87382/P3/T0400: PASS,87382keys/5463words,nerr0,qerr0,slice_err0; header-to-last16879/end-to-last16814. Sequential N43691,small4096,OPEN6 and gatherN256/P3 also PASS.
- Gather N2048/P4/T01500: PASS16384keys/1024words,nerr0.
- Gather N2048/P3/T01500: **FAIL921** errors seed1 and **FAIL1015** seed2. Prior bench1 same seed1 FAIL921 despite distinct reader RTL. First seed1 mismatch cycle4721/word104; later data may match while fault remains asserted. Reader status1000010001; qerr/slice_err0.
- Gather P3 T01000/700: FAIL921 each (informational sweeps, runner classifies x_* OK regardless result). Failure persists with larger T0 in tested1500; no throughput/root-cause proof inferred.
- Expected fail_late T060: FAIL257, confirms negative expectation only; not a source mutation witness. Informational sequential T0250/300/350 and P2 PASS.

Sequential N87382 P3 success has one key per item; gatherN2048 has16384keys and a different reader path. The long sequential success does not establish gather P3 coverage. Runner x_* cases count OK regardless TB result, so preserve actual PASS/FAIL receipts. Finite aggregate2 named-positive failures remains FAIL.

terminal.tar.gz includes original b1/b2 build logs and all case logs/res, excluding generated obj. source21.tar.gz contains source bytes selected by the original bench2 build manifest. Current-source verification includes binarySHA8f6dc9e856febe3edc6c7b81b77bc0db673f3bd57e20e980f45c3eb6c8987338. No native/depth or source32 proof transplanted.
