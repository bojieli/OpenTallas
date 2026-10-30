Actual native HEAD START input pin to first synchronizer D extraction.
Source die-head-34/mesh_e/kit/hd_mesh_e 6_final.odb+6_final.spef,
using the signoff_r3fwd exact TT/FF RVT libraries and SDC.
This core is NOT SIGNED; pin->D delays are component measurements, not a
phase/margin/STA pass. Reports split min/max and input rise/fall. Native
START rises monotonically: s0 rise delay TT170.228485..173.799072 ps,
FF132.208465..134.925965 ps; optional sf branch TT41.913453..42.2901,
FF27.499268..27.733093 ps. Full edge envelopes retained in JSON.
Three current HEAD hd_mesh_e instances can reuse this type component;
external parent wire delay and actual die phase remain separate/open.
Initial PathEnd startpoint/endpoint property expansion SIGSEGV was a
measurement API failure. Canonical report_checks works without that API.
FF SDC is the recorded golden input constraint, without signoff post-load
hold-overlay replay. Port->D subtracts the input pin arrival, so no virtual
clock insertion or input-delay budget is claimed as a physical wire delay.
Virtual19:02 run collection: ODBs+guides terminal OT_DONE, no extractedSPEF
(RCX0134); guide reconstruction readout remains diagnostic and unadopted.
