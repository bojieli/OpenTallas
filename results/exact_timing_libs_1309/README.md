# Exact timing-library selection

Standalone postcts_gate.tcl and signoff.py embed the same canonical timing_libs.tcl API (strict byte-identity regression); neither needs a new sibling runtime file. Existing generator bundle lists stay coherent. Frozen kits are not modified and must use an owner-refreshed successor.

Selector queries the actual kit config via ORFS make print-TC_LIB_FILES / print-BC_LIB_FILES (WC only for explicitly requested informational SS). It loads the complete exact result, including configured macro views; no installed-version glob or automatic VT expansion. Missing config/list, empty make result, repeated records, unresolved/missing files, duplicate files/stdcell group versions, wrong corners and incomplete five standard-cell groups fail closed. Receipt records config SHA256 and every loaded library SHA256; LOADED is written only after every read_liberty succeeds. Old receipts retained.

Signoff mounts the kit read-only at /work. Optional no-kit use must provide --library-config; no silent glob fallback. Macro paths then resolve under the config directory. This adds no new generator copy dependency. Existing signoff.py helpers such as clock_family/pair_skew remain required as before.

Actual pinned image library-only probe (no design STA/physical rerun) unit oth-ubuntu-2820116-1792961831 EXIT0 selects exactly5 files per corner: AO/OA/SIMPLE211120,INVBUF220122,SEQ220123; receipts and original Liberty warnings retained. Initial unit2762857 EXIT0 preceded only receipt-status/preservation hardening; its log is retained.

Tests: existing signoff+hold basis and first10 selector controls68PASS; final12 focused selector controls PASS, including actual standalone postgate selector without sibling and configured macro retention. Old test expecting wildcard-selected SS/macro aliases updated to exact make-selector behavior. No corrected numerical signoff result is claimed. Earlier retained-head sizing/clock API receipts used broad globs, and remain API/diagnostic evidence only.
