#!/usr/bin/python

# Copyright (C) 2014 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, 'lib')

import endpoints
import os

from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop

from protorpc import messages
from protorpc import remote
from endpoints_proto_datastore.ndb import EndpointsModel
from endpoints_proto_datastore.ndb import EndpointsAliasProperty

import httplib2
from apiclient.discovery import build
from oauth2client.client import AccessTokenCredentials

_CLIENT_IDs = [
    endpoints.API_EXPLORER_CLIENT_ID,
    'YOUR_CLIENT_ID'
]


class Line(messages.Enum):
    AKSUMITE = 1
    CAHOKIAN = 2
    DONGHU = 3
    HARAPPAN = 4
    KOORI = 5
    LATENE = 6
    MINOAN = 7
    MU = 8
    NABATEAN = 9
    OLMEC = 10
    SHANG = 11
    SUMERIAN = 12


class Student(EndpointsModel):

    _message_fields_schema = ('id', 'name', 'link', 'image', 'line')

    name = ndb.StringProperty(required=True)
    link = ndb.StringProperty(required=True)
    image = ndb.StringProperty(required=True)
    line = msgprop.EnumProperty(Line, required=True)

    def IdSet(self, value):
        if not isinstance(value, basestring):
            raise TypeError('ID must be a string.')
        self.UpdateFromKey(ndb.Key(Student, value))

    @EndpointsAliasProperty(setter=IdSet, required=True)
    def id(self):
        if self.key is not None:
            return self.key.string_id()


def check_auth(id):
    user = endpoints.get_current_user()
    if user is None:
        return False

    # We want to check if the submitted user id is the same the user authenticated with
    # Since endpoints.get_current_user() only includes the email but not the ID
    # we have to use a workaround for this, until this issue is fixed:
    # https://code.google.com/p/googleappengine/issues/detail?id=8848

    # We could use the email address as ID instead, but for privacy reason
    # I didn't want to store it and wanted to use the public G+ ID instead

    if "HTTP_AUTHORIZATION" in os.environ:
        (tokentype, token) = os.environ["HTTP_AUTHORIZATION"].split(" ")
    else:
        return False

    credentials = AccessTokenCredentials(token, 'my-user-agent/1.0')
    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('plus', 'v1', http=http)

    try:
        profile = service.people().get(userId='me', fields='id').execute()
    except:
        return False

    if id != profile['id']:
        return False

    return True


api_root = endpoints.api(name='ancientsocieties', version='v1', allowed_client_ids=_CLIENT_IDs)


@api_root.api_class(resource_name='student', path='students')
class StudentsService(remote.Service):

    @Student.method(request_fields=('id',), path='/students/{id}',
                    http_method='GET', name='get')
    def get(self, student):
        if not student.from_datastore:
            raise endpoints.NotFoundException('Student not found.')
        return student

    @Student.method(path='/students/{id}', http_method='POST',
                    name='insert')
    def insert(self, student):

        if not check_auth(student.id):
            raise endpoints.UnauthorizedException('You may only enter or change your own data.')

        student.put()
        return student

    @Student.method(request_fields=('id',), response_fields=('id',),
                    path='/students/{id}',
                    http_method='DELETE', name='delete')
    def delete(self, student):
        if not student.from_datastore:
            raise endpoints.NotFoundException('Student not found.')

        if not check_auth(student.id):
            raise endpoints.UnauthorizedException('You may only enter or change your own data.')

        student.key.delete()
        return student

    @Student.query_method(query_fields=('limit', 'pageToken'),
                          path='/students', name='list')
    def list(self, query):
        return query


server = endpoints.api_server([StudentsService], restricted=False)
