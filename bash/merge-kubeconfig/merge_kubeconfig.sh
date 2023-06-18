#!/bin/sh

kubeconfig_script_help() {
    # Display Help
    echo "Merge kubeconfigs into one file"
    echo "Usage:"
    echo "      $0 kubeconfig1 kubeconfig2 ..."
    echo
    echo "Additional options: "
    echo "      $0 [OPTIONS...]"
    echo "Options:"
    echo "h     Print Help."
    echo "r     Shorten all AWS kubeconfig context names."
    echo "g     Generate kubeconfig for the current context."
    echo
}

merge_kubeconfig() {
    temp_config=$(mktemp)

    # ctrl-C trap for Bash
    trap 'rm -f -- "$temp_config"' EXIT

    config_dir="$HOME/.kube/"
    config_path="$HOME/.kube/config"
    config_backup="$HOME/.kube/config_$(date +"%Y%m%d_%H%M").bak"

    if [ -f "$config_path" ]; then
        cp "$config_path" "$config_backup"
        echo "Creating kubeconfig backup to $config_backup"
    fi

    if [ ! -d "$config_dir" ]; then
        mkdir "$config_dir"
        echo "Creating kubeconfig directory $config_dir"
    fi

    export KUBECONFIG="$*"
    printf '%s\n' "Using PATH KUBECONFIG=$KUBECONFIG"
    kubectl config view --flatten > "$temp_config"
    mv "$temp_config" "$config_path"
    chmod 600 "$config_path"
}

rename_contexts() {
    kubectl config get-contexts --output=name | while read -r cluster_name; do
        cluster_name_short="$(printf '%s' "$cluster_name" | cut -d "/" -f 2-)"
        kubectl config rename-context "$cluster_name" "$cluster_name_short"
    done

    echo "Current context: $(kubectl config current-context)"
}

gen_kubeconfig() {
    kubectl config view --minify --raw
}

if [ "$#" -eq 0 ]; then
    kubeconfig_script_help
fi

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h | --help)
            # Display Help
            kubeconfig_script_help
            exit 0
            ;;
        -r | --rename)
            # Shorten all AWS kubeconfig context names
            rename_contexts
            exit 0
            ;;
        -g | --generate)
            # Show kubeconfig for the current context
            gen_kubeconfig
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
            # Save to OLDIFS in case the script is sourced
            OLDIFS="$IFS"
            IFS=":"
            merge_kubeconfig "$*"
            IFS="$OLDIFS"
            exit 0
            ;;
    esac
    shift
done
