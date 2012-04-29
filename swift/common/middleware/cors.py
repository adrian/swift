# Copyright (c) 2012 Dell Inc.
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

from swift.common.utils import get_logger
from webob import Request, Response
from webob.exc import HTTPForbidden, HTTPMethodNotAllowed


class CORSMiddleware(object):
    """
    CORS middleware used to support clients not originating on this domain.

    Configuration:

        local_origin
            The public facing URI of this application's host.

        allow_origins
            A comma separated list of origins authorized to make CORS requests
            to this application. The wildcard "*" means accept requests from
            any origin.

        allow_methods
            A comma-separated list of HTTP methods the app is authorized to
            accept.

        allow_headers
            A comma-separated list of headers accepted by this application.

        expose_headers
            A comma-separated list of headers to instruct the browser to expose
            to applications.

    Cross-Origin Resource Sharing
    http://www.w3.org/TR/cors/
    """

    def __init__(self, app, conf):
        self.app = app
        self.logger = get_logger(conf, log_route='cors')

        self.local_origin = conf.get('local_origin')
        if self.local_origin == None:
            raise Exception("local_origin is a required parameter")
        else:
            self.local_origin = self.local_origin.lower()

        self.allow_origins = filter(None, [origin.strip().lower()
            for origin in conf.get('allow_origins', '').split(',')])

        self.allow_methods = filter(None, [method.strip().lower()
            for method in conf.get('allow_methods', '').split(',')])

        self.allow_headers = filter(None, [header.strip().lower()
            for header in conf.get('allow_headers', '').split(',')])

        self.expose_headers = filter(None, [header.strip().lower()
            for header in conf.get('expose_headers', '').split(',')])

    def __call__(self, env, start_response):
        req = Request(env)

        self.logger.debug("Handling request: %s", req)

        # Pass non-CORS requests on to the next app
        if not self.cors_request(req):
            self.logger.debug("Handling non-CORS request")
            return self.app(env, start_response)

        self.logger.debug("Handling CORS request")

        # Block requests from unauthorized Origins
        if not '*' in self.allow_origins \
                and not req.headers['Origin'].lower() in self.allow_origins:
            self.logger.debug("Origin not authorized: %s", req.headers['Origin'])
            resp = HTTPForbidden()
            return resp(env, start_response)

        self.logger.debug("Origin is authorized")

        # Block requests with unauthorized methods
        # We always accept 'OPTIONS' since it's required for preflight requests
        req_method = req.method.lower()
        if not req_method in self.allow_methods and req_method != 'options':
            self.logger.debug("Method not authorized: %s", req_method)
            resp = HTTPMethodNotAllowed(headers = 
                {'Access-Control-Allow-Origin': req.headers['Origin']})
            return resp(env, start_response)

        self.logger.debug("Method is authorized")

        # Handle either a preflight request or a simple/actual request
        if req_method == 'options':
            self.logger.debug("Handling a CORS preflight request")
            resp = self.handle_preflight_request(req)
            return resp(env, start_response)
        else:
            self.logger.debug("Handling an actual CORS request")
            return self.handle_actual_request(req, start_response)

    def handle_preflight_request(self, req):
        """"A preflight request is sent by the client to find out if a given 
        method and set of custom headers is allowed"""
        if 'Access-Control-Request-Method' not in req.headers:
            self.logger.debug("No Access-Control-Request-Method header")
            return HTTPForbidden()

        self.logger.debug("Access-Control-Request-Method header present")

        if req.headers['Access-Control-Request-Method'].lower() \
                not in self.allow_methods:
            self.logger.debug("Method in Access-Control-Request-Method not authorized: %s",
                req.headers['Access-Control-Request-Method'])
            return HTTPForbidden()

        self.logger.debug("Method specified in Access-Control-Request-Method is authorized")

        if 'Access-Control-Request-Headers' in req.headers:
            requested_headers = [header.strip().lower() for header in 
                req.headers['Access-Control-Request-Headers'].split(',')]
            for requested_header in requested_headers:
                if requested_header not in self.allow_headers:
                    self.logger.debug("Header not authorized: %s",
                        requested_header)
                    return HTTPForbidden()

        return Response(headers = {
            'Access-Control-Allow-Origin': req.headers['Origin'],
            'Access-Control-Allow-Methods': ','.join(self.allow_methods),
            'Access-Control-Allow-Headers': ','.join(self.allow_headers),
            'Access-Control-Max-Age': 1728000
        })

    def handle_actual_request(self, req, start_response):
        """Append CORS headers to the response and call through to the app"""
        def _start_response(status, headers):
            headers.append(('Access-Control-Allow-Origin', req.headers['Origin']))
            headers.append(('Access-Control-Expose-Headers', 
                ','.join(self.expose_headers)))
            return start_response(status, headers)

        return self.app(req.environ, _start_response)
        
    def cors_request(self, req):
        """A request is said to be a CORS request if it has an Origin header and
        that origin is different to the local origin"""
        if 'Origin' in req.headers:
            return req.headers['Origin'].lower() != self.local_origin
        return False

def filter_factory(global_conf, **local_conf):
    """Return a WSGI filter for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def cors_filter(app):
        return CORSMiddleware(app, conf)

    return cors_filter
