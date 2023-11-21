from flask import Flask, render_template, request, redirect, url_for, flash
import os
import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId



load_dotenv()

app = Flask(__name__)

mongo_db_url =  os.environ.get("MONGO_DB_CONN_STRING")

client = MongoClient(mongo_db_url)
db = client['Electrade']

@app.route('/')
def index():
    return render_template('main.html')


@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/login')
def login():
    return render_template('index.html')

@app.route('/componentes')
def componentes():
    return render_template('componentes.html')

@app.route('/servicios')
def servicios():
    return render_template('servicios.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/address')
def address():
    return render_template('address.html')

@app.route('/Cart')
def Cart():
    return render_template('Cart.html')

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')




if __name__ == '__main__':
    app.secret_key = 'mysecret'
    app.run(debug=True)