#!/bin/sh
S=${SONIX_TEST_DIR:-$PWD}
cat > $S/sim/config/device_config.ini <<CFG
[ui]
language = English

[clock]
configured = true

[streaming]
keys_file = $S/sim/test-keys.ini

[tidal]
base_url = http://127.0.0.1:8765/v1
auth_url = http://127.0.0.1:8765/v1/oauth2
CFG
printf 'access_token=fake-access\nrefresh_token=fake-refresh\nexpires_at=0\ncountry=US\nuser_id=42\nuser=Tester\n' > $S/sim/config/tidal_session.ini
exec sh $S/run_sim.sh sonix_tidal_asan $S/sim/run-tidal.log
