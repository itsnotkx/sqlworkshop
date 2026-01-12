to launch:
1. activate or create a virtual environment: ```py -m venv .venv```
2. launch the virtual environment: ```.venv\scripts\activate```
3. install dependencies: ```pip install -r requirements.txt```
4. load the database using mysql workbench(run the create insert script)
5. create a .env file with the following arguments:
```
MYSQL_HOST: host name
MYSQL_PORT: port number
MYSQL_USER: username
MYSQL_PASSWORD: password
MYSQL_DATABASE: database name
```
6. launch the app: ```py app.py```
7. open to public using ngrok: ```ngrok http 5000```; share the link with participants

note: does not run on school wifi