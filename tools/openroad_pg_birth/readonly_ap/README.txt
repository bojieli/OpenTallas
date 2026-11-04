READ-ONLY source packet. Bounded pinned build passed; native design accessor not exercised yet.
load /work/apreader.so Apreader
set db [ord::get_db]
set block [ord::get_db_block]
set record [ot_ap_read_instance [$db getId] [$block getId] INSTANCE_NAME]
Returns an ordinary Tcl dictionary with instance/master/actual APidx and each
master MPin's total bucket count, all bucket sizes, bounds flag, and selected
bucket AP records (ID/MPin ID/layer/coords/per-cut-via-bucket ID+type).
No SWIG nested-vector conversion; the vector is read inside C++ public API.
An out-of-range index is DATA (index_in_range0), never dereferenced. Empty PG
MPins can be legitimate; classify functional signal pins separately. The
index is not an orientation enum. AP metadata is read in master coordinates.
No mutation/callback/birth capability/PG admission/RC/PA/STA operation is added.
Build only inside exact image16470 using cached pinned83headers, normal fleet:
g++ -std=c++20 -O2 -shared -fPIC -I/headers -I/usr/include/tcl8.6 ap_reader.cpp -o apreader.so
Exact executable SHA is checked at module initialization before command registration.
