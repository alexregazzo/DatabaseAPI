from flask import Flask, request, make_response, session, redirect, url_for, g, render_template
from functools import wraps
import server_response
import database
import json
import hashlib
import jwt

with open("config.json") as file:
    CONFIG = json.load(file)
TOKEN_KEY = CONFIG["token_secret_key"]
app = Flask(__name__, template_folder="templates")
app.secret_key = CONFIG['flask_secret_key']


# ----------------------------------------------------------- GENERAL -----------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for('login'))
    # return "index"


# ----------------------------------------------------------- API -----------------------------------------------------------
@app.route("/docs")
def docs():
    return redirect(url_for('login'))
    # return "documentation"


def restricted_token_access(func):
    @wraps(func)
    def authenticate_token(*args, **kwargs):
        if request.method == "GET":
            token_token = request.args.get('token')
            if token_token:
                try:
                    decoded_token = jwt.decode(token_token, TOKEN_KEY)
                except:
                    return make_response({"error_message": "Invalid token"}, 400)
                else:
                    return func(*args, decoded_token=decoded_token, **kwargs)
            return make_response({"error_message": "Missing token"}, 400)

    return authenticate_token


@app.route("/api/v1/<string:query_type>/")
@restricted_token_access
def database_use(query_type, decoded_token: dict):
    try:
        query = request.args['q']
    except KeyError:
        return make_response(server_response.BadResponse("Arguments missing: database and/or q").json(), 400)
    except:
        pass
    else:
        if query_type in database.Database.ALLOWED_ATRIBUTES:
            with database.Database(decoded_token['user_email'], decoded_token['database_name']) as db:
                return getattr(db, query_type)(query).json()
        else:
            return make_response(server_response.BadResponse("Invalid database query type").json(), 400)
    return make_response(server_response.BadResponse("Unkown error").json(), 400)


#

#

#

#

#

#

#

#

# ----------------------------------------------------------- USER -----------------------------------------------------------
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = database.User.get_user_by_id(session['user_id'])


def restricted_login_access(func):
    @wraps(func)
    def authenticate_login(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return authenticate_login


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        session.pop("user_id", None)
        user_fullname = request.form['fullname']
        user_email = request.form['email']
        user_password = hashlib.sha256(bytes(request.form['password'], 'utf8')).hexdigest()

        user = database.User.create(user_fullname, user_email, user_password)
        if user:
            session['user_id'] = user.user_id
            return redirect(url_for("profile"))
        else:
            return render_template("signup.html", error_message="* Something went wrong while creating the account, maybe its already created")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.pop('user_id', None)

        user_email = request.form['email']
        user_password = hashlib.sha256(bytes(request.form['password'], 'utf8')).hexdigest()

        user = database.User.get_user_by_email(user_email)

        if user and user.check_pass(user_password):
            session['user_id'] = user.user_id
            return redirect(url_for("profile"))
        else:
            return render_template("login.html", error_message="* Incorrect email or password")
    return render_template("login.html")


@app.route("/profile")
@restricted_login_access
def profile():
    """
    TODO: create tokens [database]
    TODO: show tokens [database]
    TODO: revoke token [database]
    """
    return render_template("profile.html", databases_names="<br/>".join([token.token_database_name for token in g.user.get_tokens()]))


@app.route("/database/create", methods=["GET", "POST"])
@restricted_login_access
def database_create():
    if request.method == "POST":
        # sending code
        activation_code = request.form.get('activation_code')
        token_id = request.form.get('token_id')
        if token_id and activation_code:
            # verify match
            token = database.Token.get(token_id)
            token.verify_code(activation_code)
        if token_id:
            return redirect(url_for('database_stats', token_id=token_id))
        return redirect(url_for('profile'))
    else:
        dbname = request.args.get('dbname')
        token_id = request.args.get('token_id')
        token = None
        if dbname:
            token = database.Token.create(g.user, dbname)
        elif token_id:
            token = database.Token.get(token_id)
        if token:
            # token created
            return render_template('database_create.html', dbname=dbname, token=token)
        return redirect(url_for('profile'))


@app.route("/database/stats")
@restricted_login_access
def database_stats():
    token_id = request.args.get('token_id')
    if token_id:
        # token query found
        token = database.Token.get(token_id)
        if token:
            # token found
            if token.user_id == g.user.user_id:
                # match user

                return render_template('database_stats.html', token=token)
    return redirect(url_for('profile'))


if __name__ == "__main__":
    import platform

    if platform.system() == "Windows":
        app.run("127.0.0.4", port=80, debug=True)
    elif platform.system() == "Linux":
        app.run(host='0.0.0.0', port=8245)
