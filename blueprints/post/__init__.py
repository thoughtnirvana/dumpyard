from lib import utils
from config import settings

BEFORE_REQUESTS = [utils.http_dont_auth(settings.HTTP_USERNAME, settings.HTTP_PASSWORD,
                                        'post.index', 'post.show', 'post.comment_new')]
