docker rm gnps_molecularblast
docker run -d -p 5052:5005 --name gnps_molecularblast gnps_molecularblast /app/run_server.sh
