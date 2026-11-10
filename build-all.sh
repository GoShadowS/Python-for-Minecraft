#!/usr/bin/env bash
# Builds every Python-for-Minecraft component and example mod for every supported
# combination of loader and Minecraft version.
#
# This script needs what the sandbox it was written in does not have: a JDK (21 and 25)
# and network access to Maven Central, maven.fabricmc.net, maven.neoforged.net and
# piston-meta.mojang.com. It has therefore never been executed by the project itself; the
# state of every cell is recorded in docs/testing.md.
#
# Usage:
#   ./build-all.sh                # all four combinations
#   ./build-all.sh fabric-1.21.1  # one combination
#   GRADLE=gradle ./build-all.sh  # use a specific Gradle launcher
set -euo pipefail

cd "$(dirname "$0")"

PLATFORMS=(fabric-1.21.1 fabric-26.3 neoforge-1.21.1 neoforge-26.3)
# Fabric's own example project pins Gradle 9.8.2 on both 1.21.1 and 26.3; ModDevGradle's
# own wrapper pins 8.14.5. One Gradle version cannot serve both loaders.
declare -A GRADLE_VERSION=(
  [fabric-1.21.1]=9.8.2
  [fabric-26.3]=9.8.2
  [neoforge-1.21.1]=8.14.5
  [neoforge-26.3]=8.14.5
)
declare -A JAVA_VERSION=(
  [fabric-1.21.1]=21
  [fabric-26.3]=25
  [neoforge-1.21.1]=21
  [neoforge-26.3]=25
)

if [[ $# -gt 0 ]]; then
  PLATFORMS=("$@")
fi

# The checks that need no JDK come first: if these fail, nothing else is worth building.
echo "== checks that need no JDK"
python3 -m unittest discover -s python/tests -t python
python3 tools/validate_metadata.py
python3 tools/check_java.py
python3 tools/vendor_deps.py --check \
  --requirements examples/pyhello-common/requirements.txt \
  --out examples/pyhello-common/python/vendor

for platform in "${PLATFORMS[@]}"; do
  gradle_version="${GRADLE_VERSION[$platform]}"
  java_version="${JAVA_VERSION[$platform]}"
  echo
  echo "== ${platform} (Gradle ${gradle_version}, JDK ${java_version})"

  if ! command -v java >/dev/null 2>&1; then
    echo "   BLOCKED: no java on PATH" >&2
    exit 1
  fi
  java_major="$(java -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+).*/\1/')"
  if [[ "${java_major}" -lt "${java_version}" ]]; then
    echo "   BLOCKED: this combination needs JDK ${java_version}, found ${java_major}" >&2
    exit 1
  fi

  if [[ -x "platforms/${platform}/gradlew" ]]; then
    launcher="./gradlew"
  else
    echo "   note: no Gradle wrapper jar committed; using '${GRADLE:-gradle}'"
    launcher="${GRADLE:-gradle}"
  fi

  ( cd "platforms/${platform}" && "${launcher}" --no-daemon build )
  for example in pyhello-client pyhello-common; do
    ( cd "examples/${example}/${platform}" && "${launcher}" --no-daemon build )
  done
  echo "   done: ${platform}"
done

echo
echo "== artifacts"
find platforms examples -path '*/build/libs/*.jar' -print 2>/dev/null | sort || true
