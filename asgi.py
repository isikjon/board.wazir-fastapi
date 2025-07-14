import os
import sys

# Добавляем корневую директорию в PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000, reload=False) 