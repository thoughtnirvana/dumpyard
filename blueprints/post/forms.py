import flask.ext.wtf as wtf
from wtforms.ext.sqlalchemy.orm import model_form
from flask.ext.wtf import Form, validators
import models


PostForm = model_form(models.Post, models.db.session, base_class=Form, field_args = {
    'name': {'validators': [validators.required()]},
    'title': {'validators': [validators.required(), validators.length(min=5)]},
    'content': {'validators': []},
    'tags': {'validators': []},
})

CommentForm = model_form(models.Comment, models.db.session, base_class=Form, field_args = {
    'commenter': {'validators': [validators.required()]},
    'body': {'validators': [validators.required()]},
})
