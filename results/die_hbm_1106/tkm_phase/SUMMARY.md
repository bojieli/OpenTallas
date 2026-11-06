# Actual TKM metadata phase and decode arithmetic prerequisite

The existing accepted-start/configure phase can safely precompute `gb*pf mod256` at the actual `cfg_pipe[0]` event. No DEL latency has been added by this analysis. A separate proposed +1 DEL cohort implementation remains unproved until its actual source passes the full-root vehicle.

The source is the approved optional ctlrst root, `rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_tp192_root_core__ctlrst.sv`, SHA256 `2214efc605dac6ac80efbb29fe03a38486a272fde801af7e27ad1f48d27c62ff`. `build_phase.py` retains the exact flattened module logic and adds monitors; removing unrelated outputs allows Yosys to reduce the actual control/configuration dependency cone to 76 cells. No standalone replacement scheduler is used.

`phase5.log` proves the following by unbounded one-step induction, with arbitrary binary reset, start and configuration inputs at every edge:

- While busy, either the precomputed metadata is ready and saved gb/pf match the actual latched gb/pf, or the actual configuration product stage is active at tick0.
- Every actual capture sees ready metadata with identical latched gb/pf.

There are no assumptions restricting repeated starts, rejected starts while busy, configuration changes, DEL data or reset between start and capture. Each proof step is a rising core-clock edge; a paused clock causes no state transition. Accepted start captures gb/pf at S, the existing product stage consumes them at S+1, and the first possible capture is S+9 (tick8). The monitor deliberately stores gb/pf rather than adding a multiplier to the sequential invariant; the arithmetic identity is proved separately for every finite input value.

`phase2.log` also passes 12-step bounded checking with defined external inputs and unknown initial state. Earlier logs `phase.log`, `phase3.log`, `phase4.log` remain preserved at the execution path. The initial proof allowed X external bits, and four-state induction variants were inconclusive with an X in their final induction step. Those failures are not presented as a hardware counterexample or erased; the final induction uses the explicit binary hardware-bit model. `phase_mutant.log` finds a concrete counterexample when the precompute-ready event is suppressed.

`algebra.c` exhaustively checks 16,777,216 combinations for each of these exact 8-bit functions, with zero differences:

- `(flit_f8 - ((rank-gb)*pf)) mod256 = (flit_f8 + gbpf - rank*pf) mod256` (the common arbitrary flit addend cancels; every rank/gb/pf offset is enumerated).
- The proposed split-nibble lookup form `L[rank.lo] + (H[rank.hi]<<4)`, with `L[n]=(gb-n)*pf mod256` and `H[n]=-(n*pf) mod16`.
- The actual carry-save/prefix implementation in gaps' mapped `leaf.v`, for all flit/gbpf/rankpf byte triples.

Offset+1 and omitted carry-in mutants each fail all 16,777,216 cases. `csa_formal.log` independently proves the exact candidate_csa RTL equivalent to the plain candidate RTL for arbitrary rank/pf/flit/gbpf bytes.

This is a phase/arithmetic prerequisite, not routed signoff or proof of an unimplemented pipeline change. Gaps measured only 40.92ps improvement for CSA (418.50 to377.58ps), insufficient for the current ~230ps setup deficit. Root requested a paid +1 internal DEL cohort stage; source prototype ownership remains gaps'. It must preserve external DEL receipt validation timing, register the entire cohort, align slot load and issue by one edge, shift all post-ingress calendars together, reset capture validity, and account for +1 completion/stat cycles and the changed next-start boundary. Arbitrary malformed DEL on the extra trailing busy edge must be diagnosed against the actual protocol rather than masked.

Execution artifacts, including all failed attempts and original input, remain at `epyc2:/srv/opentallas-scratch2/claude/codex-tkm-phase-proof-1106`. Heavy commands ran through ot-run with 8GB/2 threads (algebra 2GB/1). Final induction took0.49s/69MB; bounded check3.81s/348MB; readiness mutant12.52s/244MB; CSA formal0.06s/27MB. Original source and physical kits were untouched.
