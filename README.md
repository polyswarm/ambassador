`docker build -t polyswarm/ambassador -f docker/Dockerfile .`

This repo is for pumping malware through polyswarmd, for use with the test.yml file of `polyswarm/orchestration` repo

7/2/2018 - dev build pushed to master, if todays date is AFTER 7/2/18 and polyswarmd is on 646bdf947c94f21b61cdf89cb6f48dba69627a95 or earlier, `git reset --hard 0ac6b79cc9798fbc5926aaba80aaf26b57f33f6b` then `docker build -t polyswarm/ambassador -f docker/Dockerfile .`

