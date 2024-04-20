#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime

from flask import Flask, render_template, request, redirect, url_for, make_response

# import logging
import sentry_sdk
from sentry_sdk.integrations.flask import (
    FlaskIntegration,
)  # delete this if not using sentry.io

# from markupsafe import escape
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from dotenv import load_dotenv

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
load_dotenv(override=True)  # take environment variables from .env.

# initialize Sentry for help debugging... this requires an account on sentrio.io
# you will need to set the SENTRY_DSN environment variable to the value provided by Sentry
# delete this if not using sentry.io
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    # enable_tracing=True,
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
)

# instantiate the app using sentry for debugging
app = Flask(__name__)

# # turn on debugging if in development mode
# app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database

    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live


# set up the routes


@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    total_tasks = db.todos.count_documents({})
    important_tasks = db.todos.find({"priority": {"$gte": 8}}).sort("created_at", -1)
    return render_template("index.html", total_tasks=total_tasks, important_tasks=important_tasks)


@app.route("/tasks")
def read():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    task_count = db.todos.count_documents({}) 
    tasks = db.todos.find({}).sort("created_at", -1)
    return render_template("read.html", tasks=tasks, task_count=task_count)


@app.route("/create")
def create():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    if request.method == "POST":
        task_name = request.form["task_name"]
        priority = int(request.form["priority"])
        description = request.form["description"]
        task = {
            "name": task_name,
            "priority": priority,
            "description": description,
            "created_at": datetime.datetime.utcnow()
        }
        db.todos.insert_one(task)
        return redirect(url_for("read"))
    return render_template("create.html")  # render the create template


@app.route("/edit/<mongoid>")
def edit(mongoid):
    """
    Route for editing a task.
    """
    if request.method == "POST":
        updated_values = {
            "name": request.form["task_name"],
            "priority": int(request.form["priority"]),
            "description": request.form["description"],
            "created_at": datetime.datetime.utcnow()
        }
        db.todos.update_one({"_id": ObjectId(mongoid)}, {"$set": updated_values})
        return redirect(url_for("read"))
    task = db.todos.find_one({"_id": ObjectId(mongoid)})
    return render_template("edit.html", task=task)

@app.route("/delete/<mongoid>")
def delete(mongoid):
    """
    Route for GET requests to the delete page.
    Deletes the specified record from the database, and then redirects the browser to the read page.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be deleted.
    """
    db.todos.delete_one({"_id": ObjectId(mongoid)})
    return redirect(url_for("read"))

@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run(load_dotenv=True)
