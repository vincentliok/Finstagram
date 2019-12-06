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
                       port=3306,
                       user='root',
                       password='',
                       db='Finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


def loadHome():
    user = session['username']
    # to find all visible photos
    cursor = conn.cursor()
    query = '(SELECT photoID, photoPoster, filepath, postingdate, caption FROM Photo WHERE photoPoster = %s) UNION (SELECT photoID, photoPoster, filepath, postingdate, caption FROM Photo NATURAL JOIN SharedWith NATURAL JOIN BelongTo WHERE member_username = %s) UNION (SELECT photoID, photoPoster,filepath, postingdate, caption FROM Photo JOIN Follow ON photoPoster = username_followed WHERE username_follower = %s AND followstatus = 1 AND allFollowers = 1) ORDER BY postingdate DESC'
    cursor.execute(query, (user, user, user))
    data = cursor.fetchall()

    # to find data about all visible photos
    photoInfo = []
    for photo in data:
        # print(photo['photoPoster'])
        query = 'SELECT firstName,lastName FROM Photo JOIN Person ON photoPoster = username WHERE photoPoster = %s'
        cursor.execute(query, (photo['photoPoster']))
        photoInfo.append(cursor.fetchone())

    # to find tags for all visible photos
    tags = []
    for photo in data:
        # print(photo['photoPoster'])
        query = 'SELECT firstName,lastName, username FROM Photo NATURAL JOIN Tagged NATURAL JOIN Person WHERE photoID = %s AND tagstatus = 1'
        cursor.execute(query, (photo['photoID']))
        tags.append(cursor.fetchall())

    # find likes and rating
    likes = []
    for photo in data:
        # print(photo['photoPoster'])
        query = 'SELECT username,rating FROM Likes WHERE photoID = %s'
        cursor.execute(query, (photo['photoID']))
        likes.append(cursor.fetchall())

    userlike = []
    for photo in data:
        query = 'SELECT username,rating FROM Likes WHERE photoID = %s AND username = %s'
        cursor.execute(query, (photo['photoID'], user))
        userlikedata = cursor.fetchone()
        if (userlikedata):
            userlike.append(1)
        else:
            userlike.append(0)

    # for tag requests, should only have max of 1 tag per photo
    tagRequests = []
    for photo in data:
        query = 'SELECT * FROM Tagged WHERE photoID = %s AND tagstatus = 0 AND username = %s'
        cursor.execute(query, (photo['photoID'], user))
        # jinja loop in home.html loops through index so we need something even if result returns none
        tagRequests.append(cursor.fetchone())

    comments = []
    for photo in data:
        query = 'SELECT username, comment, commentTime FROM Commented WHERE photoID = %s ORDER BY commentTime DESC'
        cursor.execute(query, (photo['photoID']))
        comments.append(cursor.fetchall())

    cursor.close()
    return user, data, photoInfo, tags, likes, userlike, tagRequests, comments



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
    firstName = request.form['firstName']
    lastName = request.form['lastName']
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
        ins = 'INSERT INTO Person(username, password,firstName,lastName) VALUES(%s, %s, %s, %s)'
        cursor.execute(ins, (username, hashed_password, firstName,lastName))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
    return render_template('home.html', username=user, posts=data, photoInfo = photoInfo, tagged=tags, liked=likes, userlike=userlike, tagRequests=tagRequests, comments=comments)

@app.route('/rate', methods=['POST'])
def rate():
    user = session['username']
    photoID = request.form['submitRating']
    rating = request.form['ratings']
    cursor = conn.cursor()
    
    query = 'INSERT INTO Likes(username, photoID, liketime, rating) VALUES(%s, %s, %s, %s)'
    cursor.execute(query, (user, photoID, time.strftime('%Y-%m-%d %H:%M:%S'), rating))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))
    
@app.route('/removeRating', methods=['POST'])
def removeRating():
    user = session['username']
    photoID = request.form['removeRating']
    cursor = conn.cursor()
    
    query = 'DELETE FROM Likes WHERE username = %s AND photoID = %s'
    cursor.execute(query, (user, photoID))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))
    
