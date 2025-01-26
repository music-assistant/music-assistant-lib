#!/usr/bin/env bash
ABS_VERSIONS=(
  "2.16.0"
  "2.16.1"
  "2.16.2"
  "2.17.0"
  "2.17.1"
  "2.17.2"
  "2.17.3"
  "2.17.4"
  "2.17.5"
  "2.17.6"
  "2.17.7"
  "2.18.0"
  "2.18.1"
)

ABS_VERSION="${ABS_VERSION:-2.7.0}"
PATH_BASE="/pod/abs-test/$ABS_VERSION"
mkdir -p ${PATH_BASE}/{config,metadata,audiobooks1,audiobooks2,podcasts1,podcasts2}

podman run \
  --replace \
  --net=brpod0 \
  --ip="192.168.47.99" \
  -v "$PATH_BASE/config":/config \
  -v "$PATH_BASE/metadata":/metadata \
  -v "$PATH_BASE/audiobooks1":/audiobooks1 \
  -v "$PATH_BASE/audiobooks2":/audiobooks2 \
  -v "$PATH_BASE/podcasts1":/podcasts1 \
  -v "$PATH_BASE/podcasts2":/podcasts2 \
  --name abs-test \
  -e TZ="Europe/Berlin" \
  "ghcr.io/advplyr/audiobookshelf:${ABS_VERSION}"
podman container rm abs-test
