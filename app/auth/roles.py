from flask_principal import RoleNeed, Permission

admin_permission = Permission(RoleNeed('admin'))
author_permission = Permission(RoleNeed('author'))