from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from flask_bcrypt import Bcrypt
from datetime import datetime
from bson import DBRef
import base64
from flask_mail import Mail, Message
from datetime import timedelta



load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = 'fd4cbd6e26ed4a'
app.config['MAIL_PASSWORD'] = '4ec63b83f278b0'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Establecer la ruta donde se guardarán las imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo_db_url =  os.environ.get("MONGO_DB_CONN_STRING")

client = MongoClient(mongo_db_url)
db = client['Electrade']
servicios_collection = db['servicios']
user_collection = db['users']
components_collection = db['components']

@app.route('/')
def index():
    componentes_disponibles = components_collection.find()
    return render_template('index.html', componentes=componentes_disponibles)

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
            'creada': datetime.utcnow(),
            'direccion': 'No registrada'
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
                vendedor_id = user['_id']
                componentes_publicados = components_collection.count_documents({'user_id': DBRef('users', vendedor_id)})
                total_ventas = 0
                componentes_vendedor = components_collection.find({'user_id': DBRef('users', vendedor_id)})
                for componente in componentes_vendedor:
                    total_ventas += componente.get('compras', 0)
                return render_template('perfil_vendedor.html', username=session['username'], created=created, time_elapsed=time_elapsed_str, role=role, componentes_publicados=componentes_publicados,total_ventas=total_ventas)
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

            
            image = request.files['imagen']
            if image:
                # Guardar la imagen en el sistema de archivos
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                image.save(image_path)
            
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
                        'image': image_path,
                        'user_id': user_ref
                    }
                    
                    component_id = components_collection.insert_one(component_data).inserted_id
                
                    user_collection.update_one({'_id': user_id}, {'$push': {'componentes': DBRef('components', component_id)}})
                
                    return redirect(url_for('detalle_componente', componente_id=component_id))
        return render_template('add_component.html')
    return redirect(url_for('login'))

@app.route('/detalle_componente/<componente_id>', methods=['POST', 'GET'])
def detalle_componente(componente_id):
        user = user_collection.find_one({'username': session['username']})
        user_id = user_collection.find_one({'username': session['username']})['_id']
        componente = components_collection.find_one({'_id': ObjectId(componente_id)})
        rol = user_collection.find_one({'username': session['username']})['role']
        vendedor_id = user['_id']
        image = componente['image']


        print(image)
        componente_id = componente['_id']
        if componente:
            vendedor_ref = componente['user_id']
            if vendedor_ref:
                vendedor_id = vendedor_ref.id
                vendedor = user_collection.find_one({'_id': ObjectId(vendedor_id)})
                created = vendedor.get('creada', datetime.utcnow())

                
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
                    
                if 'logged_in' in session:
                    if rol == 'Vendedor':
                        return render_template('detalle_componente.html', componente=componente, vendedor=vendedor, time_elapsed=time_elapsed_str, componente_id=componente_id, user_id=user_id, rol=rol, image=image, total_ventas=total_ventas)
                    else:
                        total_ventas = 0
                        componentes_vendedor = components_collection.find({'user_id': DBRef('users', vendedor_id)})
                        for componente in componentes_vendedor:
                            total_ventas += componente.get('compras', 0)
                        return render_template('detalle_componente.html', componente=componente, vendedor=vendedor, time_elapsed=time_elapsed_str, componente_id=componente_id, user_id=user_id, rol=rol, image=image, total_ventas=total_ventas)
            return render_template('detalle_componente.html', componente=componente)
        else:
            flash('Componente no encontrado', 'error')
            return redirect(url_for('componentes'))


@app.route('/editar_componente/<componente_id>', methods=['POST', 'GET'])
def editar_componente(componente_id):
    if 'username' in session:
        componente = components_collection.find_one({'_id': ObjectId(componente_id)})
        
        user = user_collection.find_one({'username': session['username']})
        
        if request.method == 'POST':
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
                
                components_collection.update_one({'_id': ObjectId(componente_id)}, update_data)
                
                return redirect(url_for('detalle_componente', componente_id=componente_id))
        return render_template('editar_componente.html', componente_id=componente_id)
    return redirect(url_for('login'))
 
