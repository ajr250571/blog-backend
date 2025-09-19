docker-compose up --build

docker exec -it django /bin/bash

## Run tests
python manage.py test