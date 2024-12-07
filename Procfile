release: flask db upgrade
web: gunicorn -w 1 -k eventlet app:app
