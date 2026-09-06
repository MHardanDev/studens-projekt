import os

environment = os.getenv("DJANGO_ENV", "dev").strip().lower()

if environment == "production":
    from .production import *
elif environment == "test":
    from .test import *
else:
    from .dev import *
