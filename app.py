from flask import Flask, render_template, request, redirect, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')

app.secret_key = 'your_secret_key'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'system'
app.config['MYSQL_DB'] = 'local'

mysql = MySQL(app)

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND role = %s", (username, role))
        user = cur.fetchone()

        if user and user[2] == password:
            session['user_id'] = user[0]
            session['role'] = user[3]
            if role == 'vendor':
                return redirect('/vendor_dashboard')
            else:
                return redirect('/customer_dashboard')
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/vendor_dashboard', methods=['GET', 'POST'])
def vendor_dashboard():
    if 'role' in session and session['role'] == 'vendor':
        if request.method == 'POST':
            market_name = request.form['market_name']
            location = request.form['location']
            contact_details = request.form['contact_details']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            user_id = session['user_id']

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO vendors (user_id, market_name, location, contact_details, latitude, longitude) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (user_id, market_name, location, contact_details, latitude, longitude))
            mysql.connection.commit()
            return render_template('vendor_add_products.html')
        return render_template('vendor_dashboard.html')
    return redirect('/login')

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'role' in session and session['role'] == 'customer':
        cur = mysql.connection.cursor()
        cur.execute("SELECT vendors.market_name, vendors.location, vendors.contact_details, vendors.latitude, vendors.longitude, "
                    "GROUP_CONCAT(products.product_name) AS products "
                    "FROM vendors LEFT JOIN products ON vendors.id = products.vendor_id GROUP BY vendors.id")
        vendors = cur.fetchall()
        return render_template('customer_dashboard.html', vendors=vendors)
    return redirect('/login')


# Register function
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # # Hash the password before storing it
        # hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()

        # Check if username already exists
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            return "Username already exists. Please choose a different username."
        else:
            # Insert new user into the database
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            mysql.connection.commit()

            return redirect('/login')  # Redirect to login page after successful registration

    return render_template('register.html')


@app.route('/add_multiple_products', methods=['POST'])
def add_multiple_products():
    if request.method == 'POST':
        # Get product data from the form
        names = request.form.getlist('name[]')
        promotions = request.form.getlist('promotion[]')
        vendor_id = session['user_id']
    
        # Create a cursor to interact with the database
        cur = mysql.connection.cursor()

        # Loop through the products and insert each one
        for i in range(len(names)):
            name = names[i]
            promotion = promotions[i]

            # Insert product into the database
            cur.execute("INSERT INTO products (vendor_id,product_name, promotion) VALUES (%s,%s, %s)", 
                        (vendor_id,name, promotion))

        # Commit changes and close the cursor
        mysql.connection.commit()
        cur.close()

        return "Product added successfully"

        

@app.route('/search_vendors', methods=['GET', 'POST'])
def search_products():
    if request.method == 'POST':
        # Get the search term from the form input
        search_term = request.form['product_name']

        # Create a cursor to interact with the database
        cur = mysql.connection.cursor()

        # SQL query to search for products by name and join with the users table for vendor info
        query = """
        SELECT p.id AS product_id, p.product_name AS product_name, p.promotion AS product_description, 
               u.username AS vendor_name
        FROM products p
        JOIN users u ON p.vendor_id = u.id
        WHERE p.product_name LIKE %s
        """
        
        # Execute the query with the search term (using % to match the search term)
        cur.execute(query, ('%' + search_term + '%',))
        
        # Fetch all the results
        results = cur.fetchall()
        
        # Close the cursor
        cur.close()

        # Render the search results page
        return render_template('customer_dashboard.html', results=results, search_term=search_term)
    
    # If GET request, simply render the search form
    return render_template('customer_dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=8080)
