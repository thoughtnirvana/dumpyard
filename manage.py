import os, signal, sys
import subprocess as sp
import werkzeug.serving
from werkzeug import import_string
from flask.ext.script import Manager
import main

app = main.app
manager = Manager(app)

from config import db

@manager.command
def run_tornado(port=5000):
    """
    Runs application under tornado.
    """
    import script.serve_app_tornado as runner
    signal.signal(signal.SIGINT, interrupt_handler)
    _runner(runner, port)

@manager.command
def run_gevent(port=5000):
    """
    Runs gevent server.
    """
    import gevent
    import script.serve_app_gevent as runner
    gevent.signal(signal.SIGINT, interrupt_handler)
    _runner(runner, port)

def _runner(runner, *args, **kwargs):
    environ = os.environ.get('FLASK_ENV')
    if not environ or environ != 'prod':
        # Run with reloading.
        @werkzeug.serving.run_with_reloader
        def run_server():
            runner.run_server(app, *args, **kwargs)
        run_server()
    else:
        runner.run_server(app, *args, **kwargs)

def interrupt_handler(*args, **kwargs):
    sys.exit(1)

@manager.command
def db_createall():
    "Creates database"
    db.create_all()

@manager.command
def db_create_models():
    "Creates database tables."
    # db_createall doesn't work if the models aren't imported
    import_string('models', silent=True)
    for blueprint_name, blueprint in app.blueprints.iteritems():
        import_string('%s.models' % blueprint.import_name, silent=True)
    db.create_all()

@manager.command
def db_dropall():
    "Drops all database tables"
    # db_dropall doesn't work if the models aren't imported
    import_string('models', silent=True)
    for blueprint_name, blueprint in app.blueprints.iteritems():
        import_string('%s.models' % blueprint.import_name, silent=True)
    db.drop_all()


@manager.command
def create_blueprint(name, scaffold=False, fields=''):
    """
    Creates app folder structure. Optionally, scaffolds the app with models, forms, views and templates.
    Eg.
        # Create blueprint with scaffold.
        python manage.py create_blueprint post -s -f 'name:String(80) title:String(200) content:Text

        # Create blueprint with scaffold.
        python manage.py create_blueprint post -f 'name:String(80) title:String(200) content:Text
    """
    print sp.check_output('mkdir -p blueprints/%(name)s/templates/%(name)s' % locals(), shell=True),
    for static_dir in ('css', 'js', 'img'):
        print sp.check_output('mkdir -p blueprints/%(name)s/static/%(static_dir)s' % locals(), shell=True),
    print sp.check_output("touch blueprints/%(name)s/__init__.py" % locals(), shell=True),
    if scaffold:
        create_scaffold('%(name)s/%(name)s' % dict(name=name), fields)

@manager.command
def test():
    """
    Runs unit tests.
    """
    print sp.check_output('nosetests -v', shell=True),

@manager.command
def deps_get():
    """
    Installs dependencies.
    """
    print sp.check_output("pip install -r requirements.txt", shell=True),

@manager.command
def deps_update():
    """
    Updates dependencies.
    """
    print sp.check_output("pip install -r requirements.txt --upgrade", shell=True),

@manager.command
def create_model(name, fields=''):
    """
    Creates model scaffold and the model form.
    Eg:
        # Create top level model.
        python manage.py create_model tag -f 'name:String(80) post_id:Integer'

        # Create model within a blueprint.
        python manage.py create_model post/tag -f 'name:String(80) post_id:Integer'
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/models.py' % blueprint_name
    else:
        model_name = name
        output_file = 'models.py'
    model = create_model.model_scaffold % dict(model_name=model_name.capitalize())

    field_declares = []
    field_inits = []
    init_args = []
    for f in fields.split():
        splitted = f.split(':')
        if len(splitted) > 1:
            field_name, field_type = splitted[0], 'db.%s' % splitted[1]
        else:
            field_name, field_type = splitted[0], 'db.Text'
        field_declares.append(create_model.field_declare % dict(field_name=field_name, field_type=field_type))
        field_inits.append(create_model.field_init % dict(field_name=field_name))
        init_args.append(field_name)

    field_declares = '\n'.join(field_declares)

    init_args = (', %s' % ', '.join(init_args)) if init_args else ''
    init_body = '\n'.join(field_inits) if field_inits else '%spass' % (' ' * 8)
    init_method = '    def __init__(self%s):\n%s' % (init_args, init_body)

    file_exists = os.path.exists(output_file)
    with open(output_file, 'a') as out_file:
        model = '%(base)s%(field_declares)s\n\n%(init_method)s' % dict(base=model,
                                                                       field_declares=field_declares,
                                                                       init_method=init_method)
        if not file_exists:
            model = '%(imports)s\n%(rest)s' % dict(imports=create_model.imports,
                                                rest=model)
        out_file.write(model)
    create_model_form(name, fields)

create_model.model_scaffold = '''

class %(model_name)s(db.Model):
    id = db.Column(db.Integer, primary_key=True)
'''
create_model.imports = 'from config import db'
create_model.field_declare = '%s%%(field_name)s = db.Column(%%(field_type)s)' % (' ' * 4)
create_model.field_init = '%sself.%%(field_name)s = %%(field_name)s' % (' ' * 8)
create_model.init_method = '''
    def __init__(self%(args)s):
        %(body)s
'''


@manager.command
def create_routes(name):
    """
    Creates routes scaffold.
    Eg.
        # Top level routes.
        python manage.py create_routes post

        # Blueprint routes.
        python manage.py create_routes post/tag
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/urls.py' % blueprint_name
    else:
        model_name = name
        output_file = 'urls.py'
    file_exists = os.path.exists(output_file)
    routes = create_routes.routes_scaffold % dict(model_name=model_name.lower())
    if file_exists:
        routes = create_routes.append_routes % dict(routes=routes)
    else:
        routes = create_routes.new_routes % dict(routes=routes)
    with open(output_file, 'a') as out_file:
        if not file_exists:
            routes = '''%(imports)s\n%(rest)s''' % dict(imports=create_routes.imports,
                                                rest=routes)
        out_file.write(routes)

