from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo import MongoClient
from bson import ObjectId
from flask_bcrypt import Bcrypt
from datetime import datetime
from bson import DBRef
    


load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)


mongo_db_url =  os.environ.get("MONGO_DB_CONN_STRING")

client = MongoClient(mongo_db_url)
db = client['Electrade']
componentes_collection = db['componentes']
servicios_collection = db['servicios']
user_collection = db['users']

@app.route('/')
def index():
    return render_template('index.html')

# Register y login

@app.route('/register', methods=['POST', 'GET'])
def register():
    if 'logged_in' in session:
        flash('Ya estas registrado')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        existing_user = user_collection.find_one({'$or': [{'username': username}, {'email': email}]})
        if existing_user:
            flash('El usuario ya existe')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        user_doc = {
            'name': name,
            'username': username,
            'password': hashed_password,
            'email': email,
            'role': 'Comprador',
            'creada': datetime.utcnow()
        }
        
        user_collection.insert_one(user_doc)
        flash('Registro exitoso')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'logged_in' in session:
        flash('Ya has iniciado sesión.')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = user_collection.find_one({'username': username})
        
        if user and bcrypt.check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            flash('Bienvenido ' + user['name'])
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesion cerrada')
    return redirect(url_for('index'))


# Perfiles
@app.route('/profile', methods=['POST', 'GET'])
def profile():
        if 'logged_in' in session:
            user = user_collection.find_one({'username': session['username']})
            role = user.get('role', 'Comprador')
            created = user.get('creada', datetime.utcnow())
            
            time_elapsed = datetime.utcnow() - created
            minutes = int(time_elapsed.total_seconds() / 60)
            hours = int(minutes / 60)
            days = int(hours / 24)
            weeks = int(days / 7)

            if minutes < 60:
                time_elapsed_str = f'{minutes} minutos'
            elif hours < 24:
                time_elapsed_str = f'{hours} horas'
            elif days < 7:
                time_elapsed_str = f'{days} días'
            else:
                time_elapsed_str = f'{weeks} semanas'
        
            if role == 'Vendedor':
                return render_template('perfil_vendedor.html', username=session['username'], created=created, time_elapsed=time_elapsed_str, role=role)
            if role == 'Comprador':
                return render_template('perfil_comprador.html', username=session['username'], created=created, time_elapsed=time_elapsed_str, role=role)
        else:
            flash('Inicia sesión para ver tu perfil')
            return redirect(url_for('login'))

# Registro para vendedores
@app.route('/vendedor'  , methods=['POST', 'GET'])  
def procesar_formulario():
    
    username = session['username']
    if username:
        user = user_collection.find_one({'username': username})
        if user and user.get('role') == 'Vendedor':
            return redirect(url_for('index'))
    
    if request.method == 'POST':

        document_type = request.form.get('document_type')
        celular = request.form.get('celular')
        dni = request.form.get('DNI')
        ruc = request.form.get('RUC')
        company = request.form.get('Company')
        
        username = session['username']

        user = user_collection.find_one({'username': username})
        if user:
            if document_type == 'dni':
                update_data = {
                    '$set': {
                        'celular': celular,
                        'document_type': document_type,
                        'dni': dni,
                        'role': 'Vendedor'
                    }
                }
            else:
                update_data = {
                    '$set': {
                        'celular': celular,
                        'document_type': document_type,
                        'ruc': ruc,
                        'company': company,
                        'role': 'Vendedor'
                    }
                }
            user_collection.update_one({'username': username}, update_data)
        return redirect(url_for('index'))        
            
    return render_template('vendedor_registro.html')
    


# Pagina Vendedores
@app.route('/seller_products')
def seller_products():
    if 'user_id' in session:
        user_id = session['user_id']
        user = user_collection.find_one({'_id': ObjectId(user_id)})
        
        if user and user['user_type'] == vendedor:
            seller_name = user['name']
            seller_componentes = componentes_collection.find({'seller_name': seller_name})
            
            return render_template('seller_products.html', componentes=seller_componentes)

    return redirect(url_for('login'))

@app.route('/add_componente', methods=['POST', 'GET'])
def add_product():
    if request.method == 'POST':
        name = request.form['nombre']
        description = request.form['descripcion']
        price = float(request.form['precio'])
        stock = int(request.form['stock'])
        
        seller = session.get('user_id')
        # Procesar la imagen
        image_file = request.files['imagen']
        image_data = image_file.read()
        encoded_img = Binary(image_data, sub_type=128)
        
        # Almacenar en mongoDB
        componente_doc = {
            'name': name,
            'description': description,
            'price': price,
            'stock': stock,
            'image': encoded_img
        }
        
        componentes_collection.insert_one(componente_doc)
    return render_template('add_componente.html')

@app.route('/edit_componente/<componente_id>', methods=['POST', 'GET'])
def edit_product(componente_id):
    
    componente = componentes_collection.find_one({'_id': ObjectId(componente_id)})
    
    if request.method == 'POST':
        name = request.form['nombre']
        description = request.form['descripcion']
        price = float(request.form['precio'])
        stock = int(request.form['stock'])
        
        
        componentes_collection.update_one(
            {'_id': ObjectId(componente_id)},
            {'$set': {
                'name': name,
                'description': description,
                'price': price,
                'stock': stock
            }}
        )
        
        return redirect(url_for('componentes'))
        
        
    return render_template('edit_componente.html', componente=componente)




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