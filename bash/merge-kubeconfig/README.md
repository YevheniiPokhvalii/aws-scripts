# The script to merge kubeconfig files and shorten AWS contexts names

**Prerequisites**: `kubectl`<br>

> By default (without flags), this script merges kubeconfig files (pass kubeconfig locations to the script).<br>
Example: `./script.sh kubeconfig1 kubeconfig2 path-to/.kube/config ...`<br>

Additional features:
* Flag `-r` renames all AWS contexts to shorten their names.<br>
Example: `Context "arn:aws:eks:region-1:xxxxxxxxxxx:cluster/test" will be renamed to "test".`
* Flag `-g` displays a `kubeconfig` file for the current context (can be used for Lens).<br>