create_routes.imports = 'import views'
create_routes.routes_scaffold = '''('/', 'index', views.%(model_name)s_index),
    ('/<int:id>', 'show', views.%(model_name)s_show),
    ('/new', 'new', views.%(model_name)s_new, {'methods': ['GET', 'POST']}),
    ('/<int:id>/edit', 'edit', views.%(model_name)s_edit, {'methods': ['GET', 'POST']}),
    ('/<int:id>/delete', 'delete', views.%(model_name)s_delete, {'methods': ['POST']}),'''
create_routes.new_routes = '''
routes = [
    %(routes)s
]
'''
create_routes.append_routes = '''
routes += [
    %(routes)s
]
'''

@manager.command
def create_model_form(name, fields=''):
    """
    Creates model form scaffold.
    Eg:
        python manage.py create_model tag -f 'name:String(80) post_id:Integer'
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/forms.py' % blueprint_name
    else:
        model_name = name
        output_file = 'forms.py'
    file_exists = os.path.exists(output_file)
    field_args = []
    for f in fields.split():
        field_name = f.split(':')[0]
        field_args.append(create_model_form.field_args % dict(field_name=field_name))
    form = create_model_form.form_scaffold % dict(model_name=model_name.capitalize(), field_args=''.join(field_args))
    with open(output_file, 'a') as out_file:
        if not file_exists:
            form = '''%(imports)s\n%(rest)s''' % dict(imports=create_model_form.imports,
                                                      rest=form)
        out_file.write(form)

create_model_form.imports = '''import flask.ext.wtf as wtf
from flask.ext.wtf import Form, validators
from wtforms.ext.sqlalchemy.orm import model_form
import models
'''
create_model_form.form_scaffold = '''
%(model_name)sForm = model_form(models.%(model_name)s, model.db.session, Form, field_args = {%(field_args)s
})
'''
create_model_form.field_args = '''
    '%(field_name)s': {'validators': []},'''


@manager.command
def create_view(name, fields=''):
    """
    Creates view scaffold. It also creates the templates.
    Eg.
        # Top level views.
        python manage.py create_view comment -f 'commenter body post_id'

        # Blueprint views.
        python manage.py create_view post/comment -f 'commenter body post_id'
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/views.py' % blueprint_name
    else:
        model_name = name
        output_file = 'views.py'
    file_exists = os.path.exists(output_file)
    form_data = []
    for f in fields.split():
        form_data.append('form.%s.data' % f.split(':')[0])
    views = create_view.views_scaffold % dict(name=model_name.lower(),
                                               model_name=model_name.capitalize(),
                                               form_data=', '.join(form_data))
    with open(output_file, 'a') as out_file:
        if not file_exists:
            views = '''%(imports)s\n%(rest)s''' % dict(imports=create_view.imports,
                                                       rest=views)
        out_file.write(views)
    create_templates(name, fields)

create_view.imports = '''from flask import render_template, redirect, url_for, flash, request
from config import db
import models
import forms
'''
create_view.views_scaffold = '''
def %(name)s_index():
    object_list = models.%(model_name)s.query.all()
    return render_template('%(name)s/index.slim', object_list=object_list)

def %(name)s_show(id):
    %(name)s = models.%(model_name)s.query.get(id)
    return render_template('%(name)s/show.slim', %(name)s=%(name)s)

def %(name)s_new():
    form = forms.%(model_name)sForm()
    if form.validate_on_submit():
        %(name)s = models.%(model_name)s(%(form_data)s)
        db.session.add(%(name)s)
        db.session.commit()
        return redirect(url_for('%(name)s.index'))
    return render_template('%(name)s/new.slim', form=form)

def %(name)s_edit(id):
    %(name)s = models.%(model_name)s.query.get(id)
    form = forms.%(model_name)sForm(request.form, %(name)s)
    if form.validate_on_submit():
        form.populate_obj(%(name)s)
        db.session.add(%(name)s)
        db.session.commit()
        return redirect(url_for('%(name)s.show', id=id))
    return render_template('%(name)s/edit.slim', form=form, %(name)s=%(name)s)

def %(name)s_delete(id):
    %(name)s = models.%(model_name)s.query.get(id)
    db.session.delete(%(name)s)
    db.session.commit()
    return redirect(url_for('%(name)s.index'))
'''

