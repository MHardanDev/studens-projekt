from .base import *

DEBUG = False

if SECRET_KEY == "dev-only-change-me":
    msg = "DJANGO_SECRET_KEY must be set in production"
    raise RuntimeError(msg)
