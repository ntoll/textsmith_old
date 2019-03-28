"""
Tests for the stateless parsing which takes raw user input and appropriately
calls into the logic layer to change game state.
"""
import time
import pytest
import asynctest
from quart import Quart
from textsmith import logic
from textsmith import database
from textsmith import parser


app = Quart(__name__)


@pytest.fixture
def game_world():
    """
    Return a tuple containing game assets we can use for test purposes.
    """
    database.OBJECTS = {}
    database.USERS = {}
    database.CONNECTIONS = {}
    # Make a user.
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    # Make an object.
    obj_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[obj_uuid]
    # Make a room.
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    # The user is in the room.
    user["_meta"]["location"] = room_uuid
    # The object is in the room.
    logic.drop(obj_uuid, user)
    # Create another room.
    other_room_uuid = logic.add_room("otherroomname", "room description", user)
    other_room = database.OBJECTS[other_room_uuid]
    # Create an exit between the current room and the other room.
    exit_uuid = logic.add_exit("exitname", "exit description", user, room,
                               other_room)
    exit = database.OBJECTS[exit_uuid]
    # Provide the new user, object, room and exit for each test function.
    return (user, obj, room, exit)


@pytest.mark.asyncio
async def test_eval_handles_exceptions(game_world):
    """
    If the eval function encounters an exception, ensure it's handled with the
    expected recovery function.
    """
    user, obj, room, exit = game_world
    message = "test"
    ex = Exception("BOOM!")
    with asynctest.patch("textsmith.parser.handle_exception") as mock_ex, \
            asynctest.patch("textsmith.parser.parse", side_effect=ex):
        await parser.eval(user["_meta"]["uuid"], message)
        mock_ex.assert_called_once_with(ex, user["_meta"]["uuid"])


@pytest.mark.asyncio
async def test_handle_exception(game_world):
    """
    The handle_exception function emits a string version of the referenced
    exception to the referenced user.
    """
    user, obj, room, exit = game_world
    ex = Exception("BOOM!")
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        await parser.handle_exception(ex, user["_meta"]["uuid"])
        mock_etu.assert_called_once_with(user["_meta"]["uuid"], str(ex))


@pytest.mark.asyncio
async def test_parse_whitespace_message(game_world):
    """
    If a message only contains whitespace, it's ignored.
    """
    user, obj, room, exit = game_world
    message = "         "
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        await parser.parse(user["_meta"]["uuid"], message)
        assert mock_etu.call_count == 0


@pytest.mark.asyncio
async def test_parse_command_with_leading_whitespace(game_world):
    """
    Leading whitespace, before the actual user's command, is stripped before
    the rest of parsing occurs.
    """
    user, obj, room, exit = game_world
    message = '     "Hello, world!'
    with asynctest.patch("textsmith.parser.say") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "Hello, world!")


@pytest.mark.asyncio
async def test_parse_say(game_world):
    """
    Messages starting with a double quote are interpreted as speech. E.g.

    "Hello world!

    Should result in the player appearing to say "Hello world!" to the other
    users in their current location.
    """
    user, obj, room, exit = game_world
    message = '"Hello, world!'
    with asynctest.patch("textsmith.parser.say") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "Hello, world!")


@pytest.mark.asyncio
async def test_parse_shout(game_world):
    """
    Messages starting with an exclamation mark are interpreted as shouting.
    E.g.

    !Oi oi

    Should result in the player appearing to shout, "Oi oi" to the other users
    in their current location.
    """
    user, obj, room, exit = game_world
    message = '!Oi oi'
    with asynctest.patch("textsmith.parser.shout") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "Oi oi")


@pytest.mark.asyncio
async def test_parse_emote(game_world):
    """
    Message starting with a colon are interpreted as emoting. E.g.

    :smiles

    Should result in the player appearing to smile at the other users in their
    current location.
    """
    user, obj, room, exit = game_world
    message = ':smiles'
    with asynctest.patch("textsmith.parser.emote") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "smiles")


@pytest.mark.asyncio
async def test_parse_tell_user(game_world):
    """
    Messages starting with an ampersand are interpreted as saying something to
    the referenced user. E.g.

    @ntoll Hello

    Should result in the player appearing to say "Hello" to the user ntoll
    """
    user, obj, room, exit = game_world
    message = '@ntoll Hello'
    with asynctest.patch("textsmith.parser.tell") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "ntoll Hello")


@pytest.mark.asyncio
async def test_parse_calls_builtin(game_world):
    """
    If the user enters a command that starts with a builtin verb, then the
    associated function for that verb is called with the expected arguments.
    """
    user, obj, room, exit = game_world
    # Pretend to create a foobar object.
    message = 'create foobar Description.'
    with asynctest.patch("textsmith.parser.create") as mock_fn:
        key = ("create", "make", "cr", "mk")
        old_create = parser.BUILTINS[key]
        parser.BUILTINS[key] = mock_fn
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "foobar Description.")
        parser.BUILTINS[key] = old_create