@manager.command
def create_templates(name, fields=''):
    """
    Creates templates.
    Eg.
        # Top level templates.
        python manage.py create_templates comment -f 'commenter body post_id'

        # Blueprint templates.
        python manage.py create_templates post/comment -f 'commenter body post_id'
    """
    if '/' in name:
        blueprint_name, name = name.split('/')
        name = name.lower()
        output_dir = 'blueprints/%s/templates/%s' % (blueprint_name, name)
    else:
        name = name.lower()
        output_dir = 'templates/%s' % name
    sp.check_call('mkdir -p %s' % output_dir, shell=True),
    fields = [f.split(':')[0] for f in fields.split()]
    # Create form template.
    with open('%s/_%s_form.slim' % (output_dir, name), 'a') as out_file:
        form_fields = []
        for f in fields:
            form_fields.append(create_templates.form_field % dict(field_name=f))
        form = create_templates.form_scaffold % dict(name=name, fields=''.join(form_fields))
        out_file.write(form)
    # Create index template.
    with open('%s/index.slim' % output_dir, 'a') as out_file:
        index_fields = []
        field_headers = []
        for f in fields:
            index_fields.append(create_templates.index_field % dict(name=name, field_name=f))
            field_headers.append(create_templates.index_field_header % dict(field_header=f.capitalize()))
        index = create_templates.index_scaffold % dict(name=name,
                                                        fields=''.join(index_fields),
                                                        field_headers=''.join(field_headers))
        out_file.write(index)
    # Create show template.
    with open('%s/show.slim' % output_dir, 'a') as out_file:
        show_fields = []
        for f in fields:
            show_fields.append(create_templates.show_field % dict(name=name, field_header=f.capitalize(),
                                                                  field_name=f))
        show = create_templates.show_scaffold % dict(name=name,
                                                     fields=''.join(show_fields))
        out_file.write(show)
    # Create edit and new templates.
    for template_name in ('edit', 'new'):
        with open('%s/%s.slim' % (output_dir, template_name), 'a') as out_file:
            out_file.write(getattr(create_templates, '%s_scaffold' % template_name) % dict(name=name))

create_templates.form_scaffold = '''- from 'helpers.slim' import render_field

form method="POST"
  = form.hidden_tag()%(fields)s
  .field
    input type="submit"
'''
create_templates.form_field = '''
  = render_field(form.%(field_name)s)'''
create_templates.index_scaffold = '''- extends 'layout.slim'
- from 'helpers.slim' import delete_button

- block content
  table
    thead
      tr%(field_headers)s
        %%th
        %%th
        %%th
    tbody
      - for %(name)s in object_list
        tr%(fields)s
          td
            a href="{{ url_for('.show', id\=%(name)s.id) }}" Show
          td
            a href="{{ url_for('.edit', id\=%(name)s.id) }}" Edit
          td
            = delete_button(url_for('.delete', id\=%(name)s.id), 'Delete')

  a href="=url_for('.new')" New %(name)s
'''
create_templates.index_field = '''
          td = %(name)s.%(field_name)s'''
create_templates.index_field_header = '''
        th %(field_header)s'''
create_templates.show_scaffold = '''- extends 'layout.slim'
- from 'helpers.slim' import flashed

- block content
  = flashed()%(fields)s
  a href="{{ url_for('.edit', id\=%(name)s.id) }}" Edit
  a href="{{ url_for('.index') }}" Back
'''
create_templates.show_field = '''
  p
    strong %(field_header)s:
  p = %(name)s.%(field_name)s
'''
create_templates.edit_scaffold = '''- extends 'layout.slim'

- block content
    h2 Editing %(name)s
    - include '%(name)s/_%(name)s_form.slim'
    a href="{{ url_for('.show', id\=%(name)s.id) }}" Show
    a href="{{ url_for('.index') }}" Back
'''
create_templates.new_scaffold = '''- extends 'layout.slim'

- block content
    h2 Creating new %(name)s
    - include '%(name)s/_%(name)s_form.slim'
    a href="=url_for('.index')" Back
'''

@manager.command
def create_scaffold(name, fields=''):
    """
    Creates scaffold - model, model form, views, templates and routes.
    """
    create_model(name, fields)
    create_view(name, fields)
    create_routes(name)


if __name__ == '__main__':
    manager.run()
