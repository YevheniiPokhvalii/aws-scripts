#!/bin/sh

new_line='--------------------'

yellow_fg() {
    tput setaf 3 || true
}

no_color_out() {
    tput sgr0 || true
}

pod_name() {
    printf '%s\n' 'Enter pod name: '
    read -r pod

    if [ -z "${pod}" ]; then
        echo "Don't skip pod name"
        exit 1
    fi
}

namespace() {
    printf '%s\n' 'Enter namespace name: '
    read -r namespace
}

mounted_volumes() {
    kubectl get pod "${pod}" \
        -o jsonpath='{.spec.volumes[*].name}' -n "${namespace}"
}

mounted_volume() {
    kubectl get pod "${pod}" \
        -o jsonpath='{.spec.volumes['"$i"'].name}' -n "${namespace}"
}

pvc() {
    kubectl get pod "${pod}" \
        -o jsonpath='{.spec.volumes['"$i"'].persistentVolumeClaim.claimName}' \
        -n "${namespace}"
}

pv() {
    kubectl get pvc "${pvc}" \
        -o jsonpath='{.spec.volumeName}' -n "${namespace}"
}

aws_volume_id() {
    kubectl get pv "${pv}" \
        -o jsonpath='{.spec.awsElasticBlockStore.volumeID}'
}

aws_volume_name() {
    echo "${aws_volume_id}" | awk -F '/' '{print $4}'
}

iterate() {
    mounted_volumes_count=$(mounted_volumes | wc -w)
    echo "${new_line}"
    i=0
    while [ "$i" -lt "${mounted_volumes_count}" ]; do
        echo "Mounted Volume Name:"
        echo "$(yellow_fg)$(mounted_volume)$(no_color_out)"
        pvc="$(pvc)"
        if [ -n "${pvc}" ]; then
            echo "PersistentVolumeClaim (PVC):"
            echo "$(yellow_fg)${pvc}$(no_color_out)"

            pv=$(pv)
            echo "PersistentVolume (PV):"
            echo "$(yellow_fg)${pv}$(no_color_out)"

            aws_volume_id=$(aws_volume_id)
            echo "AWS Volume ID:"
            echo "$(yellow_fg)${aws_volume_id}$(no_color_out)"

            echo "AWS Volume Name:"
            echo "$(yellow_fg)$(aws_volume_name)$(no_color_out)"
        fi
        echo "${new_line}"

        i=$((i + 1))
    done
}

pod_name
namespace
iterate
