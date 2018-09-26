from flask import (Flask,
                   render_template,
                   url_for,
                   request,
                   redirect,
                   jsonify)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


app = Flask(__name__)

CLIENT_ID = (json.loads(open('client_secrets.json', 'r').read())
             ['web']['client_id'])

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = scoped_session(DBSession)


def createUser(login_session):
    """Add a new user to the database."""
    newUser = (User(name=login_session['username'],
               email=login_session['email'],
               picture=login_session['picture']))
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    """Retrieve a user from the database."""
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    """Retrieve a users id from the database if that user exists."""
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Check if the states match up
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # Upgrade the authorization code into a creentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = (make_response(
            json.dumps('Failed to upgrade the authorization code'), 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = (make_response(
                    json.dumps("Token's user ID doesn't match given user ID."),
                    401))
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = (make_response(
                    json.dumps("Token's client ID doesn't match app's."), 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = (make_response(
                    json.dumps('Current user is already connected.'), 200))
        response.headers['Content-Type'] = 'application/json'

    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += (' " style = "width: 300px; height: 300px;border-radius: ' +
               '150px;-webkit-border-radius: 150px;-moz-border-radius: ' +
               '150px;"> ')
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('credentials')
    if access_token is None:
        response = (make_response(
                    json.dumps('Current user not connected.'), 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['credentials']
        return redirect(url_for('showCategories'))
    else:
        response = (make_response(
                    json.dumps('Failed to revoke token for given user'), 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/login')
def showLogin():
    """Display the login template."""
    state = (''.join(random.choice(
             string.ascii_uppercase + string.digits) for x in xrange(32)))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/')
def showCategories():
    """Display the main page template."""
    categories = session.query(Category).all()
    db_items = session.query(Item).order_by(Item.id.desc()).limit(5)

    # Get category names for the recent items
    items = []
    for item in db_items:
        category_name = (str(session.query(Category.name).filter_by(
                         id=item.category_id).one()))
        items.append({'name': item.name, 'id': item.id,
                      'category_id': item.category_id,
                      'category_name': category_name[3:len(category_name)-3]})
    if 'username' not in login_session:
        return render_template('public_categories.html',
                               categories=categories, items=items)
    return render_template('categories.html',
                           categories=categories, items=items)


@app.route('/catalog/<int:category_id>/items')
def showAllItems(category_id):
    """Display the items for a corresponding category."""
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return render_template('allitems.html', category=category, items=items)


@app.route('/catalog/add', methods=['GET', 'POST'])
def addItem():
    """Display the add template or add an item to the database."""
    if 'username' not in login_session:
        return redirect('login')
    if request.method == 'GET':
        categories = session.query(Category).all()
        return render_template('additem.html', categories=categories)
    elif request.method == 'POST':
        new = Item(name=request.form['name'],
                   description=request.form['description'],
                   category_id=request.form['category'],
                   user_id=login_session['user_id'])
        session.add(new)
        session.commit()
        return redirect(url_for('showCategories'))


@app.route('/catalog/<int:category_id>/<int:item_id>')
def showItem(category_id, item_id):
    """Display the an items page."""
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(id=item_id).one()
    if ('username' not in login_session) or \
            (item.user_id != login_session['user_id']):
                return (render_template('public_item.html',
                        category=category, item=item))
    return render_template('item.html', category=category, item=item)


@app.route('/catalog/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(item_id):
    """Display the edit template or edit an item in the database."""
    if 'username' not in login_session:
        return redirect('login')
    item = session.query(Item).filter_by(id=item_id).one()
    if item.user_id != login_session['user_id']:
        return redirect('showCategories')
    if request.method == 'GET':
        return render_template('edititem.html', item=item)
    elif request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.description = request.form['description']
        session.add(item)
        session.commit()
        return redirect(url_for('showAllItems', category_id=item.category_id))


@app.route('/catalog/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteItem(item_id):
    """Display the delete template or remove an item to the database."""
    if 'username' not in login_session:
        return redirect('login')
    item = session.query(Item).filter_by(id=item_id).one()
    if item.user_id != login_session['user_id']:
        return redirect('showCategories')
    if request.method == 'GET':
        return render_template('deleteitem.html', item=item)
    elif request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('showAllItems', category_id=item.category_id))


@app.route('/catalog.JSON')
def catalogJSON():
    """API endpoint for the entire catalog."""
    categories = session.query(Category).all()
    serialized_list = []
    for category in categories:
        category_items = categoryJSON(category.id)
        items = session.query(Item).filter_by(category_id=category.id).all()
        serialized = category.serialize
        serialized['Item'] = [item.serialize for item in items]
        serialized_list.append(serialized)
    return jsonify(Category=serialized_list)


@app.route('/catalog/<int:category_id>/<int:item_id>.JSON')
def itemJSON(category_id, item_id):
    """API endpoint for an item."""
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(item.serialize)


def add_categories():
    """Add initial categories to the database."""
    if not session.query(Category).first():
        shirts = Category(name="Shirts")
        session.add(shirts)
        dresses = Category(name="Dresses")
        session.add(dresses)
        pants = Category(name="Pants")
        session.add(pants)
        shoes = Category(name="Shoes")
        session.add(shoes)
        session.commit()


if __name__ == '__main__':
    add_categories()
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
