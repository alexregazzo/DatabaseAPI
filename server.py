from flask import Flask, request, session, redirect, url_for, g, render_template
from functools import wraps
import api_response
import database.user
import database.root.types.user
import database.root.types.token
import json
import hashlib
import jwt
import os

current_dir = os.path.dirname(__file__)
with open(os.path.join(current_dir, "config.json")) as file:
    CONFIG = json.load(file)
TOKEN_KEY = CONFIG["token_secret_key"]
app = Flask(__name__, template_folder="templates")
app.secret_key = CONFIG['flask_secret_key']


# ----------------------------------------------------------- GENERAL -----------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ----------------------------------------------------------- API -----------------------------------------------------------
@app.route("/docs")
def docs():
    return render_template("documentation.html")


def restricted_token_access(func):
    @wraps(func)
    def authenticate_token(*args, **kwargs):

        if request.method == "GET":
            token_token = request.args.get('token')
            if token_token:
                try:
                    decoded_token = jwt.decode(token_token, TOKEN_KEY)
                except:
                    return api_response.APIResponse.bad(query=request.url, error_message="Invalid token").get_response()
                else:
                    return func(*args, decoded_token=decoded_token, **kwargs)
            return api_response.APIResponse.bad(query=request.url, error_message="Missing token").get_response()

    return authenticate_token


@app.route("/api/v1/query/")
@restricted_token_access
def database_use(decoded_token: dict):
    try:
        query = request.args['q']
    except KeyError:
        return api_response.APIResponse.bad(query=request.url, error_message="Arguments missing: q").get_response()
    except:
        pass
    else:
        with database.user.UserDatabase(decoded_token['user_email'], decoded_token['database_name']) as db:
            return api_response.APIResponse.good(query=request.url, database_response=db.execute(query)).get_response()

    return api_response.APIResponse.bad(query=request.url, error_message="Unkown error").get_response()


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
        try:
            g.user = database.root.types.user.User.get(user_id=session['user_id'])
        except Exception as e:
            print(e)
            g.user = None


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

        try:
            user = database.root.types.user.User.create(user_fullname=user_fullname, user_email=user_email, user_password=user_password)
            session['user_id'] = user.user_id
            print(True)
            print(user)
            return redirect(url_for("profile"))
        except Exception as e:
            return render_template("signup.html", error_message="* Something went wrong while creating the account, maybe its already created" + str(e))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.pop('user_id', None)

        user_email = request.form['email']
        user_password = hashlib.sha256(bytes(request.form['password'], 'utf8')).hexdigest()
        try:
            user = database.root.types.user.User.get(user_email=user_email)
            if user.check_pass(user_password):
                session['user_id'] = user.user_id
                return redirect(url_for("profile"))
        except:
            pass
        return render_template("login.html", error_message="* Incorrect email or password")
    return render_template("login.html")


@app.route("/profile")
@restricted_login_access
def profile():
    """
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
            try:
                token = database.root.types.token.Token.get(token_id=token_id)
                token.verify_code(activation_code)
            except:
                pass
        if token_id:
            return redirect(url_for('database_stats', token_id=token_id))
        return redirect(url_for('profile'))
    else:
        # get request
        dbname = request.args.get('dbname')
        token_id = request.args.get('token_id')
        token = None
        if dbname:
            try:
                token = database.root.types.token.Token.create(user=g.user, dbname=dbname)
            except:
                pass
        elif token_id:
            try:
                token = database.root.types.token.Token.get(token_id=token_id)
            except:
                pass
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

        try:
            token = database.root.types.token.Token.get(token_id=token_id)
            # token found
            if token.user_id == g.user.user_id:
                # match user
                return render_template('database_stats.html', token=token)
        except:
            pass
    return redirect(url_for('profile'))


if __name__ == "__main__":
    import platform

    if platform.system() == "Windows":
        app.run("127.0.0.4", port=80, debug=True)
    elif platform.system() == "Linux":
        app.run(host='0.0.0.0', port=8245)
