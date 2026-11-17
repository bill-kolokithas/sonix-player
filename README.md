# Material for the SonixLink / Tidal pull requests

Screenshots and the scripts used to test the PRs in the simulator. Not meant to be merged anywhere.

## screenshots/

- `tidal-flow.png`: the Tidal page with the new row, the favourite playlists, an opened one
- `tidal-my-playlists-unchanged.png`, `tidal-favourite-playlists-empty.png`, `tidal-favourite-playlists-error.png`
- `app-queue-before-after.png`: the SonixLink app's queue page against the simulator built from `main` (left) and from the PR (right)

## tests/

The scripts expect to run from one working directory (or `SONIX_TEST_DIR`), with the sonix-player checkout in `SONIX_REPO` (default `../sonix-player`), `ffmpeg`, Xephyr on `:99` and unprivileged user namespaces.

- `setup_sim.sh` builds a throwaway card: two library FLACs (silent), Tidal and Qobuz cache files with `.tags` sidecars (one with quotes and a backslash, one in Greek and Japanese, one with no sidecar), and a kept podcast episode.
- `run_sim.sh <binary> <log>` starts the simulator on `:99` in a private user and mount namespace where that card is `/mnt/sd_0`, which is where the caches live on the device. Nothing on the host is touched.
- `test_queue.py <binary>` is the `/api/queue` test: library-only queue, mixed queue, paging, nine malformed sidecars, 12 s of parallel readers while the queue is reordered, then a scan of the sanitizer log. It has to finish within SonixLink's 60 s boot grace, since the host has no `wlan0`.
- `mock_tidal.py <port> <log>` stands in for api.tidal.com/v1, with the real response shapes; `start_tidal_sim.sh` points the simulator at it with dummy keys and a fake session through `[tidal] base_url`.
- `tap.py <x> <y>` taps the simulator on `:99` through XTest; `prep_queue.sh` sets up the mixed queue for the app test.
