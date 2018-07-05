#!/bin/bash
set -e
set -o pipefail

export CLOUD_SDK_REPO="cloud-sdk-$(echo jessie)"
echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
apt-get update && apt-get install google-cloud-sdk kubectl -y
# gcloud init --console-only --skip-diagnostics
