# vim: set fileencoding=utf-8 :
"""
Misc. utilities.
"""
import re, os, subprocess

import config

def set_trace():
    """
    Wrapper for ``pdb.set_trace``.
    """
    from config import app
    if not app.debug: return
    import pdb
    pdb.set_trace()


def auto_version(endpoint, **values):
    """
    Auto versions static assets.
    """
    from flask import current_app as app
    from flask import url_for
    if app.debug:
        return url_for(endpoint, **values)
    # Check if accessing static file.
    static_root = None
    if endpoint == 'static':
        static_root = app.static_folder
    if not static_root:
        m = re.match(r'(.+)\.static', endpoint)
        if m:
            try:
                static_root = app.blueprints[m.group(1)].static_folder
            except:
                pass
    # Get the timestamp of the file.
    if static_root:
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(static_root, filename)
            if os.path.splitext(file_path) in ['.css', '.coffee']:
                file_path = re.sub('(css|coffee)', {'css': 'less', 'coffee': 'js'}["\\1"], file_path)
            if os.path.isfile(file_path):
                values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

def simple_form(form_type, template, success):
    from flask import render_template
    def fn():
        form = form_type()
        if form.validate_on_submit():
            return success()
        return render_template(template, form=form)
    return fn

def _simple_processor(processor, ext_private, ext_public):
    from flask import request
    request_path = request.path
    if not request_path.endswith(ext_public):
        return
    public_file = request_path[len(config.app.static_url_path) + 1:]
    public_file_path = os.path.join(config.app.static_folder, public_file)
    private_file_path = public_file_path[:-len(ext_public)] + ext_private
    # File does not exist in app static - check blueprints.
    if not os.path.isfile(private_file_path):
        for blueprint_name, blueprint in config.app.blueprints.iteritems():
            if blueprint.static_url_path and request_path.startswith(blueprint.static_url_path):
                public_file = request_path[len(blueprint.static_url_path) + 1:]
                public_file_path = os.path.join(blueprint.static_folder, public_file)
                private_file_path = public_file_path[:-len(ext_public)] + ext_private
                break
    # If file doesn't exist in the blueprints as well, let flask handle it.
    if not os.path.isfile(private_file_path):
        return
    if not os.path.isfile(public_file_path) or (os.path.getmtime(private_file_path) >=
                                                os.path.getmtime(public_file_path)):
        processor(private_file_path, public_file_path)

def less_to_css():
    processor = lambda in_file, out_file: subprocess.check_output(['lessc',
                                                                   in_file, out_file], shell=False)
    return _simple_processor(processor, '.less', '.css')

def coffee_to_js():
    processor = lambda in_file, out_file: subprocess.check_output(['coffee',
                                                                   '-c', in_file], shell=False)
    return _simple_processor(processor, '.coffee', '.js')

def http_auth(username, password, include, *endpoints):
    from flask import request, Response
    def protected():
        if request and request.endpoint and not request.endpoint.startswith('_'):
            if include:
                predicate = request.endpoint in endpoints
            else:
                predicate = request.endpoint not in endpoints
            if predicate:
                auth = request.authorization
                if not auth or not (auth.username == username and auth.password == password):
                    return Response('Could not verify your access level for that URL.\n'
                                    'You have to login with proper credentials', 401,
                                    {'WWW-Authenticate': 'Basic realm="Login Required"'})
    return protected

def http_do_auth(username, password, *endpoints):
    return http_auth(username, password, True, *endpoints)

def http_dont_auth(username, password, *endpoints):
    return http_auth(username, password, False, *endpoints)

def row_to_dict(row):
    return dict((col, getattr(row, col)) for col in row.__table__.columns.keys())

def rows_to_dict(rows):
    return map(row_to_dict, rows)
