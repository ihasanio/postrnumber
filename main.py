import os
import uvicorn
from custom_post_runner import app, state

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8083))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
