from sqlalchemy.orm import sessionmaker
from database import db_engine, User, Category, Item
from flask import Flask, render_template, request, redirect, url_for, json
from flask import jsonify, session, flash, make_response
from oauth2client import client
import httplib2
import string
import random


CLIENT_SECRET_FILE = 'client_secret.json'
CLIENT_ID = json.loads(
    open(CLIENT_SECRET_FILE, 'r').read())['web']['client_id']
AUTH_SCOPES = ['profile', 'email', 'openid']
REDIRECT_URI = 'http://localhost:5000'

# Create a session factory object for creating db sessions connected to the
# app's database
SessionFactory = sessionmaker(bind=db_engine)

db_session = SessionFactory()   # instantiate a session for db access


app = Flask(__name__)


#-----------------------------
# Helper Functions
#-----------------------------
def make_JSON_response(message, code):
    response = make_response(json.dumps(message), code)
    response.headers['Content-Type'] = 'application/json'
    return response


# customized flask render template function which passes additional custom
# arguments needed for majority of application pages
def render_catalog_template(file_or_list, **context):
    categories = db_session.query(Category).all()
    user_logged_in = isUserLoggedIn()
    return render_template(file_or_list,
                           categories=categories,
                           user_logged_in=user_logged_in,
                           **context)


# generates new random state token and sets user session state to it
def setNewState():
    state = ''.join([random.choice(string.ascii_uppercase + string.digits)
                     for x in xrange(32)])
    session['state'] = state
    return state


# verifies passed in state token matches state in user's session
def validState(state):
    if not (state and state == session.get('state')):
        return None

    return state


def isUserLoggedIn():
    return 'user_id' in session


def getUser(google_id):
    if not google_id:
        return None

    return db_session.query(User).filter_by(google_id=google_id).first()


def createNewUser(name, email, picture, google_id, google_refresh_token):
    if not (name and email and google_id):
        return None

    user = User(name=name, email=email, picture=picture,
                google_id=google_id, google_refresh_token=google_refresh_token)
    if not user:
        return None

    db_session.add(user)
    db_session.commit()
    return user


#-----------------------------
# JSON Endpoints
#-----------------------------
@app.route('/catalog.json')
def showCatalogJSON():
    category_list = db_session.query(Category).all()
    if not category_list:
        return jsonify({})

    return jsonify(Category=[category_record.serialize
                             for category_record in category_list])


#-----------------------------
# Application Route Handlers
#-----------------------------
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not validState(request.args.get('STATE')):
            return make_JSON_response('Invalid state parameter!', 401)

        if not request.form.get('code'):
            return make_JSON_response('Failed to retrieve user authorization!',
                                      401)

        auth_code = request.form.get('code')

        # Exchange client info and auth code for credentials
        # as per Google Sign-in server-side flow:
        # https://developers.google.com/identity/sign-in/web/server-side-flow
        try:
            auth_credentials = client.credentials_from_clientsecrets_and_code(
                CLIENT_SECRET_FILE,
                AUTH_SCOPES,
                auth_code
            )
        except client.FlowExchangeError as e:
            return make_JSON_response('Failed to exchange authorization code '
                                      'for valid access token', 401)

        if not (auth_credentials and auth_credentials.id_token):
            return make_JSON_response('Failed to validate user authorization',
                                      401)

        google_user_id = auth_credentials.id_token.get('sub')
        if not google_user_id:
            return make_JSON_response('Failed to validate user credentials',
                                      401)

        # Verify access token
        h = httplib2.Http()
        url = 'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token=%s'
        url = url % auth_credentials.access_token
        result = json.loads(h.request(url, 'GET')[1])
        if result.get('error_description') is not None:
            return make_JSON_response('Failed to verify access token (error: '
                                      '%s)' % result.get('error_description'),
                                      500)

        if result['sub'] != google_user_id:
            return make_JSON_response('Token\'s user_id does not match '
                                      'original user', 401)

        if result['aud'] != CLIENT_ID:
            error = 'Token\'s client ID does not match app\'s!'
            print error
            return make_JSON_response(error, 401)

        # Find existing user or create account for new user
        user = getUser(google_user_id)
        if not user:
            http_auth = auth_credentials.authorize(httplib2.Http())
            userinfo_url = 'https://www.googleapis.com/userinfo/v2/me'
            resp, content = http_auth.request(userinfo_url)

            if not (resp and resp.status == 200 and content):
                flash('Failed to locate existing user or retrieve necessary '
                      'new user info!', 'error')
                return redirect(url_for('mainPage'))

            userinfo = json.loads(content)
            user = createNewUser(userinfo.get('name'),
                                 userinfo.get('email'),
                                 userinfo.get('picture'),
                                 google_user_id,
                                 auth_credentials.refresh_token)
            if not user:
                flash('Failed to create new user!', 'error')
                return redirect(url_for('mainPage'))
            else:
                flash('Account Successfully Created!')
                flash('Welcome, %s!' % user.name)

        # Set session with authenticated user's info
        session['user_id'] = user.id
        session['name'] = user.name
        session['email'] = user.email
        session['picture'] = user.picture
        session['google_id'] = user.google_id
        session['google_refresh_token'] = user.google_refresh_token
        session['google_access_token'] = auth_credentials.access_token

        return redirect(url_for('mainPage'))
    else:
        if isUserLoggedIn():
            return redirect(url_for('mainPage'))

        return render_template('login.html', STATE=setNewState())


