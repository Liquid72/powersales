FROM python:3.11

WORKDIR /code

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./src /code/src

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update
RUN env ACCEPT_EULA=Y apt-get install -y msodbcsql18

CMD [ "fastapi", "run", "src/", "--port", "80" ]