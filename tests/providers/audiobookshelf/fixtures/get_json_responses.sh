#!/usr/bin/env bash
check_env() {
  if [[ -z "$1" ]]; then
    echo "Variables missing in environment"
    exit 1
  fi
}

check_env "${ABS_VERSION}"
ABS_HOST="${ABS_HOST:-192.168.47.99}"
ABS_USER="${ABS_USER:-root}"
ABS_PASSWORD="${ABS_PASSWORD:-root}"

BASE_PATH="${ABS_VERSION}"
mkdir -p "${BASE_PATH}"

abs_get() {
  token="$1"
  endpoint="$2"
  filename="$3"
  curl "${ABS_HOST}/api/$endpoint" \
    -H "Authorization: Bearer $token" >"${BASE_PATH}/${filename}.json"
}

lib_audiobooks1="1e2fe239-3e2c-4ede-99d6-00f38d67efc9"
lib_audiobooks2="06e88cab-4cf8-4f2c-8bad-aba7dc333c6e"
lib_podcasts1="07e93d0b-c4a2-43e6-baf4-1b17d3cc9948"
lib_podcasts2="4dce6456-f821-424b-8730-1647dddd6f25"

audiobook1="22ed6441-84a6-444a-8bb9-85fbf0495054" #  in lib_audiobooks1, has progress
audiobook2="6b0f6c63-ba21-420d-b7cf-cafc5d55c483" # in lib_audiobooks1, no progress

author1="f7e84877-2a80-43e2-a902-07336f5bf6cb" # in lib_audiobooks1

podcast1="fb1052d4-671a-4a3d-9185-2acbd86cc636"          # in lib_podcasts1
podcast1_episode2="93c2e4b2-8e37-47b6-ae6a-0dfcabf54396" # with progress, 622
podcast1_episode3="97d0f394-88be-48f0-879e-05ced08965f4" # finished, 623

# LOGIN
TOKEN="$(curl -X POST "${ABS_HOST}/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"${ABS_USER}\", \"password\" : \"${ABS_PASSWORD}\"}" \
  | tee "${BASE_PATH}/ABSLoginResponse.json" | jq -r ".user.token")"

# GET
## user
abs_get "$TOKEN" "me" "ABSUser"
## libs
abs_get "$TOKEN" "libraries" "ABSLibrariesResponse"
abs_get "$TOKEN" "libraries/${lib_audiobooks1}/items?minified=1&collapseseries=0" "ABSLibrariesItemsMinifiedBookResponse_1"
abs_get "$TOKEN" "libraries/${lib_audiobooks2}/items?minified=1&collapseseries=0" "ABSLibrariesItemsMinifiedBookResponse_2"
abs_get "$TOKEN" "libraries/${lib_podcasts1}/items?minified=1&collapseseries=0" "ABSLibrariesItemsMinifiedPodcastResponse_1"
abs_get "$TOKEN" "libraries/${lib_podcasts2}/items?minified=1&collapseseries=0" "ABSLibrariesItemsMinifiedPodcastResponse_2"
## single items
abs_get "$TOKEN" "items/${podcast1}?expanded=1" "ABSLibraryItemExpandedPodcast"
abs_get "$TOKEN" "items/${audiobook1}?expanded=1" "ABSLibraryItemExpandedBook_1"
abs_get "$TOKEN" "items/${audiobook2}?expanded=1" "ABSLibraryItemExpandedBook_2"
## progress
abs_get "$TOKEN" "me/progress/${podcast1}/${podcast1_episode2}" "ABSMediaProgress_1"
abs_get "$TOKEN" "me/progress/${podcast1}/${podcast1_episode3}" "ABSMediaProgress_2"
abs_get "$TOKEN" "me/progress/${audiobook1}" "ABSMediaProgress_3"
## authors
abs_get "$TOKEN" "/libraries/${lib_audiobooks1}/authors" "ABSAuthorsResponse"
## single author/ series
abs_get "$TOKEN" "/authors/${author1}?include=items,series" "ABSAuthorResponse"
## collections
abs_get "$TOKEN" "/libraries/${lib_audiobooks1}/collections" "ABSLibrariesItemsMinifiedCollectionResponse"
## playback session
session_id="$(curl -X POST "${ABS_HOST}/api/items/${audiobook1}/play" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"deviceInfo\": {\"clientVersion\": \"0.0.0\", \"deviceId\": \"test\", \"clientVersion\": \"0.0.0\", \"manufacturer\": \"\", \"model\": \"model\"}, \"supportedMimeTypes\": [], \"forceDirectPlay\": false, \"forceTranscode\": false}" | tee "${BASE_PATH}/ABSPlaybackSessionExpanded.json" | jq -r ".id")"
## close session
curl -X POST "${ABS_HOST}/api/session/${session_id}/close" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
