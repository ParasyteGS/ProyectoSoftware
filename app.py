from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from flask_bcrypt import Bcrypt
from datetime import datetime
from bson import DBRef
import base64
    


load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)


mongo_db_url =  os.environ.get("MONGO_DB_CONN_STRING")

client = MongoClient(mongo_db_url)
db = client['Electrade']
componentes_collection = db['componentes']
servicios_collection = db['servicios']
user_collection = db['users']
components_collection = db['components']


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

# Editar perfil
@app.route('/editar_perfil', methods=['POST', 'GET'])
def editar_perfil():
    if 'logged_in' in session:
        user = user_collection.find_one({'username': session['username']})
        name = user.get('name')
        username = user.get('username')
        email = user.get('email')
        celular = user.get('celular')
        document_type = user.get('document_type')
        if document_type == 'dni':
            document = user.get('dni')
            company = None
        else:
            document = user.get('ruc')
            company = user.get('company')
        
        if request.method == 'POST':
            new_name = request.form['new_name']
            new_email = request.form['new_email']
            new_celular = request.form['new_celular']
            
            update_data = {'name': new_name, 'email': new_email, 'celular': new_celular}
            
            if document_type == 'dni':
                update_data['dni'] = request.form['new_dni']
            else:
                update_data['ruc'] = request.form['new_ruc']
                update_data['company'] = request.form['new_company']
            
            user_collection.update_one(
                {'username': session['username']},
                {'$set': update_data}
            )
            
            return redirect(url_for('editar_perfil'))
                        
        return render_template('editar_perfil.html', username=username, name=name, email=email, celular=celular, document_type=document_type, document=document, company=company )


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

@app.route('/agregar_componente', methods=['POST', 'GET'])
def agregar_componente():
    if 'logged_in' in session:
        if request.method == 'POST':
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            precio = float(request.form['precio'])
            stock = int(request.form['stock'])
            condicion = request.form['condicion']  # Obtener el valor del select

            
            # Manejo de la imagen
            image = request.files['imagen']
            image_data = image.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            user = user_collection.find_one({'username': session['username']})
            if user:
                user_id = user['_id']
                
                user_ref = DBRef('users', user_id)
                
                component_data = {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'precio': precio,
                    'stock': stock,
                    'condicion': condicion,
                    'image': image_base64,
                    'user_id': user_ref
                }
                
                component_id = components_collection.insert_one(component_data).inserted_id
            
                user_collection.update_one({'_id': user_id}, {'$push': {'componentes': DBRef('components', component_id)}})
            
                return redirect(url_for('detalle_componente', componente_id=component_id))
        return render_template('add_component.html')
    return redirect(url_for('login'))
@app.route('/detalle_componente/<componente_id>')
def detalle_componente(componente_id):
    if 'logged_in' in session:
        
        componente = components_collection.find_one({'_id': ObjectId(componente_id)})
        
        if componente:
            return render_template('detalle_componente.html', componente=componente)
        
        return redirect(url_for('index'))
    return redirect(url_for('login'))        

@app.route('/editar_componente/<componente_id>', methods=['POST', 'GET'])
def editar_componente(component_id):
    if 'username' in session:
        componente = components_collection.find_one({'_id': ObjectId(component_id)})
        
        user = user_collection.find_one({'username': session['username']})
        es_vendedor = user['role'] == 'Vendedor' if user else Falsuevoe
        
        if es_vendedor:
            if requested.method == 'POST':
                nuevo_nombre = request.form['nombre']
                nueva_descripcion = request.form['descripcion']
                nuevo_precio = float(request.form['precio'])
                nuevo_stock = int(request.form['stock'])
                
                update_data = {
                    '$set': {
                        'nombre': nuevo_nombre,
                        'descripcion': nueva_descripcion,
                        'precio': nuevo_precio,
                        'stock': nuevo_stock
                    }
                
                }
                
                components_collection.update_one({'_id': ObjectId(component_id)}, update_data)
                
                return redirect(url_for('detalle_componente', componente_id=component_id))
        return render_template('editar_componente.html', componente_id=componente_id)
    return redirect(url_for('login'))
                
@app.route('/eliminar_componente/<componente_id>', methods=['POST', 'GET'])
def eliminar_componente(componente_id):
    if 'username' in session:
        
        user = user_collection.find_one({'username': session['username']})
        es_vendedor = user['role'] == 'Vendedor' if user else False
        
        if es_vendedor:
            
            components_collection.delete_one({'_id': ObjectId(componente_id)})
            
            user_collection.update_many({},{'$pull': {'componentes': {'$id': ObjectId(componente_id)}}})
            
            return redirect(url_for('seller_products'))
        
        return redirect(url_for('index'))
    return redirect(url_for('login'))



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