import os

import flask
import httplib2
from apiclient import discovery
from apiclient.http import MediaIoBaseDownload, MediaFileUpload
from oauth2client import client
from oauth2client.file import Storage

app = flask.Flask(__name__)


@app.route('/')
def index():
    credentials = get_credentials()
    if not credentials:
        return flask.redirect(flask.url_for('oauth2callback'))
    elif credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        all_files = fetch("'root' in parents and mimeType = 'application/vnd.google-apps.folder'",
                          sort='modifiedTime desc')
        s = ""
        for file in all_files:
            s += "%s, %s<br>" % (file['name'], file['id'])
        return s


@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets('client_id.json',
                                          scope='https://www.googleapis.com/auth/drive',
                                          redirect_uri=flask.url_for('oauth2callback',
                                                                     _external=True))
    flow.params['include_granted_scopes'] = 'true'
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        open('credentials.json', 'w').write(credentials.to_json())
        return flask.redirect(flask.url_for('index'))


def get_credentials():
    credential_path = 'credentials.json'

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        print("Credentials not found.")
        return False
    else:
        print("Credentials fetched successfully.")
        return credentials


def fetch(query, sort='modifiedTime desc'):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    results = service.files().list(
        q=query, orderBy=sort, pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items


def download_file(file_id, output_file):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    request = service.files().export_media(fileId=file_id,
                                           mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    fh = open(output_file, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.close()


def update_file(file_id, local_file):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    file = service.files().get(fileId=file_id).execute()
    media_body = MediaFileUpload(local_file, resumable=True)
    updated_file = service.files().update(
        fileId=file_id,
        media_body=media_body).execute()


if __name__ == '__main__':
    if not os.path.exists('client_id.json'):
        print('Client secrets file (client_id.json) not found in the app path.')
        exit()
    import uuid

    app.secret_key = str(uuid.uuid4())
    app.run(debug=True)
