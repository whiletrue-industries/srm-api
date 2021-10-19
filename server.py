import os
import logging

from flask import Flask
from flask_cors import CORS

import elasticsearch

from apisql import apisql_blueprint
from apies import apies_blueprint


def text_field_rules(field):
    if field.get('es:title'):
        if field.get('es:keyword'):
            return [('exact', '^10')]
        else:
            return [('inexact', '^3'), ('natural', '.hebrew^10')]
    elif field.get('es:boost'):
        if field.get('es:keyword'):
            return [('exact', '^10')]
        else:
            return [('inexact', '^10')]
    elif field.get('es:keyword'):
        return [('exact', '')]
    elif field.get('es:autocomplete'):
        return [('inexact', ''), ('inexact', '_2gram'), ('inexact', '_3gram')]
    else:
        return [('inexact', '')]


app = Flask(__name__)
CORS(app, supports_credentials=True)

# SQL API
app.register_blueprint(
    apisql_blueprint(
        connection_string=os.environ['DATABASE_READONLY_URL'],
        max_rows=10000, debug=False
    ),
    url_prefix='/api/db/'
)

# ES API
index_name = os.environ['ES_INDEX_NAME']
TYPES = ['cards', 'places', 'responses']
datapackages = [x.strip() for x in os.environ['ES_DATAPACKAGE'].split('\n') if x.strip()]
blueprint = apies_blueprint(app,
    datapackages,
    elasticsearch.Elasticsearch(
        [dict(host=os.environ['ES_HOST'], port=int(os.environ['ES_PORT']))], timeout=60,
        **({"http_auth": os.environ['ES_HTTP_AUTH'].split(':')} if os.environ.get('ES_HTTP_AUTH') else {})
    ),
    dict(
        (t, f'{index_name}__{t}')
        for t in TYPES
    ),
    f'{index_name}__docs',
    debug_queries=True,
    text_field_rules=text_field_rules
)
app.register_blueprint(blueprint, url_prefix='/api/idx/')



if __name__=='__main__':
    app.run()
else:
    gunicorn_error_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_error_logger.handlers)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info('SERVER STARTING')