@app.route('/logout/')
def logout():
    token = session.get('google_access_token')
    if not token:
        return make_JSON_response('Current user not connected', 401)

    # Revoke Google OAuth2 access token
    h = httplib2.Http()
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % token
    result = h.request(url, 'GET')[0]

    # Clear user data from session
    if result['status'] == '200':
        session.pop('user_id', None)
        session.pop('name', None)
        session.pop('email', None)
        session.pop('picture', None)
        session.pop('google_id', None)
        session.pop('google_refresh_token', None)
        session.pop('google_access_token', None)

        flash('Successfully Logged Out!')
        return redirect(url_for('mainPage'))

    return make_JSON_response('Failed to revoke token for current user', 500)


@app.route('/')
@app.route('/catalog/')
def mainPage():
    return render_catalog_template('commontemplate.html')


@app.route('/catalog/<int:category_id>/')
def showItems(category_id):
    category_record = db_session.query(Category).get(category_id)
    if not category_record:
        flash('Category with ID \'%s\' does not exist!' % category_id, 'error')
        return redirect(url_for('mainPage'))

    return render_catalog_template('showitems.html',
                                   category_id=category_id,
                                   category=category_record)


@app.route('/catalog/<int:category_id>/new/', methods=['GET', 'POST'])
def createItem(category_id):
    category_record = db_session.query(Category).get(category_id)
    if not category_record:
        flash('Category with ID \'%s\' does not exist!' % category_id, 'error')
        return redirect(url_for('mainPage'))

    if not isUserLoggedIn():
        flash('You must be logged in to create an item!', 'error')
        return redirect(url_for('showItems', category_id=category_id))

    if request.method == 'POST':
        if not validState(request.args.get('STATE')):
            return make_JSON_response('Invalid state parameter!', 401)

        try:
            name = request.form.get('name', type=str)
            description = request.form.get('description', type=str)
            sel_cat_id = request.form.get('category', type=int)
        except ValueError as e:
            flash('Valid information for new item not provided!', 'error')
            return redirect(url_for('createItem', category_id=category_id))

        # Form input validations
        if name and name.strip():
            name = name.strip()
        else:
            flash('Valid name required for new item', 'error')
            return redirect(url_for('createItem', category_id=category_id))

        if description and description.strip():
            description = description.strip()
        else:
            description = None

        if not sel_cat_id:
            flash('Valid category required for new item', 'error')
            return redirect(url_for('createItem', category_id=category_id))

        sel_cat_record = db_session.query(Category).get(sel_cat_id)
        if not sel_cat_record:
            flash('Valid category not found. You cannot create an item with '
                  'an invalid category!', 'error')
            return redirect(url_for('createItem', category_id=category_id))

        new_item = Item(name=name,
                        description=description,
                        category_id=sel_cat_id,
                        user_id=session.get('user_id'))
        db_session.add(new_item)
        db_session.commit()
        flash("'%s' successfully added to '%s' "
              "category!" % (new_item.name, sel_cat_record.name))
        return redirect(url_for('showItems', category_id=new_item.category_id))
    else:
        return render_catalog_template('newitem.html',
                                       STATE=setNewState(),
                                       category_id=category_id,
                                       category=category_record)


