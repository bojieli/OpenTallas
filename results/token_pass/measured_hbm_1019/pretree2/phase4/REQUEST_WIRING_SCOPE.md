# Static VM read identity and nonalias scope

This is the direct RTL PRETREE1, MUT0, MULTIRATE0, PIN_REG0, single-serial-clock
component benchmark. Its clocking does not establish physical timing or die bind.

The benchmark splits each prog.mem quarter word literally into control/vmr/vmw/rf/red.
The top and quarter only slice vmr into the quarter and bank-pair buses. Pgslice
assigns su_rq = {c[29], c[28:13]} for each30-bit VM request command. MULTIRATE0
wires leaf_rq=su_rq. The VM bank leaf, MUT0, assigns lg_rq={su_rq[16],su_rq[15:0]}.
Thus every actual external read request in this benchmark has exactly the encoded
sector and validity; there is no request arbitration, address rewrite or dynamic
rescheduling on this path. The source hashes are in request_wiring_sources.json.

The machine certificate enumerates every request source sector and all eight
source words at its programmed edge, through the conservative RR12+4 return/capture
allowance. It compares these with every expected write's exact source-pin quarter,
port, sector, word mask and timestamp. All4098 read/write sector records are retained.
No read has an earlier or overlapping write to any source word. Phase2's scalar
source498 is read before its later tensor overwrite. Final scalar writes use
previously-consumed input rows0/1, outside both live future-source ranges.

Runtime exactness is still a prerequisite: the benchmark checks every actual write
against the expected pin address, mask, data and edge, and checks zero faults. The
existing leaf checks read-return timing. A missing read trace is explicitly recorded
as runtime_pin_trace_observed=false; this source-wiring certificate is not presented
as an independently recorded request trace. The alias mutant tests input identity,
not write visibility. These scope limits and hashes travel with any measured result.
