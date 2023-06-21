from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = 'web'

ids = False
mysql = MySQL(app)
rooms = {}
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

@app.route("/", methods=['POST','GET'])
def Login():
    if request.method == "POST":
        name = request.form.get('username')
        passwo = request.form.get('password')
        cur = mysql.connection.cursor()
        cur.execute("select * from users where name = %s",(name,))
        Result = cur.fetchone()
        cur.close()
        print(Result)
        print(passwo)
        if passwo == Result[3]:
          global ids
          ids = True
          print("Access Granted")
          return redirect('/Home')
        else:
          print("Password Incorrect")
          return render_template('Login.html')
      
    else:
        return render_template("login.html")
    
@app.route("/Register", methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        name = request.form.get('Username')
        email = request.form.get("email")
        password = request.form.get("password")
        cur = mysql.connection.cursor()
        cur.execute("select name from users where name = %s",(name,))
        Result = cur.fetchone()
        cur.close()
        print(Result)
        if Result is None:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users(name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            mysql.connection.commit()
            cur.close()
            global ids
            ids = True
            print("Registered")
            return redirect('/Home')
        else:
            flash("Username is not available. Please choose a different username.", "warning")
            print("Username is not available")
            return render_template('register.html')
    else:
        return render_template("register.html")
  


@app.route("/Home", methods=["POST", "GET"])
def home():
    session.clear()
    if ids == True:
        if request.method == "POST":

                name = request.form.get("name")
                code = request.form.get("code")
                join = request.form.get("join", False)
                create = request.form.get("create", False)

                if not name:
                    return render_template("home.html", error="Please enter a name.", code=code, name=name)

                if join != False and not code:
                    return render_template("home.html", error="Please enter a room code.", code=code, name=name)

                room = code
                if create != False:
                    room = generate_unique_code(4)
                    rooms[room] = {"members": 0, "messages": []}
                elif code not in rooms:
                    return render_template("home.html", error="Room does not exist.", code=code, name=name)

                session["room"] = room
                session["name"] = name
                return redirect(url_for("room"))

        return render_template("home.html")
    else:
        return redirect("")

@app.route("/room")
def room():

    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

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
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        rooms[room] = {"members": 0, "messages": []} 

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
