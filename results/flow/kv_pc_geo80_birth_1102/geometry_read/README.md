# Saved PC GRT geometry for the next physical review

This read-only source query is prepared outside the progressing, immutable grt_only capsule. It cannot run until that job has written its full completion receipt, including the independently reopened saved PG audit. The input mount is read-only; the query opens only the actual saved 5_1_grt OpenDB file and extracts cells, rows, public rectangles and actual PG metal. It invokes no STA, callbacks, repair, route or database write.

The query uses the same immutable image as the physical job, normal 8 GB / one thread through ot-run. Its purpose is the mandatory actual saved-layout image before any proposed detailed-route successor; it is not a new physical variant or a replacement for clock/PG/placement/LEC gates. No query job has been started by this PREP.
