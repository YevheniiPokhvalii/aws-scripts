# The script to migrate Keycloak database between Postgres major releases

**Goals**: Postgres database major releases are incompatible and require migration.<br>
This script helps to export and import Postgres databases in Kubernetes.

**Prerequisites**: `kubectl`<br>

> By default (without flags), this script exports Keycloak Postgres databases from a Kubernetes pod to a local machine.<br>
Example: `./script.sh`<br>
Follow the prompt.<br>

> To import a database backup to a newly created Postgres Kubernetes pod, pass a database dump sql file to the script).<br>
Example: `./script.sh path-to/db_dump.sql`<br>

> Additional features:<br>
Flag `-c|-v` will run `vacuumdb` garbage collector and analyzer.<br>

**Note**: This script will likely work for any other Postgres database besides Keycloak after some adjusting.<br>
It queries `pg_dump`, `pg_dumpall`, `psql`, and `vacuumdb` under the hood.
