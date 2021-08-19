import os

from flask import Flask

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

from models import User, Player

app = Flask(__name__)

from routes import *

if __name__ == "__main__":
    app.run()


@app.shell_context_processor
def make_shell_context() -> dict:
    from main import update_url
    return {
        "User": User,
        "Group": Group,
        "Player": Player,
        "update_url": update_url,
    }
