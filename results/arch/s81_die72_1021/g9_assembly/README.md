# G9 source assembly preparation, 2026-10-21 takeover13:40

This is a source candidate and binding handover. No G9 GEN or physical chain has been launched. Current G8IQ remains immutable and diagnostic.

`g8_actual_scope.json` copies the actual case census: 159 stand-in instances across 21 masters. The priority eleven masters account for 101; the other 58 are services, CTRL, SerDes and slice parents. The case also records 259 crossings without a landing ring, 58 without a clock root and 25 hops over 405 um. Preserve these failures when using available views.

`source_assembly.json` pins the normal-slice change from 6893686b3. Its only source delta is three child-master names: xg→xgt and xr1/xr3→xrt1/xrt3. Exact substitution reproduces the whole file, and all four named source files match the materialized candidate. GEN source lists must include xgt, rstopt and xrt. XGT_XO f5f35855d and its shared XS4 source are prepared dependencies, with source-bound mechanism PASS; native/physical qualification remains pending and it is not selected here.

The CTRL main route finished but is NEEDS_RTL, with TT+108.17/FF−13.28 ps. The raw final FF report shows three reset-removal violations; all D endpoints pass. The fallback route remains live. Bind only the first actual CLOSED exact-master/source view, preserving the losing candidate until that closure is established.

GUNIT L5 is a child view, not a whole parent replacement. IDX RG3/OH2/RH2 is a structural successor with explicit calendar cost. SEQ mux_h has no qualified implementation yet; the enlarged slot is a model, and ACKP adds an edge only to host_ack_n. D512 KV leaf has real functional component evidence but is not bound or physically qualified. These obligations remain explicit rather than being represented as aliases or full-token closure.
