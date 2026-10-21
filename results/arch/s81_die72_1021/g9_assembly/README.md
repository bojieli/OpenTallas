# G9 source assembly preparation, 2026-10-21 takeover13:40

This is a source candidate and binding handover. No G9 GEN or physical chain has been launched. Current G8IQ remains immutable and diagnostic.

`g8_actual_scope.json` copies the actual case census: 159 stand-in instances across 21 masters. The priority eleven masters account for 101; the other 58 are services, CTRL, SerDes and slice parents. The case also records 259 crossings without a landing ring, 58 without a clock root and 25 hops over 405 um. Preserve these failures when using available views.

`source_assembly.json` pins the normal-slice change from 6893686b3. Its only source delta is three child-master names: xg→xgt and xr1/xr3→xrt1/xrt3. Exact substitution reproduces the whole file, and all four named source files match the materialized candidate. GEN source lists must include xgt, rstopt and xrt. XGT_XO f5f35855d and its shared XS4 source are prepared dependencies, with source-bound mechanism PASS; native/physical qualification remains pending and it is not selected here.

The CTRL main route finished but is NEEDS_RTL, with TT+108.17/FF−13.28 ps. The raw final FF report shows three reset-removal violations; all D endpoints pass. The fallback route remains live. Bind only the first actual CLOSED exact-master/source view, preserving the losing candidate until that closure is established.

GUNIT L5 is a child view, not a whole parent replacement. IDX RG3/OH2/RH2 is a structural successor with explicit calendar cost. SEQ mux_h has no qualified implementation yet; the enlarged slot is a model, and ACKP adds an edge only to host_ack_n. D512 KV leaf has real functional component evidence but is not bound or physically qualified. These obligations remain explicit rather than being represented as aliases or full-token closure.

First exact configured CTRL view is now available: bbc9c9b13, source22595e899, TT+67.84/FF+7.64/DRC0. `apply_ctrl_g9.py` adds the distinct native-configured master table row/three defines and replaces16 CTRL placements with whole-view lattice-checked coordinates; source pin/resetboot changes remain explicit. Run this before fresh route construction and before strict bind, on copied plan/table. It invalidates old paths and keeps the241stage map as capacity only.

`dv_rvcase` selects physical views by existing first-ref-wins master lookup, so a table row's `view_ref` alone is metadata. Before a chosen G9 GEN, run `check_ctrl_view_selection.py --view-ref REF ... --table TABLE --out RECEIPT` with the exact ordered GEN refs. It invokes the unchanged production selector, requires the exact CTRL kit and every selected view byte/source pin, and rejects missing native defines. The current source candidate passes with oldCREF,origin/main,5e08 refs selecting exact5e08 CTRLview; no shared tool publication is involved. Rerun with the final immutable refs before GEN. The W lane bindings remain unhardened-parent child bindings and do not remove top-level parent stand-ins.
