import os
from application import app

app.config["PROPAGATE_EXCEPTIONS"] = True

# Only enable debug mode locally
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "False").lower() == "true"

from flask_cors import CORS
CORS(app)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)