@pytest.mark.asyncio
async def test_parse_calls_get_objects(game_world):
    """
    If the verb isn't found in BUILTINS then call the get_objects function to
    get the direct and indirect objects from the remaining argument string.
    """
    user, obj, room, exit = game_world
    message = "wibble ntoll with bongo"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result) as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user, room, "ntoll with bongo")


@pytest.mark.asyncio
async def test_parse_calls_verb_on_user(game_world):
    """
    If the verb is found on the user, then emit the value associated with it.
    """
    user, obj, room, exit = game_world
    user["wibble"] = "user wibbled"
    message = "wibble ntoll with bongo"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.emit_to_user") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"], "user wibbled")


@pytest.mark.asyncio
async def test_parse_calls_verb_on_room(game_world):
    """
    If the verb is found on the room if not found on the user, then emit the
    value associated with it.
    """
    user, obj, room, exit = game_world
    room["wibble"] = "room wibbled"
    message = "wibble ntoll with bongo"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.emit_to_user") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"], "room wibbled")


@pytest.mark.asyncio
async def test_parse_calls_verb_on_direct_object(game_world):
    """
    If the verb is found on the direct object if not found on the user or room,
    then emit the value associated with it.
    """
    user, obj, room, exit = game_world
    obj["wibble"] = "obj wibbled"
    message = "wibble ntoll with bongo"
    result = (obj, "with", None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.emit_to_user") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"], "obj wibbled")


@pytest.mark.asyncio
async def test_parse_calls_verb_on_indirect_object(game_world):
    """
    If the verb is found on the indirect object if not found on the user, room,
    or direct object then emit the value associated with it.
    """
    user, obj, room, exit = game_world
    exit["wibble"] = "exit wibbled"
    message = "wibble ntoll with bongo"
    result = (obj, "with", exit)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.emit_to_user") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"], "exit wibbled")


@pytest.mark.asyncio
async def test_parse_calls_move_when_verb_matches_exit_name(game_world):
    """
    If the verb is found as the name of an exit leading OUT of the current
    location then move the user to the new location via that exit.
    """
    user, obj, room, exit = game_world
    message = "exitname"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.move") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"],
                                        exit["_meta"]["uuid"],
                                        user["_meta"]["uuid"])


@pytest.mark.asyncio
async def test_parse_calls_move_when_verb_matches_exit_alias(game_world):
    """
    If the verb is found as an alias of an exit leading OUT of the current
    location then move the user to the new location via that exit.
    """
    user, obj, room, exit = game_world
    exit["_meta"]["alias"].append("south")
    message = "south"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.move") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"],
                                        exit["_meta"]["uuid"],
                                        user["_meta"]["uuid"])


@pytest.mark.asyncio
async def test_parse_emits_room_huh(game_world):
    """
    If the parser doesn't understand the verb, but the current room has a
    "huh" attribute, then emit that to the user.
    """
    user, obj, room, exit = game_world
    room["huh"] = "What?"
    message = "wibble ntoll with bongo"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.emit_to_user") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        mock_fn.assert_called_once_with(user["_meta"]["uuid"], "What?")


@pytest.mark.asyncio
async def test_parse_emits_sarcastic_response_when_all_else_fails(game_world):
    """
    If the parser doesn't understand the verb, and the current room DOES NOT
    have a "huh" attribute, then emit a random message of last resort to the
    user, which starts by quoting the user's input.
    """
    user, obj, room, exit = game_world
    message = "wibble ntoll with bongo"
    result = (None, None, None)
    with asynctest.patch("textsmith.parser.get_objects",
                         return_value=result), \
            asynctest.patch("textsmith.logic.emit_to_user") as mock_fn:
        await parser.parse(user["_meta"]["uuid"], message)
        assert mock_fn.call_count == 1
        output = mock_fn.call_args[0][1]
        assert output.startswith(f'"{message}", ') is True
        assert len(output) > len(message) + 4


