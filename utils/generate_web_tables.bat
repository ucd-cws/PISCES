cd ../scripts/PISCES
C:\Python26\ArcGIS10.0\python.exe ./tables.py query "select * from species where Native=True" "maps/web_output/tables" species.csv
C:\Python26\ArcGIS10.0\python.exe ./tables.py query "select species_aux.* from species_aux, species where species_aux.FID = species.FID and species.Native = True" "maps/web_output/tables" species_aux.csv
C:\Python26\ArcGIS10.0\python.exe ./tables.py table huc12fullstate "maps/web_output/tables" huc12fullstate.csv
C:\Python26\ArcGIS10.0\python.exe ./tables.py table zones_aux "maps/web_output/tables" zones_aux.csv
C:\Python26\ArcGIS10.0\python.exe ./tables.py table forest_boundary "maps/web_output/tables" forest_boundary.csv
C:\Python26\ArcGIS10.0\python.exe ./tables.py query "select observations.* from observations, species where Observations.Species_ID = species.FID and species.Native = True" "maps/web_output/tables" observations.csv
C:\Python26\ArcGIS10.0\python.exe ./tables.py query "select q_all_fish_on_forest_hucs.* from q_all_fish_on_forest_hucs, species where q_all_fish_on_forest_hucs.Species_ID = species.FID and species.Native = True" "maps/web_output/tables" q_all_fish_on_forest_hucs.csv
cmd