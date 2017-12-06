from sqlalchemy.orm import sessionmaker
from database import db_engine, User, Category, Item

# Create a session factory object for creating db sessions connected to the
# app's database
SessionFactory = sessionmaker(bind=db_engine)
db_session = SessionFactory()   # instantiate a session for db access

# Initialize database with dummy data
category_names = ['Tech', 'Restaurants', 'Baseball', 'Football', 'Basketball',
                  'Soccer', 'Hockey', 'Companies', 'Food', 'Drinks']

categories = [Category(name=category_name) for category_name in category_names]
db_session.add_all(categories)
db_session.commit()

for new_category in categories:
    print 'Category \'%s\' successfully created!' % new_category.name
