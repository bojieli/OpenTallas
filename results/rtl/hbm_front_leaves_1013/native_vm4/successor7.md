Controller7 is an isolated successor; CLOSEDcontroller6b and lane2 RTL are
unchanged. SOURCE_CAP permits at most16 reservations for the actual sixteen
entry source-bank FIFO, counting formatter-flight entries before arrival.
Credits return only after real VM-clock queue dequeue. Capacity cannot be
borrowed from destination native WG's ten-credit protocol; that ABI remains
unchanged. Five-bit counters protect exact16 and under/overflow. REQ_IDLE
controls only the former request-descriptor phase2 idle edge; all source,
address, destination and range fields remain captured before admission.

Actual baseline profile identifies source reservation stalls, not model
supply throttling or destination ticket saturation. Complete profile and
actual native production successor receipts are required before any fresh
source-bound gate. Use SOURCE_CAP10/REQ_IDLE1 to reproduce baseline semantics,
SOURCE_CAP16/REQ_IDLE1 to isolate reservations, then16/0 to isolate the idle
edge. All cases preserve actual macro/SU readback, unchanged147LOADs, immutable
15674.320143998484price, originalreset/clocks and originalmutants. No physical
or production acceptance is implied by this prepared source.
