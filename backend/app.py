"""BlitzFeed API entrypoint.

Development:  python app.py
Production:   gunicorn -c gunicorn.conf.py app:app
"""

import os

from blitzfeed import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8080")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
