Additive correction of1907; preserve original/R50 byte contracts

The original tools/h3_complete_native_calendar.py is restored byte-identical to pre1907/e78, SHA c0370e63dba0eadcc06c5522c28a956ddebfd10af9b8765a61fe0e4fe025b817. Original tests restored on this branch; parent must preserve its already-reviewed canonical-DS temporary-copy fixture. Restoration hunks remove only1907 additions, leaving that parent correction intact. No parent checkout was changed.

Full versioned implementation now tools/h3_complete_native_calendar_successor_r1.py, SHA dc04ddb7da27b7a1230691a01bba6af6bdd45bacf59b8afc58b0ad853c6c0a21. It retains its own execution globals and all dependencies rather than delegating to original functions. The generic execute_ds_provider_group128 AST equals original. All four self-pin/CLI replay literals explicitly name the successor. New tests are tests/test_h3_complete_native_calendar_successor_r1.py; original tests and R50 do not import it.

All12 successor replay outputs are regenerated here and byte-identical to the1907 records. Old1907 artifacts/manifests/failure log/replay are untouched. The old1907 manifest's original-path implementation hash d533 no longer matches that intentionally restored path; this historical gap is explicit. Historical d533 source snapshot is retained byte-identical in historical_1907_calendar_source.py.gz. New replay imports the successor explicitly and uses retained1907 input archives, requiring only canonical tracked DS/Qwen program archives via --program-root. Never rewrite old records or silently reinterpret their original-path pin.

Kepler R51 contract: see Kepler_R51_constructor_contract.json. R50 remains unchanged/historical. ImportR50 to freeze original constructor anchor, exclude those immutable aliases from compact installation, install exact-constructor compact aliases in canonicalr30 and actual provider alias holders before construction, create shared callable AFTER installation to capture new class, explicitly bind preserved constructor+exact successor logger. Existing R50 older-wrapper constructor predicate is not valid for new class. Select calendar successor explicitly in all PC10Groups/endpoint source checks, verify exact file SHA/function identity/co_filename and unchanged executor AST; keep all other actual provider/PC9/home/lease/service checks intact. Do not change R50 CURRENT_SHA to chase successor files.

Commands:

    python -m unittest discover -s tests -p 'test_h3_complete_native_calendar*.py'
    python results/uarch/h3_complete_native_calendar_20261002/c0_program_shared64_additive_r2/replay.py --program-root . --verify
    PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/test_ds_hbm_current_calendar_adapter_r50.py

89original and14successor calendar tests pass;7historical R50 tests pass. Logs include combined102 tests before adding one namespace/AST test, and final14 successor tests. Original code/test restoration is independently compared againste78. Source outputs and input hashes retained; no whole numeric run, live job change, parent source mutation or heavyweight build.

Storage/services scope unchanged:819950818992B is complete conservative PC0..10 journal reservation with compact shared component, not complete continuation+actual checkpoint GO. Peirce actual project_checkpoint payload/metadata is still required at a real drained boundary.26880new alias rank publications and specialist leases are preserved as continuation obligations with unknown physical fragment aggregate; directedrank0shared9216children is not96rankproduction. Sink/consumer/reverse/CDC/HBM/L2 service remains unknown. No software ticks-to-hardware conversion, cached eligibility-as-grant or headline credit.

Parent can apply1907 then this corrective commit as one unpublished batch; aggregate diff frome78 contains no original tool/test delta. If1907 intake is aborted, export aggregate bounded additive diff frome78 to this successor commit, restricted to new successor tool/test and c0_program_shared64_r1/additive_r2 evidence. Do not replace parent's original test file wholesale. The resulting published original/R50 pins stay valid.
