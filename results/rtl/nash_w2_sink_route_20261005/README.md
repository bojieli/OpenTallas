The exact-gated W2 publication sink fails routed SS setup at the 1.2 GHz target.
The original default-off RTL is unchanged: `ot_hbm_integrated_w2_result_sink`
with ENABLE=1, the two handed f835c8641 sources (sink also published as
669ca6a80), and no tied parent ports. This is the handed component port-context
route, not a routed enclosing parent or a full-token qualification.

The selected constraints remained 833.333 ps, SS60/FF25, IO delay 20% on every
non-clock input (including POR) and output, load 3.898, maximum transition
320 ps and fanout 32, utilization 25%, density 0.5. No false paths or waivers
were added. The guarded launcher passed with zero macros. All runs used the
unchanged admission guard, 16 workers, explicit unlimited flow/synthesis
timeouts and NVMe scratch; no process memory/AS/file/time caps.

| Outcome | Actual result |
| --- | --- |
| r1 startup | Invalid absolute source spelling became `/src//srv/...`; synthesis never ran. |
| r2 startup | Correct source-root mount lacked required aligned-hook Tcl; synthesis never ran. |
| r3 full route | Completed, route_rc=0 and corner_rc=0, engineering NOT_MET. |
| Final SS setup | -1161.007568 ps, TNS -1855347.1 ps; register-to-register -1161.01 ps. |
| Final FF hold | +17.956039 ps; no negative hold D-pin slacks. |
| SS input-to-register | +441.26 ps. Reset/recovery was timed and is not the failing class. |
| SS output | -1133.213013 ps. |
| DRC / antenna / slew / cap / fanout | All zero. |
| Routed cells | 38,080 total, 1,800 sequential; 4265.61 um2 standard-cell area. |
| Core / die area | 13000.8 / 13971 um2. |
| Wire / vias | 203282 um / 362055. |

The retained ORFS Fmax field is not an admitted clock. No clock, rate, fit,
full-parent or token claim follows from this failed result. P&R peak RSS was
not measured; the 16 GiB guard reservation is not a measurement, and the
previous 175.746 MB simulation frontend is not a P&R estimate.

`r3_physical_FAIL/sink_ss_classes.log` enumerates every unique negative SS
endpoint returned by routed STA: 2146 total = all 1800 protected-register
endpoints plus 346 outputs. The corner helper's 2455 `*/D` pin tally is not
an FF endpoint census: combinational gates also have pins named D.
The exhaustive endpoint list and the full representative paths are retained;
the report includes fanout, capacitance, slew, pins, nets and propagated clocks.

| Endpoint class | Count | Worst SS slack (ps) | Actual start -> endpoint |
| --- | ---: | ---: | --- |
| Protected control word 24 | 72 | -1161.007568 | code[24][49]/QN -> code[24][71]/D |
| Protected metadata words 0..7 | 576 | -793.707520 | code[24][49]/QN -> code[4][14]/D |
| Protected payload words 8..23 | 1152 | -984.646057 | code[2][53]/QN -> code[21][27]/D |
| Request address | 32 | -1133.213013 | code[3][24]/QN -> req[332] |
| Request payload | 256 | -938.394714 | code[24][49]/QN -> req[199] |
| Request strobe | 32 | -822.205322 | code[24][49]/QN -> req[27] |
| Request direction | 1 | -822.409729 | code[24][49]/QN -> req[336] |
| Request tag | 16 | -662.150696 | code[7][10]/QN -> req[7] |
| source_permit | 1 | -975.986206 | code[20][37]/QN -> source_permit |
| fault | 1 | -970.058594 | code[20][37]/QN -> fault |
| rsp_r | 1 | -963.023315 | code[20][37]/QN -> rsp_r |
| req_v | 1 | -951.395386 | code[20][37]/QN -> req_v |
| done | 1 | -944.632385 | code[20][37]/QN -> done |
| retire_r | 1 | -919.871277 | code[20][37]/QN -> retire_r |
| reserve_r | 1 | -846.425354 | code[24][49]/QN -> reserve_r |
| quiet | 1 | -778.834656 | code[24][49]/QN -> quiet |
| retained | 1 | -712.403381 | code[24][49]/QN -> retained |

Literal source hooks sent to Rawls (sole sink/parent RTL writer):

- Sink lines 29..44: 25 protected codewords and combinational `decode64`;
  package lines 16..31: syndrome, overall parity, indexed correction and data.
- Sink lines 47..73: frame/ownership checks, global uncorrectable reduction,
  publication/acceptance guards, selected checked payload/base and request.
- Sink lines 76..98: state/bitmap/slot, response identity and complete readback
  comparison, with global fault feedback into the next protected state.
- Sink lines 100..117: `encode64` of control, reservation metadata and captured
  result payload, written back to the same protected-register bank.

The actual worst control path combines codeword decode, fault/decision logic
and protected re-encode in one edge. Its arrival is 2112.62 ps against a
951.62 ps required time. Request addresses additionally cross protected base
and slot selection before an exposed loaded port. Payload writes and metadata
writes are also coupled to checked state/identity/global-fault decoding; all
three protected-storage classes fail, not only the one worst control bit.
FF hold and DRV are clean in this measured candidate.

Necessary structural frontiers for Rawls to implement and gate, not a new
approved design or latency claim: checked/coherent row decode, decision and
readback comparison, protected encode/writeback, and held registered
request/publication outputs. Decoder stages themselves need real timing cuts;
registering only the final valid flag does not separate the measured chains.
A successor must preserve the four no-ready seats, source frame/version,
matched CAP1 debt, full payload verification and positive shared release.
Added cycles remain unmeasured until its changed-source bench and routed STA.
No arbitrary flow variant or relaxed constraint was launched.

The first supplementary representative-path collector exited 139 before
printing any class; its log and Tcl remain intact. The exhaustive-path
collector succeeded. The corrected collector uses stable register/port
objects and succeeded; `sink_ss_representatives_fixed.*` contains all 17
class representatives. Neither collection changed the ODB, SDC, SPEF, RTL,
original corner verdict or route.

Remote retained root: `/srv/opentallas-scratch2/jobs/nash-w2-sink-route-f835-r3`.
Sibling r1/r2 roots and the immutable two-source root are retained. The final
ODBs/netlist/SPEF and full ORFS closure remain remote; these committed records
carry their original hashes and the raw corner/exhaustive/class reports.
The earlier normal publication and corrupted-readback functional outcomes in
`results/rtl/nash_w2_publication_20261005/r1` remain valid and unchanged.
