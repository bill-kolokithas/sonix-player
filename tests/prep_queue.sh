#!/bin/sh
S=${SONIX_TEST_DIR:-$PWD}
B=http://127.0.0.1:7800
printf '[ui]\nlanguage = English\n\n[clock]\nconfigured = true\n\n[wireless]\nsonixlink = 1\n' > $S/sim/config/device_config.ini
sh $S/run_sim.sh "$1" $S/sim/run-app.log &
for i in $(seq 1 80); do curl -s -m 1 $B/api/ping >/dev/null && break; sleep 0.25; done
curl -s -X POST "$B/api/command?do=scan" >/dev/null
for i in $(seq 1 50); do curl -s $B/api/state | grep -q '"tracks":2' && break; sleep 0.2; done
curl -s -X POST "$B/api/command?do=play_path&list=album&value=Test%20Album&path=%2Fmnt%2Fsd_0%2FMusic%2FTest%20Artist%2FTest%20Album%2F01%20Library%20Song.flac" >/dev/null
sleep 0.5
printf '/mnt/sd_0/.local/tidal-cache/111111111.flac\n/mnt/sd_0/.local/tidal-cache/222222222.flac\n/mnt/sd_0/.local/tidal-cache/333333333.flac\n/mnt/sd_0/.local/qobuz-cache/444444444.flac\n' | curl -s -X POST --data-binary @- "$B/api/command?do=queue_next" >/dev/null
sleep 0.5
curl -s -X POST "$B/api/command?do=pause" >/dev/null
echo "queue ready: $(curl -s $B/api/state | grep -o '"queue_count":[0-9]*')"
