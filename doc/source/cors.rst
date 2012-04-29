=====================
CORS Support in Swift
=====================

The `CORS specification`_ defines a mechanisim to enable client-side cross-origin requests. Without CORS, code running in a browser served from one domain is unable to make requests to another domain. This is enforced by the `same origin policy`_.

Example page demonstrating authentication and retrieving a list of buckets, test-swift-cors.html_.

-------------
Configuration
-------------
Add the cors middleware to the front of your pipeline,

::

  pipeline = cors healthcheck cache tempauth proxy-server

Added the following section,

::

  [filter:cors]
  use = egg:swift#cors
  local_origin = http://192.168.1.132:8080
  allow_origins = *
  allow_methods = GET
  allow_headers = X-Storage-User, X-Storage-Pass, X-Auth-Token, Origin
  expose_headers = X-Auth-Token, X-Storage-Url

* **local_origin** is the full public facing URL for Swift.
* **allow_origins** is a comma-seperated list of domains allowed to access this service. The wildcard * allows requests from all domains.
* **allow_methods** is a comma-seperated list of HTTP methods the middleware will allow through from CORS clients
* **allow_headers** is a comma-seperated list of headers the middleware will allow through from CORS clients
* **expose_headers** is a comma-seperated list of headers the middleware will instruct browsers to expose to client applications (most likely Javascript)

-------------------
Sample Conversation
-------------------
This conversation describes what happens when a client application hosted on 'localhost' tries to authenticate to a Swift application running on '192.168.1.132'. The client application is a Javascript application running in a user's browser. 

1. The javascript hosted on 'localhost' issues a request to '192.168.1.132' to  authenticate. The browser sees this as a CORS request since the host the javascript came from is different to the one now being requested. It  a pre-flight request to '192.168.1.132' asking what methods and headers it will accept from CORS clients. This pre-flight request and subsequent response are transparent to the client.

::

  OPTIONS /auth/v1.0 HTTP/1.1
  Host: localhost
  Connection: keep-alive
  Access-Control-Request-Method: GET
  Origin: http://localhost
  User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19
  Access-Control-Request-Headers: x-storage-pass, origin, x-storage-user
  Accept: */*
  Referer: http://localhost/swift-gui/test-swift-cors.html
  Accept-Encoding: gzip,deflate,sdch
  Accept-Language: en-US,en;q=0.8
  Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3

2. If Swift is configured with the CORS middleware as described above it responds like this,

::

  HTTP/1.1 200 OK
  Access-Control-Allow-Origin: http://localhost
  Access-Control-Allow-Methods: get
  Access-Control-Allow-Headers: x-storage-user,x-storage-pass,x-auth-token,origin
  Access-Control-Max-Age: 1728000
  Content-Length: 0
  Date: Sun, 29 Apr 2012 16:18:29 GMT
  Connection: keep-alive

3. The browser validates it can send the required method and headers and proceeds with the original request,

::

  GET /auth/v1.0 HTTP/1.1
  Host: localhost
  Connection: keep-alive
  X-Storage-Pass: testing
  Origin: http://localhost
  X-Storage-User: test:tester
  User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19
  Accept: */*
  Referer: http://localhost/swift-gui/test-swift-cors.html
  Accept-Encoding: gzip,deflate,sdch
  Accept-Language: en-US,en;q=0.8
  Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3

4. Swift sends the reponse including a 'Access-Control-Expose-Headers' header instructing the browser to expose the quoted headers to the client Javascript,

::

  HTTP/1.1 200 OK
  X-Storage-Url: http://192.168.1.132:8080/v1/AUTH_test
  X-Storage-Token: AUTH_tka3ba9cb00a6940d7a6a2a716f463e8f2
  X-Auth-Token: AUTH_tka3ba9cb00a6940d7a6a2a716f463e8f2
  Access-Control-Allow-Origin: http://localhost
  Access-Control-Expose-Headers: x-auth-token,x-storage-url
  Content-Length: 0
  Date: Sun, 29 Apr 2012 16:18:29 GMT
  Connection: keep-alive

.. _CORS specification: http://www.w3.org/TR/cors/
.. _same origin policy: http://en.wikipedia.org/wiki/Same_origin_policy
.. _test-swift-cors.html: ./test-swift-cors.html
