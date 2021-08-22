import os
from base64 import b64encode

from flask import Flask

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

from models import User

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or b64encode(os.urandom(32)).decode()

from routes import *

if __name__ == "__main__":
    app.run()


@app.shell_context_processor
def make_shell_context() -> dict:
    from main import update_url
    from models import Player
    return {
        "User": User,
        "Group": Group,
        "Player": Player,
        "update_url": update_url,
    }
