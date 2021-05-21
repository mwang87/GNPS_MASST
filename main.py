# main.py
from app import app
import views

import dash_masstplus


if __name__ == '__main__':
    app.run(host='0.0.0.0',port='5000')
