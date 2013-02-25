#!/usr/bin/env python
from migrate.versioning.shell import main
from config import settings

if __name__ == '__main__':
    main(url=settings.SQLALCHEMY_DATABASE_URI, debug=settings.DEBUG, repository='migrations')
