__all__ = ["expose",
           "doc",
           "JSONRPC",
           "JSONRPCError"]
"""

An implementation of JSONRPC over Datpalicity M2M

http://jsonrpc.org/spec.html

"""

import inspect
import json
import re
import hashlib


log = getLogger('dataplicity-srv.api')


def expose(section_name=None, method_name=None, alias=None):
    """Set the section for a method"""
    def deco(f):
        f._jsonrpc = True
        f._jsonrpc_argspec = inspect.getargspec(f)
        f._jsonrpc_section = section_name
        f._jsonrpc_method_name = method_name
        f._jsonrpc_section_name = "{}.{}".format(section_name, method_name) if section_name else method_name
        if alias is not None:
            f._jsonrpc_alias = alias
        return f
    return deco


def doc(name, doc, type=lambda value: value, type_display=None):
    """Document a parameter"""
    def deco(f):
        params = getattr(f, '_jsonrpc_paramdocs', {})
        params[name] = doc
        setattr(f, '_jsonrpc_paramdocs', params)
        param_types = getattr(f, '_jsonrpc_paramtypes', {})
        param_types[name] = type
        setattr(f, '_jsonrpc_paramtypes', param_types)
        return f
    return deco


class JSONRPCError(Exception):
    """Thrown to indicate a problem fulfilling the request"""
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __unicode__(self):
        return "%s (%s)" % (self.msg, self.code)

    def __repr__(self):
        return "JSONRPCError(%r, %r)" % (self.code, self.msg)


class UserMessage(dict):
    def __init__(self, msg, title=None):
        self['response_type'] = "user_message"
        self['msg'] = msg
        self['title'] = title or "Response from server"


class ErrorCode(object):
    """Enumeration of error codes"""

    parse_error = -32700
    invalid_request = -32600
    method_not_found = -32601
    invalid_params = -32602
    internal_error = -32603

    to_str = {-32700: "Parse error",
              -32600: "Invalid Request",
              -32601: "Method not found",
              -32602: "Invalid params",
              -32603: "Internal error"}


class NoDefault(object):
    def __str__(self):
        return "<required>"
    __repr__ = __str__

_no_default = NoDefault()


class _RPCMethod(object):
    def __init__(self, method, name=None, section=None):
        self.name = name or method.__name__
        self.section = section
        self.callable = method
        args, varargs, keywords, defaults = method._jsonrpc_argspec
        args = args[2:]  # Ignore self and request
        defaults = defaults or ()
        self.params = dict((arg, _no_default) for arg in args)

        for arg_name, default in zip(args[::-1], defaults[::-1]):
            self.params[arg_name] = default

        self.doc = method.__doc__
        self.param_docs = getattr(method, '_jsonrpc_paramdocs', {})
        self.param_types = getattr(method, '_jsonrpc_paramtypes', {})
        self.has_kwargs = keywords is not None

    def is_required(self, param):
        """Check if a parameter is required"""
        return self.params.get(param) is _no_default

    def __call__(self, request, **kwargs):
        return self.callable(request, **kwargs)


class Interface(object):
    """A collection of exposed methods, with an optional section_name.

    Add an Interface instances to JSONRPC classes to add modular functionality

    """

    def __init__(self, section_name=None):
        self.section_name = section_name or getattr(self, 'name', None)

    def _get_methods(self):
        for method_name in dir(self):
            if method_name.startswith('_'):
                continue
            method = getattr(self, method_name)
            if callable(method) and getattr(method, '_jsonrpc', False):
                yield self.section_name, method


