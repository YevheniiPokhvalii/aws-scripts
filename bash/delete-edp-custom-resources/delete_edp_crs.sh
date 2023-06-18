#!/bin/sh

###################################################################
# A POSIX script to remove EDP Kubernetes Custom Resources        #
#                                                                 #
# PREREQUISITES                                                   #
#     kubectl>=1.23.x, awscli (for EKS authentication)            #
#                                                                 #
# TESTED                                                          #
#     OS: Ubuntu, FreeBSD, Windows (GitBash)                      #
#     Shells: zsh, bash, dash                                     #
###################################################################

[ -n "${DEBUG}" ] && set -x

set -e

exit_err() {
    printf '%s\n' "$1" >&2
    exit 1
}

check_kubectl() {
    if ! hash kubectl; then
        exit_err "Error: kubectl is not installed"
    fi
}

get_script_help() {
    self_name="$(basename "$0")"
    echo "\
${self_name} deletes EDP Kubernetes Custom Resources

Usage: ${self_name}

Options:
       ${self_name} [OPTION] [FILE]

  -h, --help          Print Help
  -k, --kubeconfig    Pass Kubeconfig file

Debug:
       DEBUG=true ${self_name}

Examples:
       ${self_name} --kubeconfig ~/.kube/custom_config"
}

yellow_fg() {
    tput setaf 3 || true
}

no_color_out() {
    tput sgr0 || true
}

get_current_context() {
    kubectl config current-context
}

get_context_ns() {
    kubectl config view \
        --minify --output jsonpath='{..namespace}' 2> /dev/null
}

get_ns() {
    kubectl get ns "${edp_ns}" --output name --request-timeout='5s'
}

delete_ns() {
    kubectl delete ns "${edp_ns}" --timeout='30s'
}

get_edp_crds() {
    kubectl get crds --no-headers=true | awk '/edp.epam.com/ {print $1}'
}

get_edp_vwc() {
    kubectl get ValidatingWebhookConfigurations \
        --ignore-not-found --request-timeout='15s' \
        | awk '/'"${edp_ns}"'/ {print $1}'
}

get_all_edp_crs_manif() {
    kubectl get "${edp_crds_comma_list}" -n "${edp_ns}" \
        --output yaml --ignore-not-found --request-timeout='15s'
}

del_edp_whc() {
    kubectl delete ValidatingWebhookConfigurations "${edp_vwc_comma_list}" \
        --ignore-not-found --timeout='12s'
}

del_all_edp_crs() {
    kubectl delete --all "${edp_crds_comma_list}" -n "${edp_ns}" \
        --ignore-not-found --timeout='12s'
}

iterate_edp_whc() {
    edp_vwc_comma_list="$(printf '%s' "$(get_edp_vwc)" | tr -s '\n' ',')"
    if [ -n "${edp_vwc_comma_list}" ]; then
        del_edp_whc
    else
        echo "No resources found"
    fi
}

iterate_edp_crs() {
    edp_crds_comma_list="$(printf '%s' "${edp_crds}" | tr -s '\n' ',')"
    get_all_edp_crs_manif \
        | sed '/finalizers:/,/.*:/{//!d;}' \
        | kubectl replace -f - || true
    del_all_edp_crs || true
}

iterate_edp_crds() {
    n=0
    while [ "$n" -lt 2 ]; do
        n=$((n + 1))

        if [ "$n" -eq 2 ]; then
            # Delete remaining resources
            edp_crds="keycloakclients,codebasebranches,codebases,jenkinsfolders"
            iterate_edp_crs
            echo "EDP Custom Resources in NS ${color_ns} have been deleted."
            break
        fi

        echo "Deleting ValidatingWebhookConfigurations..."
        iterate_edp_whc
        echo "Replacing EDP CR Manifests. Wait for output (may take 2min)..."
        edp_crds="$(get_edp_crds)"
        iterate_edp_crs
    done
}

select_ns() {
    is_context="$(get_current_context)" || exit 1
    printf '%s' "Current cluster: "
    printf '%s\n' "$(yellow_fg)${is_context}$(no_color_out)"

    current_ns="$(get_context_ns)" || true

    printf '%s\n' "Enter EDP namespace"
    printf '%s' "Skip to use [$(yellow_fg)${current_ns}$(no_color_out)]: "
    read -r edp_ns

    if [ -z "${edp_ns}" ]; then
        edp_ns="${current_ns}"
        echo "${edp_ns}"
        if [ -z "${edp_ns}" ]; then
            exit_err "Error: namespace is not specified"
        fi
    else
        get_ns || exit 1
    fi

    color_ns="$(yellow_fg)${edp_ns}$(no_color_out)"
}

choose_delete_ns() {
    printf '%s\n' "Do you want to delete namespace ${color_ns} as well? (y/n)?"
    printf '%s' "Skip or enter [N/n] to keep the namespace: "
    read -r answer
    if [ "${answer}" != "${answer#[Yy]}" ]; then
        delete_edp_ns=true
        echo "Namespace ${color_ns} is marked for deletion."
    else
        echo "Skipped. Deleting EDP Custom Resources only."
    fi
}

delete_ns_if_true() {
    if [ "${delete_edp_ns}" = true ]; then
        echo "Deleting ${color_ns} namespace..."
        delete_ns || exit 1
    fi
}

invalid_option() {
    exit_err "Invalid option '$1'. Use -h, --help for details"
}

main_func() {
    check_kubectl
    select_ns
    choose_delete_ns
    iterate_edp_crds
    delete_ns_if_true
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h | --help)
            get_script_help
            exit 0
            ;;
        -k | --kubeconfig)
            shift
            [ $# = 0 ] && exit_err "No Kubeconfig file specified"
            export KUBECONFIG="$1"
            ;;
        --)
            break
            ;;
        -k* | --k*)
            echo "Did you mean '--kubeconfig'?"
            invalid_option "$1"
            ;;
        -* | *)
            invalid_option "$1"
            ;;
    esac
    shift
done

main_func
