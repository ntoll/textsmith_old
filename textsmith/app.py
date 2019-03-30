"""
Contains the entry points and setup helpers needed to run the TextSmith
application on a server.


Copyright (C) 2019 Nicholas Tollervey and Andrew Smith.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import os
import asyncio
import time
from quart import (Quart, render_template, request, redirect, url_for, session,
                   websocket)
from textsmith import parser, logic, database
from functools import wraps


app = Quart(__name__)


try:
    secret_key = os.environ["textsmith_key"]
except Exception:
    secret_key = "CHANGETHIS"


app.config.update({
    "SECRET_KEY": secret_key,
    "DEBUG": True,
})


@app.route('/')
async def home():
    """
    Render the homepage.
    """
    return await render_template('home.html')


@app.route('/help')
async def help():
    """
    Render the help page.
    """
    return await render_template('help.html')


@app.route('/client', methods=["GET"])
async def client():
    """
    Render the client assets needed by the browser to connect to the
    websocket.
    """
    return await render_template('client.html')


async def sending():
    """
    Handle the sending of messages to a connected websocket.

    It simply reads messages off a message bus for the current user.
    """
    while True:
        if websocket.user:
            msg_bus = database.CONNECTIONS.get(websocket.user)
            if msg_bus:
                await websocket.send(msg_bus[0])
                database.CONNECTIONS[websocket.user] = msg_bus[1:]
            await asyncio.sleep(0.01)
        else:
            await asyncio.sleep(0.01)


async def receiving():
    """
    Parse incoming data. If the user is logged in pass the message into the
    game to process. Otherwise try to log them in or provide a helpful
    message if they're not doing anything sensible! :-)
    """
    while True:
        data = await websocket.receive()
        if websocket.user:
            # User is logged in, so evaluate their input.
            await parser.eval(websocket.user, data)
        elif data.startswith("login"):
            # The user has issued the login verb, so try logging them in.
            result = await login(data)
            if result:
                # Success, so snaffle away the user on the websocket object
                # for this connection.
                websocket.user = result
                await websocket.send("<p>Logged in... :-)</p>")
            else:
                # Didn't work, so send back something useful.
                await websocket.send("<p style='color:red;'>Incorrect "
                                     "login.</p>")
        else:
            # If we get here, the user hasn't entered anything useful, so
            # remind them of the only useful command they have at this point.
            await websocket.send("<p>Login with the command: "
                                 "<pre>login username password</pre></p>")


async def login(data):
    """
    Validate the user via the login command. Returns the logged in user or
    False (if login didn't work).
    """
    split = data.split()
    if len(split) == 3:
        username = split[1]
        password = split[2]
        user_id = database.USERS.get(username)
        if user_id:
            user = database.OBJECTS[user_id]
            user["_meta"]["last_login"] = time.time()
            if logic.verify_password(user["_meta"]["password"], password):
                if user["_meta"]["location"] is None:
                    await logic.nowhere(user_id)
                return user_id
    return False


@app.websocket('/ws')
async def ws():
    """
    Handle separate connections to the websocket endpoint.
    """
    # When logged in websocket.user points at the logged in user.
    websocket.user = None
    # The two tasks for sending and receiving data on this connection need
    # to be created and gathered.
    producer = asyncio.create_task(sending())
    consumer = asyncio.create_task(receiving())
    await asyncio.gather(producer, consumer)


@app.route('/signup', methods=['GET', 'POST'])
async def signup():
    """
    Renders and handles the signup page where new users sign up.

    If the content of the form is good create the user and then send them
    to the client page to actually login and connect to the game.
    """
    error = None
    if request.method == 'POST':
        form = await request.form
        username = form.get('username')
        password = form.get('password')
        confirm_password = form.get('confirm_password')
        description = form.get('description')
        if password != confirm_password:
            error = "The passwords don't match."
        elif username in database.USERS:
            error = "That username is already taken."
        elif not description.strip():
            error = "You need to provide a description of your character."
        else:
            logic.add_user(username, description, password, "no-email")
            return redirect(url_for('client'))
    return await render_template('signup.html', error=error)


DEFAULT_ROOM = """Welcome to our world!

This is a room in an interactive textual adventure.

There's not much to see here at the moment. Why not build something? If you're
the janitor, you could update this description to something more fun!
"""


async def first_run():
    """
    If no database is found. Create a new database with some required default
    objects (a janitor who is superuser, their password is read from an
    ENVAR, and a defeault room for users to start in).
    """
    password = "CHANGEME"
    try:
        password = os.environ["janitor_password"]
    except KeyError:
        # No envar, so print a warning.
        print("Janitor will use default password. THIS IS A BAD IDEA.")
    janitor_id = logic.add_user("janitor", "The janitor for this world.",
                                password, "")
    janitor = database.OBJECTS[janitor_id]
    janitor["_meta"]["superuser"] = True
    room_id = logic.add_room("WelcomeRoom", DEFAULT_ROOM, janitor)
    room = database.OBJECTS[room_id]
    room["_meta"]["default_room"] = True
    database.save_database()
    database.load_database()


async def backup():
    """
    Backs up the database every minute.
    """
    while True:
        await asyncio.sleep(60)
        database.save_database()


@app.before_serving
async def on_start():
    """
    Load the database and schedule the regular database backup task.
    """
    # Load the data into memory.
    try:
        database.load_database()
    except Exception as ex:
        await first_run()
    asyncio.create_task(backup())


@app.after_serving
async def on_stop():
    """
    Make sure the database is saved if the application stops.
    """
    database.save_database()


if __name__ == '__main__':
    app.run()
