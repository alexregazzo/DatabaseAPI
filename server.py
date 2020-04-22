from flask import Flask, request, session, redirect, url_for, g, render_template
from functools import wraps
import api_response
import database.response
import database.user
import database.root.types.user
import database.root.types.token
import json
import hashlib
import os
import re

# TODO: setup logging
# TODO: treat web pages errors better

current_dir = os.path.dirname(__file__)
with open(os.path.join(current_dir, "config.json")) as file:
    CONFIG = json.load(file)
TOKEN_KEY = CONFIG["token_secret_key"]
app = Flask(__name__, template_folder="templates")
app.secret_key = CONFIG['flask_secret_key']


# ----------------------------------------------------------- GENERAL -----------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for('profile'))


# ----------------------------------------------------------- API -----------------------------------------------------------
@app.route("/docs")
def docs():
    api_endpoint = request.url_root[:-1] + url_for('database_use')
    token_example = "YOUR_TOKEN_EXAMPLE"
    sql_query_example = "YOUR_SQL_QUERY"
    request_query_example = f"{api_endpoint}?q={sql_query_example}&token={token_example}"
    response_examples = {
        'generic_good': api_response.APIResponse.good(
            query=request_query_example,
            token_token=token_example,
            database_response=database.response.DatabaseResponse.good(
                query=sql_query_example
            )
        ).json(indent=4),
        'request_error': api_response.APIResponse.bad(
            query=request_query_example,
            error_message="Generic error message"
        ).json(indent=4),
    }
    return render_template(
        "documentation.html",
        sql_query_example=sql_query_example,
        request_query_example=request_query_example,
        token_example=token_example,
        api_endpoint=api_endpoint,
        response_examples=response_examples
    )


def restricted_token_access(func):
    @wraps(func)
    def authenticate_token(*args, **kwargs):

        if request.method == "GET":
            token_token = request.args.get('token')
            if token_token:
                try:
                    with database.root.RootDatabase() as root_db:
                        results = root_db.select_tokens(token_token=token_token)
                except:
                    return api_response.APIResponse.bad(query=request.url, error_message="Invalid token").get_response()
                else:
                    if results:
                        token = results[0]
                        if token.token_active != 1:
                            return api_response.APIResponse.bad(query=request.url, error_message="Token not active").get_response()
                        return func(*args, token=token, **kwargs)
                    else:
                        return api_response.APIResponse.bad(query=request.url, error_message="Token not found").get_response()

            return api_response.APIResponse.bad(query=request.url, error_message="Missing token").get_response()

    return authenticate_token


@app.route("/api/v1/query/")
@restricted_token_access
def database_use(token: database.root.types.token.Token):
    try:
        query = request.args['q']
    except KeyError:
        return api_response.APIResponse.bad(query=request.url, token_token=token.token_token, error_message="Arguments missing: q").get_response()
    except:
        pass
    else:
        with database.user.UserDatabase(token.user_email, token.token_database_name) as db:
            return api_response.APIResponse.good(query=request.url, token_token=token.token_token, database_response=db.execute(query)).get_response()

    return api_response.APIResponse.bad(query=request.url, token_token=token.token_token, error_message="Unkown error").get_response()


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
    TODO: logout button
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
                if token.token_active:
                    return redirect(url_for('database_stats', token_id=token_id))
                token.verify_code(activation_code)
            except:
                pass
        if token_id:
            return redirect(url_for('database_stats', token_id=token_id))
        return redirect(url_for('profile'))
    else:
        # get request
        dbname = request.args.get('dbname')
        if dbname:
            if re.match('[a-zA-Z0-9 _-]+', dbname) is None:
                return redirect(url_for('profile'))
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
            if token.token_active:
                return redirect(url_for('database_stats', token_id=token_id))
            return render_template('database_create.html', dbname=dbname, token=token)
        return redirect(url_for('profile'))


@app.route("/database/stats")
@restricted_login_access
def database_stats():
    # TODO: create disable button
    # TODO: create delete button
    # TODO: limit amount of use shown

    token_id = request.args.get('token_id')
    if token_id:
        # token query found
        try:
            token = database.root.types.token.Token.get(token_id=token_id)
            # token found
            if token.user_id == g.user.user_id:
                # match user
                uses = token.get_uses()
                return render_template('database_stats.html', token=token, uses=uses)
        except Exception as e:
            print(e)
            raise

    return redirect(url_for('profile'))


if __name__ == "__main__":
    import platform

    if platform.system() == "Windows":
        app.run("127.0.0.4", port=80, debug=True)
        # app.run("127.0.0.4", port=5478, debug=True)
    elif platform.system() == "Linux":
        app.run(host='0.0.0.0', port=8245)
