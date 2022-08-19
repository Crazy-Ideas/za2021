import os
from typing import Optional

from flask import Flask
from flask_login import LoginManager

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

from models import User
from secret import SecretConfig

app = Flask(__name__)
CI_SECURITY: bool = True if os.environ.get("ENVIRONMENT") == "prod" else False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or SecretConfig.SECRET_KEY
app.config["SESSION_COOKIE_SECURE"] = CI_SECURITY
login = LoginManager(app)
login.login_view = "login"
login.session_protection = "strong" if CI_SECURITY else "basic"


@login.user_loader
def load_user(email: str) -> Optional[User]:
    user: User = User.objects.filter_by(email=email).first()
    return user


from routes import *

if __name__ == "__main__":
    app.run()


@app.shell_context_processor
def make_shell_context() -> dict:
    import methods
    from main import update_url
    from models import Player, Group, Series, Standing, Match, FINAL_SERIES_TYPES
    import upload
    return {
        "User": User,
        "Group": Group,
        "Player": Player,
        "Series": Series,
        "Standing": Standing,
        "Match": Match,
        "update_url": update_url,
        "methods": methods,
        "FINAL_SERIES_TYPES": FINAL_SERIES_TYPES,
        "game": upload,
    }
