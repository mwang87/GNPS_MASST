build:
	docker build -t gnps_molecularblast .
server:
	docker run -d -p 5052:5005 --rm --name gnps_molecularblast gnps_molecularblast /app/run_server.sh
