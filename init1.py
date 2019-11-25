#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib
import os
import time
SALT = "CS3083"
IMAGES_DIR = os.path.join(os.getcwd(), "static")

#Initialize the app from Flask
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       db='Finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def hello():
    return render_template('index.html')

#code for uploading image
@app.route('/upload', methods=["GET"])
def upload():
    return render_template("upload.html")

@app.route("/uploadImage", methods=["POST"])

def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        print(filepath)
        image_file.save(filepath)
        query = "INSERT INTO Photo(postingdate, filepath, photoPoster, allFollowers, caption) VALUES (%s, %s, %s, %s, %s)"
        cursor = conn.cursor()
        print((time.strftime('%Y-%m-%d %H:%M:%S'), image_name, session['username']))
        followerVisible = int(request.form['followerVisible'])
        caption = request.form['caption']
        cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, session['username'], followerVisible, caption))
        conn.commit()
        cursor.close()
        message = "Image has been successfully uploaded."
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)


#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + SALT
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashed_password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + SALT
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO Person(username, password) VALUES(%s, %s)'
        cursor.execute(ins, (username, hashed_password))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user = session['username']
    #to find all visible photos
    cursor = conn.cursor()
    query = '(SELECT photoID, photoPoster, filepath, postingdate, caption FROM Photo WHERE photoPoster = %s) UNION (SELECT photoID, photoPoster, filepath, postingdate, caption FROM Photo NATURAL JOIN SharedWith NATURAL JOIN BelongTo WHERE member_username = %s) UNION (SELECT photoID, photoPoster,filepath, postingdate, caption FROM Photo JOIN Follow ON photoPoster = username_followed WHERE username_follower = %s AND allFollowers = 1) ORDER BY postingdate DESC'
    cursor.execute(query, (user, user, user))
    data = cursor.fetchall()

    #to find data about all visible photos
    photoInfo = []
    for photo in data:
        # print(photo['photoPoster'])
        query = 'SELECT firstName,lastName FROM Photo JOIN Person ON photoPoster = username WHERE photoPoster = %s'
        cursor.execute(query, (photo['photoPoster'] ))
        photoInfo.append( cursor.fetchone() )

    #to find tags for all visible photos
    tags = []
    for photo in data:
        # print(photo['photoPoster'])
        query = 'SELECT firstName,lastName, username FROM Photo NATURAL JOIN Tagged NATURAL JOIN Person WHERE photoID = %s'
        cursor.execute(query, (photo['photoID'] ))
        tags.append( cursor.fetchall() )

    #find likes and rating
    likes = []
    for photo in data:
        # print(photo['photoPoster'])
        query = 'SELECT username,rating FROM Photo natural JOIN Likes WHERE photoID = %s'
        cursor.execute(query, (photo['photoID'] ))
        likes.append( cursor.fetchall() )

    cursor.close()
    return render_template('home.html', username=user, posts=data, photoInfo = photoInfo, tagged=tags, liked=likes)

'''

@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session['username']
    cursor = conn.cursor();
    blog = request.form['blog']
    query = 'INSERT INTO blog (blog_post, username) VALUES(%s, %s)'
    cursor.execute(query, (blog, username))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/select_blogger')
def select_blogger():
    #check that user is logged in
    username = session['username']
    #should throw exception if username not found
    
    cursor = conn.cursor();
    query = 'SELECT DISTINCT username FROM blog'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('select_blogger.html', user_list=data)

@app.route('/show_posts', methods=["GET", "POST"])
def show_posts():
    #check that user is logged in
    username = session['username']
    
    poster = request.args['poster']
    cursor = conn.cursor();
    query = 'SELECT ts, blog_post FROM blog WHERE username = %s ORDER BY ts DESC'
    cursor.execute(query, poster)
    data = cursor.fetchall()
    cursor.close()
    return render_template('show_posts.html', poster_name=poster, posts=data)

'''

@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
