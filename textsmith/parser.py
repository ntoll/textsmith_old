"""
Functions for parsing user input. Calls into the game logic layer to make
stuff happen, once the instructions from the user have been parsed.

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
from textsmith import logic, database


async def parse(user_id, message):
    """
    Parse the incoming message from the referenced user.

    There are four special characters which, if they start the message, act as
    shortcuts for common activities:

    " - make it appear like the user is saying whatever follows in the message.
    ! - make it appear like the user is shouting the message.
    : - "emote" the message directly as "username " + message
    @ - make it appear like the user is saying something directly to another.

    Next the parser expects the first word of the message to be a verb. If this
    verb is one of several built-in commands, the remainder of the message is
    passed as a single string into the relevant function for that verb (as
    defined in this module).

    If the verb isn't built into the game engine, then the parser breaks the
    raw input apart into sections that follow the following patterns:

    VERB
    VERB DIRECT-OBJECT
    VERB DIRECT-OBJECT PREPOSITION INDIRECT-OBJECT

    Examples of these patterns are:

    look
    take sword
    give sword to andrew
    say "Hello there" to nicholas

    (Note, English articles ("a", "the" etc) shouldn't be used in commands.)

    Anything enclosed in double-quotes (") is treated as a single entity if
    in the direct-object or indirect-object position. The parser will try to
    match objects against available aliases available in the current room's
    context. The following reserved words are synonyms:

    "me" - the player.
    "here" - the current location.

    At this point the parser has identified the verb string, and the direct and
    indirect objects. It looks for a matching verb on the four following
    objects (in order or precedence):

    1. The player.
    2. The room the player is in (including where the verb is an exit name).
    3. The direct object (if an object in the database).
    4. The indirect object (if an object in the database).

    The game checks each object in turn and, if it finds an attribute that
    matches the verb it attempts to "execute" it.

    For now, the attribute's value will be returned.

    In later iterations (hopefully) there will be a simply scripting language
    an attributes may contain code to run. If these "executable" attributes
    are found them the associated code will be run with the following objects
    in scope:

    this - a reference to the object which matched the verb.
    player - a reference to the player who issued the command.
    room - a reference to the room in which the player is situated.
    direct_object - either the matching object or raw string for the direct
      object. This could be None.
    preposition - a string containing the preposition. This could be None.
    indirect_object - either the matching object or raw string for the indirect
      object. This could be None.

    The player, room, direct_object and indirect_object objects can all be
    passed to a special "emit" function along with a message to display to
    that object (if the object is a user, it'll be sent just to them, if the
    object is a room, the message will be sent to all players in that room).

    That's it!
    """
    user = database.OBJECTS[user_id]
    room = database.OBJECTS[user["_meta"]["location"]]
    if not message.strip():
        # Don't do anything with empty messages.
        return
    message = message.lstrip()
    if message.startswith('"'):
        # The user is saying something to everyone.
        return await say(user, room, message[1:])
    elif message.startswith("!"):
        # The user is shouting something to everyone.
        return await shout(user, room, message[1:])
    elif message.startswith(":"):
        # The user is emoting something to everyone.
        return await emote(user, room, message[1:])
    elif message.startswith("@"):
        # The user is saying something to a specific person.
        return await tell(user, room, message[1:])
    
    # Check for verbs built into the game.
    verb_split = message.split(" ", 1)
    verb = verb_split[0].lower()
    if verb in ["create", "make", "cr", "mk", ]:
        # Create a new object.
        return await create(user, room, verb_split[1:])
    elif verb == "build":
        # Build a new room.
    elif verb ["connect", "co", ]:
        # Connect the current room to another via an exit.
    elif verb in ["visibility", "viz", "vis", ]:
        # Set the visibility of an object.
    elif verb in ["remove", "delete", "destroy", "rm", "del", ]:
        # Destroy an object or delete an attribute on an object.
    elif verb in ["go", "move", "exit", "mv", ]:
        # Move to another place via an exit.
    elif verb == "teleport":
        # Teleport the user somewhere else.
    elif verb in ["clone", "copy", "cp", ]:
        # Clone an object.
    elif verb in ["take", "get", ]:
        # Take an object from the room into the user's inventory.
    elif verb == "give":
        # Give an object to another user.
    elif verb in ["drop", "leave", ]:
        # Drop an object from the user's inventory into the room.
    elif verb in ["look", "lk", "l", ]:
        # Look at either the current room or a specific object.
    elif verb in ["detail", "examine", "det", "dtl", ]:
        # Get a detailed summary of the specified object or current room.
    elif verb in ["addalias", "alias+", "ali+", ]:
        # Add an alias to the specified object.
    elif verb in ["rmalias", "alias-", "ali-", ]:
        # Remove an alias from the specified object.
    elif verb in ["set", "attr", ]:
        # Set an attribute on an object with associated value.
    elif verb in ["addallow", "allow+", "alw+", ]:
        # Add a user to the allow list for the current room.
    elif verb in ["rmallow", "allow-", "alw-", ]:
        # Remove a user from the allow list for the current room.
    elif verb in ["addexclude", "exclude+", "ex+"]:
        # Add a user to the exclude list for the current room.
    elif verb in ["rmexclude", "exclude-", "ex-"]:
        # Remove a user from the exclude list for the current room.

    # Work out the verb, direct_obj, preposition and indirect_obj.
    direct_obj = None
    preposition = None
    indirect_obj = None
    pos = 1
    word_len = len(verb_split)
    if word_len > 1:
        direct_obj = verb_split[pos]
        if direct_obj.startswith('"'):
            # Multi word entity.
            while pos < word_len:
                pos += 1
                direct_obj += " " + verb_split[pos]
                if direct_obj.endswith('"'):
                    direct_obj = direct_obj[1:-1]  # Remove quotes.
                    break
    if pos < word_len:
        pos += 1
        preposition = verb_split[pos]
    if pos < word_len:
        indirect_obj = verb_split[pos:]
        if indirect_obj.startswith('"') and indirect_obj.endswith('"'):
            indirect_obj = indirect_obj[1:-1]  # Remove quotes.
    # If the direct_obj or indirect_obj refer to an object name, replace
    # it with the referenced object.
    dobj_match = logic.get_object_from_room(direct_obj, room, user)
    if dobj_match:
        if len(match) == 1:
            direct_obj = dobj_match[0]
        else:
            # Tell user to disambiguate.
            matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                       for x in dobj_match]
            msg = ("Multiple matshes (via object name or alias). "
                   "Please disambiguate between: " + ', '.join(matches))
            return await logic.emit_to_user(user_id, msg)
    iobj_match = logic.get_object_from_room(indirect_obj, room, user)
    if iobj_match:
        if len(match) == 1:
            indirect_obj = iobj_match[0]
        else:
            # Tell user to disambiguate.
            matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                       for x in iobj_match]
            msg = ("Multiple matshes (via object name or alias). "
                   "Please disambiguate between: " + ', '.join(matches))
            return await logic.emit_to_user(user_id, msg)
    # Try to return a result by interrogating the user, room, direct and
    # indirect objects. Ensure the game doesn't inadvertently reveal the
    # contents of _meta.
    if verb != "_meta":
        if verb in user:
            return await logic.emit_to_user(user_id, user[verb])
        elif verb in room:
            return await logic.emit_to_user(user_id, room[verb])
        elif isinstance(direct_obj, dict) and verb in direct_obj:
            return await logic.emit_to_user(user_id, direct_obj[verb])
        elif isinstance(indirect_obj, dict) and verb in indirect_obj:
            return await logic.emit_to_user(user_id, indirect_obj[verb])
    # Getting here means the parser can't work out how to process the user's
    # input, so say something cheerful, helpful or, if defined as an attribute
    # of the room, whatever is in "huh". :-)
    if "huh" in room:
        return await logic.emit_to_user(user_id, room["huh"])
    else:
        return await logic.emit_to_user(user_id, "I don't understand that.")


async def handle_exception(exception, user):
    """
    Given an exception raised in the logic or parsing layer of the application,
    extract the useful message which explains what the problem is, and turn
    it into a message back to the referenced user.
    """
    await logic.emit_to_user(user["_meta"]["uuid"], str(exception))


async def say(user, room, message):
    """
    Say a message to the the whole room.
    """
    if message:
        user_message = f'> You say, "*{message}*".'
        username = user["_meta"]["name"]
        room_message = f'> {username} says, "*{message}*".'
        user_id = user["_meta"]["uuid"]
        room_id = room["_meta"]["uuid"]
        await logic.emit_to_user(user_id, user_message)
        await logic.emit_to_room(room_id, room_message, exclude=[user_id, ])


async def shout(user, room, message):
    """
    Say a message to the the whole room.
    """
    if message:
        user_message = f'> you shout , "**{message}**".'
        username = user["_meta"]["name"]
        room_message = f'> {username} shouts, "**{message}**".'
        user_id = user["_meta"]["uuid"]
        room_id = room["_meta"]["uuid"]
        await logic.emit_to_user(user_id, user_message)
        await logic.emit_to_room(room_id, room_message, exclude=[user_id, ])


async def shout(user, room, message):
    """
    Emote something to the the whole room.
    """
    if message:
        username = user["_meta"]["name"]
        emote = f'{username} {message}'
        user_id = user["_meta"]["uuid"]
        room_id = room["_meta"]["uuid"]
        await logic.emit_to_room(room_id, message)


async def tell(user, room, message):
    """
    Emote something to the the whole room.
    """
    if message:
        split = message.split(" ", 1)
        if len(split) == 2:
            recipient = split[0]
            message = split[1]
            user_message = f'> You say to {recipient}, "*{message}*".'
            username = user["_meta"]["name"]
            room_message = f'> {username} says to {recipient}, "*{message}*".'
            user_id = user["_meta"]["uuid"]
            room_id = room["_meta"]["uuid"]
            await logic.emit_to_user(user_id, user_message)
            await logic.emit_to_room(room_id, room_message,
                                     exclude=[user_id, ])


async def create(user, room, message):
    """
    Of the form:

    create newobjname A brief description of the object.
    """
    split_message = message.split(' ', 1)
    if len(split_message) == 2:
        name = split_message[0]
        description = split_message[1]
        logic.add_object(name, description, user)
        msg = f'Created object called "{name}". Check your inventory.'
        return await logic.emit_to_user(user["_meta"]["uuid"], msg)
    else:
        raise RuntimeError("Not enough arguments to create object.")
