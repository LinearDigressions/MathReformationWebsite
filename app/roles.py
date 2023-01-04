from flask_principal import RoleNeed, Permission
from collections import namedtuple
from functools import partial

# Creating Role Permissions
admin_permission = Permission(RoleNeed('admin'))
author_permission = Permission(RoleNeed('author'), RoleNeed('admin'))


# Creating Article Permission
ArticleNeed = namedtuple('article', ['method', 'value'])
EditArticleNeed = partial(ArticleNeed, 'edit')

class EditArticlePermission(Permission):
    def __init__(self, article_id):
        need = EditArticleNeed(article_id)
        super(EditArticlePermission, self).__init__(need)
