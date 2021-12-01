from fastapi import FastAPI


from main import start

app = FastAPI()

start()


# Gunicorn :
# gunicorn -w 1 -k uvicorn.workers.UvicornWorker --daemon server:app --log-level debug --error-logfile gunicorn_error.log --bind 127.0.0.1:1873
