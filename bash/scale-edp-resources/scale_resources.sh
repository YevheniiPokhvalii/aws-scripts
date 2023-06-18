#!/bin/sh

exit_err() {
    printf '%s\n' "$1" >&2
    exit 1
}

yellow_fg() {
    tput setaf 3 || true
}

no_color_out() {
    tput sgr0 || true
}

get_script_help() {
    self_name="$(basename "$0")"
    echo "\
${self_name} scales EDP Kubernetes Resources

Usage: ${self_name}

Options:
       ${self_name} [OPTION] [FILE]

  -h, --help          Print Help
  -k, --kubeconfig    Pass Kubeconfig file

Examples:
       ${self_name} --kubeconfig ~/.kube/custom_config"
}

get_current_context() {
    kubectl config current-context
}

get_context_ns() {
    kubectl config view \
        --minify --output jsonpath='{..namespace}' 2> /dev/null
}

get_ns() {
    is_context="$(get_current_context)" || exit 1
    printf '%s\n' "Current cluster: [$(yellow_fg)${is_context}$(no_color_out)]"
    printf '%s\n' "Current NS [$(yellow_fg)$(get_context_ns)$(no_color_out)]"
    printf '%s\n' "Enter namespaces. Separate with commas or spaces:"
    read -r namespaces

    if [ -z "${namespaces}" ]; then
        exit_err "Error: namespace is not specified"
    fi
}

set_replicas() {
    printf '%s' "Specify number of replicas [0-1]: "
    read -r replicas
}

scale_resources() {
    kubectl scale deployments,statefulsets --replicas="${replicas}" --all -n "${ns}"
}

scale_res_ns() {
    OLDIFS="$IFS"
    IFS=" ,"

    for ns in ${namespaces}; do
        echo "Scaling in $(yellow_fg)${ns}$(no_color_out)"
        scale_resources
    done

    IFS="$OLDIFS"
}

invalid_option() {
    exit_err "Invalid option '$1'. Use -h, --help for details"
}

main() {
    get_ns
    set_replicas
    scale_res_ns
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

main