@app.route('/postComment', methods=['POST'])
def postComment():
    user = session['username']
    photoID = request.form['submitComment']
    comment = request.form['comment']
    cursor = conn.cursor()
    
    query = 'INSERT INTO Commented(username, photoID, commentTime, comment) VALUES(%s, %s, %s, %s)'
    cursor.execute(query, (user, photoID, time.strftime('%Y-%m-%d %H:%M:%S'), comment))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/tagUser', methods=['GET', 'POST'])
def tag():
    user = session['username']
    cursor = conn.cursor()
    data=''
    photoID=''
    username=''

    try:
        username = request.form['username']
        photoID = request.form['tag']
        #check userID is valid
        query = 'SELECT * FROM Person WHERE username = %s'
        cursor.execute(query, (username))
        data = cursor.fetchone()
    except:
        pass

    #if username valid, check if username already been tagged
    if data:
        query = 'SELECT * FROM Tagged WHERE username = %s AND photoID = %s'
        cursor.execute(query, (username,photoID))
        result = cursor.fetchone()
        # if username has already been tagged, respond with message
        if result:
            if result['tagstatus']:
                message = 'User has already been tagged'
            else:
                message = 'Request is still pending from user'


                # queries to load homepage with loaded photos
                user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
                cursor.close()
                return render_template('home.html', username=user, posts=data, photoInfo=photoInfo, tagged=tags,
                                       liked=likes, tagRequests=tagRequests, comments=comments, photoID=photoID,userlike=userlike,message=message)

        #user not already tagged
        else:
            print(username)
            #if it is self-tag, simply insert with tagstatus = 1
            if username == user:
                query = 'INSERT INTO Tagged(username, photoID ,tagstatus) VALUES (%s, %s, %s)'
                cursor.execute(query, (username, photoID, 1))
                conn.commit()
                message = "You've tagged yourself"


                # queries to load homepage with loaded photos
                user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
                cursor.close()
                return render_template('home.html', username=user, posts=data, photoInfo=photoInfo, tagged=tags,
                                       liked=likes, tagRequests=tagRequests,comments=comments, photoID=photoID,userlike=userlike,message=message)

            #if not self-tag, check if user can see the photoID

            #get all visible photos the searched user can see
            query = '(SELECT photoID, photoPoster, filepath, postingdate, caption FROM Photo WHERE photoPoster = %s) UNION (SELECT photoID, photoPoster, filepath, postingdate, caption FROM Photo NATURAL JOIN SharedWith NATURAL JOIN BelongTo WHERE member_username = %s) UNION (SELECT photoID, photoPoster,filepath, postingdate, caption FROM Photo JOIN Follow ON photoPoster = username_followed WHERE username_follower = %s AND followstatus = 1) ORDER BY postingdate DESC'
            cursor.execute(query, (username, username, username))
            photos = cursor.fetchall()
            photoIDs = {}
            for photo in photos:
                id = photo['photoID']
                photoIDs[id] = id

            # if photoID is in visible photos
            if int(photoID) in photoIDs:
                # make a tag requesdt to user with tagstatus = 0
                query = 'INSERT INTO Tagged(username, photoID ,tagstatus) VALUES (%s, %s, %s)'
                cursor.execute(query, (username, photoID, 0))
                conn.commit()
                message = "Tag request have been sent."

                user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
                cursor.close()
                return render_template('home.html', username=user, posts=data, photoInfo=photoInfo, tagged=tags,
                                       liked=likes, tagRequests=tagRequests,comments=comments, photoID=photoID,userlike=userlike,message=message)

    #user cant see the image.Thus error
    else:
        message = "Invalid tag request"
        # queries to load homepage with loaded photos
        user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
        cursor.close()
        return render_template('home.html', username=user, posts=data, photoInfo=photoInfo, tagged=tags,
                               liked=likes, tagRequests=tagRequests, comments=comments, photoID=photoID,
                               userlike=userlike, message=message)



