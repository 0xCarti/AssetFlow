import sys
from app import create_app

app = create_app(sys.argv)

if __name__ == "__main__":
    app.run(debug=True)