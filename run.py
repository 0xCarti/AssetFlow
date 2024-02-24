import sys
from flask_socketio import SocketIO
from app import create_app

app = create_app(sys.argv)
socketio = SocketIO(app)
app.socketio = socketio

if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True)