@app.route('/agregar_carrito/<user_id>/<componente_id>', methods=['POST', 'GET'])
def agregar_carrito(user_id, componente_id):
    componente = components_collection.find_one({'_id': ObjectId(componente_id)})

    if 'logged_in' in session:
        username = session['username']
        user = user_collection.find_one({'username': username})
        rol = user['role']
        if rol == 'Comprador':
            if 'carrito' not in session:
                session['carrito'] = []

             # Convierte los IDs a tipos de datos compatibles
            user_id = str(user_id)
            componente_id = str(componente_id)

            # Agrega el componente al carrito del usuario actual
            session['carrito'].append({'user_id': user_id, 'componente_id': componente_id})

            flash('Componente agregado al carrito', 'agregado_exito')
            print("Contenido del carrito después de agregar:", session['carrito'])
            return redirect(url_for('detalle_componente', componente_id=componente_id))

        else:
            flash('No eres un comprador', 'error')
            return redirect(url_for('detalle_componente', componente_id=componente_id))

    else:
        flash('Inicia sesión para agregar al carrito', 'info')
        return redirect(url_for('detalle_componente', componente_id=componente_id))

@app.route('/eliminar_carrito/<componente_id>', methods=['POST', 'GET'])
def eliminar_carrito(componente_id):
    if 'logged_in' in session and 'carrito' in session:
        carrito = session['carrito']
        for item in carrito:
            if item['componente_id'] == componente_id:
                carrito.remove(item)
                session['carrito'] = carrito
                flash('Componente eliminado del carrito', 'info')
                return redirect(url_for('mostrar_carrito'))
        flash('Componente no encontrado en el carrito', 'error')
        return redirect(url_for('mostrar_carrito'))
    else:
        flash('Inicia sesión para eliminar del carrito', 'info')
        return redirect(url_for('mostrar_carrito'))

@app.route('/mostrar_carrito')
def mostrar_carrito():
    if 'logged_in' in session and 'carrito' in session:
        carrito = session['carrito']
        componentes_carrito = []
        total_precio = 0
        envio = 0
        user = user_collection.find_one({'username': session['username']})

        for item in carrito:
            user_id = item['user_id'] 
            componente_id = item['componente_id']

            
            
            usuario = user_collection.find_one({'_id': ObjectId(user_id)})
            componente = components_collection.find_one({'_id': ObjectId(componente_id)})
            
            total_precio += componente['precio']  # Sumar el precio del componente al total


            componentes_carrito.append({'user': usuario, 'componente': componente})    
            print(componentes_carrito) 

        return render_template('mostrar_carrito.html', componentes_carrito=componentes_carrito, user=user, total_precio=total_precio, envio=envio)
        

    else:
        flash('El carrito está vacío', 'info')
        return render_template('mostrar_carrito.html')
    
@app.route('/agregar_direccion', methods=['POST', 'GET'])
def agregar_direccion():
    if 'logged_in' in session:
        user = user_collection.find_one({'username': session['username']})
        if request.method == 'POST':
            direccion = request.form['direccion']
            celular = request.form['celular']
            
            add_data = {'direccion': direccion, 'celular': celular}
            
            user_collection.update_one({'username': session['username']}, {'$set': add_data})
            return redirect(url_for('mostrar_carrito'))
        return render_template('agregar_direccion.html')
    return redirect(url_for('login'))
                
@app.route('/eliminar_componente/<componente_id>', methods=['POST', 'GET'])
def eliminar_componente(componente_id):
    if 'username' in session:
        
        user = user_collection.find_one({'username': session['username']})
        vendedor = user['role']
        
        if vendedor == 'Vendedor' :
            
            components_collection.delete_one({'_id': ObjectId(componente_id)})
            
            user_collection.update_many({},{'$pull': {'componentes': {'$id': ObjectId(componente_id)}}})
            
            session.pop('carrito', None)
            return redirect(url_for('seller_products'))
        
        return redirect(url_for('index'))
    return redirect(url_for('login'))


