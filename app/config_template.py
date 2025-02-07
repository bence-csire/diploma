import os

SECRET_KEY = os.getenv('your_secret_key_here')
DATABASE_URI = os.getenv('sqlite:///android.db')