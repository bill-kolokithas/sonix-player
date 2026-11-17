#!/bin/sh
# run_sim.sh <binary> <log>: runs the simulator on :99 in a private mount
# namespace where the throwaway card is /mnt/sd_0.
S=${SONIX_TEST_DIR:-$PWD}/sim
BIN=$1
LOG=$2
exec unshare --user --map-root-user --mount sh -c "
mount -t tmpfs none /mnt && mkdir /mnt/sd_0 && mount --bind '$S/card' /mnt/sd_0 || exit 1
cd '$S' && exec env DISPLAY=:99 SDL_VIDEODRIVER=x11 SONIX_SD_ROOT=/mnt/sd_0 \
	SONIX_CONFIG='$S/config/device_config.ini' SONIX_NO_MOUNT=1 SONIX_NO_SYSSERVER=1 SONIX_PANEL=480x800 \
	ASAN_OPTIONS=halt_on_error=0:detect_leaks=0 UBSAN_OPTIONS=print_stacktrace=1 \
	'./$BIN' > '$LOG' 2>&1
"
