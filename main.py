# main.py
from app import app
import views

import dash_masstplus
import dash_microbemasst
import dash_foodmasst2
import dash_plantmasst
import dash_metadatamasst

if __name__ == '__main__':
    app.run(host='0.0.0.0',port='5000')
