docker rm gnps_molecularblast
docker run -d -p 5052:5050 --name gnps_molecularblast gnps_molecularblast /app/run_server.sh