@pytest.mark.asyncio
async def test_get_objects_empty_args(game_world):
    """
    If the args to get_objects is empty, return a default (None, None) to
    indicate there's no direct object (position 0) or indirect object (position
    1).
    """
    user, obj, room, exit = game_world
    args = ""
    assert (None, None, None) == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_simple_direct_object(game_world):
    """
    If the args are just a single word, return the word as the value of the
    direct object.
    """
    user, obj, room, exit = game_world
    args = "dobj"
    assert ("dobj", None, None) == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_direct_object_trailing_preposition(game_world):
    """
    If the args are just a single direct object and preposition, return the
    words in the expected position in the tuple..
    """
    user, obj, room, exit = game_world
    args = "dobj prep"
    assert ("dobj", "prep", None) == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_simple_objects_and_prep(game_world):
    """
    If the args are just three words, return the words in the expected
    positions of the tuple.
    """
    user, obj, room, exit = game_world
    args = "dobj prep iobj"
    expected = ("dobj", "prep", "iobj")
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_direct_obj(game_world):
    """
    If the args are just complex words, return the words as the direct object.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj"'
    expected = ("complex dobj", None, None)
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_direct_obj_preposition(game_world):
    """
    If the args are complex words and then a preposition, return the
    complex words as direct object with preposition.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj" foo'
    expected = ("complex dobj", "foo", None)
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_direct_obj_simple_obj(game_world):
    """
    If the args are complex words, preposition, simple word, return the
    complex words as direct object, the preposition and indirect object as
    a single word.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj" foo iobj'
    expected = ("complex dobj", "foo", "iobj")
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_direct_obj_complex_indirect_obj(game_world):
    """
    If the args are just three words, return the words in the expected
    positions of the tuple.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj" foo "complex iobj"'
    expected = ("complex dobj", "foo", "complex iobj")
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_direct_obj_complex_indirect_obj(game_world):
    """
    If the args are just three words, return the words in the expected
    positions of the tuple.
    """
    user, obj, room, exit = game_world
    args = 'dobj foo "complex iobj"'
    expected = ("dobj", "foo", "complex iobj")
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_dobj_missing_quotes_end(game_world):
    """
    A ValueError happens if the quotes are missing from the end of the
    direct object.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj foo "complex iobj"'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_dobj_missing_quotes_start(game_world):
    """
    A ValueError happens if the quotes are missing from the start of the
    direct object.
    """
    user, obj, room, exit = game_world
    args = 'complex dobj" foo "complex iobj"'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_dobj_missing_quotes_both(game_world):
    """
    A ValueError happens if the quotes are missing from both the start and end
    of the direct object.
    """
    user, obj, room, exit = game_world
    args = 'complex dobj foo "complex iobj"'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_iobj_missing_quotes_start(game_world):
    """
    A ValueError happens if the quotes are missing from the start of the
    indirect object.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj" foo complex iobj"'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_iobj_missing_quotes_end(game_world):
    """
    A ValueError happens if the quotes are missing from the end of the
    indirect object.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj" foo "complex iobj'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_iobj_missing_quotes_both(game_world):
    """
    A ValueError happens if the quotes are missing from both the start and end
    of the indirect object.
    """
    user, obj, room, exit = game_world
    args = '"complex dobj" foo complex iobj'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_quoted_single_word_dobj(game_world):
    """
    A ValueError happens if the quotes surround a single word direct object.
    """
    user, obj, room, exit = game_world
    args = '"dobj" foo iobj'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_quoted_single_word_iobj(game_world):
    """
    A ValueError happens if the quotes surround a single word indirect object.
    """
    user, obj, room, exit = game_world
    args = 'dobj foo "iobj"'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_complex_preposition_causes_failure(game_world):
    """
    A ValueError happens if preposition is complex.
    """
    user, obj, room, exit = game_world
    args = 'dobj "foo bar" iobj'
    with pytest.raises(ValueError):
        assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_replace_direct_obj(game_world):
    """
    If the string of direct_obj is the name or alias of an object in context,
    replace the string with the object's dictionary.
    """
    user, obj, room, exit = game_world
    args = 'objectname prep iobj'
    expected = (obj, "prep", "iobj")
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_replace_indirect_obj(game_world):
    """
    If the string of indirect_obj is the name or alias of an object in context,
    replace the string with the object's dictionary.
    """
    user, obj, room, exit = game_world
    args = 'dobj prep objectname'
    expected = ("dobj", "prep", obj)
    assert expected == await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_replace_direct_obj_multi_matches(game_world):
    """
    If the string of direct_obj is the name or alias of multiple objects in
    the current context, raise a ValueError
    """
    user, obj, room, exit = game_world
    new_obj = logic.add_object("obj2", "description", user)
    ob2 = database.OBJECTS[new_obj]
    ob2["_meta"]["alias"].append("objectname")
    args = 'objectname prep iobj'
    with pytest.raises(ValueError):
        await parser.get_objects(user, room, args)


@pytest.mark.asyncio
async def test_get_objects_replace_indirect_obj_multi_matches(game_world):
    """
    If the string of indirect_obj is the name or alias of multiple objects in
    the current context, raise a ValueError
    """
    user, obj, room, exit = game_world
    new_obj = logic.add_object("obj2", "description", user)
    ob2 = database.OBJECTS[new_obj]
    ob2["_meta"]["alias"].append("objectname")
    args = 'dobj prep objectname'
    with pytest.raises(ValueError):
        await parser.get_objects(user, room, args)
