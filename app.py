import os

from flask import Flask

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

from models import User, Group, Player

app = Flask(__name__)


@app.route("/")
def hello_world():  # put application"s code here
    return "Hello World!"


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
