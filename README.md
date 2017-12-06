# Item Catalog App

**Description**
---------------
An Item Catalog application that allows authenticated users to view, create, update, and delete categorized items. Google Sign-In is utilized to allow users to register and authenticate.

**3rd Party Tools Used**
- Flask web framework for Python
- SQLAlchemy ORM with SQLite DB
- Google OAuth
- JQuery


**Download**
---------------
To download the project source code, simply clone the repository or download and extract the zip of the repository.

**System Requirements**
- Python 2.7+
- [VirtualBox](https://www.virtualbox.org/)
- [Vagrant](https://www.vagrantup.com/)

**Requirements Installation**
- To install [VirtualBox](https://www.virtualbox.org/wiki/Downloads), download and install the 'platform package' for your operating system
- To install [Vagrant](https://www.vagrantup.com/downloads.html), download and install the package for your operating system


**Setup**
---------------
1. Open the command line interface application ("Terminal" application on Mac, Linux; "Command Prompt" application on Windows)
2. Enter 'cd {project directory path}/vagrant' to change to the vagrant directory of the project folder
3. From within the vagrant directory:
    - Enter 'vagrant up' to start the vagrant virtual machine
    - Enter 'vagrant ssh' to connect to the VM (virtual machine)
4. Enter 'cd /vagrant/catalog', **within the VM**, to change to the catalog directory of the project folder
5. From within the catalog directory of the project folder:
    - Enter 'python database.py' to generate the app's database file 'itemcatalog.db'
    - Enter 'python initcatalog.py' to populate the database with sample categories


**Run**
---------------
To start the application, using Terminal, run 'python application.py' **from within the VM** '/vagrant/catalog' directory. Then visit http://localhost:5000/ in your favorite browser.

**JSON Endpoint**
- Visit http://localhost:5000/catalog.json to view the JSON data for the app's catalog