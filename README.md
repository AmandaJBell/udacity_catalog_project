# udacity_catalog_project
Udacity Fullstack Nanodegree Catalog Project
# Project: Build Item Catalog
================================

This is the fourth project in the Udacity Full Stack Nanodegree. The purpose of this project is to build a basic CRUD application which allows users to view a clothing catalog, and if they are logged in to add, update, and delete items in the clothing catalog.

Required Libraries and Dependencies
-----------------------------------
This project requires Python v2.\*, Flask, and SQLAlchemy to be installed. 

In addition Vagrant and VirtualBox are also required.

You will also need to retrieve your own Google+ Oauth2 client_id and client_secret, and will need to add them to login.html, views.py, and client_secret.json where specified.

How to Run Project
------------------
**1.** After cloning the project, navigate to the repo in your terminal and unzip newsdata.zip.

**2.** Setup the VM by typing the following into terminal:
    ```vagrant up```

**3.** Login to the VM by typing the following into terminal:
    ```vagrant ssh```
    
**4.** Get to the right folder typing the following into terminal:
    ```cd /vagrant```

**5.** Finally run the project by typing the following into terminal:
    ```python views.py```
