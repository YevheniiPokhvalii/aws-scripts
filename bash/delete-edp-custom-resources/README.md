# The script to remove custom EDP resources

**Goals**: Some custom EDP resources are not deleted automatically along with an EDP namespace.<br>
This is a POSIX compliant script to remove Kubernetes finalizers from custom resource objects.

**Prerequisites**: `kubectl`>=1.23, `awscli` (for EKS authentication)

**Tested on**: Linux, FreeBSD, Windows (GitBash); Shells (zsh, bash, dash)

**Usage**: `chmod +x` on the script and run it. The prompt will ask you to enter the EDP namespace.<br>
Also, you can choose to delete this namespace along with all custom resources.