@app.route('/acceptTag', methods=['GET', 'POST'])
def acceptTag():
    user = session['username']
    cursor = conn.cursor()
    tagMessage=''
    photoID =''
    try:
        photoID = request.form['accept']
        #update tagstatus based on accepted photoID
        cursor = conn.cursor()

        query = 'UPDATE Tagged SET tagstatus = 1 WHERE Tagged.username = %s AND Tagged.photoID = %s'
        cursor.execute(query, (user, photoID))
        tagMessage = "You've accepted to be tagged"
        conn.commit()
    except:
        pass

    user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
    cursor.close()
    return render_template('home.html', username=user, posts=data,userlike=userlike, comments=comments,photoInfo = photoInfo, tagged=tags, liked=likes, tagRequests=tagRequests, tagMessage=tagMessage, photoID=photoID)

@app.route('/DeclineTag', methods=['GET', 'POST'])
def declineTag():
    user = session['username']
    cursor = conn.cursor()
    tagMessage=''
    photoID = ''
    try:
        photoID = request.form['decline']
        #update tagstatus based on accepted photoID
        cursor = conn.cursor()

        #delete request by deleting entry in tagged
        query = 'DELETE FROM Tagged WHERE Tagged.username = %s AND Tagged.photoID = %s '
        cursor.execute(query, (user, photoID))
        tagMessage = "You've rejected to be tagged"
        conn.commit()
    except:
        pass

    #queries to load homepage with loaded photos

    user, data, photoInfo, tags, likes, userlike, tagRequests, comments = loadHome()
    cursor.close()
    return render_template('home.html', username=user, posts=data, comments=comments, photoInfo = photoInfo,userlike=userlike, tagged=tags, liked=likes, tagRequests=tagRequests, tagMessage=tagMessage, photoID=photoID)


@app.route('/manageFollows')
def follow():
    #search for all follow requests

    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT * FROM Follow WHERE username_followed = %s AND followstatus = 0'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    requests = []
    for i in data:
        requests.append(i['username_follower'])
    cursor.close()

    return render_template('follows.html',requests=requests)

@app.route('/acceptFollow', methods=['GET','POST'])
def accept():
    user = session['username']
    cursor = conn.cursor()
    message = ''

    try:
        username = request.form['accept']

        #update followStatus based in accepted username
        cursor = conn.cursor()
        query = 'UPDATE Follow SET followstatus = 1 WHERE Follow.username_followed = %s AND Follow.username_follower = %s'
        cursor.execute(query, (user, username))
        message = "You've accepted {} as a follower".format(username)
        conn.commit()
    except:
        pass

    # query for follow requests
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT * FROM Follow WHERE username_followed = %s AND followstatus = 0'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    requests = []
    for i in data:
        requests.append(i['username_follower'])
    cursor.close()

    return render_template('follows.html', requests=requests,message=message)

@app.route('/DeclineFollow', methods=['GET','POST'])
def decline():
    user = session['username']
    message = ''
    try:
        username = request.form['decline']

        #delete request from follow table
        cursor = conn.cursor()
        query = 'DELETE FROM Follow WHERE Follow.username_followed = %s AND Follow.username_follower = %s '
        cursor.execute(query, (user, username))
        message = "You've rejected {} as follower".format(username)
        conn.commit()
    except:
        cursor = conn.cursor()


    # query for follow requests
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT * FROM Follow WHERE username_followed = %s AND followstatus = 0'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    requests = []
    for i in data:
        requests.append(i['username_follower'])
    cursor.close()

    return render_template('follows.html', requests=requests,message=message)


