from google.cloud.storage import Client


class Config:
    IMG_EXT: tuple = ("jpg", "jpeg", "png")
    BUCKET = Client().bucket("za-2021")