@app.route('/catalog/<int:category_id>/<int:item_id>/edit/',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    category_record = db_session.query(Category).get(category_id)
    if not category_record:
        flash('Category with ID \'%s\' does not exist!' % category_id, 'error')
        return redirect(url_for('mainPage'))

    item_record = db_session.query(Item).get(item_id)
    if not item_record:
        flash('Item with ID \'%s\' does not exist!' % item_id, 'error')
        return redirect(url_for('showItems', category_id=category_id))

    if not isUserLoggedIn():
        flash('You must be logged in and have created the item to edit it!',
              'error')
        return redirect(url_for('showItems', category_id=category_id))

    if item_record.user_id != session['user_id']:
        flash('You must have created the item to edit it!', 'error')
        return redirect(url_for('showItems', category_id=category_id))

    if request.method == 'POST':
        if not validState(request.args.get('STATE')):
            return make_JSON_response('Invalid state parameter!', 401)

        update_record = False

        try:
            name = request.form.get('name', type=str)
            description = request.form.get('description', type=str)
            sel_cat_id = request.form.get('category', type=int)
        except ValueError as e:
            flash('Valid information for item update not provided!', 'error')
            return redirect(url_for('editItem',
                                    category_id=item_record.category_id,
                                    item_id=item_record.id))

        # Form input validations
        if name and name.strip():
            name = name.strip()
            if name != item_record.name:
                item_record.name = name
                update_record = True

        if description and description.strip():
            description = description.strip()
            if description != item_record.description:
                item_record.description = description
                update_record = True

        if sel_cat_id and sel_cat_id != item_record.category_id:
            sel_cat_record = db_session.query(Category).get(sel_cat_id)
            if sel_cat_record:
                item_record.category_id = sel_cat_id
                update_record = True

        # Do not update record if valid change is not made
        if not update_record:
            return redirect(url_for('editItem',
                                    category_id=item_record.category_id,
                                    item_id=item_record.id))

        db_session.add(item_record)
        db_session.commit()
        flash("'%s' successfully updated!" % item_record.name)
        return redirect(url_for('showItems',
                                category_id=item_record.category_id))
    else:
        return render_catalog_template('edititem.html',
                                       STATE=setNewState(),
                                       category_id=category_id,
                                       item=item_record)


@app.route('/catalog/<int:category_id>/<int:item_id>/delete/',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    category_record = db_session.query(Category).get(category_id)
    if not category_record:
        flash('Category with ID \'%s\' does not exist!' % category_id, 'error')
        return redirect(url_for('mainPage'))

    item_record = db_session.query(Item).get(item_id)
    if not item_record:
        flash('Item with ID \'%s\' does not exist!' % item_id, 'error')
        return redirect(url_for('showItems', category_id=category_id))

    if not isUserLoggedIn():
        flash('You must be logged in and have created the item to delete it!',
              'error')
        return redirect(url_for('showItems', category_id=category_id))

    if item_record.user_id != session['user_id']:
        flash('You must have created the item to delete it!', 'error')
        return redirect(url_for('showItems', category_id=category_id))

    if request.method == 'POST':
        if not validState(request.args.get('STATE')):
            return make_JSON_response('Invalid state parameter!', 401)

        db_session.delete(item_record)
        db_session.commit()
        flash("'%s' successfully deleted from '%s' "
              "category!" % (item_record.name, item_record.category.name))
        return redirect(url_for('showItems', category_id=category_id))
    else:
        return render_catalog_template('deleteitem.html',
                                       STATE=setNewState(),
                                       category_id=category_id,
                                       item=item_record)


#-----------------------------
# Application Main
#-----------------------------
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.run(debug=True, host='0.0.0.0', port=5000)
