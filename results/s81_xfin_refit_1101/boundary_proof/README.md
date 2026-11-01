Boundary rewrite closure for 8f0bf2371d540ee4daa6d5b627f446395002abb1

The successful attempt_02 proves the changed input-valid, root-valid, sticky-fault and valid-qualified root-data mechanisms against the prior source. The unchanged arithmetic datapath is abstracted by unconstrained wr_v/wr_n/wr_d/f_add/dup streams. Induction uses held-root equality when each root is complete. No cycle is added. Parent ot_s81dv_xfin observes root data only under r_v; zeroing it outside r_v is intentionally allowed.

Native Yosys 0.68: unmutated proof succeeds; valid-qualified bit corruption produces an actual counterexample. This is a compositional boundary proof, not an unqualified equality claim for inactive root pins. Prior full golden arithmetic functional baselines and mutation controls remain in the containing evidence directory.

Attempts 00 and 01 were harness/tool errors and are retained with diagnoses, not counted as RTL failures. Reproduction: run prove.py from a checkout containing the named source commit with YOSYS set to the fleet native Yosys.