#manage follow page
@app.route('/findID', methods=['GET', 'POST'])
def findID():
    user = session['username']
    username = request.form['username']
    cursor = conn.cursor()

    #find if searched user exists
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    data = cursor.fetchone()
    if (data):
        # if userID exists, search if there is already an follow request or already following

        query = 'SELECT * FROM Follow WHERE username_followed = %s AND username_follower = %s'
        cursor.execute(query, (username,user))
        result = cursor.fetchone()
        if result:
            # different message depending if user has accepted request
            if result['followstatus']:
                message = "You've already followed this user"
            else:
                message = 'Request is still pending from user'
        else:
            # if no entry in the follow table, submit an follow request with followStatus = 0
            query = 'INSERT INTO Follow(username_followed, username_follower ,followstatus) VALUES (%s, %s, %s)'
            cursor.execute(query, (username,user,0))
            conn.commit()
            message = "Follow request have been sent."

        #query for follow requests
        user = session['username']
        cursor = conn.cursor()
        query = 'SELECT * FROM Follow WHERE username_followed = %s AND followstatus = 0'
        cursor.execute(query, (user))
        data = cursor.fetchall()
        requests = []
        for i in data:
            requests.append(i['username_follower'])
        cursor.close()

        return render_template('follows.html',message=message, requests=requests)

    #if userid don't exist, return error
    else:

        #query for follow requests
        user = session['username']
        cursor = conn.cursor()
        query = 'SELECT * FROM Follow WHERE username_followed = %s AND followstatus = 0'
        cursor.execute(query, (user))
        data = cursor.fetchall()
        requests = []
        for i in data:
            requests.append(i['username_follower'])

        cursor.close()
        error = "This user does not exist"
        return render_template('follows.html',error=error, requests=requests)

# Routes to add friend group
@app.route('/addGroup')
def addFriendGroup():
    user = session['username']
    return render_template('create_group.html')

# A user creates a Friend Group with a different name than his other groups. Otherwise there is an error
@app.route('/addGroupAuth', methods=['GET', 'POST'])
def addFriendGroupAuth():
    username = session['username']
    cursor = conn.cursor()
    group_name = request.form['name']
    description = request.form['description']
    query = 'SELECT groupName FROM friendgroup WHERE groupOwner = %s and groupName = %s'
    cursor.execute(query, (username, group_name))
    group_list = cursor.fetchone()
    cursor.close()
    error = None
    success = None
    if (group_list):
        # If the previous query returns data, then groupName exists with the same groupOwner
        error = "This group name already exists"
        return render_template('create_group.html', error = error)
    else:
        insert = 'INSERT INTO friendgroup VALUES(%s, %s, %s)'
        cursor.execute(insert, (username, group_name, description))
        cursor.close()
        success = "You have successfully created the group: "
        return render_template('create_group.html', success = success, groupName = group_name)


# Shows list of groups the user owns and gives the option to select add friend to group
@app.route('/friendgroups')
def friendgroups():
    # check that user is logged in
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT groupName FROM friendgroup WHERE groupOwner = %s'
    cursor.execute(query, user)
    groups = cursor.fetchall()
    cursor.close()
    return render_template('friendgroups.html', friendgroups = groups, groupOwner = user)

# Adds person to selected group if the friend is not already in the group and person exists
@app.route('/add_friend_to_group', methods=['GET', 'POST'])
def add_friend():
    user = session['username']
    groupName = request.args['groupName']
    session['groupName'] = groupName
    return render_template('addFriendToGroup.html', username = user, groupName =groupName)


# Identifies if the username or member being added to group exists in person
# or if the username is already in the group
@app.route('/add_friend_to_groupauth', methods=['GET', 'POST'])
def add_friendauth():
    owner = session['username']
    friend = request.form['username']
    groupName = session['groupName']
    cursor = conn.cursor()
    query = 'SELECT username FROM person WHERE username = %s'
    cursor.execute(query, (friend))
    friend = cursor.fetchone()
    cursor.close()
    error_exists = None
    error_empty = None
    if friend:
        # If found username or person exists
        cursor = conn.cursor()
        query = 'SELECT * FROM belongto JOIN friendgroup USING(groupName) WHERE member_username = %s AND belongto.owner_username = %s AND friendgroup.groupOwner = %s AND groupName = %s'
        cursor.execute(query, (friend, owner, owner, groupName))
        found_friend = cursor.fetchone()
        if found_friend:
            # returns an error message to html page if member already part of the group
            error_exists = "This username is already a member"
            return render_template('addFriendToGroup.html', username = owner, groupName = groupName ,error = error_exists)
        else:
            insert = 'INSERT INTO belongto VALUES(%s, %s, %s)'
            cursor.execute(insert, (friend, owner, groupName))
            conn.commit()
            cursor.close()
            return render_template('addFriendToGroup.html')
    else:
        #If the person does not exists in the database
        error_empty = "This user does not exists"
        return render_template('addFriendToGroup.html', username = owner, groupName = groupName, error = error_empty)

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