@app.route('/finalizar_compra', methods=['POST'])
def finalizar_compra():
    if 'logged_in' in session and 'carrito' in session:
        carrito = session['carrito']

        # Obtener la fecha y hora actual
        fecha_compra = datetime.utcnow()

        # Crear una lista para almacenar los detalles del pedido
        detalles_pedido = []

        # Enviar correo al vendedor
        for item in carrito:
            componente_id = item['componente_id']
            componente = components_collection.find_one({'_id': ObjectId(componente_id)})
            vendedor_id = componente['user_id'].id
            vendedor = user_collection.find_one({'_id': ObjectId(vendedor_id)})

            user_id = item['user_id']
            usuario = user_collection.find_one({'_id': ObjectId(user_id)})

            # Incrementar la cantidad de compras en 1
            components_collection.update_one({'_id': ObjectId(componente_id)}, {'$inc': {'compras': 1}})

            # Calcular la fecha estimada de envío (2 días a partir de la fecha de compra)
            fecha_estimada_envio = fecha_compra + timedelta(days=2)

            # Agregar detalles del componente al pedido
            detalles_pedido.append({
                'nombre': componente['nombre'],
                'precio': componente['precio'],
                'fecha_compra': fecha_compra,
                'fecha_estimada_envio': fecha_estimada_envio,
                'componente_id': str(componente['_id'])
            })

            # Construir el mensaje del correo con la fecha y hora de compra
            subject = 'Compra realizada en ElecTrade'
            body = f'Se ha realizado una compra del artículo {componente["nombre"]}.\n\n' \
                   f'Precio: S/ {componente["precio"]}\n' \
                   f'Dirección de envío: {usuario["direccion"]}\n' \
                   f'Celular de contacto: {usuario["celular"]}\n' \
                   f'Fecha y hora de compra: {fecha_compra} UTC\n' \
                   f'Fecha estimada de envío: {fecha_estimada_envio} UTC'

            # Crear el objeto de mensaje
            message = Message(subject=subject,
                              recipients=[vendedor["email"]],
                              body=body,
                              sender='alexantast@gmail.com')

            # Enviar el correo
            mail.send(message)

            # Reducir el stock del componente
            nuevo_stock = componente['stock'] - 1
            components_collection.update_one({'_id': ObjectId(componente_id)}, {'$set': {'stock': nuevo_stock}})

        # Actualizar la colección de usuarios con los detalles del pedido
        user_collection.update_one({'username': session['username']}, {'$push': {'pedidos': detalles_pedido}})

        # Resto del código para finalizar la compra y redirigir a la sección de Mis Pedidos
        session.pop('carrito', None)
        flash('Compra realizada con éxito', 'compra_exito')
        return redirect(url_for('mis_pedidos'))

    else:
        flash('Inicia sesión y agrega componentes al carrito para finalizar la compra', 'info')
        return redirect(url_for('mostrar_carrito'))

@app.route('/mis_pedidos')
def mis_pedidos():
    if 'logged_in' in session:
        username = session['username']
        user = user_collection.find_one({'username': username})

        # Obtener la lista de pedidos del usuario
        pedidos = user.get('pedidos', [])

        # Obtener la información completa de cada componente junto con la fecha de compra
        componentes_info = []
        for pedido in pedidos:
            for componente_pedido in pedido:
                componente_id = componente_pedido['componente_id']
                componente_info = components_collection.find_one({'_id': ObjectId(componente_id)})
                if componente_info:
                    # Agregar la fecha de compra al diccionario del componente
                    componente_info['fecha_compra'] = componente_pedido['fecha_compra']
                    componente_info['fecha_estimada_envio'] = componente_pedido['fecha_estimada_envio']
                    
                    componentes_info.append(componente_info)

        return render_template('mis_pedidos.html', componentes_info=componentes_info)
    else:
        flash('Inicia sesión para ver tus pedidos', 'info')
        return redirect(url_for('login'))

@app.route('/componentes')
def componentes():
    componentes_disponibles = components_collection.find()
    return render_template('componentes.html', componentes=componentes_disponibles)

@app.route('/servicios')
def servicios():
    return render_template('servicios.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/enviar_mensaje', methods=['POST'])
def enviar_mensaje():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        mensaje = request.form['mensaje']

        # Construir el mensaje del correo
        subject = f'Mensaje de {nombre} - Contacto ElecTrade'
        body = f'Nombre: {nombre}\nCorreo Electrónico: {email}\n\nMensaje:\n{mensaje}'

        # Crear el objeto de mensaje
        message = Message(subject=subject,
                          recipients=['support@gmail.com'],  # Reemplaza con tu dirección de correo de soporte
                          body=body,
                          sender='alexantast@gmail.com')

        # Enviar el correo
        mail.send(message)
        flash('Mensaje enviado con éxito', 'mensaje_exito')
        return redirect(url_for('contacto'))
    else:
        flash('Error al enviar el mensaje', 'error')
        return redirect(url_for('contacto'))


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