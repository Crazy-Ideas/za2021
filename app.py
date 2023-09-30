import os
from typing import Optional

from flask import Flask
from flask_login import LoginManager

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"


from secret import SecretConfig

app = Flask(__name__)
CI_SECURITY: bool = True if os.environ.get("ENVIRONMENT") == "prod" else False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or SecretConfig.SECRET_KEY
app.config["SESSION_COOKIE_SECURE"] = CI_SECURITY
login = LoginManager(app)
login.login_view = "login"
login.session_protection = "strong" if CI_SECURITY else "basic"

from models import User

@login.user_loader
def load_user(email: str) -> Optional[User]:
    user: User = User.objects.filter_by(email=email).first()
    return user


# noinspection PyUnresolvedReferences
import routes
from s2022 import bp as world_cup_bp
from s2021 import bp as s2021_bp
from adventure import bp as adventure_bp
from super_cup import bp as super_cup_bp

app.register_blueprint(world_cup_bp)
app.register_blueprint(s2021_bp)
app.register_blueprint(adventure_bp)
app.register_blueprint(super_cup_bp)

if __name__ == "__main__":
    app.run()


@app.shell_context_processor
def make_shell_context() -> dict:
    import methods
    from s2022 import wc_methods
    from main import update_url, generate_url
    from models import Player, Group, Series, Standing, Match, FINAL_SERIES_TYPES
    from super_cup.models import CupSeries
    from adventure.models import Adventure
    import adventure.play as adventure_play
    import upload
    return {
        "User": User,
        "Group": Group,
        "Player": Player,
        "Series": Series,
        "Standing": Standing,
        "Match": Match,
        "update_url": update_url,
        "generate_url": generate_url,
        "methods": methods,
        "FINAL_SERIES_TYPES": FINAL_SERIES_TYPES,
        "game": upload,
        "wc_methods": wc_methods,
        "CupSeries": CupSeries,
        "Adventure": Adventure,
        "adventure_play": adventure_play,
    }
