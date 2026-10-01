"""Start the offline analyst dashboard."""
import logging
from app.main import create_app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    create_app().run(host='127.0.0.1',port=26228,debug=False)
