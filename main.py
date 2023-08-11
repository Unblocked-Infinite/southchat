from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import random
from string import ascii_uppercase
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "SouthChatterBox"
socketio = SocketIO(app)

rooms = {}
active_sessions = {}

def pretty_print_to_log(data):
    log_folder = "logs"
    # os.makedirs(log_folder, exist_ok=True)

    # timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # log_filename = f"{timestamp}_log.json"
    # full_log_path = os.path.join(log_folder, log_filename)

    # with open(full_log_path, 'w') as log_file:
    #     json.dump(data, log_file, indent=4)

    # print(f"Logged data to {full_log_path}")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/rooms")
def rooms_page():
    return render_template("rooms.html", rooms=rooms)

@app.route("/join", methods=["POST", "GET"])
def join(): 
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        accepted_chars = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*_+=-"
        char_list = []
        for char in accepted_chars:
            char_list.append(char)
        for charecter in name:
            if charecter in char_list:
                pass
            else:
                flash("Please Dont Use Any Outside Characters!", category='error')
                return render_template("join.html", code=code, name="")

        if not name or '"' in name or "'" in name:
            flash("Please Enter A Valid Name!", category='error')
            return render_template("join.html", code=code, name=name)
        if " " in name:
            flash("Name Can Not Contain Spaces", category='error')
            return render_template("join.html", code=code, name="")
        if join != False and not code:
            flash("Please Enter A Room Code!", category='error')
            return render_template("join.html", code=code, name=name)
        if create != False:
            if len(code) < 4:
                flash("Code Needs To Be Longer Then 4!", category='error')
                return render_template("join.html", code="", name=name)
            elif code in rooms:
                flash("Code Already Exits!", category='error')
                return render_template("join.html", code="", name=name)
            elif '"' in code or "'" in code:
                flash("You Cant Have Quotes!", category='error')
                return render_template("join.html", code="", name=name)
            elif len(code) > 15:
                flash("Code Is Too Long!", category='error')
                return render_template("join.html", code="", name=name)
            elif " " in code:
                flash("Code Can Not Contain Spaces", category='error')
                return render_template("join.html", code="", name=name)
            else:
                room = code
                rooms[room] = {"members": 0, "messages": []}
                flash("Room Created", category='success')
        elif code not in rooms:
            flash("Room Code Does Not Exits!", category='error')
            return render_template("join.html", code="", name=name)
        elif len(code) < 4:
            flash("Room Code Is To Short!", category='error')
            return render_template("join.html", code="", name=name)

        if any(data.get("name") == name for data in active_sessions.values()):
            flash("The name is already in use!", category="error")
            return render_template("join.html", code=code, name="")
            
        # Add the session data to the active_sessions dictionary
        active_sessions[name] = {"name": name, "room": code}
        session["room"] = code
        session["name"] = name

        return redirect(url_for("room"))
            


    return render_template("join.html")

@app.route("/room")
def room():
    room = session.get('room')
    name = session.get('name')
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("join"))
    
    return render_template("room.html", code=room, name=name, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    data_to_log = rooms
    pretty_print_to_log(data_to_log)



@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "Joined Room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} Joined Room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    if name in active_sessions:
        del active_sessions[name]
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0 and len(rooms) > 20:
            del rooms[room]
            del active_sessions[request.sid]
    
    send({"name": name, "message": "Left Room"}, to=room)
    print(f"{name} has left the room {room}")



@app.route('/test')
def index():
    return render_template('index.html')

@socketio.on('iframe_content')
def receive_iframe_content(data):
    content = data['content']
    emit('load_iframe', {'content': content})


if __name__ == "__main__":
    socketio.run(app, debug=True)