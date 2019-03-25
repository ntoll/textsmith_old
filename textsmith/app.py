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
from quart import Quart, render_template


app = Quart(__name__)


@app.route('/')
async def home():
    return await render_template('home.html')


@app.route('/login')
async def login():
    pass


@app.route('/signup', methods=['GET', 'POST'])
async def signup():
    error = None
    if request.method == 'POST':
        form = await request.form
        username = form.get('username')
        email = form.get('email')
        password = form.get('password')
        confirm_password = form.get('confirm_password')
        # TODO: Finish this.
    return await render_template('signup.html')


@app.route('/confirm')
async def confirm():
    pass


if __name__ == '__main__':
    app.run()
