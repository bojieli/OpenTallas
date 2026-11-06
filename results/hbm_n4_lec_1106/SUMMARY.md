# N4 rsq LEC triage, 2026-11-06

The current full routed LEC completed EQUIVALENT: 13,427 compare points, 13,427 proved, zero differences and zero undecided, in 1,234.6 seconds. It uses the existing 64-edge reset contract without debug override. HBM owns physical signoff collection and qualified count updates.

The terminal earlier `lec_pre.log` reported 13,401 compare points, 13,325 proved and 76 differences. Its raw-prefix artifacts used four edges. The valid existing kit reset contract, installed after that run, permits 64 clocked reset edges and explicitly lists `ot_hnx_fused_hub_n4ext_rsq`.

On the exact original gold AIG, 97 removed packed-state relationships were proved universally after eight edges from arbitrary initial state and arbitrary fresh inputs at every edge:

- the high error bit of the eps and three Newton-step adders is zero;
- removed bypass-code bits of those Newton-step adders are zero or equal the surviving same-stage bit62.

No reset assumption, correspondence hypothesis, input restriction, X mask or arithmetic change enters these prefix proofs. The 97-output miter reduces to zero; the wrong-constant control is a difference. The Python builder had 35,787 ANDs before dead-cone reduction. This identifies the observed failure class as insufficient settling/state correspondence, rather than evidence of a numeric design change. The completed full-core proof independently confirms equivalence.

The original and live post-route gold AIGs are byte-identical:
`b5b97295f1af3f2e7ad12546c2cdcbf361843d0a164af8f6c18b260983e75c12`.

No RTL, constraint, clock, reset duration, sign-off gate or physical database was changed. The completed full post-route proof is retained and owned by HBM; no duplicate full proof was launched. Original failed evidence is unchanged.

Evidence:

- original kit: `epyc6:/srv/opentallas-scratch2/claude/codex-hbm-n4/eco/i1`;
- original failed artifacts: `lec_pre/`, terminal `lec_pre.log`;
- current full proof: `lec_postroute_k4fq3y2f/`;
- independent immutable analysis copy: `epyc6:/srv/opentallas-scratch2/claude/codex-n4-logic-1106`;
- exact executed script and formal results: adjacent `proof_prefix.py`, `prefix8_result.json`, `prefix8_abc.log`, `mutant_result.json`;
- proof run: ot-run epyc4 unit `oth-ubuntu-768520-1793956633`, 8GB/2threads, exit0, outputs copied back to epyc6.

The source-only analysis script expects its exact `lec.py` and `failed_pre/{gold,gate}.{aig,map}` basis in the execution directory. These immutable inputs remain at the analysis path; the script should run inside the project ORFS image for its ABC binary.
