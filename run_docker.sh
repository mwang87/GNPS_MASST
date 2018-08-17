docker rm gnps_molecularblast
docker run -d -p 5051:5008 --name gnps_molecularblast gnps_molecularblast /app/run_server.sh