class JSONRPC(object):
    """An object that exposes selected methods via JSON RPC"""

    def __init__(self, *interfaces):
        self._interfaces = {interface.section_name: interface
                            for interface in interfaces}
        # Gather all the exposed methods and build a few data-structures
        self.rpc_methods = {}
        for method_name in dir(self):
            if not method_name.startswith('_'):
                method = getattr(self, method_name)
                if isinstance(method, Interface):
                    for method_section, method in method._get_methods():
                        self._add_method(method, section_name=method_section)
                else:
                    self._add_method(method)

        for interface in interfaces:
            if isinstance(interface, Interface):
                for method_section, method in interface._get_methods():
                    self._add_method(method, section_name=method_section)

    def get_interface(self, name):
        return self._interfaces[name]

    def _add_method(self, method, section_name=None):
        if callable(method) and getattr(method, '_jsonrpc', False):
            expose_name = getattr(method, '_jsonrpc_method_name', method.__name__) or method.__name__
            section = getattr(method, '_jsonrpc_section', section_name) or section_name
            if section:
                expose_name = "{}.{}".format(section, expose_name)
            self.rpc_methods[expose_name] = _RPCMethod(method, expose_name, section=section)
            if hasattr(method, '_jsonrpc_alias'):
                self.rpc_methods[method._jsonrpc_alias] = _RPCMethod(method, method._jsonrpc_alias)

    def __call__(self, request, json_req):

        try:
            self.on_request_start(request)
        except Exception as e:
            log.exception('error in on_request_start')

        try:
            req = json.loads(json_req)
        except Exception as e:
            response = self._make_error(None,
                                        ErrorCode.parse_error,
                                        unicode(e))
        else:
            if isinstance(req, dict):
                response = self._method_call(request, req)
            elif isinstance(req, list):
                response = self._batch_call(request, req)
            else:
                response = self._make_error(None,
                                            ErrorCode.invalid_request,
                                            "request should be an object or list")

        if response == 'CACHED':
            return response

        try:
            response_json = json.dumps(response, indent=4)
        except Exception as e:
            log.exception("Unable to serialize response %r", e)
            response = self._make_error(req.get('id', None),
                                        ErrorCode.internal_error,
                                        "The server was unable to serialize the response")
            response_json = json.dumps(response, indent=4)

        # Hook for completed request
        try:
            self.on_request_complete(request, json_req, response_json)
        except:
            # Don't risk breaking anything
            log.exception('error in on_request_complete')

        return response_json

    def on_request_start(self, request):
        """Called prior to any methods"""
        # Implementation has a chance to look at the request before doing anything else

    def on_request_complete(self, request, request_json, response_json):
        """Called when the request has been processed"""

    def on_method_error(self, request, error):
        """Called when a method raises an error"""
        pass

    def _on_method_error(self, request, error):
        try:
            self.on_method_error(request, error)
        except:
            log.exception('error in on_method_error')

    _re_doc = re.compile(r'\`(.*?)\`')
    _re_pre = re.compile(r'\*\*\*(.*?)\*\*\*', re.DOTALL)


    @classmethod
    def _make_error(self, call_id, code, message, data=None, exception=None):
        """Construct an error response"""
        code_msg = ErrorCode.to_str.get(code)
        if not code_msg:
            message = message or u'Unknown error'
        else:
            message = "%s. %s" % (code_msg, message)

        if exception is not None:
            #import traceback
            #exc = traceback.format_exc(exception)
            import traceback
            from StringIO import StringIO
            tb = StringIO()
            traceback.print_exc(file=tb)
            exception = tb.getvalue()

            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import HtmlFormatter

            lexer = get_lexer_by_name("pytb", stripall=True)
            formatter = HtmlFormatter(linenos=False, cssclass="uigentb")
            exc = highlight(exception, lexer, formatter)

            if data is None:
                data = {}
            data['exception'] = exc

        error = dict(code=code, message=message)
        if data is not None:
            error['data'] = data
        response = dict(jsonrpc="2.0",
                        error=error,
                        id=call_id)
        return response

    def local_call(self, request, method_name, **params):
        """Allow calling of a JSON RPC method internally and not via POST request"""
        method = self.rpc_methods.get(method_name)
        return method(request, **params)

    def _batch_call(self, request, req_batch):
        """Call a jsonrpc batch"""
        response = []
        for req in req_batch:
            notification = 'id' not in req
            try:
                result = self._method_call(request, req)
            except JSONRPCError as e:
                result = self._make_error(req.get('id', None), e.code, e.msg)
            if not notification:
                response.append(result)
        return response

    def _method_call(self, request, req):
        """Dispatch a json remote procedure call to exposed method."""
        call_id = None
        method_name = None
        request_from = req.pop('_request_from', None)
        param_summary = None
        try:
            if req.get('jsonrpc', '') != '2.0':
                raise JSONRPCError(ErrorCode.invalid_request,
                                   "Not JSONRPC 2.0 ('jsonrpc' should be '2.0')")
            if 'method' not in req:
                raise JSONRPCError(ErrorCode.invalid_request,
                                   "'method' not specified in request JSON")
            method_name = req['method']
            call_id = req.get('id')

            if not isinstance(method_name, basestring):
                raise JSONRPCError(ErrorCode.invalid_request,
                                   "'method' should be a string")

            method = self.rpc_methods.get(method_name)

            if method is None:
                return self._make_error(call_id,
                                        ErrorCode.method_not_found,
                                        u"'%s' is not an exposed method" % method_name)

            req_params = req.get('params', {})

            if not isinstance(req_params, dict):
                return self._make_error(call_id,
                                        ErrorCode.invalid_request,
                                        "'params' must be an object")

            def get_password(p):
                if isinstance(p, basestring):
                    return '*' * len(p)

            if 0:
                param_summary = ', '.join('%s=%r' % (k, v if k != 'password' else get_password(v))
                                          for k, v in req_params.iteritems())
                if len(param_summary) > 1024:
                    param_summary = param_summary[:1024] + " [...]"

            params = method.params.copy()
            params.update(req_params)

            if not method.has_kwargs:
                for k in params:
                    if k not in method.params:
                        raise JSONRPCError(ErrorCode.invalid_params,
                                           u"'{}' is an unexpected parameter for this method".format(k))

            param_types = method.param_types

            if isinstance(params, dict):
                for k, v in params.items():
                    if k in param_types:
                        try:
                            params[k] = param_types[k](v)
                        except Exception as e:
                            raise JSONRPCError(ErrorCode.invalid_params,
                                               u"Error with param '%s': %s" % (k, e))

                missing = []
                for k, v in params.iteritems():
                    if v is _no_default:
                        missing.append(k)
                if missing:
                    if len(missing) == 1:
                        msg = "'{}' is a required parameter".format(missing[0])
                    else:
                        msg = "{} are required parameters".format(", ".join("'%s'" % k for k in missing))
                    raise JSONRPCError(ErrorCode.invalid_request, msg)


                log.debug("%s(%s)", method_name, param_summary)

                # Method call here
                # -------------------------------------------------------------------
                result = method(request, **params)
                # -------------------------------------------------------------------
            else:
                raise JSONRPCError(ErrorCode.invalid_request,
                                   u"'params' should be a list or object, not %r" % params)

            return_data = {"jsonrpc": "2.0",
                           "result": result,
                           "id": call_id}

            return return_data

        except JSONRPCError as e:
            # No need to log errors here
            # These exceptions are considered normal operations
            self._on_method_error(request, e)
            return self._make_error(call_id, e.code, e.msg)

        except Exception as e:
            # An unhandled exception
            # Probably indicates a bug in an exposed method
            # if settings.DEBUG:
            #     from traceback import print_exc
            #     print_exc(e)
            log.exception("JSONRPC error on method '%s' from %s, params %s",
                          method_name,
                          request_from or '<unknown>',
                          "({})".format(param_summary) if param_summary is not None else '<unknown>')

            # Catch unknown errors
            return self._make_error(call_id,
                                    ErrorCode.internal_error,
                                    "The server was unable to process your request.",
                                    exception=e)


class TestExpose(JSONRPC):

    @expose()
    @doc("a", "first number to add")
    def add(self, request, a, b=0):
        """Add two numbers together"""
        return a + b


if __name__ == "__main__":

    test_expose = TestExpose()

    test = """
{"jsonrpc": "2.0",
 "method": "add",
 "params": [2, 3],
 "id": 1}"""

    print test_expose(None, test)
    print test_expose._get_documentation()
