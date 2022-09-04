import base64
import json
import re

import O365


def encode_content(content):
    """Convert img src to base64 content bytes."""
    data = base64.b64encode(content)  # encode to base64 (bytes)
    data = data.decode()  # convert bytes to string

    return data


def message_json(message: O365.Message):
    soup = O365.message.bs(message.unique_body, "html.parser")

    body = str(soup)

    # get the json data
    data = re.search(r"{.*\s.*}", body).group()
    data = json.loads(data)

    return data
