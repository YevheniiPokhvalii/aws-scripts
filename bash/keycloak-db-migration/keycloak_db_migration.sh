#!/bin/bash

# set -x

db_migration_help(){
    echo "Keycloak Postgres database migration"
    echo
    echo "Usage:"
    echo "------------------------------------------"
    echo "Export Keycloak Postgres database from pod"
    echo "Run without parameters:"
    echo "      $0"
    echo "------------------------------------------"
    echo "Import Keycloak Postgres database to pod"
    echo "Pass filename to script:"
    echo "      $0 path/to/db_dump.sql"
    echo "------------------------------------------"
    echo "Additional options: "
    echo "      $0 [OPTIONS...]"
    echo "Options:"
    echo "h     Print Help."
    echo "c|v   Run garbage collector and analyzer."
}

keycloak_ns(){
    printf '%s\n' 'Enter keycloak namespace: '
    read -r keycloak_namespace

    if [ -z "${keycloak_namespace}" ]; then
        echo "Don't skip namespace"
        exit 1
    fi
}

postgres_pod(){
    printf '%s\n' 'Enter postgres pod name: '
    read -r postgres_pod_name

    if [ -z "${postgres_pod_name}" ]; then
        echo "Don't skip pod name"
        exit 1
    fi
}

postgres_user(){
    printf '%s\n' 'Enter postgres username: '
    printf '%s' "Skip to use [postgres] superuser: "
    read -r postgres_username

    if [ -z "${postgres_username}" ]; then
        postgres_username='postgres'
    fi
}

pgdb_host_info(){
    database_name='keycloak'
    db_host='localhost'
    db_port='5432'
}

postgresql_admin_pass(){
    postgresql_password='POSTGRES_PASSWORD'
    postgresql_admin_password="$(kubectl exec -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
        sh -c "printenv ${postgresql_password}")"
}

postgresql_su_pass(){
    postgresql_postgres_password='POSTGRES_POSTGRES_PASSWORD'
    postgresql_superuser_password="$(kubectl exec -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
        sh -c "printenv ${postgresql_postgres_password}")"

    if [ -z "${postgresql_superuser_password}" ]; then
        echo "SuperUser password variable does not exist. Using user password instead..."
        postgresql_admin_pass
        postgresql_superuser_password="${postgresql_admin_password}"
    fi
}

keycloak_pgdb_export(){
    current_cluster="$(kubectl config current-context | tr -dc '[:alnum:]-')"
    exported_db_name="keycloak_db_dump_${current_cluster}_${keycloak_namespace}_${postgres_username}_$(date +"%Y%m%d%H%M").sql"

    if [ "${postgres_username}" == 'postgres' ]; then
        # call a function to get a pass for postgres user
        postgresql_su_pass
        kubectl exec -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
            sh -c "PGPASSWORD='"${postgresql_superuser_password}"' pg_dumpall -h "${db_host}" -p "${db_port}" -U "${postgres_username}"" > "${exported_db_name}"
    else
        # call a function to get a pass for admin user
        postgresql_admin_pass
        kubectl exec -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
            sh -c "PGPASSWORD='"${postgresql_admin_password}"' pg_dump -h "${db_host}" -p "${db_port}" -U "${postgres_username}" -d "${database_name}"" > "${exported_db_name}"
    fi

    separate_lines="---------------"

    if [ ! -s "${exported_db_name}" ]; then
        rm -f "${exported_db_name}"
        echo "${separate_lines}"
        echo "Something went wrong. The database dump file is empty and was not saved."
    else
        echo "${separate_lines}"
        grep 'Dumped' "${exported_db_name}" | sort -u
        echo "Database has been exported to $(pwd)/${exported_db_name}"
    fi
}

keycloak_pgdb_import(){
    echo "Preparing Import"
    echo "----------------"

    if [ ! -f "$1" ]; then
        echo "The file $1 does not exist."
        exit 1
    fi

    keycloak_ns
    postgres_pod
    postgres_user
    pgdb_host_info

    if [ "${postgres_username}" == 'postgres' ]; then
        # restore full backup with all databases and roles as superuser or a single database
        postgresql_su_pass
        if [ -n "$(cat "$1" | grep 'CREATE ROLE')" ]; then
            cat "$1" | kubectl exec -i -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
                sh -c "cat | PGPASSWORD='"${postgresql_superuser_password}"' psql -h "${db_host}" -p "${db_port}" -U "${postgres_username}""
        else
            cat "$1" | kubectl exec -i -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
                sh -c "cat | PGPASSWORD='"${postgresql_superuser_password}"' psql -h "${db_host}" -p "${db_port}" -U "${postgres_username}" -d "${database_name}""
        fi
    else
        # restore database objects only
        postgresql_admin_pass
        cat "$1" | kubectl exec -i -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
            sh -c "cat | PGPASSWORD='"${postgresql_admin_password}"' psql -h "${db_host}" -p "${db_port}" -U "${postgres_username}" -d "${database_name}""
    fi
}

vacuum_pgdb(){
    echo "Preparing garbage collector and analyzer"
    echo "----------------------------------------"

    keycloak_ns
    postgres_pod
    postgres_user
    pgdb_host_info

    if [ "${postgres_username}" == 'postgres' ]; then
        postgresql_su_pass
        kubectl exec -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
            sh -c "PGPASSWORD='"${postgresql_superuser_password}"' vacuumdb --analyze --all -h "${db_host}" -p "${db_port}" -U "${postgres_username}""
    else
        postgresql_admin_pass
        kubectl exec -n "${keycloak_namespace}" "${postgres_pod_name}" "--" \
            sh -c "PGPASSWORD='"${postgresql_admin_password}"' vacuumdb --analyze -h "${db_host}" -p "${db_port}" -U "${postgres_username}" -d "${database_name}""
    fi
}

while [ "$#" -eq 1 ]; do
    case "$1" in
        -h | --help)
            db_migration_help
            exit 0
            ;;
        -c | --clean | -v | --vacuum)
            vacuum_pgdb
            exit 0
            ;;
        --)
            break
            ;;
        -*)
            echo "Invalid option '$1'. Use -h|--help to see the valid options" >&2
            exit 1
            ;;
        *)
            keycloak_pgdb_import "$1"
            exit 0
            ;;
    esac
    shift
done

if [ "$#" -gt 1 ]; then
    echo "Please pass a single file to the script"
    exit 1
fi

echo "Preparing Export"
echo "----------------"
keycloak_ns
postgres_pod
postgres_user
pgdb_host_info
keycloak_pgdb_export
