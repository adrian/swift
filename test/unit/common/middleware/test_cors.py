# Copyright (c) 2010-2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from webob import Request, Response

from swift.common.middleware import cors

class FakeApp(object):
    def __call__(self, env, start_response):
        return Response('FAKE APP')(env, start_response)

class TestCORSMiddleware(unittest.TestCase):

    def setUp(self):
        self.fake_app = FakeApp()
        self.local_origin = 'http://foo.com'

    def test_non_cors_request(self):
        '''A non-CORS request should pass through to the next app'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'GET'}
        req = Request.blank('/', environ)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 200)
        self.assertEquals(resp.body, 'FAKE APP')

    def test_preflight_request_bad_origin(self):
        '''If a preflight request is made from an unauthorized Origin the client
        should see a generic response with no CORS headers'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'OPTIONS'}
        headers = {'Origin': 'http://baz.com'}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 403)
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
        self.assertNotIn('Access-Control-Allow-Methods', resp.headers)
        self.assertNotIn('Access-Control-Allow-Headers', resp.headers)

    def test_preflight_request_no_request_method(self):
        '''An OPTIONS request must have an 'Access-Control-Request-Method'
        header'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'OPTIONS'}
        headers = {'Origin': conf['allow_origins']}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 403)

    def test_preflight_request_invalid_request_method(self):
        '''The 'Access-Control-Request-Method' header should contain an allowed
        method'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'OPTIONS'}
        headers = {'Origin': conf['allow_origins'],
                   'Access-Control-Request-Method': 'PUT'}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 403)

    def test_preflight_request_invalid_request_header(self):
        '''The 'Access-Control-Request-Method' header should contain an allowed
        method'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'OPTIONS'}
        headers = {'Origin': conf['allow_origins'],
                   'Access-Control-Request-Method': 'GET',
                   'Access-Control-Request-Headers': 'X-Custom3'}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 403)

    def test_good_preflight_request(self):
        '''An OPTIONS request should return a number of Access-Control-Allow-*
        headers describing what origins, methods and custom headers a resource
        will serve'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'OPTIONS'}
        headers = {'Origin': conf['allow_origins'],
                   'Access-Control-Request-Method': conf['allow_methods']}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 200)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEquals(conf['allow_origins'],
            resp.headers['Access-Control-Allow-Origin'])
        self.assertIn('Access-Control-Allow-Methods', resp.headers)
        self.assertEquals(conf['allow_methods'].lower(),
            resp.headers['Access-Control-Allow-Methods'])
        self.assertIn('Access-Control-Allow-Headers', resp.headers)
        self.assertEquals(conf['allow_headers'].lower(),
            resp.headers['Access-Control-Allow-Headers'])

    def test_actual_request_bad_method(self):
        '''A request with an invalid method should return a 405'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'POST',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'GET'}
        headers = {'Origin': conf['allow_origins']}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 405)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEquals(conf['allow_origins'],
            resp.headers['Access-Control-Allow-Origin'])

    def test_good_request(self):
        conf = {'local_origin': self.local_origin,
                'allow_origins': 'http://bar.com',
                'allow_methods': 'GET,PUT',
                'allow_headers': 'X-Custom1,X-Custom2'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'GET'}
        headers = {'Origin': conf['allow_origins'],
                   'X-Custom1': 'test'}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 200)
        self.assertEquals(resp.body, 'FAKE APP')
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEquals(conf['allow_origins'],
            resp.headers['Access-Control-Allow-Origin'])
        self.assertIn('Access-Control-Expose-Headers', resp.headers)
        self.assertEquals(conf['allow_headers'].lower(),
            resp.headers['Access-Control-Expose-Headers'])

    def test_asterisk_origin(self):
        '''When allow_origins = "*" all origins should be accepted'''
        conf = {'local_origin': self.local_origin,
                'allow_origins': '*',
                'allow_methods': 'GET'}
        app = cors.filter_factory({}, **conf)(self.fake_app)
        environ = {'REQUEST_METHOD': 'GET'}
        headers = {'Origin': 'http://bar.com'}
        req = Request.blank('/', environ, headers = headers)
        resp = req.get_response(app)
        self.assertEquals(resp.status_int, 200)
        self.assertEquals(resp.body, 'FAKE APP')
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEquals('http://bar.com',
            resp.headers['Access-Control-Allow-Origin'])
        self.assertIn('Access-Control-Expose-Headers', resp.headers)
        self.assertEquals('',
            resp.headers['Access-Control-Expose-Headers'])

if __name__ == '__main__':
    unittest.main()
