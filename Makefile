server-compose-build:
	docker-compose build

server-compose-interactive:
	docker-compose build
	docker-compose up

server-compose-server:
	docker-compose up -d

server-compose-production:
	docker-compose -f docker-compose.yml up -d

build:
	docker build -t gnps_molecularblast .

build-no-cache:
	docker build --no-cache -t gnps_molecularblast .

server:
	docker run -d -p 5052:5005 --rm --name gnps_molecularblast gnps_molecularblast /app/run_server.sh

interactive:
	docker run -it -p 5052:5005 --rm --name gnps_molecularblast gnps_molecularblast /app/run_server.sh
