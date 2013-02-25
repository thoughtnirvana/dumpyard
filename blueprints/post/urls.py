import views

routes = [
    ('/', 'index', views.post_index),
    ('/<int:id>', 'show', views.post_show),

    ('/<int:post_id>/comments/new', 'comment_new', views.comment_new, {'methods': ['GET', 'POST']}),
    ('/<int:post_id>/comments/<int:id>/delete', 'comment_delete', views.comment_delete, {'methods': ['POST']}),

    ('/new', 'new', views.post_new, {'methods': ['GET', 'POST']}),
    ('/<int:id>/edit', 'edit', views.post_edit, {'methods': ['GET', 'POST']}),
    ('/<int:id>/delete', 'delete', views.post_delete, {'methods': ['POST']}),
]
