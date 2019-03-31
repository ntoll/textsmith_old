# TextSmith

A multi-user platform for creating and interacting within text based worlds.

A version of this game is hosted at
[http://textsmith.org/](http://textsmith.org).

The run the game:

* Within a virtualenv gather the requirements: `pip install -r requirements.txt`
* Use the following command to launch the server: `make run`
* Connect to the [local server](http://localhost:8000) via your browser.

If the `make` command doesn't work, try the following command from the shell:
`hypercorn textsmith.app:app`.

The game database (`database.json`) is dumped once every minute while the server
is running.

This is very much a FIRST DRAFT and all feedback is most welcome..!
