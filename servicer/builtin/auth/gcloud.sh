#!/bin/bash
set -e
set -o pipefail

main() {
  echo
  echo "---- ---- ---- ----"
  echo " gcloud auth"
  echo "---- ---- ---- ----"
  echo
  gcloud -v

  if [ -f "$GCLOUD_KEY_FILE_PATH" ]; then
    echo "gcloud key-file already exists: $GCLOUD_KEY_FILE_PATH"
  else
    echo "generating gcloud key-file: $GCLOUD_KEY_FILE_PATH"
    touch "$GCLOUD_KEY_FILE_PATH"
    echo "$GCLOUD_KEY_FILE_JSON" > "$GCLOUD_KEY_FILE_PATH"
  fi

  gcloud auth activate-service-account --key-file "$GCLOUD_KEY_FILE_PATH"
  gcloud config set project "$PROJECT_NAME"
  gcloud config set compute/zone "$GCLOUD_COMPUTE_ZONE"

  return $?
}

main
