#!/bin/sh
# Builds a throwaway simulator environment: card, config, resource tree.
set -eu
SIM=${SONIX_TEST_DIR:-$PWD}/sim
REPO=${SONIX_REPO:-../sonix-player}

rm -rf "$SIM/card" "$SIM/config" "$SIM/usr"
mkdir -p "$SIM/card/Music/Test Artist/Test Album" "$SIM/card/.local/tidal-cache" \
	"$SIM/card/.local/qobuz-cache" "$SIM/config" "$SIM/usr"
cp -r "$REPO/sonix-packer/assets/R1/usr/resource" "$SIM/usr/"

silent() { # out, then -metadata pairs
	out=$1; shift
	ffmpeg -loglevel error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 20 "$@" "$out"
}

silent "$SIM/card/Music/Test Artist/Test Album/01 Library Song.flac" \
	-metadata title="Library Song" -metadata artist="Test Artist" -metadata album="Test Album" -metadata track=1
silent "$SIM/card/Music/Test Artist/Test Album/02 Second Song.flac" \
	-metadata title="Second Song" -metadata artist="Test Artist" -metadata album="Test Album" -metadata track=2

# Cached streaming tracks: no tags in the file, only the sidecar, as the
# caches write them.
silent "$SIM/card/.local/tidal-cache/111111111.flac"
printf 'title=Bohemian "Rhapsody" \\ Live\nartist=Queen\nalbum=A Night at the Opera\ntrack=11\nalbum_id=1000\n' \
	> "$SIM/card/.local/tidal-cache/111111111.flac.tags"
silent "$SIM/card/.local/tidal-cache/222222222.flac"
printf 'title=Ελληνικά — 日本語 ✓\nartist=Σωκράτης\nalbum=Ünïcödé\ntrack=2\nalbum_id=2000\n' \
	> "$SIM/card/.local/tidal-cache/222222222.flac.tags"
silent "$SIM/card/.local/tidal-cache/333333333.flac"
silent "$SIM/card/.local/qobuz-cache/444444444.flac"
printf 'title=Qobuz Track\nartist=Qobuz Artist\nalbum=Qobuz Album\ntrack=4\n' \
	> "$SIM/card/.local/qobuz-cache/444444444.flac.tags"

mkdir -p "$SIM/card/Podcast/My Show"
silent "$SIM/card/Podcast/My Show/2026-10-05 Episode.flac"
printf 'title=Episode 12: Tests\nartist=My Show\nalbum=My Show\n' > "$SIM/card/Podcast/My Show/2026-10-05 Episode.flac.tags"

cat > "$SIM/config/device_config.ini" <<EOF
[wireless]
sonixlink = 1
EOF
echo "sim ready in $SIM"
